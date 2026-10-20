"""Synthetic RSM source-ownership checks using actual persisted API responses."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, Route, expect

from app_readiness import diagnosed_page, wait_for_app_ready


def verify_rsm_context(browser: Browser, base_url: str, output: Path) -> None:
    route_path = "/analysis/doe/doe.response_surface"
    with diagnosed_page(browser, output, "response-context", locale="ko") as page:
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(base_url + route_path, wait_until="domcontentloaded")
        wait_for_app_ready(page, "ko", route_path)
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and urlsplit(response.url).path == "/api/v1/doe-designs/response-surface"
        ) as created:
            page.get_by_role("button", name="CCD 생성", exact=True).click()
        assert created.value.status == 201
        design = created.value.json()
        runs = design["runs"]
        save = page.get_by_role("button", name="반응 저장", exact=True)
        analyze = page.get_by_role("button", name="Quadratic model 적합", exact=True)
        response_path = (
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/responses"
        )
        writes: list[dict] = []
        page.on(
            "request",
            lambda request: writes.append(request.post_data_json)
            if request.method == "PUT" and urlsplit(request.url).path == response_path
            else None,
        )
        save.click()
        expect(page.locator(".error-box")).to_contain_text(
            "doe_rsm_response_values_required"
        )
        assert not writes

        # Exact zero is valid; nonconstant synthetic responses support a later fit.
        for index, run in enumerate(runs):
            page.get_by_label(f"Run {run['run_order']} 반응", exact=True).fill(
                str(index)
            )
        history_pattern = (
            f"**/api/v1/doe-designs/{design['design_id']}/response-revisions*"
        )
        page.route(
            history_pattern,
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                json={"error": {"code": "synthetic_history_unavailable"}},
            ),
        )
        with page.expect_response(
            lambda response: response.request.method == "PUT"
            and urlsplit(response.url).path == response_path
        ) as saved:
            save.click()
        assert saved.value.status == 200
        saved_payload = saved.value.json()
        expect(analyze).to_be_enabled()
        expect(page.get_by_role("button", name="이력 다시 불러오기")).to_be_visible()
        expect(page.locator(".error-box")).to_have_count(0)
        assert writes[-1]["values"][0]["value"] == 0
        page.unroute(history_pattern)
        page.get_by_role("button", name="이력 다시 불러오기").click()
        expect(page.get_by_role("button", name="이력 다시 불러오기")).to_have_count(0)
        expect(page.get_by_label("RSM response revision history")).to_be_visible()
        revision = saved_payload["responses"][0]
        expect(page.get_by_label("CCD 설계 요약")).to_contain_text(
            revision["response_revision_sha256"][:12]
        )

        held: list[tuple[Route, dict]] = []

        def hold_save(route: Route) -> None:
            if route.request.method != "PUT":
                route.continue_()
                return
            response = route.fetch()
            assert response.status == 200
            held.append((route, response.json()))

        page.route("**" + response_path, hold_save)
        save.click()
        _wait_held(page, held)
        first = page.get_by_label(f"Run {runs[0]['run_order']} 반응", exact=True)
        first.fill("0.5")
        pending_save, saved_response = held.pop()
        pending_save.fulfill(status=200, json=saved_response)
        expect(first).to_have_value("0.5")
        expect(analyze).to_be_disabled()
        expect(save).to_be_enabled()
        page.unroute("**" + response_path)

        save.click()
        expect(analyze).to_be_enabled()
        analysis_path = (
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/analyses"
        )

        def hold_analysis(route: Route) -> None:
            response = route.fetch()
            assert response.status == 201, response.text()
            held.append((route, response.json()))

        page.route("**" + analysis_path, hold_analysis)
        analyze.click()
        _wait_held(page, held)
        first.fill("0.75")
        pending, payload = held.pop()
        pending.fulfill(status=201, json=payload)
        expect(page.locator("#rsm-result-title")).to_have_count(0)
        expect(analyze).to_be_disabled()
        expect(first).to_have_value("0.75")
        # The obsolete UI completion must not delete the committed server artifact.
        restored = page.request.get(
            base_url + analysis_path + "/" + payload["analysis_id"]
        )
        assert restored.status == 200
        assert restored.json() == payload
        page.unroute("**" + analysis_path)
        page.screenshot(
            path=str(output / "response-context" / "rsm-context-after-edit.png"),
            full_page=True,
        )


def _wait_held(page: Page, held: list[tuple[Route, dict]]) -> None:
    # Wait for the observable request-start UI; route.fetch dispatches via Playwright.
    for _ in range(200):
        if held:
            return
        page.wait_for_timeout(50)
    raise AssertionError("Synthetic delayed RSM response was not captured")
