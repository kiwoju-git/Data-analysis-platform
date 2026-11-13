"""Built-UI measured X/Y import and real multiresponse recommendation regression."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from app_readiness import diagnosed_page, wait_for_bayesian_ready

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def seed(page, base, csv_bytes=None):
    response = page.request.post(
        base + "/api/v1/datasets",
        headers={"Origin": base},
        multipart={
            "file": {
                "name": "synthetic-import.csv",
                "mimeType": "text/csv",
                "buffer": csv_bytes
                if csv_bytes is not None
                else b"x,Yield,Cost\n6.944186141483639,40,3\n3.6300444412189226,41,4\n0.4113583179671809,42,5\n",
            }
        },
    )
    assert response.status == 201, response.text()
    response = page.request.post(
        base + "/api/v1/datasets/" + response.json()["dataset_id"] + "/confirm-parsing",
        headers={"Origin": base},
        data={
            "parsing": {
                "kind": "delimited_text",
                "encoding": "utf-8",
                "delimiter": ",",
                "quote_char": '"',
                "decimal": ".",
                "thousands": None,
                "has_header": True,
                "header_row": 1,
                "data_start_row": 2,
                "missing_tokens": ["", "NA"],
            },
            "columns": [],
        },
    )
    assert response.status == 201, response.text()
    return response.json()


def verify_category_import(browser, base, output):
    """Saved correlation policy is explicit; category strings remain untouched."""
    with diagnosed_page(
        browser,
        output,
        "category-import",
        init_script="localStorage.setItem('statistical-twin.locale','en')",
    ) as page:
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        version = seed(page, base, "등급,Yield\n낮음,40\n중간,42\n높음,44\n".encode())
        page.goto(base + ROUTE, wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        page.locator("#active-dataset-version").select_option(version["version_id"])
        page.locator('select:has(option[value="dataset"])').select_option("dataset")
        form = page.get_by_role("region", name="Start BO from existing X/Y", exact=True)
        form.get_by_label("Import study name", exact=True).fill(
            "Synthetic category import"
        )
        form.get_by_label("X 1", exact=True).select_option(
            version["columns"][0]["column_id"]
        )
        form.get_by_label("X 1 type", exact=True).select_option("ordinal")
        form.get_by_label("X 1 levels", exact=True).fill("낮음\n중간\n높음")
        form.get_by_label("Response objective", exact=True).select_option("vector")
        form.get_by_label("Y 1", exact=True).select_option(
            version["columns"][1]["column_id"]
        )
        form.get_by_label("Response 1 lower", exact=True).fill("0")
        form.get_by_label("Response 1 target", exact=True).fill("100")
        advanced = form.locator("details").filter(
            has=page.get_by_text("Advanced options", exact=True)
        )
        expect(advanced).not_to_have_attribute("open", "")
        advanced.locator("summary").click()
        policy = form.get_by_label("X 1 Category correlation policy", exact=True)
        policy.select_option("ordinal_monotone_latent_rbf_v1")
        form.get_by_label("X 1 type", exact=True).select_option("nominal")
        advanced.locator("summary").click()
        expect(form.locator('td p[role="alert"]')).to_be_visible()
        posts = []
        page.on(
            "request",
            lambda request: posts.append(request.url)
            if request.method == "POST"
            else None,
        )
        form.get_by_role("button", name="Preflight import", exact=True).click()
        expect(form.locator(".error-box code")).to_have_text(
            "bayesian_category_correlation_policy_invalid"
        )
        assert posts == [], posts
        advanced.locator("summary").click()
        policy.select_option("unequal_hyperspherical_correlation_v1")
        with page.expect_response("**/bayesian-studies/import-preflight") as reviewed:
            form.get_by_role("button", name="Preflight import", exact=True).click()
        assert reviewed.value.status == 200, reviewed.value.text()
        policy.select_option("equal_positive_correlation_v1")
        expect(
            form.get_by_role("region", name="Import review", exact=True)
        ).to_have_count(0)
        policy.select_option("unequal_hyperspherical_correlation_v1")
        page.locator(".language-switcher button").filter(has_text="KOR").click()
        expect(page.get_by_label("X 1 범주 상관 정책", exact=True)).to_have_value(
            "unequal_hyperspherical_correlation_v1"
        )
        expect(page.get_by_label("X 1 수준", exact=True)).to_have_value(
            "낮음\n중간\n높음"
        )
        page.set_viewport_size({"width": 1024, "height": 900})
        page.locator(".language-switcher button").filter(has_text="ENG").click()
        with page.expect_response("**/bayesian-studies/import-preflight") as reviewed:
            form.get_by_role("button", name="Preflight import", exact=True).click()
        assert reviewed.value.status == 200, reviewed.value.text()
        assert reviewed.value.json()["n_used"] == 3
        with page.expect_response("**/bayesian-studies/from-dataset") as created:
            form.get_by_role(
                "button", name="Import observations and create study", exact=True
            ).click()
        assert created.value.status == 201, created.value.text()
        study = created.value.json()
        assert study["study_schema_version"] == 7
        assert study["factors"][0]["name"] == "등급"
        assert study["factors"][0]["levels"] == ["낮음", "중간", "높음"]
        assert (
            study["factors"][0]["correlation_policy"]
            == "unequal_hyperspherical_correlation_v1"
        )
        assert [row["actual_coordinates"]["factor_1"] for row in study["trials"]] == [
            "낮음",
            "중간",
            "높음",
        ]
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        page.reload(wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        assert page.request.get(api).json() == study
        page.screenshot(
            path=str(output / "category-import-restored.png"), full_page=True
        )
        assert not errors, errors
        return {
            "synthetic": True,
            "study_id": study["study_id"],
            "correlation_policy": study["factors"][0]["correlation_policy"],
            "restored_unchanged": True,
            "korean_categories_preserved": True,
            "invalid_policy_post_count": 0,
            "pageerrors": errors,
        }


def verify_bo_dataset_import(browser, base, output, *, isolated_workspace=False):
    if not isolated_workspace:
        raise ValueError(
            "Synthetic BO import requires an explicitly isolated workspace"
        )
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "dataset-import",
        init_script="localStorage.setItem('statistical-twin.locale','en')",
    ) as page:
        page.set_default_timeout(20000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        version = seed(page, base)
        other_version = seed(page, base)
        page.goto(base + ROUTE, wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        page.locator("#active-dataset-version").select_option(version["version_id"])
        page.locator('select:has(option[value="dataset"])').select_option("dataset")
        form = page.get_by_role("region", name="Start BO from existing X/Y", exact=True)
        expect(form).to_be_visible()
        # A-B-A ownership: a completed old preflight must not resurrect review.
        form.get_by_label("Import study name", exact=True).fill("Old draft")
        form.get_by_label("X 1", exact=True).select_option(
            version["columns"][0]["column_id"]
        )
        form.get_by_label("X 1 low", exact=True).fill("0")
        form.get_by_label("X 1 high", exact=True).fill("10")
        form.get_by_label("Y", exact=True).select_option(
            version["columns"][1]["column_id"]
        )
        held = []

        def hold(route):
            held.append((route, route.fetch()))

        page.route("**/bayesian-studies/import-preflight", hold)
        form.get_by_role("button", name="Preflight import", exact=True).click()
        expect(form.get_by_role("status")).to_be_visible()
        page.locator("#active-dataset-version").select_option(
            other_version["version_id"]
        )
        expect(form.get_by_label("Import study name", exact=True)).to_have_value("")
        page.locator("#active-dataset-version").select_option(version["version_id"])
        expect(form.get_by_label("Import study name", exact=True)).to_have_value("")
        assert len(held) == 1
        held[0][0].fulfill(response=held[0][1])
        page.unroute("**/bayesian-studies/import-preflight", hold)
        expect(
            form.get_by_role(
                "button", name="Import observations and create study", exact=True
            )
        ).to_have_count(0)
        form.get_by_label("Import study name", exact=True).fill(
            "Synthetic measured multiresponse"
        )
        form.get_by_label("X 1", exact=True).select_option(
            version["columns"][0]["column_id"]
        )
        form.get_by_label("X 1 low", exact=True).fill("0")
        form.get_by_label("X 1 high", exact=True).fill("10")
        form.get_by_label("Response objective", exact=True).select_option("vector")
        form.get_by_label("Y 1", exact=True).select_option(
            version["columns"][1]["column_id"]
        )
        form.get_by_role("button", name="Add response", exact=True).click()
        form.get_by_label("Y 2", exact=True).select_option(
            version["columns"][2]["column_id"]
        )
        form.get_by_label("Response 1 lower", exact=True).fill("0")
        form.get_by_label("Response 1 target", exact=True).fill("100")
        form.get_by_label("Response 2 goal", exact=True).select_option("minimize")
        form.get_by_label("Response 2 target", exact=True).fill("1")
        form.get_by_label("Response 2 upper", exact=True).fill("10")
        advanced = form.locator("details").filter(
            has=page.get_by_text("Advanced options", exact=True)
        )
        expect(advanced).not_to_have_attribute("open", "")
        advanced.locator("summary").click()
        form.get_by_role("button", name="Add constraint", exact=True).click()
        form.get_by_label("Coefficient constraint_1 factor_1", exact=True).fill("1")
        form.get_by_label("Bound constraint_1", exact=True).fill("10")
        expect(form.get_by_label("X 1", exact=True)).to_be_disabled()
        expect(form.get_by_label("X 1 type", exact=True)).to_be_disabled()
        writes = []
        layout_checks = []
        page.on(
            "request",
            lambda request: writes.append(request.url)
            if request.method == "POST"
            else None,
        )
        for width in (1024, 1440):
            page.set_viewport_size({"width": width, "height": 900})
            page.locator(".language-switcher button").filter(has_text="KOR").click()
            expect(page.get_by_label("가져오기 Study 이름", exact=True)).to_have_value(
                "Synthetic measured multiresponse"
            )
            page.locator(".language-switcher button").filter(has_text="ENG").click()
            expect(form.get_by_label("Response 2 upper", exact=True)).to_have_value(
                "10"
            )
            layout = form.evaluate("""root => {
                const rows = [...root.querySelectorAll('label')].flatMap(label => {
                    const control = label.querySelector('input,select,textarea');
                    const text = [...label.childNodes].find(node =>
                        node.nodeType === Node.TEXT_NODE && node.textContent.trim());
                    if (!control || !text || !control.getClientRects().length) return [];
                    const range = document.createRange();
                    range.selectNodeContents(text);
                    const caption = range.getBoundingClientRect();
                    const input = control.getBoundingClientRect();
                    const box = label.getBoundingClientRect();
                    return [{gap: input.top - caption.bottom,
                        contained: input.left >= box.left - 1 && input.right <= box.right + 1}];
                });
                return {rows, overflow: document.documentElement.scrollWidth > innerWidth + 1};
            }""")
            assert len(layout["rows"]) >= 8, layout
            assert not layout["overflow"], layout
            assert all(
                row["gap"] >= 5 and row["contained"] for row in layout["rows"]
            ), layout
            layout_checks.append({"width": width, **layout})
        assert writes == [], writes
        page.screenshot(path=str(output / "import-form.png"), full_page=True)
        with page.expect_response("**/bayesian-studies/import-preflight") as preflight:
            form.get_by_role("button", name="Preflight import", exact=True).click()
        assert preflight.value.status == 200, preflight.value.text()
        assert preflight.value.json()["n_used"] == 3
        assert preflight.value.request.post_data_json["constraints"][0]["bound"] == 10
        form.get_by_label("Bound constraint_1", exact=True).fill("9")
        expect(
            form.get_by_role("region", name="Import review", exact=True)
        ).to_have_count(0)
        form.get_by_label("Bound constraint_1", exact=True).fill("10")
        # Editing invalidates the reviewed request before it can be committed.
        form.get_by_label("X 1 high", exact=True).fill("11")
        expect(
            form.get_by_role(
                "button", name="Import observations and create study", exact=True
            )
        ).to_have_count(0)
        form.get_by_label("X 1 high", exact=True).fill("10")
        form.get_by_role("button", name="Preflight import", exact=True).click()
        commit = form.get_by_role(
            "button", name="Import observations and create study", exact=True
        )
        expect(commit).to_be_enabled()
        with page.expect_response("**/bayesian-studies/from-dataset") as created:
            commit.click()
        assert created.value.status == 201, created.value.text()
        study = created.value.json()
        assert study["constraints"][0]["bound"] == 10
        assert study["constraints"][0]["terms"] == [
            {"factor_id": "factor_1", "coefficient": 1}
        ]
        assert study["completed_trial_count"] == 3 and study["pending_trial_count"] == 0
        assert [row["response_values"] for row in study["trials"]] == [
            {"response_1": 40, "response_2": 3},
            {"response_1": 41, "response_2": 4},
            {"response_1": 42, "response_2": 5},
        ]
        expect(form).to_have_count(0)
        panel = page.get_by_role(
            "region", name="Multiresponse candidate review", exact=True
        )
        panel.get_by_label("Experiments in this batch (1-8)", exact=True).select_option(
            "2"
        )
        api = base + "/api/v1/bayesian-studies/" + study["study_id"]
        with page.expect_response(
            api + "/desirability-reviews", timeout=120000
        ) as reviewed:
            panel.get_by_role("button", name="Review ordered batch", exact=True).click()
        assert reviewed.value.status == 200, reviewed.value.text()
        with page.expect_response(
            lambda response: "/desirability-" in response.url
            and response.request.method == "POST"
            and not response.url.endswith("reviews"),
            timeout=120000,
        ) as confirmed:
            panel.get_by_role(
                "button", name="Confirm entire pending batch", exact=True
            ).click()
        assert confirmed.value.status in (200, 201), confirmed.value.text()
        current = page.request.get(api).json()
        assert (
            current["completed_trial_count"] == 3
            and current["pending_trial_count"] == 2
        )
        entry = page.get_by_role(
            "region", name="Multiresponse observation entry", exact=True
        )
        for trial in current["trials"]:
            if trial["state"] != "pending":
                continue
            x = trial["actual_coordinates"]["factor_1"]
            for response_id, value in {
                "response_1": 43 - 0.02 * x * x,
                "response_2": 4 + 0.1 * x,
            }.items():
                entry.locator(
                    f'input[data-trial-id="{trial["trial_id"]}"][data-response-id="{response_id}"]'
                ).fill(str(value))
        entry.get_by_role("button", name="Review measurements", exact=True).click()
        with page.expect_response(api + "/observations/batch") as observed:
            entry.get_by_role("button", name="Confirm measurements", exact=True).click()
        assert observed.value.status == 200, observed.value.text()
        panel.get_by_label("Experiments in this batch (1-8)", exact=True).select_option(
            "1"
        )
        with page.expect_response(
            api + "/desirability-reviews", timeout=120000
        ) as next_review:
            panel.get_by_role("button", name="Review ordered batch", exact=True).click()
        assert next_review.value.status == 200, next_review.value.text()
        original_hash = study["initial_design"]["observations_sha256"]
        restored = page.request.get(api).json()
        assert restored["initial_design"]["observations_sha256"] == original_hash
        assert restored["constraints"] == study["constraints"]
        assert (
            restored["completed_trial_count"] == 5
            and restored["pending_trial_count"] == 0
        )
        page.screenshot(path=str(output / "imported-multiresponse.png"), full_page=True)
        page.reload(wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        expect(
            page.get_by_role(
                "region", name="Multiresponse candidate review", exact=True
            )
        ).to_be_visible()
        sources = page.request.get(
            base
            + "/api/v1/reports/sources?source_kind=bayesian_history_revision&limit=20"
        )
        assert sources.status == 200, sources.text()
        descriptor = next(
            item
            for item in sources.json()["items"]
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
        create_report = page.locator("[data-create-managed-report]")
        expect(create_report).to_be_enabled()
        with page.expect_response(
            lambda response: response.url == base + "/api/v1/reports"
            and response.request.method == "POST"
        ) as exported:
            create_report.click()
        assert exported.value.status == 201, exported.value.text()
        report = exported.value.json()
        assert report["source"] == descriptor["source"]
        with page.expect_download() as download:
            page.locator(f'[data-managed-report="{report["export_id"]}"]').get_by_role(
                "button", name="Download", exact=True
            ).click()
        html_path = output / "imported-history-report.html"
        download.value.save_as(html_path)
        assert hashlib.sha256(html_path.read_bytes()).hexdigest() == report["sha256"]
        assert page.request.get(api).json() == restored
        offline = page.context.new_page()
        try:
            page.context.set_offline(True)
            offline.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded")
            expect(offline.locator("body")).to_contain_text("Yield")
            expect(offline.locator("body")).to_contain_text("Cost")
            offline.screenshot(
                path=str(output / "offline-history-report.png"), full_page=True
            )
        finally:
            offline.close()
            page.context.set_offline(False)
        assert not errors, errors
        receipt = {
            "synthetic": True,
            "browser": browser.version,
            "api_contract": 43,
            "study_id": study["study_id"],
            "imported": 3,
            "completed_after_batch": 5,
            "q2_review_http": reviewed.value.status,
            "next_q1_http": next_review.value.status,
            "source_observations_sha256": original_hash,
            "pageerrors": errors,
            "restore": True,
            "source_a_b_a_preflight_discarded": True,
            "locale_resize_preserved_draft_without_post": True,
            "layout_checks": layout_checks,
            "managed_report_sha256": report["sha256"],
            "managed_report_offline_open": True,
            "advanced_numeric_constraint_restored": restored["constraints"]
            == study["constraints"],
            "category_import": verify_category_import(browser, base, output),
        }
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--isolated-workspace", action="store_true")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            print(
                json.dumps(
                    verify_bo_dataset_import(
                        browser,
                        args.base_url,
                        args.output,
                        isolated_workspace=args.isolated_workspace,
                    ),
                    indent=2,
                )
            )
        finally:
            browser.close()
