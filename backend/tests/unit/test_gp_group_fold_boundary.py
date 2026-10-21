import numpy as np
import pytest
from sklearn.model_selection import GroupKFold

from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    calculate_gaussian_process_regression,
)
from app.statistics.gp_validation import GpValidationError, build_validation_plan


def test_group_count_equal_to_row_count_and_fold_count_is_supported():
    groups = ["batch-A", "batch-B", "batch-C", "batch-D", "batch-E"]
    independent = list(GroupKFold(n_splits=5).split(np.arange(5), groups=groups))
    plan = build_validation_plan(
        method="group_k_fold",
        row_indices=list(range(5)),
        folds=5,
        shuffle=False,
        seed=7,
        groups=groups,
    )
    assert [(train.tolist(), test.tolist()) for train, test in plan.splits] == [
        (train.tolist(), test.tolist()) for train, test in independent
    ]
    assert plan.scored_mask.tolist() == [True] * 5
    assert all(fold["training_count"] == 4 for fold in plan.payload["folds"])
    assert all(
        fold["train_validation_group_intersection_count"] == 0 for fold in plan.payload["folds"]
    )


def test_actual_gp_accepts_five_group_fold_boundary_without_changing_row_cv_policy():
    response = GaussianProcessColumn("y", 0, "Response", "decimal", "continuous", "response", "mm")
    predictor = GaussianProcessColumn("x", 1, "Input", "decimal", "continuous", "feature", "s")
    group = GaussianProcessColumn("group", 2, "Batch", "string", "nominal", "id", None)
    rows = [[str(2 * index + 0.1 * index**2), str(index), f"batch-{index}"] for index in range(5)]
    result = calculate_gaussian_process_regression(
        rows,
        response,
        [predictor],
        metadata_columns=[group],
        options=GaussianProcessOptions(
            validation_method="group_k_fold",
            group_column_id="group",
            cv_folds=5,
            cv_shuffle=False,
            optimizer_restarts=0,
            cv_optimizer_restarts=0,
            noise_mode="fixed",
            fixed_noise_standard_deviation=0.1,
        ),
    )
    assert result["sample"]["n_used"] == 5
    assert result["validation_plan"]["n_scored"] == 5
    assert result["validation_plan"]["distinct_group_count"] == 5
    assert np.isfinite(result["model_summary"]["cv_rmse"])
    assert all(
        point["cross_validated_fitted"] is not None for point in result["diagnostics"]["points"]
    )
    with pytest.raises(GpValidationError, match="gp_cv_fold_invalid"):
        build_validation_plan(
            method="k_fold",
            row_indices=list(range(5)),
            folds=5,
            shuffle=False,
            seed=7,
        )
