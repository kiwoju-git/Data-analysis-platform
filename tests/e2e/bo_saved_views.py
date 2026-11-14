"""Built all-factor plots, exact saved payloads, and offline managed HTML."""

import hashlib
import json
from pathlib import Path

from app_readiness import diagnosed_page, wait_for_layout_settled
from playwright.sync_api import expect


def verify_saved_matrix(browser, page, api, model, host, button, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    endpoint = api + "/planning-models/" + model["model_id"] + "/view-evaluations"
    writes = []

    def record(request):
        if "/api/" in request.url and request.method in {"POST", "PUT", "DELETE"}:
            writes.append(request.url)

    page.on("request", record)
    before = page.request.get(api).json()
    with page.expect_response(endpoint, timeout=125000) as evaluated:
        host.get_by_role("button", name=button, exact=True).click()
    assert evaluated.value.status == 200, evaluated.value.text()
    receipt = evaluated.value.json()
    payload = receipt["payload"]
    assert payload["kind"] == "profiler_matrix"
    assert payload["source"]["model_sha256"] == model["snapshot_sha256"]
    matrix = host.get_by_role("region", name="Whole-factor profiler matrix", exact=True)
    expect(matrix).to_be_visible()
    for metric in (
        "mean_raw",
        "latent_standard_deviation_raw",
        "predictive_standard_deviation_raw",
    ):
        matrix.get_by_label("Response display", exact=True).select_option(metric)
        previous = matrix.get_by_role("button", name="Previous page", exact=True)
        while previous.is_enabled():
            previous.click()
        for start in range(0, len(payload["axes"]), 2):
            for response in payload["responses"]:
                row = matrix.locator(
                    f'[data-profile-kind="response"][data-response-id="{response["response_id"]}"]'
                )
                for index, axis in enumerate(payload["axes"][start : start + 2]):
                    cell = row.locator(".bo-profile-grid-item").nth(index)
                    expect(cell).to_contain_text(axis["name"])
                    if not axis["points"]:
                        expect(cell.locator("svg")).to_have_count(0)
                        expect(cell).to_contain_text(axis["path"]["unavailable_reason"])
                    for coordinate_index, point in enumerate(axis["points"]):
                        marker = cell.locator(f'[data-point-id="{point["row_id"]}"]')
                        expect(marker).to_have_count(1)
                        prediction = next(
                            p
                            for p in point["response_predictions"]
                            if p["response_id"] == response["response_id"]
                        )
                        assert (
                            float(marker.get_attribute("data-y")) == prediction[metric]
                        )
                        x = (
                            coordinate_index
                            if axis["kind"] in {"nominal", "ordinal"}
                            else point["actual_coordinates"][axis["factor_id"]]
                        )
                        assert float(marker.get_attribute("data-x")) == x
                        if not point["constraints_satisfied"]:
                            assert marker.evaluate("e => e.tagName") == "polygon"
                    if axis["kind"] in {"nominal", "ordinal"}:
                        assert cell.locator("path.interactive-data-line").count() == 0
            if start + 2 < len(payload["axes"]):
                matrix.get_by_role("button", name="Next page", exact=True).click()
    assert writes == [endpoint], writes
    for locale, button_name, title in (
        ("ko", "KOR", "전체 요인 Profiler 행렬"),
        ("en", "ENG", "Whole-factor profiler matrix"),
    ):
        page.locator(".language-switcher button").filter(has_text=button_name).click()
        expect(page.locator("html")).to_have_attribute("lang", locale)
        translated = page.get_by_role("region", name=title, exact=True)
        for width in (1024, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            wait_for_layout_settled(page)
            assert translated.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
            controls = translated.locator(".bo-profile-matrix-pagination button")
            expect(controls).to_have_count(2)
            for control in controls.all():
                box = control.bounding_box()
                assert box and 32 <= box["width"] <= 48 and box["height"] >= 32
            left, right = (control.bounding_box() for control in controls.all())
            assert abs(left["y"] - right["y"]) <= 1
            assert right["x"] > left["x"] + left["width"] + 8
            expect(translated).to_contain_text(model["snapshot_sha256"])
            translated.screenshot(path=output / f"matrix-{locale}-{width}.png")
    assert writes == [endpoint], writes
    first = matrix.locator("[data-point-id]").first
    if first.count():
        first.focus()
        first.press("Enter")
        expect(first).to_have_attribute("data-selected", "true")
        first.press("Escape")
        expect(first).to_have_attribute("data-selected", "false")
    with page.expect_response(api + "/views") as saved_response:
        host.get_by_role("button", name="Save displayed view", exact=True).click()
    assert saved_response.value.status == 201, saved_response.value.text()
    saved = saved_response.value.json()
    assert (
        saved["payload"] == payload and saved["view_sha256"] == receipt["view_sha256"]
    )
    with page.expect_response(
        lambda r: r.url.endswith("/api/v1/reports") and r.request.method == "POST"
    ) as exported:
        host.get_by_role("button", name="Create HTML report", exact=True).click()
    assert exported.value.status == 201, exported.value.text()
    artifact = exported.value.json()
    with page.expect_download() as downloaded:
        host.get_by_role("button", name="Download HTML", exact=True).click()
    html = output / "saved-profiler.html"
    downloaded.value.save_as(html)
    assert hashlib.sha256(html.read_bytes()).hexdigest() == artifact["sha256"]
    with diagnosed_page(browser, output, "offline-profiler") as offline:
        offline.context.set_offline(True)
        offline.goto(html.resolve().as_uri(), wait_until="domcontentloaded")
        expect(offline.locator("body")).to_contain_text(saved["view_sha256"])
        assert offline.locator("svg").count() >= sum(
            bool(axis["points"]) for axis in payload["axes"]
        )
        if payload["schema_version"] == 2:
            expect(offline.locator("body")).to_contain_text("co-vary")
        offline.screenshot(path=output / "offline-profiler.png", full_page=True)
    assert page.request.get(api).json() == before
    assert page.request.get(api + "/views/" + saved["view_id"]).json() == saved
    page.remove_listener("request", record)
    (output / "saved-profiler-receipt.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "view_sha256": saved["view_sha256"],
                "model_sha256": model["snapshot_sha256"],
                "n_axes": len(payload["axes"]),
                "export_sha256": artifact["sha256"],
                "mutating_requests": writes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return saved
