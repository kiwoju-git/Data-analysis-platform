from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Playwright, expect, sync_playwright


def _prepare(page: Page, url: str) -> str:
    page.goto(f"{url}/tests/desktop-resize.html", wait_until="networkidle")
    page.locator("#active-dataset-version").select_option("version-two")
    page.get_by_label("Draft value", exact=True).fill("retained synthetic draft")
    page.get_by_label("Loading component", exact=True).select_option("2")
    page.locator(
        '[data-chart-id="pls-loading"] .chart-page-controls button'
    ).last.click()
    point = page.locator('[data-chart-id="pca-score"] [tabindex]').first
    point.click()
    expect(point).to_have_attribute("data-selected", "true")
    return page.get_by_test_id("resize-content").get_attribute("data-instance") or ""


def _assert_retained(page: Page, instance: str) -> None:
    expect(page.get_by_test_id("resize-content")).to_have_attribute(
        "data-instance", instance
    )
    expect(page.locator("#active-dataset-version")).to_have_value("version-two")
    expect(page.get_by_label("Draft value", exact=True)).to_have_value(
        "retained synthetic draft"
    )
    expect(page.get_by_label("Loading component", exact=True)).to_have_value("2")
    expect(
        page.locator('[data-chart-id="pca-score"] [tabindex]').first
    ).to_have_attribute("data-selected", "true")
    expect(
        page.locator('[data-chart-id="pls-loading"] .chart-page-controls span')
    ).to_contain_text("13-24")
    expect(page.get_by_role("button", name="Run fixture", exact=True)).to_be_enabled()


def _geometry(page: Page) -> dict[str, Any]:
    result = page.evaluate("""() => {
      const scope = document.querySelector('.analysis-results-scope');
      const grid = document.querySelector('.analysis-result-grid');
      const table = document.querySelector('[data-testid="wide-table"]');
      return {
        width: innerWidth, height: innerHeight, devicePixelRatio,
        scrollWidth: document.documentElement.scrollWidth,
        shellDisplay: getComputedStyle(document.querySelector('.app-shell')).display,
        mainLeft: document.querySelector('.main').getBoundingClientRect().left,
        mainWidth: document.querySelector('.main').getBoundingClientRect().width,
        headerWidth: document.querySelector('.mobile-shell-header').getBoundingClientRect().width,
        scopeWidth: scope.getBoundingClientRect().width,
        scopeContentWidth: scope.clientWidth - parseFloat(getComputedStyle(scope).paddingLeft)
          - parseFloat(getComputedStyle(scope).paddingRight),
        gridColumns: getComputedStyle(grid).gridTemplateColumns.split(' ').length,
        tableClientWidth: table.clientWidth, tableScrollWidth: table.scrollWidth,
        charts: [...document.querySelectorAll('.chart-frame-svg')].map(svg => {
          const frame = svg.closest('.chart-frame').getBoundingClientRect();
          const box = svg.getBoundingClientRect();
          return { left: box.left, right: box.right, width: box.width, height: box.height,
            frameLeft: frame.left, frameRight: frame.right,
            radius: svg.querySelector('[tabindex]')?.getAttribute('r') ?? null };
        })
      };
    }""")
    assert result["scrollWidth"] <= result["width"] + 1, result
    if result["width"] < 1100:
        assert (
            result["shellDisplay"] == "block"
        ), "Narrow drawer must replace the two-column shell"
        assert result["mainLeft"] <= 1, result
        assert result["mainWidth"] >= result["width"] - 1, result
        assert result["headerWidth"] >= result["width"] - 1, result
    for chart in result["charts"]:
        assert chart["width"] > 0 and chart["height"] > 0
        assert chart["left"] >= chart["frameLeft"] - 1, chart
        assert chart["right"] <= chart["frameRight"] + 1, chart
        if chart["radius"] is not None:
            assert chart["radius"] == "3.5", chart
    assert result["tableScrollWidth"] >= 1200
    assert result["tableClientWidth"] <= result["width"]
    assert result["gridColumns"] in {1, 2}
    assert result["gridColumns"] == (
        2 if result["scopeContentWidth"] >= 900 else 1
    ), result
    return result


def _drawer_focus_cycle(page: Page) -> None:
    sidebar = page.locator("#application-sidebar")
    opener = page.locator(".mobile-menu-toggle")
    opener.click()
    expect(opener).to_have_attribute("aria-expanded", "true")
    expect(sidebar).to_have_attribute("aria-hidden", "false")
    expect(page.locator(".sidebar-scrim")).to_be_visible()
    focusable = sidebar.locator(
        'button:not(:disabled):visible, a[href]:visible, [tabindex]:not([tabindex="-1"]):visible'
    )
    first, last = focusable.first, focusable.last
    last.focus()
    last.press("Tab")
    expect(first).to_be_focused()
    first.press("Shift+Tab")
    expect(last).to_be_focused()
    last.press("Escape")
    expect(opener).to_have_attribute("aria-expanded", "false")
    expect(sidebar).to_have_attribute("aria-hidden", "true")
    expect(opener).to_be_focused()
    assert sidebar.evaluate("node => node.inert")
    opener.press("Tab")
    assert page.evaluate("!document.activeElement.closest('#application-sidebar')")


def verify_desktop_resize(browser: Browser, base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    errors: list[str] = []
    api_requests: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "request",
        lambda request: api_requests.append(request.url)
        if request.url.startswith(f"{base_url}/api/")
        else None,
    )
    report: dict[str, Any] = {
        "fixture": "real AppChrome with synthetic result components",
        "steps": [],
    }
    try:
        instance = _prepare(page, base_url)
        sidebar = page.locator("#application-sidebar")
        opener = page.locator(".mobile-menu-toggle")
        for index, width in enumerate((1920, 1440, 1280, 1024, 900, 768, 1440, 390)):
            page.set_viewport_size(
                {"width": width, "height": 900 if width > 390 else 844}
            )
            page.wait_for_timeout(100)
            _assert_retained(page, instance)
            if width < 1100:
                expect(opener).to_be_visible()
                expect(sidebar).to_have_attribute("aria-hidden", "true")
                _drawer_focus_cycle(page)
            else:
                expect(opener).not_to_be_visible()
                expect(sidebar).to_have_attribute("aria-hidden", "false")
                assert not sidebar.evaluate("node => node.inert")
            dimensions = _geometry(page)
            if width == 1920:
                assert dimensions["gridColumns"] == 2
            if width < 900:
                assert dimensions["gridColumns"] == 1
            page.mouse.move(0, 0)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(
                path=str(output / f"desktop-resize-{index}-{width}.png"), full_page=True
            )
            report["steps"].append(dimensions)

        page.set_viewport_size({"width": 1024, "height": 768})
        opener.click()
        expect(sidebar).to_have_attribute("aria-hidden", "false")
        sidebar.locator('[aria-current="page"]').click()
        expect(opener).to_have_attribute("aria-expanded", "false")
        expect(page.get_by_test_id("navigation-count")).to_have_text("1")
        opener.click()
        expect(opener).to_have_attribute("aria-expanded", "true")
        page.set_viewport_size({"width": 1440, "height": 900})
        expect(opener).to_have_attribute("aria-expanded", "false")
        expect(opener).not_to_be_visible()
        expect(page.locator(".sidebar-scrim")).to_have_count(0)
        assert page.evaluate(
            "document.activeElement !== document.querySelector('.mobile-menu-toggle')"
        )
        last = sidebar.locator("button:not(:disabled):visible, a[href]:visible").last
        last.focus()
        last.press("Tab")
        assert page.evaluate(
            "!document.activeElement.closest('#application-sidebar')"
        ), "Drawer trap leaked into wide layout"
        _assert_retained(page, instance)
        page.get_by_role("button", name="Run fixture", exact=True).click()
        expect(page.get_by_test_id("run-count")).to_have_text("1")
        assert api_requests == [], api_requests
        assert errors == [], errors
        report["status"] = "passed"
        report["focus"] = (
            "narrow Tab wrap, Escape return, navigation close, wide trap cleanup passed"
        )
        (output / "desktop-resize-validation.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    except Exception:
        page.screenshot(path=str(output / "desktop-resize-failure.png"), full_page=True)
        raise
    finally:
        context.close()


def verify_real_browser_zoom(
    playwright: Playwright, base_url: str, output: Path
) -> None:
    """Use Chromium's tab zoom API, not deviceScaleFactor or CSS scale."""
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="datalab-zoom-browser-") as temporary:
        root = Path(temporary)
        extension = root / "extension"
        extension.mkdir()
        (extension / "manifest.json").write_text(
            json.dumps(
                {
                    "manifest_version": 3,
                    "name": "Synthetic browser zoom verification",
                    "version": "1.0",
                    "permissions": ["tabs"],
                    "background": {"service_worker": "worker.js"},
                }
            ),
            encoding="utf-8",
        )
        (extension / "worker.js").write_text(
            "chrome.runtime.onInstalled.addListener(() => {});", encoding="utf-8"
        )
        context = playwright.chromium.launch_persistent_context(
            str(root / "profile"),
            channel="chromium",
            headless=True,
            viewport={"width": 1440, "height": 900},
            args=[
                f"--disable-extensions-except={extension}",
                f"--load-extension={extension}",
            ],
        )
        try:
            worker = (
                context.service_workers[0]
                if context.service_workers
                else context.wait_for_event("serviceworker")
            )
            page = context.new_page()
            instance = _prepare(page, base_url)
            report: dict[str, Any] = {
                "mechanism": "chrome.tabs.setZoom/getZoom",
                "deviceScaleFactor_override": False,
                "steps": [],
            }
            for factor in (1.0, 1.25, 1.5, 1.0):
                actual = worker.evaluate(
                    """async ({url, factor}) => {
                    const tabs = await chrome.tabs.query({});
                    const tab = tabs.find(tab => tab.url?.startsWith(url));
                    if (!tab) throw new Error('Fixture tab missing');
                    await chrome.tabs.setZoomSettings(tab.id, {mode: 'automatic', scope: 'per-tab'});
                    await chrome.tabs.setZoom(tab.id, factor);
                    return chrome.tabs.getZoom(tab.id);
                }""",
                    {"url": f"{base_url}/tests/desktop-resize.html", "factor": factor},
                )
                assert abs(actual - factor) < 1e-9
                page.wait_for_function(
                    "expected => Math.abs(innerWidth - expected) <= 2",
                    arg=1440 / factor,
                )
                _assert_retained(page, instance)
                dimensions = _geometry(page)
                dimensions["browserZoom"] = actual
                report["steps"].append(dimensions)
                page.mouse.move(0, 0)
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(
                    path=str(
                        output / f"desktop-browser-zoom-{round(factor * 100)}.png"
                    ),
                    full_page=True,
                )
            report["status"] = "passed"
            (output / "desktop-browser-zoom-validation.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
        finally:
            context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-zoom", action="store_true")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            verify_desktop_resize(browser, args.url, args.output)
        finally:
            browser.close()
        if not args.skip_zoom:
            verify_real_browser_zoom(playwright, args.url, args.output)
