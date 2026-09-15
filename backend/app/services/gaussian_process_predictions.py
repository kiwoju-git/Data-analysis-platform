from __future__ import annotations

import hashlib
import io
from math import isfinite
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from fastapi import status
from numpy.typing import NDArray

from app.api.v1.schemas.analyses import (
    GaussianProcessPointPredictionRequest,
    GaussianProcessPointPredictionResponse,
    GaussianProcessPointPredictionRow,
    GaussianProcessPredictionInterval,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import canonical_json_bytes
from app.services.dataset_rows import get_dataset_rows_context
from app.services.regression_models import get_regression_model_manifest
from app.statistics.gaussian_process_regression import (
    GaussianProcessRegressionError,
    build_gaussian_process_state,
    predict_from_gaussian_process_state,
)
from app.storage.metadata import get_analysis_run_record

EXPECTED_ARRAYS = {
    "x_train_scaled",
    "cholesky",
    "dual_coefficients",
    "x_mean",
    "x_scale",
    "predictor_medians",
}
NORMAL_975 = 1.959963984540054


def create_gaussian_process_point_predictions(
    settings: Settings,
    *,
    model_id: UUID,
    body: GaussianProcessPointPredictionRequest,
) -> GaussianProcessPointPredictionResponse:
    model = get_regression_model_manifest(settings, model_id)
    manifest = model.manifest
    if not (
        model.method_id == "regression.gaussian_process"
        and manifest.get("method_id") == "regression.gaussian_process"
        and manifest.get("model_family") == "gaussian_process_regression"
        and manifest.get("manifest_kind") == "gaussian_process_model_manifest"
        and manifest.get("manifest_schema_version") in {1, 2}
    ):
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    if body.expected_model_manifest_sha256 != model.manifest_sha256:
        raise _error("gp_model_manifest_checksum_mismatch", status.HTTP_409_CONFLICT)
    if manifest["manifest_schema_version"] == 2:
        selection = manifest.get("kernel_selection")
        summaries = manifest.get("candidate_summaries")
        if not (
            isinstance(selection, dict)
            and isinstance(summaries, list)
            and selection.get("selected_preset") == manifest.get("kernel", {}).get("preset")
            and hashlib.sha256(canonical_json_bytes({"candidates": summaries})).hexdigest()
            == manifest.get("candidate_summary_sha256")
        ):
            raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    source_run = get_analysis_run_record(settings.workspace_root, str(model.analysis_id))
    if source_run is None or source_run.stale or source_run.status != "succeeded":
        raise _error("gp_prediction_model_stale", status.HTTP_409_CONFLICT)
    source = get_dataset_rows_context(settings, model.dataset_version_id)
    if not (
        source.version.schema_hash == model.schema_hash
        and manifest.get("source_schema_hash") == model.schema_hash
        and manifest.get("source_canonical_artifact_sha256")
        == source.canonical_rows_artifact.sha256
    ):
        raise _error("gp_prediction_model_stale", status.HTTP_409_CONFLICT)

    predictors = _predictors(manifest)
    expected_ids = [str(item["column_id"]) for item in predictors]
    ranges = _training_ranges(manifest, expected_ids)
    state = _load_state(settings.workspace_root, manifest, len(expected_ids))
    client_ids = [row.client_row_id for row in body.rows]
    if len(set(client_ids)) != len(client_ids):
        raise _error("gp_prediction_input_invalid", status.HTTP_422_UNPROCESSABLE_ENTITY)

    matrix: list[list[float]] = []
    row_warnings: list[list[str]] = []
    for row in body.rows:
        if set(row.values) != set(expected_ids):
            raise _error("gp_prediction_input_invalid", status.HTTP_422_UNPROCESSABLE_ENTITY)
        values: list[float] = []
        warnings: list[str] = []
        for column_id in expected_ids:
            value = row.values[column_id]
            if isinstance(value, bool) or not isfinite(float(value)):
                raise _error("gp_prediction_input_invalid", status.HTTP_422_UNPROCESSABLE_ENTITY)
            numeric = float(value)
            values.append(numeric)
            lower, upper = ranges[column_id]
            if numeric < lower or numeric > upper:
                warnings.append("gp_extrapolation")
        matrix.append(values)
        row_warnings.append(sorted(set(warnings)))
    try:
        prediction = predict_from_gaussian_process_state(
            state,
            np.asarray(matrix, dtype=np.float64),
        )
    except GaussianProcessRegressionError as exc:
        raise _error(exc.code, status.HTTP_409_CONFLICT) from exc
    output: list[GaussianProcessPointPredictionRow] = []
    for index, row in enumerate(body.rows):
        mean = float(prediction["mean"][index])
        latent_std = float(prediction["latent_standard_deviation"][index])
        predictive_std = float(prediction["predictive_standard_deviation"][index])
        output.append(
            GaussianProcessPointPredictionRow(
                client_row_id=row.client_row_id,
                predicted_mean=mean,
                latent_standard_deviation=latent_std,
                latent_interval_95=_interval(mean, latent_std),
                predictive_standard_deviation=predictive_std,
                predictive_interval_95=_interval(mean, predictive_std),
                warnings=row_warnings[index],
            )
        )
    response = manifest.get("response")
    if not isinstance(response, dict) or not isinstance(response.get("column_id"), str):
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    return GaussianProcessPointPredictionResponse(
        model_id=model_id,
        model_manifest_sha256=model.manifest_sha256,
        response_column_id=response["column_id"],
        row_count=len(output),
        rows=output,
    )


def _load_state(
    workspace_root: Path,
    manifest: dict[str, Any],
    predictor_count: int,
) -> Any:
    prediction_state = manifest.get("prediction_state")
    scaling = manifest.get("scaling")
    noise = manifest.get("noise_policy")
    if not (
        isinstance(prediction_state, dict)
        and isinstance(scaling, dict)
        and isinstance(noise, dict)
        and isinstance(prediction_state.get("signal_kernel"), dict)
        and isinstance(prediction_state.get("numeric_artifact"), dict)
    ):
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    artifact = prediction_state["numeric_artifact"]
    arrays_metadata = artifact.get("arrays")
    if not isinstance(arrays_metadata, dict) or set(arrays_metadata) != EXPECTED_ARRAYS:
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    artifact_path = _safe_artifact_path(workspace_root, artifact.get("path"))
    try:
        artifact_bytes = artifact_path.read_bytes()
    except OSError as exc:
        raise _error("gp_model_artifact_missing", status.HTTP_409_CONFLICT) from exc
    expected_sha = artifact.get("sha256")
    if (
        not isinstance(expected_sha, str)
        or hashlib.sha256(artifact_bytes).hexdigest() != expected_sha
    ):
        raise _error("gp_model_artifact_checksum_mismatch", status.HTTP_409_CONFLICT)
    arrays = _load_arrays(artifact_bytes, arrays_metadata)
    _validate_array_shapes(arrays, predictor_count)
    y_mean = _finite(scaling.get("y_mean"))
    y_scale = _finite(scaling.get("y_scale"), positive=True)
    observation_noise = _finite(noise.get("observation_noise_variance_scaled"), nonnegative=True)
    try:
        return build_gaussian_process_state(
            x_train_scaled=arrays["x_train_scaled"],
            cholesky=arrays["cholesky"],
            dual_coefficients=arrays["dual_coefficients"],
            x_mean=arrays["x_mean"],
            x_scale=arrays["x_scale"],
            y_mean=y_mean,
            y_scale=y_scale,
            predictor_medians=arrays["predictor_medians"],
            signal_kernel_payload=prediction_state["signal_kernel"],
            observation_noise_variance_scaled=observation_noise,
        )
    except GaussianProcessRegressionError as exc:
        raise _error("gp_model_artifact_invalid", status.HTTP_409_CONFLICT) from exc


def _safe_artifact_path(workspace_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    root = workspace_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT) from exc
    return candidate


def _load_arrays(
    artifact_bytes: bytes,
    metadata: dict[str, Any],
) -> dict[str, NDArray[np.float64]]:
    try:
        with np.load(io.BytesIO(artifact_bytes), allow_pickle=False) as loaded:
            if set(loaded.files) != EXPECTED_ARRAYS:
                raise ValueError("array names")
            arrays: dict[str, NDArray[np.float64]] = {}
            for name in sorted(EXPECTED_ARRAYS):
                array = loaded[name]
                expected = metadata.get(name)
                if not isinstance(expected, dict):
                    raise ValueError("array metadata")
                if (
                    array.dtype.hasobject
                    or str(array.dtype) != expected.get("dtype")
                    or list(array.shape) != expected.get("shape")
                    or not np.issubdtype(array.dtype, np.floating)
                    or not np.all(np.isfinite(array))
                ):
                    raise ValueError("array contract")
                arrays[name] = np.asarray(array, dtype=np.float64)
            return arrays
    except (OSError, ValueError) as exc:
        raise _error("gp_model_artifact_invalid", status.HTTP_409_CONFLICT) from exc


def _validate_array_shapes(
    arrays: dict[str, NDArray[np.float64]],
    predictor_count: int,
) -> None:
    x = arrays["x_train_scaled"]
    cholesky = arrays["cholesky"]
    alpha = arrays["dual_coefficients"]
    if (
        x.ndim != 2
        or x.shape[1] != predictor_count
        or cholesky.shape != (x.shape[0], x.shape[0])
        or alpha.shape != (x.shape[0],)
        or arrays["x_mean"].shape != (predictor_count,)
        or arrays["x_scale"].shape != (predictor_count,)
        or arrays["predictor_medians"].shape != (predictor_count,)
        or np.any(arrays["x_scale"] <= 0.0)
    ):
        raise _error("gp_model_artifact_invalid", status.HTTP_409_CONFLICT)


def _predictors(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = manifest.get("predictors")
    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, dict) or not isinstance(item.get("column_id"), str)
            for item in value
        )
    ):
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    return value


def _training_ranges(
    manifest: dict[str, Any],
    expected_ids: list[str],
) -> dict[str, tuple[float, float]]:
    value = manifest.get("training_ranges")
    if not isinstance(value, list):
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    ranges: dict[str, tuple[float, float]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("column_id"), str):
            raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
        lower = _finite(item.get("minimum"))
        upper = _finite(item.get("maximum"))
        if lower > upper:
            raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
        ranges[item["column_id"]] = (lower, upper)
    if set(ranges) != set(expected_ids):
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    return ranges


def _finite(value: object, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not isfinite(float(value)):
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    number = float(value)
    if (positive and number <= 0.0) or (nonnegative and number < 0.0):
        raise _error("gp_model_manifest_invalid", status.HTTP_409_CONFLICT)
    return number


def _interval(mean: float, standard_deviation: float) -> GaussianProcessPredictionInterval:
    half_width = NORMAL_975 * standard_deviation
    return GaussianProcessPredictionInterval(
        lower=mean - half_width,
        upper=mean + half_width,
    )


def _error(code: str, status_code: int) -> ApiError:
    messages = {
        "gp_model_manifest_invalid": "저장된 Gaussian Process 모델 manifest를 검증할 수 없습니다.",
        "gp_model_manifest_checksum_mismatch": (
            "Gaussian Process 모델 manifest가 요청 시점과 달라졌습니다."
        ),
        "gp_model_artifact_missing": "Gaussian Process 숫자 모델 artifact를 찾을 수 없습니다.",
        "gp_model_artifact_invalid": (
            "Gaussian Process 숫자 모델 artifact 계약이 올바르지 않습니다."
        ),
        "gp_model_artifact_checksum_mismatch": (
            "Gaussian Process 숫자 모델 artifact checksum이 일치하지 않습니다."
        ),
        "gp_prediction_model_stale": "Gaussian Process 모델 source가 변경되어 예측할 수 없습니다.",
        "gp_prediction_input_invalid": (
            "Gaussian Process 예측 입력이 모델 predictor 계약과 일치하지 않습니다."
        ),
        "gp_prediction_failed": "Gaussian Process 예측을 계산할 수 없습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Gaussian Process 예측을 완료할 수 없습니다."),
        status_code=status_code,
    )
