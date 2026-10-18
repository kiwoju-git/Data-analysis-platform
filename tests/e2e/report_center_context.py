"""Synthetic, mocked transport checks against the real Report Center and hooks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Browser, Route, expect, sync_playwright

from app_readiness import diagnosed_page

ANALYSIS_A = "10000000-0000-4000-8000-000000000001"
ANALYSIS_B = "10000000-0000-4000-8000-000000000002"
DATASET = "20000000-0000-4000-8000-000000000001"


def _status(analysis_id: str) -> dict[str, object]:
    return {
        "analysis_id": analysis_id,
        "dataset_version_id": DATASET,
        "method_id": "eda.descriptive",
        "method_version": "0.1.0",
        "status": "succeeded",
        "config_schema_version": 1,
        "stale": analysis_id == ANALYSIS_A,
        "result_available": True,
        "artifact_count": 1,
        "created_at": "2026-10-18T00:00:00Z",
        "updated_at": "2026-10-18T00:00:00Z",
        "completed_at": "2026-10-18T00:00:00Z",
    }


def _result(analysis_id: str) -> dict[str, object]:
    return {
        **_status(analysis_id),
        "warnings": [],
        "provenance": {},
        "result": {"summary_type": "descriptive_statistics", "columns": []},
    }


def _capability(
    analysis_id: str, locale: str, level: str = "full", source_hash: str = "a"
) -> dict[str, object]:
    return {
        "capability_schema_version": 1,
        "analysis_id": analysis_id,
        "method_id": "eda.descriptive",
        "summary_type": "descriptive_statistics",
        "result_schema_version": 1,
        "source_result_sha256": source_hash * 64,
        "stale": analysis_id == ANALYSIS_A,
        "locale": locale,
        "renderer_id": "descriptive",
        "renderer_version": "1",
        "variant_id": "default",
        "report_level": level,
        "html_available": level != "unsupported",
        "reason": "partial_stored_payload" if level == "summary" else None,
        "source_validation": "stored_dependencies_only",
        "sections": [
            {
                "section_id": "summary",
                "title": "Stored <column> \ue000",
                "status": "rendered",
                "reason": None,
            },
            {
                "section_id": "plot",
                "title": "Plot",
                "status": "missing" if level == "summary" else "not_applicable",
                "reason": "stored_plot_unavailable",
            },
        ],
    }


def verify_report_center_context(browser: Browser, base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    evidence: list[dict[str, object]] = []
    for locale in ("ko", "en"):
        requests: list[tuple[str, str]] = []
        modes: dict[str, str] = {}
        held: list[tuple[Route, dict[str, object]]] = []
        state = {"hold_list": False, "hold_delete": False, "status_failure": False}

        def serve(route: Route) -> None:
            parsed = urlparse(route.request.url)
            path = parsed.path
            requests.append((route.request.method, path))
            root = "/api/v1/analysis-runs"
            if path == root:
                query = parse_qs(parsed.query)
                runs = [_status(ANALYSIS_A), _status(ANALYSIS_B)]
                if query.get("stale") == ["false"]:
                    runs = [runs[1]]
                payload = {
                    "dataset_version_id": query.get("dataset_version_id", [None])[0],
                    "method_id": None,
                    "status": query.get("status", [None])[0],
                    "stale": None,
                    "result_available": True,
                    "offset": int(query.get("offset", ["0"])[0]),
                    "limit": 20,
                    "returned_count": len(runs),
                    "has_more": False,
                    "runs": runs,
                }
                if state["hold_list"]:
                    payload["runs"] = []
                    payload["returned_count"] = 0
                    held.append((route, payload))
                else:
                    route.fulfill(json=payload)
                return
            suffix = path.removeprefix(root + "/").split("/")
            analysis_id = suffix[0]
            if suffix[1:] == ["report-capability"]:
                route.fulfill(
                    json=_capability(analysis_id, parse_qs(parsed.query)["locale"][0])
                )
            elif len(suffix) == 2 and suffix[1] == "result":
                mode = modes.get(analysis_id)
                if mode == "hold":
                    held.append((route, _result(analysis_id)))
                elif mode in ("404", "503"):
                    route.fulfill(
                        status=int(mode),
                        json={
                            "error": {
                                "code": "analysis_run_not_found"
                                if mode == "404"
                                else "analysis_result_fetch_failed"
                            }
                        },
                    )
                elif mode == "wrong":
                    route.fulfill(
                        json=_result(
                            ANALYSIS_B if analysis_id == ANALYSIS_A else ANALYSIS_A
                        )
                    )
                else:
                    route.fulfill(json=_result(analysis_id))
            elif len(suffix) == 1 and route.request.method == "GET":
                if state["status_failure"]:
                    route.fulfill(
                        status=503,
                        json={"error": {"code": "analysis_status_fetch_failed"}},
                    )
                else:
                    route.fulfill(json=_status(analysis_id))
            elif suffix[1:] == ["deletion"] and route.request.method == "DELETE":
                payload = {"analysis_id": analysis_id, "cleanup_status": "deleted"}
                if state["hold_delete"]:
                    held.append((route, payload))
                else:
                    route.fulfill(json=payload)
            elif suffix[1:] == ["deletion-preflight"]:
                route.fulfill(
                    json={
                        **_status(analysis_id),
                        "deletion_ready": True,
                        "blockers": [],
                        "counts": {
                            "total_file_count": 1,
                            "file_bytes": 128,
                            "metadata_record_count": 1,
                        },
                        "deletion_manifest_sha256": "d" * 64,
                    }
                )
            elif suffix[1:] == ["exports"]:
                route.fulfill(json={"analysis_id": analysis_id, "exports": []})
            elif suffix[1:] == ["exports", "json"]:
                route.fulfill(
                    json={
                        "schema_version": 1,
                        "analysis_id": analysis_id,
                        "export_id": "synthetic-export-preserved",
                        "sha256": "e" * 64,
                        "size_bytes": 128,
                        "stale": True,
                        "result": _result(analysis_id),
                    }
                )
            else:
                route.fulfill(
                    status=404, json={"error": {"code": "fixture_route_unexpected"}}
                )

        def release() -> None:
            pending = list(held)
            held.clear()
            assert pending, "Expected a deliberately held transport response"
            for route, payload in pending:
                route.fulfill(json=payload)

        with diagnosed_page(
            browser, output, f"reports-{locale}", locale=locale
        ) as page:
            page.route("**/api/v1/analysis-runs**", serve)
            page.goto(
                f"{base_url}/tests/report-center.html?tab=reports&keep=source&analysis_id={ANALYSIS_A}#saved",
                wait_until="domcontentloaded",
            )
            panel = page.locator(".report-selected-result")
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_A)
            expect(panel).to_have_attribute("data-report-status", "stale")
            expect(panel.locator('[data-report-capability="full"]')).to_be_visible()
            assert (
                requests.count(("GET", f"/api/v1/analysis-runs/{ANALYSIS_A}/result"))
                >= 2
            ), "StrictMode cold mount must replay effects"
            page.evaluate(
                "history.replaceState({test: 'preserved'}, '', location.href)"
            )
            panel.evaluate("node => { window.reportPanel = node; }")
            panel.locator(".export-format-card").filter(
                has=page.locator("strong", has_text="JSON")
            ).get_by_role("button").click()
            expect(panel.locator(".export-status-box code")).to_have_attribute(
                "title", "e" * 64
            )
            baseline = list(requests)
            page.locator(".report-filter-grid select").nth(1).select_option("fresh")
            expect(page.locator(".report-run-row")).to_have_count(1)
            assert panel.evaluate("node => node === window.reportPanel")
            expect(panel.locator(".export-status-box code")).to_have_attribute(
                "title", "e" * 64
            )
            expect(panel).to_have_attribute("data-report-status", "stale")
            assert requests[len(baseline) :] == [
                ("GET", "/api/v1/analysis-runs")
            ], "Filters must not refetch result/status/exports"

            current_only = page.locator(".report-dataset-filter input")
            current_only.check()
            expect(page.locator(".report-run-row")).to_have_count(1)
            baseline = list(requests)
            page.get_by_role("button", name="Clear fixture dataset").click()
            expect(
                page.locator(
                    '[data-report-feedback="report_center_current_dataset_required"]'
                )
            ).to_be_visible()
            expect(current_only).to_be_checked()
            expect(current_only).to_be_enabled()
            expect(page.locator(".report-run-row")).to_have_count(0)
            assert requests == baseline
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_A)
            for width, height in [(1440, 900), (1280, 800), (1024, 768), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                assert panel.evaluate("node => node === window.reportPanel")
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                )
                page.screenshot(
                    path=str(output / f"reports-{locale}-{width}.png"), full_page=True
                )
            other_locale = "en" if locale == "ko" else "ko"
            page.get_by_role(
                "button", name="ENG" if other_locale == "en" else "KOR", exact=True
            ).click()
            expect(page.locator("html")).to_have_attribute(
                "data-app-locale", other_locale
            )
            expect(
                page.locator(
                    '[data-report-feedback="report_center_current_dataset_required"]'
                )
            ).to_contain_text(
                "explicitly view all" if other_locale == "en" else "명시적으로 선택"
            )
            expect(panel.locator('[data-report-capability="full"]')).to_be_visible()
            assert requests[len(baseline) :] == [
                ("GET", f"/api/v1/analysis-runs/{ANALYSIS_A}/report-capability")
            ], "Locale changes refresh coverage only"
            page.get_by_role(
                "button", name="KOR" if locale == "ko" else "ENG", exact=True
            ).click()
            expect(panel.locator('[data-report-capability="full"]')).to_be_visible()
            current_only.uncheck()
            page.locator(".report-filter-grid select").nth(1).select_option("all")
            expect(page.locator(".report-run-row")).to_have_count(2)

            modes[ANALYSIS_B] = "hold"
            page.locator(f'.report-run-row[data-analysis-id="{ANALYSIS_B}"]').click()
            expect(page.locator(".report-direct-selection")).to_have_attribute(
                "data-report-selection", ANALYSIS_B
            )
            assert parse_qs(urlparse(page.url).query)["analysis_id"] == [ANALYSIS_B]
            page.locator(".report-filter-grid select").nth(1).select_option("fresh")
            expect(page.locator(".report-run-row")).to_have_count(1)
            modes.pop(ANALYSIS_B)
            release()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)
            assert page.evaluate("history.state.test") == "preserved"
            assert parse_qs(urlparse(page.url).query)["keep"] == ["source"]
            assert urlparse(page.url).fragment == "saved"

            page.locator(".report-filter-grid select").nth(1).select_option("all")
            expect(page.locator(".report-run-row")).to_have_count(2)
            modes[ANALYSIS_A] = "hold"
            page.locator(f'.report-run-row[data-analysis-id="{ANALYSIS_A}"]').click()
            page.locator(f'.report-run-row[data-analysis-id="{ANALYSIS_B}"]').click()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)
            modes.pop(ANALYSIS_A)
            release()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)

            state["hold_list"] = True
            with page.expect_request(lambda request: "status=failed" in request.url):
                page.locator(".report-filter-grid select").nth(2).select_option(
                    "failed"
                )
            state["hold_list"] = False
            page.locator(".report-filter-grid select").nth(2).select_option("succeeded")
            expect(page.locator(".report-run-row")).to_have_count(2)
            release()
            expect(page.locator(".report-run-row")).to_have_count(2)
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)

            modes[ANALYSIS_B] = "503"
            page.locator(f'.report-run-row[data-analysis-id="{ANALYSIS_B}"]').click()
            error = page.locator(
                '[data-report-feedback="analysis_result_fetch_failed"]'
            )
            expect(error).to_be_visible()
            assert parse_qs(urlparse(page.url).query)["analysis_id"] == [ANALYSIS_B]
            modes.pop(ANALYSIS_B)
            error.get_by_role("button").click()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)

            state["status_failure"] = True
            page.locator(f'.report-run-row[data-analysis-id="{ANALYSIS_A}"]').click()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_A)
            expect(panel).to_have_attribute("data-report-status", "unknown")
            status_error = page.locator(
                '[data-report-feedback="analysis_status_fetch_failed"]'
            )
            expect(status_error).to_be_visible()
            before_retry = requests.count(
                ("GET", f"/api/v1/analysis-runs/{ANALYSIS_A}/result")
            )
            state["status_failure"] = False
            status_error.get_by_role("button").click()
            expect(panel).to_have_attribute("data-report-status", "stale")
            assert (
                requests.count(("GET", f"/api/v1/analysis-runs/{ANALYSIS_A}/result"))
                == before_retry
            )

            state["hold_delete"] = True
            panel.locator(".report-analysis-deletion > button").click()
            confirmation = panel.locator(".report-analysis-deletion .error-box")
            expect(confirmation).to_be_visible()
            confirmation.get_by_role("button").first.click()
            page.locator(f'.report-run-row[data-analysis-id="{ANALYSIS_B}"]').click()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)
            release()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)
            assert parse_qs(urlparse(page.url).query)["analysis_id"] == [ANALYSIS_B]

            before_invalid = len(requests)
            page.evaluate(
                """id => {
                const url = new URL(location.href);
                url.searchParams.append('analysis_id', id);
                history.pushState(history.state, '', url);
                dispatchEvent(new PopStateEvent('popstate'));
            }""",
                ANALYSIS_A,
            )
            expect(
                page.locator(
                    '[data-report-feedback="report_center_analysis_id_invalid"]'
                )
            ).to_be_visible()
            expect(panel).to_have_count(0)
            assert len(requests) == before_invalid
            page.evaluate(
                """id => {
                const url = new URL(location.href); url.searchParams.set('analysis_id', id);
                history.replaceState(history.state, '', url);
                dispatchEvent(new Event('datalab:location-change'));
            }""",
                ANALYSIS_A,
            )
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_A)
            modes[ANALYSIS_B] = "hold"
            with page.expect_request(
                lambda request: request.url.endswith(f"/{ANALYSIS_B}/result")
            ):
                page.locator(
                    f'.report-run-row[data-analysis-id="{ANALYSIS_B}"]'
                ).click()
            page.get_by_role("button", name="Toggle fixture view").click()
            expect(page.locator(".report-center-page")).to_have_count(0)
            modes.pop(ANALYSIS_B)
            release()
            expect(panel).to_have_count(0)
            assert parse_qs(urlparse(page.url).query)["analysis_id"] == [ANALYSIS_B]
            page.get_by_role("button", name="Toggle fixture view").click()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)
            modes[ANALYSIS_B] = "404"
            page.locator(f'.report-run-row[data-analysis-id="{ANALYSIS_B}"]').click()
            expect(
                page.locator('[data-report-feedback="report_center_result_removed"]')
            ).to_be_visible()
            expect(panel).to_have_count(0)
            assert "analysis_id" not in parse_qs(urlparse(page.url).query)
            assert parse_qs(urlparse(page.url).query)["keep"] == ["source"]
            evidence.append(
                {
                    "locale": locale,
                    "strict_mode": True,
                    "requests": requests,
                    "viewports": [1440, 1280, 1024, 390],
                }
            )
    (output / "report-center-evidence.json").write_text(
        json.dumps(
            {
                "fixture": "synthetic mocked transport; real React hooks/UI",
                "cases": evidence,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    verify_report_capability_context(browser, base_url, output / "capability")


def verify_report_capability_context(
    browser: Browser, base_url: str, output: Path
) -> None:
    """Capability is server-owned and HTML creation uses its exact source hash."""
    output.mkdir(parents=True, exist_ok=True)
    evidence = []
    for locale in ("ko", "en"):
        state = {
            "level": "summary",
            "hash": "a",
            "hold_locale": None,
            "hold_html": False,
            "conflict": False,
        }
        held: list[tuple[Route, dict[str, object]]] = []
        posts: list[dict[str, object]] = []
        requests: list[str] = []

        def serve(route: Route) -> None:
            parsed = urlparse(route.request.url)
            path = parsed.path
            requests.append(path)
            root = "/api/v1/analysis-runs"
            if path == root:
                route.fulfill(
                    json={
                        "runs": [_status(ANALYSIS_A), _status(ANALYSIS_B)],
                        "offset": 0,
                        "limit": 20,
                        "has_more": False,
                        "returned_count": 2,
                    }
                )
                return
            suffix = path.removeprefix(root + "/").split("/")
            owner = suffix[0]
            if suffix[1:] == ["result"]:
                route.fulfill(json=_result(owner))
            elif len(suffix) == 1:
                route.fulfill(json=_status(owner))
            elif suffix[1:] == ["exports"]:
                route.fulfill(json={"analysis_id": owner, "exports": []})
            elif suffix[1:] == ["report-capability"]:
                language = parse_qs(parsed.query)["locale"][0]
                payload = _capability(
                    owner, language, str(state["level"]), str(state["hash"])
                )
                if state["hold_locale"] == language:
                    held.append((route, payload))
                else:
                    route.fulfill(json=payload)
            elif suffix[1:] == ["exports", "html"]:
                body = route.request.post_data_json
                posts.append({"analysis_id": owner, **body})
                assert body == {
                    "locale": locale,
                    "expected_source_result_sha256": state["hash"] * 64,
                }
                if state["conflict"]:
                    state["hash"] = "b"
                    state["conflict"] = False
                    route.fulfill(
                        status=409,
                        json={"error": {"code": "analysis_report_source_changed"}},
                    )
                    return
                payload = {
                    "schema_version": 4,
                    "analysis_id": owner,
                    "export_id": "synthetic-html",
                    "format": "analysis_result_html_report",
                    "artifact_kind": "analysis_result_html_report",
                    "media_type": "text/html",
                    "sha256": "e" * 64,
                    "source_result_sha256": state["hash"] * 64,
                    "size_bytes": 128,
                    "stale": True,
                    "report_locale": locale,
                    "title": "Synthetic report",
                    "section_count": 1,
                    "report_level": state["level"],
                    "renderer_version": "1",
                    "rendered_section_ids": ["summary"],
                    "created_at": "2026-10-18T00:00:00Z",
                }
                if state["hold_html"]:
                    held.append((route, payload))
                else:
                    route.fulfill(status=201, json=payload)
            elif suffix[1:] == ["exports", "synthetic-html", "download"]:
                route.fulfill(
                    body="<!doctype html><title>Synthetic report</title><p>Stored report</p>",
                    content_type="text/html; charset=utf-8",
                    headers={
                        "Content-Disposition": "attachment; filename=fallback.html; filename*=UTF-8''%EB%B3%B4%EA%B3%A0%EC%84%9C.html"
                    },
                )
            else:
                route.fulfill(
                    status=404, json={"error": {"code": "fixture_route_unexpected"}}
                )

        def release() -> None:
            assert held
            pending = list(held)
            held.clear()
            for route, payload in pending:
                route.fulfill(json=payload)

        with diagnosed_page(
            browser, output, f"report-capability-{locale}", locale=locale
        ) as page:
            page.route("**/api/v1/analysis-runs**", serve)
            page.goto(
                f"{base_url}/tests/report-center.html?analysis_id={ANALYSIS_A}",
                wait_until="domcontentloaded",
            )
            panel = page.locator(".report-selected-result")
            coverage = panel.locator("[data-report-capability]")
            expect(coverage).to_have_attribute("data-report-capability", "summary")
            coverage.locator("summary").click()
            expect(coverage).to_contain_text("stored_plot_unavailable")
            expect(coverage).to_contain_text("Stored <column> \ue000")
            html_button = (
                panel.locator(".export-format-card")
                .filter(has=page.locator("strong", has_text="HTML"))
                .get_by_role("button")
            )
            expect(html_button).to_be_enabled()
            baseline = len(requests)
            with page.expect_request(lambda request: "status=failed" in request.url):
                page.locator(".report-filter-grid select").nth(2).select_option(
                    "failed"
                )
            expect(page.locator(".report-run-row")).to_have_count(2)
            assert requests[baseline:] == ["/api/v1/analysis-runs"], requests[baseline:]
            for width, height in [(1440, 900), (1280, 800), (1024, 768), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                )
                page.screenshot(
                    path=str(output / f"capability-{locale}-{width}.png"),
                    full_page=True,
                )
            other = "en" if locale == "ko" else "ko"
            state["hold_locale"] = other
            with page.expect_request(
                lambda request: "report-capability" in request.url
                and f"locale={other}" in request.url
            ):
                page.get_by_role(
                    "button", name="ENG" if other == "en" else "KOR", exact=True
                ).click()
            expect(coverage).to_have_attribute("data-report-capability", "loading")
            expect(html_button).to_have_count(0)
            page.get_by_role(
                "button", name="ENG" if locale == "en" else "KOR", exact=True
            ).click()
            expect(coverage).to_have_attribute("data-report-capability", "summary")
            state["hold_locale"] = None
            release()
            expect(coverage).to_have_attribute("data-report-capability", "summary")
            expect(html_button).to_be_enabled()
            state["hold_html"] = True
            with page.expect_request(lambda request: request.method == "POST"):
                html_button.click()
            state["level"] = "unsupported"
            page.locator(f'.report-run-row[data-analysis-id="{ANALYSIS_B}"]').click()
            expect(panel).to_have_attribute("data-analysis-id", ANALYSIS_B)
            expect(coverage).to_have_attribute("data-report-capability", "unsupported")
            state["hold_html"] = False
            release()
            expect(panel.locator(".export-status-box")).to_have_count(0)
            expect(html_button).to_have_count(0)
            expect(
                panel.locator(".export-format-card")
                .filter(has=page.locator("strong", has_text="JSON"))
                .get_by_role("button")
            ).to_be_enabled()
            state["level"] = "full"
            page.get_by_role("button", name="Refresh fixture workspace").click()
            expect(coverage).to_have_attribute("data-report-capability", "full")
            state["conflict"] = True
            html_button.click()
            expect(coverage).to_contain_text("b" * 64)
            expect(panel).to_contain_text("analysis_report_source_changed")
            assert (
                len(posts) == 2
            ), "A source conflict must not automatically recreate HTML"
            html_button.click()
            expect(panel.locator(".export-status-box")).to_have_count(1)
            with page.expect_download() as download_event:
                panel.locator(".export-status-box").get_by_role("button").click()
            download = download_event.value
            assert download.suggested_filename == "보고서.html"
            download.save_as(output / f"download-{locale}.html")
            evidence.append(
                {
                    "locale": locale,
                    "posts": posts,
                    "filename": download.suggested_filename,
                    "viewports": [1440, 1280, 1024, 390],
                }
            )
    (output / "report-capability-evidence.json").write_text(
        json.dumps(
            {
                "fixture": "synthetic mocked transport; real React UI, guard and downloads",
                "cases": evidence,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            verify_report_center_context(
                browser, args.base_url.rstrip("/"), args.output
            )
        finally:
            browser.close()
    print("Report Center context browser checks passed (KO/EN)")


if __name__ == "__main__":
    main()
