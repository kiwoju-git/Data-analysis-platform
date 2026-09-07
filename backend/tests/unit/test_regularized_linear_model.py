import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from app.statistics.linear_model import LinearModelColumn, LinearModelError
from app.statistics.regularized_linear_model import (
    RegularizationConfig,
    calculate_regularized_linear_model,
)

REFERENCE = json.loads(
    Path("backend/tests/reference/fixtures/regularized_linear_model_reference.json").read_text(
        encoding="utf-8"
    )
)


def column(name, index, categorical=False):
    return LinearModelColumn(
        name,
        index,
        name,
        "text" if categorical else "decimal",
        "nominal" if categorical else "continuous",
        "factor",
        None,
    )


def calculate(x, y, config, **kwargs):
    rows = [
        [str(value) if value is not None else None for value in [target, *row]]
        for row, target in zip(x, y, strict=True)
    ]
    return calculate_regularized_linear_model(
        rows,
        column("y", 0),
        [column(f"x{i}", i + 1) for i in range(len(x[0]))],
        config=config,
        **kwargs,
    )


@pytest.mark.parametrize("kind", ["ridge", "lasso", "elastic_net"])
def test_fixed_static_independent_reference(kind):
    data = REFERENCE["input"]
    expected = REFERENCE["fixed"][kind]
    result = calculate(
        data["x"],
        data["y"],
        RegularizationConfig(
            estimator=kind,
            mode="fixed",
            validation="none",
            fixed_alpha=0.2,
            fixed_l1_ratio=0.7,
            max_iter=100_000,
            tolerance=1e-10,
        ),
    )
    assert result["schema_version"] == 6
    np.testing.assert_allclose(
        [row["estimate"] for row in result["coefficients"]],
        [expected["intercept"], *expected["coefficients"]],
        atol=1e-7,
    )
    prediction = result["equation"]["intercept"] + np.asarray(data["new_x"]) @ np.asarray(
        [row["estimate"] for row in result["coefficients"][1:]]
    )
    np.testing.assert_allclose(prediction, expected["prediction"], atol=1e-7)
    assert result["regularization"]["converged"]
    assert result["prediction_basis"]["kind"] == "point_only"
    assert "xtx_inverse" not in result["prediction_basis"]
    assert "anova" not in result
    assert "adjusted_r_squared" not in result["fit"]
    for row in result["coefficients"]:
        assert (
            not {"p_value", "statistic", "standard_error", "confidence_interval", "vif"}
            & row.keys()
        )


@pytest.mark.parametrize("kind", ["ridge", "lasso", "elastic_net"])
def test_nested_cv_static_independent_reference(kind):
    data = REFERENCE["input"]
    expected = REFERENCE["automatic"][kind]
    result = calculate(
        data["x"],
        data["y"],
        RegularizationConfig(
            estimator=kind,
            outer_folds=3,
            inner_folds=3,
            alpha_candidates=5,
            alpha_min=1e-3,
            alpha_max=10,
            l1_ratio_candidates=(0.1, 0.7),
            max_iter=100_000,
            tolerance=1e-10,
        ),
    )
    validation = result["validation"]
    assert validation["nested"]
    assert result["regularization"]["selected_alpha"] == pytest.approx(
        expected["selected"]["model__alpha"]
    )
    if kind == "elastic_net":
        assert (
            result["regularization"]["selected_l1_ratio"] == expected["selected"]["model__l1_ratio"]
        )
    np.testing.assert_allclose(
        validation["oof_predictions"], expected["oof_predictions"], atol=1e-7
    )
    for metric in ("press", "predicted_r_squared", "rmse", "mae"):
        assert validation[metric] == pytest.approx(expected[metric], abs=1e-7)
    test_rows = [index for fold in validation["folds"] for index in fold["test_row_indices"]]
    assert sorted(test_rows) == list(range(len(data["y"])))
    x = np.asarray(data["x"])
    for fold in validation["folds"]:
        train = np.delete(x, fold["test_row_indices"], axis=0)
        np.testing.assert_allclose(fold["scaler_means"], train.mean(axis=0), atol=1e-12)
        assert not np.allclose(fold["scaler_means"], x.mean(axis=0))
    np.testing.assert_allclose(result["regularization"]["scaler_means"], x.mean(axis=0))
    assert (
        result["regularization"]["estimated_fit_count"]
        == result["regularization"]["completed_fit_count"]
    )


@pytest.mark.parametrize("kind", ["ridge", "lasso", "elastic_net"])
def test_hand_checkable_orthogonal_shrinkage(kind):
    x = np.array([[-1, -1], [-1, 1], [1, -1], [1, 1]] * 2, dtype=float)
    y = 5 + 2 * x[:, 0] + 0.1 * x[:, 1]
    result = calculate(
        x,
        y,
        RegularizationConfig(
            estimator=kind, mode="fixed", validation="none", fixed_alpha=0.5, fixed_l1_ratio=0.5
        ),
    )
    if kind == "ridge":
        expected = [5, 2 * 8 / 8.5, 0.1 * 8 / 8.5]
    elif kind == "lasso":
        expected = [5, 1.5, 0]
    else:
        expected = [5, (2 - 0.25) / 1.25, 0]
    np.testing.assert_allclose(
        [item["estimate"] for item in result["coefficients"]], expected, atol=1e-10
    )


def test_complete_case_constant_fold_and_zero_model_are_explicit():
    rows = [[str(i), str(i), "B" if i == 0 else "A"] for i in range(12)]
    rows += [[None, "20", "A"], ["bad", "21", "A"]]
    result = calculate_regularized_linear_model(
        rows,
        column("y", 0),
        [column("x", 1), column("group", 2, True)],
        config=RegularizationConfig(
            estimator="lasso", mode="fixed", fixed_alpha=1e6, outer_folds=3
        ),
    )
    assert result["sample"]["n_used"] == 12
    assert result["sample"]["n_excluded_missing"] == 1
    assert result["sample"]["n_excluded_non_numeric"] == 1
    assert result["regularization"]["zero_coefficient_count"] == 2
    assert "regularized_model_categorical_levelwise_penalty" in result["warnings"]
    assert "regularized_model_constant_fold_feature" in result["warnings"]
    assert "lasso_all_or_most_coefficients_zero" in result["warnings"]
    assert result["validation"]["predicted_r_squared"] < 0


def test_fixed_loo_and_collinear_p_greater_than_n():
    rng = np.random.default_rng(19)
    x = rng.normal(size=(8, 10))
    x[:, 1] = x[:, 0]
    y = rng.normal(size=8)
    result = calculate(
        x, y, RegularizationConfig(mode="fixed", fixed_alpha=1, validation="leave_one_out")
    )
    assert result["validation"]["outer_folds"] == 8
    assert result["sample"]["feature_count"] == 10
    assert result["regularization"]["converged"]


def test_derived_features_keep_original_scale_prediction():
    x = [[i / 5, (i % 3) + 0.1 * i] for i in range(20)]
    y = [2 + row[0] ** 2 + row[0] * row[1] + (i % 2) / 10 for i, row in enumerate(x)]
    result = calculate(
        x,
        y,
        RegularizationConfig(mode="fixed", validation="none", fixed_alpha=0.01),
        quadratic_terms=["x0"],
        interaction_terms=[("x0", "x1")],
    )
    assert result["regularization"]["feature_order"] == ["x0", "x1", "x0^2", "x0:x1"]
    beta = np.array([row["estimate"] for row in result["coefficients"]])
    expected = [[1, a, b, a * a, a * b] @ beta for a, b in x]
    np.testing.assert_allclose(
        [row["fitted"] for row in result["diagnostics"]["points"]], expected, atol=1e-10
    )


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"fixed_alpha": 0}, "regularized_model_alpha_invalid"),
        ({"estimator": "elastic_net", "fixed_l1_ratio": 1}, "regularized_model_l1_ratio_invalid"),
        ({"estimator": "elastic_net", "fixed_l1_ratio": 0}, "regularized_model_l1_ratio_invalid"),
        ({"outer_folds": 11}, "regularized_model_cv_folds_invalid"),
    ],
)
def test_invalid_config(changes, code):
    config = replace(RegularizationConfig(mode="fixed", fixed_alpha=1), **changes)
    with pytest.raises(LinearModelError, match=code):
        calculate(REFERENCE["input"]["x"], REFERENCE["input"]["y"], config)


def test_search_budget_rejected_before_fitting():
    with pytest.raises(LinearModelError, match="regularized_model_search_budget_exceeded"):
        calculate(
            REFERENCE["input"]["x"],
            REFERENCE["input"]["y"],
            RegularizationConfig(
                estimator="elastic_net",
                outer_folds=10,
                inner_folds=10,
                alpha_candidates=100,
            ),
        )


def test_timeout_and_nonconvergence_are_not_silent():
    data = REFERENCE["input"]
    with pytest.raises(LinearModelError, match="regularized_model_time_budget_exhausted"):
        calculate(data["x"], data["y"], RegularizationConfig(time_budget_seconds=1e-12))
    result = calculate(
        data["x"],
        data["y"],
        RegularizationConfig(
            estimator="lasso",
            mode="fixed",
            fixed_alpha=1e-9,
            validation="none",
            max_iter=1,
        ),
    )
    assert not result["regularization"]["converged"]
    assert "regularized_model_convergence_warning" in result["warnings"]
