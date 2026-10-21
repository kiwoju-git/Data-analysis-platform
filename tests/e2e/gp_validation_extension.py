"""Real-form GPR validation/mixed-model journey, synthetic isolated workspace only."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

from playwright.sync_api import Browser, Page, expect

from app_readiness import diagnosed_page, wait_for_app_ready
from gp_prediction_context import _restore
from managed_reports_live import verify_saved_prediction_report

ROUTE = "/analysis/regression/regression.gaussian_process"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _dataset(page: Page, base: str) -> dict:
    lines = ["response,x1,x2,category,batch,time,series"]
    for i in range(36):
        category = "level-A" if i % 2 else "level-B"
        x1, x2 = i / 5, (i * 7 % 13) / 4
        y = math.sin(x1) + 0.2 * x2 + (0.6 if i % 2 else 0) + 0.015 * (i % 3)
        lines.append(f"{y:.17g},{x1},{x2},{category},{'X'*121}-{i//6},{i},series-A")
    uploaded = page.request.post(
        base + "/api/v1/datasets",
        headers={"Origin": base},
        multipart={
            "file": {
                "name": "synthetic-gp-extension.csv",
                "mimeType": "text/csv",
                "buffer": ("\n".join(lines) + "\n").encode(),
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
    version = confirmed.json()
    updated = page.request.patch(
        base + f"/api/v1/dataset-versions/{version['version_id']}/schema",
        headers={"Origin": base},
        data={
            "expected_schema_hash": version["schema_hash"],
            "columns": [
                {
                    "column_id": c["column_id"],
                    "display_name": c["display_name"],
                    "measurement_level": "nominal",
                    "role": "id" if c["display_name"] != "category" else "feature",
                    "unit": None,
                }
                for c in version["columns"]
                if c["display_name"] in {"category", "batch", "series"}
            ],
        },
    )
    assert updated.status == 200, updated.text()
    return page.request.get(
        base + f"/api/v1/dataset-versions/{version['version_id']}"
    ).json()


def _run(page: Page, method: str, *, lag: bool = False) -> tuple[dict, dict]:
    panel = page.locator(".gp-regression-panel")
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith("/api/v1/analysis-runs"),
        timeout=180_000,
    ) as pending:
        panel.get_by_role(
            "button", name="Run Gaussian Process Regression", exact=True
        ).click()
    assert pending.value.status == 201, pending.value.text()
    request, envelope = pending.value.request.post_data_json, pending.value.json()
    result = envelope["result"]
    assert request["options"]["cv"]["method"] == method
    assert result["schema_version"] == 4
    assert result["validation_plan"]["effective_method"] == method
    assert bool(result.get("feature_lineage")) is lag
    expect(page.locator(".gp-point-prediction")).to_be_visible()
    return envelope, request


def _predict(page: Page, result: dict, *, save: bool) -> tuple[dict, dict]:
    panel = page.locator(".gp-point-prediction")
    for predictor in result["predictors"]:
        control = panel.get_by_label(predictor["display_name"] + " 1", exact=True)
        if predictor.get("kind") == "nominal":
            control.select_option("level-A")
        else:
            training_range = next(
                r
                for r in result["training_ranges"]
                if r["column_id"] == predictor["column_id"]
            )
            control.fill(str(training_range["median"]))
    if save:
        panel.locator("[data-save-completed-prediction]").check()
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith("/gaussian-process-predictions")
    ) as predicted:
        panel.get_by_role("button", name="Run Prediction", exact=True).click()
    assert predicted.value.status == 200, predicted.value.text()
    payload, request = predicted.value.json(), predicted.value.request.post_data_json
    expect(panel).to_have_attribute("data-prediction-state", "ready")
    for row in payload["rows"]:
        assert math.isfinite(row["predicted_mean"])
        assert (
            row["predictive_standard_deviation"]
            >= row["latent_standard_deviation"]
            >= 0
        )
    return payload, request


def verify_gp_validation_extension(
    browser: Browser, base: str, root: Path, *, isolated_workspace: bool
) -> dict:
    if not isolated_workspace:
        raise ValueError("GPR extension fixtures require an owned synthetic workspace")
    root.mkdir(parents=True, exist_ok=True)
    evidence: dict = {
        "fixture": "synthetic",
        "events": [],
        "execution_evidence": "real built/dev UI forms with API-prepared synthetic CSV",
    }
    with diagnosed_page(browser, root, "gp-validation-extension", locale="en") as page:
        version = _dataset(page, base)
        ids = {c["display_name"]: c["column_id"] for c in version["columns"]}
        page.goto(
            base + ROUTE + f"?dataset_version_id={version['version_id']}",
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, "en", ROUTE)
        expect(page.locator("#active-dataset-version")).to_have_value(
            version["version_id"]
        )
        panel = page.locator(".gp-regression-panel")
        panel.get_by_label("Response", exact=True).select_option(ids["response"])
        for name in ("x1", "x2", "category"):
            panel.get_by_role("group", name="Predictors", exact=True).get_by_role(
                "checkbox", name=name, exact=True
            ).check()
        panel.get_by_label("Folds", exact=True).fill("3")
        panel.get_by_text("Advanced settings", exact=True).click()
        for key, value in (
            ("Final model restarts", "0"),
            ("CV restarts", "0"),
            ("Profile points", "10"),
            ("Surface grid size", "10"),
        ):
            panel.get_by_label(key, exact=True).fill(value)
        panel.get_by_label(
            "Split repeated measurements by group or batch", exact=True
        ).check()
        panel.get_by_label("Validation group column", exact=True).select_option(
            ids["batch"]
        )
        grouped, group_request = _run(page, "group_k_fold")
        plan = grouped["result"]["validation_plan"]
        assert plan["distinct_group_count"] == 6 and plan["n_scored"] == 36
        assert all(
            fold["train_validation_group_intersection_count"] == 0
            for fold in plan["folds"]
        )
        panel.get_by_label("Validation", exact=True).select_option("time_series_split")
        panel.get_by_label("Time column", exact=True).select_option(ids["time"])
        panel.get_by_label("Numeric time unit", exact=True).fill("hour")
        timed, time_request = _run(page, "time_series_split")
        assert 0 < timed["result"]["validation_plan"]["n_scored"] < 36
        assert any(
            point["cross_validated_fitted"] is None
            for point in timed["result"]["diagnostics"]["points"]
        )
        panel.get_by_text("One-step past-observation features", exact=True).click()
        panel.get_by_label(
            "Use explicit positive observation-order lags", exact=True
        ).check()
        panel.get_by_role("group", name="Lag source columns", exact=True).get_by_role(
            "checkbox", name="response", exact=True
        ).check()
        panel.get_by_label("Positive lags, separated by commas", exact=True).fill("1")
        panel.get_by_label("Series identifier (optional)", exact=True).select_option(
            ids["series"]
        )
        lagged, lag_request = _run(page, "time_series_split", lag=True)
        lineage = lagged["result"]["feature_lineage"]
        assert lineage["prediction_input_policy"] == "explicit_past_lag_values"
        assert all(
            all(t < row["target_time"] for t in row["source_times"])
            for row in lineage["rows"]
        )
        _predict(page, lagged["result"], save=False)
        _restore(page, base, version, grouped)
        prediction, prediction_request = _predict(page, grouped["result"], save=True)
        unknown = json.loads(json.dumps(prediction_request))
        unknown["save_result"] = False
        unknown["rows"][0]["values"][ids["category"]] = "never-trained"
        rejected = page.request.post(
            base
            + f"/api/v1/regression-models/{prediction['model_id']}/gaussian-process-predictions",
            headers={"Origin": base},
            data=unknown,
        )
        assert (
            rejected.status == 422
            and rejected.json()["error"]["code"] == "gp_category_unknown"
        )
        # Unknown category is an API rejection test; the UI select only offers trained levels.
        surface = panel.locator(".gp-surface-result")
        surface.get_by_label("category \u00b7 Hold value", exact=True).select_option(
            "level-B"
        )
        with page.expect_response(
            lambda r: r.request.method == "POST"
            and r.url.endswith("/gaussian-process-predictions")
        ) as generated:
            surface.get_by_role("button", name="Generate Surface", exact=True).click()
        assert generated.value.status == 200, generated.value.text()
        surface.get_by_role("button", name="Latent SD", exact=True).click()
        with page.expect_response(
            lambda r: r.request.method == "POST"
            and r.url.endswith("/gaussian-process-predictions")
        ) as saved_view:
            surface.get_by_role("button", name="Save applied view", exact=True).click()
        assert saved_view.value.status == 200, saved_view.value.text()
        view_request = saved_view.value.request.post_data_json
        assert (
            view_request["save_result"]
            and view_request["surface_view"]["display_mode"] == "latent_sd"
        )
        assert view_request["surface_view"]["hold_values"][ids["category"]] == "level-B"
        calls: list[str] = []
        page.on(
            "request",
            lambda r: calls.append(r.url)
            if r.method == "POST"
            and (
                r.url.endswith("/analysis-runs")
                or r.url.endswith("/gaussian-process-predictions")
            )
            else None,
        )
        for locale, label in (("ko", "KOR"), ("en", "ENG")):
            page.locator(".language-switcher button").filter(has_text=label).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                expect(page.locator(".gp-point-prediction")).to_have_attribute(
                    "data-prediction-state", "ready"
                )
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                )
                page.screenshot(
                    path=str(root / f"mixed-{locale}-{width}.png"), full_page=True
                )
        assert calls == [], calls
        html_root = root / "html"
        html_root.mkdir(exist_ok=True)
        diagnostics = SimpleNamespace(
            html_root=html_root,
            record=evidence["events"].append,
            capture_page=lambda p, name: p.screenshot(
                path=str(root / name), full_page=True
            ),
        )
        managed = verify_saved_prediction_report(
            page, diagnostics, prediction, prediction_request, family="gaussian_process"
        )
        view_root = root / "surface-html"
        view_root.mkdir(exist_ok=True)
        diagnostics.html_root = view_root
        view_managed = verify_saved_prediction_report(
            page,
            diagnostics,
            saved_view.value.json(),
            view_request,
            family="gaussian_process",
        )
        for envelope in (grouped, timed, lagged):
            restored = page.request.get(
                base + f"/api/v1/analysis-runs/{envelope['analysis_id']}/result"
            )
            assert restored.status == 200 and _digest(
                restored.json()["result"]
            ) == _digest(envelope["result"])
        evidence.update(
            schema_version=1,
            synthetic=True,
            status="succeeded",
            version_id=version["version_id"],
            analyses=[grouped, timed, lagged],
            requests=[group_request, time_request, lag_request],
            prediction=prediction,
            managed=managed,
            surface_managed=view_managed,
            forbidden_resize_locale_requests=calls,
            group_form=True,
            time_form=True,
            lag_form=True,
            mixed_restore_prediction=True,
            unknown_category_api_rejected=True,
            surface_hold_saved=True,
            managed_report_reopened=True,
            source_checksums_unchanged=True,
            group_count=6,
            raw_n=36,
            locales_viewports=[
                {"locale": locale, "width": width}
                for locale in ("ko", "en")
                for width in (1024, 1440)
            ],
        )
    (root / "gp-validation-extension.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    return evidence
