from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import numpy as np
from fastapi import status
from numpy.typing import NDArray
from pydantic import ValidationError

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisRunState,
    AnalysisWarning,
    GaussianProcessRegressionOptions,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    APP_VERSION,
    RowSnapshotArtifact,
    analysis_config_json,
    analysis_provenance,
    analysis_result_relative_path,
    atomic_write_bytes,
    canonical_json_bytes,
    create_row_snapshot_artifact,
    iter_rows_for_snapshot,
    remove_file_if_exists,
    utc_now,
)
from app.services.dataset_rows import DatasetRowsContext, get_dataset_rows_context
from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    GaussianProcessRegressionError,
    calculate_gaussian_process_regression,
)
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    DatasetColumnRecord,
    RegressionModelRecord,
    insert_analysis_run_record_with_artifacts_and_regression_model,
)

GP_MODEL_MANIFEST_SCHEMA_VERSION = 1
GP_MODEL_ARTIFACT_KIND = "regression_model_manifest"
GP_NUMERIC_ARTIFACT_KIND = "gaussian_process_model_numeric_state"
GP_MODEL_MEDIA_TYPE = "application/json"
GP_NUMERIC_MEDIA_TYPE = "application/x-npz"


def run_gaussian_process_regression_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Gaussian Process 회귀에는 데이터셋 버전이 필요합니다.",
        )
    options = _validate_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response, predictors = _selected_columns(context, options)
    analysis_id = uuid4()
    completed_at = utc_now()
    row_snapshot = create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    try:
        try:
            result = calculate_gaussian_process_regression(
                iter_rows_for_snapshot(context, row_snapshot),
                response,
                predictors,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                options=_statistics_options(options),
            )
        except GaussianProcessRegressionError as exc:
            raise _api_error(exc.code) from exc
        return _store_result_and_model(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_analysis_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_options(value: dict[str, Any]) -> GaussianProcessRegressionOptions:
    try:
        return GaussianProcessRegressionOptions.model_validate(value)
    except ValidationError as exc:
        raise ApiError(
            code="invalid_gaussian_process_options",
            message="Gaussian Process 회귀 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_columns(
    context: DatasetRowsContext,
    options: GaussianProcessRegressionOptions,
) -> tuple[GaussianProcessColumn, list[GaussianProcessColumn]]:
    by_id = {column.column_id: column for column in context.columns}
    response = by_id.get(options.response_column_id)
    if response is None:
        raise _api_error("gp_response_required")
    _validate_column(response, response=True)
    predictors: list[GaussianProcessColumn] = []
    for column_id in options.predictor_column_ids:
        column = by_id.get(column_id)
        if column is None:
            raise _api_error("gp_predictor_type_unsupported")
        _validate_column(column, response=False)
        predictors.append(_column(column))
    return _column(response), predictors


def _validate_column(column: DatasetColumnRecord, *, response: bool) -> None:
    if (
        column.data_type not in {"integer", "decimal"}
        or column.role == "id"
        or column.measurement_level == "nominal"
    ):
        raise _api_error(
            "gp_response_type_unsupported" if response else "gp_predictor_type_unsupported"
        )


def _column(column: DatasetColumnRecord) -> GaussianProcessColumn:
    return GaussianProcessColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _statistics_options(options: GaussianProcessRegressionOptions) -> GaussianProcessOptions:
    return GaussianProcessOptions(
        kernel_preset=options.kernel_preset,
        noise_mode=options.noise_mode,
        fixed_noise_standard_deviation=options.fixed_noise_standard_deviation,
        standardize_predictors=options.standardize_predictors,
        normalize_response=options.normalize_response,
        jitter=options.jitter,
        optimizer_restarts=options.optimizer_restarts,
        cv_optimizer_restarts=options.cv_optimizer_restarts,
        random_seed=options.cv.seed,
        validation_method=options.cv.method,
        cv_folds=options.cv.folds,
        cv_shuffle=options.cv.shuffle,
        plot_point_limit=options.plot_point_limit,
        profile_points=options.profile_points,
        surface_grid_size=options.surface_grid_size,
        time_budget_seconds=options.time_budget_seconds,
    )


def _store_result_and_model(
    *,
    settings: Settings,
    request: AnalysisRunRequest,
    context: DatasetRowsContext,
    analysis_id: UUID,
    completed_at: str,
    row_snapshot: RowSnapshotArtifact,
    result: dict[str, object],
    warnings: list[AnalysisWarning],
) -> AnalysisResultEnvelope:
    model_id = uuid4()
    directory = Path("workspaces") / "analyses" / str(analysis_id)
    manifest_relative_path = directory / f"model-{model_id}.json"
    numeric_relative_path = directory / f"model-{model_id}.npz"
    result_path: Path | None = None
    manifest_path: Path | None = None
    numeric_path: Path | None = None
    try:
        basis = _prediction_basis(result)
        arrays = _artifact_arrays(basis)
        numeric_bytes = _npz_bytes(arrays)
        numeric_sha256 = hashlib.sha256(numeric_bytes).hexdigest()
        numeric_path = settings.workspace_root / numeric_relative_path
        atomic_write_bytes(numeric_path, numeric_bytes)
        manifest = _manifest_payload(
            model_id=str(model_id),
            analysis_id=str(analysis_id),
            context=context,
            request=request,
            result=result,
            row_snapshot=row_snapshot,
            created_at=completed_at,
            basis=basis,
            numeric_relative_path=numeric_relative_path,
            numeric_sha256=numeric_sha256,
            arrays=arrays,
        )
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_path = settings.workspace_root / manifest_relative_path
        atomic_write_bytes(manifest_path, manifest_bytes)
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

        result_payload = dict(result)
        result_payload.pop("prediction_basis", None)
        result_payload["model_manifest"] = {
            "model_id": str(model_id),
            "manifest_schema_version": GP_MODEL_MANIFEST_SCHEMA_VERSION,
            "manifest_sha256": manifest_sha256,
        }
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=analysis_provenance(settings, request, context, row_snapshot),
            result=result_payload,
        )
        result_bytes = canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()
        artifacts = [
            row_snapshot.record,
            AnalysisArtifactRecord(
                artifact_id=str(uuid4()),
                analysis_id=str(analysis_id),
                kind=GP_MODEL_ARTIFACT_KIND,
                path=manifest_relative_path.as_posix(),
                sha256=manifest_sha256,
                media_type=GP_MODEL_MEDIA_TYPE,
                created_at=completed_at,
            ),
            AnalysisArtifactRecord(
                artifact_id=str(uuid4()),
                analysis_id=str(analysis_id),
                kind=GP_NUMERIC_ARTIFACT_KIND,
                path=numeric_relative_path.as_posix(),
                sha256=numeric_sha256,
                media_type=GP_NUMERIC_MEDIA_TYPE,
                created_at=completed_at,
            ),
        ]
        insert_analysis_run_record_with_artifacts_and_regression_model(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=artifacts,
            regression_model=RegressionModelRecord(
                model_id=str(model_id),
                analysis_id=str(analysis_id),
                dataset_version_id=str(request.dataset_version_id),
                method_id=request.method_id,
                method_version=request.method_version,
                manifest_path=manifest_relative_path.as_posix(),
                manifest_sha256=manifest_sha256,
                schema_hash=context.version.schema_hash,
                created_at=completed_at,
                app_version=APP_VERSION,
            ),
        )
        return envelope
    except Exception:
        for path in (result_path, manifest_path, numeric_path):
            if path is not None:
                remove_file_if_exists(path)
        raise


def _prediction_basis(result: dict[str, object]) -> dict[str, Any]:
    basis = result.get("prediction_basis")
    if not isinstance(basis, dict):
        raise _api_error("gp_fit_failed")
    return cast(dict[str, Any], basis)


def _artifact_arrays(basis: dict[str, Any]) -> dict[str, NDArray[np.float64]]:
    value = basis.get("artifact_arrays")
    if not isinstance(value, dict):
        raise _api_error("gp_fit_failed")
    expected = {
        "x_train_scaled",
        "cholesky",
        "dual_coefficients",
        "x_mean",
        "x_scale",
        "predictor_medians",
    }
    if set(value) != expected:
        raise _api_error("gp_fit_failed")
    arrays: dict[str, NDArray[np.float64]] = {}
    for name in sorted(expected):
        array = np.asarray(value[name], dtype=np.float64)
        if array.dtype.hasobject or not np.all(np.isfinite(array)):
            raise _api_error("gp_fit_failed")
        arrays[name] = array
    return arrays


def _npz_bytes(arrays: dict[str, NDArray[np.float64]]) -> bytes:
    stream = io.BytesIO()
    np.savez_compressed(stream, **cast(dict[str, Any], arrays))
    return stream.getvalue()


def _manifest_payload(
    *,
    model_id: str,
    analysis_id: str,
    context: DatasetRowsContext,
    request: AnalysisRunRequest,
    result: dict[str, object],
    row_snapshot: RowSnapshotArtifact,
    created_at: str,
    basis: dict[str, Any],
    numeric_relative_path: Path,
    numeric_sha256: str,
    arrays: dict[str, NDArray[np.float64]],
) -> dict[str, Any]:
    artifact = {
        "kind": GP_NUMERIC_ARTIFACT_KIND,
        "path": numeric_relative_path.as_posix(),
        "sha256": numeric_sha256,
        "media_type": GP_NUMERIC_MEDIA_TYPE,
        "arrays": {
            name: {"shape": list(array.shape), "dtype": str(array.dtype)}
            for name, array in arrays.items()
        },
    }
    return {
        "manifest_schema_version": GP_MODEL_MANIFEST_SCHEMA_VERSION,
        "manifest_kind": "gaussian_process_model_manifest",
        "model_id": model_id,
        "analysis_id": analysis_id,
        "model_family": "gaussian_process_regression",
        "method_id": request.method_id,
        "method_version": request.method_version,
        "app_version": APP_VERSION,
        "dataset_version_id": context.version.version_id,
        "source_schema_hash": context.version.schema_hash,
        "source_canonical_artifact_sha256": context.canonical_rows_artifact.sha256,
        "row_snapshot_sha256": row_snapshot.record.sha256,
        "created_at": created_at,
        "response": result["response"],
        "predictors": result["predictors"],
        "scaling": {
            "standardize_predictors": result["method"]["standardize_predictors"],  # type: ignore[index]
            "normalize_response": result["method"]["normalize_response"],  # type: ignore[index]
            "y_mean": basis["y_mean"],
            "y_scale": basis["y_scale"],
        },
        "kernel": result["kernel"],
        "noise_policy": {
            "mode": basis["noise_mode"],
            "jitter": basis["jitter"],
            "observation_noise_variance_scaled": basis["observation_noise_variance_scaled"],
        },
        "prediction_state": {
            "signal_kernel": basis["signal_kernel"],
            "numeric_artifact": artifact,
        },
        "training_ranges": result["training_ranges"],
        "model_summary": result["model_summary"],
        "package_versions": {
            "scikit-learn": result["method"]["engine_version"],  # type: ignore[index]
            "numpy": np.__version__,
        },
        "limitations": [
            "exact_gp_maximum_500_rows",
            "numeric_predictors_only",
            "single_response",
            "homoscedastic_observation_noise",
            "uncertainty_conditional_on_kernel",
            "predictive_not_causal",
        ],
    }


def _analysis_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    messages = {
        "gp_predictive_not_causal": (
            "Gaussian Process 예측 관계는 관찰 데이터만으로 인과 효과를 의미하지 않습니다."
        ),
        "gp_uncertainty_conditional_on_kernel": (
            "예측 불확실성은 선택한 kernel과 적합된 hyperparameter에 조건부입니다."
        ),
        "gp_not_converged": ("하나 이상의 Gaussian Process 적합이 안정적으로 수렴하지 않았습니다."),
        "gp_hyperparameter_near_bound": (
            "하나 이상의 kernel hyperparameter가 탐색 경계에 가깝습니다."
        ),
        "gp_amplitude_near_bound": "신호 amplitude가 탐색 경계에 가깝습니다.",
        "gp_length_scale_near_bound": ("하나 이상의 ARD length scale이 탐색 경계에 가깝습니다."),
        "gp_noise_level_near_bound": "추정 관측 noise가 탐색 경계에 가깝습니다.",
        "gp_negative_cv_r_squared": "교차검증 예측 R²가 음수입니다.",
        "gp_interval_undercoverage": "교차검증 95% 예측구간의 경험적 포함률이 낮습니다.",
        "gp_training_cv_gap": "학습 성능과 교차검증 성능 차이가 큽니다.",
        "missing_values_excluded": "결측 또는 비수치 행은 complete-case 정책으로 제외했습니다.",
    }
    info_codes = {"gp_predictive_not_causal", "gp_uncertainty_conditional_on_kernel"}
    codes = result.get("warnings")
    if not isinstance(codes, list):
        return []
    return [
        AnalysisWarning(
            code=code,
            severity="info" if code in info_codes else "warning",
            message=messages[code],
        )
        for code in codes
        if isinstance(code, str) and code in messages
    ]


def _api_error(code: str) -> ApiError:
    messages = {
        "gp_response_required": "Gaussian Process 반응 변수를 선택하세요.",
        "gp_predictor_required": "Gaussian Process 예측변수를 하나 이상 선택하세요.",
        "gp_predictor_type_unsupported": (
            "Gaussian Process P0 예측변수는 비명목 숫자형만 지원합니다."
        ),
        "gp_response_type_unsupported": (
            "Gaussian Process P0 반응 변수는 비명목 숫자형만 지원합니다."
        ),
        "gp_duplicate_predictor": "Gaussian Process 예측변수가 중복되었습니다.",
        "gp_response_in_predictors": "반응 변수를 예측변수로 동시에 사용할 수 없습니다.",
        "gp_usable_rows_too_few": "Gaussian Process 계산에 사용할 수 있는 완전한 행이 부족합니다.",
        "gp_usable_rows_limit": "정확 Gaussian Process의 500행 실행 상한을 초과했습니다.",
        "gp_predictor_count_limit": "Gaussian Process 예측변수 12개 상한을 초과했습니다.",
        "gp_constant_response": "Gaussian Process 반응 변수의 분산이 0입니다.",
        "gp_constant_predictor": "분산이 0인 Gaussian Process 예측변수가 있습니다.",
        "gp_kernel_policy_invalid": "Gaussian Process kernel 설정이 올바르지 않습니다.",
        "gp_noise_mode_invalid": "Gaussian Process noise 설정이 올바르지 않습니다.",
        "gp_noise_value_invalid": "고정 관측 noise 표준편차를 올바르게 입력하세요.",
        "gp_jitter_invalid": "Gaussian Process numerical jitter 범위가 올바르지 않습니다.",
        "gp_cv_fold_invalid": "Gaussian Process 교차검증 fold 설정이 올바르지 않습니다.",
        "gp_leave_one_out_limit": "Leave-One-Out은 200행 이하에서만 지원합니다.",
        "gp_fit_failed": "Gaussian Process 모형을 안정적으로 적합할 수 없습니다.",
        "gp_cross_validation_failed": "Gaussian Process 교차검증을 완료할 수 없습니다.",
        "gp_covariance_not_positive_definite": "공분산 행렬을 안정적으로 분해할 수 없습니다.",
        "gp_time_budget_exhausted": "Gaussian Process 계산 시간 예산을 초과했습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Gaussian Process 회귀를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )
