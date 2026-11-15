"""Built UI six-response import, recommendation, actual measurements and restore."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from app_readiness import diagnosed_page, wait_for_bayesian_ready
from bo_dataset_import import ROUTE, seed


def verify_six_responses(browser, base, output, *, isolated_workspace=False):
    if not isolated_workspace:
        raise ValueError("Six-response E2E requires an isolated synthetic workspace")
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "six-responses",
        init_script="localStorage.setItem('statistical-twin.locale','en')",
    ) as page:
        page.set_default_timeout(30000)
        errors, posts = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: posts.append(request.url)
            if request.method == "POST" and "/bayesian-studies/" in request.url
            else None,
        )
        names = ["Yield", "Strength", "Purity", "Recovery", "Stability", "Durability"]
        csv = (
            "x,"
            + ",".join(names)
            + "\n"
            + "\n".join(
                ",".join(
                    str(value) for value in [x, *[10 + 2 * x + i for i in range(6)]]
                )
                for x in (0, 5, 10)
            )
            + "\n"
        ).encode()
        version = seed(page, base, csv)
        page.goto(base + ROUTE, wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        page.locator("#active-dataset-version").select_option(version["version_id"])
        page.locator('select:has(option[value="dataset"])').select_option("dataset")
        form = page.locator(".bo-dataset-import")
        form.get_by_label("Import study name", exact=True).fill(
            "Synthetic six responses"
        )
        form.get_by_label("X 1", exact=True).select_option(
            version["columns"][0]["column_id"]
        )
        form.get_by_label("X 1 low", exact=True).fill("0")
        form.get_by_label("X 1 high", exact=True).fill("10")
        form.get_by_label("Response objective", exact=True).select_option("vector")
        for i in range(6):
            if i:
                form.get_by_role("button", name="Add response", exact=True).click()
            form.get_by_label(f"Y {i + 1}", exact=True).select_option(
                version["columns"][i + 1]["column_id"]
            )
            form.get_by_label(f"Response {i + 1} lower", exact=True).fill("0")
            form.get_by_label(f"Response {i + 1} target", exact=True).fill("40")
        expect(
            form.get_by_role("button", name="Add response", exact=True)
        ).to_be_disabled()
        for width in (1024, 1440):
            page.set_viewport_size({"width": width, "height": 960})
            form.get_by_label("Y 6", exact=True).scroll_into_view_if_needed()
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            page.screenshot(path=str(output / f"six-inputs-en-{width}.png"))
        before = len(posts)
        page.get_by_role("button", name="Korean", exact=True).click()
        expect(form.get_by_label("Y 6", exact=True)).to_have_value(
            version["columns"][6]["column_id"]
        )
        expect(form.get_by_label("반응 6 목표값", exact=True)).to_have_value("40")
        page.screenshot(path=str(output / "six-inputs-ko.png"))
        page.get_by_role("button", name="영어", exact=True).click()
        assert len(posts) == before
        with page.expect_response("**/bayesian-studies/import-preflight") as response:
            form.get_by_role("button", name="Preflight import", exact=True).click()
        assert response.value.status == 200, response.value.text()
        with page.expect_response("**/bayesian-studies/from-dataset") as response:
            form.get_by_role(
                "button", name="Import observations and create study", exact=True
            ).click()
        assert response.value.status == 201, response.value.text()
        study = response.value.json()
        assert len(study["objective"]["responses"]) == 6
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        panel = page.get_by_role(
            "region", name="Multiresponse candidate review", exact=True
        )
        panel.get_by_label("Experiments in this batch (1-8)", exact=True).select_option(
            "1"
        )
        with page.expect_response(
            api + "/desirability-reviews", timeout=180000
        ) as response:
            panel.get_by_role("button", name="Review ordered batch", exact=True).click()
        assert response.value.status == 200, response.value.text()
        review = response.value.json()
        assert len(review["calculation"]["items"][0]["response_predictions"]) == 6
        with page.expect_response(
            lambda response: "/desirability-" in response.url
            and response.url.endswith("/confirm"),
            timeout=120000,
        ) as response:
            panel.get_by_role(
                "button", name="Confirm entire pending batch", exact=True
            ).click()
        assert response.value.status == 201, response.value.text()
        current = page.request.get(api).json()
        pending = next(
            trial for trial in current["trials"] if trial["state"] == "pending"
        )
        entry = page.get_by_role(
            "region", name="Multiresponse observation entry", exact=True
        )
        for i, item in enumerate(study["objective"]["responses"]):
            entry.locator(
                f'input[data-trial-id="{pending["trial_id"]}"][data-response-id="{item["response_id"]}"]'
            ).fill(str(20 + i))
        entry.get_by_role("button", name="Review measurements", exact=True).click()
        with page.expect_response(api + "/observations/batch") as response:
            entry.get_by_role("button", name="Confirm measurements", exact=True).click()
        assert response.value.status == 200, response.value.text()
        current = page.request.get(api).json()
        assert (
            current["completed_trial_count"] == 4
            and current["pending_trial_count"] == 0
        )
        assert current["trials"][:3] == study["trials"]
        assert len(current["trials"][-1]["response_values"]) == 6
        page.reload(wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        expect(panel).to_be_visible()
        assert page.request.get(api).json() == current
        page.screenshot(path=str(output / "six-restored.png"), full_page=True)
        assert not errors, errors
        receipt = {
            "synthetic": True,
            "responses": 6,
            "csv_sha256": hashlib.sha256(csv).hexdigest(),
            "api_contract": page.request.get(base + "/api/v1/runtime-info").json()[
                "api_contract_version"
            ],
            "review_id": review["review_id"],
            "source_unchanged": True,
            "restored": True,
            "locales": ["en", "ko"],
            "pageerrors": errors,
        }
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--isolated-workspace", action="store_true")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            verify_six_responses(
                browser,
                args.base_url,
                args.output,
                isolated_workspace=args.isolated_workspace,
            )
        finally:
            browser.close()
