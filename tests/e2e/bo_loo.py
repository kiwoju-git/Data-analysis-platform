"""Built-app exact diagnostic value, localization, download and source-lane checks."""

import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from app_readiness import wait_for_layout_settled
from playwright.sync_api import expect


def verify_loo(page, api: str, model: dict, output: Path, *, mixed: bool = False) -> dict:
    family = "/mixed-planning-models/" if mixed else "/planning-models/"
    model_url = api + family + model["model_id"]
    endpoint = model_url + "/loo"
    before = page.request.get(api).json()
    before_model = page.request.get(model_url).json()
    requests = []

    def record(request):
        if "/api/" in request.url and request.method in {"POST", "PUT", "DELETE"}:
            requests.append(request.url)

    page.on("request", record)
    panel = page.get_by_role("region", name="Saved-model LOO diagnostics", exact=True)
    with page.expect_response(endpoint, timeout=90000) as calculated:
        panel.get_by_role("button", name="Calculate LOO", exact=True).click()
    assert calculated.value.status == 200, calculated.value.text()
    view = calculated.value.json()
    expect(panel.get_by_role("button", name="Download diagnostic JSON")).to_be_enabled()
    assert view["model_sha256"] == model["snapshot_sha256"]
    assert view["history_sha256"] == model["history_sha256"]
    for response in view["calculation"]["responses"]:
        definition = next(row for row in model["objective"]["responses"] if row["response_id"] == response["response_id"])
        section = panel.get_by_role("region", name=definition["name"], exact=True)
        for point in response["points"]:
            marker = section.locator(f'.bo-loo-observed [data-point-id="{point["trial_id"]}"]')
            expect(marker).to_have_count(1)
            assert float(marker.get_attribute("data-x")) == point["predicted"]
            assert float(marker.get_attribute("data-y")) == point["observed"]
            residual = section.locator(f'.bo-loo-residual [data-point-id="{point["trial_id"]}"]')
            expect(residual).to_have_count(1)
            assert float(residual.get_attribute("data-x")) == point["predicted"]
            assert float(residual.get_attribute("data-y")) == point["residual"]
        zero = section.locator('.bo-loo-residual line[data-y1="0"][data-y2="0"]')
        expect(zero).to_have_count(1)
        for chart in (".bo-loo-observed", ".bo-loo-residual"):
            first = section.locator(f"{chart} [data-point-id]").first
            first.focus()
            first.press("Enter")
            expect(first).to_have_attribute("data-selected", "true")
            first.press("Escape")
            expect(first).to_have_attribute("data-selected", "false")
    for locale, language, title in (
        ("ko", "KOR", "저장 모형 LOO 진단"),
        ("en", "ENG", "Saved-model LOO diagnostics"),
    ):
        page.locator(".language-switcher button").filter(has_text=language).click()
        expect(page.locator("html")).to_have_attribute("lang", locale)
        translated = page.get_by_role("region", name=title, exact=True)
        for width in (1024, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            wait_for_layout_settled(page)
            assert translated.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
            assert translated.locator("svg [data-point-id]").count() == 2 * sum(len(row["points"]) for row in view["calculation"]["responses"])
            translated.screenshot(path=output / f"loo-{locale}-{width}.png")
    with page.expect_download() as download:
        panel.get_by_role("button", name="Download diagnostic JSON", exact=True).click()
    assert json.loads(Path(download.value.path()).read_text(encoding="utf-8")) == view
    assert requests == [endpoint], requests
    assert page.request.get(model_url).json() == before_model
    assert page.request.get(api).json() == before
    page.remove_listener("request", record)
    if not mixed:
        verify_source_lane(page, api, model, view, endpoint)
    (output / "loo-receipt.json").write_text(json.dumps(view, indent=2), encoding="utf-8")
    return view


def verify_source_lane(page, api: str, model: dict, view: dict, endpoint: str) -> None:
    # A second real model is only synthetic test setup, not a fabricated response.
    parsed = urlsplit(api)
    base = f"{parsed.scheme}://{parsed.netloc}"
    second = page.request.post(api + "/planning-models", headers={"Origin": base}, data={"request_id": str(uuid4()), "fit": model["fit"]})
    assert second.status == 201, second.text()
    other = second.json()
    parent = page.get_by_role("region", name="Saved model, candidates and profiler", exact=True)
    parent.get_by_role("button", name="Refresh saved sources", exact=True).click()
    select = parent.get_by_label("Saved models", exact=True)
    expect(select.locator(f'option[value="{other["model_id"]}"]')).to_have_count(1)
    panel = page.get_by_role("region", name="Saved-model LOO diagnostics", exact=True)
    for old_error in (False, True):
        held = []
        page.route(endpoint, lambda route: held.append(route))
        panel.get_by_role("button", name="Calculate LOO", exact=True).click()
        expect(panel.get_by_text("Calculating LOO", exact=True)).to_be_visible()
        assert len(held) == 1
        select.select_option(other["model_id"])
        expect(select).to_have_value(other["model_id"])
        expect(parent.get_by_text(other["snapshot_sha256"], exact=True).first).to_be_attached()
        expect(panel.get_by_role("button", name="Download diagnostic JSON")).to_have_count(0)
        expect(panel.locator(".bo-loo-residual")).to_have_count(0)
        select.select_option(model["model_id"])
        expect(select).to_have_value(model["model_id"])
        expect(parent.get_by_text(model["snapshot_sha256"], exact=True).first).to_be_attached()
        panel.get_by_role("button", name="Calculate LOO", exact=True).click()
        expect(panel.get_by_text("Calculating LOO", exact=True)).to_be_visible()
        assert len(held) == 2
        held[0].fulfill(status=409 if old_error else 200, json={"error": {"code": "synthetic_late_failure"}} if old_error else view)
        expect(panel.get_by_text("Calculating LOO", exact=True)).to_be_visible()
        expect(panel.get_by_role("alert")).to_have_count(0)
        expect(panel.get_by_role("button", name="Download diagnostic JSON")).to_have_count(0)
        expect(panel.locator(".bo-loo-residual")).to_have_count(0)
        held[1].fulfill(json=view)
        expect(panel.get_by_role("button", name="Download diagnostic JSON")).to_be_visible()
        expect(panel.locator(".bo-loo-residual")).to_have_count(len(view["calculation"]["responses"]))
        page.unroute(endpoint)
