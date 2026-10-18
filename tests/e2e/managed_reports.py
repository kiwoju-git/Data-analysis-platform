"""Real React/Chromium managed-report ownership checks with synthetic mocked HTTP."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from playwright.sync_api import Browser, Route, expect, sync_playwright

from app_readiness import diagnosed_page

ID = "10000000-0000-4000-8000-000000000001"
HASH = "a" * 64
HTML = "<!doctype html><html lang='ko'><title>Saved synthetic report</title><p>저장된 결과</p></html>".encode()


def _wait_held(page, held: list) -> None:
    deadline = time.monotonic() + 5
    while not held and time.monotonic() < deadline:
        page.wait_for_timeout(10)
    assert held, "Expected the exact mocked request to be held"


def _sources() -> list[dict]:
    revision = {"response_revision_id": ID, "response_revision_sha256": HASH}
    return [
        {"kind": "analysis_run", "analysis_id": ID, "expected_source_sha256": HASH},
        {
            "kind": "regression_prediction",
            "prediction": {
                "storage": "completed_prediction",
                "family": "pls",
                "source_analysis_id": ID,
                "source_result_sha256": HASH,
                "model_id": ID,
                "model_manifest_sha256": HASH,
                "prediction_artifact_id": ID,
                "expected_source_sha256": HASH,
            },
        },
        {
            "kind": "doe_analysis",
            "family": "factorial",
            "design_id": ID,
            "design_version_id": ID,
            "design_sha256": HASH,
            "analysis_id": ID,
            "expected_source_sha256": HASH,
            "response_revision": revision,
        },
        {
            "kind": "doe_optimizer_result",
            "optimizer": {
                "workflow": "response_surface",
                "design_id": ID,
                "design_version_id": ID,
                "design_sha256": HASH,
                "optimization_id": ID,
                "expected_source_sha256": HASH,
                "source_bundle_sha256": HASH,
                "source_dependencies": [
                    {
                        "analysis_id": ID,
                        "analysis_sha256": HASH,
                        "response_revision": revision,
                    }
                ],
            },
        },
        {
            "kind": "lhs_design_revision",
            "design_id": ID,
            "design_version_id": ID,
            "expected_source_sha256": HASH,
            "response_revisions": [revision],
        },
        {
            "kind": "bayesian_history_revision",
            "study_id": ID,
            "study_version_id": ID,
            "definition_sha256": HASH,
            "history_revision_id": ID,
            "expected_source_sha256": HASH,
            "attachment": {
                "kind": "batch",
                "batch_id": ID,
                "result_json_sha256": HASH,
                "result_payload_sha256": HASH,
            },
        },
    ]


def verify_managed_reports(browser: Browser, base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for locale in ("ko", "en"):
        sources = _sources()
        descriptors = {
            source["kind"]: {
                "source": source,
                "source_ref_sha256": str(index + 1) * 64,
                "title": f"Synthetic {source['kind']} <name> \ue000literal\ue001",
                "created_at": "2026-10-18T00:00:00Z",
                "stale": True,
                "open_target": "/analysis/exploration/eda.descriptive",
            }
            for index, source in enumerate(sources)
        }
        reports: list[dict] = []
        requests: list[dict] = []
        held: list[tuple[Route, dict | None]] = []
        state = {
            "hold_create": False,
            "hold_delete": False,
            "hold_download": False,
            "hold_capability": False,
            "hold_snapshot": False,
            "unsupported": False,
        }

        def serve(route: Route) -> None:
            parsed = urlparse(route.request.url)
            path, method = parsed.path, route.request.method
            body = route.request.post_data_json if route.request.post_data else None
            requests.append({"path": path, "method": method, "body": body})
            if path == "/api/v1/reports/sources":
                kind = parse_qs(parsed.query)["source_kind"][0]
                route.fulfill(
                    json={
                        "items": [descriptors[kind]],
                        "limit": 20,
                        "offset": 0,
                        "has_more": False,
                    }
                )
                return
            if path == "/api/v1/reports/capability":
                descriptor = descriptors[body["source"]["kind"]]
                assert body["source"] == descriptor["source"]
                payload = {
                    "capability_schema_version": 1,
                    "source": descriptor["source"],
                    "source_ref_sha256": descriptor["source_ref_sha256"],
                    "title": descriptor["title"],
                    "locale": body["locale"],
                    "stale": True,
                    "report_level": "unsupported"
                    if state["unsupported"]
                    else "summary",
                    "renderer_id": "synthetic",
                    "renderer_version": "1",
                    "sections": [
                        {
                            "section_id": "saved",
                            "title": "Stored <name> \ue000literal\ue001",
                            "status": "rendered",
                            "reason": None,
                        },
                        {
                            "section_id": "optional",
                            "title": "Optional",
                            "status": "missing",
                            "reason": "stored_section_unavailable",
                        },
                    ],
                    "reason": "renderer_unavailable" if state["unsupported"] else None,
                    "html_available": not state["unsupported"],
                }
                if state["hold_capability"]:
                    held.append((route, payload))
                else:
                    route.fulfill(json=payload)
                return
            if path == "/api/v1/reports/artifacts/query":
                route.fulfill(
                    json={
                        "items": [
                            item
                            for item in reports
                            if item["source"] == body["source"]
                            and item["locale"] == body["locale"]
                        ]
                    }
                )
                return
            if path == "/api/v1/reports/source-snapshot":
                descriptor = descriptors[body["source"]["kind"]]
                assert body["source"] == descriptor["source"]
                payload = {
                    "schema_version": 1,
                    "source": descriptor["source"],
                    "source_ref_sha256": descriptor["source_ref_sha256"],
                    "locale": body["locale"],
                    "title": descriptor["title"],
                    "created_at": descriptor["created_at"],
                    "stale": True,
                    "payload": {
                        "kind": descriptor["source"]["kind"],
                        "saved_value": 0.125,
                        "user_name": "<script>literal</script>\ue000user\ue001",
                    },
                }
                if state["hold_snapshot"]:
                    held.append((route, payload))
                else:
                    route.fulfill(json=payload)
                return
            if path == "/api/v1/reports" and method == "POST":
                descriptor = descriptors[body["source"]["kind"]]
                assert body["source"] == descriptor["source"]
                assert (
                    body["expected_source_ref_sha256"]
                    == descriptor["source_ref_sha256"]
                )
                payload = {
                    "export_id": f"20000000-0000-4000-8000-{len(reports) + 1:012d}",
                    "source": descriptor["source"],
                    "source_ref_sha256": descriptor["source_ref_sha256"],
                    "locale": body["locale"],
                    "report_level": "summary",
                    "renderer_version": "1",
                    "sha256": hashlib.sha256(HTML).hexdigest(),
                    "size_bytes": len(HTML),
                    "created_at": "2026-10-18T00:00:00Z",
                    "stale": True,
                    "media_type": "text/html",
                }
                reports.append(payload)
                if state["hold_create"]:
                    held.append((route, payload))
                else:
                    route.fulfill(json=payload)
                return
            report_id = path.split("/")[4]
            report = next(
                (item for item in reports if item["export_id"] == report_id), None
            )
            if report is None and method == "GET":
                route.fulfill(
                    status=404,
                    json={
                        "error": {
                            "code": "managed_report_not_found",
                            "message": "Saved report not found",
                            "correlation_id": ID,
                        }
                    },
                )
                return
            assert report is not None, path
            if method == "GET":
                route.fulfill(json=report)
            elif path.endswith("/download"):
                assert body == {
                    "source": report["source"],
                    "expected_sha256": report["sha256"],
                }
                if state["hold_download"]:
                    held.append((route, None))
                else:
                    route.fulfill(
                        body=HTML,
                        content_type="text/html",
                        headers={
                            "Content-Disposition": f"attachment; filename=fallback.html; filename*=UTF-8''{quote('보고서-검증.html')}"
                        },
                    )
            elif method == "DELETE":
                assert body == {
                    "source": report["source"],
                    "expected_sha256": report["sha256"],
                }
                reports.remove(report)
                if state["hold_delete"]:
                    held.append((route, {"deleted": True}))
                else:
                    route.fulfill(json={"deleted": True})
            else:
                raise AssertionError((method, path))

        with diagnosed_page(
            browser, output, f"managed-reports-{locale}", locale=locale
        ) as page:
            page.set_viewport_size({"width": 1440, "height": 900})
            downloads = []
            page.on("download", lambda download: downloads.append(download))
            page.route("**/api/v1/reports**", serve)
            completed = False
            try:
                page.goto(
                    f"{base_url}/tests/report-center.html?source_kind=analysis_run"
                )
                page.get_by_role(
                    "button", name="KOR" if locale == "ko" else "ENG", exact=True
                ).click()
                selector = page.locator("[data-report-source-kind]")
                expect(selector.locator("option")).to_have_count(6)
                for source in sources:
                    kind = source["kind"]
                    selector.select_option(kind)
                    page.locator(
                        f"[data-report-source='{descriptors[kind]['source_ref_sha256']}']"
                    ).click()
                    detail = page.locator("[data-managed-report-selection]")
                    expect(detail).to_have_attribute(
                        "data-managed-report-selection",
                        descriptors[kind]["source_ref_sha256"],
                    )
                    expect(
                        detail.locator("[data-report-capability]")
                    ).to_have_attribute("data-report-capability", "summary")
                    snapshot_count = sum(
                        item["path"].endswith("/source-snapshot") for item in requests
                    )
                    detail.locator("[data-view-stored-source]").click()
                    expect(
                        detail.locator("[data-stored-source-snapshot]")
                    ).to_have_attribute(
                        "data-stored-source-snapshot",
                        descriptors[kind]["source_ref_sha256"],
                    )
                    expect(
                        detail.locator("[data-stored-source-snapshot] pre")
                    ).to_contain_text('"saved_value": 0.125')
                    expect(
                        detail.locator("[data-stored-source-snapshot] pre")
                    ).to_contain_text("<script>literal</script>\ue000user\ue001")
                    assert (
                        sum(
                            item["path"].endswith("/source-snapshot")
                            for item in requests
                        )
                        == snapshot_count + 1
                    )
                    detail.locator("[data-create-managed-report]").click()
                    expect(detail.locator("[data-managed-report]")).to_have_count(1)
                # Filters are list-only: current BO selection stays exact.
                selector.select_option("analysis_run")
                expect(
                    page.locator("[data-managed-report-selection]")
                ).to_have_attribute("data-managed-report-selection", "6" * 64)
                expect(page.locator("[data-stored-source-snapshot]")).to_have_attribute(
                    "data-stored-source-snapshot", "6" * 64
                )
                state["hold_snapshot"] = True
                page.locator("[data-view-stored-source]").click()
                _wait_held(page, held)
                page.locator(f"[data-report-source='{'1' * 64}']").click()
                detail = page.locator("[data-managed-report-selection]")
                route, payload = held.pop(0)
                route.fulfill(json=payload)
                state["hold_snapshot"] = False
                expect(detail.locator("[data-stored-source-snapshot]")).to_have_count(0)
                expect(detail.locator("[data-managed-report]")).to_have_count(1)
                state["hold_create"] = True
                detail.locator("[data-create-managed-report]").click()
                _wait_held(page, held)
                selector.select_option("doe_analysis")
                page.locator(f"[data-report-source='{'3' * 64}']").click()
                assert held
                route, payload = held.pop(0)
                route.fulfill(json=payload)
                state["hold_create"] = False
                expect(detail).to_have_attribute(
                    "data-managed-report-selection", "3" * 64
                )
                expect(detail.locator("[data-managed-report]")).to_have_count(1)
                # Old locale completion cannot replace the new capability.
                state["hold_capability"] = True
                page.get_by_role(
                    "button", name="Refresh fixture workspace", exact=True
                ).click()
                _wait_held(page, held)
                state["hold_capability"] = False
                other = "en" if locale == "ko" else "ko"
                page.get_by_role(
                    "button", name="ENG" if other == "en" else "KOR", exact=True
                ).click()
                expect(detail.locator("[data-report-capability]")).to_have_attribute(
                    "data-report-capability", "summary"
                )
                for route, payload in held[:]:
                    route.fulfill(json=payload)
                held.clear()
                page.get_by_role(
                    "button", name="ENG" if locale == "en" else "KOR", exact=True
                ).click()
                expect(detail.locator("[data-managed-report]")).to_have_count(1)
                row = detail.locator("[data-managed-report]").first
                with page.expect_download() as download_info:
                    row.get_by_role(
                        "button",
                        name="다운로드" if locale == "ko" else "Download",
                        exact=True,
                    ).click()
                download = download_info.value
                assert download.suggested_filename == "보고서-검증.html"
                destination = output / f"managed-{locale}.html"
                download.save_as(destination)
                assert (
                    hashlib.sha256(destination.read_bytes()).hexdigest()
                    == hashlib.sha256(HTML).hexdigest()
                )
                # Verified bytes from an obsolete source must not trigger a download.
                download_count = len(downloads)
                state["hold_download"] = True
                row.get_by_role(
                    "button",
                    name="다운로드" if locale == "ko" else "Download",
                    exact=True,
                ).click()
                _wait_held(page, held)
                selector.select_option("regression_prediction")
                page.locator(f"[data-report-source='{'2' * 64}']").click()
                route, _ = held.pop(0)
                route.fulfill(body=HTML, content_type="text/html")
                state["hold_download"] = False
                expect(detail).to_have_attribute(
                    "data-managed-report-selection", "2" * 64
                )
                expect(detail.locator("[data-managed-report]")).to_have_count(1)
                page.evaluate(
                    "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
                )
                assert len(downloads) == download_count
                selector.select_option("doe_analysis")
                page.locator(f"[data-report-source='{'3' * 64}']").click()
                expect(detail.locator("[data-managed-report]")).to_have_count(1)
                row = detail.locator("[data-managed-report]").first
                # Deletion is explicit and held completion cannot clear another source.
                state["hold_delete"] = True
                row.get_by_role(
                    "button", name="삭제" if locale == "ko" else "Delete", exact=True
                ).click()
                page.get_by_role(
                    "button",
                    name="보고서 삭제 확인"
                    if locale == "ko"
                    else "Confirm report deletion",
                    exact=True,
                ).click()
                _wait_held(page, held)
                selector.select_option("analysis_run")
                page.locator(f"[data-report-source='{'1' * 64}']").click()
                assert held
                route, payload = held.pop(0)
                route.fulfill(json=payload)
                state["hold_delete"] = False
                expect(detail).to_have_attribute(
                    "data-managed-report-selection", "1" * 64
                )
                expect(detail.locator("[data-managed-report]")).to_have_count(2)
                detail.locator("[data-view-stored-source]").click()
                expect(
                    detail.locator("[data-stored-source-snapshot]")
                ).to_have_attribute("data-stored-source-snapshot", "1" * 64)
                for width, height in (
                    (1440, 900),
                    (1280, 800),
                    (1024, 768),
                    (390, 844),
                ):
                    page.set_viewport_size({"width": width, "height": height})
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth + 1"
                    ), (locale, width)
                    page.screenshot(
                        path=str(output / f"managed-reports-{locale}-{width}.png"),
                        full_page=True,
                    )
                artifact = reports[0]
                page.goto(
                    f"{base_url}/tests/report-center.html?report_id={artifact['export_id']}"
                )
                expect(
                    page.locator("[data-managed-report-selection]")
                ).to_have_attribute(
                    "data-managed-report-selection", artifact["source_ref_sha256"]
                )
                expect(
                    page.locator(f"[data-managed-report='{artifact['export_id']}']")
                ).to_have_count(1)
                page.goto(
                    f"{base_url}/tests/report-center.html?report_id=ffffffff-ffff-4fff-8fff-ffffffffffff"
                )
                expect(page.get_by_role("alert")).to_contain_text(
                    "managed_report_not_found"
                )
                page.locator(f"[data-report-source='{'2' * 64}']").click()
                expect(
                    page.locator("[data-managed-report-selection]")
                ).to_have_attribute("data-managed-report-selection", "2" * 64)
                expect(page.get_by_role("alert")).to_have_count(0)
                before = len(requests)
                page.goto(f"{base_url}/tests/report-center.html?report_id=invalid")
                expect(page.get_by_role("alert")).to_contain_text(
                    "managed_report_query_invalid"
                )
                assert len(requests) == before
                completed = True
            finally:
                (output / f"managed-reports-{locale}.json").write_text(
                    json.dumps(
                        {
                            "completed": completed,
                            "transport": "mocked synthetic HTTP",
                            "source_kinds": [source["kind"] for source in sources],
                            "requests": requests,
                            "download_sha256": hashlib.sha256(HTML).hexdigest(),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch()
        try:
            verify_managed_reports(chromium, args.base_url, args.output)
        finally:
            chromium.close()
