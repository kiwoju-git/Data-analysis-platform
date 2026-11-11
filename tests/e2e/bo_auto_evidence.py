"""Confirm a saved Auto review, reopen exact bytes and inspect offline HTML."""

import hashlib

from app_readiness import wait_for_app_ready, wait_for_layout_settled
from playwright.sync_api import expect


def verify_saved_auto_evidence(browser, page, api, base, model, selection, output, *, mixed=False):
    parent = page.get_by_role("region", name="Mixed-factor candidates and planning" if mixed else "Experimental augmentation", exact=True)
    endpoint = api + ("/mixed-selections/" if mixed else "/augmentations/") + selection["selection_id"] + "/confirm"
    # Commit succeeds but the browser loses the response. Retry must not duplicate trials.
    captured = []
    def lose_response(route):
        response = route.fetch()
        captured.append(response.json())
        route.abort("failed")
    page.route(endpoint, lose_response)
    parent.get_by_role("button", name="Confirm entire pending batch", exact=True).click()
    expect(parent.get_by_role("button", name="Retry identical request", exact=True)).to_be_visible()
    assert len(captured) == 1 and captured[0]["result_schema_version"] == (12 if mixed else 11)
    committed = page.request.get(api).json()
    page.unroute(endpoint)
    with page.expect_response(endpoint) as retried:
        parent.get_by_role("button", name="Retry identical request", exact=True).click()
    assert retried.value.status == 201, retried.value.text()
    batch = retried.value.json()
    assert batch["batch_id"] == captured[0]["batch_id"]
    assert page.request.get(api).json() == committed
    assert (batch["response_models"] if mixed else batch["model"]) is None
    assert batch["calculation"]["auto_evidence"] == selection["calculation"]["auto_evidence"]
    target = base + "/analysis/doe/doe.bayesian_optimization?study_id=" + batch["study_id"] + ("&mixed_planning_batch_id=" if mixed else "&augmentation_batch_id=") + batch["batch_id"]
    page.goto(target, wait_until="domcontentloaded")
    wait_for_app_ready(page, "en", "/analysis/doe/doe.bayesian_optimization")
    saved = page.get_by_role("region", name="Saved mixed-factor batch" if mixed else "Saved augmentation batch", exact=True)
    evidence = saved.get_by_role("region", name="Saved Auto decision evidence", exact=True)
    expect(evidence).to_be_visible()
    posts = []
    page.on("request", lambda request: posts.append(request.url) if request.method == "POST" else None)
    for locale, button, title in (("ko", "KOR", "저장된 Auto 판단 근거"), ("en", "ENG", "Saved Auto decision evidence")):
        page.locator(".language-switcher button").filter(has_text=button).click()
        expect(page.locator("html")).to_have_attribute("lang", locale)
        panel = page.get_by_role("region", name=title, exact=True)
        for width in (1024, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            wait_for_layout_settled(page)
            assert panel.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
            panel.screenshot(path=output / f"saved-auto-{locale}-{width}.png")
    assert not posts
    with page.expect_response(lambda response: response.url == base + "/api/v1/reports" and response.request.method == "POST") as exported:
        saved.get_by_role("button", name="Create managed HTML report", exact=True).click()
    assert exported.value.status == 201, exported.value.text()
    report = exported.value.json()
    with page.expect_download() as downloaded:
        saved.get_by_role("button", name="Download verified report", exact=True).click()
    path = output / "auto-evidence-report.html"
    downloaded.value.save_as(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == report["sha256"]
    offline = browser.new_context(offline=True)
    try:
        report_page = offline.new_page()
        report_page.goto(path.resolve().as_uri(), wait_until="domcontentloaded")
        section = report_page.locator('[data-auto-evidence="1"]')
        expect(section).to_be_visible()
        expect(section).to_contain_text(selection["calculation"]["auto_evidence"]["decision_sha256"])
        metrics = section.locator("table").last.locator("tbody tr")
        for row, metric in zip(metrics.all(), selection["calculation"]["auto_evidence"]["diagnostic"]["calculation"]["responses"], strict=True):
            displayed = float(row.locator("td").nth(1).inner_text().replace(",", ""))
            assert abs(displayed - metric["r_squared"]) <= max(abs(metric["r_squared"]) * 1e-9, 1e-30)
        section.screenshot(path=output / "offline-auto-evidence.png")
    finally:
        offline.close()
    return {"synthetic": True, "mixed": mixed, "study_id": batch["study_id"], "batch_id": batch["batch_id"],
            "selection_id": selection["selection_id"], "model_sha256": model["snapshot_sha256"],
            "decision_sha256": selection["calculation"]["auto_evidence"]["decision_sha256"],
            "report_sha256": report["sha256"], "lost_confirmation_retry_no_duplicate": True,
            "browser": browser.version}
