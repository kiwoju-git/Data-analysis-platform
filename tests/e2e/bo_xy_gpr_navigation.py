"""Built AI-to-GPR navigation with one opt-in synthetic-data model fit."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Browser, Page, expect, sync_playwright

from app_readiness import diagnosed_page, wait_for_app_ready, wait_for_layout_settled

AI_ROUTE = "/analysis?domain=ai-ml-experimental-design"
GP_ROUTE = "/analysis/regression/regression.gaussian_process"


def _dataset(page: Page, base: str) -> dict:
    csv = "response,predictor\n1.1,0\n1.5,1\n2.2,2\n2.8,3\n4.1,4\n5.3,5\n6.8,6\n8.4,7\n"
    uploaded = page.request.post(
        base + "/api/v1/datasets",
        headers={"Origin": base},
        multipart={
            "file": {
                "name": "synthetic-bo-xy-gpr-navigation.csv",
                "mimeType": "text/csv",
                "buffer": csv.encode("utf-8"),
            }
        },
    )
    assert uploaded.status == 201, uploaded.text()
    confirmed = page.request.post(
        base + f"/api/v1/datasets/{uploaded.json()['dataset_id']}/confirm-parsing",
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
    assert confirmed.status == 201, confirmed.text()
    return confirmed.json()


def _fit(page: Page, base: str, version: dict, output: Path) -> dict:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.locator(".language-switcher button").filter(has_text="ENG").click()
    page.locator(".analysis-domain-landing").get_by_role(
        "button", name="Gaussian Process Regression", exact=True
    ).click()
    wait_for_app_ready(page, "en", GP_ROUTE)
    columns = {column["display_name"]: column for column in version["columns"]}
    rows_response = page.request.get(
        base + f"/api/v1/dataset-versions/{version['version_id']}/rows?offset=0&limit=8"
    )
    assert rows_response.status == 200, rows_response.text()
    rows = rows_response.json()
    assert [column["display_name"] for column in rows["columns"]] == [
        "response",
        "predictor",
    ]
    assert [row["values"] for row in rows["rows"]] == [
        ["1.1", "0"],
        ["1.5", "1"],
        ["2.2", "2"],
        ["2.8", "3"],
        ["4.1", "4"],
        ["5.3", "5"],
        ["6.8", "6"],
        ["8.4", "7"],
    ]
    panel = page.locator(".gp-regression-panel")
    panel.get_by_label("Response", exact=True).select_option(
        columns["response"]["column_id"]
    )
    panel.get_by_role("group", name="Predictors", exact=True).get_by_role(
        "checkbox", name="predictor", exact=True
    ).check()
    page.screenshot(path=str(output / "gpr-fit-default-form.png"), full_page=True)
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == "/api/v1/analysis-runs",
        timeout=180_000,
    ) as pending:
        panel.get_by_role(
            "button", name="Run Gaussian Process Regression", exact=True
        ).click()
    response = pending.value
    request, envelope = response.request.post_data_json, response.json()
    for name, value in (
        ("request", request),
        ("result", envelope),
        ("source", version),
        ("rows", rows),
    ):
        (output / f"gpr-fit-{name}.json").write_text(
            json.dumps(value, indent=2), encoding="utf-8"
        )
    assert response.status == 201, envelope
    assert envelope["status"] == "succeeded"
    assert envelope["dataset_version_id"] == version["version_id"]
    assert envelope["provenance"]["source_schema_hash"] == version["schema_hash"]
    result = envelope["result"]
    assert result["response"]["column_id"] == columns["response"]["column_id"]
    assert result["response"]["display_name"] == "response"
    assert [
        (item["column_id"], item["display_name"]) for item in result["predictors"]
    ] == [(columns["predictor"]["column_id"], "predictor")]
    assert result["sample"]["n_total"] == result["sample"]["n_used"] == 8
    assert result["sample"]["n_excluded"] == 0
    defaults = {
        "kernel_preset": "matern_5_2_ard",
        "noise_mode": "estimate",
        "standardize_predictors": True,
        "normalize_response": True,
        "validation_method": "k_fold",
        "cv_folds": 5,
        "cv_shuffle": True,
        "random_seed": 20260829,
        "optimizer_restarts": 3,
        "cv_optimizer_restarts": 0,
    }
    for key, value in defaults.items():
        assert result["method"][key] == value, (key, result["method"])
    assert request["options"]["cv"]["method"] == "k_fold"
    assert result["validation_plan"]["effective_method"] == "k_fold"
    points = result["diagnostics"]["points"]
    assert [point["row_index"] for point in points] == list(range(8))
    assert [point["observed"] for point in points] == [
        1.1,
        1.5,
        2.2,
        2.8,
        4.1,
        5.3,
        6.8,
        8.4,
    ]
    assert all(math.isfinite(point["cross_validated_fitted"]) for point in points)
    training_range = result["training_ranges"][0]
    assert training_range["column_id"] == columns["predictor"]["column_id"]
    assert (training_range["minimum"], training_range["maximum"]) == (0, 7)
    model_id = result["model_manifest"]["model_id"]
    saved_response = page.request.get(base + f"/api/v1/regression-models/{model_id}")
    assert saved_response.status == 200, saved_response.text()
    saved_model = saved_response.json()
    (output / "gpr-fit-model.json").write_text(
        json.dumps(saved_model, indent=2), encoding="utf-8"
    )
    manifest = saved_model["manifest"]
    assert saved_model["analysis_id"] == envelope["analysis_id"]
    assert saved_model["manifest_sha256"] == result["model_manifest"]["manifest_sha256"]
    assert manifest["dataset_version_id"] == version["version_id"]
    assert manifest["source_schema_hash"] == version["schema_hash"]
    assert (
        manifest["source_canonical_artifact_sha256"]
        == version["canonical_artifact"]["sha256"]
    )
    assert manifest["response"] == result["response"]
    assert manifest["predictors"] == result["predictors"]
    expect(page.locator(".gp-results")).to_be_visible()
    expect(page.locator(".gp-point-prediction")).to_be_visible()
    expect(page.locator("#active-dataset-version")).to_have_value(version["version_id"])
    wait_for_layout_settled(page)
    page.screenshot(path=str(output / "gpr-fit-results.png"), full_page=True)
    return {
        "analysis_id": envelope["analysis_id"],
        "model_id": model_id,
        "default_options_preserved": defaults,
        "exact_xy_labels_and_observed_values": True,
        "saved_source_hashes_verified": True,
        "n_used": 8,
        "cross_validated_points": len(points),
        "warnings": envelope["warnings"],
    }


def verify_bo_xy_gpr_navigation(
    browser: Browser,
    base: str,
    output: Path,
    *,
    isolated_workspace: bool,
    fit: bool = False,
) -> dict:
    if not isolated_workspace:
        raise ValueError("Navigation fixture requires an owned synthetic workspace")
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(browser, output, "bo-xy-gpr-navigation", locale="en") as page:
        page.set_viewport_size({"width": 1440, "height": 1000})
        version = _dataset(page, base)
        version_id = version["version_id"]
        catalog = page.request.get(base + "/api/v1/analysis-methods").json()
        method = next(
            item
            for item in catalog["methods"]
            if item["method_id"] == "regression.gaussian_process"
        )
        writes: list[str] = []
        page.on(
            "request",
            lambda request: writes.append(urlsplit(request.url).path)
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and urlsplit(request.url).path.startswith("/api/")
            else None,
        )
        page.goto(base + AI_ROUTE, wait_until="domcontentloaded")
        wait_for_app_ready(page, "en", AI_ROUTE)
        page.locator("#active-dataset-version").select_option(version_id)
        expect(page.locator("#active-dataset-version")).to_have_value(version_id)
        layouts = []
        for locale, language in (("en", "ENG"), ("ko", "KOR")):
            page.locator(".language-switcher button").filter(has_text=language).click()
            for width, height in ((1440, 1000), (390, 844)):
                page.set_viewport_size({"width": width, "height": height})
                wait_for_app_ready(page, locale, AI_ROUTE)
                landing = page.locator(
                    '.analysis-domain-landing[data-domain-id="ai-ml-experimental-design"]'
                )
                expect(
                    landing.locator("button.analysis-domain-method-card")
                ).to_have_count(3)
                link = landing.get_by_role(
                    "button", name=method[f"label_{locale}"], exact=True
                )
                expect(link).to_be_enabled()
                wait_for_layout_settled(page)
                assert link.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
                landing.screenshot(path=str(output / f"gpr-ai-{locale}-{width}.png"))
                link.focus()
                link.press("Enter")
                wait_for_app_ready(page, locale, GP_ROUTE)
                assert urlsplit(page.url).path == GP_ROUTE
                assert parse_qs(urlsplit(page.url).query).get("dataset_version_id") == [
                    version_id
                ]
                expect(page.locator("#active-dataset-version")).to_have_value(
                    version_id
                )
                panel = page.locator(".gp-regression-panel")
                expect(panel).to_be_visible()
                response_label = "Response" if locale == "en" else "반응 변수"
                response = panel.get_by_label(response_label, exact=True)
                expect(
                    response.locator("option").filter(has_text="response")
                ).to_have_count(1)
                expect(
                    response.locator("option").filter(has_text="predictor")
                ).to_have_count(1)
                if width == 1440:
                    regression = page.locator(
                        "#sidebar-tree-correlation-regression-prediction"
                    )
                    expect(
                        regression.get_by_role(
                            "button",
                            name=method[f"label_{locale}"],
                            exact=True,
                            include_hidden=True,
                        )
                    ).to_have_attribute("aria-current", "page")
                    expect(
                        page.locator(
                            "#sidebar-tree-ai-ml-experimental-design"
                        ).get_by_role(
                            "button",
                            name=method[f"label_{locale}"],
                            exact=True,
                            include_hidden=True,
                        )
                    ).to_have_count(0)
                wait_for_layout_settled(page)
                page.screenshot(path=str(output / f"gpr-form-{locale}-{width}.png"))
                layouts.append({"locale": locale, "width": width, "route": GP_ROUTE})
                page.go_back()
                wait_for_app_ready(page, locale, AI_ROUTE)
        assert not writes, writes
        navigation_writes = list(writes)
        fit_receipt = _fit(page, base, version, output) if fit else None
        assert writes == (["/api/v1/analysis-runs"] if fit else []), writes
        receipt = {
            "status": "succeeded",
            "synthetic": True,
            "browser": browser.version,
            "dataset_version_id": version_id,
            "row_count": version["row_count"],
            "layouts": layouts,
            "header_selection_preserved": True,
            "canonical_regression_sidebar": True,
            "keyboard_activation": True,
            "gp_fit_executed": fit,
            "fit": fit_receipt,
            "api_writes_during_navigation": navigation_writes,
            "api_writes_total": writes,
        }
        (output / "gpr-navigation-receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--isolated-workspace", action="store_true")
    parser.add_argument("--fit", action="store_true")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            print(
                json.dumps(
                    verify_bo_xy_gpr_navigation(
                        browser,
                        args.base_url,
                        args.output,
                        isolated_workspace=args.isolated_workspace,
                        fit=args.fit,
                    ),
                    indent=2,
                )
            )
        finally:
            browser.close()
