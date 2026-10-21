from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    GaussianProcessRegressionError,
    calculate_gaussian_process_regression,
)
from app.statistics.gp_time_features import LagObservation, build_lag_features
from app.statistics.gp_validation import GpValidationError, build_validation_plan, parse_time_value


def test_group_plan_uses_full_identity_and_no_train_test_intersection() -> None:
    groups = ["X" * 121 + suffix for suffix in ["-A", "-A", "-B", "-B", "-C", "-C"]]
    plan = build_validation_plan(
        method="group_k_fold",
        row_indices=[4, 8, 9, 10, 12, 18],
        folds=3,
        shuffle=False,
        seed=29,
        groups=groups,
    )
    assert all(plan.scored_mask)
    assert plan.payload["distinct_group_count"] == 3
    for train, test in plan.splits:
        assert not {groups[i] for i in train} & {groups[i] for i in test}
    assert (
        plan.payload["split_plan_sha256"]
        == build_validation_plan(
            method="group_k_fold",
            row_indices=[4, 8, 9, 10, 12, 18],
            folds=3,
            shuffle=False,
            seed=29,
            groups=groups,
        ).payload["split_plan_sha256"]
    )


def test_time_blocks_gap_and_warmup_are_explicit() -> None:
    times = [4.0, 1.0, 3.0, 1.0, 2.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    plan = build_validation_plan(
        method="time_series_split",
        row_indices=list(range(len(times))),
        folds=3,
        shuffle=False,
        seed=1,
        times=times,
        gap_time_blocks=1,
    )
    assert not all(plan.scored_mask)
    for train, test in plan.splits:
        assert max(times[i] for i in train) < min(times[i] for i in test)
        assert not {times[i] for i in train} & {times[i] for i in test}
        assert len(set(times)) >= 3
        assert (1 in train) == (3 in train)
        assert (1 in test) == (3 in test)
    assert plan.payload["gap_unit"] == "time_blocks"


@pytest.mark.parametrize(
    "groups,code", [(["a", "a", "a", "b"], "group_count"), (["a", "", "b", "c"], "group_missing")]
)
def test_invalid_group_plan_does_not_guess(groups: list[str], code: str) -> None:
    with pytest.raises(GpValidationError, match=code):
        build_validation_plan(
            method="group_k_fold",
            row_indices=list(range(4)),
            folds=3,
            shuffle=False,
            seed=1,
            groups=groups,
        )


def test_timestamp_requires_explicit_timezone_rule() -> None:
    with pytest.raises(GpValidationError, match="timezone_required"):
        parse_time_value("2026-01-01T12:00:00", time_format="timestamp")
    utc = parse_time_value("2026-01-01T12:00:00Z", time_format="timestamp")
    assert utc == parse_time_value("2026-01-01T21:00:00+09:00", time_format="timestamp")
    assert utc == parse_time_value(
        "2026-01-01T12:00:00", time_format="timestamp", timestamp_timezone="UTC"
    )


def test_lag_never_crosses_series_or_reads_same_or_future_time() -> None:
    observations = [
        LagObservation(i, time, series, {"y": value})
        for i, (time, series, value) in enumerate(
            [
                (3.0, "a", 30.0),
                (1.0, "b", 101.0),
                (1.0, "a", 10.0),
                (2.0, "a", 20.0),
                (2.0, "b", 102.0),
                (4.0, "a", 40.0),
            ]
        )
    ]
    lag = build_lag_features(observations, column_ids=["y"], lags=[1])
    assert lag.values_by_row[0] == [20.0]
    assert lag.values_by_row[4] == [101.0]
    assert set(lag.excluded_row_indices) == {1, 2}
    assert lag.source_rows_by_row[0] == [3]
    assert all(
        source < observations[row].time
        for row, sources in lag.source_times_by_row.items()
        for source in sources
    )


def test_lag_duplicate_timestamp_within_series_is_rejected_not_ordered() -> None:
    with pytest.raises(GpValidationError, match="ambiguous_time"):
        build_lag_features(
            [LagObservation(0, 1.0, "a", {"y": 1.0}), LagObservation(1, 1.0, "a", {"y": 2.0})],
            column_ids=["y"],
            lags=[1],
        )


def test_lag_sources_in_embargo_are_removed_before_fit_not_hidden_failure() -> None:
    times = list(map(float, range(12)))
    plan = build_validation_plan(
        method="time_series_split",
        row_indices=list(range(12)),
        folds=2,
        shuffle=False,
        seed=1,
        times=times,
        gap_time_blocks=1,
        lag_source_times=[[time - 1] for time in times],
    )
    assert plan.payload["n_excluded_lag_embargo"] == 2
    for fold in plan.payload["folds"]:
        assert len(fold["excluded_lag_embargo_row_indices"]) == 1
    assert all(len(test) > 0 for _, test in plan.splits)


def _columns() -> list[GaussianProcessColumn]:
    return [
        GaussianProcessColumn(
            name,
            i,
            name,
            "integer" if name in {"y", "x", "time"} else "string",
            "continuous" if name != "group" else "nominal",
            "id" if name == "group" else "feature",
            None,
        )
        for i, name in enumerate(["y", "x", "group", "time"])
    ]


def _options(**updates) -> GaussianProcessOptions:
    return replace(
        GaussianProcessOptions(
            optimizer_restarts=0,
            cv_optimizer_restarts=0,
            profile_points=10,
            surface_grid_size=10,
            cv_folds=3,
        ),
        **updates,
    )


def test_lag_preparation_rejects_explicit_memory_budget_before_fit(monkeypatch) -> None:
    import app.statistics.gaussian_process_regression as gp

    cols = _columns()
    monkeypatch.setattr(gp, "MAX_GP_LAG_PREPARATION_BYTES", 1024, raising=False)
    with pytest.raises(GaussianProcessRegressionError, match="gp_parse_memory_budget_exceeded"):
        calculate_gaussian_process_regression(
            [[str(i), str(i), "g", str(i)] for i in range(10)],
            cols[0],
            cols[1:2],
            options=_options(
                validation_method="time_series_split",
                cv_shuffle=False,
                time_column_id="time",
                time_format="numeric",
                time_unit="seconds",
                lagged_column_ids=("y",),
                lags=(1,),
            ),
            metadata_columns=cols[2:],
        )


def test_stream_row_limit_stops_reading_without_silent_sampling() -> None:
    cols = _columns()

    def rows():
        for i in range(501):
            yield [str(i), str(i)]
        raise AssertionError("Rows beyond the explicit valid-row limit were consumed")

    with pytest.raises(GaussianProcessRegressionError, match="gp_usable_rows_limit"):
        calculate_gaussian_process_regression(
            rows(), cols[0], cols[1:2], options=_options(validation_method="none")
        )


def test_group_cv_calculation_preserves_metadata_alignment_after_exclusions() -> None:
    cols = _columns()
    rows = [[str(np.sin(i / 3)), str(i), "X" * 121 + str(i % 4), str(i)] for i in range(24)]
    rows[3][1] = ""
    result = calculate_gaussian_process_regression(
        rows,
        cols[0],
        [cols[1]],
        metadata_columns=cols[2:],
        options=_options(
            validation_method="group_k_fold", cv_shuffle=False, group_column_id="group"
        ),
    )
    assert result["sample"]["n_used"] == 23
    plan = result["validation_plan"]
    assert plan["distinct_group_count"] == 4
    for record in result["optimization"]["cv_folds"]:
        train = record["training_row_indices"]
        test = record["validation_row_indices"]
        assert 3 not in train + test
        assert not {rows[i][2] for i in train} & {rows[i][2] for i in test}
        assert record["x_mean"] == pytest.approx([np.mean([float(rows[i][1]) for i in train])])


def test_time_cv_metrics_score_only_predicted_rows_and_json_warmup_is_null() -> None:
    cols = _columns()
    rows = [[str(np.sin(i / 3)), str(i), str(i % 4), str(i)] for i in range(24)]
    result = calculate_gaussian_process_regression(
        rows,
        cols[0],
        [cols[1]],
        metadata_columns=cols[2:],
        options=_options(
            validation_method="time_series_split",
            cv_shuffle=False,
            time_column_id="time",
            time_format="numeric",
            time_unit="day",
        ),
    )
    points = result["diagnostics"]["points"]
    scored = [point for point in points if point["cross_validated_fitted"] is not None]
    assert 0 < len(scored) < len(points)
    residuals = np.array([p["observed"] - p["cross_validated_fitted"] for p in scored])
    assert result["model_summary"]["press"] == pytest.approx(float(residuals @ residuals))
    assert result["model_summary"]["cv_rmse"] == pytest.approx(np.sqrt(np.mean(residuals**2)))
    import json

    json.dumps({k: v for k, v in result.items() if k != "prediction_basis"}, allow_nan=False)


def test_lag_calculation_has_virtual_predictors_and_explicit_past_lineage() -> None:
    cols = _columns()
    rows = [[str(np.sin(i / 4) + i * 0.03), str(i), "series", str(i)] for i in range(36)]
    result = calculate_gaussian_process_regression(
        rows,
        cols[0],
        [cols[1]],
        metadata_columns=cols[2:],
        options=_options(
            validation_method="time_series_split",
            cv_shuffle=False,
            time_column_id="time",
            time_format="numeric",
            time_unit="day",
            lagged_column_ids=("y",),
            lags=(1,),
            series_column_id="group",
        ),
    )
    assert result["sample"]["n_excluded_lag"] == 1
    assert result["sample"]["predictor_count"] == 2
    assert result["predictors"][1]["column_id"] == "gp_lag:y:1"
    assert result["feature_lineage"]["prediction_horizon"] == 1
    for row in result["feature_lineage"]["rows"]:
        assert all(index < row["row_index"] for index in row["source_row_indices"])


def test_missing_group_metadata_is_explicit_error() -> None:
    cols = _columns()
    rows = [[str(i), str(i), "" if i == 5 else str(i % 3), str(i)] for i in range(12)]
    with pytest.raises(GaussianProcessRegressionError, match="group_missing"):
        calculate_gaussian_process_regression(
            rows,
            cols[0],
            [cols[1]],
            metadata_columns=cols[2:],
            options=_options(
                validation_method="group_k_fold", cv_shuffle=False, group_column_id="group"
            ),
        )


@pytest.mark.parametrize("method", ["group_k_fold", "time_series_split"])
def test_kernel_comparison_reuses_one_plan_and_scored_rows(method) -> None:
    cols = _columns()
    rows = [[str(np.sin(i / 4) + 0.02 * i), str(i), str(i % 3), str(i)] for i in range(24)]
    options = _options(
        validation_method=method,
        cv_shuffle=False,
        group_column_id="group" if method == "group_k_fold" else None,
        time_column_id="time" if method == "time_series_split" else None,
        time_format="numeric" if method == "time_series_split" else None,
        time_unit="day" if method == "time_series_split" else None,
        kernel_selection_mode="compare",
        kernel_candidates=("matern_5_2_ard", "rbf_ard"),
        retain_candidate_details=True,
    )
    result = calculate_gaussian_process_regression(
        rows,
        cols[0],
        [cols[1]],
        metadata_columns=cols[2:],
        options=options,
    )
    expected = result["validation_plan"]["split_plan_sha256"]
    assert result["kernel_selection"]["validation_plan_sha256"] == expected
    for candidate in result["kernel_candidates"]:
        assert candidate["status"] == "succeeded"
        details = candidate["details"]
        assert details["validation_plan"]["split_plan_sha256"] == expected
        assert (
            details["validation_plan"]["scored_row_indices"]
            == result["validation_plan"]["scored_row_indices"]
        )


def test_lag_preserves_past_only_features_and_missing_observation_order() -> None:
    rows = [LagObservation(i, float(i), "a", {"y": float(i)}) for i in range(8)]
    first = build_lag_features(rows, column_ids=["y"], lags=[1, 2])
    changed = [replace(row, values={"y": 999.0}) if row.row_index >= 6 else row for row in rows]
    second = build_lag_features(changed, column_ids=["y"], lags=[1, 2])
    assert all(first.values_by_row[i] == second.values_by_row[i] for i in range(2, 7))
    missing = [replace(row, values={"y": None}) if row.row_index == 3 else row for row in rows]
    result = build_lag_features(missing, column_ids=["y"], lags=[1])
    assert 4 in result.excluded_row_indices
    assert result.source_rows_by_row[5] == [4]


def test_gap_that_removes_entire_validation_fold_is_explicit_error() -> None:
    with pytest.raises(GpValidationError, match="empty_fold_after_lag_gap"):
        build_validation_plan(
            method="time_series_split",
            row_indices=list(range(5)),
            folds=3,
            shuffle=False,
            seed=1,
            times=list(map(float, range(5))),
            gap_time_blocks=1,
            lag_source_times=[[float(i - 1)] for i in range(5)],
        )
