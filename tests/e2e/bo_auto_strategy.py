"""Built UI advice, exact source, late responses and explicit review; synthetic only."""

import json
from pathlib import Path

from app_readiness import wait_for_layout_settled
from playwright.sync_api import expect


def verify_auto_strategy(page, api: str, model: dict, output: Path, *, mixed=False, keep_selection=False):
    parent = page.get_by_role("region", name=(
        "Mixed-factor candidates and planning" if mixed else "Experimental augmentation"
    ), exact=True)
    family = "/mixed-planning-models/" if mixed else "/planning-models/"
    model_url = api + family + model["model_id"]
    endpoint = model_url + "/auto-strategy"
    before = page.request.get(api).json()
    if not mixed:
        parent.get_by_role("button", name="Refresh saved sources", exact=True).click()
        models = parent.get_by_label("Saved models", exact=True)
        expect(models.locator(f'option[value="{model["model_id"]}"]')).to_have_count(1)
        models.select_option(model["model_id"])
        parent.get_by_label("Candidate table name", exact=True).fill("Synthetic Auto advice")
        parent.get_by_label("Uniform candidates (1–10000)", exact=True).fill("32")
        with page.expect_response(api + "/candidate-revisions", timeout=90000) as created:
            parent.get_by_role("button", name="Generate new table", exact=True).click()
        assert created.value.status == 201, created.value.text()
    panel = parent.get_by_role("region", name="Auto strategy advice", exact=True)
    expect(panel).to_be_visible()
    writes = []

    def record(request):
        if "/api/" in request.url and request.method in {"POST", "PUT", "DELETE"}:
            writes.append(request.url)

    page.on("request", record)

    def calculate():
        with page.expect_response(endpoint, timeout=90000) as response:
            panel.get_by_role("button", name="Suggest strategy", exact=True).click()
        assert response.value.status == 200, response.value.text()
        expect(panel.get_by_role("button", name="Apply suggested strategy", exact=True)).to_be_enabled()
        return response.value.json()

    view = calculate()
    for row, metric in zip(panel.locator("tbody tr").all(), view["diagnostic"]["calculation"]["responses"], strict=True):
        assert float(row.locator("td").inner_text()) == metric["r_squared"]
    for locale, button, title in (("ko", "KOR", "Auto 전략 제안"), ("en", "ENG", "Auto strategy advice")):
        page.locator(".language-switcher button").filter(has_text=button).click()
        expect(page.locator("html")).to_have_attribute("lang", locale)
        translated = parent.get_by_role("region", name=title, exact=True) if locale == "en" else page.get_by_role("region", name=title, exact=True)
        for width in (1024, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            wait_for_layout_settled(page)
            assert translated.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
            translated.screenshot(path=output / f"auto-{locale}-{width}.png")
    assert writes == [endpoint]
    with page.expect_download() as downloaded:
        panel.get_by_role("button", name="Download Auto advice JSON", exact=True).click()
    assert json.loads(Path(downloaded.value.path()).read_text(encoding="utf-8")) == view

    # Deliberately reverse completions across threshold A -> B -> A.
    for old_error in (False, True):
        held = []
        page.route(endpoint, lambda route: held.append(route))
        panel.get_by_role("button", name="Suggest strategy", exact=True).click()
        expect(panel.get_by_role("status")).to_be_visible()
        threshold = panel.get_by_label("LOO R² threshold", exact=True)
        threshold.fill("0.3")
        threshold.fill("0.25")
        panel.get_by_role("button", name="Suggest strategy", exact=True).click()
        expect(panel.get_by_role("status")).to_be_visible()
        assert len(held) == 2
        held[0].fulfill(status=409 if old_error else 200, json={"error": {"code": "synthetic_late_error"}} if old_error else view)
        expect(panel.get_by_role("status")).to_be_visible()
        expect(panel.get_by_role("alert")).to_have_count(0)
        expect(panel.get_by_role("button", name="Apply suggested strategy", exact=True)).to_have_count(0)
        held[1].fulfill(json=view)
        expect(panel.get_by_role("button", name="Apply suggested strategy", exact=True)).to_be_enabled()
        page.unroute(endpoint)

    # Applying advice must re-read currentness, not trust the old browser receipt.
    page.route(model_url, lambda route: route.fulfill(json={**model, "source_is_current": False}))
    panel.get_by_role("button", name="Apply suggested strategy", exact=True).click()
    expect(panel.get_by_role("alert")).to_be_visible()
    expect(panel.get_by_role("button", name="Apply suggested strategy", exact=True)).to_have_count(0)
    page.unroute(model_url)
    calculate()
    if mixed:
        # Reviewer regression: manual selection during the apply GET owns the UI.
        held = []
        page.route(model_url, lambda route: held.append(route))
        panel.get_by_role("button", name="Apply suggested strategy", exact=True).click()
        expect(panel.get_by_role("status")).to_be_visible()
        checkbox = parent.get_by_role("table", name="Candidate table", exact=True).get_by_role("checkbox").filter(visible=True)
        enabled = next(box for box in checkbox.all() if box.is_enabled())
        enabled.check()
        assert len(held) == 1
        held[0].fulfill(json=model)
        expect(parent.get_by_label("Selection mode", exact=True)).to_have_value("manual_ordered")
        expect(panel.get_by_role("button", name="Apply suggested strategy", exact=True)).to_have_count(0)
        enabled.uncheck()
        page.unroute(model_url)

        # A competing evaluation owns the workflow before its result arrives.
        panel.get_by_label("LOO R² threshold", exact=True).fill("0.4")
        calculate()
        held_models, held_evaluations = [], []
        evaluate_url = model_url + "/evaluate"
        page.route(model_url, lambda route: held_models.append(route))
        page.route(evaluate_url, lambda route: held_evaluations.append(route))
        panel.get_by_role("button", name="Apply suggested strategy", exact=True).click()
        expect(panel.get_by_role("status")).to_be_visible()
        evaluate_button = parent.get_by_role("button", name="Evaluate this page", exact=True)
        evaluate_button.click()
        expect(evaluate_button).to_be_disabled()
        assert len(held_models) == len(held_evaluations) == 1
        held_models[0].fulfill(json=model)
        expect(evaluate_button).to_be_disabled()
        expect(parent.get_by_label("Selection mode", exact=True)).to_have_value("manual_ordered")
        with page.expect_response(evaluate_url, timeout=90000) as evaluated:
            held_evaluations[0].continue_()
        assert evaluated.value.status == 200, evaluated.value.text()
        expect(evaluate_button).to_be_enabled()
        expect(panel.get_by_role("button", name="Apply suggested strategy", exact=True)).to_have_count(0)
        expect(panel.get_by_label("LOO R² threshold", exact=True)).to_have_value("0.4")
        page.unroute(model_url)
        page.unroute(evaluate_url)

    # Threshold 1 deterministically exercises the model-free exploration path.
    panel.get_by_label("LOO R² threshold", exact=True).fill("1")
    exploration = calculate()
    policy = "greedy_mixed_maximin_v1" if mixed else "greedy_incremental_maxpro_v1"
    assert exploration["decision"]["recommended_policy"] == policy
    write_count = len(writes)
    panel.get_by_role("button", name="Apply suggested strategy", exact=True).click()
    policy_input = parent.get_by_role("combobox", name="Augmentation strategy", exact=True)
    expect(policy_input).to_have_value(policy)
    expect(panel.get_by_role("status")).to_have_count(0)
    assert len(writes) == write_count  # Only GET currentness checks, not a POST.
    expect(parent.get_by_text("Auto evidence attached · threshold: 1", exact=True)).to_be_visible()
    policy_input.select_option("confirm_mean_then_competitive_sd_v1" if mixed else "greedy_mixed_maximin_v1")
    expect(parent.get_by_text("Auto evidence attached", exact=False)).to_have_count(0)
    policy_input.select_option(policy)
    expect(parent.get_by_text("Auto evidence attached", exact=False)).to_have_count(0)
    panel.get_by_label("LOO R² threshold", exact=True).fill("1")
    exploration = calculate()
    panel.get_by_role("button", name="Apply suggested strategy", exact=True).click()
    expect(parent.get_by_text("Auto evidence attached · threshold: 1", exact=True)).to_be_visible()
    selection_endpoint = api + ("/mixed-selections" if mixed else "/augmentations")
    with page.expect_response(selection_endpoint, timeout=90000) as selected:
        parent.get_by_role("button", name="Save automatic selection", exact=True).click()
    assert selected.value.status == 201, selected.value.text()
    selection = selected.value.json()
    assert selection["request"]["policy"] == policy
    assert selection["request"]["model_id"] is None
    assert selection["calculation"]["prediction_evaluations"] == 0
    assert selection["schema_version"] == selection["request"]["schema_version"] == (5 if mixed else 4)
    evidence = selection["calculation"]["auto_evidence"]
    assert evidence["decision_sha256"] == exploration["decision_sha256"]
    assert evidence["diagnostic"] == {key: value for key, value in exploration["diagnostic"].items()
                                       if key != "source_is_current"}
    saved = parent.get_by_role("region", name="Saved Auto decision evidence", exact=True)
    expect(saved).to_be_visible()
    for row, metric in zip(saved.locator("tbody tr").all(), evidence["diagnostic"]["calculation"]["responses"], strict=True):
        assert float(row.locator("td").nth(0).inner_text()) == metric["r_squared"]
    assert page.request.get(selection_endpoint + "/" + selection["selection_id"]).json() == selection
    assert page.request.get(api).json() == before
    assert page.request.get(model_url).json() == model
    page.remove_listener("request", record)
    if mixed and not keep_selection:
        parent.get_by_label("Selection mode", exact=True).select_option("manual_ordered")
    (output / "auto-advice.json").write_text(json.dumps(exploration, indent=2), encoding="utf-8")
    (output / "auto-effective-selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    return selection
