"""Real built UI: measured mixture import through saved plots and the next batch."""

import argparse
import json
import math
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from app_readiness import diagnosed_page, wait_for_bayesian_ready
from bo_dataset_import import seed
from bo_saved_views import verify_saved_matrix
from playwright.sync_api import expect, sync_playwright

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def verify_mixture_completion(browser, base: str, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "mixture",
        init_script="localStorage.setItem('statistical-twin.locale','en')",
    ) as page:
        page.set_default_timeout(20000)
        csv = (
            "성분 A,Component B,Fixed,Temperature,Lot,Yield\n"
            + "\n".join(
                f"{a},{b},0.1,{temp},{lot},{20 + 3*a - b + temp/100}"
                for a, b, temp, lot in (
                    (0.2, 0.7, 10, "A"),
                    (0.3, 0.6, 20, "A"),
                    (0.4, 0.5, 30, "A"),
                    (0.5, 0.4, 10, "A"),
                    (0.2, 0.7, 30, "B"),
                    (0.3, 0.6, 10, "B"),
                    (0.4, 0.5, 20, "B"),
                    (0.5, 0.4, 30, "B"),
                )
            )
            + "\n"
        )
        version = seed(page, base, csv.encode("utf-8"))
        page.goto(base + ROUTE, wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        page.locator("#active-dataset-version").select_option(version["version_id"])
        page.locator('select:has(option[value="dataset"])').select_option("dataset")
        form = page.get_by_role("region", name="Start BO from existing X/Y", exact=True)
        form.get_by_label("Import study name", exact=True).fill(
            "Synthetic measured mixture"
        )
        form.get_by_role("checkbox", name="Mixture study", exact=True).check()
        for _ in range(3):
            form.get_by_role("button", name="Add predictor", exact=True).click()
        form.get_by_label("Pseudocomponent coding", exact=True).select_option("lower")
        for index in range(5):
            form.get_by_label(f"X {index + 1}", exact=True).select_option(
                version["columns"][index]["column_id"]
            )
        for index, bounds in enumerate(
            (("0.1", "0.8"), ("0.1", "0.8"), ("0.1", "0.1"))
        ):
            form.get_by_role("checkbox", name="Mixture components", exact=True).nth(
                index
            ).check()
            form.get_by_label(f"X {index + 1} low", exact=True).fill(bounds[0])
            form.get_by_label(f"X {index + 1} high", exact=True).fill(bounds[1])
        form.get_by_label("X 4 type", exact=True).select_option("discrete_numeric")
        for field, value in (("low", "10"), ("high", "30"), ("step", "10")):
            form.get_by_label(f"X 4 {field}", exact=True).fill(value)
        form.get_by_label("X 5 type", exact=True).select_option("nominal")
        form.get_by_label("X 5 levels", exact=True).fill("A\nB")
        form.get_by_label("Response objective", exact=True).select_option("vector")
        form.get_by_label("Y 1", exact=True).select_option(
            version["columns"][5]["column_id"]
        )
        form.get_by_label("Response 1 lower", exact=True).fill("0")
        form.get_by_label("Response 1 target", exact=True).fill("30")
        with page.expect_response("**/bayesian-studies/import-preflight") as reviewed:
            form.get_by_role("button", name="Preflight import", exact=True).click()
        assert reviewed.value.status == 200, reviewed.value.text()
        assert reviewed.value.json()["schema_version"] == 2
        with page.expect_response("**/bayesian-studies/from-dataset") as imported:
            form.get_by_role(
                "button", name="Import observations and create study", exact=True
            ).click()
        assert imported.value.status == 201, imported.value.text()
        study = imported.value.json()
        assert (
            study["study_schema_version"] == 8 and study["completed_trial_count"] == 8
        )
        assert study["factors"][0]["name"] == "성분 A"
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        workspace = page.get_by_role("region", name="Mixture study", exact=True)
        with page.expect_response(
            lambda r: r.url == api + "/mixture-planning-models" and r.request.method == "POST",
            timeout=90000,
        ) as fitted:
            workspace.get_by_role("button", name="Fit surrogate", exact=True).click()
        assert fitted.value.status == 201, fitted.value.text()
        model = fitted.value.json()
        diagnostics = workspace.get_by_role("region", name="Actual holds", exact=True)
        saved = verify_saved_matrix(
            browser,
            page,
            api,
            model,
            diagnostics,
            "Evaluate full conditional profiler",
            output / "saved-matrix",
        )
        workspace.get_by_label("Candidate count", exact=True).fill("8")
        with page.expect_response(
            api + "/mixture-candidate-revisions", timeout=90000
        ) as candidate:
            workspace.get_by_role(
                "button", name="Generate candidates", exact=True
            ).click()
        assert candidate.value.status == 201, candidate.value.text()
        keys = [c["factor_id"] for c in study["mixture"]["components"]]
        for point in candidate.value.json()["items"]:
            assert math.isclose(
                sum(point["actual_coordinates"][key] for key in keys), 1, abs_tol=1e-14
            )
        workspace.get_by_label("Selection policy", exact=True).select_option("maximin")
        workspace.get_by_label("Batch size", exact=True).fill("2")
        with page.expect_response(
            api + "/mixture-selections", timeout=90000
        ) as selected:
            workspace.get_by_role(
                "button", name="Review selection", exact=True
            ).first.click()
        assert selected.value.status == 201, selected.value.text()
        selection = selected.value.json()
        workspace.get_by_role(
            "checkbox", name="I checked the displayed source and settings", exact=True
        ).first.check()
        with page.expect_response(
            "**/mixture-selections/*/confirm", timeout=90000
        ) as confirmed:
            workspace.get_by_role(
                "button", name="Confirm reviewed trials", exact=True
            ).click()
        assert confirmed.value.status == 201, confirmed.value.text()
        expect(page).to_have_url(re.compile("mixture_planning_batch_id=" + selection["selection_id"]))
        assert urlsplit(page.url).path == ROUTE
        assert parse_qs(urlsplit(page.url).query) == {
            "dataset_version_id": [version["version_id"]],
            "study_id": [study["study_id"]],
            "mixture_planning_batch_id": [selection["selection_id"]],
        }
        current = page.request.get(api).json()
        assert current["pending_trial_count"] == 2
        for trial in current["trials"]:
            if trial["state"] == "pending":
                workspace.get_by_label(
                    f'{trial["trial_number"]}: Yield', exact=True
                ).fill("22.125")
        with page.expect_response(api + "/observations/batch") as observed:
            workspace.get_by_role(
                "button", name="Save observations", exact=True
            ).click()
        assert observed.value.status == 200, observed.value.text()
        assert observed.value.json()["study"]["completed_trial_count"] == 10
        with page.expect_response(
            lambda r: r.url == api + "/mixture-planning-models" and r.request.method == "POST",
            timeout=90000,
        ) as refitted:
            workspace.get_by_role("button", name="Fit surrogate", exact=True).click()
        assert refitted.value.status == 201, refitted.value.text()
        assert refitted.value.json()["history_sha256"] != model["history_sha256"]
        with page.expect_response(
            api + "/mixture-candidate-revisions", timeout=90000
        ) as next_candidates:
            workspace.get_by_role(
                "button", name="Generate candidates", exact=True
            ).click()
        assert next_candidates.value.status == 201, next_candidates.value.text()
        page.goto(
            base
            + ROUTE
            + "?study_id="
            + study["study_id"]
            + "&view_id="
            + saved["view_id"],
            wait_until="domcontentloaded",
        )
        wait_for_bayesian_ready(page, "en", ROUTE)
        restored = page.get_by_role("region", name="Saved diagnostic views", exact=True)
        expect(restored).to_contain_text(saved["view_sha256"])
        expect(restored).to_contain_text(model["snapshot_sha256"])
        assert page.request.get(api + "/views/" + saved["view_id"]).json() == saved
        page.screenshot(path=output / "historical-mixture-view.png", full_page=True)
        receipt = {
            "synthetic": True,
            "import_schema": 2,
            "completed_before": 8,
            "completed_after": 10,
            "source_model_sha256": model["snapshot_sha256"],
            "next_model_sha256": refitted.value.json()["snapshot_sha256"],
            "saved_view_sha256": saved["view_sha256"],
            "candidate_count": len(next_candidates.value.json()["items"]),
            "saved_matrix": json.loads(
                (output / "saved-matrix/saved-profiler-receipt.json").read_text(encoding="utf-8")
            ),
        }
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            verify_mixture_completion(browser, args.base_url, args.output)
        finally:
            browser.close()
