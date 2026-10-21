"""Fold-local numeric scaling and equality-only nominal encoding for GPR."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


class GpPreprocessingError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class GpPredictorSpec:
    column_id: str
    kind: Literal["numeric", "nominal"]


@dataclass(frozen=True)
class _PredictorState:
    spec: GpPredictorSpec
    mean: float = 0.0
    scale: float = 1.0
    median: float = 0.0
    minimum: float = 0.0
    maximum: float = 0.0
    vocabulary: tuple[str, ...] = ()
    counts: tuple[int, ...] = ()
    mode: str | None = None


def _validate_specs(predictors: Sequence[GpPredictorSpec]) -> None:
    if (
        not 1 <= len(predictors) <= 12
        or any(
            not isinstance(predictor, GpPredictorSpec)
            or not isinstance(predictor.column_id, str)
            or not predictor.column_id
            or predictor.kind not in {"numeric", "nominal"}
            for predictor in predictors
        )
        or len({predictor.column_id for predictor in predictors}) != len(predictors)
        or sum(predictor.kind == "nominal" for predictor in predictors) > 4
    ):
        raise GpPreprocessingError("gp_predictor_contract_invalid")


def _number(value: Any) -> float:
    if isinstance(value, bool | np.bool_) or not isinstance(value, int | float | np.number):
        raise GpPreprocessingError("gp_numeric_value_invalid")
    try:
        numeric = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise GpPreprocessingError("gp_numeric_value_invalid") from exc
    if not math.isfinite(numeric):
        raise GpPreprocessingError("gp_numeric_value_invalid")
    return numeric


def _category(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise GpPreprocessingError("gp_category_value_invalid")
    return value


def _rows(rows: Sequence[Sequence[Any]], width: int, *, minimum: int) -> list[list[Any]]:
    if isinstance(rows, str | bytes):
        raise GpPreprocessingError("gp_predictor_rows_invalid")
    try:
        result = []
        for row in rows:
            if isinstance(row, str | bytes):
                raise ValueError
            result.append(list(row))
    except (TypeError, ValueError) as exc:
        raise GpPreprocessingError("gp_predictor_rows_invalid") from exc
    if len(result) < minimum or any(len(row) != width for row in result):
        raise GpPreprocessingError("gp_predictor_rows_invalid")
    return result


@dataclass(frozen=True)
class GpPreprocessor:
    states: tuple[_PredictorState, ...]
    standardize_numeric: bool
    training_row_count: int
    warning_codes: tuple[str, ...]
    allow_constant_numeric: bool = False

    @property
    def numeric_indices(self) -> tuple[int, ...]:
        return tuple(i for i, state in enumerate(self.states) if state.spec.kind == "numeric")

    @property
    def categorical_indices(self) -> tuple[int, ...]:
        return tuple(i for i, state in enumerate(self.states) if state.spec.kind == "nominal")

    @property
    def active_categorical_indices(self) -> tuple[int, ...]:
        return tuple(i for i in self.categorical_indices if len(self.states[i].vocabulary) > 1)

    @property
    def hold_values(self) -> tuple[float | str, ...]:
        return tuple(
            state.median if state.spec.kind == "numeric" else str(state.mode)
            for state in self.states
        )

    def to_payload(self) -> dict[str, Any]:
        predictors = []
        for state in self.states:
            item: dict[str, Any] = {"column_id": state.spec.column_id, "kind": state.spec.kind}
            if state.spec.kind == "numeric":
                item.update(
                    mean=state.mean,
                    scale=state.scale,
                    median=state.median,
                    minimum=state.minimum,
                    maximum=state.maximum,
                )
            else:
                item.update(
                    vocabulary=list(state.vocabulary), counts=list(state.counts), mode=state.mode
                )
            predictors.append(item)
        return {
            "schema_version": 1,
            "standardize_numeric": self.standardize_numeric,
            "numeric_scale_ddof": 1,
            "numeric_constant_policy": "allow_unscaled"
            if self.allow_constant_numeric
            else "reject",
            "training_row_count": self.training_row_count,
            "category_order_policy": "first_training_occurrence",
            "mode_tie_policy": "first_training_occurrence",
            "predictors": predictors,
        }

    @classmethod
    def from_payload(cls, payload: Any) -> GpPreprocessor:
        try:
            return _read_payload(payload)
        except (GpPreprocessingError, KeyError, TypeError, ValueError, OverflowError) as exc:
            raise GpPreprocessingError("gp_preprocessor_payload_invalid") from exc


def _warnings(states: Sequence[_PredictorState], n: int) -> tuple[str, ...]:
    result: list[str] = []
    for state in states:
        if state.spec.kind != "nominal":
            if state.minimum == state.maximum:
                result.append("gp_numeric_constant_training_fold")
            continue
        if len(state.vocabulary) == 1:
            result.append("gp_categorical_constant_training_fold")
        if min(state.counts) < 3:
            result.append("gp_category_sparse_levels")
        if len(state.vocabulary) > 16 or len(state.vocabulary) > n / 2:
            result.append("gp_category_high_cardinality")
    return tuple(dict.fromkeys(result))


def fit_gp_preprocessor(
    rows: Sequence[Sequence[Any]],
    predictors: Sequence[GpPredictorSpec],
    *,
    standardize_numeric: bool = True,
    allow_constant_numeric: bool = False,
) -> tuple[GpPreprocessor, FloatArray]:
    _validate_specs(predictors)
    if (
        not isinstance(standardize_numeric, bool)
        or not isinstance(allow_constant_numeric, bool)
        or (standardize_numeric and allow_constant_numeric)
    ):
        raise GpPreprocessingError("gp_predictor_contract_invalid")
    training = _rows(rows, len(predictors), minimum=2)
    states: list[_PredictorState] = []
    for index, predictor in enumerate(predictors):
        if predictor.kind == "numeric":
            values = np.array([_number(row[index]) for row in training])
            with np.errstate(over="ignore", invalid="ignore"):
                actual_mean, actual_scale = float(values.mean()), float(values.std(ddof=1))
                median = float(np.median(values))
            if not all(math.isfinite(value) for value in (actual_mean, actual_scale, median)):
                raise GpPreprocessingError("gp_numeric_scaling_invalid")
            if actual_scale <= 0 and not allow_constant_numeric:
                raise GpPreprocessingError("gp_numeric_predictor_constant")
            states.append(
                _PredictorState(
                    predictor,
                    actual_mean if standardize_numeric else 0.0,
                    actual_scale if standardize_numeric else 1.0,
                    median,
                    float(values.min()),
                    float(values.max()),
                )
            )
        else:
            counts: dict[str, int] = {}
            for row in training:
                category = _category(row[index])
                counts[category] = counts.get(category, 0) + 1
                if len(counts) > 32:
                    raise GpPreprocessingError("gp_category_level_limit")
            mode = max(counts, key=lambda key: counts[key])
            states.append(
                _PredictorState(
                    predictor,
                    vocabulary=tuple(counts),
                    counts=tuple(counts.values()),
                    mode=mode,
                )
            )
    processor = GpPreprocessor(
        tuple(states),
        standardize_numeric,
        len(training),
        _warnings(states, len(training)),
        allow_constant_numeric,
    )
    return processor, transform_gp_rows(processor, training)


def transform_gp_rows(processor: GpPreprocessor, rows: Sequence[Sequence[Any]]) -> FloatArray:
    source = _rows(rows, len(processor.states), minimum=1)
    result = np.empty((len(source), len(processor.states)), dtype=np.float64)
    for index, state in enumerate(processor.states):
        if state.spec.kind == "numeric":
            values = np.array([_number(row[index]) for row in source])
            with np.errstate(over="ignore", invalid="ignore"):
                result[:, index] = (values - state.mean) / state.scale
        else:
            codes = {value: code for code, value in enumerate(state.vocabulary)}
            for row_index, row in enumerate(source):
                category = _category(row[index])
                if category not in codes:
                    raise GpPreprocessingError("gp_category_unknown")
                result[row_index, index] = codes[category]
    validate_encoded_gp_matrix(processor, result)
    return result


def validate_encoded_gp_matrix(processor: GpPreprocessor, matrix: Any) -> None:
    values = np.asarray(matrix)
    if (
        values.dtype.kind not in "iuf"
        or values.ndim != 2
        or values.shape[1] != len(processor.states)
        or len(values) == 0
        or not np.all(np.isfinite(values))
    ):
        raise GpPreprocessingError("gp_encoded_matrix_invalid")
    for index in processor.categorical_indices:
        codes = values[:, index]
        if (
            np.any(codes != np.floor(codes))
            or np.any(codes < 0)
            or np.any(codes >= len(processor.states[index].vocabulary))
        ):
            raise GpPreprocessingError("gp_encoded_matrix_invalid")


def _read_payload(payload: Any) -> GpPreprocessor:
    expected = {
        "schema_version",
        "standardize_numeric",
        "numeric_scale_ddof",
        "numeric_constant_policy",
        "training_row_count",
        "category_order_policy",
        "mode_tie_policy",
        "predictors",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ValueError
    if (
        type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
        or type(payload["numeric_scale_ddof"]) is not int
        or payload["numeric_scale_ddof"] != 1
        or not isinstance(payload["standardize_numeric"], bool)
        or payload["numeric_constant_policy"] not in {"reject", "allow_unscaled"}
        or (payload["standardize_numeric"] and payload["numeric_constant_policy"] != "reject")
        or type(payload["training_row_count"]) is not int
        or payload["training_row_count"] < 2
        or payload["category_order_policy"] != "first_training_occurrence"
        or payload["mode_tie_policy"] != "first_training_occurrence"
        or not isinstance(payload["predictors"], list)
    ):
        raise ValueError
    states = []
    for item in payload["predictors"]:
        if not isinstance(item, dict):
            raise ValueError
        spec = GpPredictorSpec(item["column_id"], item["kind"])
        if spec.kind == "numeric":
            keys = {"column_id", "kind", "mean", "scale", "median", "minimum", "maximum"}
            if set(item) != keys:
                raise ValueError
            mean, scale, median, minimum, maximum = (
                _number(item[key]) for key in ("mean", "scale", "median", "minimum", "maximum")
            )
            if not (scale > 0 and minimum <= maximum and minimum <= median <= maximum):
                raise ValueError
            if minimum == maximum and payload["numeric_constant_policy"] != "allow_unscaled":
                raise ValueError
            if not payload["standardize_numeric"] and (mean != 0 or scale != 1):
                raise ValueError
            states.append(_PredictorState(spec, mean, scale, median, minimum, maximum))
        elif spec.kind == "nominal":
            if set(item) != {"column_id", "kind", "vocabulary", "counts", "mode"}:
                raise ValueError
            vocabulary, counts = item["vocabulary"], item["counts"]
            if (
                not isinstance(vocabulary, list)
                or not 1 <= len(vocabulary) <= 32
                or any(not isinstance(value, str) or not value for value in vocabulary)
                or len(set(vocabulary)) != len(vocabulary)
                or not isinstance(counts, list)
                or len(counts) != len(vocabulary)
                or any(type(count) is not int or count < 1 for count in counts)
                or sum(counts) != payload["training_row_count"]
                or item["mode"] != vocabulary[counts.index(max(counts))]
            ):
                raise ValueError
            states.append(
                _PredictorState(
                    spec,
                    vocabulary=tuple(vocabulary),
                    counts=tuple(counts),
                    mode=item["mode"],
                )
            )
        else:
            raise ValueError
    _validate_specs(tuple(state.spec for state in states))
    n = payload["training_row_count"]
    return GpPreprocessor(
        tuple(states),
        payload["standardize_numeric"],
        n,
        _warnings(states, n),
        payload["numeric_constant_policy"] == "allow_unscaled",
    )
