"""Black-box archive smoke: no imports from the installed application's source."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.error
import urllib.request
from pathlib import Path


def request(base: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        base + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def create_dataset(base: str, content: str) -> dict:
    uploaded = request(
        base,
        "/api/v1/datasets/paste",
        {"content": content, "original_filename": "release-synthetic.csv"},
    )
    return request(
        base,
        f"/api/v1/datasets/{uploaded['dataset_id']}/confirm-parsing",
        {
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


def verify_application(base: str, output: Path) -> dict:
    from playwright.sync_api import expect, sync_playwright

    info = request(base, "/api/v1/runtime-info")
    content = (
        "response,x1,x2,group\n"
        + "\n".join(
            f"{math.sin(i/3)+.35*((i*7)%11)/4:.12f},{i/3:.12f},{((i*7)%11)/4:.12f},{'A' if i <= 8 else 'B'}"
            for i in range(1, 17)
        )
        + "\n"
    )
    version = create_dataset(base, content)
    ids = [column["column_id"] for column in version["columns"]]
    methods = [
        (
            "eda.principal_components",
            "0.1.0",
            {"column_ids": ids[:3]},
            "principal_components_analysis",
        ),
        (
            "regression.partial_least_squares",
            "0.1.0",
            {
                "response_column_id": ids[0],
                "predictor_column_ids": ids[1:3],
                "max_components": 2,
                "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 19},
            },
            "partial_least_squares_regression",
        ),
        (
            "regression.gaussian_process",
            "0.3.0",
            {
                "response_column_id": ids[0],
                "predictor_column_ids": ids[1:3],
                "optimizer_restarts": 0,
                "cv_optimizer_restarts": 0,
                "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 29},
                "profile_points": 10,
                "surface_grid_size": 10,
                "time_budget_seconds": 120,
            },
            "gaussian_process_regression",
        ),
        (
            "quality.two_variances",
            "0.1.0",
            {
                "response_column_id": ids[0],
                "group_column_id": ids[3],
                "numerator_group_key": "A",
                "denominator_group_key": "B",
            },
            "two_variances_test",
        ),
    ]
    results = []
    reports = []
    for method_id, method_version, options, summary in methods:
        source = request(
            base,
            "/api/v1/analysis-runs",
            {
                "method_id": method_id,
                "method_version": method_version,
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": options,
            },
        )
        assert source["result"]["summary_type"] == summary
        analysis_id = source["analysis_id"]
        restored = request(base, f"/api/v1/analysis-runs/{analysis_id}/result")
        assert restored["result"] == source["result"]
        export = request(
            base, f"/api/v1/analysis-runs/{analysis_id}/exports/html", {"locale": "en"}
        )
        with urllib.request.urlopen(
            base
            + f"/api/v1/analysis-runs/{analysis_id}/exports/{export['export_id']}/download",
            timeout=30,
        ) as response:
            html = response.read()
        assert b"<svg" in html and b"<table" in html and b"<script" not in html
        path = output / f"{method_id}.html"
        path.write_bytes(html)
        reports.append(path)
        assert (
            request(base, f"/api/v1/analysis-runs/{analysis_id}/result")["result"]
            == source["result"]
        )
        results.append(
            {
                "method_id": method_id,
                "analysis_id": analysis_id,
                "result_sha256": hashlib.sha256(
                    json.dumps(source["result"], sort_keys=True).encode()
                ).hexdigest(),
                "html_sha256": hashlib.sha256(html).hexdigest(),
            }
        )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.add_init_script("localStorage.setItem('statistical-twin.locale','en')")
        page = context.new_page()
        page.goto(base + "/home", wait_until="networkidle")
        expect(
            page.get_by_role("heading", name="Statistical Twin", exact=True)
        ).to_be_visible()
        assert "version mismatch" not in page.locator("body").inner_text().lower()
        page.screenshot(path=str(output / "release-home.png"), full_page=True)
        for route, selector in (
            (
                "/analysis/quality/quality.two_variances",
                '[data-analysis-execution="quality.two_variances"]',
            ),
            (
                "/analysis/regression/regression.gaussian_process",
                '[data-analysis-execution="regression.gaussian_process"]',
            ),
            ("/reports", ".report-center-page #report-center-title"),
        ):
            page.goto(base + route, wait_until="networkidle")
            page.reload(wait_until="networkidle")
            expect(page.locator(selector)).to_be_visible(timeout=30_000)
            expect(page.locator(".error-box[role=alert]")).to_have_count(0)
        for report in reports:
            context.set_offline(True)
            page.goto(report.as_uri())
            expect(page.locator("svg").first).to_be_visible()
            assert page.locator("table").count() > 0
            context.set_offline(False)
        browser.close()
    return {
        "runtime": info,
        "dataset_version_id": version["version_id"],
        "analyses": results,
        "checks": [
            "CSV paste",
            "PCA",
            "PLS",
            "GPR",
            "Two Variances",
            "result restore",
            "HTML download",
            "offline HTML",
            "built home",
            "deep-link refresh",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Run validation without Python optimization")
    args.output.mkdir(parents=True, exist_ok=True)
    result = verify_application(args.url, args.output)
    (args.output / "application-smoke.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
