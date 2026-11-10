"""API-seeded restore plus built-UI vector creation and measured entry.

Includes the separately diagnosed q1 candidate review/confirmation journey.
Only use against an isolated synthetic test workspace.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

from app_readiness import diagnosed_page, wait_for_app_ready, wait_for_layout_settled
from bo_desirability_review import verify_desirability_review
from bo_target_curve_preview import verify_target_curve_preview
from playwright.sync_api import Browser, expect, sync_playwright

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def verify_bo_vector_history(browser: Browser, base: str, output: Path) -> dict:
    from bo_augmentation import verify_augmentation
    from bo_mixed_workflow import verify_mixed_workflow
    from bo_persistent_planning import verify_persistent_planning
    from bo_target_curve_recommendation import verify_target_curve_recommendation

    # A fixed locale init script would overwrite the user's choice on every reload.
    with diagnosed_page(
        browser,
        output,
        "vector-history",
        init_script="""if (localStorage.getItem('statistical-twin.locale') === null) {
            localStorage.setItem('statistical-twin.locale', 'ko');
        }""",
    ) as page:
        request = {
            "name": "Synthetic multiresponse history",
            "factors": [
                {"factor_id": "x", "name": "Temperature", "low": 0, "high": 10}
            ],
            "initial_design_seed": 42,
            "initial_design_size": 3,
            "objective": {
                "name": "Joint goals",
                "goal_type": "desirability",
                "observation_policy": "complete_response_vector",
                "curve_policy": "derringer_suich_linear_v1",
                "responses": [
                    {
                        "response_id": "yield",
                        "name": "수율 <raw>",
                        "unit": "mg",
                        "goal": "maximize",
                        "lower": 0,
                        "target": 1,
                        "upper": None,
                        "importance": 2,
                    },
                    {
                        "response_id": "cost",
                        "name": "Cost",
                        "unit": "USD",
                        "goal": "minimize",
                        "lower": None,
                        "target": 1,
                        "upper": 10,
                        "importance": 1,
                    },
                ],
            },
        }
        created = page.request.post(
            base + "/api/v1/bayesian-studies", headers={"Origin": base}, data=request
        )
        assert created.status == 201, created.text()
        study = created.json()
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        observation_request = {
            "request_id": str(uuid4()),
            "expected_study_version_id": study["study_version_id"],
            "expected_history_revision_id": study["observation_history"][
                "history_revision_id"
            ],
            "expected_observation_history_sha256": study["observation_history"][
                "observation_history_sha256"
            ],
            "observations": [
                {
                    "trial_id": trial["trial_id"],
                    "response_values": {
                        "yield": (index + 1) * 1e-8,
                        "cost": 1000000000001 + index,
                    },
                }
                for index, trial in enumerate(study["trials"])
            ],
        }
        saved = page.request.put(
            api + "/observations/batch",
            headers={"Origin": base},
            data=observation_request,
        )
        assert saved.status == 200, saved.text()
        before = saved.json()["study"]
        writes: list[str] = []
        page.on(
            "request",
            lambda request: writes.append(request.method)
            if "/api/" in request.url and request.method in {"POST", "PUT", "DELETE"}
            else None,
        )
        page.goto(
            base + ROUTE + "?study_id=" + study["study_id"],
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, "ko", ROUTE)
        measurements = []
        for locale, button in (("ko", "KOR"), ("en", "ENG"), ("ko", "KOR")):
            page.locator(".language-switcher button").filter(has_text=button).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            panel = page.get_by_role(
                "region",
                name="다중 반응 저장 이력"
                if locale == "ko"
                else "Stored multiresponse history",
            )
            expect(panel).to_be_visible()
            expect(panel.get_by_role("status")).to_contain_text(
                "검토는 실험을 만들지 않으며 확정할 때 대기 배치 전체를 한 번에 생성합니다."
                if locale == "ko"
                else "Review creates no experiments; confirmation creates the entire pending batch atomically."
            )
            expect(panel.locator("input, select, button")).to_have_count(0)
            expect(panel).to_contain_text("수율 <raw>")
            expect(panel).to_contain_text("1e-8")
            expect(panel).to_contain_text("1000000000001")
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                wait_for_layout_settled(page)
                measurements.append(
                    panel.evaluate("""element => {
                    const r = element.getBoundingClientRect();
                    return {left:r.left, right:r.right, width:r.width, viewport:innerWidth};
                }""")
                )
                assert measurements[-1]["left"] >= 0
                assert measurements[-1]["right"] <= width + 1
                panel.screenshot(path=str(output / f"vector-{locale}-{width}.png"))
            assert (
                page.evaluate("localStorage.getItem('statistical-twin.locale')")
                == locale
            )
            page.reload(wait_until="domcontentloaded")
            wait_for_app_ready(page, locale, ROUTE)
            expect(panel).to_be_visible()
        assert writes == [], writes
        assert page.request.get(api).json() == before
        batch_output = output / "ordered-batch"
        batch_output.mkdir(parents=True, exist_ok=True)
        fit_output = output / "fit-quality-batch"
        fit_output.mkdir(parents=True, exist_ok=True)
        receipt = {
            "target_curve_preview": verify_target_curve_preview(
                browser, base, output / "curve-preview"
            ),
            "synthetic": True,
            "status": "succeeded",
            "browser": browser.version,
            "api_vector_storage": True,
            "ui_read_only_restore": True,
            "locale_resize_reload_no_writes": True,
            "history_unchanged": True,
            "ui_vector_entry": verify_bo_vector_entry(browser, base, output),
            "q1_desirability_review": verify_desirability_review(browser, base, output),
            "q2_desirability_batch": verify_desirability_review(
                browser, base, batch_output, 2
            ),
            "q2_fit_quality_batch": verify_desirability_review(
                browser, base, fit_output, 2, fit_quality=True
            ),
            "layout": measurements,
        }
        receipt["stored_target_curves"] = verify_target_curve_recommendation(
            browser, base, output / "stored-target-curves"
        )
        receipt["persistent_planning"] = verify_persistent_planning(
            browser, base, output / "persistent-planning"
        )
        receipt["augmentation"] = verify_augmentation(
            browser, base, output / "augmentation"
        )
        receipt["mixed_planning"] = verify_mixed_workflow(
            browser, base, output / "mixed-planning"
        )
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


def verify_bo_vector_entry(
    browser: Browser, base: str, output: Path, curve_policy: bool = False
) -> dict:
    with diagnosed_page(
        browser,
        output,
        "vector-entry",
        init_script="""
        if (localStorage.getItem('statistical-twin.locale') === null)
            localStorage.setItem('statistical-twin.locale', 'en');
    """,
    ) as page:
        writes = []
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda r: writes.append((r.method, r.url, r.post_data))
            if "/api/" in r.url and r.method in {"POST", "PUT", "DELETE"}
            else None,
        )
        page.goto(base + ROUTE, wait_until="domcontentloaded")
        wait_for_app_ready(page, "en", ROUTE)
        page.locator("#bayesian-study-name").fill("Synthetic UI vector entry")
        page.locator("#bayesian-response-mode").select_option("vector")
        page.locator("#bayesian-objective-name").fill("Quality and cost")
        page.locator("#bayesian-initial-design-size").fill("3")
        goals = page.get_by_role("region", name="Response goals", exact=True)
        goals.get_by_label("Response 1 name", exact=True).fill("수율 <raw>")
        goals.get_by_label("Response 1 unit", exact=True).fill("mg")
        goals.get_by_label("Response 1 lower", exact=True).fill("0")
        goals.get_by_label("Response 1 target", exact=True).fill("1")
        goals.get_by_label("Response 2 name", exact=True).fill("Cost")
        goals.get_by_label("Response 2 goal", exact=True).select_option("minimize")
        goals.get_by_label("Response 2 target", exact=True).fill("1")
        goals.get_by_label("Response 2 upper", exact=True).fill("10")
        if curve_policy:
            goals.get_by_label("Response 1 goal", exact=True).select_option(
                "match_target"
            )
            goals.get_by_label("Response 1 lower", exact=True).fill("-1")
            goals.get_by_label("Response 1 target", exact=True).fill("0")
            goals.get_by_label("Response 1 upper", exact=True).fill("1")
            goals.get_by_label(
                "수율 <raw>: Recommendation curve", exact=True
            ).select_option("gaussian_target")
            goals.get_by_label(
                "수율 <raw>: Desirability at lower control", exact=True
            ).fill("0.04")
            goals.get_by_label(
                "수율 <raw>: Desirability at upper control", exact=True
            ).fill("0.2")
        for width in (1024, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            wait_for_layout_settled(page)
            bounds = goals.bounding_box()
            assert (
                bounds
                and bounds["x"] >= 0
                and bounds["x"] + bounds["width"] <= width + 1
            )
            goals.screenshot(path=str(output / f"vector-goals-en-{width}.png"))
            if curve_policy:
                controls = goals.locator(
                    ".bo-curve-policy input, .bo-curve-policy select"
                )
                assert controls.count() == 3
                for control in controls.all():
                    assert (
                        control.evaluate("e => e.getBoundingClientRect().height") >= 34
                    )
        with page.expect_response(
            lambda r: r.url.endswith("/api/v1/bayesian-studies")
            and r.request.method == "POST"
        ) as created:
            page.get_by_role("button", name="Create study", exact=True).click()
        assert created.value.status == 201, created.value.text()
        study = created.value.json()
        if curve_policy:
            assert study["study_schema_version"] == 6
            assert study["objective"]["responses"][0]["curve"] == {
                "policy": "two_sided_gaussian_target_peak_one_v1",
                "lower_desirability": 0.04,
                "upper_desirability": 0.2,
            }
        assert study["objective"]["goal_type"] == "desirability"
        assert study["objective"]["responses"][1]["lower"] is None
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        entry = page.get_by_role(
            "region", name="Multiresponse observation entry", exact=True
        )
        expect(entry).to_be_visible()
        trial = study["trials"][0]

        def cell(response_id):
            return page.locator(
                f'input[data-trial-id="{trial["trial_id"]}"][data-response-id="{response_id}"]'
            )

        cell("response_1").fill("-")
        page.keyboard.type("1e-8")
        expect(cell("response_1")).to_have_value("-1e-8")
        expect(cell("response_1")).to_be_focused()
        before_url = page.url
        entry.get_by_role("button", name="Review measurements", exact=True).click()
        expect(entry.get_by_role("alert")).to_contain_text("every response")
        assert len(writes) == 1
        cell("response_2").fill("1000000000001")
        entry.get_by_role("button", name="Review measurements", exact=True).click()
        expect(
            page.get_by_role("region", name="Confirm measured responses", exact=True)
        ).to_contain_text("1000000000001")
        for locale, button in (("ko", "KOR"), ("en", "ENG")):
            page.locator(".language-switcher button").filter(has_text=button).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            expect(cell("response_1")).to_have_value("-1e-8")
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                wait_for_layout_settled(page)
                panel = page.get_by_role(
                    "region",
                    name="다중 반응 관측 입력"
                    if locale == "ko"
                    else "Multiresponse observation entry",
                    exact=True,
                )
                bounds = panel.bounding_box()
                assert (
                    bounds
                    and bounds["x"] >= 0
                    and bounds["x"] + bounds["width"] <= width + 1
                )
                panel.screenshot(
                    path=str(output / f"vector-entry-{locale}-{width}.png")
                )
        assert len(writes) == 1 and page.url == before_url
        # A true server commit with a lost response must be replayed, not duplicated.
        endpoint = api + "/observations/batch"
        lost_payload = []

        def lose_response(route):
            lost_payload.append(route.request.post_data_json)
            result = route.fetch()
            assert result.status == 200, result.text()
            route.abort("failed")

        page.route(endpoint, lose_response)
        entry.get_by_role("button", name="Confirm measurements", exact=True).click()
        expect(
            entry.get_by_role("button", name="Retry same request", exact=True)
        ).to_be_visible()
        assert len(lost_payload) == 1 and len(writes) == 2
        page.unroute(endpoint, lose_response)
        with page.expect_response(endpoint) as replay:
            entry.get_by_role("button", name="Retry same request", exact=True).click()
        assert replay.value.status == 200
        assert replay.value.request.post_data_json == lost_payload[0]
        saved = replay.value.json()["study"]
        assert saved["completed_trial_count"] == 1 and saved["trial_count"] == 3
        assert saved["trials"][0]["response_values"] == {
            "response_1": -1e-8,
            "response_2": 1000000000001,
        }
        expect(cell("response_1")).to_have_count(0)
        # Hold an old request until a newer draft has been successfully committed.
        trial = study["trials"][1]
        cell("response_1").fill("1")
        cell("response_2").fill("2")
        entry.get_by_role("button", name="Review measurements", exact=True).click()
        held = []

        def delay_first(route):
            if not held:
                held.append(route)
            else:
                route.continue_()

        page.route(endpoint, delay_first)
        entry.get_by_role("button", name="Confirm measurements", exact=True).click()
        expect(entry.get_by_role("button", name="Saving", exact=True)).to_be_visible()
        assert len(held) == 1
        cell("response_1").fill("3")
        expect(
            page.get_by_role("region", name="Confirm measured responses", exact=True)
        ).to_have_count(0)
        entry.get_by_role("button", name="Review measurements", exact=True).click()
        with page.expect_response(endpoint) as fresh:
            entry.get_by_role("button", name="Confirm measurements", exact=True).click()
        assert fresh.value.status == 200
        old = held[0].fetch()
        assert old.status == 409
        held[0].fulfill(response=old)
        page.unroute(endpoint, delay_first)
        expect(entry.get_by_role("alert")).to_have_count(0)
        before = page.request.get(api).json()
        assert before["completed_trial_count"] == 2
        assert before["trials"][1]["response_values"]["response_1"] == 3
        # Another client closes a trial with different values. Refresh must not
        # erase our unsaved draft or overwrite the remote measurements.
        trial = study["trials"][2]
        cell("response_1").fill("5")
        cell("response_2").fill("6")
        entry.get_by_role("button", name="Review measurements", exact=True).click()
        remote = page.request.put(
            endpoint,
            headers={"Origin": base},
            data={
                "request_id": str(uuid4()),
                "expected_study_version_id": before["study_version_id"],
                "expected_history_revision_id": before["observation_history"][
                    "history_revision_id"
                ],
                "expected_observation_history_sha256": before["observation_history"][
                    "observation_history_sha256"
                ],
                "observations": [
                    {
                        "trial_id": trial["trial_id"],
                        "response_values": {"response_1": 7, "response_2": 8},
                    }
                ],
            },
        )
        assert remote.status == 200
        entry.get_by_role("button", name="Confirm measurements", exact=True).click()
        expect(entry.get_by_role("alert")).to_be_visible()
        entry.get_by_role("button", name="Refresh history", exact=True).click()
        comparison = page.get_by_role(
            "region", name="Compare saved history with my inputs", exact=True
        )
        expect(comparison).to_be_visible()
        expect(comparison.locator("tbody tr").first.locator("td").nth(1)).to_have_text(
            "5"
        )
        expect(comparison.locator("tbody tr").first.locator("td").nth(2)).to_have_text(
            "7"
        )
        entry.get_by_role(
            "button", name="Discard unsaved inputs for closed trials", exact=True
        ).click()
        expect(comparison).to_have_count(0)
        before = page.request.get(api).json()
        assert before["completed_trial_count"] == 3
        assert before["trials"][2]["response_values"] == {
            "response_1": 7,
            "response_2": 8,
        }
        count = len(writes)
        page.reload(wait_until="domcontentloaded")
        wait_for_app_ready(page, "en", ROUTE)
        expect(
            page.get_by_role("region", name="Stored multiresponse history", exact=True)
        ).to_contain_text("1000000000001")
        assert page.request.get(api).json() == before
        assert len(writes) == count and errors == []
        return {
            "status": "succeeded",
            "ui_create": True,
            "partial_vector_no_request": True,
            "lost_response_same_request_replay": True,
            "late_error_ignored": True,
            "conflict_draft_retained_until_explicit_discard": True,
            "raw_values_preserved": True,
            "locale_resize_no_writes": True,
            "restored_exact_history": True,
            "pageerrors": errors,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            print(
                json.dumps(
                    verify_bo_vector_history(browser, args.base_url, args.output)
                )
            )
        finally:
            browser.close()
