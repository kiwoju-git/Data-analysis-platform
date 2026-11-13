"""Canonical regression-to-GPR navigation with a read-only CLI runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from playwright.sync_api import Page, expect, sync_playwright

from app_readiness import wait_for_app_ready

REGRESSION_ROUTE = "/analysis?domain=correlation-regression-prediction"
GP_ROUTE = "/analysis/regression/regression.gaussian_process"


def verify_gpr_navigation(page: Page, dataset_version_id: str, *, locale: str) -> dict:
    """Open the real catalog control and prove source continuity without a fit."""
    selected = page.locator("#active-dataset-version")
    expect(selected).to_have_value(dataset_version_id)
    source_label = selected.locator("option:checked").inner_text()
    base = f"{urlsplit(page.url).scheme}://{urlsplit(page.url).netloc}"
    catalog_response = page.request.get(base + "/api/v1/analysis-methods")
    assert catalog_response.ok, catalog_response.status
    method = next(
        item
        for item in catalog_response.json()["methods"]
        if item["method_id"] == "regression.gaussian_process"
    )
    source_response = page.request.get(
        base + f"/api/v1/dataset-versions/{dataset_version_id}"
    )
    assert source_response.ok, source_response.status
    source = source_response.json()
    landing = page.locator(
        '.analysis-domain-landing[data-domain-id="correlation-regression-prediction"]'
    )
    control = landing.get_by_role("button", name=method[f"label_{locale}"], exact=True)
    expect(control).to_be_visible()
    expect(control).to_be_enabled()
    control.click()
    wait_for_app_ready(page, locale, GP_ROUTE)
    assert urlsplit(page.url).path == GP_ROUTE
    assert parse_qs(urlsplit(page.url).query).get("dataset_version_id") == [
        dataset_version_id
    ]
    expect(selected).to_have_value(dataset_version_id)
    expect(selected.locator("option:checked")).to_have_text(source_label)
    panel = page.locator(".gp-regression-panel")
    expect(panel).to_be_visible()
    response = panel.get_by_label(
        "Response" if locale == "en" else "반응 변수", exact=True
    )
    eligible_columns = [
        column
        for column in source["columns"]
        if column["data_type"] in {"integer", "decimal"}
        and column["role"] != "id"
        and column["measurement_level"] != "nominal"
    ]
    assert eligible_columns, "GPR navigation requires a numeric source column"
    expect(response.locator("option")).to_have_count(len(eligible_columns) + 1)
    for column in eligible_columns:
        option = response.locator(f'option[value="{column["column_id"]}"]')
        expect(option).to_have_text(column["display_name"])
    return {
        "method_id": method["method_id"],
        "accessible_role": "button",
        "accessible_name": method[f"label_{locale}"],
        "dataset_version_id": dataset_version_id,
        "source_schema_hash": source["schema_hash"],
        "source_numeric_column_ids": [
            column["column_id"] for column in eligible_columns
        ],
        "url": page.url,
        "panel_visible": True,
        "fit_executed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--dataset-version-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--locale", choices=("ko", "en"), default="ko")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        try:
            page = context.new_page()
            writes = []
            page.on(
                "request",
                lambda request: writes.append(urlsplit(request.url).path)
                if request.method in {"POST", "PUT", "PATCH", "DELETE"}
                and urlsplit(request.url).path.startswith("/api/")
                else None,
            )
            page.goto(
                args.base_url
                + REGRESSION_ROUTE
                + "&"
                + urlencode({"dataset_version_id": args.dataset_version_id}),
                wait_until="domcontentloaded",
            )
            language = "KOR" if args.locale == "ko" else "ENG"
            page.locator(".language-switcher button").filter(has_text=language).click()
            wait_for_app_ready(page, args.locale, REGRESSION_ROUTE)
            page.screenshot(
                path=str(args.output / "gpr-navigation.png"), full_page=True
            )
            receipt = verify_gpr_navigation(
                page, args.dataset_version_id, locale=args.locale
            )
            assert writes == [], writes
            receipt["api_writes"] = writes
            page.screenshot(
                path=str(args.output / "gpr-navigation-panel.png"), full_page=True
            )
            (args.output / "receipt.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(receipt, ensure_ascii=True, indent=2))
        finally:
            context.close()
            browser.close()
