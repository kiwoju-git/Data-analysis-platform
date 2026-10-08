from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Locator, Route, expect, sync_playwright


def verify_chart_interactions(browser: Browser, base_url: str, output: Path) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    requests: list[str] = []
    page.on(
        "request",
        lambda request: requests.append(request.url)
        if request.url.startswith(f"{base_url}/api/")
        else None,
    )
    try:
        page.goto(f"{base_url}/tests/chart-interaction.html", wait_until="networkidle")
        chart = page.locator(".interactive-chart")
        points = chart.locator("[tabindex]")
        first = page.get_by_role("img", name="Point 1", exact=True)
        second = page.get_by_role("img", name="Point 2", exact=True)
        third = page.get_by_role("img", name="Point 3", exact=True)
        expect(points).to_have_count(3)
        expect(chart.locator('[tabindex="0"]')).to_have_count(1)
        first.focus()
        expect(page.get_by_role("tooltip")).to_contain_text("Point 1")
        first.press("ArrowRight")
        expect(second).to_be_focused()
        second.press("End")
        expect(third).to_be_focused()
        third.press("Home")
        expect(first).to_be_focused()
        first.press("Enter")
        expect(page.get_by_test_id("selection-count")).to_have_text("1")
        second.hover()
        expect(page.get_by_role("tooltip")).to_contain_text("Point 2")
        expect(chart.locator(".chart-selected-detail")).to_contain_text("Point 1")
        expect(first).to_have_attribute("data-selected", "true")
        expect(second).to_have_attribute("data-selected", "false")
        expect(page.get_by_test_id("selection-count")).to_have_text("1")
        page.mouse.move(5, 5)
        expect(page.get_by_test_id("selection")).to_have_text("point:1")
        page.get_by_role("button", name="Locale", exact=True).click()
        expect(first).to_have_attribute("data-selected", "true")
        first.focus()
        first.press("Escape")
        expect(page.get_by_role("tooltip")).to_have_count(0)
        expect(first).to_be_focused()
        expect(first).to_have_attribute("tabindex", "0")
        page.set_viewport_size({"width": 1024, "height": 768})
        expect(page.get_by_role("tooltip")).to_have_count(0)
        page.get_by_role("button", name="External selection").click()
        expect(third).to_have_attribute("data-selected", "true")
        expect(chart.locator(".chart-selected-detail")).to_contain_text("Point 3")
        first.focus()
        first.press(" ")
        expect(page.get_by_test_id("selection")).to_have_text("point:1")
        first.press("Tab")
        expect(page.get_by_role("button", name="After chart")).to_be_focused()
        page.get_by_role("button", name="Remove point").click()
        expect(page.get_by_test_id("selection")).to_have_text("none")
        second.click()
        page.get_by_role("button", name="Replace result").click()
        expect(page.get_by_test_id("selection")).to_have_text("none")

        third.click()
        page.get_by_role("button", name="Move coordinates").click()
        tooltip = page.get_by_role("tooltip")
        expect(tooltip).to_be_visible()
        page.wait_for_timeout(100)
        point_box = third.bounding_box()
        tooltip_box = tooltip.bounding_box()
        assert point_box is not None and tooltip_box is not None
        center_y = point_box["y"] + point_box["height"] / 2
        assert abs(tooltip_box["y"] + tooltip_box["height"] + 10 - center_y) < 2

        for scale in [0.5, 1, 1.5]:
            chart.locator(".chart-frame-svg").evaluate(
                "(svg, scale) => { svg.style.width = `${svg.viewBox.baseVal.width * scale}px`; svg.style.maxWidth = 'none'; }",
                scale,
            )
            third.hover()
            tooltip = page.get_by_role("tooltip")
            expect(tooltip).to_be_visible()
            box = tooltip.bounding_box()
            assert box is not None and box["x"] >= 8 and box["y"] >= 8
            assert box["x"] + box["width"] <= 1024 - 8
            assert box["y"] + box["height"] <= 768 - 8
            described = third.get_attribute("aria-describedby")
            assert described == tooltip.get_attribute("id")
            assert tooltip.evaluate("node => node.parentElement === document.body")
        third.click()
        page.mouse.move(5, 5)
        page.evaluate("window.scrollTo(0, 80)")
        third.focus()
        expect(page.get_by_role("tooltip")).to_be_visible()
        output.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output / "chart-interaction.png"))
        assert requests == [], "Chart interactions must not call analysis APIs"
    finally:
        context.close()


def _axis_text(chart: Locator) -> list[str]:
    return chart.locator(".chart-visible-axis-title").evaluate_all(
        "nodes => nodes.map(node => [...node.childNodes]"
        ".filter(child => child.nodeName.toLowerCase() !== 'title')"
        ".map(child => child.textContent).join(''))"
    )


def _assert_square_scale(chart: Locator, data_dx: float, data_dy: float) -> None:
    points = chart.locator("[tabindex]")
    first = points.nth(0).bounding_box()
    second = points.nth(1).bounding_box()
    assert first is not None and second is not None
    dx = abs(first["x"] + first["width"] / 2 - second["x"] - second["width"] / 2)
    dy = abs(first["y"] + first["height"] / 2 - second["y"] - second["height"] / 2)
    assert abs(dx / data_dx - dy / data_dy) < 0.02, "Unequal PCA pixels per unit"
    plot = chart.locator("clipPath rect")
    assert plot.get_attribute("width") == plot.get_attribute("height") == "384"


def _surface_response(route: Route, offset: float) -> dict[str, Any]:
    request = route.request.post_data_json
    rows = [
        {
            "client_row_id": row["client_row_id"],
            "predicted_mean": offset
            + 10 * row["values"]["x1"]
            + row["values"]["x2"]
            + row["values"]["x3"],
            "predictive_standard_deviation": 0.25 + index / 100,
        }
        for index, row in enumerate(request["rows"])
    ]
    return {
        "model_id": "model-gp",
        "model_manifest_sha256": request["expected_model_manifest_sha256"],
        "response_column_id": "response",
        "row_count": len(rows),
        "rows": list(reversed(rows)),
    }


def verify_result_chart_models(browser: Browser, base_url: str, output: Path) -> None:
    """Verify stored-payload display adapters, independently of interaction fixture."""
    output.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    errors: list[str] = []
    api_requests: list[str] = []
    pending: list[Route] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "request",
        lambda request: api_requests.append(request.url)
        if request.url.startswith(f"{base_url}/api/")
        else None,
    )
    prediction_route = (
        "**/api/v1/regression-models/model-gp/gaussian-process-predictions"
    )
    page.route(prediction_route, lambda route: pending.append(route))

    def chart(chart_id: str) -> Locator:
        return page.locator(f'[data-chart-id="{chart_id}"]')

    report: dict[str, Any] = {
        "fixture": "synthetic stored result payloads",
        "viewports": [],
    }
    try:
        page.goto(f"{base_url}/tests/result-charts.html", wait_until="networkidle")
        expect(chart("pca-scree")).to_be_visible()
        assert _axis_text(chart("pca-scree")) == ["Component", "Eigenvalue"]
        assert _axis_text(chart("pca-score")) == [
            "PC1 score (90% variance)",
            "PC2 score (10% variance)",
        ]
        _assert_square_scale(chart("pca-score"), 2, 0.4)
        pca_score = chart("pca-score").locator("[tabindex]").first
        pca_score.focus()
        expect(page.get_by_role("tooltip")).to_contain_text("1.1")
        pca_loading = chart("pca-loading").locator("[tabindex]").first
        pca_loading.focus()
        expect(page.get_by_role("tooltip")).to_contain_text("temperature_c")
        expect(page.get_by_role("tooltip")).to_contain_text("0.95")
        expect(page.get_by_role("tooltip")).to_contain_text("0.32")
        pca_loading.press("Escape")
        labels = chart("pca-biplot").locator(".chart-vector-label").all_text_contents()
        assert len(labels) <= 2 and all("Row" not in label for label in labels)
        assert not any(label.strip() in {"1", "2"} for label in labels)
        expect(chart("pca-biplot").locator("line[marker-end]")).to_have_count(2)
        assert _axis_text(chart("pca-outliers")) == [
            "Row",
            "Squared Mahalanobis distance",
        ]
        expect(
            chart("pca-outliers").locator("g[clip-path] .reference-line")
        ).to_have_count(1)

        selection = chart("pls-selection")
        expect(selection.locator("path.pls-training-line")).to_have_count(1)
        expect(selection.locator("path.pls-cv-line")).to_have_count(1)
        expect(
            selection.locator(
                ".chart-series-legend li:has(circle), .chart-series-legend li:has(polygon)"
            )
        ).to_have_count(2)
        negative = selection.locator("[tabindex][aria-label*='-0.4']")
        expect(negative).to_have_count(1)
        negative.focus()
        expect(page.get_by_role("tooltip")).to_contain_text("-0.4")
        expect(page.get_by_role("tooltip")).to_contain_text("PRESS")
        assert negative.evaluate("""point => {
            const box = point.getBBox();
            const clip = point.ownerSVGElement.querySelector('clipPath rect');
            return box.y >= +clip.getAttribute('y') && box.y + box.height <=
              +clip.getAttribute('y') + +clip.getAttribute('height');
        }"""), "Negative predicted R-squared clipped out of plot"
        response = chart("pls-response")
        assert _axis_text(response) == [
            "Observed yield_pct",
            "Predicted value yield_pct",
        ]
        expect(response.locator("[tabindex]")).to_have_count(4)
        expect(
            response.locator(
                ".chart-series-legend li:has(circle), .chart-series-legend li:has(polygon)"
            )
        ).to_have_count(2)
        expect(response.locator("g[clip-path] .reference-line")).to_have_count(1)
        assert "PLS t2" not in _axis_text(chart("pls-scores"))

        loading = chart("pls-loading")
        expect(loading.locator("[tabindex]")).to_have_count(12)
        expect(loading.locator(".chart-page-controls span")).to_contain_text("1")
        loading.get_by_role("button", name="Next variables", exact=True).click()
        expect(loading.locator("[tabindex]")).to_have_count(12)
        expect(loading.locator("[tabindex]").first).to_have_attribute(
            "aria-label", re.compile(r"Predictor 13 with a long label:")
        )
        page.get_by_role("button", name="Change loading component", exact=True).click()
        expect(loading.locator("[tabindex]").first).to_have_attribute(
            "aria-label", "Predictor 13 with a long label: 0.3"
        )
        assert "Component 2 loadings" in _axis_text(loading)
        loading.get_by_role("button", name="Next variables", exact=True).click()
        expect(loading.locator("[tabindex]")).to_have_count(1)
        expect(
            loading.get_by_role("button", name="Next variables", exact=True)
        ).to_be_disabled()
        loading.get_by_role("button", name="Previous variables", exact=True).click()
        expect(loading.locator("[tabindex]")).to_have_count(12)

        page.get_by_role("button", name="Toggle one component", exact=True).click()
        assert _axis_text(chart("pca-score")) == ["Row", "PC1 score (90% variance)"]
        expect(chart("pca-loading-1d").locator("[tabindex]")).to_have_count(2)
        expect(chart("pca-biplot")).to_have_count(0)
        expect(
            page.get_by_text("A biplot requires two stored components.", exact=True)
        ).to_be_visible()
        assert "PLS t2" not in _axis_text(chart("pls-scores"))
        page.get_by_role("button", name="Toggle one component", exact=True).click()
        expect(chart("pca-biplot")).to_be_visible()

        expect(chart("gp-cv")).to_have_count(2)
        ids = page.locator("svg [id]").evaluate_all(
            "nodes => nodes.map(node => node.id)"
        )
        assert len(ids) == len(set(ids)), "Candidate and selected SVG IDs collide"
        assert "New-observation predictive SD" in _axis_text(chart("gp-uncertainty"))
        profile = chart("gp-profile-x1")
        expect(profile.locator("[tabindex]")).to_have_count(25)
        expect(profile.locator('[tabindex="0"]')).to_have_count(1)
        expect(profile.locator(".chart-interval-band")).to_have_count(1)
        profile.locator("[tabindex]").first.focus()
        profile.locator("[tabindex]").first.press("End")
        expect(profile.locator("[tabindex]").last).to_be_focused()
        expect(page.get_by_role("tooltip").locator("dd")).to_have_text(
            ["1", "11", "10 - 12"]
        )
        profile.locator("[tabindex]").last.press("Escape")
        assert (
            api_requests == []
        ), "Display interactions must not issue prediction/analysis calls"

        surface = page.locator(".gp-surface-result")
        surface_chart = chart("gp-surface")
        assert _axis_text(surface_chart) == ["temperature_c", "pressure_bar"]
        expect(surface_chart.locator(".chart-color-scale")).to_be_visible()
        expect(surface_chart.locator("[data-grid-cell]")).to_have_count(9)
        surface.get_by_role("combobox", name=re.compile(r"^X predictor")).select_option(
            "x3"
        )
        assert _axis_text(surface_chart) == ["temperature_c", "pressure_bar"]
        generate = surface.locator(".gp-surface-controls > button")
        with page.expect_request(prediction_route):
            generate.click()
        page.wait_for_timeout(50)
        assert len(pending) == 1
        first_request = pending.pop()
        surface.get_by_role("combobox", name=re.compile(r"^X predictor")).select_option(
            "x1"
        )
        with page.expect_request(prediction_route):
            generate.click()
        page.wait_for_timeout(50)
        assert len(pending) == 1
        second_request = pending.pop()
        second_request.fulfill(json=_surface_response(second_request, 2000))
        expected_corner = surface_chart.locator('[data-grid-cell="cell:70:5"]')
        expect(expected_corner).to_have_attribute("aria-label", re.compile(r"2705\.5$"))
        first_request.fulfill(json=_surface_response(first_request, 9000))
        page.wait_for_timeout(100)
        assert _axis_text(surface_chart) == ["temperature_c", "pressure_bar"]
        expect(expected_corner).to_have_attribute("aria-label", re.compile(r"2705\.5$"))
        expected_corner.focus()
        expected_corner.press("ArrowRight")
        expect(surface_chart.locator('[data-grid-cell="cell:85:5"]')).to_be_focused()

        for corruption in ("duplicate", "missing", "unexpected"):
            with page.expect_request(prediction_route):
                generate.click()
            page.wait_for_timeout(50)
            route = pending.pop()
            payload = _surface_response(route, 5000)
            if corruption == "duplicate":
                payload["rows"][0] = payload["rows"][1].copy()
            elif corruption == "missing":
                payload["rows"].pop()
            else:
                payload["rows"][0]["client_row_id"] = "unexpected-row"
            route.fulfill(json=payload)
            expect(surface.get_by_role("alert")).to_contain_text(
                "gp_surface_response_invalid"
            )
            expect(expected_corner).to_have_attribute(
                "aria-label", re.compile(r"2705\.5$")
            )

        with page.expect_request(prediction_route):
            generate.click()
        page.wait_for_timeout(50)
        obsolete_source_request = pending.pop()
        page.get_by_role("button", name="Replace source", exact=True).click()
        expect(surface_chart.locator('[data-grid-cell="cell:0:0"]')).to_be_visible()
        initial_cells = surface_chart.locator("[data-grid-cell]").evaluate_all(
            "nodes => nodes.map(node => node.getAttribute('aria-label'))"
        )
        obsolete_source_request.fulfill(
            json=_surface_response(obsolete_source_request, 7000)
        )
        page.wait_for_timeout(100)
        assert (
            surface_chart.locator("[data-grid-cell]").evaluate_all(
                "nodes => nodes.map(node => node.getAttribute('aria-label'))"
            )
            == initial_cells
        )
        assert len(api_requests) == 6

        for width, height in ((1440, 900), (1024, 768), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            page.mouse.move(0, 0)
            page.evaluate("document.activeElement?.blur(); window.scrollTo(0, 0)")
            dimensions = page.evaluate("""() => ({
                width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
                charts: [...document.querySelectorAll('.chart-frame-svg')].map(svg => {
                    const a = svg.getBoundingClientRect();
                    const b = svg.closest('.chart-frame').getBoundingClientRect();
                    return {left: a.left, right: a.right, parentLeft: b.left,
                      parentRight: b.right, width: a.width, height: a.height};
                })
            })""")
            assert dimensions["scrollWidth"] <= width + 1, dimensions
            for box in dimensions["charts"]:
                assert box["width"] > 0 and box["height"] > 0
                assert box["left"] >= box["parentLeft"] - 1
                assert box["right"] <= box["parentRight"] + 1
            _assert_square_scale(chart("pca-score"), 2, 0.4)
            expect(loading.locator("[tabindex]").first).to_have_attribute(
                "aria-label", "Predictor 13 with a long label: 0.3"
            )
            page.screenshot(
                path=str(output / f"result-chart-models-{width}.png"), full_page=True
            )
            report["viewports"].append(dimensions)
        assert errors == [], errors
        report["status"] = "passed"
        report["prediction_requests"] = len(api_requests)
        report["assertions"] = [
            "PCA square equal units, visible axes, raw tooltip values, sparse labels, single component",
            "PLS negative predicted R2, separate series, loading page preservation",
            "GP unique SVG IDs, 25 keyboard profile points, grid neighbor keys",
            "GP shuffled IDs, stale request/source rejection, malformed response rejection",
            "1440/1024/390 no page overflow and plots contained",
        ]
        (output / "result-chart-models-validation.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    except Exception:
        page.screenshot(
            path=str(output / "result-chart-models-failure.png"), full_page=True
        )
        raise
    finally:
        for route in pending:
            route.abort()
        context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--suite", choices=["all", "interaction", "models"], default="all"
    )
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            if args.suite in {"all", "interaction"}:
                verify_chart_interactions(browser, args.url, args.output)
            if args.suite in {"all", "models"}:
                verify_result_chart_models(browser, args.url, args.output)
        finally:
            browser.close()
