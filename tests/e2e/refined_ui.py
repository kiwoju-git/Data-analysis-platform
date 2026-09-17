"""Read-only visual/interaction checks, also run against the isolated E2E workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Browser, Page, expect, sync_playwright


def assert_no_overflow(page: Page) -> None:
    overflow = page.evaluate("document.documentElement.scrollWidth - innerWidth")
    assert overflow <= 1, f"{page.url}: horizontal overflow {overflow}px"


def verify_refined_ui(browser: Browser, base_url: str, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    measurements = []
    routes = {
        "home": "/",
        "datasets": "/datasets",
        "domain-root": "/analysis",
        "regression-domain": "/analysis?domain=correlation-regression-prediction",
        "mean-domain": "/analysis?domain=mean-equivalence",
        "doe-domain": "/analysis?domain=doe-optimization",
        "graphs": "/graphs",
        "reports": "/reports",
        "manage": "/manage",
        "help": "/help",
    }
    for locale in ("en", "ko"):
        context = browser.new_context()
        context.add_init_script(
            f"localStorage.setItem('statistical-twin.locale', '{locale}')"
        )
        page = context.new_page()
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))
        for width, height in ((1440, 900), (1280, 800), (1024, 768), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            for name, route in routes.items():
                if width in (1280, 1024) and name not in (
                    "domain-root",
                    "regression-domain",
                ):
                    continue
                page.goto(base_url + route, wait_until="networkidle")
                expect(page.locator("html")).to_have_attribute("lang", locale)
                expect(page.locator(".topbar .status-ready")).to_be_visible()
                assert_no_overflow(page)
                if "domain" in name:
                    guide = page.locator(".analysis-domain-guide")
                    if guide.count():
                        expect(guide).not_to_have_attribute("open", "")
                        guide.locator("summary").focus()
                        page.keyboard.press("Enter")
                        expect(guide).to_have_attribute("open", "")
                        page.keyboard.press("Enter")
                if name == "regression-domain" and width == 1440:
                    cards = page.locator(".analysis-domain-method-grid > button")
                    expect(cards).to_have_count(5)
                    boxes = [card.bounding_box() for card in cards.all()]
                    assert (
                        max(box["y"] for box in boxes) - min(box["y"] for box in boxes)
                        < 2
                    )
                    assert max(box["y"] + box["height"] for box in boxes) < height
                    measurements.append(
                        {"locale": locale, "width": width, "cards": boxes}
                    )
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(path=str(root / f"{name}-{locale}-{width}.png"))

            page.goto(
                base_url + "/analysis/hypothesis/hypothesis.two_sample_t",
                wait_until="networkidle",
            )
            selector = page.locator("#active-dataset-version")
            expect(selector.locator("option").nth(1)).to_be_attached()
            selector.select_option(index=1)
            panel = page.locator(".analysis-run-panel")
            alpha = panel.locator('input[type="number"]').first
            expect(alpha).to_be_visible()
            alpha.fill("0.1")
            page.evaluate("window.__uiRefinementSentinel = 'same-document'")
            current_url = page.url
            dataset_id = selector.input_value()
            navigation = page.locator(".analysis-method-navigation")
            expect(navigation).not_to_have_attribute("open", "")
            expect(navigation.locator(".analysis-domain-method-grid")).to_be_hidden()
            toggle = navigation.locator("summary").first
            toggle.focus()
            page.keyboard.press("Enter")
            expect(navigation).to_have_attribute("open", "")
            expect(navigation.locator(".analysis-domain-method-grid")).to_be_visible()
            toggle.press("Space")
            expect(navigation).not_to_have_attribute("open", "")
            toggle.press("Tab")
            expect(page.locator(".workbench-heading-actions button")).to_be_focused()
            expect(alpha).to_have_value("0.1")
            other_locale = "ko" if locale == "en" else "en"
            page.locator(".language-switcher button").filter(
                has_text="KOR" if other_locale == "ko" else "ENG"
            ).click()
            expect(page.locator("html")).to_have_attribute("lang", other_locale)
            expect(alpha).to_have_value("0.1")
            assert page.url == current_url
            assert selector.input_value() == dataset_id
            assert page.evaluate("window.__uiRefinementSentinel") == "same-document"
            page.locator(".language-switcher button").filter(
                has_text="ENG" if locale == "en" else "KOR"
            ).click()
            title = page.locator(".workbench-heading-main").bounding_box()
            actions = page.locator(".workbench-heading-actions").bounding_box()
            strip = page.locator(".workbench-method-context-strip").bounding_box()
            assert strip["y"] >= max(
                title["y"] + title["height"], actions["y"] + actions["height"]
            )
            if width > 760:
                assert abs(title["y"] - actions["y"]) < 2
            else:
                menu = page.locator(".mobile-menu-toggle")
                menu.click()
                expect(menu).to_have_attribute("aria-expanded", "true")
                expect(
                    page.locator('.sidebar-method-button[aria-current="page"]')
                ).to_be_visible()
                page.keyboard.press("Escape")
                expect(menu).to_be_focused()
            assert_no_overflow(page)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(root / f"workbench-{locale}-{width}.png"))

        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(base_url + "/graphs", wait_until="networkidle")
        page.locator("#active-dataset-version").select_option(index=1)
        graph = page.locator(".graph-type-button.is-selected")
        expect(graph).to_be_visible()
        selected_color = graph.evaluate("e => getComputedStyle(e).backgroundColor")
        assert selected_color == "rgb(34, 90, 167)"
        for selected in (
            ".language-switcher button.is-active",
            ".sidebar-group-active > .sidebar-group-heading",
        ):
            assert (
                page.locator(selected).evaluate(
                    "e => getComputedStyle(e).backgroundColor"
                )
                == selected_color
            )
        page.screenshot(path=str(root / f"graph-selected-{locale}.png"))
        assert not failures, failures
        context.close()
    (root / "layout-measurements.json").write_text(
        json.dumps(measurements, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8600")
    parser.add_argument(
        "--diagnostics", type=Path, default=Path(".tmp/refined-ui/verified")
    )
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            verify_refined_ui(browser, args.url, args.diagnostics)
        finally:
            browser.close()
    print(
        "Refined UI checks passed (KOR/ENG, four viewports, state, colors, navigation)."
    )
