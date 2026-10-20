"""Visible synthetic DOE/RSM completion journey, reusable against a release."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, expect

from app_readiness import diagnosed_page, wait_for_app_ready


def verify_doe_rsm_completion(browser: Browser, base: str, output: Path) -> dict:
    route = "/analysis/doe/doe.response_surface"
    receipt: dict = {"fixture": "synthetic", "designs": [], "analyses": []}
    with diagnosed_page(
        browser,
        output,
        "rsm-completion",
        init_script=(
            "if (localStorage.getItem('statistical-twin.locale') === null) "
            "localStorage.setItem('statistical-twin.locale', 'ko')"
        ),
    ) as page:
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(base + route, wait_until="domcontentloaded")
        wait_for_app_ready(page, "ko", route)
        # Four factors make the four requested parameter counts distinguishable.
        for _ in range(2):
            page.get_by_role("button", name="요인 추가", exact=True).click()
        long_name = "합성 반응기 온도 Synthetic reactor temperature with a long factor name"
        long_unit = "synthetic degree Celsius"
        page.get_by_label("요인 1 이름", exact=True).fill(long_name)
        page.get_by_label(f"{long_name} 단위", exact=True).fill(long_unit)
        expect(page.locator("#rsm-center-points")).to_have_value("7")
        for kind in ("inscribed", "face_centered", "circumscribed"):
            page.locator("#rsm-alpha-mode").select_option(kind)
            if kind == "circumscribed":
                page.get_by_label(
                    "표시된 cube 범위 밖 축점도 실행 가능하며 공정 허용범위 안임을 확인했습니다.",
                    exact=True,
                ).check()
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and urlsplit(response.url).path
                == "/api/v1/doe-designs/response-surface"
            ) as pending:
                page.get_by_role("button", name="CCD 생성", exact=True).click()
            assert pending.value.status == 201, pending.value.text()
            design = pending.value.json()
            assert design["options"]["ccd_type"] == kind
            assert len(design["runs"]) == 31
            assert design["factors"][0]["name"] == long_name
            assert design["factors"][0]["unit"] == long_unit
            for factor in design["factors"]:
                coding = design["coding"][factor["name"]]
                half = (factor["high"] - factor["low"]) / 2
                expected_scale = half / 2 if kind == "inscribed" else half
                assert coding["scale"] == expected_scale
            receipt["designs"].append(
                {
                    "id": design["design_id"],
                    "kind": kind,
                    "sha256": design["design_sha256"],
                    "coding": design["coding"],
                }
            )

        names = [factor["name"] for factor in design["factors"]]
        for run in design["runs"]:
            a, b, _, _ = [run["coded_levels"][name] for name in names]
            value = (
                20
                + 3 * a
                - 2 * b
                + 4 * a * b
                + 5 * a * a
                + 0.013 * (run["run_order"] % 5 - 2)
            )
            page.get_by_label(f"Run {run['run_order']} 반응", exact=True).fill(
                str(value)
            )
        response_path = (
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/responses"
        )
        with page.expect_response(
            lambda response: response.request.method == "PUT"
            and urlsplit(response.url).path == response_path
        ) as pending:
            page.get_by_role("button", name="반응 저장", exact=True).click()
        assert pending.value.status == 200, pending.value.text()
        analysis_path = (
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/analyses"
        )
        for preset, count in (
            ("linear", 5),
            ("linear_squares", 9),
            ("linear_interactions", 11),
            ("full_quadratic", 15),
        ):
            page.get_by_role("combobox", name="RSM 모형항", exact=True).select_option(preset)
            analysis = _analyze(page, analysis_path)
            assert analysis["result"]["sample"]["parameter_count"] == count
            assert analysis["result"]["term_preset"] == preset
            receipt["analyses"].append(
                {"id": analysis["analysis_id"], "preset": preset}
            )
        page.locator(".doe-model-selection select").select_option(
            "backward_elimination"
        )
        analysis = _analyze(page, analysis_path)
        result = analysis["result"]
        assert result["model_selection"]["method"] == "backward_elimination"
        assert (
            result["final_basis"]["term_ids"][1:]
            == result["model_selection"]["final_term_ids"]
        )
        saved_analysis = page.request.get(
            base + analysis_path + "/" + analysis["analysis_id"]
        )
        assert saved_analysis.status == 200
        original_bytes = saved_analysis.body()
        plots = page.locator(".rsm-plot-options")
        expect(plots.locator('path[fill-rule="evenodd"]').first).to_be_visible()
        requests: list[str] = []
        page.on(
            "request",
            lambda request: requests.append(urlsplit(request.url).path)
            if request.method == "POST"
            else None,
        )
        plots.get_by_role("combobox", name="X 요인", exact=True).select_option("factor_3")
        held_value = design["factors"][0]["low"] / 2 + design["factors"][0]["high"] / 2
        plots.get_by_label("고정 실제값: " + names[0], exact=False).fill(
            str(held_value)
        )
        plots.get_by_role("combobox", name="축 좌표", exact=True).select_option("coded")
        plot_path = (
            f"/api/v1/doe-designs/{design['design_id']}"
            f"/response-surface-analyses/{analysis['analysis_id']}"
        )
        with page.expect_response(
            lambda response: urlsplit(response.url).path == plot_path + "/plot-view"
        ) as pending:
            plots.get_by_role("button", name="그래프 설정 적용", exact=True).click()
        assert pending.value.status == 200, pending.value.text()
        view = pending.value.json()
        assert view["bundle"]["settings"]["x_factor_id"] == "factor_3"
        assert view["bundle"]["settings"]["axis_scale"] == "coded"
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and urlsplit(response.url).path == plot_path + "/plot-views"
        ) as pending:
            plots.get_by_role("button", name="뷰 저장", exact=True).click()
        assert pending.value.status == 201, pending.value.text()
        saved = pending.value.json()
        assert saved["view"]["view_sha256"] == view["view_sha256"]
        assert analysis_path not in requests, "View edits must never refit the model"
        plots.get_by_label("소형 전체 보기", exact=True).check()
        expect(plots.locator(".doe-compact-plot")).to_have_count(10)
        dimensions = []
        for width in (1920, 1440, 1280, 1024, 900, 768, 390, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            expect(plots.locator(".doe-compact-grid")).to_be_visible()
            overflow = page.evaluate("""() => ({
                viewport: innerWidth,
                scrollWidth: document.documentElement.scrollWidth,
                elements: [...document.querySelectorAll('.analysis-run-panel *')]
                    .map(element => ({
                        tag: element.tagName, class: element.className,
                        right: element.getBoundingClientRect().right,
                        scrollWidth: element.scrollWidth, clientWidth: element.clientWidth,
                        overflowX: getComputedStyle(element).overflowX
                    }))
                    .filter(element => element.right > innerWidth + 1
                        || (element.overflowX === 'visible'
                            && element.scrollWidth > element.clientWidth + 1))
                    .slice(0, 30)
            })""")
            assert overflow["scrollWidth"] <= overflow["viewport"] + 1, overflow
            cards = plots.locator(".doe-compact-plot")
            for card in cards.all():
                svg = card.locator("svg.chart-frame-svg").bounding_box()
                box = card.bounding_box()
                assert svg and box and svg["x"] >= box["x"] - 1
                assert svg["x"] + svg["width"] <= box["x"] + box["width"] + 1
            content_width = plots.locator(".doe-compact-scope").bounding_box()["width"]
            columns = plots.locator(".doe-compact-grid").evaluate(
                "element => getComputedStyle(element).gridTemplateColumns.split(' ').length"
            )
            expected_columns = (
                4
                if content_width >= 1040
                else 3
                if content_width >= 780
                else 2
                if content_width >= 520
                else 1
            )
            dimension = {
                "viewport": width,
                "content": content_width,
                "columns": columns,
            }
            assert columns == expected_columns, dimension
            dimensions.append(dimension)
        assert {item["columns"] for item in dimensions} == {1, 2, 3, 4}, dimensions
        first = plots.locator('svg [tabindex="0"]').first
        first.focus()
        first.press("ArrowRight")
        first.press("Escape")
        page.screenshot(
            path=str(output / "rsm-completion" / "compact-ko.png"), full_page=True
        )
        page.locator(".language-switcher button").filter(has_text="ENG").click()
        expect(page.locator("html")).to_have_attribute("lang", "en")
        assert analysis_path not in requests
        expect(plots.get_by_label("Compact overview", exact=True)).to_be_checked()
        page.screenshot(
            path=str(output / "rsm-completion" / "compact-en.png"), full_page=True
        )

        sources = page.request.get(
            base + "/api/v1/reports/sources?source_kind=doe_analysis"
        ).json()
        source = next(
            item
            for item in sources["items"]
            if (item["source"].get("plot_view") or {}).get("plot_view_id")
            == saved["asset_id"]
        )
        page.goto(
            base + "/reports?source_kind=doe_analysis", wait_until="domcontentloaded"
        )
        wait_for_app_ready(page, "en", "/reports")
        page.locator(f'[data-report-source="{source["source_ref_sha256"]}"]').click()
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and urlsplit(response.url).path == "/api/v1/reports"
        ) as pending:
            page.locator("[data-create-managed-report]").click()
        assert pending.value.status == 201, pending.value.text()
        report = pending.value.json()
        row = page.locator(f'[data-managed-report="{report["export_id"]}"]')
        with page.expect_download() as pending_download:
            row.get_by_role("button", name="Download", exact=True).click()
        path = output / "rsm-completion" / "saved-contour.html"
        pending_download.value.save_as(path)
        html = path.read_text(encoding="utf-8")
        assert 'data-rsm-contour="stored-geometry"' in html
        assert "Selected saved custom view" in html
        assert hashlib.sha256(path.read_bytes()).hexdigest() == report["sha256"]
        assert (
            page.request.get(
                base + analysis_path + "/" + analysis["analysis_id"]
            ).body()
            == original_bytes
        )
        page.goto(
            base
            + route
            + f"?design_id={design['design_id']}&analysis_id={analysis['analysis_id']}",
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, "en", route)
        expect(page.locator("#rsm-result-title")).to_be_visible()
        restored_plots = page.locator(".rsm-plot-options")
        restored_plots.get_by_role("combobox", name="Saved views", exact=True).select_option(
            saved["asset_id"]
        )
        expect(restored_plots.get_by_role("combobox", name="X factor", exact=True)).to_have_value(
            "factor_3"
        )
        expect(
            restored_plots.get_by_role("combobox", name="Axis coordinates", exact=True)
        ).to_have_value("coded")
        assert (
            page.request.get(
                base + analysis_path + "/" + analysis["analysis_id"]
            ).body()
            == original_bytes
        )
        assert analysis_path not in requests
        receipt.update(
            {
                "schema_version": 1,
                "status": "succeeded",
                "design_id": design["design_id"],
                "analysis_id": analysis["analysis_id"],
                "view": saved["asset_id"],
                "report_id": report["export_id"],
                "report_sha256": report["sha256"],
                "report_source_ref_sha256": report["source_ref_sha256"],
                "report_locale": report["locale"],
                "result_payload_sha256": hashlib.sha256(original_bytes).hexdigest(),
                "view_sha256": saved["sha256"],
                "report_path": str(path.resolve()),
                "resize_content_widths": dimensions,
                "browser_zoom": "not exercised by this fixture",
            }
        )
    return receipt


def _analyze(page: Page, path: str) -> dict:
    button = page.get_by_role("button", name="지정 RSM 모형 적합", exact=True)
    expect(button).to_be_enabled()
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == path
    ) as pending:
        button.click()
    assert pending.value.status == 201, pending.value.text()
    expect(page.locator("#rsm-result-title")).to_be_visible()
    return pending.value.json()
