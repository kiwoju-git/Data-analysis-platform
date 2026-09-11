"""Stored final-model DOE workflow, with synthetic design fixtures only."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from playwright.sync_api import expect


def verify_factorial_model_workflow(page, diagnostics, backend):
    origin = f"{urlsplit(page.url).scheme}://{urlsplit(page.url).netloc}"
    page.set_viewport_size({"width": 1440, "height": 900})
    korean = page.locator(".language-switcher button").filter(has_text="KOR")
    if korean.is_enabled():
        korean.click()

    def api(method, path, body=None):
        response = page.request.fetch(backend + path, method=method, data=body)
        assert response.ok, (method, path, response.status, response.text())
        return response.json()

    def fixture(*, general=False, replicates=2, centers=0, save=False):
        factors = ([{"name": "A", "levels": [1, 2, 3]},
                    {"name": "B", "levels": ["Low", "High"]}] if general else
                   [{"name": name, "low": -1, "high": 1} for name in "ABC"])
        request = {"name": "Workflow reference", "factors": factors,
                   "replicates": replicates, "randomize": False, "randomization_seed": 11}
        if not general:
            request.update(center_points=centers, block_count=1)
        design = api("POST", "/api/v1/doe-designs/" + ("general-factorial" if general else "factorial"), request)
        base = "/api/v1/doe-designs/" + ("general-factorial/" if general else "") + design["design_id"]
        values = []
        for run in design["runs"]:
            if general:
                a, b = (run["level_indices"][name] for name in "AB")
                y = 10 + 3*a + 2*b + .001*a*b
            else:
                a, b, c = (run["coded_levels"][name] for name in "ABC")
                y = 10 + 3*a + 2*b + c + .02*a*b + .03*a*c + .04*b*c + .01*a*b*c
            values.append({"run_order": run["run_order"], "value": y + .5*(run["replicate_index"]-1)})
        if save:
            api("PUT", base + "/responses", {"response_name": "Yield", "values": values})
        return design, base, values

    def open_design(design, *, general=False, analysis_id=None):
        url = origin + "/analysis/doe/doe.factorial_design?design_id=" + design["design_id"]
        url += "&design_kind=" + ("general" if general else "two_level")
        if analysis_id:
            url += "&analysis_id=" + analysis_id
        page.goto(url, wait_until="networkidle")
        root = page.locator('.analysis-run-panel[data-analysis-execution="doe.factorial_design"]')
        expect(root).to_be_visible(timeout=20_000)
        return root

    def analyze(root, base, backward=True, order="3"):
        root.get_by_label("최대 상호작용 차수", exact=True).select_option(order)
        root.locator(".doe-model-selection select").select_option("backward_elimination" if backward else "none")
        if backward:
            expect(root.locator(".doe-model-selection input[type=number]").first).to_have_value("0.05")
        with page.expect_response(lambda response: response.url == backend + base + "/analyses" and response.request.method == "POST") as pending:
            root.get_by_role("button", name="효과 및 ANOVA 분석", exact=True).click()
        response = pending.value
        assert response.status == 201, response.text()
        result = response.json()
        expect(root.locator(".factorial-coded-coefficients")).to_be_visible()
        return result

    diagnostics.step("factorial: paste preview is draft-only, then save one revision")
    design, base, values = fixture()
    root = open_design(design)
    root.get_by_role("button", name="반응값 붙여넣기", exact=True).click()
    paste = root.locator(".doe-response-paste")
    paste.locator("textarea").fill("\n".join(str(row["value"]) for row in values))
    paste.get_by_role("button", name="미리보기", exact=True).click()
    expect(paste.locator("tbody tr")).to_have_count(16)
    diagnostics.capture_locator(paste, "factorial-response-paste.png")
    paste.get_by_role("button", name="반응값 입력표에 적용", exact=True).click()
    expect(root.get_by_label("run 1 response", exact=True)).to_have_value(str(values[0]["value"]))
    assert api("GET", base + "/responses")["responses"] == []
    root.get_by_role("button", name="반응값 저장", exact=True).click()
    expect(root.get_by_label("저장된 DOE 반응 요약")).to_be_visible()

    diagnostics.step("factorial: none parity and replicated hierarchical backward selection")
    full = analyze(root, base, backward=False)
    assert full["result"]["model_selection"]["removed_term_ids"] == []
    root.locator(".doe-model-selection select").select_option("backward_elimination")
    diagnostics.capture_locator(root.locator(".doe-model-selection"), "factorial-backward-settings.png")
    selected = analyze(root, base)
    selection = selected["result"]["model_selection"]
    assert len(selection["final_term_ids"]) == 3
    assert not selection["initial_model_saturated"]
    assert selected["result"]["final_model"]["prediction_basis"]["residual_df"] == 12
    diagnostics.capture_locator(root.locator(".factorial-selection-results"), "factorial-model-selection-steps.png")
    diagnostics.capture_locator(root.locator(".factorial-equation"), "factorial-coded-equation.png")
    diagnostics.capture_locator(root.locator(".factorial-coded-coefficients"), "factorial-coded-coefficients.png")

    diagnostics.step("factorial: final raw and standardized four-in-one diagnostics")
    root.get_by_text("4-in-1 잔차 그림", exact=True).click()
    residual = root.locator(".factorial-residual-plots")
    expect(residual.locator("svg")).to_have_count(4)
    diagnostics.capture_locator(residual, "factorial-four-in-one-residuals.png")
    residual.locator("select").select_option("standardized")
    expect(residual.locator("svg")).to_have_count(4)
    first_point = residual.locator('svg [tabindex="0"]').first
    first_point.focus()
    first_point.press("ArrowRight")
    boxes = [residual.locator(".chart-panel").nth(i).bounding_box() for i in range(4)]
    assert abs(boxes[0]["y"] - boxes[1]["y"]) <= 2
    assert boxes[2]["y"] >= boxes[0]["y"] + boxes[0]["height"] - 1

    diagnostics.step("factorial: saved final-model multi-row prediction and intervals")
    prediction = root.locator(".factorial-prediction")
    prediction.get_by_role("button", name="행 추가", exact=True).click()
    prediction.get_by_role("button", name="행 추가", exact=True).click()
    for index, settings in enumerate([(.2, -.4, .7), (1, 1, 1), (-1, 0, 1)], 1):
        for factor, value in zip("ABC", settings, strict=True):
            prediction.get_by_label(f"{factor} {index}", exact=True).fill(str(value))
    prediction.get_by_role("button", name="전체 사전점검", exact=True).click()
    predict = prediction.get_by_role("button", name="전체 예측", exact=True)
    expect(predict).to_be_enabled()
    predict.click()
    expect(prediction.locator(".factorial-prediction-results tbody tr")).to_have_count(3)
    diagnostics.capture_locator(prediction, "factorial-prediction.png")

    diagnostics.step("factorial: fitted main, interaction and cube plots")
    plots = root.locator(".factorial-plots")
    expect(plots.locator("svg").first).to_be_visible()
    diagnostics.capture_locator(plots.locator(".chart-grid").first, "factorial-main-effects.png")
    diagnostics.capture_locator(plots.locator(".chart-grid").nth(1), "factorial-interaction-plot.png")
    diagnostics.capture_locator(plots.locator(".factorial-cube-chart"), "factorial-cube-plot.png")
    diagnostics.step("factorial: switch to observed data means")
    plots.locator("select").first.select_option("data_mean")
    diagnostics.step("factorial: show all interaction pairs")
    plots.get_by_label("모든 요인 쌍 (최대 15개)", exact=True).check()
    expect(plots.locator(".chart-grid").nth(1).locator("svg")).to_have_count(3)
    plots.locator("select").first.select_option("fitted_mean")
    diagnostics.step("factorial: switch cube to two factors")
    plots.get_by_label("큐브 차원", exact=True).select_option("2")
    expect(plots.locator(".factorial-cube-chart circle")).to_have_count(4)
    plots.get_by_label("큐브 차원", exact=True).select_option("3")

    diagnostics.step("factorial: managed HTML report from stored analysis, then restore")
    assets = root.locator(".factorial-analysis-assets")
    assets.get_by_role("button", name="HTML 분석 보고서 생성", exact=True).click()
    report = assets.locator("tbody tr").filter(has_text="HTML").first
    expect(report).to_be_visible()
    with page.expect_download() as download:
        report.get_by_role("button", name="다운로드", exact=True).click()
    path = diagnostics.root / "factorial-analysis-report.html"
    download.value.save_as(path)
    html = path.read_text(encoding="utf-8")
    assert selected["analysis_id"] in html and "<svg" in html
    assert "<script" not in html and "https://" not in html
    report_page = page.context.new_page()
    report_page.goto(path.resolve().as_uri())
    diagnostics.capture_page(report_page, "factorial-report-html.png", full_page=False)
    report_page.close()
    root = open_design(design, analysis_id=selected["analysis_id"])
    expect(root.locator(".factorial-coded-coefficients")).to_be_visible()
    assert api("GET", base)["design_sha256"] == design["design_sha256"]

    diagnostics.step("factorial: explicit run mapping creates a new revision without changing history")
    expect(root.get_by_role("button", name="반응값 붙여넣기", exact=True)).to_be_disabled()
    root.get_by_role("button", name="새 revision으로 수정", exact=True).click()
    root.get_by_role("button", name="반응값 붙여넣기", exact=True).click()
    paste = root.locator(".doe-response-paste")
    paste.get_by_label("입력 형식", exact=True).select_option("run_order")
    paste.get_by_label("첫 행에 열 이름 포함", exact=True).check()
    paste.locator("textarea").fill("run_order\tresponse\n" + "\n".join(f"{row['run_order']}\t{row['value'] + 1}" for row in reversed(values)))
    paste.get_by_role("button", name="미리보기", exact=True).click()
    paste.get_by_role("button", name="반응값 입력표에 적용", exact=True).click()
    expect(root.get_by_label("run 1 response", exact=True)).to_have_value(str(values[0]["value"] + 1))
    before = api("GET", base + "/analyses/" + selected["analysis_id"])
    root.get_by_role("button", name="새 revision 저장", exact=True).click()
    expect(root.get_by_role("button", name="새 revision 저장", exact=True)).to_have_count(0)
    assert api("GET", base + "/analyses/" + selected["analysis_id"]) == before

    diagnostics.step("factorial: report is discoverable in asset management")
    catalog = api("GET", "/api/v1/assets?category=analyses")
    report_asset = next(item for item in catalog["items"] if item["asset_type"] == "doe_analysis_report")
    page.goto(origin + "/manage?tab=analyses", wait_until="networkidle")
    expect(page.locator(".asset-catalog-table")).to_contain_text("HTML")
    page.goto(origin + report_asset["open_target"]["path"], wait_until="networkidle")
    expect(page.locator(".factorial-analysis-assets")).to_contain_text("HTML")

    diagnostics.step("factorial: saturated pooling without invented p-values")
    saturated, sat_base, _ = fixture(replicates=1, save=True)
    root = open_design(saturated)
    sat = analyze(root, sat_base)
    trace = sat["result"]["model_selection"]
    assert trace["initial_model_saturated"] and trace["pooled_term_ids"]
    assert all(step["removal_p_value"] is None for step in trace["steps"] if step["phase"] == "initial_pooling")
    diagnostics.capture_locator(root.locator(".factorial-selection-results"), "factorial-saturated-pooling.png")

    diagnostics.step("factorial: English semantic interaction labels and mobile layout")
    page.locator(".language-switcher button").filter(has_text="ENG").click()
    options = root.locator("select[aria-label]").filter(has=page.locator('option[value="3"]')).first
    expect(options).to_contain_text("Main effects only")
    assert not re.search(r"[123]\s*tea", root.inner_text(), re.I)
    assert not re.search(r"[가-힣]", root.inner_text()), "Unresolved Korean in English DOE"
    diagnostics.capture_locator(root.locator(".doe-model-selection"), "factorial-english-interaction-order.png")
    root.locator(".factorial-analysis-assets").get_by_role("button", name="Create HTML analysis report", exact=True).click()
    expect(root.locator(".factorial-analysis-assets tbody tr").filter(has_text="EN")).to_have_count(1)
    for width, height in [(1280, 800), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        if width == 390:
            page.wait_for_function("document.querySelector('.sidebar').getBoundingClientRect().right <= 0")
        root.locator(".doe-model-selection").scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        if width == 390:
            for control in root.locator(".doe-model-selection select, .doe-model-selection input[type=number]").all():
                box = control.bounding_box()
                assert box["x"] >= 0 and box["x"] + box["width"] <= 391
            diagnostics.capture_page(page, "factorial-mobile.png", full_page=False)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.locator(".language-switcher button").filter(has_text="KOR").click()

    diagnostics.step("factorial: General Full multi-DF block selection and known-level prediction")
    general, general_base, _ = fixture(general=True, save=True)
    root = open_design(general, general=True)
    root.locator(".doe-model-selection select").select_option("backward_elimination")
    with page.expect_response(lambda response: response.url == backend + general_base + "/analyses" and response.request.method == "POST") as pending:
        root.get_by_role("button", name=re.compile("ANOVA")).click()
    assert pending.value.status == 201, pending.value.text()
    general_analysis = pending.value.json()
    assert general_analysis["result"]["model_selection"]["steps"][1]["removal_df"] == 2
    expect(root.locator(".factorial-prediction select").first).to_be_visible()
    assert root.locator(".factorial-prediction-input input").count() == 0

    diagnostics.step("factorial: center-curvature interior prediction is blocked")
    centered, center_base, _ = fixture(centers=2, save=True)
    root = open_design(centered)
    analyze(root, center_base, backward=False, order="2")
    prediction = root.locator(".factorial-prediction")
    prediction.get_by_label("A 1", exact=True).fill("0")
    prediction.get_by_role("button", name="전체 사전점검", exact=True).click()
    expect(prediction.get_by_role("button", name="전체 예측", exact=True)).to_be_disabled()
    expect(prediction.locator('[role="status"]')).to_contain_text("corner")
    diagnostics.record("Factorial stored-model workflow passed")
