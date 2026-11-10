"""Synthetic built UI candidate/profiler/ordered-confirm/exact-restore journey."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from app_readiness import diagnosed_page, wait_for_app_ready, wait_for_layout_settled
from playwright.sync_api import Browser, expect, sync_playwright

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def verify_persistent_planning(browser: Browser, base: str, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "persistent-planning",
        init_script="localStorage.setItem('statistical-twin.locale', 'en');",
    ) as page:
        created = page.request.post(
            base + "/api/v1/bayesian-studies",
            data={
                "name": "Synthetic persistent planning",
                "initial_design_seed": 42,
                "initial_design_size": 3,
                "factors": [
                    {"factor_id": "x", "name": "Temperature", "low": 0, "high": 10}
                ],
                "objective": {
                    "name": "Synthetic goals",
                    "goal_type": "desirability",
                    "observation_policy": "complete_response_vector",
                    "curve_policy": "derringer_suich_linear_v1",
                    "responses": [
                        {
                            "response_id": "yield",
                            "name": "Yield",
                            "unit": "%",
                            "goal": "maximize",
                            "lower": 0,
                            "target": 100,
                            "upper": None,
                            "importance": 1,
                        }
                    ],
                },
            },
        )
        assert created.status == 201, created.text()
        study = created.json()
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        measured = page.request.put(
            api + "/observations/batch",
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
                        "response_values": {"yield": 40.0 + index},
                    }
                    for index, trial in enumerate(study["trials"])
                ],
            },
        )
        assert measured.status == 200, measured.text()
        before = measured.json()["study"]
        writes, errors = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: writes.append(request.url)
            if "/api/" in request.url and request.method in {"POST", "PUT", "DELETE"}
            else None,
        )
        page.goto(
            base + ROUTE + "?study_id=" + study["study_id"],
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, "en", ROUTE)
        settings = page.get_by_role(
            "region", name="Multiresponse candidate review", exact=True
        )
        settings.get_by_label(
            "Experiments in this batch (1-8)", exact=True
        ).select_option("2")
        settings.get_by_label("Posterior samples (16-256)", exact=True).fill("16")
        settings.get_by_label("Yield: Signal kernel", exact=True).select_option(
            "exponential"
        )
        settings.get_by_label("Yield: Measurement noise", exact=True).select_option(
            "fixed"
        )
        settings.get_by_label("%", exact=True).fill("0.2")
        panel = page.get_by_role(
            "region", name="Saved model, candidates and profiler", exact=True
        )
        with page.expect_response(
            lambda response: response.url == api + "/planning-models"
            and response.request.method == "POST",
            timeout=90000,
        ) as fitted:
            panel.get_by_role("button", name="Fit and save model", exact=True).click()
        assert fitted.value.status == 201, fitted.value.text()
        model = fitted.value.json()
        assert page.request.get(api).json() == before
        panel.get_by_label("Candidate table name", exact=True).fill(
            "Synthetic candidate table"
        )
        panel.get_by_label("Uniform candidates (1–10000)", exact=True).fill("60")
        with page.expect_response(
            api + "/candidate-revisions", timeout=90000
        ) as generated:
            panel.get_by_role("button", name="Generate new table", exact=True).click()
        assert generated.value.status == 201, generated.value.text()
        first_page = generated.value.json()
        panel.get_by_role("button", name="Next page", exact=True).click()
        checks = panel.get_by_role("checkbox", name="Select candidate", exact=False)
        expect(checks).to_have_count(10)
        checks.nth(1).check()
        panel.get_by_role("button", name="Previous page", exact=True).click()
        expect(checks).to_have_count(50)
        checks.nth(0).check()
        panel.get_by_role("button", name="Move earlier: 2", exact=True).click()
        panel.get_by_role("button", name="Undo selection change", exact=True).click()
        panel.get_by_role("button", name="Redo selection change", exact=True).click()
        profiler = panel.get_by_role("region", name="Saved-model profiler", exact=True)
        profiler.get_by_label("Temperature", exact=True).fill("1.25")
        with page.expect_response(
            api + f"/planning-models/{model['model_id']}/evaluate", timeout=90000
        ) as point:
            profiler.get_by_role(
                "button", name="Evaluate complete point", exact=True
            ).click()
        assert point.value.status == 200, point.value.text()
        assert point.value.json()["items"][0]["actual_coordinates"] == {"x": 1.25}
        with page.expect_response(
            api + f"/planning-models/{model['model_id']}/evaluate", timeout=90000
        ) as curve:
            profiler.get_by_role(
                "button", name="Evaluate conditional curve", exact=True
            ).click()
        assert curve.value.status == 200, curve.value.text()
        assert curve.value.json()["model_refit"] is False
        curve_rows = curve.value.json()["items"]
        write_count = len(writes)
        profiler.get_by_label("Profile quantity", exact=True).select_option(
            "response:yield"
        )
        for metric in (
            "mean_raw",
            "latent_standard_deviation_raw",
            "predictive_standard_deviation_raw",
        ):
            profiler.get_by_label("Response display", exact=True).select_option(metric)
            for row in curve_rows:
                marker = profiler.locator(
                    f'[data-point-id="{row["row_id"]}:yield:{metric}"]'
                )
                expect(marker).to_have_count(1)
                assert (
                    float(marker.get_attribute("data-x"))
                    == row["actual_coordinates"]["x"]
                )
                assert (
                    float(marker.get_attribute("data-y"))
                    == row["response_predictions"][0][metric]
                )
            expect(profiler.locator("svg").first).to_be_visible()
        assert len(writes) == write_count
        with page.expect_response(
            lambda response: response.url == api + "/planning-selections"
            and response.request.method == "POST",
            timeout=90000,
        ) as reviewed:
            panel.get_by_role(
                "button", name="Save and review ordered selection", exact=True
            ).click()
        assert reviewed.value.status == 201, reviewed.value.text()
        selection = reviewed.value.json()
        assert selection["request"]["row_ids"][0] == first_page["items"][0]["row_id"]
        assert len(selection["request"]["row_ids"]) == 2
        assert page.request.get(api).json()["trial_count"] == 3
        held = []
        confirm_url = api + f"/planning-selections/{selection['selection_id']}/confirm"
        page.route(confirm_url, lambda route: held.append(route))
        panel.get_by_role(
            "button", name="Confirm entire pending batch", exact=True
        ).click()
        expect(panel.get_by_label("Candidate table name", exact=True)).to_be_disabled()
        assert len(held) == 1
        confirmed = held[0].fetch(timeout=90000)
        assert confirmed.status == 201, confirmed.text()
        batch = confirmed.json()
        held[0].fulfill(response=confirmed)
        page.unroute(confirm_url)
        expect(page).to_have_url(
            base
            + ROUTE
            + "?study_id="
            + study["study_id"]
            + "&planning_batch_id="
            + batch["batch_id"]
        )
        assert page.request.get(api).json()["trial_count"] == 5
        page.reload(wait_until="domcontentloaded")
        wait_for_app_ready(page, "en", ROUTE)
        expect(page.get_by_text(batch["batch_id"], exact=True).first).to_be_visible()
        saved = page.request.get(api + "/planning-batches/" + batch["batch_id"])
        assert (
            saved.status == 200
            and saved.json()["result_sha256"] == batch["result_sha256"]
        )
        mutating_before = len(writes)
        for locale, button, title in (
            ("ko", "KOR", "저장된 수동 후보 배치"),
            ("en", "ENG", "Saved manual candidate batch"),
        ):
            page.locator(".language-switcher button").filter(has_text=button).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            current = page.get_by_role("region", name=title, exact=True)
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                wait_for_layout_settled(page)
                assert current.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
                expect(current).to_contain_text(batch["result_sha256"])
                page.screenshot(
                    path=output / f"planning-{locale}-{width}.png", full_page=True
                )
        assert len(writes) == mutating_before
        saved_panel = page.get_by_role(
            "region", name="Saved manual candidate batch", exact=True
        )
        with page.expect_response(
            lambda response: response.url == base + "/api/v1/reports"
            and response.request.method == "POST",
            timeout=30000,
        ) as exported:
            saved_panel.get_by_role(
                "button", name="Create managed HTML report", exact=True
            ).click()
        assert exported.value.status == 201, exported.value.text()
        report = exported.value.json()
        assert report["source"]["attachment"]["batch_id"] == batch["batch_id"]
        assert (
            report["source"]["attachment"]["result_payload_sha256"]
            == batch["result_sha256"]
        )
        with page.expect_download() as downloaded:
            saved_panel.get_by_role(
                "button", name="Download verified report", exact=True
            ).click()
        html_path = output / "exact-planning-report.html"
        downloaded.value.save_as(html_path)
        assert hashlib.sha256(html_path.read_bytes()).hexdigest() == report["sha256"]
        offline = browser.new_context(offline=True)
        try:
            report_page = offline.new_page()
            report_page.goto(
                html_path.resolve().as_uri(), wait_until="domcontentloaded"
            )
            expect(report_page.locator("body")).to_contain_text(
                model["snapshot_sha256"]
            )
            assert report_page.locator("table tbody tr").count() >= 2
            report_page.screenshot(
                path=output / "planning-offline-report.png", full_page=True
            )
        finally:
            offline.close()
        assert (
            page.request.get(api + "/planning-batches/" + batch["batch_id"]).json()[
                "result_sha256"
            ]
            == batch["result_sha256"]
        )
        assert sum(url == api + "/planning-models" for url in writes) == 1
        assert not errors, errors
        page.screenshot(path=output / "planning-exact-batch.png", full_page=True)
        receipt = {
            "synthetic": True,
            "browser": browser.version,
            "study_id": study["study_id"],
            "model_id": model["model_id"],
            "model_sha256": model["snapshot_sha256"],
            "candidate_revision_id": first_page["revision"]["revision_id"],
            "batch_id": batch["batch_id"],
            "result_sha256": batch["result_sha256"],
            "fit_posts": 1,
            "report_sha256": report["sha256"],
            "locale_resize_and_profile_display_no_fit": True,
            "pageerrors": errors,
        }
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            print(
                json.dumps(
                    verify_persistent_planning(browser, args.base_url, args.output)
                )
            )
        finally:
            browser.close()
