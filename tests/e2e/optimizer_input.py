"""Keyboard/caret/source checks on the actual optimizer, with synthetic data only."""

from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, Route, expect


def verify_optimizer_input(page: Page, output: Path) -> None:
    panel = page.locator('section[aria-labelledby="response-optimizer-title"]')
    page.locator("#optimizer-goal").select_option("target")
    original_url = page.url
    history_length = page.evaluate("history.length")
    page.locator("#optimizer-lower-weight").fill("1.5")
    page.locator("#optimizer-importance").fill("2")
    for locale, language in (("ko", "KOR"), ("en", "ENG")):
        page.locator(".language-switcher button").filter(has_text=language).click()
        expect(page.locator("html")).to_have_attribute("lang", locale)
        for width in (1024, 1280, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            for field in ("lower", "target", "upper"):
                control = page.locator(f"#optimizer-{field}")
                control.evaluate("el => el.dataset.inputMountProbe = 'same-node'")
                control.focus()
                control.press("ControlOrMeta+a")
                control.press("Backspace")
                expect(control).to_have_value("")
                control.press_sequentially("-")
                expect(control).to_have_value("-")
                control.press_sequentially("1.25")
                expect(control).to_have_value("-1.25")
                control.evaluate("el => el.setSelectionRange(2, 2)")
                control.press_sequentially("0")
                expect(control).to_have_value("-10.25")
                assert control.evaluate("el => el.selectionStart") == 3
                control.press("End")
                control.press("Backspace")
                control.press("Backspace")
                expect(control).to_have_value("-10.")
                control.fill("1e-")
                expect(control).to_have_value("1e-")
                control.press_sequentially("10")
                expect(control).to_have_value("1e-10")
                expect(control).to_be_focused()
                expect(control).to_have_attribute("data-input-mount-probe", "same-node")
            expect(page.locator("#optimizer-lower-weight")).to_have_value("1.5")
            expect(page.locator("#optimizer-importance")).to_have_value("2")
            assert page.url == original_url
            assert page.evaluate("history.length") == history_length
            box = panel.bounding_box()
            assert box and box["x"] + box["width"] <= width + 1
            factor_text = panel.locator(
                ".response-optimizer-factor-table tbody td:first-child"
            ).evaluate_all("""cells => cells.map(cell => {
                const bounds = cell.getBoundingClientRect();
                const range = document.createRange();
                range.selectNodeContents(cell);
                return {
                    left: bounds.left, right: bounds.right,
                    textRects: [...range.getClientRects()].map(rect => ({
                        left: rect.left, right: rect.right
                    }))
                };
            })""")
            assert factor_text
            for cell in factor_text:
                assert all(
                    rect["left"] >= cell["left"] - 1
                    and rect["right"] <= cell["right"] + 1
                    for rect in cell["textRects"]
                ), {"locale": locale, "viewport": width, "cell": cell}
        page.screenshot(path=str(output / f"optimizer-input-{locale}.png"), full_page=True)
        panel.screenshot(path=str(output / f"optimizer-input-panel-{locale}.png"))
    page.locator(".language-switcher button").filter(has_text="KOR").click()
    # Restore valid preferences explicitly; editing/resize/locale must never run search.
    page.locator("#optimizer-lower").fill("-100")
    page.locator("#optimizer-target").fill("20")
    page.locator("#optimizer-upper").fill("100")


def verify_optimizer_request_context(page: Page, base: str, design_id: str) -> dict:
    panel = page.locator('section[aria-labelledby="response-optimizer-title"]')
    acknowledgment = panel.locator(".inline-option input[type=checkbox]")
    if acknowledgment.count():
        acknowledgment.check()
    button = panel.get_by_role("button", name="Response Optimizer 실행", exact=True)
    expect(button).to_be_enabled()
    path = f"/api/v1/doe-designs/response-surface/{design_id}/optimizations"
    held: list[tuple[Route, dict]] = []

    def delay(route: Route) -> None:
        response = route.fetch()
        assert response.status == 201, response.text()
        held.append((route, response.json()))

    page.route("**" + path, delay)
    button.click()
    for _ in range(400):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "Optimizer response did not reach the synthetic delay fixture"
    page.locator("#optimizer-target").fill("21")
    pending, committed = held.pop()
    pending.fulfill(status=201, json=committed)
    expect(page.locator("#response-optimizer-result-title")).to_have_count(0)
    expect(button).to_be_enabled()
    restored = page.request.get(base + path + "/" + committed["optimization_id"])
    assert restored.status == 200 and restored.json() == committed
    page.unroute("**" + path)
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == path
    ) as pending:
        button.click()
    assert pending.value.status == 201, pending.value.text()
    result = pending.value.json()
    assert result["result"]["objectives"][0]["target"] == 21
    assert result["result"]["factor_region"]["region_mode"] == "axial_bounds"
    expect(page.locator("#response-optimizer-result-title")).to_be_visible()
    return result
