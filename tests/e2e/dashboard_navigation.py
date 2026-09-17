"""Dashboard navigation, bilingual layouts, and independent disclosure controls."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, expect


def verify_dashboard_navigation(page: Page, diagnostics: Any) -> None:
    original_url = page.url
    page.set_viewport_size({"width": 1440, "height": 900})
    page.locator(".brand-home-link").click()
    expect(page.locator(".home-quick-card .navigation-card-top")).to_have_count(6)
    expect(page.locator(".home-analysis-section .analysis-domain-card")).to_have_count(
        8
    )
    current_dataset = parse_qs(urlsplit(page.url).query).get("dataset_version_id")
    analysis = page.locator(".sidebar-group").filter(
        has=page.locator(".sidebar-group-control").filter(has_text=re.compile("^분석$"))
    )
    analysis.locator(".sidebar-group-control").click()
    expect(page).to_have_url(re.compile(r"/analysis(?:\?|$)"))
    expect(page.locator(".analysis-domain-card")).to_have_count(8)
    root_url = page.url
    toggle = analysis.locator(".sidebar-group-toggle")
    toggle.focus()
    page.keyboard.press("Enter")
    expect(toggle).to_have_attribute("aria-expanded", "false")
    assert page.url == root_url
    page.keyboard.press("Space")
    expect(toggle).to_have_attribute("aria-expanded", "true")
    page.locator(".brand-home-link").click()
    page.locator(".home-quick-card.is-analysis").click()
    assert page.url == root_url
    page.locator(".brand-home-link").click()
    page.locator(".home-analysis-section .analysis-domain-card").nth(3).click()
    expect(page).to_have_url(re.compile("domain=correlation-regression-prediction"))
    expect(page.locator("button.analysis-domain-method-card")).to_have_count(5)
    assert (
        parse_qs(urlsplit(page.url).query).get("dataset_version_id") == current_dataset
    )
    page.go_back()
    expect(page.locator(".home-quick-card")).to_have_count(6)
    page.go_forward()
    expect(page.locator("button.analysis-domain-method-card")).to_have_count(5)

    page.locator(".sidebar-group-control").filter(
        has_text=re.compile("^그래프$")
    ).click()
    expect(page).to_have_url(re.compile(r"/graphs(?:\?|$)"))
    expect(page.locator(".graph-type-button")).to_have_count(8)
    selected_color = page.locator(".graph-type-button.is-selected").evaluate(
        "e => getComputedStyle(e).backgroundColor"
    )
    assert selected_color == "rgb(34, 90, 167)"
    diagnostics.capture_page(page, "navigation-graph-types.png")

    for locale, language_button in (("ko", "KOR"), ("en", "ENG")):
        page.locator(".language-switcher button").filter(
            has_text=language_button
        ).click()
        for width, height in ((1440, 900), (1280, 800), (1024, 768), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            home = ".mobile-brand-home-link" if width < 761 else ".brand-home-link"
            page.locator(home).click()
            expect(page.locator(".home-quick-card")).to_have_count(6)
            expect(page.locator(".analysis-domain-card")).to_have_count(8)
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            assert page.locator(".home-quick-card, .analysis-domain-card").evaluate_all(
                "els => els.every(e => e.scrollWidth <= e.clientWidth + 1)"
            )
            if locale == "en":
                assert not re.search(
                    r"[가-힣]", page.locator(".home-analysis-section").inner_text()
                )
            diagnostics.capture_page(page, f"dashboard-refresh-{locale}-{width}.png")
            page.locator(".home-quick-card.is-analysis").click()
            expect(page.locator(".analysis-domain-card")).to_have_count(8)
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            diagnostics.capture_page(
                page, f"analysis-domain-refresh-{locale}-{width}.png"
            )
            for domain_index, expected_count in enumerate((4, 10, 3, 5, 3, 2, 5, 3)):
                page.locator(".analysis-domain-card").nth(domain_index).click()
                cards = page.locator("button.analysis-domain-method-card")
                expect(cards).to_have_count(expected_count)
                expect(page.locator(".analysis-domain-family-card")).to_have_count(0)
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                )
                assert cards.evaluate_all(
                    "els => els.every(e => e.scrollWidth <= e.clientWidth + 1)"
                )
                expect(page.locator(".analysis-domain-guide")).not_to_have_attribute(
                    "open", ""
                )
                if locale == "en":
                    assert not re.search(
                        r"[가-힣]",
                        page.locator(".analysis-domain-landing").inner_text(),
                    )
                diagnostics.capture_page(
                    page, f"unified-domain-{domain_index}-{locale}-{width}.png"
                )
                if width == 1440 and locale == "ko":
                    cards.first.click()
                    expect(page.locator("#workbench-title")).to_be_visible()
                    page.reload()
                    expect(page.locator("#workbench-title")).to_be_visible()
                    assert (
                        parse_qs(urlsplit(page.url).query).get("dataset_version_id")
                        == current_dataset
                    )
                    page.go_back()
                    expect(cards).to_have_count(expected_count)
                page.go_back()
                expect(page.locator(".analysis-domain-card")).to_have_count(8)

    page.set_viewport_size({"width": 390, "height": 844})
    page.locator(".language-switcher button").filter(has_text="KOR").click()
    page.get_by_role("button", name="주요 메뉴 열기").click()
    analysis.locator(".sidebar-group-control").click()
    expect(page.locator(".mobile-menu-toggle")).to_have_attribute(
        "aria-expanded", "false"
    )
    expect(page.locator(".mobile-menu-toggle")).to_be_focused()
    expect(page.locator(".analysis-domain-card")).to_have_count(8)
    page.set_viewport_size({"width": 1440, "height": 900})
    for locale, language in (("ko", "KOR"), ("en", "ENG")):
        page.locator(".language-switcher button").filter(has_text=language).click()
        menu = page.locator(".sidebar")
        for button in menu.locator('[data-node-kind="domain"] > button[aria-expanded]').all():
            if button.get_attribute("aria-expanded") == "false":
                button.click()
        for button in menu.locator('[data-node-kind="family"] > button[aria-expanded]').all():
            if button.is_visible() and button.get_attribute("aria-expanded") == "false":
                button.click()
        menu.locator('[data-node-kind="family"] [data-node-kind="method"] > button').first.click()
        leaf = menu.locator('[aria-current="page"]').last
        expect(leaf).to_be_visible()
        assert leaf.evaluate("e => getComputedStyle(e).fontWeight") == "600"
        ancestors = menu.locator(".is-active-ancestor")
        assert ancestors.count() >= 2
        assert all(button.evaluate("e => getComputedStyle(e).backgroundColor") !=
                   leaf.evaluate("e => getComputedStyle(e).backgroundColor") for button in ancestors.all())
        assert menu.locator('[role="tree"]').count() == 0
        diagnostics.capture_locator(menu, f"sidebar-expanded-hierarchy-{locale}.png")
    page.locator(".language-switcher button").filter(has_text="KOR").click()
    page.goto(original_url)
