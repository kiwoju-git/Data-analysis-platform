"""Stored PLS report, offline rendering and applied standalone GPR settings."""

from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import Page, expect


def verify_pls_exports(page: Page, diagnostics: Any, analysis: dict, open_reports: Any) -> None:
    prediction = page.locator(".pls-point-prediction")
    with page.expect_download() as snapshot:
        prediction.get_by_role("button", name="예측 스냅샷 다운로드 (JSON)").click()
    body = json.loads(snapshot.value.path().read_text(encoding="utf-8"))
    assert body["source_analysis_id"] == analysis["analysis_id"]
    assert body["prediction_recalculated_on_export"] is False
    assert body["response"]["rows"]
    analysis_url = page.url
    for locale, language in (("ko", "KOR"), ("en", "ENG")):
        page.locator(".language-switcher button").filter(has_text=language).click()
        with page.expect_response(
            lambda r: r.request.method == "POST" and r.url.endswith("/exports/html")
        ) as created:
            page.locator(".export-format-card").filter(
                has=page.locator("strong").filter(has_text="HTML")
            ).get_by_role("button").click()
        assert created.value.ok, created.value.text()
        assert created.value.json()["analysis_id"] == analysis["analysis_id"]
        with page.expect_download() as downloaded:
            page.locator(".export-status-box").filter(
                has=page.locator("span").filter(has_text="HTML")
            ).get_by_role("button").click()
        path = diagnostics.html_root / f"pls-stored-report-{locale}.html"
        downloaded.value.save_as(path)
        browser = page.context.browser
        assert browser is not None
        offline = browser.new_context(
            offline=True, viewport={"width": 1280, "height": 800}
        )
        try:
            report = offline.new_page()
            report.goto(path.resolve().as_uri())
            core = report.locator('[data-pls-report="1"]')
            expect(core).to_be_visible()
            assert core.locator("svg").count() >= 6
            assert core.locator("table").count() >= 7
            expect(core.locator("[data-loading-component]")).to_have_count(
                analysis["result"]["model_summary"]["selected_components"]
            )
            assert report.locator("script, link[href], img[src]").count() == 0
            diagnostics.capture_page(report, f"pls-offline-report-{locale}.png")
        finally:
            offline.close()
    page.locator(".language-switcher button").filter(has_text="KOR").click()
    open_reports()
    row = page.locator(".report-run-row").filter(has_text="PLS").first
    expect(row).to_be_visible()
    row.click()
    exports = page.locator(".export-list-item").filter(has_text="HTML")
    expect(exports).to_have_count(2)
    with page.expect_download() as again:
        exports.first.get_by_role("button", name="다운로드", exact=True).click()
    assert 'data-pls-report="1"' in again.value.path().read_text(encoding="utf-8")
    page.goto(analysis_url)


def configure_and_verify_gp_settings(page: Page, diagnostics: Any) -> None:
    panel = page.locator(".gp-regression-panel")
    settings = panel.locator(".gp-optimization-settings")
    expect(settings.get_by_label("길이 척도 하한", exact=True)).to_have_value("0.5")
    scaling = panel.locator(".gp-settings-table").get_by_role("checkbox").first
    settings.get_by_label("길이 척도 하한", exact=True).fill("0.75")
    page.once("dialog", lambda dialog: dialog.dismiss())
    scaling.click()
    expect(scaling).to_be_checked()
    expect(settings.get_by_label("길이 척도 하한", exact=True)).to_have_value("0.75")
    page.once("dialog", lambda dialog: dialog.accept())
    scaling.click()
    expect(scaling).not_to_be_checked()
    expect(settings.get_by_label("길이 척도 하한", exact=True)).to_have_value("0.01")
    page.once("dialog", lambda dialog: dialog.accept())
    scaling.click()
    expect(scaling).to_be_checked()
    expect(settings.get_by_label("길이 척도 하한", exact=True)).to_have_value("0.5")
    settings.get_by_label("최적화 알고리즘", exact=True).select_option("bfgs")
    settings.get_by_label("길이 척도 하한", exact=True).fill("1")
    expect(
        panel.get_by_role("button", name="Gaussian Process 회귀 실행")
    ).to_be_disabled()
    settings.get_by_label("길이 척도 하한", exact=True).fill("0.75")
    settings.get_by_label("길이 척도 상한", exact=True).fill("20")
    expect(
        panel.get_by_role("button", name="Gaussian Process 회귀 실행")
    ).to_be_enabled()
    for locale, language in (("ko", "KOR"), ("en", "ENG")):
        page.locator(".language-switcher button").filter(has_text=language).click()
        for width, height in ((1440, 900), (1280, 800), (1024, 768), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            settings.scroll_into_view_if_needed()
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            assert settings.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
            geometry = settings.evaluate("""e => ({
                left: e.getBoundingClientRect().left,
                right: e.getBoundingClientRect().right,
                panelLeft: e.closest('.gp-regression-panel').getBoundingClientRect().left,
                controls: [...e.querySelectorAll('input, select, legend, label > span')].map(c => ({
                    left: c.getBoundingClientRect().left, right: c.getBoundingClientRect().right
                }))
            })""")
            diagnostics.record(f"GPR settings geometry {locale}/{width}: {geometry}")
            assert geometry["left"] >= geometry["panelLeft"] - 1
            assert all(c["left"] >= geometry["left"] - 1 and c["right"] <= geometry["right"] + 1
                       for c in geometry["controls"])
            diagnostics.capture_page(page, f"gp-applied-settings-{locale}-{width}.png")
            if width == 390:
                diagnostics.capture_page(page, f"gp-settings-viewport-{locale}.png", full_page=False)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.locator(".language-switcher button").filter(has_text="KOR").click()
