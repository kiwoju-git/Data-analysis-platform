from __future__ import annotations

from math import isfinite
from typing import Any
from uuid import UUID

from fastapi import status

from app.api.v1.schemas.analyses import (
    PlsPointPredictionRequest,
    PlsPointPredictionResponse,
    PlsPointPredictionRow,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.dataset_rows import get_dataset_rows_context
from app.services.regression_models import get_regression_model_manifest
from app.statistics.pls_regression import PlsRegressionError, predict_from_pls_basis
from app.storage.metadata import get_analysis_run_record


def create_pls_point_predictions(
    settings: Settings,
    *,
    model_id: UUID,
    body: PlsPointPredictionRequest,
) -> PlsPointPredictionResponse:
    model = get_regression_model_manifest(settings, model_id)
    manifest = model.manifest
    if not (
        model.method_id == "regression.partial_least_squares"
        and manifest.get("method_id") == "regression.partial_least_squares"
        and manifest.get("model_family") == "partial_least_squares_regression"
        and manifest.get("manifest_kind") == "pls_model_manifest"
        and manifest.get("manifest_schema_version") == 1
    ):
        raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
    if body.expected_model_manifest_sha256 != model.manifest_sha256:
        raise _error("pls_model_manifest_checksum_mismatch", status.HTTP_409_CONFLICT)
    source_run = get_analysis_run_record(settings.workspace_root, str(model.analysis_id))
    if source_run is None or source_run.stale or source_run.status != "succeeded":
        raise _error("pls_prediction_model_stale", status.HTTP_409_CONFLICT)
    source = get_dataset_rows_context(settings, model.dataset_version_id)
    if not (
        source.version.schema_hash == model.schema_hash
        and manifest.get("source_schema_hash") == model.schema_hash
        and manifest.get("source_canonical_artifact_sha256")
        == source.canonical_rows_artifact.sha256
    ):
        raise _error("pls_prediction_model_stale", status.HTTP_409_CONFLICT)

    predictors = _predictors(manifest)
    basis = _prediction_basis(manifest)
    expected_ids = [str(item["column_id"]) for item in predictors]
    if basis["predictor_order"] != expected_ids:
        raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
    ranges = _training_ranges(manifest, expected_ids)
    client_ids = [row.client_row_id for row in body.rows]
    if len(set(client_ids)) != len(client_ids):
        raise _error("pls_prediction_duplicate_row_id", status.HTTP_422_UNPROCESSABLE_ENTITY)

    output: list[PlsPointPredictionRow] = []
    coefficients = basis["coefficients"]
    intercept = basis["effective_intercept"]
    for row in body.rows:
        if set(row.values) != set(expected_ids):
            raise _error(
                "pls_prediction_predictor_mapping_invalid",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        values: list[float] = []
        warnings: list[str] = []
        for column_id in expected_ids:
            value = row.values[column_id]
            if isinstance(value, bool) or not isfinite(float(value)):
                raise _error("pls_prediction_value_invalid", status.HTTP_422_UNPROCESSABLE_ENTITY)
            numeric = float(value)
            values.append(numeric)
            lower, upper = ranges[column_id]
            if numeric < lower or numeric > upper:
                warnings.append("prediction_extrapolation_risk")
        try:
            prediction = predict_from_pls_basis(
                values,
                coefficients=coefficients,
                effective_intercept=intercept,
            )
        except PlsRegressionError as exc:
            raise _error(exc.code, status.HTTP_409_CONFLICT) from exc
        output.append(
            PlsPointPredictionRow(
                client_row_id=row.client_row_id,
                predicted_value=prediction,
                warnings=sorted(set(warnings)),
            )
        )
    response = manifest.get("response")
    if not isinstance(response, dict) or not isinstance(response.get("column_id"), str):
        raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
    return PlsPointPredictionResponse(
        model_id=model_id,
        model_manifest_sha256=model.manifest_sha256,
        response_column_id=response["column_id"],
        row_count=len(output),
        intervals_supported=False,
        rows=output,
    )


def _predictors(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = manifest.get("predictors")
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, dict) for item in value)
    ):
        raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
    return value


def _prediction_basis(manifest: dict[str, Any]) -> dict[str, Any]:
    value = manifest.get("prediction_basis")
    if not isinstance(value, dict):
        raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
    order = value.get("predictor_order")
    coefficients = value.get("coefficients")
    intercept = value.get("effective_intercept")
    if not (
        isinstance(order, list)
        and all(isinstance(item, str) for item in order)
        and isinstance(coefficients, list)
        and len(coefficients) == len(order)
        and all(
            not isinstance(item, bool) and isinstance(item, int | float) and isfinite(float(item))
            for item in coefficients
        )
        and not isinstance(intercept, bool)
        and isinstance(intercept, int | float)
        and isfinite(float(intercept))
    ):
        raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
    return {
        "predictor_order": order,
        "coefficients": [float(item) for item in coefficients],
        "effective_intercept": float(intercept),
    }


def _training_ranges(
    manifest: dict[str, Any],
    expected_ids: list[str],
) -> dict[str, tuple[float, float]]:
    value = manifest.get("training_ranges")
    if not isinstance(value, list):
        raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
    ranges: dict[str, tuple[float, float]] = {}
    for item in value:
        if not isinstance(item, dict):
            raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
        column_id = item.get("column_id")
        lower = item.get("minimum")
        upper = item.get("maximum")
        if not (
            isinstance(column_id, str)
            and isinstance(lower, int | float)
            and not isinstance(lower, bool)
            and isinstance(upper, int | float)
            and not isinstance(upper, bool)
            and isfinite(float(lower))
            and isfinite(float(upper))
            and float(lower) <= float(upper)
        ):
            raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
        ranges[column_id] = (float(lower), float(upper))
    if set(ranges) != set(expected_ids):
        raise _error("pls_model_manifest_invalid", status.HTTP_409_CONFLICT)
    return ranges


def _error(code: str, status_code: int) -> ApiError:
    messages = {
        "pls_model_manifest_invalid": "저장된 PLS 모델 manifest를 검증할 수 없습니다.",
        "pls_model_manifest_checksum_mismatch": "PLS 모델 manifest가 요청 시점과 달라졌습니다.",
        "pls_prediction_model_stale": "PLS 모델 source가 변경되어 새 예측을 실행할 수 없습니다.",
        "pls_prediction_duplicate_row_id": "PLS 예측 입력 행 ID가 중복되었습니다.",
        "pls_prediction_predictor_mapping_invalid": "PLS 예측변수 입력이 모델과 일치하지 않습니다.",
        "pls_prediction_value_invalid": "PLS 예측값은 유한한 숫자여야 합니다.",
        "pls_prediction_failed": "PLS 점예측을 계산할 수 없습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "PLS 점예측을 완료할 수 없습니다."),
        status_code=status_code,
    )
