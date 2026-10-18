"""Read-only visual/interaction checks, also run against the isolated E2E workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Browser, Page, expect, sync_playwright

from app_readiness import diagnosed_page, wait_for_app_ready


def assert_no_overflow(page: Page) -> None:
    overflow = page.evaluate("document.documentElement.scrollWidth - innerWidth")
    assert overflow <= 1, f"{page.url}: horizontal overflow {overflow}px"


def create_refined_ui_fixture(browser: Browser, base_url: str) -> str:
    """Create only in the caller's isolated E2E workspace; use the returned ID."""
    context = browser.new_context(extra_http_headers={"Origin": base_url})
    try:
        response = context.request.post(
            base_url + "/api/v1/datasets",
            multipart={
                "file": {
                    "name": "synthetic-refined-ui.csv",
                    "mimeType": "text/csv",
                    "buffer": b"value,group\n1,A\n2,A\n3,A\n4,B\n5,B\n6,B\n",
                },
            },
        )
        assert response.status == 201, response.text()
        dataset_id = response.json()["dataset_id"]
        response = context.request.post(
            base_url + f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            data={
                "parsing": {
                    "kind": "delimited_text",
                    "encoding": "utf-8",
                    "delimiter": ",",
                    "quote_char": '"',
                    "decimal": ".",
                    "thousands": None,
                    "has_header": True,
                    "header_row": 1,
                    "data_start_row": 2,
                    "missing_tokens": ["", "NA"],
                },
                "columns": [],
            },
        )
        assert response.status == 201, response.text()
        return response.json()["version_id"]
    finally:
        context.close()


def verify_refined_ui(
    browser: Browser, base_url: str, root: Path, dataset_version_id: str
) -> None:
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
        with diagnosed_page(browser, root, locale, locale=locale) as page:
            _verify_locale(
                page, base_url, root, locale, routes, measurements, dataset_version_id
            )
    (root / "layout-measurements.json").write_text(
        json.dumps(measurements, indent=2), encoding="utf-8"
    )


def _verify_locale(
    page: Page,
    base_url: str,
    root: Path,
    locale: str,
    routes: dict[str, str],
    measurements: list,
    dataset_version_id: str,
) -> None:
    # Keep errors from this page, not the parent critical-path page.
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
            page.goto(base_url + route, wait_until="domcontentloaded")
            wait_for_app_ready(page, locale, route)
            expect(page.locator(".topbar .status-ready")).to_be_visible()
            if name == "datasets":
                limits = page.locator(".dataset-intake-limits")
                expect(limits).to_be_visible()
                expect(limits).to_contain_text("104,857,600")
                expect(limits).to_contain_text("1,048,576")
                expect(limits).to_contain_text("16,384")
            assert_no_overflow(page)
            if name.endswith("-domain"):
                guide = page.locator(".analysis-domain-guide")
                expect(guide).to_be_visible()
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
                    max(box["y"] for box in boxes) - min(box["y"] for box in boxes) < 2
                )
                assert max(box["y"] + box["height"] for box in boxes) < height
                measurements.append({"locale": locale, "width": width, "cards": boxes})
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(root / f"{name}-{locale}-{width}.png"))

        if width in (1440, 390):
            _verify_capability_help(page, base_url, root, locale, width)

        page.goto(
            base_url + "/analysis/hypothesis/hypothesis.two_sample_t",
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, locale, "/analysis/hypothesis/hypothesis.two_sample_t")
        selector = page.locator("#active-dataset-version")
        expect(
            selector.locator(f'option[value="{dataset_version_id}"]')
        ).to_be_attached()
        selector.select_option(dataset_version_id)
        panel = page.locator(".analysis-run-panel")
        alpha = panel.locator('input[type="number"]').first
        expect(alpha).to_be_visible()
        alpha.fill("0.1")
        page.evaluate("window.__uiRefinementSentinel = 'same-document'")
        current_url = page.url
        dataset_id = selector.input_value()
        navigation = page.locator(".analysis-method-navigation")
        expect(navigation).not_to_have_attribute("open", "")
        for grid in navigation.locator(".analysis-domain-method-grid").all():
            expect(grid).to_be_hidden()
        toggle = navigation.locator("summary").first
        toggle.focus()
        page.keyboard.press("Enter")
        expect(navigation).to_have_attribute("open", "")
        for grid in navigation.locator(".analysis-domain-method-grid").all():
            expect(grid).to_be_visible()
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
        if width < 1100:
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
    page.goto(base_url + "/graphs", wait_until="domcontentloaded")
    wait_for_app_ready(page, locale, "/graphs")
    page.locator("#active-dataset-version").select_option(dataset_version_id)
    graph = page.locator(".graph-type-button.is-selected")
    expect(graph).to_be_visible()
    selected_color = graph.evaluate("e => getComputedStyle(e).backgroundColor")
    assert selected_color == "rgb(34, 90, 167)"
    for selected in (
        ".language-switcher button.is-active",
        ".sidebar-group-active > .sidebar-group-heading",
    ):
        assert (
            page.locator(selected).evaluate("e => getComputedStyle(e).backgroundColor")
            == selected_color
        )
    page.screenshot(path=str(root / f"graph-selected-{locale}.png"))
    assert not failures, failures


def _verify_capability_help(
    page: Page, base_url: str, root: Path, locale: str, width: int
) -> None:
    cases = (
        ("eda.principal_components", "D"),
        (
            "doe.general_factorial_design",
            "multi-level" if locale == "en" else "수준",
        ),
        (
            "regression.predict",
            "Compatible saved regression model required"
            if locale == "en"
            else "호환되는 저장 회귀 모델 필요",
        ),
    )
    for method_id, expected_text in cases:
        route = f"/help?section=methods&method_id={method_id}"
        page.goto(base_url + route, wait_until="domcontentloaded")
        wait_for_app_ready(page, locale, route)
        detail = page.locator(".help-method-detail")
        expect(detail).to_be_visible()
        expect(detail).to_contain_text(expected_text)
        if method_id == "regression.predict":
            expect(
                detail.locator('[data-source-prerequisite="regression_model"]')
            ).to_be_visible()
        roadmap = page.locator('[data-help-roadmap="true"]')
        expect(roadmap).to_have_count(2)
        for item in roadmap.all():
            expect(item).to_contain_text(
                "Roadmap only" if locale == "en" else "로드맵 전용"
            )
            expect(item.get_by_role("button")).to_have_count(0)
        assert_no_overflow(page)
        page.screenshot(path=str(root / f"capability-{method_id}-{locale}-{width}.png"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8600")
    parser.add_argument("--dataset-version-id", required=True)
    parser.add_argument(
        "--diagnostics", type=Path, default=Path(".tmp/refined-ui/verified")
    )
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            verify_refined_ui(
                browser, args.url, args.diagnostics, args.dataset_version_id
            )
        finally:
            browser.close()
    print(
        "Refined UI checks passed (KOR/ENG, four viewports, state, colors, navigation)."
    )
