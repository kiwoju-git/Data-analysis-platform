"""Exact supplied DOE fixture and shared-fold GP comparison in the production UI."""
import re
from urllib.parse import urlsplit

from playwright.sync_api import expect


def verify_curvature_selection(page, diagnostics, backend):
    origin = f"{urlsplit(page.url).scheme}://{urlsplit(page.url).netloc}"
    page.set_viewport_size({"width": 1440, "height": 900})
    korean = page.locator(".language-switcher button").filter(has_text="KOR")
    if korean.is_enabled():
        korean.click()
    def api(method, path, body=None):
        response = page.request.fetch(backend + path, method=method, data=body)
        assert response.ok, response.text()
        return response.json()
    diagnostics.step("curvature: exact 11-run Titer fixture, editable server-owned terms")
    design = api("POST", "/api/v1/doe-designs/factorial", {
        "name": "Titer center selection reference", "factors": [
            {"name": "Temperature", "low": 35, "high": 37},
            {"name": "pH", "low": 6, "high": 7}, {"name": "Glucose", "low": 1, "high": 2}],
        "replicates": 1, "center_points": 3, "block_count": 1, "randomize": False, "randomization_seed": 41,
    })
    base = "/api/v1/doe-designs/" + design["design_id"]
    values = [1.88, 5.79, .91, 4.87, 4.23, 5.39, 5.09, 6.04, 4.11, 4.36, 4.26]
    api("PUT", base + "/responses", {"response_name": "Titer", "values": [
        {"run_order": index + 1, "value": value} for index, value in enumerate(values)]})
    page.goto(origin + "/analysis/doe/doe.factorial_design?design_id=" + design["design_id"], wait_until="networkidle")
    root = page.locator('.analysis-run-panel[data-analysis-execution="doe.factorial_design"]')
    terms = root.locator(".doe-term-selection")
    expect(terms.get_by_label("Center curvature", exact=True)).to_have_value("candidate")
    expect(terms.get_by_label("Temperature", exact=True).locator('option[value="excluded"]')).to_be_disabled()
    diagnostics.capture_locator(terms, "factorial-term-selection.png")
    def analyze():
        with page.expect_response(lambda response: response.url == origin + base + "/analyses" and response.request.method == "POST") as pending:
            root.get_by_role("button", name="효과 및 ANOVA 분석", exact=True).click()
        assert pending.value.ok, pending.value.text()
        return pending.value.json()
    full = analyze()
    center = next(term for term in full["result"]["terms"] if term["kind"] == "curvature")
    assert abs(center["p_value"] - .71296244) < 1e-7
    root.locator(".doe-model-selection select").select_option("backward_elimination")
    diagnostics.capture_locator(terms, "factorial-center-candidate.png")
    selected = analyze()
    trace = selected["result"]["model_selection"]
    assert trace["removed_term_ids"] == ["center_curvature", "factor_1:factor_2"]
    assert trace["final_term_ids"] == ["factor_1", "factor_2", "factor_3", "factor_1:factor_3", "factor_2:factor_3"]
    assert abs(trace["steps"][-1]["press"] - .19198344) < 1e-8
    matrix = root.locator(".doe-step-matrix")
    expect(matrix).to_contain_text("Mallows Cp")
    diagnostics.capture_locator(matrix, "factorial-backward-step-matrix.png")
    diagnostics.capture_locator(root.locator(".factorial-selection-results"), "factorial-user-fixture-final.png")
    prediction = root.locator(".factorial-prediction")
    for name, value in [("Temperature", "36.2"), ("pH", "6.3"), ("Glucose", "1.8")]:
        prediction.get_by_label(name + " 1", exact=True).fill(value)
    prediction.get_by_role("button", name="전체 사전점검", exact=True).click()
    expect(prediction.get_by_role("button", name="전체 예측", exact=True)).to_be_enabled()
    prediction.get_by_role("button", name="전체 예측", exact=True).click()
    expect(prediction.locator(".factorial-prediction-results tbody tr")).to_have_count(1)
    for width, height in [(1280, 800), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        matrix.scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        if width == 390:
            page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")
            mobile = matrix.locator(".doe-step-mobile")
            expect(mobile).to_be_visible()
            mobile.locator("select").select_option("2")
            expect(mobile).to_contain_text("PRESS")
            diagnostics.capture_locator(mobile, "factorial-step-mobile.png")
    page.set_viewport_size({"width": 1440, "height": 900})
    terms.get_by_label("Center curvature", exact=True).select_option("forced")
    diagnostics.capture_locator(terms, "factorial-center-forced.png")
    forced = analyze()
    assert forced["result"]["model_selection"]["removed_term_ids"] == ["factor_1:factor_2"]
    assert forced["result"]["model_policy"]["center_curvature_included"]
    root.locator(".doe-model-selection select").select_option("none")
    terms.get_by_label("pH * Glucose", exact=True).select_option("excluded")
    manual = analyze()
    assert manual["result"]["model_selection"]["initially_excluded_term_ids"] == ["factor_2:factor_3"]
    terms.get_by_role("button", name="모두 선택", exact=True).click()
    expect(terms.get_by_label("pH * Glucose", exact=True)).to_have_value("candidate")
    expect(terms.get_by_label("Center curvature", exact=True)).to_have_value("forced")
    assert api("GET", base)["design_sha256"] == design["design_sha256"]
    page.locator(".language-switcher button").filter(has_text="ENG").click()
    assert not re.search(r"[가-힣]", terms.inner_text())
    page.locator(".language-switcher button").filter(has_text="KOR").click()


def verify_gp_kernel_comparison(page, diagnostics, panel, api_base):
    diagnostics.step("GP: noise composition, shared-fold kernel comparison, retained candidate details")
    settings = panel.locator(".gp-kernel-selection")
    expect(settings).to_contain_text("WhiteKernel")
    diagnostics.capture_locator(settings, "gp-whitekernel-help.png")
    settings.get_by_role("radio", name="후보 kernel 비교", exact=True).check()
    settings.get_by_role("checkbox", name="Rational Quadratic", exact=True).check()
    settings.get_by_role("checkbox", name="후보 kernel별 상세 결과 저장", exact=True).check()
    panel.get_by_label("Fold 수", exact=True).fill("3")
    panel.get_by_label("CV restart 수", exact=True).fill("2")
    diagnostics.capture_locator(settings, "gp-kernel-selection.png")
    before = page.request.get(api_base + "/regression-models").json()["models"]
    with page.expect_response(lambda response: response.url == api_base + "/analysis-runs" and response.request.method == "POST", timeout=120_000) as pending:
        panel.get_by_role("button", name="Gaussian Process 회귀 실행", exact=True).click()
    assert pending.value.ok, pending.value.text()
    result = pending.value.json()["result"]
    assert result["kernel_selection"]["mode"] == "compare"
    assert len(result["kernel_candidates"]) == 3
    assert sum(item["selected"] for item in result["kernel_candidates"]) == 1
    assert all(item["details"] is not None for item in result["kernel_candidates"])
    after = page.request.get(api_base + "/regression-models").json()["models"]
    assert len(after) == len(before) + 1
    comparison = panel.locator(".gp-kernel-comparison")
    expect(comparison).to_be_visible()
    diagnostics.capture_locator(comparison.locator(".table-wrap").first, "gp-kernel-comparison.png")
    for radio in comparison.get_by_role("radio").all():
        radio.check()
        expect(comparison.locator("svg")).to_have_count(2)
    diagnostics.capture_locator(comparison, "gp-candidate-details.png")
    prediction = panel.locator(".gp-point-prediction")
    prediction.get_by_label("temperature_c 1", exact=True).fill("75")
    prediction.get_by_label("pressure_bar 1", exact=True).fill("8")
    with page.expect_response(lambda response: response.url.endswith("/gaussian-process-predictions") and response.request.method == "POST") as pending_prediction:
        prediction.get_by_role("button", name="예측 실행", exact=True).click()
    assert pending_prediction.value.ok, pending_prediction.value.text()
    panel.get_by_label("CV restart 수", exact=True).fill("5")
    expect(panel.locator(".gp-optimizer-starts")).to_contain_text("57")
    settings.get_by_role("checkbox", name="Matérn 3/2 ARD", exact=True).check()
    panel.get_by_label("Fold 수", exact=True).fill("10")
    panel.get_by_label("최종 모형 restart 수", exact=True).fill("10")
    expect(panel.locator(".gp-optimizer-starts")).to_contain_text("284")
    expect(panel.get_by_role("button", name="Gaussian Process 회귀 실행", exact=True)).to_be_disabled()
    diagnostics.capture_locator(panel.locator(".gp-optimizer-starts"), "gp-budget-warning.png")
    for width, height in [(1280, 800), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        settings.scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        if width == 390:
            page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")
            diagnostics.capture_page(page, "gp-kernel-mobile.png", full_page=False)
    page.set_viewport_size({"width": 1440, "height": 900})
