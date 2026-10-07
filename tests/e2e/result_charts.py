from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import Browser, expect, sync_playwright


def verify_chart_interactions(browser: Browser, base_url: str, output: Path) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url) if "/api/" in request.url else None)
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
            chart.locator("svg").evaluate("(svg, scale) => { svg.style.width = `${440 * scale}px`; svg.style.maxWidth = 'none'; }", scale)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            verify_chart_interactions(browser, args.url, args.output)
        finally:
            browser.close()
