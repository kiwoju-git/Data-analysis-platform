from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisRunState,
    AnalysisWarning,
    PlsRegressionOptions,
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
from app.statistics.pls_regression import (
    PlsColumn,
    PlsOptions,
    PlsRegressionError,
    calculate_pls_regression,
)
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    DatasetColumnRecord,
    RegressionModelRecord,
    insert_analysis_run_record_with_artifacts_and_regression_model,
)

PLS_MODEL_MANIFEST_SCHEMA_VERSION = 1
PLS_MODEL_ARTIFACT_KIND = "regression_model_manifest"
PLS_MODEL_MEDIA_TYPE = "application/json"


def run_pls_regression_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="PLS 회귀에는 데이터셋 버전이 필요합니다.",
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
            result = calculate_pls_regression(
                iter_rows_for_snapshot(context, row_snapshot),
                response,
                predictors,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                options=_statistics_options(options),
            )
        except PlsRegressionError as exc:
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


def _validate_options(value: dict[str, Any]) -> PlsRegressionOptions:
    try:
        return PlsRegressionOptions.model_validate(value)
    except ValidationError as exc:
        raise ApiError(
            code="invalid_pls_options",
            message="PLS 회귀 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_columns(
    context: DatasetRowsContext,
    options: PlsRegressionOptions,
) -> tuple[PlsColumn, list[PlsColumn]]:
    by_id = {column.column_id: column for column in context.columns}
    response = by_id.get(options.response_column_id)
    if response is None:
        raise _api_error("pls_response_required")
    _validate_column(response, response=True)
    predictors: list[PlsColumn] = []
    for column_id in options.predictor_column_ids:
        column = by_id.get(column_id)
        if column is None:
            raise _api_error("pls_predictor_type_unsupported")
        _validate_column(column, response=False)
        predictors.append(_column(column))
    return _column(response), predictors


def _validate_column(column: DatasetColumnRecord, *, response: bool) -> None:
    if column.data_type not in {"integer", "decimal"} or column.role == "id":
        raise _api_error(
            "pls_response_type_unsupported" if response else "pls_predictor_type_unsupported"
        )


def _column(column: DatasetColumnRecord) -> PlsColumn:
    return PlsColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _statistics_options(options: PlsRegressionOptions) -> PlsOptions:
    return PlsOptions(
        scale=options.scale,
        component_selection=options.component_selection,
        n_components=options.n_components,
        max_components=options.max_components,
        cv_method=options.cv.method,
        cv_folds=options.cv.folds,
        cv_shuffle=options.cv.shuffle,
        cv_seed=options.cv.seed,
        max_iter=options.max_iter,
        tol=options.tol,
        plot_point_limit=options.plot_point_limit,
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
    result_path: Path | None = None
    manifest_path: Path | None = None
    manifest_relative_path = (
        Path("workspaces") / "analyses" / str(analysis_id) / f"model-{model_id}.json"
    )
    try:
        manifest = _manifest_payload(
            model_id=str(model_id),
            analysis_id=str(analysis_id),
            context=context,
            request=request,
            result=result,
            row_snapshot=row_snapshot,
            created_at=completed_at,
        )
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_path = settings.workspace_root / manifest_relative_path
        atomic_write_bytes(manifest_path, manifest_bytes)
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

        result_payload = dict(result)
        result_payload.pop("prediction_basis", None)
        result_payload["model_manifest"] = {
            "model_id": str(model_id),
            "manifest_schema_version": PLS_MODEL_MANIFEST_SCHEMA_VERSION,
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
        model_artifact = AnalysisArtifactRecord(
            artifact_id=str(uuid4()),
            analysis_id=str(analysis_id),
            kind=PLS_MODEL_ARTIFACT_KIND,
            path=manifest_relative_path.as_posix(),
            sha256=manifest_sha256,
            media_type=PLS_MODEL_MEDIA_TYPE,
            created_at=completed_at,
        )
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
            artifacts=[row_snapshot.record, model_artifact],
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
        if result_path is not None:
            remove_file_if_exists(result_path)
        if manifest_path is not None:
            remove_file_if_exists(manifest_path)
        raise


def _manifest_payload(
    *,
    model_id: str,
    analysis_id: str,
    context: DatasetRowsContext,
    request: AnalysisRunRequest,
    result: dict[str, object],
    row_snapshot: RowSnapshotArtifact,
    created_at: str,
) -> dict[str, Any]:
    basis = result.get("prediction_basis")
    if not isinstance(basis, dict):
        raise _api_error("pls_model_fit_failed")
    return {
        "manifest_schema_version": PLS_MODEL_MANIFEST_SCHEMA_VERSION,
        "manifest_kind": "pls_model_manifest",
        "model_id": model_id,
        "analysis_id": analysis_id,
        "model_family": "partial_least_squares_regression",
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
        "selected_components": result["model_summary"]["selected_components"],  # type: ignore[index]
        "scaling": {
            "enabled": basis["scale"],
            "x_mean": basis["x_mean"],
            "x_standard_deviation": basis["x_standard_deviation"],
            "y_mean": basis["y_mean"],
            "y_standard_deviation": basis["y_standard_deviation"],
        },
        "prediction_basis": {
            "predictor_order": basis["predictor_order"],
            "coefficients": basis["coefficients"],
            "effective_intercept": basis["effective_intercept"],
        },
        "training_ranges": result["training_ranges"],
        "model_selection": result["component_selection"],
        "model_summary": result["model_summary"],
        "coefficients": result["coefficients"],
        "latent_components": {
            key: result["latent_components"][key]  # type: ignore[index]
            for key in ("x_weights", "y_weights", "x_loadings", "y_loadings", "x_rotations")
        },
        "package_versions": {
            "scikit-learn": result["method"]["engine_version"],  # type: ignore[index]
        },
        "limitations": [
            "point_prediction_only",
            "no_classical_coefficient_p_values",
            "predictive_not_causal",
            "pls1_single_response",
        ],
    }


def _analysis_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    messages = {
        "pls_predictive_not_causal": (
            "PLS 예측 관계는 관찰 데이터만으로 인과 효과를 의미하지 않습니다."
        ),
        "pls_no_classical_coefficient_p_values": (
            "PLS 계수에는 OLS 방식의 p-value를 제공하지 않습니다."
        ),
        "pls_negative_predicted_r_squared": (
            "교차검증 예측 R²가 음수여서 평균 예측보다 성능이 낮습니다."
        ),
        "pls_selected_maximum_component": (
            "평가한 최대 성분 수가 선택되어 더 넓은 탐색이 필요할 수 있습니다."
        ),
        "pls_training_r_squared_much_higher_than_cv": (
            "학습 R²가 교차검증 예측 R²보다 크게 높습니다."
        ),
        "pls_model_not_converged": "일부 PLS 적합이 반복 한도 안에서 수렴하지 않았습니다.",
        "missing_values_excluded": "결측 또는 비수치 행은 complete-case 정책으로 제외했습니다.",
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "pls_predictive_not_causal": "info",
        "pls_no_classical_coefficient_p_values": "info",
    }
    codes = result.get("warnings")
    if not isinstance(codes, list):
        return []
    return [
        AnalysisWarning(
            code=code,
            severity=severities.get(code, "warning"),
            message=messages[code],
        )
        for code in codes
        if isinstance(code, str) and code in messages
    ]


def _api_error(code: str) -> ApiError:
    messages = {
        "pls_response_required": "PLS 반응 변수를 선택하세요.",
        "pls_predictors_too_few": "PLS 예측변수를 두 개 이상 선택하세요.",
        "pls_predictor_type_unsupported": "PLS P0 예측변수는 숫자형만 지원합니다.",
        "pls_response_type_unsupported": "PLS P0 반응 변수는 숫자형만 지원합니다.",
        "pls_usable_rows_too_few": "PLS 계산에 사용할 수 있는 완전한 행이 부족합니다.",
        "pls_usable_rows_limit": "PLS 계산 행 수가 현재 실행 예산을 초과합니다.",
        "pls_constant_response": "PLS 반응 변수의 분산이 0입니다.",
        "pls_constant_predictor": "분산이 0인 PLS 예측변수가 있습니다.",
        "pls_component_count_invalid": "PLS 성분 수가 현재 표본과 예측변수 범위에 맞지 않습니다.",
        "pls_cv_fold_count_invalid": "PLS 교차검증 fold 수가 올바르지 않습니다.",
        "pls_cv_group_invalid": "현재 PLS P0는 grouped CV를 지원하지 않습니다.",
        "pls_leave_one_out_limit": "Leave-One-Out 표본 수가 현재 실행 예산을 초과합니다.",
        "pls_model_fit_failed": "PLS 모형을 안정적으로 적합할 수 없습니다.",
        "pls_model_not_converged": "PLS 모형이 반복 한도 안에서 수렴하지 않았습니다.",
        "pls_cross_validation_failed": "PLS 교차검증을 완료할 수 없습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "PLS 회귀를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )
