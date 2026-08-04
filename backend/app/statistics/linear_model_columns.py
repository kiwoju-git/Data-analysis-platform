from __future__ import annotations

from typing import Literal

LinearModelPredictorKind = Literal["numeric", "categorical", "unsupported"]

_NUMERIC_DATA_TYPES = {"integer", "decimal"}
_CATEGORICAL_MEASUREMENT_LEVELS = {"nominal", "ordinal", "binary"}
_NUMERIC_RESPONSE_MEASUREMENT_LEVELS = {"continuous", "count", "unknown"}


def classify_linear_model_predictor(
    *,
    data_type: object,
    measurement_level: object,
    role: object,
) -> LinearModelPredictorKind:
    """Classify model representation independently from the analysis role."""
    if role == "id" or measurement_level == "id":
        return "unsupported"
    if data_type == "datetime" or measurement_level == "datetime":
        return "unsupported"
    if measurement_level in _CATEGORICAL_MEASUREMENT_LEVELS:
        return "categorical"
    if data_type in _NUMERIC_DATA_TYPES:
        return "numeric"
    if data_type in {"text", "boolean"}:
        return "categorical"
    return "unsupported"


def is_supported_linear_model_response(
    *,
    data_type: object,
    measurement_level: object,
    role: object,
) -> bool:
    if role == "id" or measurement_level == "id":
        return False
    return (
        data_type in _NUMERIC_DATA_TYPES
        and measurement_level in _NUMERIC_RESPONSE_MEASUREMENT_LEVELS
    )
