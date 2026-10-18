"""Two real browser editors exercise schema CAS without changing source files."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, expect

from app_readiness import diagnosed_page
from dataset_context import HeldWrite, _create_version, _expect_active, _open


def _schema_path(version: dict) -> str:
    return f"/api/v1/dataset-versions/{version['version_id']}/schema"


def _save(page: Page, version: dict, expected_status: int) -> dict:
    path = _schema_path(version)
    with page.expect_response(
        lambda response: response.request.method == "PATCH"
        and urlsplit(response.url).path == path
    ) as received:
        page.locator(".schema-actions button").last.click()
    response = received.value
    assert response.status == expected_status, response.text()
    request = response.request.post_data_json
    assert len(request["expected_schema_hash"]) == 64
    if expected_status == 409:
        assert response.json()["error"]["code"] == "dataset_schema_conflict"
    else:
        expect(page.locator(".schema-actions button").last).to_be_enabled()
    return {"request": request, "response": response.json()}


def _first_field(page: Page, index: int):
    return page.locator(".schema-table tbody tr").first.locator("input").nth(index)


def _conflict(page: Page):
    region = page.locator("[data-schema-conflict]")
    expect(region).to_have_attribute("data-conflict-state", "ready")
    return region


def _action(page: Page, action: str) -> None:
    page.locator(f'[data-schema-conflict-action="{action}"]').click()


def _frames(page: Page) -> None:
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )


def _analysis_export(page: Page, base_url: str, analysis_id: str) -> dict:
    response = page.request.post(
        base_url + f"/api/v1/analysis-runs/{analysis_id}/exports/json",
        headers={"Origin": base_url},
    )
    assert response.status == 201, response.text()
    return response.json()


def _analysis(page: Page, base_url: str, version: dict) -> dict:
    catalog = page.request.get(base_url + "/api/v1/analysis-methods").json()
    method = next(
        row for row in catalog["methods"] if row["method_id"] == "eda.descriptive"
    )
    response = page.request.post(
        base_url + "/api/v1/analysis-runs",
        headers={"Origin": base_url},
        data={
            "method_id": method["method_id"],
            "method_version": method["method_version"],
            "dataset_version_id": version["version_id"],
            "roles": {},
            "options": {
                "column_ids": [version["columns"][0]["column_id"]],
                "missing_policy": "available_case_by_column",
            },
        },
    )
    assert response.status == 201, response.text()
    return _analysis_export(page, base_url, response.json()["analysis_id"])


def _case(
    first: Page,
    second: Page,
    base_url: str,
    version: dict,
    other: dict,
    locale: str,
    kind: str,
) -> dict:
    initial_export = _analysis(first, base_url, version)
    _open(first, base_url, version, locale)
    _open(second, base_url, version, locale)
    paths = []
    second.on(
        "request",
        lambda request: paths.append(request.post_data_json)
        if request.method == "PATCH"
        and urlsplit(request.url).path == _schema_path(version)
        else None,
    )
    draft_name = 'local "name" \\ \ue000literal\ue001'
    # Existing schema label policy removes non-printable characters, not transport.
    saved_name = 'local "name" \\ literal'
    _first_field(second, 0).fill(draft_name)
    _first_field(first, 1).fill("mg")
    winner = _save(first, version, 200)
    first_hash = winner["response"]["schema_hash"]
    assert winner["request"]["expected_schema_hash"] == version["schema_hash"]
    assert first_hash != version["schema_hash"]

    held = None
    if kind == "late-latest":
        path = f"/api/v1/dataset-versions/{version['version_id']}"
        held = HeldWrite(second, path, "GET")
        second.route("**" + path, held.handle)
    loser = _save(second, version, 409)
    assert loser["request"]["expected_schema_hash"] == version["schema_hash"]
    expect(_first_field(second, 0)).to_have_value(draft_name)
    latest = first.request.get(base_url + _schema_path(version)).json()
    assert latest["schema_hash"] == first_hash
    assert latest["columns"][0]["display_name"] == version["columns"][0]["display_name"]
    assert latest["columns"][0]["unit"] == "mg"

    if held is not None:
        held.wait()
        second.locator("#active-dataset-version").select_option(other["version_id"])
        _expect_active(second, other)
        held.release()
        _expect_active(second, other)
        expect(second.locator("[data-schema-conflict]")).to_have_count(0)
        assert len(paths) == 1
    elif kind == "discard":
        _conflict(second)
        _action(second, "discard")
        expect(_first_field(second, 0)).to_have_value(
            version["columns"][0]["display_name"]
        )
        expect(_first_field(second, 1)).to_have_value("mg")
        expect(second.locator("[data-schema-conflict]")).to_have_count(0)
        _frames(second)
        assert len(paths) == 1, "Discard must not issue another PATCH"
    else:
        _conflict(second)
        _action(second, "edit")
        expect(_first_field(second, 0)).to_have_value(draft_name)
        _frames(second)
        assert len(paths) == 1, "Re-edit must not issue another PATCH"
        _save(second, version, 409)
        assert paths[-1]["expected_schema_hash"] == version["schema_hash"]
        _conflict(second)
        _action(second, "apply")
        expect(_first_field(second, 0)).to_have_value(draft_name)
        expect(_first_field(second, 1)).to_have_value("mg")
        _frames(second)
        assert len(paths) == 2, "Apply stages a draft; only Save sends it"

        # Another writer wins after the displayed comparison was accepted.
        _first_field(first, 1).fill("g")
        newer = _save(first, version, 200)
        second_hash = newer["response"]["schema_hash"]
        assert newer["request"]["expected_schema_hash"] == first_hash
        _save(second, version, 409)
        assert paths[-1]["expected_schema_hash"] == first_hash
        _conflict(second)
        expect(_first_field(second, 0)).to_have_value(draft_name)
        _action(second, "apply")
        expect(_first_field(second, 1)).to_have_value("g")
        _frames(second)
        assert len(paths) == 3
        final = _save(second, version, 200)
        assert final["request"]["expected_schema_hash"] == second_hash
        assert final["request"]["columns"][0]["display_name"] == draft_name, final
        assert final["response"]["columns"][0]["display_name"] == saved_name, final
        assert final["response"]["columns"][0]["unit"] == "g", final
        expect(second.locator("[data-schema-conflict]")).to_have_count(0)
        second.set_viewport_size({"width": 390, "height": 844})
        second.locator(".language-switcher button").nth(
            1 if locale == "ko" else 0
        ).click()
        expect(_first_field(second, 0)).to_have_value(saved_name)
        _frames(second)
        assert len(paths) == 4

    current = first.request.get(
        base_url + "/api/v1/dataset-versions/" + version["version_id"]
    ).json()
    assert current["canonical_artifact"] == version["canonical_artifact"]
    assert current["source_sha256"] == version["source_sha256"]
    final_export = _analysis_export(first, base_url, initial_export["analysis_id"])
    assert (
        final_export["source_result_sha256"] == initial_export["source_result_sha256"]
    )
    assert final_export["result"]["result"] == initial_export["result"]["result"]
    assert final_export["stale"] is True
    return {
        "fixture": "synthetic",
        "scenario": kind,
        "locale": locale,
        "version_id": version["version_id"],
        "initial_schema_hash": version["schema_hash"],
        "final_schema_hash": current["schema_hash"],
        "canonical_sha256": current["canonical_artifact"]["sha256"],
        "source_result_sha256": final_export["source_result_sha256"],
        "second_tab_requests": paths,
    }


def verify_schema_concurrency(
    browser: Browser, base_url: str, root: Path, *, isolated_workspace: bool
) -> None:
    if not isolated_workspace:
        raise ValueError("Schema concurrency requires an owned synthetic workspace")
    for locale in ("ko", "en"):
        for kind in ("apply", "discard", "late-latest"):
            name = f"{kind}-{locale}"
            with (
                diagnosed_page(browser, root, name + "-first", locale=locale) as first,
                diagnosed_page(
                    browser, root, name + "-second", locale=locale
                ) as second,
            ):
                first.on("dialog", lambda dialog: dialog.accept())
                second.on("dialog", lambda dialog: dialog.accept())
                version = _create_version(first, base_url, "schema-CAS-" + name)
                other = _create_version(first, base_url, "schema-other-" + name)
                evidence = _case(first, second, base_url, version, other, locale, kind)
                (root / (name + "-second") / "evidence.json").write_text(
                    json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                for suffix, page in (("first", first), ("second", second)):
                    page.screenshot(
                        path=str(root / (name + "-" + suffix) / "completed.png"),
                        full_page=True,
                    )
