"""Real-server stored prediction -> managed HTML -> exact restore, synthetic data only."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect

from app_readiness import wait_for_app_ready


def verify_saved_prediction_report(
    page: Page, diagnostics: Any, prediction: dict, request: dict
) -> None:
    source = prediction["saved_prediction"]["source"]
    assert source["prediction"]["storage"] == "completed_prediction"
    ref_hash = hashlib.sha256(
        json.dumps(
            source, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    previous_url = page.url
    parts = urlsplit(previous_url)
    base = f"{parts.scheme}://{parts.netloc}"
    page.goto(
        base + "/reports?source_kind=regression_prediction",
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, "ko", "/reports")
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
        path = diagnostics.html_root / f"managed-prediction-{locale}.html"
        download.value.save_as(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == report["sha256"]
        browser = page.context.browser
        assert browser is not None
        offline = browser.new_context(
            offline=True, viewport={"width": 1280, "height": 800}
        )
        try:
            view = offline.new_page()
            view.goto(path.resolve().as_uri())
            expect(view.locator("html")).to_have_attribute("lang", locale)
            expect(view.locator('[data-report-section="inputs"]')).to_be_visible()
            expect(view.locator('[data-report-section="predictions"]')).to_be_visible()
            assert view.locator("table").count() >= 4
            inputs = view.locator(
                '[data-report-section="inputs"] tbody tr'
            ).evaluate_all(
                "rows => rows.map(row => [...row.cells].map(cell => cell.textContent))"
            )
            for shown_row, saved_row in zip(inputs, request["rows"], strict=True):
                assert shown_row[0] == saved_row["client_row_id"]
                for shown_value, predictor in zip(
                    shown_row[1:], snapshot["payload"]["predictors"], strict=True
                ):
                    assert math.isclose(
                        float(shown_value),
                        saved_row["values"][predictor["column_id"]],
                        rel_tol=6e-10,
                        abs_tol=0,
                    )
            outputs = view.locator(
                '[data-report-section="predictions"] tbody tr'
            ).evaluate_all(
                "rows => rows.map(row => [...row.cells].map(cell => cell.textContent))"
            )
            by_id = {row["client_row_id"]: row for row in prediction["rows"]}
            assert len(outputs) == len(by_id)
            for shown_row in outputs:
                # HTML uses ten significant digits; compare that display precision only.
                assert math.isclose(
                    float(shown_row[1]),
                    by_id[shown_row[0]]["predicted_value"],
                    rel_tol=6e-10,
                    abs_tol=0,
                )
            assert view.locator("script, link[href], img[src]").count() == 0
            diagnostics.capture_page(view, f"managed-prediction-offline-{locale}.png")
        finally:
            offline.close()
        reports.append(report)
        diagnostics.capture_page(page, f"managed-prediction-center-{locale}.png")
    report = reports[-1]
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
        "Live managed prediction report: exact source/hash, EN/KO, offline HTML, deep-link restore passed."
    )
    diagnostics.record(
        "KO download passed with WebCrypto explicitly unavailable; this is a browser fallback test, not a second LAN device test."
    )
    page.locator(".language-switcher button").filter(has_text="KOR").click()
    page.goto(previous_url, wait_until="domcontentloaded")
    wait_for_app_ready(page, "ko", urlsplit(previous_url).path)
