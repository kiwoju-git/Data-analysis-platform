"""Run the tutorial pack through real DataLab Studio APIs and verify expected results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

TUTORIAL_ROOT = ROOT / "examples" / "tutorial"
EXPECTED_PATH = TUTORIAL_ROOT / "tutorial_expected_results.json"
ABSOLUTE_TOLERANCE = 1e-8
RELATIVE_TOLERANCE = 1e-8


def _require(response: Any, expected_status: int, operation: str) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise RuntimeError(
            f"{operation} failed with HTTP {response.status_code}: {response.text[:800]}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"{operation} returned a non-object response")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_rows(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def _upload(client: TestClient, path: Path, *, delimiter: str = ",") -> dict[str, Any]:
    media_type = "text/tab-separated-values" if delimiter == "\t" else "text/csv"
    uploaded = _require(
        client.post(
            "/api/v1/datasets",
            files={"file": (path.name, path.read_bytes(), media_type)},
        ),
        201,
        f"upload {path.name}",
    )
    return _require(
        client.post(
            f"/api/v1/datasets/{uploaded['dataset_id']}/confirm-parsing",
            json={
                "parsing": {
                    "kind": "delimited_text",
                    "encoding": "utf-8",
                    "delimiter": delimiter,
                    "quote_char": '"',
                    "decimal": ".",
                    "thousands": None,
                    "has_header": True,
                    "header_row": 1,
                    "data_start_row": 2,
                    "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
                },
                "columns": [],
            },
        ),
        201,
        f"confirm {path.name}",
    )


def _columns(version: dict[str, Any]) -> dict[str, str]:
    return {item["display_name"]: item["column_id"] for item in version["columns"]}


def _analysis(
    client: TestClient,
    versions: dict[str, str],
    version: dict[str, Any],
    method_id: str,
    roles: dict[str, str],
    options: dict[str, Any],
) -> dict[str, Any]:
    return _require(
        client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": method_id,
                "method_version": versions[method_id],
                "dataset_version_id": version["version_id"],
                "roles": roles,
                "options": options,
            },
        ),
        201,
        method_id,
    )


def _method_result(
    envelope: dict[str, Any],
    input_sha256: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "method_id": envelope["method_id"],
        "method_version": envelope["method_version"],
        "input_file_sha256": input_sha256,
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "relative_tolerance": RELATIVE_TOLERANCE,
        "result": result,
    }


def _collect_generic_results(
    client: TestClient,
    versions: dict[str, str],
    training: dict[str, Any],
    prediction_target: dict[str, Any],
    gage: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    columns = _columns(training)
    training_sha = _sha256(TUTORIAL_ROOT / "studio_process_training.csv")
    gage_sha = _sha256(TUTORIAL_ROOT / "studio_gage_rr.csv")
    yield_id = columns["yield_pct"]
    tensile_id = columns["tensile_strength_mpa"]
    descriptive = _analysis(
        client,
        versions,
        training,
        "eda.descriptive",
        {"responses": f"{yield_id},{tensile_id}"},
        {
            "column_ids": [yield_id, tensile_id],
            "missing_policy": "available_case_by_column",
        },
    )
    descriptive_columns = {
        item["display_name"]: {
            key: item[key]
            for key in (
                "n_total",
                "n_used",
                "n_missing",
                "mean",
                "std",
                "min",
                "q1",
                "median",
                "q3",
                "max",
            )
        }
        for item in descriptive["result"]["columns"]
    }

    graphical = _analysis(
        client,
        versions,
        training,
        "eda.graphical_summary",
        {"responses": f"{yield_id},{tensile_id}"},
        {
            "column_ids": [yield_id, tensile_id],
            "histogram_bin_count": None,
            "point_limit": 500,
        },
    )
    graphical_columns = {
        item["display_name"]: {
            "n_used": item["n_used"],
            "n_missing": item["n_missing"],
            "minimum": item["min"],
            "maximum": item["max"],
            "histogram_bin_count": item["histogram"]["bin_count"],
            "boxplot_outlier_count": item["boxplot"]["outlier_count"],
        }
        for item in graphical["result"]["columns"]
    }

    supplier_id = columns["supplier"]
    two_sample = _analysis(
        client,
        versions,
        training,
        "hypothesis.two_sample_t",
        {"response": yield_id, "group": supplier_id},
        {
            "response_column_id": yield_id,
            "group_column_id": supplier_id,
            "alpha": 0.05,
            "confidence_level": 0.95,
            "alternative": "two_sided",
            "variance_assumption": "welch",
            "null_difference": 0.0,
            "missing_policy": "complete_case",
        },
    )
    two_result = two_sample["result"]
    anova = _analysis(
        client,
        versions,
        training,
        "hypothesis.one_way_anova",
        {"response": yield_id, "group": columns["production_line"]},
        {
            "response_column_id": yield_id,
            "group_column_id": columns["production_line"],
            "alpha": 0.05,
            "confidence_level": 0.95,
            "anova_type": "standard",
            "posthoc_method": "tukey_kramer",
            "posthoc_policy": "after_significant",
            "missing_policy": "complete_case",
        },
    )
    anova_result = anova["result"]
    one_proportion = _analysis(
        client,
        versions,
        training,
        "categorical.one_proportion",
        {"response": columns["pass_flag"]},
        {
            "response_column_id": columns["pass_flag"],
            "event_level": "Pass",
            "null_proportion": 0.8,
            "alpha": 0.05,
            "confidence_level": 0.95,
            "alternative": "two_sided",
            "ci_method": "wilson",
            "missing_policy": "complete_case",
        },
    )
    proportion_result = one_proportion["result"]
    chi_square = _analysis(
        client,
        versions,
        training,
        "categorical.chi_square_association",
        {"row": columns["production_line"], "column": columns["pass_flag"]},
        {
            "row_column_id": columns["production_line"],
            "column_column_id": columns["pass_flag"],
            "alpha": 0.05,
            "missing_policy": "complete_case",
        },
    )
    chi_result = chi_square["result"]
    pearson = _analysis(
        client,
        versions,
        training,
        "regression.pearson",
        {"x": columns["temperature_c"], "y": yield_id},
        {
            "x_column_id": columns["temperature_c"],
            "y_column_id": yield_id,
            "alpha": 0.05,
            "confidence_level": 0.95,
            "missing_policy": "complete_case",
        },
    )
    pearson_result = pearson["result"]
    numeric_predictors = [
        columns[name]
        for name in (
            "temperature_c",
            "pressure_bar",
            "cycle_time_s",
            "catalyst_pct",
            "feed_rate_kg_h",
        )
    ]
    xy = _analysis(
        client,
        versions,
        training,
        "regression.xy_correlation",
        {"x": ",".join(numeric_predictors), "y": f"{yield_id},{tensile_id}"},
        {
            "x_column_ids": numeric_predictors,
            "y_column_ids": [yield_id, tensile_id],
            "alpha": 0.05,
            "confidence_level": 0.95,
            "missing_policy": "pairwise_complete_case",
        },
    )
    xy_result = xy["result"]
    linear_predictors = [*numeric_predictors, columns["material_grade"]]
    linear = _analysis(
        client,
        versions,
        training,
        "regression.linear_model",
        {"response": yield_id, "predictors": ",".join(linear_predictors)},
        {
            "response_column_id": yield_id,
            "predictor_column_ids": linear_predictors,
            "quadratic_terms": [columns["temperature_c"], columns["pressure_bar"]],
            "interaction_terms": [
                {
                    "left_column_id": columns["temperature_c"],
                    "right_column_id": columns["pressure_bar"],
                }
            ],
            "alpha": 0.05,
            "confidence_level": 0.95,
            "missing_policy": "complete_case",
            "include_intercept": True,
            "covariance_type": "standard",
        },
    )
    linear_result = linear["result"]
    model_id = linear_result["model_manifest"]["model_id"]
    target_columns = _columns(prediction_target)
    preflight = _require(
        client.post(
            f"/api/v1/regression-models/{model_id}/prediction-preflight",
            json={"dataset_version_id": prediction_target["version_id"]},
        ),
        200,
        "regression prediction preflight",
    )
    prediction = _require(
        client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={
                "dataset_version_id": prediction_target["version_id"],
                "confidence_level": 0.95,
                "missing_policy": "complete_case",
                "include_intervals": True,
            },
        ),
        200,
        "regression prediction",
    )
    prediction_export = _require(
        client.post(
            f"/api/v1/regression-models/predictions/{prediction['prediction_id']}/exports/csv"
        ),
        201,
        "regression prediction CSV",
    )
    run_chart = _analysis(
        client,
        versions,
        training,
        "quality.run_chart",
        {"response": yield_id, "order": columns["timestamp"]},
        {
            "value_column_id": yield_id,
            "order_column_id": columns["timestamp"],
            "center_method": "median",
            "missing_policy": "complete_case",
            "trend_min_length": 6,
            "oscillation_min_length": 14,
            "runs_test_alpha": 0.05,
            "point_limit": 500,
        },
    )
    run_result = run_chart["result"]
    capability = _analysis(
        client,
        versions,
        training,
        "quality.capability",
        {"response": yield_id},
        {
            "value_column_id": yield_id,
            "lsl": 68.0,
            "usl": 92.0,
            "target": 82.0,
            "missing_policy": "complete_case",
            "histogram_bin_limit": 30,
        },
    )
    capability_result = capability["result"]
    phase_one = _analysis(
        client,
        versions,
        training,
        "quality.attribute_control_chart",
        {
            "count": columns["defectives_count"],
            "denominator": columns["inspected_count"],
        },
        {
            "phase": "phase_1",
            "chart_type": "p",
            "count_definition": "defectives",
            "count_column_id": columns["defectives_count"],
            "denominator_column_id": columns["inspected_count"],
            "constant_opportunity_confirmed": False,
            "missing_policy": "complete_case",
            "point_limit": 500,
        },
    )
    phase_one_result = phase_one["result"]
    limit_set_response = client.post(
        "/api/v1/quality/attribute-control-limit-sets",
        json={"source_analysis_id": phase_one["analysis_id"]},
    )
    if limit_set_response.status_code != 201:
        raise RuntimeError(
            "tutorial Phase I data is not eligible for promotion: "
            f"{limit_set_response.status_code} {limit_set_response.text[:800]}; "
            f"signals={len(phase_one_result['signals'])}, "
            f"dispersion={phase_one_result['dispersion']['ratio']}, "
            f"warnings={phase_one_result['warnings']}"
        )
    limit_set = limit_set_response.json()
    phase_two = _analysis(
        client,
        versions,
        prediction_target,
        "quality.attribute_control_chart",
        {
            "count": target_columns["defectives_count"],
            "denominator": target_columns["inspected_count"],
        },
        {
            "phase": "phase_2",
            "limit_set_id": limit_set["limit_set_id"],
            "chart_type": "p",
            "count_definition": "defectives",
            "count_column_id": target_columns["defectives_count"],
            "denominator_column_id": target_columns["inspected_count"],
            "constant_opportunity_confirmed": False,
            "missing_policy": "complete_case",
            "point_limit": 100,
        },
    )
    phase_two_result = phase_two["result"]
    gage_columns = _columns(gage)
    gage_rr = _analysis(
        client,
        versions,
        gage,
        "quality.gage_rr",
        {
            "measurement": gage_columns["measurement_mpa"],
            "part": gage_columns["part_id"],
            "operator": gage_columns["operator_id"],
            "replicate": gage_columns["replicate"],
        },
        {
            "measurement_column_id": gage_columns["measurement_mpa"],
            "part_column_id": gage_columns["part_id"],
            "operator_column_id": gage_columns["operator_id"],
            "replicate_column_id": gage_columns["replicate"],
            "missing_policy": "complete_case",
        },
    )
    gage_result = gage_rr["result"]

    results = {
        "eda.descriptive": _method_result(
            descriptive, training_sha, descriptive_columns
        ),
        "eda.graphical_summary": _method_result(
            graphical, training_sha, graphical_columns
        ),
        "hypothesis.two_sample_t": _method_result(
            two_sample,
            training_sha,
            {
                "n_total": two_result["n_total"],
                "n_used": two_result["n_used"],
                "groups": [
                    {"label": item["group_label"], "n": item["n"], "mean": item["mean"]}
                    for item in two_result["groups"]
                ],
                "mean_difference": two_result["contrast"]["estimate"],
                "confidence_interval": two_result["contrast"]["confidence_interval"],
                "p_value": two_result["contrast"]["p_value"],
                "hedges_g": two_result["contrast"]["effect_size"]["hedges_g"],
                "warnings": two_result["warnings"],
            },
        ),
        "hypothesis.one_way_anova": _method_result(
            anova,
            training_sha,
            {
                "n_total": anova_result["n_total"],
                "n_used": anova_result["n_used"],
                "group_n": {
                    item["group_label"]: item["n"] for item in anova_result["groups"]
                },
                "f_statistic": anova_result["test"]["f_statistic"],
                "df_between": anova_result["test"]["df_between"],
                "df_within": anova_result["test"]["df_within"],
                "p_value": anova_result["test"]["p_value"],
                "eta_squared": anova_result["test"]["effect_size"]["eta_squared"],
                "omega_squared": anova_result["test"]["effect_size"]["omega_squared"],
                "posthoc_performed": anova_result["posthoc"]["performed"],
            },
        ),
        "categorical.one_proportion": _method_result(
            one_proportion,
            training_sha,
            {
                "event_level": proportion_result["event_level"],
                "n": proportion_result["sample"]["total"],
                "event_count": proportion_result["sample"]["event_count"],
                "sample_proportion": proportion_result["sample"]["sample_proportion"],
                "confidence_interval": proportion_result["confidence_interval"],
                "p_value": proportion_result["test"]["p_value"],
                "cohen_h": proportion_result["effect_size"]["cohen_h"],
            },
        ),
        "categorical.chi_square_association": _method_result(
            chi_square,
            training_sha,
            {
                "n_used": chi_result["n_used"],
                "chi_square": chi_result["test"]["statistic"],
                "df": chi_result["test"]["df"],
                "p_value": chi_result["test"]["p_value"],
                "cramers_v": chi_result["effect_size"]["cramers_v"],
                "expected_count_summary": chi_result["expected_count_summary"],
                "warnings": chi_result["warnings"],
            },
        ),
        "regression.pearson": _method_result(
            pearson,
            training_sha,
            {
                "n_used": pearson_result["n_used"],
                "correlation": pearson_result["association"]["correlation"],
                "r_squared": pearson_result["association"]["r_squared"],
                "confidence_interval": pearson_result["confidence_interval"],
                "p_value": pearson_result["test"]["p_value"],
            },
        ),
        "regression.xy_correlation": _method_result(
            xy,
            training_sha,
            {
                "x_column_count": xy_result["x_column_count"],
                "y_column_count": xy_result["y_column_count"],
                "pair_count": xy_result["pair_count"],
                "pairs": [
                    {
                        "x": item["x"]["display_name"],
                        "y": item["y"]["display_name"],
                        "n_used": item["n_used"],
                        "correlation": item["association"]["correlation"],
                        "p_value": item["test"]["p_value"],
                    }
                    for item in xy_result["pairs"]
                ],
            },
        ),
        "regression.linear_model": _method_result(
            linear,
            training_sha,
            {
                "n_total": linear_result["sample"]["n_total"],
                "n_used": linear_result["sample"]["n_used"],
                "n_excluded": linear_result["sample"]["n_excluded_missing"]
                + linear_result["sample"]["n_excluded_non_numeric"],
                "r_squared": linear_result["fit"]["r_squared"],
                "adjusted_r_squared": linear_result["fit"]["adjusted_r_squared"],
                "model_asset_created": bool(linear_result.get("model_manifest")),
                "coefficients": [
                    {
                        "term": item["term"],
                        "kind": item["term_kind"],
                        "estimate": item["estimate"],
                        "p_value": item["p_value"],
                        "sign": "positive" if item["estimate"] > 0 else "negative",
                    }
                    for item in linear_result["coefficients"]
                ],
                "warnings": linear_result["warnings"],
            },
        ),
        "regression.predict": {
            "method_id": "regression.predict",
            "method_version": versions["regression.predict"],
            "input_file_sha256": _sha256(
                TUTORIAL_ROOT / "studio_process_prediction.csv"
            ),
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
            "result": {
                "preflight_ready": preflight["prediction_ready"],
                "row_count_total": preflight["row_count_total"],
                "row_count_usable": preflight["row_count_usable"],
                "extrapolation_warning_count": sum(
                    item["n_below_training_range"] + item["n_above_training_range"]
                    for item in preflight["numeric_checks"]
                ),
                "row_count_predicted": prediction["row_count_predicted"],
                "row_count_excluded": prediction["row_count_excluded"],
                "first_five": [
                    {
                        "row_index": item["row_index"],
                        "predicted_mean": item["predicted_mean"],
                        "mean_confidence_interval": item["mean_confidence_interval"],
                        "prediction_interval": item["prediction_interval"],
                    }
                    for item in prediction["rows"][:5]
                ],
                "csv_row_count": prediction_export["row_count"],
                "warnings": [item["code"] for item in prediction["warnings"]],
            },
        },
        "quality.run_chart": _method_result(
            run_chart,
            training_sha,
            {
                "n_used": run_result["n_used"],
                "center_line": run_result["center_line"],
                "point_count": run_result["chart"]["point_count"],
                "signal_count": len(run_result["signals"]),
                "warnings": run_result["warnings"],
            },
        ),
        "quality.capability": _method_result(
            capability,
            training_sha,
            {
                "n_used": capability_result["n_used"],
                "spec_limits": capability_result["spec_limits"],
                "cp": capability_result["capability"]["within"]["two_sided"],
                "cpk": capability_result["capability"]["within"]["min_side"],
                "pp": capability_result["capability"]["overall"]["two_sided"],
                "ppk": capability_result["capability"]["overall"]["min_side"],
                "warnings": capability_result["warnings"],
            },
        ),
        "quality.attribute_control_chart": _method_result(
            phase_one,
            training_sha,
            {
                "phase_1_center_line": phase_one_result["center_line"],
                "phase_1_point_count": phase_one_result["chart"]["point_count"],
                "phase_1_signal_count": len(phase_one_result["signals"]),
                "limit_set_promoted": True,
                "phase_2_target_point_count": phase_two_result["chart"]["point_count"],
                "phase_2_signal_count": len(phase_two_result["signals"]),
                "phase_2_dispersion_available": phase_two_result["dispersion"][
                    "available"
                ],
                "phase_2_dispersion_ratio": phase_two_result["dispersion"]["ratio"],
            },
        ),
        "quality.gage_rr": _method_result(
            gage_rr,
            gage_sha,
            {
                "n_used": gage_result["sample"]["n_used"],
                "balanced": gage_result["design"]["balanced"],
                "repeatability": gage_result["variance_components"]["repeatability"],
                "reproducibility": gage_result["variance_components"][
                    "reproducibility"
                ],
                "total_gage_rr": gage_result["variance_components"]["total_gage_rr"],
                "part_to_part": gage_result["variance_components"]["part_to_part"],
                "ndc": gage_result["variance_components"]["ndc"],
                "warnings": gage_result["warnings"],
            },
        ),
    }
    return results, {"linear": linear, "model_id": model_id, "prediction": prediction}


def _collect_doe_results(
    client: TestClient, versions: dict[str, str]
) -> dict[str, Any]:
    factorial_rows = _read_rows(TUTORIAL_ROOT / "studio_factorial_responses.csv")
    factorial_design = _require(
        client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "Synthetic tutorial factorial",
                "factors": [
                    {"name": "temperature_c", "low": 68.0, "high": 84.0, "unit": "C"},
                    {"name": "pressure_bar", "low": 7.0, "high": 13.0, "unit": "bar"},
                    {"name": "catalyst_pct", "low": 0.8, "high": 2.2, "unit": "%"},
                ],
                "replicates": 2,
                "center_points": 0,
                "randomize": False,
                "randomization_seed": 20260718,
                "block_count": 1,
            },
        ),
        201,
        "factorial design",
    )
    factorial_lookup = {
        (
            float(row["temperature_c"]),
            float(row["pressure_bar"]),
            float(row["catalyst_pct"]),
            int(row["replicate"]),
        ): float(row["response_yield_pct"])
        for row in factorial_rows
    }
    factorial_values = []
    for run in factorial_design["runs"]:
        actual = run["factor_levels"]
        key = (
            float(actual["temperature_c"]),
            float(actual["pressure_bar"]),
            float(actual["catalyst_pct"]),
            int(run["replicate_index"]),
        )
        factorial_values.append(
            {"run_order": run["run_order"], "value": factorial_lookup[key]}
        )
    _require(
        client.put(
            f"/api/v1/doe-designs/{factorial_design['design_id']}/responses",
            json={
                "response_name": "yield_pct",
                "unit": "%",
                "values": factorial_values,
            },
        ),
        200,
        "factorial responses",
    )
    factorial_analysis = _require(
        client.post(
            f"/api/v1/doe-designs/{factorial_design['design_id']}/analyses",
            json={
                "response_name": "yield_pct",
                "max_interaction_order": 2,
                "confidence_level": 0.95,
                "point_limit": 64,
            },
        ),
        201,
        "factorial analysis",
    )
    factorial_result = factorial_analysis["result"]

    rsm_rows = _read_rows(TUTORIAL_ROOT / "studio_rsm_responses.csv")
    rsm_design = _require(
        client.post(
            "/api/v1/doe-designs/response-surface",
            json={
                "name": "Synthetic tutorial RSM",
                "factors": [
                    {"name": "temperature_c", "low": 65.0, "high": 85.0, "unit": "C"},
                    {"name": "pressure_bar", "low": 6.0, "high": 14.0, "unit": "bar"},
                ],
                "alpha_mode": "face_centered",
                "factorial_replicates": 1,
                "axial_replicates": 1,
                "center_points": 5,
                "randomize": False,
                "randomization_seed": 20260718,
            },
        ),
        201,
        "RSM design",
    )
    rsm_lookup: dict[tuple[float, float], list[float]] = {}
    for row in rsm_rows:
        rsm_lookup.setdefault(
            (float(row["temperature_c"]), float(row["pressure_bar"])), []
        ).append(float(row["response_yield_pct"]))
    rsm_values = []
    for run in rsm_design["runs"]:
        actual = run["factor_levels"]
        key = (float(actual["temperature_c"]), float(actual["pressure_bar"]))
        available = rsm_lookup.get(key, [])
        if not available:
            raise RuntimeError(f"RSM response coordinate missing: {key}")
        rsm_values.append({"run_order": run["run_order"], "value": available.pop(0)})
    _require(
        client.put(
            f"/api/v1/doe-designs/response-surface/{rsm_design['design_id']}/responses",
            json={"response_name": "yield_pct", "unit": "%", "values": rsm_values},
        ),
        200,
        "RSM responses",
    )
    rsm_analysis = _require(
        client.post(
            f"/api/v1/doe-designs/response-surface/{rsm_design['design_id']}/analyses",
            json={
                "response_name": "yield_pct",
                "confidence_level": 0.95,
                "point_limit": 64,
                "contour_grid_size": 21,
            },
        ),
        201,
        "RSM analysis",
    )
    rsm_result = rsm_analysis["result"]
    predicted_values = [point["predicted"] for point in rsm_result["contour"]["points"]]
    acknowledgment_codes: list[str] = []
    if rsm_result["sample"]["df_residual"] < 5:
        acknowledgment_codes.append("response_optimizer_source_residual_df_small")
    if rsm_result["diagnostics"]["high_cooks_distance_count"] > 0:
        acknowledgment_codes.append("response_optimizer_source_influential_run")
    if rsm_result["diagnostics"]["high_leverage_count"] > 0:
        acknowledgment_codes.append("response_optimizer_source_high_leverage")
    if rsm_result["diagnostics"]["high_standardized_residual_count"] > 0:
        acknowledgment_codes.append(
            "response_optimizer_source_large_standardized_residual"
        )
    normality_p = rsm_result["diagnostics"]["shapiro_wilk"]["p_value"]
    if normality_p is not None and normality_p < 0.01:
        acknowledgment_codes.append(
            "response_optimizer_source_residual_normality_severe"
        )
    optimizer = _require(
        client.post(
            f"/api/v1/doe-designs/response-surface/{rsm_design['design_id']}/optimizations",
            json={
                "objectives": [
                    {
                        "source_analysis_id": rsm_analysis["analysis_id"],
                        "goal": "maximize",
                        "lower": min(predicted_values),
                        "target": max(predicted_values),
                        "upper": None,
                        "lower_weight": 1.0,
                        "upper_weight": 1.0,
                        "importance": 1.0,
                    }
                ],
                "factor_bounds": [],
                "linear_constraints": [],
                "acknowledged_source_warning_codes": acknowledgment_codes,
                "search": {
                    "random_seed": 20260718,
                    "random_candidate_count": 256,
                    "multi_start_count": 8,
                    "max_iterations": 120,
                    "max_evaluations": 5000,
                    "time_budget_ms": 5000,
                },
            },
        ),
        201,
        "Response Optimizer",
    )
    optimizer_result = optimizer["result"]
    return {
        "doe.factorial_design": {
            "method_id": "doe.factorial_design",
            "method_version": factorial_analysis["method_version"],
            "input_file_sha256": _sha256(
                TUTORIAL_ROOT / "studio_factorial_responses.csv"
            ),
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
            "result": {
                "n_observations": factorial_result["sample"]["n_observations"],
                "df_residual": factorial_result["sample"]["df_residual"],
                "effect_ordering": [
                    {"term_id": item["term_id"], "effect": item["effect"]}
                    for item in sorted(
                        [
                            item
                            for item in factorial_result["terms"]
                            if item["effect"] is not None
                        ],
                        key=lambda item: abs(item["effect"]),
                        reverse=True,
                    )
                ],
                "selected_interaction": "factor_1:factor_2",
                "anova_residual": factorial_result["anova"]["residual"],
                "warning_count": len(factorial_result["warnings"]),
            },
        },
        "doe.response_surface": {
            "method_id": "doe.response_surface",
            "method_version": rsm_analysis["method_version"],
            "input_file_sha256": _sha256(TUTORIAL_ROOT / "studio_rsm_responses.csv"),
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
            "result": {
                "r_squared": rsm_result["fit"]["r_squared"],
                "adjusted_r_squared": rsm_result["fit"]["adjusted_r_squared"],
                "stationary_point": rsm_result["stationary_point"],
                "lack_of_fit": rsm_result["anova"]["lack_of_fit"],
                "warning_count": len(rsm_result["warnings"]),
            },
        },
        "regression.response_optimizer": {
            "method_id": "regression.response_optimizer",
            "method_version": optimizer["method_version"],
            "input_file_sha256": _sha256(TUTORIAL_ROOT / "studio_rsm_responses.csv"),
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
            "result": {
                "source_analysis_count": len(optimizer["source_analysis_ids"]),
                "goal": optimizer_result["recommendation"]["objectives"][0]["goal"],
                "actual_coordinates": optimizer_result["recommendation"][
                    "actual_coordinates"
                ],
                "predicted_response": optimizer_result["recommendation"]["objectives"][
                    0
                ]["predicted_response"],
                "composite_desirability": optimizer_result["recommendation"][
                    "composite_desirability"
                ],
                "termination_reason": optimizer_result["search"]["termination_reason"],
                "global_optimum_guaranteed": optimizer_result["search"][
                    "global_optimum_guaranteed"
                ],
                "warnings": optimizer_result["warnings"],
            },
        },
    }


def _collect_bayesian_result(
    client: TestClient, versions: dict[str, str]
) -> dict[str, Any]:
    observation_rows = _read_rows(TUTORIAL_ROOT / "studio_bayesian_observations.csv")
    study = _require(
        client.post(
            "/api/v1/bayesian-studies",
            json={
                "name": "Synthetic tutorial Bayesian study",
                "factors": [
                    {
                        "factor_id": "temperature_c",
                        "name": "temperature_c",
                        "low": 60.0,
                        "high": 90.0,
                        "unit": "C",
                    },
                    {
                        "factor_id": "pressure_bar",
                        "name": "pressure_bar",
                        "low": 5.0,
                        "high": 15.0,
                        "unit": "bar",
                    },
                ],
                "objective": {
                    "name": "yield_pct",
                    "unit": "%",
                    "direction": "maximize",
                    "observation_policy": "manual_single_observation",
                },
                "constraints": [],
                "initial_design_seed": 20260718,
                "initial_design_size": 5,
            },
        ),
        201,
        "Bayesian study",
    )
    history_revision_id = study["observation_history"]["history_revision_id"]
    for trial, row in zip(study["trials"], observation_rows, strict=True):
        for factor_id in ("temperature_c", "pressure_bar"):
            if not math.isclose(
                trial["actual_coordinates"][factor_id],
                float(row[factor_id]),
                rel_tol=0.0,
                abs_tol=1e-7,
            ):
                raise RuntimeError(
                    f"Bayesian tutorial coordinate mismatch for {factor_id}"
                )
        completed = _require(
            client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
                json={
                    "objective_value": float(row["objective_yield_pct"]),
                    "expected_history_revision_id": history_revision_id,
                },
            ),
            200,
            "Bayesian observation",
        )
        history_revision_id = completed["observation_history"]["history_revision_id"]
    restored = _require(
        client.get(f"/api/v1/bayesian-studies/{study['study_id']}"),
        200,
        "Bayesian study restore",
    )
    recommendation = _require(
        client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json={
                "expected_history_revision_id": history_revision_id,
                "search": {
                    "random_seed": 20260718,
                    "xi": 0.01,
                    "candidate_count": 128,
                    "local_start_count": 4,
                    "max_iterations": 60,
                    "max_evaluations": 1024,
                    "model_max_iterations": 50,
                    "model_max_evaluations": 200,
                    "hyperparameter_restart_count": 0,
                    "time_budget_ms": 15000,
                    "jitter": 1e-8,
                    "duplicate_tolerance": 1e-6,
                    "total_trial_budget": 20,
                },
            },
        ),
        201,
        "Bayesian recommendation",
    )
    result = recommendation["result"]
    return {
        "method_id": "doe.bayesian_optimization",
        "method_version": versions["doe.bayesian_optimization"],
        "input_file_sha256": _sha256(
            TUTORIAL_ROOT / "studio_bayesian_observations.csv"
        ),
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "relative_tolerance": RELATIVE_TOLERANCE,
        "result": {
            "completed_observation_count": restored["completed_trial_count"],
            "actual_coordinates": result["recommended_actual_coordinates"],
            "predicted_mean": result["predicted_objective_mean"],
            "predicted_standard_deviation": result["posterior_standard_deviation"],
            "expected_improvement": result["expected_improvement"],
            "confirmation_required": any(
                "confirmation" in item
                for item in [*result["warnings"], *result["limitations"]]
            ),
            "global_optimum_guaranteed": (
                "bayesian_optimization_no_global_optimum_guarantee"
                not in result["warnings"]
            ),
            "trial_state": recommendation["trial"]["state"],
            "warnings": result["warnings"],
            "limitations": result["limitations"],
        },
    }


def collect_results() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="datalab-tutorial-") as temporary:
        settings = Settings(workspace_root=Path(temporary), git_commit="tutorial-smoke")
        with TestClient(create_app(settings)) as client:
            catalog = _require(
                client.get("/api/v1/analysis-methods"), 200, "analysis method catalog"
            )
            versions = {
                item["method_id"]: item["method_version"] for item in catalog["methods"]
            }
            training = _upload(client, TUTORIAL_ROOT / "studio_process_training.csv")
            prediction = _upload(
                client, TUTORIAL_ROOT / "studio_process_prediction.csv"
            )
            gage = _upload(client, TUTORIAL_ROOT / "studio_gage_rr.csv")
            results, _context = _collect_generic_results(
                client, versions, training, prediction, gage
            )
            results.update(_collect_doe_results(client, versions))
            results["doe.bayesian_optimization"] = _collect_bayesian_result(
                client, versions
            )
    return {
        "expected_results_schema_version": 1,
        "generated_by": "DataLab Studio API tutorial smoke",
        "dynamic_ids_and_timestamps_omitted": True,
        "results": results,
    }


def _compare(expected: Any, actual: Any, path: str = "$") -> None:
    if isinstance(expected, bool) or isinstance(actual, bool):
        if expected != actual:
            raise AssertionError(f"{path}: expected {expected!r}, received {actual!r}")
        return
    if isinstance(expected, int | float) and isinstance(actual, int | float):
        if not math.isclose(
            float(expected),
            float(actual),
            rel_tol=RELATIVE_TOLERANCE,
            abs_tol=ABSOLUTE_TOLERANCE,
        ):
            raise AssertionError(f"{path}: expected {expected!r}, received {actual!r}")
        return
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            raise AssertionError(
                f"{path}: object keys differ: expected {sorted(expected)}, received {sorted(actual)}"
            )
        for key in expected:
            _compare(expected[key], actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            raise AssertionError(f"{path}: list length differs")
        for index, (expected_item, actual_item) in enumerate(
            zip(expected, actual, strict=True)
        ):
            _compare(expected_item, actual_item, f"{path}[{index}]")
        return
    if expected != actual:
        raise AssertionError(f"{path}: expected {expected!r}, received {actual!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-expected",
        action="store_true",
        help="Write normalized expected results from this real Studio API execution.",
    )
    args = parser.parse_args()
    actual = collect_results()
    if args.write_expected:
        EXPECTED_PATH.write_text(
            json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {EXPECTED_PATH.relative_to(ROOT)} from real Studio API results.")
        return 0
    if not EXPECTED_PATH.exists():
        raise RuntimeError(
            "tutorial_expected_results.json is missing; run --write-expected"
        )
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    _compare(expected, actual)
    print(
        f"Verified {len(actual['results'])} tutorial result sections against Studio APIs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
