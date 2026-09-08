"""Browser assertions for real regularized runs, not mocked solver responses."""

import re
from urllib.parse import urlsplit

from playwright.sync_api import expect


def verify_regularized_regression(page, diagnostics, navigate, paste, select_method):
    navigate(page, "데이터셋")
    data = "y\tx1\tx2\n" + "\n".join(
        f"{3 + 2 * i + (i % 3 - 1) * .2}\t{i}\t{i * .7 + (i % 4) * .1}"
        for i in range(1, 25)
    )
    paste(page, data)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible()
    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/confirm-parsing")) as confirmed:
        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect(page.locator("#active-dataset-version")).to_have_value(confirmed.value.json()["version_id"], timeout=20_000)
    navigate(page, "분석")
    select_method(page, "상관관계 및 회귀분석", "회귀모형 적합")
    panel = page.locator('[data-analysis-execution="regression.linear_model"]')
    expect(panel.get_by_role("radio", name="OLS", exact=True)).to_be_checked()
    panel.get_by_label("반응 변수").select_option(label="y")
    for name in ("x1", "x2"):
        panel.get_by_label("예측변수", exact=True).get_by_role(
            "checkbox", name=re.compile(f"^{name}")
        ).check()
    diagnostics.capture_page(page, "regression-estimator-selector.png")
    diagnostics.capture_page(page, "regression-ols-settings.png")
    panel.get_by_label("모형 선택 방법").select_option("backward_elimination")
    panel.get_by_label("Alpha to remove").fill("0.12")
    panel.get_by_role("radio", name="Ridge", exact=True).check()
    page.locator("#regularization-ridge-mode").select_option("fixed")
    page.locator("#regularization-ridge-alpha").fill("0.25")
    panel.get_by_role("radio", name="Lasso", exact=True).check()
    panel.get_by_role("radio", name="OLS", exact=True).check()
    expect(panel.get_by_label("Alpha to remove")).to_have_value("0.12")
    panel.get_by_role("radio", name="Ridge", exact=True).check()
    expect(page.locator("#regularization-ridge-alpha")).to_have_value("0.25")
    expect(panel.get_by_label("Alpha to remove")).to_have_count(0)

    last_analysis = None
    for estimator, label in (("ridge", "Ridge"), ("lasso", "Lasso"), ("elastic_net", "Elastic Net")):
        panel.get_by_role("radio", name=label, exact=True).check()
        settings = panel.locator(".regularization-settings")
        page.locator(f"#regularization-{estimator}-mode").select_option("automatic_cv")
        settings.locator("summary").click()
        page.locator(f"#regularization-{estimator}-alpha_candidates").fill("5")
        page.locator(f"#regularization-{estimator}-alpha_min").fill("0.001")
        page.locator(f"#regularization-{estimator}-alpha_max").fill("10")
        page.locator(f"#regularization-{estimator}-outer_folds").fill("3")
        page.locator(f"#regularization-{estimator}-inner_folds").fill("3")
        settings.locator("summary").click()
        diagnostics.capture_page(page, f"regression-{estimator}-settings.png")
        with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/api/v1/analysis-runs"), timeout=180_000) as response:
            panel.get_by_role("button", name="회귀모형 적합 실행", exact=True).click()
        assert response.value.ok, response.value.text()
        body = response.value.json()
        result = body["result"]
        last_analysis = body["analysis_id"]
        assert result["estimator"]["kind"] == estimator, f"Requested {estimator}, received {result['estimator']}"
        assert result["validation"]["nested"]
        assert result["regularization"]["selected_alpha"] > 0
        assert result["model_manifest"]["model_id"]
        assert "anova" not in result
        assert all("p_value" not in c for c in result["coefficients"])
        output = panel.locator(".regularized-results")
        expect(output).to_be_visible(timeout=20_000)
        expect(output).to_contain_text("PRESS")
        expect(output.locator('svg[aria-labelledby~="regularization-cv-curve-title"]')).to_be_visible()
        expect(output.locator('svg[aria-labelledby~="regularization-coefficient-path-title"]')).to_be_visible()
        output.scroll_into_view_if_needed()
        diagnostics.capture_page(page, f"regression-{estimator.replace('_', '-')}-result.png")
        page.locator(".language-switcher button").filter(has_text="ENG").click()
        expect(page.locator("html")).to_have_attribute("lang", "en")
        assert not re.search("[가-힣]", output.inner_html()), "English regression result contains untranslated UI"
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "Regression result overflows mobile viewport"
        diagnostics.capture_page(page, f"regression-{estimator}-mobile-en.png")
        page.set_viewport_size({"width": 1440, "height": 900})
        page.locator(".language-switcher button").filter(has_text="KOR").click()
        if estimator == "lasso":
            diagnostics.capture_page(page, "regularization-cv-curve.png")
            diagnostics.capture_page(page, "regularization-coefficient-path.png")
        manual = panel.locator(".regression-manual-prediction")
        for input_box, value in zip(manual.locator("tbody input").all(), ("5", "3.7")):
            input_box.fill(value)
        manual.get_by_role("button", name="전체 사전점검", exact=True).click()
        predict = manual.get_by_role("button", name="전체 예측 실행", exact=True)
        expect(predict).to_be_enabled(timeout=20_000)
        with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/pasted-predictions")) as predicted:
            predict.click()
        assert predicted.value.ok, predicted.value.text()
        assert predicted.value.json()["prediction_uncertainty_kind"] == "point_only"
        expect(manual.locator("th").filter(has_text="개별 예측구간")).to_have_count(0)

    # Refresh the saved analysis, with its immutable model, rather than refitting it.
    base = urlsplit(page.url)
    origin = f"{base.scheme}://{base.netloc}"
    version_id = body["dataset_version_id"]
    page.goto(f"{origin}/analysis/regression/regression.linear_model?dataset_version_id={version_id}")
    history = page.locator(".compact-analysis-history")
    history.get_by_role("button", name="최근 이력 열기", exact=True).click()
    with page.expect_response(lambda r: r.url.endswith(f"/analysis-runs/{last_analysis}/result")):
        history.get_by_role("button", name="결과 불러오기", exact=True).first.click()
    expect(page.locator(".regularized-results")).to_be_visible(timeout=30_000)
    expect(page.get_by_role("radio", name="Elastic Net", exact=True)).to_be_checked()
    verify_compact_domains(page, diagnostics, origin)


def verify_compact_domains(page, diagnostics, origin):
    for locale in ("en", "ko"):
        page.locator(".language-switcher button").filter(has_text="ENG" if locale == "en" else "KOR").click()
        for width, height in ((1440, 900), (1280, 800), (1024, 768), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            page.goto(f"{origin}/analysis")
            page.locator(".language-switcher button").filter(has_text="ENG" if locale == "en" else "KOR").click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            expect(page.locator(".analysis-domain-card")).to_have_count(8)
            if width == 1440:
                diagnostics.capture_page(page, f"compact-domain-root-{locale}.png")
            for domain, name in (("correlation-regression-prediction", "regression"), ("doe-optimization", "doe"), ("mean-equivalence", "mean")):
                page.goto(f"{origin}/analysis?domain={domain}")
                page.locator(".language-switcher button").filter(has_text="ENG" if locale == "en" else "KOR").click()
                expect(page.locator("html")).to_have_attribute("lang", locale)
                guide = page.locator("details.analysis-domain-guide")
                expect(guide).to_be_visible(timeout=20_000)
                expect(guide).not_to_have_attribute("open", "")
                expect(page.locator(".analysis-domain-guidance")).to_have_count(0)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                if name == "regression":
                    cards = page.locator("button.analysis-domain-method-card")
                    expect(cards).to_have_count(5)
                    if width == 1440:
                        for card in cards.all():
                            box = card.locator("strong").bounding_box()
                            assert box and box["y"] + box["height"] < height
                if width in (1440, 390):
                    diagnostics.capture_page(page, f"compact-{name}-domain-{locale}-{width}.png")
                guide.locator("summary").click()
                expect(guide).to_have_attribute("open", "")
            if width == 390:
                diagnostics.capture_page(page, f"compact-domain-mobile-{locale}.png")
    page.set_viewport_size({"width": 1440, "height": 900})
