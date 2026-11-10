"""Built UI model-free augmentation, exact confirmation and offline report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from app_readiness import diagnosed_page, wait_for_app_ready, wait_for_layout_settled
from playwright.sync_api import Browser, expect, sync_playwright

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def verify_augmentation(browser: Browser, base: str, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "augmentation",
        init_script="localStorage.setItem('statistical-twin.locale', 'en');",
    ) as page:
        created = page.request.post(
            base + "/api/v1/bayesian-studies",
            data={
                "name": "Synthetic augmentation",
                "initial_design_seed": 41,
                "initial_design_size": 4,
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
        errors, writes = [], []
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
        panel = page.get_by_role("region", name="Experimental augmentation", exact=True)
        panel.get_by_label("Candidate table name", exact=True).fill(
            "Synthetic independent table"
        )
        panel.get_by_label("Uniform candidates (1–10000)", exact=True).fill("60")
        with page.expect_response(
            api + "/candidate-revisions", timeout=90000
        ) as generated:
            panel.get_by_role("button", name="Generate new table", exact=True).click()
        assert generated.value.status == 201, generated.value.text()
        candidates = generated.value.json()
        assert candidates["revision"]["schema_version"] == 2
        assert candidates["revision"]["model_id"] is None
        panel.get_by_role("button", name="Next page", exact=True).click()
        expect(panel.get_by_role("table").first.locator("tbody tr")).to_have_count(10)
        panel.get_by_label("Augmentation strategy", exact=True).select_option(
            "greedy_mixed_maximin_v1"
        )
        panel.get_by_label("Batch size (1–8)", exact=True).fill("2")
        with page.expect_response(
            lambda response: response.url == api + "/augmentations"
            and response.request.method == "POST",
            timeout=90000,
        ) as selected:
            panel.get_by_role(
                "button", name="Save automatic selection", exact=True
            ).click()
        assert selected.value.status == 201, selected.value.text()
        selection = selected.value.json()
        assert selection["calculation"]["source_row_count"] == 60
        assert selection["calculation"]["prediction_evaluations"] == 0
        assert page.request.get(api).json() == before
        trace = panel.get_by_role("table", name="Automatic selection trace", exact=True)
        expect(trace.locator("tbody tr")).to_have_count(2)
        confirm_url = api + "/augmentations/" + selection["selection_id"] + "/confirm"
        with page.expect_response(confirm_url, timeout=90000) as confirmed:
            panel.get_by_role(
                "button", name="Confirm entire pending batch", exact=True
            ).click()
        assert confirmed.value.status == 201, confirmed.value.text()
        batch = confirmed.value.json()
        expect(page).to_have_url(
            base
            + ROUTE
            + "?study_id="
            + study["study_id"]
            + "&augmentation_batch_id="
            + batch["batch_id"]
        )
        page.reload(wait_until="domcontentloaded")
        wait_for_app_ready(page, "en", ROUTE)
        count = len(writes)
        for locale, button, title in (
            ("ko", "KOR", "저장된 실험 보강 배치"),
            ("en", "ENG", "Saved augmentation batch"),
        ):
            page.locator(".language-switcher button").filter(has_text=button).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            saved = page.get_by_role("region", name=title, exact=True)
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                wait_for_layout_settled(page)
                expect(saved).to_contain_text(batch["result_sha256"])
                assert saved.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
                page.screenshot(
                    path=output / f"augmentation-{locale}-{width}.png", full_page=True
                )
        assert len(writes) == count
        saved = page.get_by_role("region", name="Saved augmentation batch", exact=True)
        with page.expect_response(
            lambda response: response.url == base + "/api/v1/reports"
            and response.request.method == "POST",
            timeout=30000,
        ) as exported:
            saved.get_by_role(
                "button", name="Create managed HTML report", exact=True
            ).click()
        assert exported.value.status == 201, exported.value.text()
        report = exported.value.json()
        assert (
            report["source"]["attachment"]["result_payload_sha256"]
            == batch["result_sha256"]
        )
        with page.expect_download() as downloaded:
            saved.get_by_role(
                "button", name="Download verified report", exact=True
            ).click()
        path = output / "augmentation-report.html"
        downloaded.value.save_as(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == report["sha256"]
        offline = browser.new_context(offline=True)
        try:
            report_page = offline.new_page()
            report_page.goto(path.resolve().as_uri(), wait_until="domcontentloaded")
            expect(report_page.locator("body")).to_contain_text(
                selection["result_sha256"]
            )
            assert report_page.locator("table tbody tr").count() >= 2
        finally:
            offline.close()
        assert page.request.get(api).json()["trial_count"] == before["trial_count"] + 2
        assert not any(url.endswith("/planning-models") for url in writes)
        assert not errors, errors
        receipt = {
            "synthetic": True,
            "browser": browser.version,
            "study_id": study["study_id"],
            "batch_id": batch["batch_id"],
            "result_sha256": batch["result_sha256"],
            "report_sha256": report["sha256"],
            "no_fit": True,
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
            print(json.dumps(verify_augmentation(browser, args.base_url, args.output)))
        finally:
            browser.close()
