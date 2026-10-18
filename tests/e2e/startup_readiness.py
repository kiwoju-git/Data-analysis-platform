"""Synthetic cold-start, blocked storage and failed/slow module browser checks."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Browser, expect

from app_readiness import diagnosed_page, wait_for_app_ready


def verify_startup_readiness(browser: Browser, base_url: str, root: Path) -> None:
    scenarios = {
        "empty": (None, "en"),
        "saved-ko": ("localStorage.setItem('statistical-twin.locale', 'ko')", "ko"),
        "invalid": ("localStorage.setItem('statistical-twin.locale', 'invalid')", "en"),
        "getter-denied": (
            """Object.defineProperty(window, 'localStorage', {
            get() { throw new DOMException('private storage details', 'SecurityError'); }
        })""",
            "en",
        ),
        "get-item-denied": (
            """Storage.prototype.getItem = () => {
            throw new DOMException('private storage details', 'SecurityError');
        }""",
            "en",
        ),
        "set-item-denied": (
            """Storage.prototype.setItem = () => {
            throw new DOMException('private storage details', 'SecurityError');
        }""",
            "en",
        ),
    }
    for name, (script, locale) in scenarios.items():
        with diagnosed_page(browser, root, name, init_script=script) as page:
            page.goto(base_url + "/help", wait_until="domcontentloaded")
            wait_for_app_ready(page, locale, "/help")
            search = page.locator(".help-search-field input")
            search.fill("regression")
            other = "ko" if locale == "en" else "en"
            page.locator(".language-switcher button").filter(
                has_text="KOR" if other == "ko" else "ENG"
            ).click()
            wait_for_app_ready(page, other, "/help")
            expect(search).to_have_value("regression")
            expect(page.locator("body")).not_to_contain_text("private storage details")
            page.screenshot(path=str(root / name / "switched.png"))
            # A blocked store can only keep locale in memory, not across reloads.
            if name in ("empty", "getter-denied", "get-item-denied", "set-item-denied"):
                page.reload(wait_until="domcontentloaded")
                wait_for_app_ready(page, other if name == "empty" else "en", "/help")

    with diagnosed_page(browser, root, "slow-app-module", locale="ko") as page:
        held = []
        page.route("**/src/App.tsx*", lambda route: held.append(route))
        page.goto(base_url + "/home", wait_until="domcontentloaded")
        expect(page.locator('[data-app-startup="loading"]')).to_be_visible()
        expect(page.locator('[data-runtime-state="compatible"]')).to_have_count(0)
        page.wait_for_function("document.documentElement.dataset.appLocale === 'ko'")
        assert held, "App import must be deferred until the startup boundary mounts"
        for route in held:
            route.continue_()
        wait_for_app_ready(page, "ko", "/home")

    with diagnosed_page(browser, root, "runtime-pending", locale="en") as page:
        held = []
        page.route("**/api/v1/runtime-info", lambda route: held.append(route))
        page.goto(base_url + "/home", wait_until="domcontentloaded")
        expect(page.locator('[data-runtime-state="checking"]')).to_be_visible()
        expect(page.locator(".app-shell")).to_have_count(0)
        for route in held:
            route.continue_()
        page.unroute("**/api/v1/runtime-info")
        wait_for_app_ready(page, "en", "/home")

    with diagnosed_page(browser, root, "catalog-pending", locale="en") as page:
        held = []
        page.route("**/api/v1/analysis-methods", lambda route: held.append(route))
        route_path = "/analysis?domain=mean-equivalence"
        page.goto(base_url + route_path, wait_until="domcontentloaded")
        expect(page.locator(".app-shell")).to_be_visible()
        expect(page.locator("#analysis-modules-title")).to_be_visible()
        expect(page.locator(".analysis-domain-landing")).to_have_count(0)
        assert held
        # A deliberately failed readiness assertion must identify the absent
        # landing, even though the page title and runtime are already ready.
        try:
            wait_for_app_ready(page, "en", route_path, timeout_ms=250)
        except AssertionError as error:
            assert "data-domain-id" in str(error)
        else:
            raise AssertionError("An unloaded domain must not be reported ready")
        for route in held:
            route.continue_()
        wait_for_app_ready(page, "en", route_path)

    for name, rendering_error in (
        ("failed-app-module", False),
        ("initial-render-error", True),
    ):
        with diagnosed_page(
            browser, root, name, locale="ko", allow_page_errors=True
        ) as page:
            if rendering_error:
                page.route(
                    "**/src/App.tsx*",
                    lambda route: route.fulfill(
                        content_type="application/javascript",
                        body="export default function App() { throw new Error('private render details'); }",
                    ),
                )
            else:
                page.route("**/src/App.tsx*", lambda route: route.abort())
            page.goto(base_url + "/home", wait_until="domcontentloaded")
            error = page.locator('[data-app-startup="failed"]')
            expect(error).to_be_visible()
            expect(error.get_by_role("button")).to_be_visible()
            expect(error).not_to_contain_text("private render details")
            expect(error).not_to_contain_text("Failed to fetch")
            page.screenshot(path=str(root / name / "error.png"))
            page.unroute("**/src/App.tsx*")
            error.get_by_role("button").click()
            wait_for_app_ready(page, "ko", "/home")

    # Exercise the diagnostics failure path deliberately; the suite must preserve
    # the original exception and capture this child, not a parent browser page.
    sentinel = "synthetic_child_diagnostic_probe"
    try:
        with diagnosed_page(browser, root, "diagnostic-probe", locale="ko") as page:
            page.goto(base_url + "/help", wait_until="domcontentloaded")
            wait_for_app_ready(page, "ko", "/help")
            raise AssertionError(sentinel)
    except AssertionError as error:
        assert str(error) == sentinel
    evidence = json.loads(
        (root / "diagnostic-probe/failure.json").read_text(encoding="utf-8")
    )
    assert evidence["url"].endswith("/help")
    assert evidence["document"]["lang"] == "ko"
    assert evidence["document"]["runtime"] == "compatible"
    for filename in ("trace.zip", "failure.png", "failure.html"):
        assert (root / "diagnostic-probe" / filename).is_file()
