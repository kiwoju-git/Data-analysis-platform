"""Dataset request races against real synthetic server writes, not hook mocks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import APIResponse, Browser, Page, Route, expect

from app_readiness import diagnosed_page, wait_for_app_ready


def _create_version(page: Page, base_url: str, name: str) -> dict:
    response = page.request.post(
        base_url + "/api/v1/datasets",
        headers={"Origin": base_url},
        multipart={
            "file": {
                "name": name + ".csv",
                "mimeType": "text/csv",
                "buffer": f"{name},group\n1,A\n2,A\n3,A\n4,B\n5,B\n6,B\n".encode(),
            }
        },
    )
    assert response.status == 201, response.text()
    response = page.request.post(
        base_url + f"/api/v1/datasets/{response.json()['dataset_id']}/confirm-parsing",
        headers={"Origin": base_url},
        data={
            "parsing": {
                "kind": "delimited_text",
                "encoding": "utf-8",
                "delimiter": ",",
                "quote_char": '"',
                "decimal": ".",
                "thousands": None,
                "has_header": True,
                "header_row": 1,
                "data_start_row": 2,
                "missing_tokens": ["", "NA"],
            },
            "columns": [],
        },
    )
    assert response.status == 201, response.text()
    return response.json()


def _open(page: Page, base_url: str, version: dict, locale: str) -> None:
    page.goto(
        base_url + "/datasets?dataset_version_id=" + version["version_id"],
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, locale, "/datasets")
    _expect_active(page, version)


def _expect_active(page: Page, version: dict) -> None:
    expect(page.locator("#active-dataset-version")).to_have_value(version["version_id"])
    expect(
        page.locator(".schema-table tbody tr").first.locator("input").first
    ).to_have_value(version["columns"][0]["display_name"])
    page.wait_for_function(
        "id => new URL(location.href).searchParams.get('dataset_version_id') === id && "
        "sessionStorage.getItem('datalab.current_dataset_version_id') === id",
        arg=version["version_id"],
    )


class HeldWrite:
    """Let the server commit; withhold only its response to the originating tab."""

    def __init__(self, page: Page, path: str, method: str):
        self.page, self.path, self.method = page, path, method
        self.route: Route | None = None
        self.response: APIResponse | None = None
        self.payload: dict | None = None
        self.request: dict | None = None

    def handle(self, route: Route) -> None:
        if (
            self.route is not None
            or route.request.method != self.method
            or urlsplit(route.request.url).path != self.path
        ):
            route.continue_()
            return
        self.route = route
        self.request = route.request.post_data_json
        self.response = route.fetch()
        assert self.response.status in (200, 201), self.response.text()
        self.payload = self.response.json()
        self.page.evaluate("window.__datasetWriteHeld = true")

    def wait(self) -> None:
        self.page.wait_for_function("window.__datasetWriteHeld === true")
        assert self.payload is not None

    def release(self) -> None:
        assert self.route is not None and self.response is not None
        with self.page.expect_response(
            lambda response: response.request.method == self.method
            and urlsplit(response.url).path == self.path
        ) as received:
            self.route.fulfill(response=self.response)
        assert received.value.json() == self.payload
        # Allow the fetch continuation and React commit to run, without using
        # networkidle (catalog/profile requests have separate lifecycles).
        self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )


def _unchanged(page: Page, base_url: str, version: dict) -> None:
    response = page.request.get(
        base_url + "/api/v1/dataset-versions/" + version["version_id"]
    )
    assert response.status == 200
    current = response.json()
    for key in ("schema_hash", "source_sha256", "columns", "canonical_artifact"):
        assert current[key] == version[key], key


def _schema_race(page: Page, base_url: str, first: dict, second: dict) -> dict:
    path = f"/api/v1/dataset-versions/{first['version_id']}/schema"
    held = HeldWrite(page, path, "PATCH")
    page.route("**" + path, held.handle)
    name = page.locator(".schema-table tbody tr").first.locator("input").first
    name.fill("saved-on-A-not-B")
    page.locator(".schema-actions button").last.click()
    held.wait()
    page.locator("#active-dataset-version").select_option(second["version_id"])
    _expect_active(page, second)
    held.release()
    _expect_active(page, second)
    expect(page.locator(".schema-actions button").last).to_be_enabled()
    _unchanged(page, base_url, second)
    saved = page.request.get(base_url + path).json()
    assert saved["columns"][0]["display_name"] == "saved-on-A-not-B"
    assert saved["schema_hash"] == held.payload["schema_hash"]
    return {
        "request": held.request,
        "saved_schema_hash": saved["schema_hash"],
        "active_version_id": second["version_id"],
    }


def _cell_race(page: Page, base_url: str, first: dict, second: dict) -> dict:
    path = f"/api/v1/dataset-versions/{first['version_id']}/cell-corrections"
    held = HeldWrite(page, path, "POST")
    page.route("**" + path, held.handle)
    cell = page.locator('.canonical-preview-grid [data-canonical-cell="0-0"]')
    expect(cell).to_contain_text("1")
    cell.click()
    page.locator(".canonical-preview-section .cell-edit-button").click()
    page.locator(".canonical-preview-section .cell-editor textarea").fill("18")
    page.locator(".canonical-preview-section .cell-editor .primary-button").click()
    dialog = page.locator('.confirmation-dialog[role="dialog"]')
    expect(dialog).to_be_visible()
    dialog.locator(".primary-button").click()
    held.wait()
    page.locator("#active-dataset-version").select_option(second["version_id"])
    _expect_active(page, second)
    held.release()
    _expect_active(page, second)
    expect(
        page.locator('.canonical-preview-grid [data-canonical-cell="0-0"]')
    ).to_contain_text("1")
    expect(page.locator(".canonical-preview-section .success-box")).to_have_count(0)
    _unchanged(page, base_url, first)
    _unchanged(page, base_url, second)
    child = held.payload["new_version"]
    stored = page.request.get(
        base_url + "/api/v1/dataset-versions/" + child["version_id"]
    )
    assert stored.status == 200
    assert (
        stored.json()["canonical_artifact"]["sha256"]
        == child["canonical_artifact"]["sha256"]
    )
    return {
        "child_version_id": child["version_id"],
        "active_version_id": second["version_id"],
        "parent_sha256": first["canonical_artifact"]["sha256"],
        "child_sha256": child["canonical_artifact"]["sha256"],
    }


def _schema_intake_race(page: Page, base_url: str, first: dict, second: dict) -> dict:
    path = f"/api/v1/dataset-versions/{first['version_id']}/schema"
    held = HeldWrite(page, path, "PATCH")
    page.route("**" + path, held.handle)
    page.locator(".schema-table tbody tr").first.locator("input").first.fill(
        "saved-with-new-intake-draft"
    )
    page.locator(".schema-actions button").last.click()
    held.wait()
    file_input = page.locator('.upload-panel input[type="file"]')
    file_input.set_input_files(
        {
            "name": "pending-intake.csv",
            "mimeType": "text/csv",
            "buffer": b"new\n12\n13\n",
        }
    )
    held.release()
    saved = page.request.get(
        base_url + "/api/v1/dataset-versions/" + first["version_id"]
    ).json()
    _expect_active(page, saved)
    page.locator(".dataset-technical-details summary").click()
    expect(page.locator("dd.hash-text", has_text=saved["schema_hash"])).to_be_visible()
    assert saved["schema_hash"] == held.payload["schema_hash"]
    assert saved["canonical_artifact"] == first["canonical_artifact"]
    assert file_input.evaluate("input => input.files[0]?.name") == "pending-intake.csv"
    expect(page.locator('.upload-panel button[type="submit"]')).to_be_enabled()
    _unchanged(page, base_url, second)
    return {
        "active_version_id": first["version_id"],
        "acknowledged_schema_hash": saved["schema_hash"],
        "preserved_intake_draft": "pending-intake.csv",
        "canonical_sha256": saved["canonical_artifact"]["sha256"],
    }


def _partial_read(page: Page, base_url: str, first: dict, locale: str) -> dict:
    pattern = f"**/api/v1/dataset-versions/{first['version_id']}/profile*"
    page.route(
        pattern,
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body=json.dumps(
                {
                    "error": {
                        "code": "synthetic_profile_unavailable",
                        "message": "Synthetic fixture",
                        "correlation_id": "synthetic",
                    }
                }
            ),
        ),
    )
    _open(page, base_url, first, locale)
    alert = page.locator('[data-dataset-request-error="profile"]')
    expect(alert).to_be_visible()
    expect(page.locator(".canonical-preview-grid tbody tr")).to_have_count(
        first["row_count"]
    )
    _expect_active(page, first)
    page.unroute(pattern)
    alert.locator("button").click()
    expect(alert).to_have_count(0)
    _expect_active(page, first)
    _unchanged(page, base_url, first)
    return {"profile_failure_kept_version": first["version_id"], "retry": "succeeded"}


def _cancel_file_replacement(
    page: Page, base_url: str, first: dict, second: dict
) -> dict:
    original = b"original\n17\n19\n"
    file_input = page.locator('.upload-panel input[type="file"]')
    file_input.set_input_files(
        {"name": "original-draft.csv", "mimeType": "text/csv", "buffer": original}
    )
    file_input.set_input_files(
        {
            "name": "rejected-draft.csv",
            "mimeType": "text/csv",
            "buffer": b"other\n100\n",
        }
    )
    assert file_input.evaluate("input => input.files[0]?.name") == "original-draft.csv"
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == "/api/v1/datasets"
    ) as received:
        page.locator('.upload-panel button[type="submit"]').click()
    assert received.value.status == 201
    uploaded = received.value.json()
    assert uploaded["original_filename"] == "original-draft.csv"
    assert uploaded["sha256"] == hashlib.sha256(original).hexdigest()
    _expect_active(page, first)
    _unchanged(page, base_url, first)
    _unchanged(page, base_url, second)
    return {
        "preserved_draft": uploaded["original_filename"],
        "upload_sha256": uploaded["sha256"],
    }


def _paste_clear_race(page: Page, base_url: str, first: dict, second: dict) -> dict:
    held = HeldWrite(page, "/api/v1/datasets/paste", "POST")
    page.route("**/api/v1/datasets/paste", held.handle)
    page.locator(".paste-panel .view-mode-control button").nth(1).click()
    text = "fresh\n11\n12\n"
    raw = page.locator(".paste-panel textarea")
    raw.fill(text)
    page.locator(".paste-actions .primary-button").click()
    held.wait()
    page.locator(".paste-panel .view-mode-control button").nth(1).click()
    raw.fill("")
    held.release()
    expect(raw).to_have_value("")
    expect(page.locator("#dataset-parsing")).to_have_count(0)
    _expect_active(page, first)
    _unchanged(page, base_url, first)
    _unchanged(page, base_url, second)
    assert held.payload["sha256"] == hashlib.sha256(text.encode()).hexdigest()
    versions = page.request.get(
        base_url + f"/api/v1/datasets/{held.payload['dataset_id']}/versions"
    )
    assert versions.status == 200
    return {
        "stored_upload_id": held.payload["dataset_id"],
        "cleared_draft_preserved": True,
    }


def _paste_replacement_race(
    page: Page, base_url: str, first: dict, second: dict
) -> dict:
    held = HeldWrite(page, "/api/v1/datasets/paste", "POST")
    page.route("**/api/v1/datasets/paste", held.handle)
    raw_mode = page.locator(".paste-panel .view-mode-control button").nth(1)
    raw_mode.click()
    raw = page.locator(".paste-panel textarea")
    raw.fill("old\n11\n12\n")
    submit = page.locator(".paste-actions .primary-button")
    submit.click()
    held.wait()
    raw_mode.click()
    replacement = "new-replacement\n1234\n5678\n"
    raw.fill(replacement)
    expect(submit).to_be_enabled()
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == "/api/v1/datasets/paste"
    ) as received:
        submit.click()
    assert received.value.status == 201
    newer = received.value.json()
    assert newer["sha256"] == hashlib.sha256(replacement.encode()).hexdigest()
    expect(page.locator("#dataset-parsing")).to_be_visible()
    held.release()
    expect(page.locator("#dataset-parsing .metadata-grid")).to_contain_text(
        f"{len(replacement.encode())} bytes"
    )
    _expect_active(page, first)
    path = f"/api/v1/datasets/{newer['dataset_id']}/confirm-parsing"
    parsing = page.locator("#dataset-parsing")
    parsing.locator("select").nth(0).select_option("utf-8")
    parsing.locator("select").nth(1).select_option(",")
    parsing.locator('input[type="checkbox"]').check()
    parsing.locator('input[type="number"]').fill("1")
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == path
    ) as confirmed:
        page.locator("#dataset-parsing button.primary-button").click()
    assert confirmed.value.status == 201
    _expect_active(page, confirmed.value.json())
    _unchanged(page, base_url, first)
    _unchanged(page, base_url, second)
    return {
        "old_upload_id": held.payload["dataset_id"],
        "confirmed_upload_id": newer["dataset_id"],
    }


def _cancel_dirty_switch(page: Page, base_url: str, first: dict, second: dict) -> dict:
    name = page.locator(".schema-table tbody tr").first.locator("input").first
    name.fill("unsaved-user-draft")
    page.locator("#active-dataset-version").select_option(second["version_id"])
    expect(page.locator("#active-dataset-version")).to_have_value(first["version_id"])
    expect(name).to_have_value("unsaved-user-draft")
    assert (
        page.evaluate("new URL(location.href).searchParams.get('dataset_version_id')")
        == first["version_id"]
    )
    assert (
        page.evaluate("sessionStorage.getItem('datalab.current_dataset_version_id')")
        == first["version_id"]
    )
    _unchanged(page, base_url, first)
    _unchanged(page, base_url, second)
    return {
        "cancelled_switch_preserved_draft": True,
        "active_version_id": first["version_id"],
    }


def verify_dataset_context(
    browser: Browser, base_url: str, root: Path, *, isolated_workspace: bool
) -> None:
    if not isolated_workspace:
        raise ValueError("Dataset race fixtures require an owned synthetic workspace")
    root.mkdir(parents=True, exist_ok=True)
    for locale in ("ko", "en"):
        for kind in (
            "schema",
            "cell",
            "schema-intake",
            "partial-read",
            "dirty-cancel",
            "file-cancel",
            "paste-clear",
            "paste-replacement",
        ):
            name = f"{kind}-{locale}"
            with diagnosed_page(browser, root, name, locale=locale) as page:
                page.on(
                    "dialog",
                    lambda dialog: dialog.dismiss()
                    if kind in ("dirty-cancel", "file-cancel")
                    else dialog.accept(),
                )
                first = _create_version(page, base_url, "race-A-" + name)
                second = _create_version(page, base_url, "race-B-" + name)
                if kind == "partial-read":
                    evidence = _partial_read(page, base_url, first, locale)
                else:
                    _open(page, base_url, first, locale)
                    scenario = {
                        "schema": _schema_race,
                        "cell": _cell_race,
                        "schema-intake": _schema_intake_race,
                        "dirty-cancel": _cancel_dirty_switch,
                        "file-cancel": _cancel_file_replacement,
                        "paste-clear": _paste_clear_race,
                        "paste-replacement": _paste_replacement_race,
                    }[kind]
                    evidence = scenario(page, base_url, first, second)
                evidence.update(
                    {"fixture": "synthetic", "locale": locale, "scenario": kind}
                )
                (root / name / "evidence.json").write_text(
                    json.dumps(evidence, indent=2), encoding="utf-8"
                )
                page.screenshot(path=str(root / name / "completed.png"), full_page=True)
