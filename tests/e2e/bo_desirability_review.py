"""Synthetic built-UI ordered desirability review and explicit whole confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from app_readiness import (
    diagnosed_page,
    wait_for_app_ready,
    wait_for_bayesian_ready,
    wait_for_layout_settled,
)
from playwright.sync_api import Browser, expect, sync_playwright

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def verify_desirability_review(
    browser: Browser,
    base: str,
    output: Path,
    batch_size: int = 1,
    fit_quality: bool = False,
    curve_policy: bool = False,
) -> dict:
    with diagnosed_page(
        browser,
        output,
        "desirability-review",
        init_script="""
        if (localStorage.getItem('statistical-twin.locale') === null)
          localStorage.setItem('statistical-twin.locale', 'en');
    """,
    ) as page:
        created = page.request.post(
            base + "/api/v1/bayesian-studies",
            headers={"Origin": base},
            data={
                "name": f"Synthetic q{batch_size} desirability journey",
                "initial_design_seed": 42,
                "initial_design_size": 3,
                "factors": [
                    {"factor_id": "x", "name": "Temperature", "low": 0, "high": 10}
                ],
                "objective": {
                    "name": "Joint goals",
                    "goal_type": "desirability",
                    "observation_policy": "complete_response_vector",
                    "curve_policy": "per_response_target_gaussian_or_ds_v1"
                    if curve_policy
                    else "derringer_suich_linear_v1",
                    "responses": [
                        {
                            "response_id": "yield",
                            "name": "수율 <raw>",
                            "unit": "%",
                            "goal": "maximize",
                            "lower": 0,
                            "target": 100,
                            "upper": None,
                            "importance": 2,
                        },
                        {
                            "response_id": "cost",
                            "name": "Cost",
                            "unit": "USD",
                            "goal": "match_target" if curve_policy else "minimize",
                            "lower": 1 if curve_policy else None,
                            "target": 4 if curve_policy else 1,
                            "upper": 10,
                            "importance": 1,
                            **(
                                {
                                    "curve": {
                                        "policy": "two_sided_gaussian_target_peak_one_v1",
                                        "lower_desirability": 0.04,
                                        "upper_desirability": 0.2,
                                    }
                                }
                                if curve_policy
                                else {}
                            ),
                        },
                    ],
                },
            },
        )
        assert created.status == 201, created.text()
        study = created.json()
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        measured = page.request.put(
            api + "/observations/batch",
            headers={"Origin": base},
            data={
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
                        "response_values": {"yield": 40.0 + i, "cost": 3.0 + i},
                    }
                    for i, trial in enumerate(study["trials"])
                ],
            },
        )
        assert measured.status == 200, measured.text()
        before = measured.json()["study"]
        errors, writes = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: writes.append((request.url, request.post_data))
            if "/api/" in request.url and request.method in {"POST", "PUT", "DELETE"}
            else None,
        )
        page.goto(
            base + ROUTE + "?study_id=" + study["study_id"],
            wait_until="domcontentloaded",
        )
        wait_for_bayesian_ready(page, "en", ROUTE)
        panel = page.get_by_role(
            "region", name="Multiresponse candidate review", exact=True
        )
        expect(panel).to_be_visible()
        review_button = panel.get_by_role(
            "button", name="Review ordered batch", exact=True
        )
        expect(review_button).to_be_enabled()
        panel.get_by_label("Experiments in this batch (1-8)", exact=True).select_option(
            str(batch_size)
        )
        if fit_quality:
            panel.get_by_label("GP initialization", exact=True).select_option(
                "bounded_multiscale_starts_v1"
            )
            panel.get_by_label("Screened starts to refine (1-3)", exact=True).fill("1")
            panel.get_by_label("Shared model evaluations (2–2000)", exact=True).fill(
                "1800"
            )
        if batch_size > 1:
            panel.get_by_label("Posterior samples (16-256)", exact=True).fill("16")
            # An explicit supported-options fixture, not an automatic fallback.
            # The estimate/Matérn fixture has a separate precision-rejection test.
            for goal in study["objective"]["responses"]:
                panel.get_by_label(
                    goal["name"] + ": Signal kernel", exact=True
                ).select_option("exponential")
                panel.get_by_label(
                    goal["name"] + ": Measurement noise", exact=True
                ).select_option("fixed")
                panel.get_by_label(goal["unit"], exact=True).fill("0.2")
        held = []

        def hold(route):
            held.append(route)

        page.route(api + "/desirability-reviews", hold)
        review_button.click()
        expect(
            panel.get_by_role("button", name="Calculating review…", exact=True)
        ).to_be_visible()
        assert len(held) == 1
        panel.get_by_label("Seed (0–2147483647)", exact=True).fill("43")
        old = held[0].fetch(timeout=90000)
        assert old.status == 200, old.text()
        held[0].fulfill(response=old)
        page.unroute(api + "/desirability-reviews", hold)
        expect(
            panel.get_by_role("button", name="Confirm entire pending batch", exact=True)
        ).to_have_count(0)
        assert page.request.get(api).json()["trial_count"] == 3
        with page.expect_response(
            api + "/desirability-reviews", timeout=90000
        ) as response:
            review_button.click()
        assert response.value.status == 200, response.value.text()
        review = response.value.json()
        expect(
            panel.get_by_role("button", name="Confirm entire pending batch", exact=True)
        ).to_be_visible()
        assert page.request.get(api).json() == before
        assert review["calculation"]["batch_size"] == batch_size
        assert len(review["calculation"]["items"]) == batch_size
        if curve_policy:
            curve_table = panel.get_by_role(
                "table", name="Stored recommendation curves", exact=True
            )
            curve_row = curve_table.get_by_role("row").filter(has_text="Cost")
            cells = curve_row.locator("td")
            assert [float(cells.nth(i).inner_text()) for i in (1, 2, 3)] == [
                0.04,
                1,
                0.2,
            ]
            expect(cells.nth(0)).to_have_text("Two-sided Gaussian target")
        if fit_quality:
            assert review["schema_version"] == (5 if curve_policy else 4) and review[
                "calculation"
            ]["schema_version"] == (7 if curve_policy else 6)
            fit_panel = panel.get_by_role(
                "region", name="Surrogate fit diagnostics", exact=True
            )
            expect(fit_panel).to_be_visible()
            for model in review["calculation"]["shared_model"]["response_models"]:
                goal = next(
                    g
                    for g in study["objective"]["responses"]
                    if g["response_id"] == model["response_id"]
                )
                section = fit_panel.get_by_role(
                    "region",
                    name="Surrogate fit diagnostics: " + goal["name"],
                    exact=True,
                )
                table = section.get_by_role(
                    "table",
                    name="Surrogate fit diagnostics: " + goal["name"],
                    exact=True,
                )
                cells = table.locator("tbody tr").first.locator("td")
                assert (
                    float(cells.nth(1).inner_text())
                    == -model["model"]["fit_diagnostics"]["start_best_evaluations"][0][
                        "negative_log_likelihood"
                    ]
                )
                point = section.locator(".bo-fit-point[tabindex]").first
                point.focus()
                point.press("Enter")
                point.press("Escape")
                assert section.locator("svg").count() > 0
        if batch_size > 1:
            expect(panel.locator("[data-candidate-rank]")).to_have_count(batch_size)
            for rank in range(1, batch_size + 1):
                candidate_panel = panel.get_by_role(
                    "region", name=f"Selection rank {rank}", exact=True
                )
                expect(candidate_panel).to_be_visible()
                candidate_panel.get_by_text(
                    "Conditional batch planning", exact=True
                ).click()
                expect(candidate_panel).to_contain_text(
                    "excludes Beta approximation error"
                )
                original = review["calculation"]["items"][rank - 1]
                # Visible table values, not hidden proof fields or screenshots alone.
                factor_cells = candidate_panel.get_by_role(
                    "table", name="Candidate actual settings", exact=True
                ).locator("tbody td")
                for index, factor in enumerate(study["factors"]):
                    assert (
                        float(factor_cells.nth(index).inner_text())
                        == original["actual_coordinates"][factor["factor_id"]]
                    )
                predicted = candidate_panel.get_by_role(
                    "table",
                    name="Per-response predictions (original units)",
                    exact=True,
                ).locator("tbody tr")
                for index, goal in enumerate(study["objective"]["responses"]):
                    expected = next(
                        row
                        for row in original["response_predictions"]
                        if row["response_id"] == goal["response_id"]
                    )
                    cells = predicted.nth(index).locator("td")
                    for column, field in enumerate(
                        (
                            "mean_raw",
                            "latent_standard_deviation_raw",
                            "predictive_standard_deviation_raw",
                        )
                    ):
                        assert float(cells.nth(column).inner_text()) == expected[field]
        count = len(writes)
        for locale, name, title in (
            ("ko", "KOR", "다중 반응 후보 검토"),
            ("en", "ENG", "Multiresponse candidate review"),
        ):
            page.locator(".language-switcher button").filter(has_text=name).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            current = page.get_by_role("region", name=title, exact=True)
            expect(current).to_contain_text("수율 <raw>")
            if curve_policy:
                curves = current.get_by_role(
                    "table",
                    name="저장된 추천 곡선"
                    if locale == "ko"
                    else "Stored recommendation curves",
                    exact=True,
                )
                expect(curves).to_contain_text("Cost")
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1100})
                wait_for_layout_settled(page)
                assert current.evaluate("e => e.getBoundingClientRect().width") > 400
                assert current.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
                for control in current.locator(
                    ".bo-desirability-settings input, .bo-desirability-settings select"
                ).all():
                    assert (
                        control.evaluate("e => e.getBoundingClientRect().height") >= 32
                    )
                for metric in current.locator(".bo-desirability-summary > div").all():
                    assert metric.evaluate(
                        "e => e.querySelector('dd').getBoundingClientRect().top >= e.querySelector('dt').getBoundingClientRect().bottom"
                    )
                page.screenshot(
                    path=str(output / f"desirability-{locale}-{width}.png"),
                    full_page=True,
                )
                if fit_quality:
                    diagnostic = current.locator(".bo-fit-response").first
                    assert diagnostic.evaluate(
                        "e => e.scrollWidth <= e.clientWidth + 1"
                    )
                    diagnostic.screenshot(
                        path=str(output / f"fit-diagnostic-{locale}-{width}.png")
                    )
        assert len(writes) == count
        endpoint = api + f"/desirability-reviews/{review['review_id']}/confirm"
        committed = []

        def lose_response(route):
            result = route.fetch(timeout=90000)
            assert result.status == 201, result.text()
            committed.append(result.json())
            route.abort("failed")

        page.route(endpoint, lose_response)
        panel.get_by_role(
            "button", name="Confirm entire pending batch", exact=True
        ).click()
        expect(panel.get_by_role("alert")).to_be_visible()
        page.unroute(endpoint, lose_response)
        with page.expect_response(endpoint) as retried:
            panel.get_by_role(
                "button", name="Confirm entire pending batch", exact=True
            ).click()
        assert retried.value.status == 201
        batch = retried.value.json()
        assert committed == [batch]
        assert batch["calculation"] == review["calculation"]
        for item in batch["items"]:
            assert item["trial"]["objective_value"] is None
            assert "response_values" not in item["trial"]
        expect(page).to_have_url(
            base
            + ROUTE
            + "?study_id="
            + study["study_id"]
            + "&batch_id="
            + batch["batch_id"]
        )
        current = page.request.get(api).json()
        assert (
            current["trial_count"] == 3 + batch_size
            and current["pending_trial_count"] == batch_size
        )
        entry = page.get_by_role(
            "region", name="Multiresponse observation entry", exact=True
        )
        # Complete the last selected trial first. A partial batch must stay owned
        # by the original recommendation, not become a new recommendation source.
        for completed_count, item in enumerate(reversed(batch["items"]), start=1):
            inputs = entry.locator(
                f'input[data-trial-id="{item["trial"]["trial_id"]}"]'
            )
            expect(inputs).to_have_count(2)
            inputs.nth(0).fill("43.25")
            inputs.nth(1).fill("3.125")
            entry.get_by_role("button", name="Review measurements", exact=True).click()
            with page.expect_response(api + "/observations/batch") as observed:
                entry.get_by_role(
                    "button", name="Confirm measurements", exact=True
                ).click()
            assert observed.value.status == 200, observed.value.text()
            page.reload(wait_until="domcontentloaded")
            wait_for_bayesian_ready(page, "en", ROUTE)
            partial = page.request.get(
                api + "/desirability-recommendations/" + batch["batch_id"]
            ).json()
            assert partial["result_sha256"] == batch["result_sha256"]
            assert partial["calculation"] == batch["calculation"]
            if completed_count < batch_size:
                assert partial["batch_state"] == "partially_completed"
                expect(panel).to_contain_text("Partially completed")
                expect(review_button).to_be_disabled()
                assert (
                    sum(
                        item["current_trial"]["state"] == "pending"
                        for item in partial["items"]
                    )
                    == batch_size - completed_count
                )
        expect(panel).to_contain_text("43.25")
        restored = page.request.get(
            api + "/desirability-recommendations/" + batch["batch_id"]
        ).json()
        assert restored["result_sha256"] == batch["result_sha256"]
        assert restored["calculation"] == batch["calculation"]
        for item in restored["items"]:
            assert item["current_trial"]["response_values"] == {
                "yield": 43.25,
                "cost": 3.125,
            }
        sources = page.request.get(
            base
            + "/api/v1/reports/sources?source_kind=bayesian_history_revision&limit=100"
        ).json()
        descriptor = next(
            item
            for item in sources["items"]
            if item["source"].get("attachment", {}).get("batch_id") == batch["batch_id"]
        )
        source = descriptor["source"]
        capability = page.request.post(
            base + "/api/v1/reports/capability",
            headers={"Origin": base},
            data={"source": source, "locale": "en"},
        )
        assert capability.status == 200, capability.text()
        reference = capability.json()["source_ref_sha256"]
        panel.get_by_role(
            "link", name="Report Center: Bayesian history sources", exact=True
        ).click()
        wait_for_app_ready(page, "en", "/reports")
        page.locator(f'[data-report-source="{reference}"]').click()
        selected = page.locator(f'[data-managed-report-selection="{reference}"]')
        with page.expect_response("**/reports/source-snapshot") as snapshot_response:
            selected.locator("[data-view-stored-source]").click()
        assert snapshot_response.value.status == 200, snapshot_response.value.text()
        snapshot = snapshot_response.value.json()
        assert snapshot["source"] == source
        assert snapshot["payload"]["attachment"]["calculation"] == batch["calculation"]
        shown = selected.locator(".managed-report-snapshot-json")
        expect(shown).to_be_visible()
        assert json.loads(shown.inner_text()) == snapshot["payload"]
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/v1/reports")
        ) as report_response:
            selected.locator("[data-create-managed-report]").click()
        assert report_response.value.status == 201, report_response.value.text()
        report = report_response.value.json()
        assert report["source"] == source and report["locale"] == "en"
        row = selected.locator(f'[data-managed-report="{report["export_id"]}"]')
        with page.expect_download() as downloaded:
            row.get_by_role("button", name="Download", exact=True).click()
        html = output / "desirability-saved-report.html"
        downloaded.value.save_as(html)
        assert hashlib.sha256(html.read_bytes()).hexdigest() == report["sha256"]
        page.goto(
            base + f'/reports?report_id={report["export_id"]}',
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, "en", "/reports")
        expect(
            page.locator(f'[data-managed-report-selection="{reference}"]')
        ).to_be_visible()
        expect(
            page.locator(f'[data-managed-report="{report["export_id"]}"]')
        ).to_be_visible()
        expect(
            selected.get_by_text("Loading stored records...", exact=True)
        ).to_have_count(0)
        page.screenshot(
            path=str(output / "desirability-report-center.png"), full_page=True
        )
        page.context.set_offline(True)
        page.goto(html.resolve().as_uri(), wait_until="domcontentloaded")
        expect(page.locator("[data-report-section='noise_summary']")).to_contain_text(
            "Beta moment-matched EI"
        )
        assert page.locator("svg").count() >= 2
        if curve_policy:
            expect(
                page.locator("[data-report-section='noise_summary']")
            ).to_contain_text("two_sided_gaussian_target_peak_one_v1")
            assert review["calculation"]["schema_version"] == 7
            assert batch["model_schema_version"] == 7
        if fit_quality:
            expect(
                page.locator("[data-fit-policy='bounded_multiscale_starts_v1']")
            ).to_have_count(len(study["objective"]["responses"]))
            expect(
                page.get_by_role(
                    "heading", name="Surrogate fit diagnostics: 수율 <raw>", exact=True
                )
            ).to_be_visible()
            for section in page.locator("[data-fit-policy]").all():
                expect(
                    section.get_by_role(
                        "columnheader", name="Best visited LML", exact=True
                    )
                ).to_be_visible()
                assert section.locator("svg [data-y]").count() >= 3
        if batch_size > 1:
            expect(page.locator("[data-batch-rank]")).to_have_count(batch_size)
            for item in batch["calculation"]["items"]:
                section = page.locator(f'[data-batch-rank="{item["rank"]}"]')
                expect(section).to_be_visible()
                expect(section).to_contain_text("Marginal batch improvement")
        page.screenshot(
            path=str(output / "desirability-offline-report.png"), full_page=True
        )
        assert errors == []
        receipt = {
            "synthetic": True,
            "batch_size": batch_size,
            "all_ranks_reviewed": True,
            "partial_reverse_order_measurements": batch_size > 1,
            "browser": browser.version,
            "review_no_write": True,
            "stale_review_ignored": True,
            "lost_confirm_same_id_replay": True,
            "measured_vector_entry": True,
            "exact_restore": True,
            "locale_resize_no_fit": True,
            "report_created_downloaded_restored_ui": True,
            "saved_report_viewed_offline": True,
            "batch_id": batch["batch_id"],
            "study_id": study["study_id"],
            "report_id": report["export_id"],
            "result_sha256": batch["result_sha256"],
            "report_sha256": report["sha256"],
            "pageerrors": errors,
        }
        (output / "desirability-receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


def verify_desirability_restart(
    browser: Browser, base: str, output: Path, receipt_path: Path
) -> dict:
    """Call after the owning test server was stopped and restarted by the runner."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    with diagnosed_page(
        browser,
        output,
        "desirability-restarted",
        init_script="localStorage.setItem('statistical-twin.locale', 'en');",
    ) as page:
        api = base + "/api/v1/bayesian-studies/" + receipt["study_id"]
        response = page.request.get(
            api + "/desirability-recommendations/" + receipt["batch_id"]
        )
        assert response.status == 200, response.text()
        saved = response.json()
        assert saved["result_sha256"] == receipt["result_sha256"]
        assert (
            saved["batch_size"] == receipt["batch_size"]
            and saved["batch_state"] == "completed"
        )
        writes = []
        page.on(
            "request",
            lambda request: writes.append(request.url)
            if request.method in {"POST", "PUT", "DELETE"} and "/api/" in request.url
            else None,
        )
        page.goto(
            base
            + ROUTE
            + f'?study_id={receipt["study_id"]}&batch_id={receipt["batch_id"]}',
            wait_until="domcontentloaded",
        )
        wait_for_bayesian_ready(page, "en", ROUTE)
        panel = page.get_by_role(
            "region", name="Multiresponse candidate review", exact=True
        )
        expect(panel).to_contain_text("Saved recommendation: Completed")
        expect(panel).to_contain_text("43.25")
        expect(panel).to_contain_text(receipt["result_sha256"])
        for rank in range(1, receipt["batch_size"] + 1):
            expect(
                panel.get_by_role("region", name=f"Selection rank {rank}", exact=True)
            ).to_be_visible()
        if saved["calculation"]["schema_version"] in {6, 7} and any(
            "fit_diagnostics" in r["model"]
            for r in saved["calculation"]["shared_model"]["response_models"]
        ):
            for item in saved["calculation"]["shared_model"]["response_models"]:
                goal = next(
                    response
                    for response in saved["calculation"]["objective"]["responses"]
                    if response["response_id"] == item["response_id"]
                )
                section = panel.get_by_role(
                    "region",
                    name="Surrogate fit diagnostics: " + goal["name"],
                    exact=True,
                )
                expect(section).to_be_visible()
                rows = section.get_by_role(
                    "table",
                    name="Surrogate fit diagnostics: " + goal["name"],
                    exact=True,
                ).locator("tbody tr")
                evidence = item["model"]["fit_diagnostics"]
                expect(rows).to_have_count(len(evidence["start_best_evaluations"]))
                for index, best in enumerate(evidence["start_best_evaluations"]):
                    assert float(rows.nth(index).locator("td").nth(1).inner_text()) == (
                        -best["negative_log_likelihood"]
                    )
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1100})
                wait_for_layout_settled(page)
                section = panel.locator(".bo-fit-response").first
                assert section.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
                section.screenshot(path=str(output / f"restarted-fit-{width}.png"))
        assert writes == []
        page.screenshot(path=str(output / "restarted-batch.png"), full_page=True)
    result = {
        "synthetic": True,
        "restart_restore": True,
        "batch_id": receipt["batch_id"],
        "result_sha256": receipt["result_sha256"],
        "writes": writes,
    }
    (output / "restart-receipt.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, choices=range(1, 9), default=1)
    parser.add_argument("--restore-receipt", type=Path)
    parser.add_argument("--fit-quality", action="store_true")
    parser.add_argument("--curve-policy", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            print(
                json.dumps(
                    verify_desirability_restart(
                        browser, args.base_url, args.output, args.restore_receipt
                    )
                    if args.restore_receipt
                    else verify_desirability_review(
                        browser,
                        args.base_url,
                        args.output,
                        args.batch_size,
                        args.fit_quality,
                        args.curve_policy,
                    )
                )
            )
        finally:
            browser.close()
