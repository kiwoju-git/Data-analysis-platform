"""Production Two Variances workflow against an isolated synthetic workspace."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import traceback
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

CSV = "value,group,alternate\n1,A,X\n2,A,X\n3,A,X\n4,A,X\n5,A,X\n1,B,Y\n3,B,Y\n5,B,Y\n7,B,Y\n9,B,Y\n"
PREFLIGHT = "/api/v1/analysis-methods/quality.two_variances/preflight"
RUNS = "/api/v1/analysis-runs"


def _language(page, language: str) -> None:
    button = page.locator(".language-switcher button").filter(has_text=language)
    if button.is_enabled():
        button.click()


def _assert_close(actual: float, expected: float, tolerance: float = 1e-10) -> None:
    assert math.isclose(actual, expected, abs_tol=tolerance, rel_tol=tolerance), (
        actual,
        expected,
    )


def verify_two_variances(page, diagnostics, backend: str) -> None:
    """Reusable critical-path helper; no production dataset or model is touched."""
    from critical_path import open_primary_navigation, paste_plain_text

    origin = f"{urlsplit(page.url).scheme}://{urlsplit(page.url).netloc}"
    page.set_viewport_size({"width": 1440, "height": 900})
    _language(page, "KOR")
    diagnostics.step("two variances: paste synthetic two-group CSV")
    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, CSV)
    page.get_by_role("button", name="붙여넣기 데이터 등록", exact=True).click()
    expect(page.get_by_role("heading", name="파싱 옵션", exact=True)).to_be_visible()
    with page.expect_response(
        lambda response: "/confirm-parsing" in response.url
        and response.request.method == "POST"
    ) as parsed:
        page.get_by_role("button", name="파싱 확정 및 버전 생성", exact=True).click()
    assert parsed.value.ok, parsed.value.text()
    version = parsed.value.json()
    expect(page.locator("#version-title")).to_contain_text("v1")
    columns = {
        column["display_name"]: column["column_id"] for column in version["columns"]
    }
    page.goto(
        origin + "/analysis/quality/quality.two_variances", wait_until="networkidle"
    )
    _language(page, "ENG")
    root = page.locator('[data-analysis-execution="quality.two_variances"]')
    expect(root).to_be_visible()
    input_selects = root.locator(".option-grid").first.locator("select")
    input_selects.nth(0).select_option(columns["value"])
    input_selects.nth(1).select_option(columns["group"])
    run_button = root.get_by_role("button", name="Run analysis", exact=True)
    expect(run_button).to_be_disabled()

    def api(method, path, body=None):
        response = page.request.fetch(backend + path, method=method, data=body)
        assert response.ok, response.text()
        return response.json()

    def check_groups():
        with page.expect_response(
            lambda response: response.url == origin + PREFLIGHT
            and response.request.method == "POST"
        ) as checked:
            root.get_by_role("button", name="Check groups", exact=True).click()
        assert checked.value.ok, checked.value.text()
        expect(run_button).to_be_enabled()
        return checked.value.json()

    diagnostics.step("two variances: ignore stale preflight after group change")
    pending = []
    page.route("**" + PREFLIGHT, lambda route: pending.append(route))
    root.get_by_role("button", name="Check groups", exact=True).click()
    page.wait_for_timeout(50)
    assert len(pending) == 1
    input_selects.nth(1).select_option(columns["alternate"])
    expect(root.get_by_role("button", name="Check groups", exact=True)).to_be_enabled()
    root.get_by_role("button", name="Check groups", exact=True).click()
    page.wait_for_timeout(50)
    assert len(pending) == 2
    old = api("POST", PREFLIGHT, pending[0].request.post_data_json)
    new = api("POST", PREFLIGHT, pending[1].request.post_data_json)
    pending[1].fulfill(
        status=200, content_type="application/json", body=json.dumps(new)
    )
    numerator = root.get_by_role("combobox", name=re.compile(r"^Numerator group"))
    expect(numerator.locator("option")).to_have_text(["X", "Y"])
    pending[0].fulfill(
        status=200, content_type="application/json", body=json.dumps(old)
    )
    page.wait_for_timeout(100)
    expect(numerator.locator("option")).to_have_text(["X", "Y"])
    page.unroute("**" + PREFLIGHT)
    input_selects.nth(1).select_option(columns["group"])
    expect(run_button).to_be_disabled()
    preflight = check_groups()
    assert preflight["eligible"] and preflight["n_used"] == 10
    assert [(group["key"], group["n_used"]) for group in preflight["groups"]] == [
        ("A", 5),
        ("B", 5),
    ]
    numerator.select_option("B")
    expect(root).to_contain_text("Denominator group: A")
    numerator.select_option("A")
    settings = root.locator(".option-grid").last
    assert settings.evaluate("element => getComputedStyle(element).display") == "grid"
    method = settings.locator("select").nth(0)
    scale = settings.locator("select").nth(1)
    alternative = settings.locator("select").nth(2)
    expect(method).to_have_value("brown_forsythe")
    expect(alternative).to_be_disabled()
    expect(settings.locator("input").first).to_be_disabled()

    def analyze():
        with page.expect_response(
            lambda response: response.url == origin + RUNS
            and response.request.method == "POST"
        ) as response:
            run_button.click()
        assert response.value.ok, response.value.text()
        envelope = response.value.json()
        assert envelope["method_id"] == "quality.two_variances"
        assert envelope["result"]["summary_type"] == "two_variances_test"
        request = response.value.request.post_data_json
        assert request["options"]["preflight_fingerprint"] == preflight["fingerprint"]
        expect(root.locator(".result-section")).to_be_visible()
        expect(run_button).to_be_enabled()
        return envelope

    diagnostics.step("two variances: default Brown-Forsythe, no invented interval")
    bf = analyze()
    _assert_close(bf["result"]["test"]["statistic"], 72 / 35)
    _assert_close(bf["result"]["test"]["p_value"], 0.189403661093321)
    _assert_close(bf["result"]["ratio_estimate"]["variance"], 0.25)
    assert not bf["result"]["ratio_interval"]["available"]
    expect(root.locator(".result-section")).to_contain_text(
        "Not provided by the selected method"
    )
    expect(root.locator('[data-chart-id="two-variances-ratio"]')).to_have_count(0)
    expect(
        root.locator('[data-chart-id="two-variances-groups"] [data-selected]')
    ).to_have_count(10)
    diagnostics.capture_locator(root, "two-variances-brown-forsythe.png")

    diagnostics.step("two variances: normal F two-sided and directional intervals")
    method.select_option("normal_f")
    expect(settings.locator("input").first).to_be_enabled()
    expect(alternative).to_be_enabled()
    f_two = analyze()
    _assert_close(f_two["result"]["test"]["p_value"], 0.208)
    _assert_close(
        f_two["result"]["ratio_interval"]["lower"]["value"], 0.0260293843634819
    )
    _assert_close(f_two["result"]["ratio_interval"]["upper"]["value"], 2.40113247118072)
    expect(root.locator('[data-chart-id="two-variances-ratio"]')).to_be_visible()
    alternative.select_option("greater")
    f_greater = analyze()
    assert f_greater["result"]["ratio_interval"]["upper"] == {
        "kind": "unbounded",
        "value": None,
    }
    expect(root.locator(".result-section")).to_contain_text("∞")
    alternative.select_option("less")
    scale.select_option("standard_deviation")
    f_less = analyze()
    _assert_close(f_less["result"]["ratio_estimate"]["value"], 0.5)
    assert f_less["result"]["ratio_interval"]["lower"] == {
        "kind": "finite",
        "value": 0.0,
    }
    assert f_less["result"]["ratio_interval"]["upper"]["kind"] == "finite"
    expect(root.locator('[data-chart-id="two-variances-ratio"]')).to_contain_text(
        "Standard deviation ratio"
    )
    for width, height in [(1440, 900), (1024, 768), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(100)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        diagnostics.capture_locator(root, f"two-variances-f-{width}.png")
    page.set_viewport_size({"width": 1440, "height": 900})
    _language(page, "KOR")
    expect(root.get_by_role("button", name="분석 실행", exact=True)).to_be_visible()
    expect(method).to_have_value("normal_f")
    expect(scale).to_have_value("standard_deviation")
    diagnostics.capture_locator(root, "two-variances-korean.png")

    diagnostics.step(
        "two variances: saved result and report center use exact analysis ID"
    )
    page.reload(wait_until="networkidle")
    _language(page, "KOR")
    history = page.locator(".compact-analysis-history")
    history.get_by_role("button", name="최근 이력 열기", exact=True).click()
    with page.expect_response(
        lambda response: response.url
        == origin + f"{RUNS}/{f_less['analysis_id']}/result"
    ) as restored:
        history.get_by_role("button", name="결과 불러오기", exact=True).first.click()
    assert restored.value.ok and restored.value.json()["result"] == f_less["result"]
    expect(method).to_have_value("normal_f")
    expect(scale).to_have_value("standard_deviation")
    expect(alternative).to_have_value("less")
    expect(root.locator(".result-section")).to_be_visible()
    snapshots = {}
    for envelope in [bf, f_two, f_greater, f_less]:
        analysis_id = envelope["analysis_id"]
        stored = api("GET", f"{RUNS}/{analysis_id}/result")
        assert stored["result"] == envelope["result"]
        snapshots[analysis_id] = stored
    exports = []
    for envelope, locale in [(bf, "en"), (f_greater, "ko")]:
        analysis_id = envelope["analysis_id"]
        page.goto(
            origin + "/reports?analysis_id=" + analysis_id, wait_until="networkidle"
        )
        _language(page, "ENG" if locale == "en" else "KOR")
        export_panel = page.locator(".report-selected-result .analysis-export-panel")
        expect(export_panel).to_be_visible()
        with page.expect_response(
            lambda response: response.url
            == origin + f"{RUNS}/{analysis_id}/exports/html"
            and response.request.method == "POST"
        ) as created:
            export_panel.get_by_role("button", name=re.compile(r"^HTML ")).first.click()
        assert created.value.ok, created.value.text()
        assert created.value.request.post_data_json["locale"] == locale
        artifact = created.value.json()
        assert artifact["analysis_id"] == analysis_id
        with page.expect_download() as downloaded:
            export_panel.get_by_role("button", name=re.compile(r"^HTML ")).last.click()
        destination = diagnostics.html_root / f"two-variances-{locale}.html"
        downloaded.value.save_as(destination)
        assert (
            hashlib.sha256(destination.read_bytes()).hexdigest() == artifact["sha256"]
        )
        html = destination.read_text(encoding="utf-8")
        assert "<script" not in html.lower()
        offline = page.context.browser.new_context(offline=True)
        report = offline.new_page()
        try:
            report.goto(destination.resolve().as_uri(), wait_until="load")
            expect(report.locator("svg")).not_to_have_count(0)
            assert report.locator("dd").filter(has_text=analysis_id).count() == 1
            body = report.locator('[data-two-variances-report="1"]').inner_text()
            assert report.locator(
                '[data-two-variances-report="1"] svg text[y="249"]'
            ).all_text_contents() == ["A", "B"]
            if locale == "en":
                assert "Brown" in body and "not" in body.lower()
                assert "0.25" in body
            else:
                assert "상한 없음" in body
            report.screenshot(
                path=str(
                    diagnostics.screenshot_root / f"two-variances-report-{locale}.png"
                ),
                full_page=True,
            )
        finally:
            offline.close()
        exports.append(
            {"analysis_id": analysis_id, "locale": locale, "sha256": artifact["sha256"]}
        )

    for kind in ["json", "csv"]:
        analysis_id = f_less["analysis_id"]
        artifact = api("POST", f"{RUNS}/{analysis_id}/exports/{kind}")
        download = page.request.get(
            backend + f"{RUNS}/{analysis_id}/exports/{artifact['export_id']}/download"
        )
        assert download.ok
        assert hashlib.sha256(download.body()).hexdigest() == artifact["sha256"]
        if kind == "json":
            assert download.json()["result"]["result"] == f_less["result"]
        else:
            assert "two_variances_test" in download.text()
    for analysis_id, before in snapshots.items():
        assert api("GET", f"{RUNS}/{analysis_id}/result") == before
    diagnostics.root.joinpath("two-variances-validation.json").write_text(
        json.dumps(
            {
                "analysis_ids": list(snapshots),
                "exports": exports,
                "preflight_stale_response_ignored": True,
                "offline_html": True,
                "viewport_widths": [1440, 1024, 390],
                "locales": ["ko", "en"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _browser_flow(frontend, diagnostics, backend, *_flags) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        context.add_init_script("localStorage.setItem('statistical-twin.locale', 'ko')")
        page = context.new_page()
        try:
            page.goto(frontend, wait_until="networkidle")
            expect(page.get_by_text("API 준비됨", exact=True)).to_be_visible(
                timeout=20_000
            )
            verify_two_variances(page, diagnostics, backend)
        except Exception:
            traceback.print_exc()
            diagnostics.capture_page_failure(page)
            raise
        finally:
            browser.close()


def main() -> int:
    # Reuse the established temporary-workspace/process lifecycle, with owned ports.
    import critical_path

    critical_path.run_browser_flow = _browser_flow
    return critical_path.main()


if __name__ == "__main__":
    sys.exit(main())
