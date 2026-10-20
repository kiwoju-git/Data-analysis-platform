"""Exact saved RSM view checks after release restart and with its server stopped."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, expect

from app_readiness import diagnosed_page, wait_for_app_ready


def verify_rsm_resume(
    browser: Browser, base: str, output: Path, original: dict
) -> dict:
    design_id, analysis_id = original["design_id"], original["analysis_id"]
    route = "/analysis/doe/doe.response_surface"
    api = f"/api/v1/doe-designs/response-surface/{design_id}/analyses/{analysis_id}"
    view_api = (
        f"/api/v1/doe-designs/{design_id}/response-surface-analyses/{analysis_id}"
        f"/plot-views/{original['view']}"
    )
    with diagnosed_page(browser, output, "rsm-restart", locale="ko") as page:
        fit_calls = []
        page.on(
            "request",
            lambda request: fit_calls.append(request.url)
            if request.method == "POST"
            and urlsplit(request.url).path
            == f"/api/v1/doe-designs/response-surface/{design_id}/analyses"
            else None,
        )
        page.goto(
            base + route + f"?design_id={design_id}&analysis_id={analysis_id}",
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, "ko", route)
        expect(page.locator("#rsm-result-title")).to_be_visible()
        plots = page.locator(".rsm-plot-options")
        plots.get_by_label("저장된 뷰", exact=True).select_option(original["view"])
        expect(plots.get_by_label("X 요인", exact=True)).to_have_value("factor_3")
        expect(plots.get_by_label("축 좌표", exact=True)).to_have_value("coded")
        result = page.request.get(base + api)
        assert result.status == 200, result.text()
        assert (
            hashlib.sha256(result.body()).hexdigest()
            == original["result_payload_sha256"]
        )
        view = page.request.get(base + view_api)
        assert view.status == 200, view.text()
        assert view.json()["sha256"] == original["view_sha256"]
        page.goto(
            base + "/reports?source_kind=doe_analysis", wait_until="domcontentloaded"
        )
        wait_for_app_ready(page, "ko", "/reports")
        sources = page.request.get(
            base + "/api/v1/reports/sources?source_kind=doe_analysis"
        ).json()
        source = next(
            item
            for item in sources["items"]
            if (item["source"].get("plot_view") or {}).get("plot_view_id")
            == original["view"]
        )
        page.locator(f'[data-report-source="{source["source_ref_sha256"]}"]').click()
        row = page.locator(f'[data-managed-report="{original["report_id"]}"]')
        path = output / "rsm-restart" / "restored-contour.html"
        with page.expect_download() as download:
            row.get_by_role("button", name="다운로드", exact=True).click()
        download.value.save_as(path)
        assert path.read_bytes() == Path(original["report_path"]).read_bytes()
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest() == original["report_sha256"]
        )
        assert not fit_calls
        return {
            "schema_version": 1,
            "status": "succeeded",
            "phase": "resume",
            "design_id": design_id,
            "analysis_id": analysis_id,
            "view": original["view"],
            "report_id": original["report_id"],
            "result_payload_sha256": original["result_payload_sha256"],
            "view_sha256": original["view_sha256"],
            "report_sha256": original["report_sha256"],
            "visible_saved_view_restored": True,
            "report_bytes_unchanged": True,
            "analysis_post_count": 0,
        }


def verify_rsm_offline(page: Page, output: Path, original: dict) -> dict:
    path = Path(original["report_path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original["report_sha256"]
    page.goto(path.resolve().as_uri(), wait_until="domcontentloaded")
    expect(
        page.locator('svg[data-rsm-contour="stored-geometry"]').first
    ).to_be_visible()
    expect(
        page.get_by_text("Selected saved custom view", exact=False).first
    ).to_be_visible()
    assert page.locator('svg path[fill-rule="evenodd"]').count() > 0
    assert page.locator("table").count() > 0
    assert page.locator("script, link[href], img[src]").count() == 0
    page.screenshot(path=str(output / "offline-rsm-contour.png"), full_page=True)
    return {
        "schema_version": 1,
        "status": "succeeded",
        "phase": "offline",
        "report_id": original["report_id"],
        "report_sha256": original["report_sha256"],
        "visible_stored_geometry": True,
    }
