"""Built mixed BO UI with synthetic typed identities and exact stored reports.

Study creation is API-seeded; observations, fit, profiling, candidate review,
confirmation and report export are real UI actions, not simulated requests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app_readiness import (
    diagnosed_page,
    wait_for_bayesian_ready,
    wait_for_layout_settled,
)
from playwright.sync_api import Browser, expect, sync_playwright
from bo_loo import verify_loo
from bo_auto_strategy import verify_auto_strategy
from bo_auto_evidence import verify_saved_auto_evidence

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def verify_mixed_builder(page, base: str) -> dict:
    page.goto(base + ROUTE, wait_until="domcontentloaded")
    wait_for_bayesian_ready(page, "en", ROUTE)
    page.get_by_role("button", name="Create a new study", exact=True).click()
    page.get_by_label("Study creation", exact=True).select_option("mixed")
    builder = page.get_by_role("region", name="Mixed-factor Bayesian study", exact=True)
    builder.get_by_label("Study name", exact=True).fill("Synthetic mixed UI creation")
    builder.get_by_label("Initial design seed", exact=True).fill("31")
    builder.get_by_label("Initial conditions (2–64)", exact=True).fill("12")
    numeric = builder.get_by_role("group", name="Factor 1", exact=True)
    numeric.get_by_label("Factor ID", exact=True).fill("x")
    numeric.get_by_label("Factor name", exact=True).fill("Temperature")
    numeric.get_by_label("Factor kind", exact=True).select_option("discrete_numeric")
    numeric.get_by_label("Lower bound", exact=True).fill("0")
    numeric.get_by_label("Upper bound", exact=True).fill("1")
    numeric.get_by_label("Executable step", exact=True).fill("0.1")
    numeric.get_by_label("Display decimals", exact=True).fill("1")
    nominal = builder.get_by_role("group", name="Factor 2", exact=True)
    nominal.get_by_label("Factor ID", exact=True).fill("material")
    nominal.get_by_label("Factor name", exact=True).fill("Material")
    nominal.get_by_label("Category correlation policy", exact=True).select_option(
        "unequal_hyperspherical_correlation_v1"
    )
    nominal.get_by_label("Material: Declared levels 1", exact=True).fill("001")
    nominal.get_by_label("Material: Declared levels 2", exact=True).fill("한글 <raw>")
    nominal.get_by_role("button", name="Add level", exact=True).click()
    nominal.get_by_label("Material: Declared levels 3", exact=True).fill("=FORMULA()")
    builder.get_by_role("button", name="Add factor", exact=True).click()
    ordinal = builder.get_by_role("group", name="Factor 3", exact=True)
    ordinal.get_by_label("Factor ID", exact=True).fill("grade")
    ordinal.get_by_label("Factor name", exact=True).fill("Grade")
    ordinal.get_by_label("Factor kind", exact=True).select_option("ordinal")
    ordinal.get_by_label("Category correlation policy", exact=True).select_option(
        "ordinal_monotone_latent_rbf_v1"
    )
    ordinal.get_by_label("Grade: Declared levels 1", exact=True).fill("low")
    ordinal.get_by_label("Grade: Declared levels 2", exact=True).fill("middle")
    ordinal.get_by_role("button", name="Add level", exact=True).click()
    ordinal.get_by_label("Grade: Declared levels 3", exact=True).fill("high")
    ordinal.get_by_role("button", name="Move level earlier", exact=True).nth(2).click()
    for index, value in enumerate(["low", "high", "middle"]):
        expect(ordinal.locator("ol input").nth(index)).to_have_value(value)
    constraints = builder.get_by_role(
        "group", name="Actual-unit numeric constraints", exact=True
    )
    constraints.get_by_role("button", name="Add constraint", exact=True).click()
    constraints.get_by_label("Constraint name", exact=True).fill(
        "Synthetic temperature bound"
    )
    constraints.get_by_label("Temperature: Coefficient", exact=True).fill("1")
    constraints.get_by_label("Bound", exact=True).fill("1")
    constraints.get_by_label("Relation", exact=True).select_option("less_than_or_equal")
    assert constraints.get_by_label("Material: Coefficient", exact=True).count() == 0
    builder.get_by_label("Response 1 name", exact=True).fill("Yield")
    builder.get_by_label("Response 1 lower", exact=True).fill("0")
    builder.get_by_label("Response 1 target", exact=True).fill("10abc")
    requests = []
    endpoint = base + "/api/v1/bayesian-studies/mixed"
    page.on(
        "request",
        lambda request: requests.append(request.post_data_json)
        if request.url == endpoint and request.method == "POST"
        else None,
    )
    builder.get_by_role("button", name="Create mixed-factor study", exact=True).click()
    expect(builder.get_by_role("alert")).to_be_visible()
    assert not requests
    builder.get_by_label("Response 1 target", exact=True).fill("10")
    page.locator(".language-switcher button").filter(has_text="KOR").click()
    expect(page.locator("html")).to_have_attribute("lang", "ko")
    page.locator(".language-switcher button").filter(has_text="ENG").click()
    expect(builder.get_by_label("Study name", exact=True)).to_have_value(
        "Synthetic mixed UI creation"
    )
    for index, value in enumerate(["low", "high", "middle"]):
        expect(ordinal.locator("ol input").nth(index)).to_have_value(value)
    with page.expect_response(endpoint) as created:
        builder.get_by_role(
            "button", name="Create mixed-factor study", exact=True
        ).click()
    assert created.value.status == 201, created.value.text()
    study = created.value.json()
    assert len(requests) == 1
    assert study["factors"][0]["step"] == 0.1
    assert study["constraints"][0]["terms"] == [{"factor_id": "x", "coefficient": 1}]
    assert study["factors"][1]["levels"] == ["001", "한글 <raw>", "=FORMULA()"]
    assert study["factors"][2]["levels"] == ["low", "high", "middle"]
    assert (
        study["factors"][1]["correlation_policy"]
        == "unequal_hyperspherical_correlation_v1"
    )
    assert study["factors"][2]["correlation_policy"] == "ordinal_monotone_latent_rbf_v1"
    expect(page).to_have_url(base + ROUTE + "?study_id=" + study["study_id"])
    return {
        "study_id": study["study_id"],
        "definition_sha256": study["definition_sha256"],
        "create_posts": 1,
        "invalid_draft_posts": 0,
    }


def verify_mixed_workflow(browser: Browser, base: str, output: Path, *, auto_evidence_only=False) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "mixed-planning",
        init_script="localStorage.setItem('statistical-twin.locale', 'en');",
    ) as page:
        builder_receipt = verify_mixed_builder(page, base)
        created = page.request.post(
            base + "/api/v1/bayesian-studies/mixed",
            headers={"Origin": base},
            data={
                "schema_version": 7,
                "name": "Synthetic typed BO",
                "initial_design_seed": 31,
                "initial_design_size": 12,
                "factors": [
                    {
                        "factor_id": "x",
                        "name": "Temperature",
                        "domain_kind": "continuous",
                        "low": 0,
                        "high": 1,
                    },
                    {
                        "factor_id": "material",
                        "name": "Material",
                        "domain_kind": "nominal",
                        "levels": ["1", "한글 <raw>", "=FORMULA()"],
                        "correlation_policy": "equal_positive_correlation_v1",
                    },
                    {
                        "factor_id": "grade",
                        "name": "Grade",
                        "domain_kind": "ordinal",
                        "levels": ["low", "middle", "high"],
                        "correlation_policy": "ordinal_monotone_latent_rbf_v1",
                    },
                ],
                "objective": {
                    "name": "Synthetic response goal",
                    "goal_type": "desirability",
                    "observation_policy": "complete_response_vector",
                    "curve_policy": "derringer_suich_linear_v1",
                    "responses": [
                        {
                            "response_id": "yield",
                            "name": "Yield",
                            "unit": "g",
                            "goal": "maximize",
                            "lower": 0,
                            "target": 10,
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
        wait_for_bayesian_ready(page, "en", ROUTE)
        source = page.get_by_role(
            "region", name="Mixed-factor Bayesian study", exact=True
        )
        expect(source).to_contain_text("한글 <raw>")
        for trial in study["trials"]:
            point = trial["actual_coordinates"]
            measured = (
                2
                + point["x"] * 3
                + ["1", "한글 <raw>", "=FORMULA()"].index(point["material"]) * 0.25
            )
            measured += ["low", "middle", "high"].index(point["grade"]) * 0.4
            source.get_by_label(
                f"Trial {trial['trial_number']}: Yield", exact=True
            ).fill(str(measured))
        source.get_by_role(
            "button", name="Review complete observations", exact=True
        ).click()
        with page.expect_response(api + "/observations/batch") as observations:
            source.get_by_role(
                "button", name="Save actual observations", exact=True
            ).click()
        assert observations.value.status == 200, observations.value.text()
        before = observations.value.json()["study"]
        assert (
            before["completed_trial_count"] == 12 and before["pending_trial_count"] == 0
        )
        panel = page.get_by_role(
            "region", name="Mixed-factor candidates and planning", exact=True
        )
        panel.get_by_label("Typed deterministic starts", exact=True).fill("1")
        panel.get_by_label("Measurement noise", exact=True).select_option("fixed")
        panel.get_by_label("Measured SD (response units)", exact=True).fill("0.05")
        with page.expect_response(
            lambda response: response.url == api + "/mixed-planning-models"
            and response.request.method == "POST",
            timeout=90000,
        ) as fitted:
            panel.get_by_role(
                "button", name="Fit and save mixed model", exact=True
            ).click()
        assert fitted.value.status == 201, fitted.value.text()
        model = fitted.value.json()
        verify_loo(page, api, model, output, mixed=True)
        expect(
            panel.get_by_role("region", name="Mixed-factor saved model", exact=True)
        ).to_contain_text(model["snapshot_sha256"])
        panel.get_by_label("Candidate table name", exact=True).fill(
            "Synthetic typed candidates"
        )
        panel.get_by_label("Uniform candidates (1–10000)", exact=True).fill("60")
        with page.expect_response(
            api + "/mixed-candidate-revisions", timeout=90000
        ) as generated:
            panel.get_by_role("button", name="Generate new table", exact=True).click()
        assert generated.value.status == 201, generated.value.text()
        candidate = generated.value.json()
        assert candidate["revision"]["row_count"] == 60
        assert all(
            isinstance(row["actual_coordinates"]["material"], str)
            for row in candidate["items"]
        )
        auto_selection = verify_auto_strategy(page, api, model, output, mixed=True, keep_selection=auto_evidence_only)
        if auto_evidence_only:
            receipt = verify_saved_auto_evidence(browser, page, api, base, model, auto_selection, output, mixed=True)
            assert not errors, errors
            receipt["pageerrors"] = errors
            (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            return receipt
        panel.get_by_role("button", name="Next page", exact=True).click()
        candidate_table = panel.get_by_role("table", name="Candidate table", exact=True)
        expect(candidate_table.locator("tbody tr")).to_have_count(10)
        evaluate_url = api + "/mixed-planning-models/" + model["model_id"] + "/evaluate"
        with page.expect_response(evaluate_url, timeout=90000) as evaluated:
            panel.get_by_role("button", name="Evaluate this page", exact=True).click()
        assert evaluated.value.status == 200, evaluated.value.text()
        assert evaluated.value.json()["model_refit"] is False
        boxes = candidate_table.get_by_role("checkbox")
        enabled = [box for box in boxes.all() if box.is_enabled()]
        assert len(enabled) >= 2
        enabled[0].check()
        enabled[1].check()
        original = panel.locator("ol.bo-planning-order code").all_text_contents()
        panel.get_by_role("button", name="Move earlier 2", exact=True).click()
        expect(panel.locator("ol.bo-planning-order code")).to_have_text(
            list(reversed(original))
        )
        panel.get_by_role("button", name="Undo selection change", exact=True).click()
        expect(panel.locator("ol.bo-planning-order code")).to_have_text(original)
        panel.get_by_role("button", name="Redo selection change", exact=True).click()
        selected_order = list(reversed(original))

        profiler = panel.get_by_role("region", name="Mixed-factor profiler", exact=True)
        profiler.get_by_label("Profile factor", exact=True).select_option("material")
        with page.expect_response(evaluate_url, timeout=90000) as profiled:
            profiler.get_by_role(
                "button", name="Declared category levels", exact=True
            ).click()
        assert profiled.value.status == 200, profiled.value.text()
        profile = profiled.value.json()
        assert [row["actual_coordinates"]["material"] for row in profile["items"]] == [
            "1",
            "한글 <raw>",
            "=FORMULA()",
        ]
        expect(profiler.locator("svg")).to_have_count(1)
        expect(profiler.locator("svg")).to_contain_text("한글 <raw>")
        profiler.get_by_label("Profile quantity", exact=True).select_option("yield")
        for metric, field in (
            ("mean", "mean_raw"),
            ("latent", "latent_standard_deviation_raw"),
            ("predictive", "predictive_standard_deviation_raw"),
        ):
            profiler.get_by_label("Response display", exact=True).select_option(metric)
            values = profiler.locator("svg [data-y]").evaluate_all(
                "els => els.map(e => Number(e.dataset.y))"
            )
            for row in profile["items"]:
                expected = row["response_predictions"][0][field]
                assert any(
                    abs(value - expected) <= 1e-12 * max(1, abs(expected))
                    for value in values
                )
        assert (
            len([url for url in writes if url == api + "/mixed-planning-models"]) == 1
        )
        profiler.get_by_label("Profile factor", exact=True).select_option("grade")
        with page.expect_response(evaluate_url, timeout=90000) as ordinal_profile:
            profiler.get_by_role(
                "button", name="Declared category levels", exact=True
            ).click()
        assert ordinal_profile.value.status == 200, ordinal_profile.value.text()
        assert [
            row["actual_coordinates"]["grade"]
            for row in ordinal_profile.value.json()["items"]
        ] == ["low", "middle", "high"]
        expect(profiler.locator("svg")).to_contain_text("middle")
        assert profiler.locator("svg").evaluate("""svg => {
            const clip = svg.querySelector('clipPath rect').getBBox();
            const points = [...svg.querySelectorAll('[data-point-id]')];
            return points.length === 3 && points.every(point => {
                const box = point.getBBox();
                return box.x > clip.x && box.y > clip.y &&
                    box.x + box.width < clip.x + clip.width &&
                    box.y + box.height < clip.y + clip.height;
            });
        }""")
        profiler.screenshot(path=output / "mixed-ordinal-profiler.png")
        assert page.request.get(api).json() == before
        with page.expect_response(
            lambda response: response.url == api + "/mixed-selections"
            and response.request.method == "POST",
            timeout=90000,
        ) as reviewed:
            panel.get_by_role(
                "button", name="Save and review ordered selection", exact=True
            ).click()
        assert reviewed.value.status == 201, reviewed.value.text()
        selection = reviewed.value.json()
        assert selection["request"]["row_ids"] == selected_order
        assert [
            row["row_id"] for row in selection["calculation"]["items"]
        ] == selected_order
        assert selection["calculation"]["model_refit"] is False
        assert page.request.get(api).json() == before
        with page.expect_response(
            api + "/mixed-selections/" + selection["selection_id"] + "/confirm",
            timeout=90000,
        ) as confirmed:
            panel.get_by_role(
                "button", name="Confirm entire pending batch", exact=True
            ).click()
        assert confirmed.value.status == 201, confirmed.value.text()
        batch = confirmed.value.json()
        exact_url = (
            base
            + ROUTE
            + "?study_id="
            + study["study_id"]
            + "&mixed_planning_batch_id="
            + batch["batch_id"]
        )
        expect(page).to_have_url(exact_url)
        page.reload(wait_until="domcontentloaded")
        wait_for_bayesian_ready(page, "en", ROUTE)
        write_count = len(writes)
        for locale, label, title in (
            ("ko", "KOR", "저장된 혼합 요인 배치"),
            ("en", "ENG", "Saved mixed-factor batch"),
        ):
            page.locator(".language-switcher button").filter(has_text=label).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            saved = page.get_by_role("region", name=title, exact=True)
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                wait_for_layout_settled(page)
                expect(saved).to_contain_text(batch["result_sha256"])
                assert saved.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
                page.screenshot(
                    path=output / f"mixed-{locale}-{width}.png", full_page=True
                )
                saved.screenshot(path=output / f"mixed-saved-{locale}-{width}.png")
            expect(
                page.get_by_role(
                    "region",
                    name="혼합 요인 Bayesian 연구"
                    if locale == "ko"
                    else "Mixed-factor Bayesian study",
                    exact=True,
                )
            ).to_contain_text("한글 <raw>")
        assert len(writes) == write_count
        saved = page.get_by_role("region", name="Saved mixed-factor batch", exact=True)
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
        with page.expect_download() as download:
            saved.get_by_role(
                "button", name="Download verified report", exact=True
            ).click()
        path = output / "mixed-report.html"
        download.value.save_as(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == report["sha256"]
        offline = browser.new_context(offline=True)
        try:
            document = offline.new_page()
            document.goto(path.resolve().as_uri(), wait_until="domcontentloaded")
            expect(document.locator("body")).to_contain_text(selection["result_sha256"])
            expect(document.locator("body")).to_contain_text("한글 <raw>")
            assert document.locator("table tbody tr").count() > 2
        finally:
            offline.close()
        after = page.request.get(api).json()
        assert after["trial_count"] == 14 and after["pending_trial_count"] == 2
        assert after["observation_history"] == before["observation_history"]
        assert (
            len([url for url in writes if url == api + "/mixed-planning-models"]) == 1
        )
        assert not errors, errors
        receipt = {
            "synthetic": True,
            "separate_ui_builder": builder_receipt,
            "browser": browser.version,
            "study_id": study["study_id"],
            "model_id": model["model_id"],
            "snapshot_sha256": model["snapshot_sha256"],
            "batch_id": batch["batch_id"],
            "result_sha256": batch["result_sha256"],
            "report_sha256": report["sha256"],
            "fit_count": 1,
            "creation": "API fixture",
            "observations_fit_profile_review_confirm_report": "built UI",
            "pageerrors": errors,
        }
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--auto-evidence-only", action="store_true")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            print(
                json.dumps(verify_mixed_workflow(browser, args.base_url, args.output, auto_evidence_only=args.auto_evidence_only))
            )
        finally:
            browser.close()
