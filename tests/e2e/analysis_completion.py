"""Real analysis publication with held transport responses and current-input guards."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import APIResponse, Browser, Page, Route, expect

from app_readiness import diagnosed_page, wait_for_app_ready


PCA_ROUTE = "/analysis/exploration/eda.principal_components"


def _version(page: Page, base_url: str, name: str) -> dict:
    values = ["x,y"] + [f"{i},{i * i + i % 3}" for i in range(1, 13)]
    uploaded = page.request.post(
        base_url + "/api/v1/datasets",
        headers={"Origin": base_url},
        multipart={
            "file": {
                "name": name + ".csv",
                "mimeType": "text/csv",
                "buffer": ("\n".join(values) + "\n").encode(),
            }
        },
    )
    assert uploaded.status == 201, uploaded.text()
    confirmed = page.request.post(
        base_url + f"/api/v1/datasets/{uploaded.json()['dataset_id']}/confirm-parsing",
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
    assert confirmed.status == 201, confirmed.text()
    return confirmed.json()


def _open(page: Page, base_url: str, version: dict, locale: str) -> None:
    page.goto(
        base_url + PCA_ROUTE + "?dataset_version_id=" + version["version_id"],
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, locale, PCA_ROUTE)
    expect(page.locator("#active-dataset-version")).to_have_value(version["version_id"])
    panel = page.locator(".pca-panel")
    expect(panel.locator(".numeric-column-picker input")).to_have_count(2)
    for checkbox in panel.locator(".numeric-column-picker input").all():
        checkbox.check()
    expect(panel.locator(".primary-button")).to_be_enabled()


def _frames(page: Page) -> None:
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )


class HeldAnalysis:
    """The analysis genuinely commits on the server; only delivery is delayed."""

    def __init__(self, page: Page):
        self.page = page
        self.route: Route | None = None
        self.response: APIResponse | None = None
        self.payload: dict | None = None
        self.request: dict | None = None

    def handle(self, route: Route) -> None:
        if route.request.method != "POST" or self.route is not None:
            route.continue_()
            return
        self.route = route
        self.request = route.request.post_data_json
        self.response = route.fetch()
        assert self.response.status == 201, self.response.text()
        self.payload = self.response.json()
        self.page.evaluate("window.__heldCurrentAnalysis = true")

    def wait(self) -> None:
        self.page.wait_for_function("window.__heldCurrentAnalysis === true")
        assert self.payload is not None

    def release(self) -> None:
        assert self.route is not None and self.response is not None
        with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and urlsplit(response.url).path == "/api/v1/analysis-runs"
        ):
            self.route.fulfill(response=self.response)
        _frames(self.page)


def _case(
    page: Page, base_url: str, version: dict, other: dict, locale: str, kind: str
) -> dict:
    calls: list[dict] = []

    def record(request) -> None:
        path = urlsplit(request.url).path
        if path == "/api/v1/analysis-runs" and request.method == "POST":
            calls.append({"method": "POST", "path": path})
        elif (
            re.fullmatch(r"/api/v1/analysis-runs/[0-9a-f-]{36}", path)
            and request.method == "GET"
        ):
            calls.append({"method": "GET", "path": path})

    page.on("request", record)
    held = HeldAnalysis(page)
    page.route("**/api/v1/analysis-runs", held.handle)
    panel = page.locator(".pca-panel")
    panel.locator(".primary-button").click()
    held.wait()
    assert held.payload is not None
    analysis_id = held.payload["analysis_id"]
    status_path = f"/api/v1/analysis-runs/{analysis_id}"
    expect(page.locator(".pca-results")).to_have_count(0)
    if kind in ("configuration", "configuration-aba"):
        page.locator("#pca-matrix-type").select_option("covariance")
        if kind == "configuration-aba":
            page.locator("#pca-matrix-type").select_option("correlation")
        held.release()
        expect(page.locator(".pca-results")).to_have_count(0)
        expect(panel.locator(".primary-button")).to_be_enabled()
        assert not any(call["path"] == status_path for call in calls)
    elif kind == "filter":
        controls = page.locator(".filter-panel")
        controls.get_by_role(
            "button",
            name="조건 추가" if locale == "ko" else "Add condition",
            exact=True,
        ).click()
        row = controls.locator(".filter-row").last
        row.locator("select").first.select_option(version["columns"][0]["column_id"])
        row.locator("select").nth(1).select_option("gt")
        row.locator("input").fill("3")
        held.release()
        expect(page.locator(".pca-results")).to_have_count(0)
        expect(panel.locator(".primary-button")).to_be_enabled()
        assert not any(call["path"] == status_path for call in calls)
    elif kind == "disconnected-post":
        # The server committed the request. A lost response is not permission to
        # replay its POST or delete its successful artifact.
        assert held.route is not None
        held.route.abort("connectionreset")
        expect(panel.locator(".primary-button")).to_be_enabled()
        expect(page.locator(".pca-results")).to_have_count(0)
        expect(page.get_by_role("alert").first).to_be_visible()
        _frames(page)
    elif kind == "dataset-aba":
        page.locator("#active-dataset-version").select_option(other["version_id"])
        expect(page.locator("#active-dataset-version")).to_have_value(
            other["version_id"]
        )
        page.wait_for_function(
            "id => sessionStorage.getItem('datalab.current_dataset_version_id') === id",
            arg=other["version_id"],
        )
        page.locator("#active-dataset-version").select_option(version["version_id"])
        page.wait_for_function(
            "id => sessionStorage.getItem('datalab.current_dataset_version_id') === id",
            arg=version["version_id"],
        )
        held.release()
        expect(page.locator(".pca-results")).to_have_count(0)
        assert not any(call["path"] == status_path for call in calls)
    elif kind == "cross-tab-schema":
        columns = [
            {
                key: column[key]
                for key in (
                    "column_id",
                    "display_name",
                    "measurement_level",
                    "role",
                    "unit",
                )
            }
            for column in version["columns"]
        ]
        columns[0]["unit"] = "synthetic-unit"
        changed = page.request.patch(
            base_url + f"/api/v1/dataset-versions/{version['version_id']}/schema",
            headers={"Origin": base_url},
            data={"expected_schema_hash": version["schema_hash"], "columns": columns},
        )
        assert changed.status == 200, changed.text()
        assert changed.json()["schema_hash"] != version["schema_hash"]
        held.release()
        expect(page.get_by_role("alert")).to_contain_text(
            "analysis_completion_source_changed"
        )
        expect(page.locator(".pca-results")).to_have_count(0)
        assert page.request.get(base_url + status_path).json()["stale"] is True
    elif kind == "verification-retry":
        failures = []

        def unavailable(route: Route) -> None:
            failures.append(route.request.url)
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps(
                    {
                        "error": {
                            "code": "service_unavailable",
                            "message": "Synthetic verification outage",
                            "correlation_id": "synthetic-verification",
                        }
                    }
                ),
            )

        page.route("**" + status_path, unavailable)
        held.release()
        expect(page.get_by_role("alert")).to_contain_text(
            "analysis_completion_verification_failed"
        )
        expect(page.locator(".pca-results")).to_have_count(0)
        page.unroute("**" + status_path, unavailable)
        page.get_by_role(
            "button",
            name="저장 완료 상태 다시 확인"
            if locale == "ko"
            else "Verify saved completion again",
            exact=True,
        ).click()
        expect(page.locator(".pca-results")).to_be_visible()
        assert len(failures) == 1
        assert sum(call["path"] == status_path for call in calls) == 2
    else:
        held.release()
        expect(page.locator(".pca-results")).to_be_visible()
        if kind == "failed-activation":
            path = f"/api/v1/dataset-versions/{other['version_id']}"
            page.route(
                "**" + path,
                lambda route: route.fulfill(
                    status=503,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "error": {
                                "code": "service_unavailable",
                                "message": "Synthetic activation outage",
                            }
                        }
                    ),
                ),
            )
            with page.expect_response(
                lambda response: urlsplit(response.url).path == path
                and response.status == 503
            ):
                page.locator("#active-dataset-version").select_option(
                    other["version_id"]
                )
            error = page.locator('[data-dataset-request-error="activation"]')
            expect(error).to_contain_text("service_unavailable")
            expect(error.locator("button")).to_be_enabled()
            expect(page.locator("#active-dataset-version")).to_be_enabled()
            expect(page.locator("#active-dataset-version")).to_have_value(
                version["version_id"]
            )
            expect(page.locator(".pca-results")).to_be_visible()
        elif kind == "display-only":
            next_locale = "en" if locale == "ko" else "ko"
            page.locator(".language-switcher button").filter(
                has_text="ENG" if next_locale == "en" else "KOR"
            ).click()
            expect(page.locator("html")).to_have_attribute("lang", next_locale)
            for width, height in ((1280, 800), (1024, 768), (390, 844), (1440, 900)):
                page.set_viewport_size({"width": width, "height": height})
                expect(page.locator(".pca-results")).to_be_visible()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 1"
                )
            expect(page.locator("#pca-matrix-type")).to_have_value("correlation")
        else:
            raise AssertionError(kind)
    stored = page.request.get(base_url + f"/api/v1/analysis-runs/{analysis_id}/result")
    assert stored.status == 200
    assert stored.json() == held.payload
    assert sum(call["method"] == "POST" for call in calls) == 1
    assert held.payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    return {
        "scenario": kind,
        "request": held.request,
        "saved_analysis_id": analysis_id,
        "saved_schema_hash": held.payload["provenance"]["source_schema_hash"],
        "calls": calls,
        "original_result_unchanged": True,
    }


def verify_analysis_completion(
    browser: Browser, base_url: str, root: Path, *, isolated_workspace: bool
) -> None:
    if not isolated_workspace:
        raise ValueError(
            "Analysis completion checks require an owned synthetic workspace"
        )
    root.mkdir(parents=True, exist_ok=True)
    for locale in ("ko", "en"):
        for kind in (
            "configuration",
            "configuration-aba",
            "filter",
            "disconnected-post",
            "dataset-aba",
            "cross-tab-schema",
            "verification-retry",
            "failed-activation",
            "display-only",
        ):
            name = f"{kind}-{locale}"
            with diagnosed_page(browser, root, name, locale=locale) as page:
                version = _version(page, base_url, "synthetic-completion-" + name)
                other = _version(page, base_url, "synthetic-other-" + name)
                _open(page, base_url, version, locale)
                evidence = _case(page, base_url, version, other, locale, kind)
                (root / name / "evidence.json").write_text(
                    json.dumps(evidence, indent=2), encoding="utf-8"
                )
                page.screenshot(path=str(root / name / "completed.png"), full_page=True)
