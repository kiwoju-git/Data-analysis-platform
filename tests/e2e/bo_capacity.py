"""Real built UI: 240 measured rows, two responses, recommendation and restore."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from app_readiness import diagnosed_page, wait_for_bayesian_ready
from bo_dataset_import import ROUTE, seed


def synthetic_csv(count):
    rows = ["pressure,temp,cat_pct,cycle_time,yield_pct,tensile_strength"]
    for index in range(count):
        x = [
            index / max(1, count - 1),
            ((index * 37) % count) / count,
            ((index * 73) % count) / count,
            ((index * 97) % count) / count,
        ]
        values = [
            10 + 10 * x[0],
            50 + 50 * x[1],
            1 + 4 * x[2],
            5 + 10 * x[3],
            70 + 8 * math.sin(2 * x[0]) + 2 * x[1] - x[2] + 0.05 * math.sin(index),
            100 + 10 * x[1] + 3 * x[2] - 2 * x[3] + 0.05 * math.cos(index),
        ]
        rows.append(",".join(format(value, ".17g") for value in values))
    return ("\n".join(rows) + "\n").encode("utf-8")


def fill_import(page, base, count):
    csv = synthetic_csv(count)
    version = seed(page, base, csv)
    page.goto(base + ROUTE, wait_until="domcontentloaded")
    wait_for_bayesian_ready(page, "en", ROUTE)
    page.locator("#active-dataset-version").select_option(version["version_id"])
    page.locator('select:has(option[value="dataset"])').select_option("dataset")
    form = page.get_by_role("region", name="Start BO from existing X/Y", exact=True)
    form.get_by_label("Import study name", exact=True).fill(
        f"Synthetic {count} measured rows"
    )
    for index, (low, high) in enumerate(((10, 20), (50, 100), (1, 5), (5, 15))):
        if index:
            form.get_by_role("button", name="Add predictor", exact=True).click()
        form.get_by_label(f"X {index + 1}", exact=True).select_option(
            version["columns"][index]["column_id"]
        )
        form.get_by_label(f"X {index + 1} low", exact=True).fill(str(low))
        form.get_by_label(f"X {index + 1} high", exact=True).fill(str(high))
    form.get_by_label("Response objective", exact=True).select_option("vector")
    for index, (lower, target) in enumerate(((50, 90), (80, 120))):
        if index:
            form.get_by_role("button", name="Add response", exact=True).click()
        form.get_by_label(f"Y {index + 1}", exact=True).select_option(
            version["columns"][index + 4]["column_id"]
        )
        form.get_by_label(f"Response {index + 1} lower", exact=True).fill(str(lower))
        form.get_by_label(f"Response {index + 1} target", exact=True).fill(str(target))
    return form, hashlib.sha256(csv).hexdigest()


def verify_capacity(browser, base, output, *, isolated_workspace):
    if not isolated_workspace:
        raise ValueError(
            "Capacity tests require an explicitly isolated synthetic workspace"
        )
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "capacity240",
        init_script="localStorage.setItem('statistical-twin.locale','en')",
    ) as page:
        page.set_default_timeout(30000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        form, csv_hash = fill_import(page, base, 240)
        with page.expect_response("**/bayesian-studies/import-preflight") as response:
            form.get_by_role("button", name="Preflight import", exact=True).click()
        assert response.value.status == 200, response.value.text()
        assert response.value.json()["n_used"] == 240
        with page.expect_response("**/bayesian-studies/from-dataset") as response:
            form.get_by_role(
                "button", name="Import observations and create study", exact=True
            ).click()
        assert response.value.status == 201, response.value.text()
        study = response.value.json()
        assert study["trial_count"] == study["completed_trial_count"] == 240
        assert study["pending_trial_count"] == 0
        assert study["initial_design"]["n_used"] == 240
        original = study["initial_design"]["observations_sha256"]
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        panel = page.get_by_role(
            "region", name="Multiresponse candidate review", exact=True
        )
        budget = panel.get_by_label("Total trial budget (2–500)", exact=True)
        expect(budget).to_have_value("248")
        budget.fill("500")
        panel.get_by_label("Experiments in this batch (1-8)", exact=True).select_option(
            "1"
        )
        with page.expect_response(
            api + "/desirability-reviews", timeout=180000
        ) as response:
            panel.get_by_role("button", name="Review ordered batch", exact=True).click()
        assert response.value.status == 200, response.value.text()
        reviewed = response.value.json()
        with page.expect_response(
            lambda response: "/desirability-" in response.url
            and response.request.method == "POST"
            and not response.url.endswith("reviews"),
            timeout=120000,
        ) as response:
            panel.get_by_role(
                "button", name="Confirm entire pending batch", exact=True
            ).click()
        assert response.value.status in (200, 201), response.value.text()
        current = page.request.get(api).json()
        assert current["trial_count"] == 241 and current["pending_trial_count"] == 1
        entry = page.get_by_role(
            "region", name="Multiresponse observation entry", exact=True
        )
        for trial in current["trials"]:
            if trial["state"] == "pending":
                for response, value in zip(
                    study["objective"]["responses"], (78.25, 106.5)
                ):
                    response_id = response["response_id"]
                    entry.locator(
                        f'input[data-trial-id="{trial["trial_id"]}"][data-response-id="{response_id}"]'
                    ).fill(str(value))
        entry.get_by_role("button", name="Review measurements", exact=True).click()
        with page.expect_response(api + "/observations/batch") as response:
            entry.get_by_role("button", name="Confirm measurements", exact=True).click()
        assert response.value.status == 200, response.value.text()
        restored = page.request.get(api).json()
        assert (
            restored["completed_trial_count"] == 241
            and restored["pending_trial_count"] == 0
        )
        assert restored["initial_design"]["observations_sha256"] == original
        assert restored["trials"][:240] == study["trials"]
        page.reload(wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        expect(panel).to_be_visible()
        assert page.request.get(api).json() == restored
        page.screenshot(path=str(output / "capacity240-restored.png"), full_page=True)
        sources = page.request.get(
            base
            + "/api/v1/reports/sources?source_kind=bayesian_history_revision&limit=20"
        ).json()
        descriptor = next(
            item
            for item in sources["items"]
            if item["source"]["study_id"] == study["study_id"]
            and item["source"]["history_revision_id"]
            == restored["observation_history"]["history_revision_id"]
            and item["source"]["attachment"]["kind"] == "none"
        )
        page.goto(
            base + "/reports?source_kind=bayesian_history_revision",
            wait_until="domcontentloaded",
        )
        page.locator(
            f'[data-report-source="{descriptor["source_ref_sha256"]}"]'
        ).click()
        with page.expect_response(
            lambda response: response.url == base + "/api/v1/reports"
            and response.request.method == "POST"
        ) as response:
            page.locator("[data-create-managed-report]").click()
        assert response.value.status == 201, response.value.text()
        report = response.value.json()
        with page.expect_download() as download:
            page.locator(f'[data-managed-report="{report["export_id"]}"]').get_by_role(
                "button", name="Download", exact=True
            ).click()
        html_path = output / "capacity-history.html"
        download.value.save_as(html_path)
        assert hashlib.sha256(html_path.read_bytes()).hexdigest() == report["sha256"]
        offline = page.context.new_page()
        try:
            page.context.set_offline(True)
            offline.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded")
            expect(offline.locator("body")).to_contain_text("yield_pct")
            expect(offline.locator("body")).to_contain_text("tensile_strength")
        finally:
            offline.close()
            page.context.set_offline(False)
        assert not errors, errors
        receipt = {
            "synthetic": True,
            "csv_sha256": csv_hash,
            "n_imported": 240,
            "n_after_observation": 241,
            "history_unchanged": True,
            "review_id": reviewed["review_id"],
            "report_sha256": report["sha256"],
            "pageerrors": errors,
        }
    with diagnosed_page(
        browser,
        output,
        "capacity501",
        init_script="localStorage.setItem('statistical-twin.locale','en')",
    ) as page:
        form, _ = fill_import(page, base, 501)
        before = page.request.get(base + "/api/v1/bayesian-studies").json()
        with page.expect_response("**/bayesian-studies/import-preflight") as response:
            form.get_by_role("button", name="Preflight import", exact=True).click()
        assert response.value.status == 409, response.value.text()
        assert response.value.json()["error"]["limits"] == {
            "observed_count": 501,
            "maximum_count": 500,
        }
        alert = form.locator(".error-box")
        expect(alert).to_contain_text("501 valid measurement rows; maximum 500")
        expect(alert).to_be_focused()
        page.locator(".language-switcher button").filter(has_text="KOR").click()
        localized_alert = page.locator(".bo-dataset-import .error-box")
        expect(localized_alert).to_contain_text("사용할 측정행 501개 / 허용 500개.")
        assert page.request.get(base + "/api/v1/bayesian-studies").json() == before
        page.screenshot(path=str(output / "capacity501-rejected.png"), full_page=True)
        receipt["501_rejected_atomically"] = True
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--isolated-workspace", action="store_true")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            receipt = verify_capacity(
                browser,
                args.base_url,
                args.output,
                isolated_workspace=args.isolated_workspace,
            )
        finally:
            browser.close()
    (args.output / "receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
