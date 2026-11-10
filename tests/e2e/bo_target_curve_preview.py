"""Built-app, synthetic curve comparison. No study or observation is created."""

import argparse
import json
import math
from pathlib import Path

from app_readiness import (
    diagnosed_page,
    wait_for_bayesian_ready,
    wait_for_layout_settled,
)
from playwright.sync_api import Browser, expect, sync_playwright

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def verify_target_curve_preview(browser: Browser, base: str, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "target-curve",
        init_script="""
        localStorage.setItem('statistical-twin.locale', 'en');
    """,
    ) as page:
        errors, writes = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda r: writes.append(r.url)
            if "/api/" in r.url and r.method == "POST"
            else None,
        )
        page.goto(base + ROUTE, wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        page.locator("#bayesian-response-mode").select_option("vector")
        goals = page.get_by_role("region", name="Response goals", exact=True)
        goals.get_by_label("Response 1 name", exact=True).fill("측정 <raw>")
        goals.get_by_label("Response 1 goal", exact=True).select_option("match_target")
        for field, value in [("lower", "-1"), ("target", "0"), ("upper", "1")]:
            goals.get_by_label("Response 1 " + field, exact=True).fill(value)
        panel = page.locator(".bo-curve-preview")
        panel.locator("summary").first.click()
        panel.get_by_label("Target response", exact=True).select_option(
            label="측정 <raw>"
        )
        for field in ("lower", "upper"):
            panel.get_by_label(f"Desirability at {field} control", exact=True).fill(
                str(math.exp(-1))
            )
        panel.get_by_label(
            "Compare an explicitly assumed Gaussian distribution", exact=True
        ).check()
        button = panel.get_by_role("button", name="Compare curves", exact=True)
        expect(button).to_be_disabled()
        for label, value in [
            ("Assumed mean (response unit)", "0"),
            ("Assumed SD (response unit)", "1"),
            ("Assumed incumbent (desirability)", "0.5"),
        ]:
            panel.get_by_label(label, exact=True).fill(value)
        endpoint = base + "/api/v1/bayesian-studies/target-curve-preview"
        held = []

        def hold(route):
            held.append(route)

        page.route(endpoint, hold)
        button.click()
        expect(
            panel.get_by_role("button", name="Comparing...", exact=True)
        ).to_be_visible()
        assert len(held) == 1
        # Programmatic source A-B-A must invalidate, not only changed final values.
        source = goals.get_by_label("Response 1 target", exact=True)
        source.fill("0.2")
        source.fill("0")
        old = held[0].fetch()
        assert old.status == 200
        held[0].fulfill(response=old)
        page.unroute(endpoint, hold)
        expect(panel.locator("section")).to_have_count(0)
        expect(button).to_be_enabled()
        with page.expect_response(endpoint) as done:
            button.click()
        assert done.value.status == 200, done.value.text()
        result = done.value.json()
        assert abs(result["metrics"][0]["mean"] - 1 / math.sqrt(3)) < 2e-14
        assert (
            abs(result["metrics"][0]["variance"] - (1 / math.sqrt(5) - 1 / 3)) < 2e-14
        )
        expect(
            panel.get_by_role(
                "table", name="Assumed-distribution comparison", exact=True
            )
        ).to_contain_text(str(result["metrics"][0]["mean"]))
        # Common chart uses data-x/data-y for the original values, not CSS coordinates.
        plotted = panel.locator("[data-x][data-y]").evaluate_all(
            "es => es.map(e => [Number(e.dataset.x), Number(e.dataset.y)])"
        )
        assert [0, 1] in plotted
        assert any(x == -1 and abs(y - math.exp(-1)) < 1e-14 for x, y in plotted)
        point = panel.locator('[tabindex="0"][data-x][data-y]').first
        point.focus()
        point.press("Enter")
        point.press("Escape")
        before = len(writes)
        layouts = []
        for locale, button_name in (("en", "ENG"), ("ko", "KOR"), ("en", "ENG")):
            page.locator(".language-switcher button").filter(
                has_text=button_name
            ).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            expect(panel).to_contain_text("측정 <raw>")
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                wait_for_layout_settled(page)
                box = panel.bounding_box()
                assert box and box["x"] >= 0 and box["x"] + box["width"] <= width + 1
                layouts.append(
                    {"locale": locale, "viewport": width, "content": box["width"]}
                )
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(
                    path=str(output / f"target-{locale}-{width}.png"), full_page=True
                )
        assert len(writes) == before
        assert all(url == endpoint for url in writes)
        expect(source).to_have_value("0")
        # Explicit network failure does not retry or hide the draft.
        panel.get_by_label("Assumed mean (response unit)", exact=True).fill("0.1")
        page.route(endpoint, lambda route: route.abort())
        button.click()
        expect(panel.get_by_role("alert")).to_be_visible()
        count = len(writes)
        page.set_viewport_size({"width": 1280, "height": 1000})
        wait_for_layout_settled(page)
        assert len(writes) == count
        page.unroute(endpoint)
        panel.get_by_label(
            "Compare an explicitly assumed Gaussian distribution", exact=True
        ).uncheck()
        for field in ("lower", "upper"):
            panel.get_by_label(f"Desirability at {field} control", exact=True).fill(
                "1e-300"
            )
        with page.expect_response(endpoint) as underflow:
            button.click()
        assert underflow.value.json()["gaussian_underflow_count"] > 0
        expect(panel).to_contain_text("they are not exact zero preferences")
        assert not errors, errors
        receipt = {
            "synthetic": True,
            "browser": browser.version,
            "api": page.request.get(base + "/api/v1/runtime-info").json()[
                "api_contract_version"
            ],
            "source_aba_ignored": True,
            "explicit_failure_no_retry": True,
            "no_persistent_post": True,
            "tail_underflow_explicit": True,
            "locale_resize_no_request": True,
            "independent_moments": result["metrics"][0],
            "layouts": layouts,
            "pageerrors": errors,
        }
        (output / "target-curve-receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            print(
                json.dumps(
                    verify_target_curve_preview(browser, args.base_url, args.output),
                    indent=2,
                )
            )
        finally:
            browser.close()
