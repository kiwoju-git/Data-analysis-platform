import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from app.api.v1.schemas.analyses import GaussianProcessRegressionOptions
from app.statistics import gaussian_process_kernel_selection as selection
from app.statistics.gaussian_process_regression import (
    MAX_GP_OPTIMIZER_STARTS,
    GaussianProcessColumn,
    GaussianProcessOptions,
    GaussianProcessRegressionError,
    calculate_gaussian_process_regression,
    optimizer_start_count,
)

FIXTURES = Path(__file__).parents[1] / "reference/fixtures"
REFERENCE = json.loads(
    (FIXTURES / "gp_kernel_comparison_reference.json").read_text(encoding="utf-8")
)


def calculate(case, options):
    columns = [
        GaussianProcessColumn(
            name,
            index,
            name,
            "decimal",
            "continuous",
            "response" if name == "y" else "predictor",
            None,
        )
        for index, name in enumerate(["x1", "x2", "y"])
    ]
    rows = [[*map(str, x), str(y)] for x, y in zip(case["x"], case["y"], strict=True)]
    return calculate_gaussian_process_regression(rows, columns[-1], columns[:-1], options=options)


def options(**kwargs):
    return replace(
        GaussianProcessOptions(
            kernel_selection_mode="compare",
            kernel_candidates=selection.PRESET_PRIORITY,
            optimizer_restarts=0,
            cv_folds=3,
            random_seed=41,
            profile_points=10,
            surface_grid_size=10,
            plot_point_limit=100,
        ),
        **kwargs,
    )


def assert_nested(actual, expected):
    if isinstance(expected, dict):
        for key, value in expected.items():
            assert_nested(actual[key], value)
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected, strict=True):
            assert_nested(left, right)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, abs=1e-8, rel=1e-7)
    else:
        assert actual == expected


@pytest.mark.parametrize("preset", selection.PRESET_PRIORITY)
def test_legacy_single_kernel_parity(preset):
    reference = json.loads((FIXTURES / "gp_single_kernel_legacy.json").read_text(encoding="utf-8"))
    rows = np.asarray(reference["rows"], dtype=float)
    actual = calculate(
        {"x": rows[:, :2], "y": rows[:, 2]},
        options(kernel_selection_mode="single", kernel_candidates=(), kernel_preset=preset),
    )
    assert_nested(actual, reference["results"][preset])
    assert actual["schema_version"] == 3
    assert actual["kernel_selection"]["mode"] == "single"


@pytest.mark.parametrize("case", REFERENCE["cases"], ids=lambda case: case["name"])
def test_independent_sklearn_kernel_comparison(case):
    result = calculate(case, options(retain_candidate_details=True))
    assert result["kernel_selection"]["cv_validation_row_indices"] == REFERENCE["splits"]
    assert result["kernel_selection"]["selected_preset"] == case["selected"]["nlpd"]
    for candidate, expected in zip(result["kernel_candidates"], case["candidates"], strict=True):
        assert candidate["status"] == "succeeded"
        assert candidate["metrics"] == pytest.approx(expected["metrics"], abs=1e-6, rel=1e-6)
        details = candidate["details"]
        assert details["kernel"]["log_marginal_likelihood"] == pytest.approx(
            expected["lml"], abs=1e-6, rel=1e-6
        )
        assert [
            point["cross_validated_fitted"] for point in details["diagnostics"]["points"]
        ] == pytest.approx(expected["oof_mean"], abs=1e-6)
        assert [
            point["cross_validated_predictive_standard_deviation"]
            for point in details["diagnostics"]["points"]
        ] == pytest.approx(expected["oof_sd"], abs=1e-6)
        assert (
            not {
                "prediction_basis",
                "model_manifest",
                "conditional_profiles",
                "two_predictor_surface",
            }
            & details.keys()
        )
    assert "gp_kernel_selection_not_external_validation" in result["warnings"]


@pytest.mark.parametrize("criterion", ["cv_rmse", "cv_mae"])
def test_other_criteria_and_order_independence(criterion):
    case = REFERENCE["cases"][0]
    result = calculate(
        case,
        options(
            selection_criterion=criterion,
            kernel_candidates=tuple(reversed(selection.PRESET_PRIORITY)),
        ),
    )
    assert result["kernel_selection"]["selected_preset"] == case["selected"][criterion[3:]]
    assert all(candidate["details"] is None for candidate in result["kernel_candidates"])
    assert [candidate["preset"] for candidate in result["kernel_candidates"]] == list(
        selection.PRESET_PRIORITY
    )


@pytest.mark.parametrize("restarts", [0, 1, 5])
def test_cv_restarts_and_seed_reproducibility(restarts):
    config = options(
        kernel_candidates=("matern_5_2_ard", "rbf_ard"), cv_folds=2, cv_optimizer_restarts=restarts
    )
    left = calculate(REFERENCE["cases"][0], config)
    right = calculate(REFERENCE["cases"][0], config)
    assert left["kernel_selection"]["optimizer_starts"] == 4 * (1 + restarts) + 1
    assert left["model_summary"] == pytest.approx(right["model_summary"])
    assert (
        left["kernel_selection"]["selected_preset"] == right["kernel_selection"]["selected_preset"]
    )


def test_failure_continuation_and_all_failure(monkeypatch):
    original = selection._cross_validate

    def fail_one(parsed, active, *args, **kwargs):
        if active.kernel_preset == "matern_5_2_ard":
            raise GaussianProcessRegressionError("gp_fit_failed")
        return original(parsed, active, *args, **kwargs)

    monkeypatch.setattr(selection, "_cross_validate", fail_one)
    result = calculate(
        REFERENCE["cases"][0], options(kernel_candidates=("matern_5_2_ard", "rbf_ard"))
    )
    assert result["kernel_selection"]["selected_preset"] == "rbf_ard"
    assert result["kernel_candidates"][0]["metrics"] is None
    assert result["kernel_candidates"][0]["failure_code"] == "gp_fit_failed"

    def fail_all(*args, **kwargs):
        raise GaussianProcessRegressionError("gp_fit_failed")

    monkeypatch.setattr(selection, "_cross_validate", fail_all)
    with pytest.raises(GaussianProcessRegressionError, match="gp_all_kernel_candidates_failed"):
        calculate(REFERENCE["cases"][0], options())


def test_tie_and_optimizer_budget_arithmetic():
    metrics = {"nlpd": 1, "rmse": 1, "mae": 1, "interval_coverage_95": 0.95}
    candidates = [
        {"preset": preset, "metrics": metrics, "status": "succeeded"}
        for preset in reversed(selection.PRESET_PRIORITY)
    ]
    assert selection.rank_candidates(candidates, "cv_nlpd")[0]["preset"] == "matern_5_2_ard"
    assert optimizer_start_count(options(cv_optimizer_restarts=5, optimizer_restarts=3), 5) == 124
    assert (
        optimizer_start_count(
            options(cv_optimizer_restarts=5, optimizer_restarts=3, retain_candidate_details=True), 5
        )
        == 136
    )
    frontend = (Path(__file__).parents[3] / "frontend/src/gpCapabilities.ts").read_text(
        encoding="utf-8"
    )
    assert f"MAX_GP_OPTIMIZER_STARTS = {MAX_GP_OPTIMIZER_STARTS}" in frontend
    with pytest.raises(GaussianProcessRegressionError, match="gp_kernel_search_budget_exceeded"):
        calculate(
            REFERENCE["cases"][0],
            options(
                cv_folds=10,
                cv_optimizer_restarts=5,
                optimizer_restarts=10,
                retain_candidate_details=True,
            ),
        )


def test_request_union_legacy_normalization_and_invalid_combinations():
    base = {"response_column_id": "y", "predictor_column_ids": ["x"]}
    legacy = GaussianProcessRegressionOptions.model_validate({**base, "kernel_preset": "rbf_ard"})
    assert legacy.kernel_selection.mode == "single"
    assert legacy.kernel_selection.kernel_preset == "rbf_ard"
    with pytest.raises(ValidationError):
        GaussianProcessRegressionOptions.model_validate({**base, "cv_optimizer_restarts": 6})
    for candidates in [["rbf_ard"], ["rbf_ard", "rbf_ard"], ["rbf_ard", "white_kernel"]]:
        with pytest.raises(ValidationError):
            GaussianProcessRegressionOptions.model_validate(
                {**base, "kernel_selection": {"mode": "compare", "kernel_candidates": candidates}}
            )
    with pytest.raises(ValidationError, match="gp_kernel_comparison_requires_validation"):
        GaussianProcessRegressionOptions.model_validate(
            {
                **base,
                "cv": {"method": "none"},
                "kernel_selection": {
                    "mode": "compare",
                    "kernel_candidates": ["rbf_ard", "matern_5_2_ard"],
                },
            }
        )
