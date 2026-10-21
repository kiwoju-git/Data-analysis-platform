"""Row-identity-preserving split plans for standalone Gaussian Process regression."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any

import numpy as np
from numpy.typing import NDArray


class GpValidationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class GpValidationPlan:
    splits: list[tuple[NDArray[np.int64], NDArray[np.int64]]]
    scored_mask: NDArray[np.bool_]
    payload: dict[str, Any]


def parse_time_value(
    value: str | None,
    *,
    time_format: str,
    timestamp_timezone: str = "require_offset",
    decimal: str = ".",
    thousands: str | None = None,
) -> float:
    if value is None or not str(value).strip():
        raise GpValidationError("gp_validation_time_missing")
    text = str(value).strip()
    try:
        if time_format == "numeric":
            if thousands:
                text = text.replace(thousands, "")
            if decimal != ".":
                text = text.replace(decimal, ".")
            number = float(Decimal(text))
        elif time_format == "timestamp":
            parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                if timestamp_timezone != "UTC":
                    raise GpValidationError("gp_validation_timezone_required")
                parsed = parsed.replace(tzinfo=timezone.utc)
            number = parsed.timestamp()
        else:
            raise GpValidationError("gp_validation_time_format_invalid")
    except GpValidationError:
        raise
    except (ValueError, InvalidOperation, OverflowError, OSError) as exc:
        raise GpValidationError("gp_validation_time_invalid") from exc
    if not isfinite(number):
        raise GpValidationError("gp_validation_time_invalid")
    return number


def build_validation_plan(
    *,
    method: str,
    row_indices: Sequence[int],
    folds: int,
    shuffle: bool,
    seed: int,
    groups: Sequence[str] | None = None,
    times: Sequence[float] | None = None,
    gap_time_blocks: int = 0,
    lag_source_times: Sequence[Sequence[float]] | None = None,
) -> GpValidationPlan:
    from sklearn.model_selection import (  # type: ignore[import-untyped]
        GroupKFold,
        KFold,
        LeaveOneOut,
        TimeSeriesSplit,
    )

    n = len(row_indices)
    if len(set(row_indices)) != n:
        raise GpValidationError("gp_validation_row_identity_invalid")
    indices = np.arange(n, dtype=np.int64)
    splits: list[tuple[NDArray[np.int64], NDArray[np.int64]]] = []
    group_values: list[str] | None = None
    time_values: NDArray[np.float64] | None = None
    gap_exclusions: list[list[int]] = []
    original_validation: list[list[int]] = []
    if method != "none":
        if method != "leave_one_out" and (
            not 2 <= folds <= 10 or folds > n or (folds == n and method != "group_k_fold")
        ):
            raise GpValidationError("gp_cv_fold_invalid")
        if method == "k_fold":
            iterator = KFold(
                n_splits=folds, shuffle=shuffle, random_state=seed if shuffle else None
            ).split(indices)
        elif method == "leave_one_out":
            if n > 200:
                raise GpValidationError("gp_leave_one_out_limit")
            iterator = LeaveOneOut().split(indices)
        elif method == "group_k_fold":
            if shuffle:
                raise GpValidationError("gp_validation_shuffle_unsupported")
            if (
                groups is None
                or len(groups) != n
                or any(not str(value).strip() for value in groups)
            ):
                raise GpValidationError("gp_validation_group_missing")
            group_values = list(groups)
            if len(set(group_values)) < folds:
                raise GpValidationError("gp_cv_group_count_invalid")
            iterator = GroupKFold(n_splits=folds).split(indices, groups=group_values)
        elif method == "time_series_split":
            if shuffle:
                raise GpValidationError("gp_validation_shuffle_unsupported")
            if times is None or len(times) != n:
                raise GpValidationError("gp_validation_time_missing")
            time_values = np.asarray(times, dtype=np.float64)
            if not np.all(np.isfinite(time_values)):
                raise GpValidationError("gp_validation_time_invalid")
            if (
                isinstance(gap_time_blocks, bool)
                or not isinstance(gap_time_blocks, int)
                or gap_time_blocks < 0
            ):
                raise GpValidationError("gp_validation_gap_invalid")
            unique_times = np.unique(time_values)
            order = np.argsort(time_values, kind="stable")
            try:
                block_splits = list(
                    TimeSeriesSplit(n_splits=folds, gap=gap_time_blocks).split(unique_times)
                )
            except ValueError as exc:
                raise GpValidationError("gp_cv_fold_invalid") from exc
            iterator = (
                (
                    order[np.isin(time_values[order], unique_times[train])],
                    order[np.isin(time_values[order], unique_times[test])],
                )
                for train, test in block_splits
            )
        else:
            raise GpValidationError("gp_cv_fold_invalid")
        for train, test in iterator:
            training = np.asarray(train, dtype=np.int64)
            validation = np.asarray(test, dtype=np.int64)
            original_validation.append([int(index) for index in validation])
            excluded: list[int] = []
            if lag_source_times is not None:
                if time_values is None or len(lag_source_times) != n:
                    raise GpValidationError("gp_lag_time_validation_required")
                train_max = float(np.max(time_values[training]))
                validation_min = float(np.min(time_values[validation]))
                excluded = [
                    int(index)
                    for index in validation
                    if any(
                        train_max < value < validation_min for value in lag_source_times[int(index)]
                    )
                ]
                validation = validation[~np.isin(validation, excluded)]
            if not len(training) or not len(validation):
                raise GpValidationError("gp_validation_empty_fold_after_lag_gap")
            splits.append((training, validation))
            gap_exclusions.append(excluded)
    scored = np.zeros(n, dtype=np.bool_)
    records: list[dict[str, Any]] = []
    for index, (training, validation) in enumerate(splits):
        if np.any(scored[validation]):
            raise GpValidationError("gp_validation_overlapping_test_rows")
        scored[validation] = True
        record: dict[str, Any] = {
            "fold": index + 1,
            "training_row_indices": [row_indices[int(i)] for i in training],
            "validation_row_indices": [row_indices[int(i)] for i in validation],
            "planned_validation_row_indices": [row_indices[i] for i in original_validation[index]],
            "excluded_lag_embargo_row_indices": [row_indices[i] for i in gap_exclusions[index]],
            "training_count": len(training),
            "validation_count": len(validation),
        }
        if group_values is not None:
            train_groups = {group_values[int(i)] for i in training}
            test_groups = {group_values[int(i)] for i in validation}
            if train_groups & test_groups:
                raise GpValidationError("gp_validation_group_leakage")
            record.update(
                training_group_count=len(train_groups),
                validation_group_count=len(test_groups),
                train_validation_group_intersection_count=0,
            )
        if time_values is not None:
            if np.max(time_values[training]) >= np.min(time_values[validation]):
                raise GpValidationError("gp_validation_time_leakage")
            record.update(
                training_time_min=float(np.min(time_values[training])),
                training_time_max=float(np.max(time_values[training])),
                validation_time_min=float(np.min(time_values[validation])),
                validation_time_max=float(np.max(time_values[validation])),
            )
        records.append(record)
    payload: dict[str, Any] = {
        "requested_method": method,
        "effective_method": method,
        "aggregation": "row_weighted",
        "folds": records,
        "scored_row_indices": [row_indices[i] for i in range(n) if scored[i]],
        "unscored_row_indices": [row_indices[i] for i in range(n) if not scored[i]],
        "n_scored": int(np.count_nonzero(scored)),
        "n_unscored": int(n - np.count_nonzero(scored)),
        "scored_fraction": float(np.mean(scored)) if n else 0.0,
        "distinct_group_count": len(set(group_values)) if group_values is not None else None,
        "gap_unit": "time_blocks" if method == "time_series_split" else None,
        "gap_time_blocks": gap_time_blocks if method == "time_series_split" else None,
        "n_excluded_lag_embargo": sum(len(value) for value in gap_exclusions),
        "lag_gap_policy": "exclude_embargo_sources" if lag_source_times is not None else None,
        "seed": seed,
        "shuffle": shuffle if method == "k_fold" else False,
        "evaluation_purpose": {
            "k_fold": "exchangeable_rows",
            "group_k_fold": "new_group_generalization",
            "time_series_split": "one_step_rolling_observed_history"
            if lag_source_times is not None
            else "future_observations",
            "leave_one_out": "leave_one_row_out",
            "none": "no_external_validation",
        }[method],
    }
    payload["split_plan_sha256"] = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return GpValidationPlan(splits, scored, payload)
