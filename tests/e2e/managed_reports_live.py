"""Real-server stored prediction -> managed HTML -> exact restore, synthetic data only."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect

from app_readiness import wait_for_app_ready


def verify_saved_prediction_report(
    page: Page,
    diagnostics: Any,
    prediction: dict,
    request: dict,
    *,
    family: str = "pls",
    open_offline: bool = True,
) -> dict:
    assert family in ("pls", "gaussian_process")
    assert request["save_result"] is True
    source = prediction["saved_prediction"]["source"]
    assert source["prediction"]["storage"] == "completed_prediction"
    ref_hash = hashlib.sha256(
        json.dumps(
            source, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    previous_url = page.url
    previous_locale = page.locator("html").get_attribute("lang")
    assert previous_locale in ("ko", "en")
    parts = urlsplit(previous_url)
    base = f"{parts.scheme}://{parts.netloc}"
    page.goto(
        base + "/reports?source_kind=regression_prediction",
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, previous_locale, "/reports")
    source_button = page.locator(f'[data-report-source="{ref_hash}"]')
    expect(source_button).to_be_visible()
    source_button.click()
    selected = page.locator(f'[data-managed-report-selection="{ref_hash}"]')
    reports = []
    for locale, language in (("ko", "KOR"), ("en", "ENG")):
        page.locator(".language-switcher button").filter(has_text=language).click()
        with page.expect_response(
            lambda r: r.request.method == "POST"
            and r.url.endswith("/reports/source-snapshot")
        ) as snapshot_info:
            selected.locator("[data-view-stored-source]").click()
        assert snapshot_info.value.ok, snapshot_info.value.text()
        snapshot = snapshot_info.value.json()
        assert snapshot["source"] == source
        assert snapshot["locale"] == locale
        assert snapshot["payload"]["request"] == request
        assert snapshot["payload"]["result"]["rows"] == prediction["rows"]
        assert snapshot["payload"]["family"] == family
        assert snapshot["payload"]["model_id"] == prediction["model_id"]
        assert (
            snapshot["payload"]["model_manifest_sha256"]
            == request["expected_model_manifest_sha256"]
        )
        shown = selected.locator(".managed-report-snapshot-json")
        expect(shown).to_be_visible()
        assert json.loads(shown.inner_text()) == snapshot["payload"]
        with page.expect_response(
            lambda r: r.request.method == "POST" and r.url.endswith("/api/v1/reports")
        ) as created:
            selected.locator("[data-create-managed-report]").click()
        assert created.value.status == 201, created.value.text()
        report = created.value.json()
        assert report["source"] == source and report["locale"] == locale
        row = selected.locator(f'[data-managed-report="{report["export_id"]}"]')
        expect(row).to_be_visible()
        if locale == "ko":
            assert page.evaluate("() => !Object.hasOwn(crypto, 'subtle')")
            page.evaluate(
                "() => Object.defineProperty(crypto, 'subtle', {value: undefined, configurable: true})"
            )
        try:
            with page.expect_download() as download:
                row.get_by_role(
                    "button",
                    name="Download" if locale == "en" else "다운로드",
                    exact=True,
                ).click()
        finally:
            if locale == "ko":
                page.evaluate("() => { delete crypto.subtle; }")
        path = diagnostics.html_root / f"managed-{family}-prediction-{locale}.html"
        download.value.save_as(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == report["sha256"]
        if open_offline:
            browser = page.context.browser
            assert browser is not None
            offline = browser.new_context(
                offline=True, viewport={"width": 1280, "height": 800}
            )
            try:
                view = offline.new_page()
                verify_prediction_html(view, path, snapshot["payload"], locale)
                diagnostics.capture_page(
                    view, f"managed-{family}-prediction-offline-{locale}.png"
                )
            finally:
                offline.close()
        reports.append({"descriptor": report, "path": str(path.resolve())})
        diagnostics.capture_page(
            page, f"managed-{family}-prediction-center-{locale}.png"
        )
    report = reports[-1]["descriptor"]
    page.goto(
        base + f'/reports?report_id={report["export_id"]}',
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, "en", "/reports")
    expect(
        page.locator(f'[data-managed-report="{report["export_id"]}"]')
    ).to_be_visible()
    expect(
        page.locator(f'[data-managed-report-selection="{ref_hash}"]')
    ).to_be_visible()
    diagnostics.record(
        f"Live managed {family} prediction report: exact source/hash, EN/KO, download and deep-link restore passed; offline verification={open_offline}."
    )
    diagnostics.record(
        "KO download passed with WebCrypto explicitly unavailable; this is a browser fallback test, not a second LAN device test."
    )
    page.locator(".language-switcher button").filter(
        has_text="KOR" if previous_locale == "ko" else "ENG"
    ).click()
    page.goto(previous_url, wait_until="domcontentloaded")
    wait_for_app_ready(page, previous_locale, urlsplit(previous_url).path)
    return {
        "family": family,
        "source": source,
        "source_ref_sha256": ref_hash,
        "request": request,
        "prediction": prediction,
        "snapshot": snapshot,
        "reports": reports,
    }


def prediction_values(row: dict, family: str) -> list[float]:
    if family == "pls":
        return [row["predicted_value"]]
    if family == "gaussian_process":
        return [
            row["predicted_mean"],
            row["latent_standard_deviation"],
            row["latent_interval_95"]["lower"],
            row["latent_interval_95"]["upper"],
            row["predictive_standard_deviation"],
            row["predictive_interval_95"]["lower"],
            row["predictive_interval_95"]["upper"],
        ]
    raise AssertionError(f"Unsupported prediction family: {family}")


def verify_prediction_html(page: Page, path: Path, payload: dict, locale: str) -> None:
    """Inspect visible tables against stored values, including all GP uncertainty fields."""
    page.goto(path.resolve().as_uri())
    expect(page.locator("html")).to_have_attribute("lang", locale)
    expect(page.locator('[data-report-section="inputs"]')).to_be_visible()
    expect(page.locator('[data-report-section="predictions"]')).to_be_visible()
    assert page.locator("table").count() >= 4
    inputs = page.locator('[data-report-section="inputs"] tbody tr').evaluate_all(
        "rows => rows.map(row => [...row.cells].map(cell => cell.textContent))"
    )
    for shown, saved in zip(inputs, payload["request"]["rows"], strict=True):
        assert shown[0] == saved["client_row_id"]
        for value, predictor in zip(shown[1:], payload["predictors"], strict=True):
            assert math.isclose(
                float(value),
                saved["values"][predictor["column_id"]],
                rel_tol=6e-10,
                abs_tol=0,
            )
    outputs = page.locator('[data-report-section="predictions"] tbody tr').evaluate_all(
        "rows => rows.map(row => [...row.cells].map(cell => cell.textContent))"
    )
    by_id = {row["client_row_id"]: row for row in payload["result"]["rows"]}
    assert len(by_id) == len(outputs) == len(payload["result"]["rows"])
    assert [row[0] for row in outputs] == [
        row["client_row_id"] for row in payload["request"]["rows"]
    ]
    for shown in outputs:
        # The renderer uses ten significant digits, not changed calculation tolerances.
        for value, expected in zip(
            shown[1:],
            prediction_values(by_id[shown[0]], payload["family"]),
            strict=True,
        ):
            assert math.isclose(float(value), expected, rel_tol=6e-10, abs_tol=0)
    assert page.locator("script, link[href], img[src]").count() == 0
