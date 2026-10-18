"""Display-only formatter verification against a synthetic, API-free fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Browser, Locator, expect, sync_playwright

from app_readiness import diagnosed_page


def _geometry(chart: Locator) -> list[dict[str, str | None]]:
    return (
        chart.locator(".chart-frame-svg > g[clip-path]")
        .locator("circle, line, path")
        .evaluate_all(
            "nodes => nodes.map(node => Object.fromEntries("
            "['cx','cy','r','x1','x2','y1','y2','d'].map(key => "
            "[key, node.getAttribute(key)])))"
        )
    )


def verify_chart_formatting(browser: Browser, base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    requests: list[str] = []
    evidence: list[dict[str, object]] = []
    with diagnosed_page(browser, output, "chart-formatting", locale="ko") as page:
        page.set_viewport_size({"width": 1440, "height": 900})
        page.on(
            "request",
            lambda request: requests.append(request.url)
            if "/api/" in request.url
            else None,
        )
        page.goto(
            f"{base_url}/tests/chart-formatting.html", wait_until="domcontentloaded"
        )
        chart = page.locator('[data-chart-id="formatter"]')
        common = page.locator('[data-chart-id="common-formatter"]')
        expect(chart).to_be_visible()
        initial = _geometry(chart)
        numeric_charts = {
            name: page.locator(f'[data-chart-id="numeric-{name}"]')
            for name in ("narrow-positive", "large-origin", "narrow-negative")
        }
        numeric_geometry = {
            name: _geometry(item) for name, item in numeric_charts.items()
        }
        first = chart.get_by_role("img", name="Row 7", exact=True)
        first.click()
        expect(first).to_have_attribute("data-selected", "true")
        expect(chart.locator(".chart-selected-detail")).to_contain_text(
            "User \ue000name & <stored>"
        )
        expect(chart.locator(".chart-selected-detail")).to_contain_text("0.25")
        expect(page.get_by_test_id("select-count")).to_have_text("1")
        for locale in ("en", "ko"):
            page.get_by_role("button", name="ENG" if locale == "en" else "KOR").click()
            expect(page.locator("html")).to_have_attribute("data-app-locale", locale)
            page.get_by_label("Formatter policy").select_option("axis")
            labels = chart.locator(".chart-tick-label")
            expect(labels.filter(has_text=f"{locale}:1.0")).to_have_count(1)
            expect(labels.filter(has_text="-50%")).to_have_count(1)
            expect(chart.locator(".chart-visible-axis-title").first).to_contain_text(
                "X \ue000 & <stored> (s)"
            )
            expect(first).to_have_attribute("data-selected", "true")
            assert _geometry(chart) == initial

            page.get_by_label("Formatter policy").select_option("legacy")
            assert all(
                label.startswith("legacy:") for label in labels.all_text_contents()
            )
            assert _geometry(chart) == initial
            page.get_by_label("Formatter policy").select_option("common")
            expect(labels.filter(has_text="legacy:")).to_have_count(0)
            expect(
                common.locator(".chart-tick-label").filter(has_text="2,000")
            ).to_have_count(1)
            expect(
                common.locator(".chart-tick-label").filter(has_text="2e-8")
            ).to_have_count(1)
            assert _geometry(chart) == initial
            page.get_by_label("Formatter policy").select_option("explicit")
            expect(labels.filter(has_text="PC1 \ue000 & <stored>")).to_have_count(1)
            expect(labels.filter(has_text="PC1.5")).to_have_count(0)
            assert _geometry(chart) == initial
            expect(first).to_have_attribute("data-selected", "true")
            page.get_by_label("Formatter policy").select_option("axis")
            for width, height in [(1440, 900), (1280, 800), (1024, 768), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                expect(first).to_have_attribute("data-selected", "true")
                expect(page.get_by_test_id("select-count")).to_have_text("1")
                expect(page.get_by_test_id("source")).to_have_text("1")
                assert _geometry(chart) == initial
                for name, item in numeric_charts.items():
                    numeric_labels = item.locator(
                        '.chart-axes > g > text[text-anchor="middle"]'
                    ).all_text_contents()
                    assert len(numeric_labels) > 1 and len(set(numeric_labels)) == len(
                        numeric_labels
                    ), (name, numeric_labels)
                    assert _geometry(item) == numeric_geometry[name]
                    if name == "large-origin":
                        offset = item.locator('[data-axis="x"][data-axis-offset]')
                        expect(offset).to_have_attribute(
                            "data-axis-offset", "1000000000000"
                        )
                        expect(offset).to_contain_text("+1000000000000")
                        expect(offset.locator("title")).to_contain_text("mg/L")
                    for node in item.locator(".chart-tick-label").all():
                        box = node.bounding_box()
                        if box is not None:
                            assert (
                                box["x"] >= -1 and box["x"] + box["width"] <= width + 1
                            )
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 1"
                ), f"Page overflow at {locale}/{width}"
                first.focus()
                expect(page.get_by_role("tooltip")).to_contain_text("0.25")
                page.screenshot(
                    path=str(output / f"formatters-{locale}-{width}.png"),
                    full_page=True,
                )
                evidence.append(
                    {
                        "locale": locale,
                        "viewport": [width, height],
                        "coordinates_unchanged": True,
                        "pin_retained": True,
                        "narrow_numeric_ticks_distinct": True,
                        "large_origin_offset_visible": True,
                    }
                )
        first.press("Escape")
        expect(first).to_have_attribute("data-selected", "false")
        first.press("Enter")
        expect(first).to_have_attribute("data-selected", "true")
        expect(page.get_by_test_id("select-count")).to_have_text("2")
        page.get_by_role("button", name="Replace source").click()
        expect(page.get_by_test_id("source")).to_have_text("2")
        expect(first).to_have_attribute("data-selected", "false")
        assert _geometry(chart) == initial
        assert requests == [], "Display-only formatting must not call analysis APIs"
    (output / "formatter-evidence.json").write_text(
        json.dumps(
            {"fixture": "synthetic", "viewports": evidence, "api_requests": requests},
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            verify_chart_formatting(browser, args.base_url.rstrip("/"), args.output)
        finally:
            browser.close()
    print("Chart formatter browser checks passed")


if __name__ == "__main__":
    main()
