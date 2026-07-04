import hashlib
from collections.abc import Sequence
from math import isfinite
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
    LinearModelOptions,
    PearsonOptions,
    XyCorrelationOptions,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    APP_VERSION,
    NUMERIC_DATA_TYPES,
)
from app.services.analysis_run_execution import (
    RowSnapshotArtifact as _RowSnapshotArtifact,
)
from app.services.analysis_run_execution import (
    analysis_config_json as _analysis_config_json,
)
from app.services.analysis_run_execution import (
    analysis_provenance as _analysis_provenance,
)
from app.services.analysis_run_execution import (
    analysis_result_relative_path as _analysis_result_relative_path,
)
from app.services.analysis_run_execution import (
    canonical_json_bytes as _canonical_json_bytes,
)
from app.services.analysis_run_execution import (
    create_row_snapshot_artifact as _create_row_snapshot_artifact,
)
from app.services.analysis_run_execution import (
    iter_rows_for_snapshot as _iter_rows_for_snapshot,
)
from app.services.analysis_run_execution import (
    remove_file_if_exists as _remove_file_if_exists,
)
from app.services.analysis_run_execution import (
    store_succeeded_analysis_result as _store_succeeded_analysis_result,
)
from app.services.analysis_run_execution import (
    utc_now as _utc_now,
)
from app.services.dataset_rows import DatasetRowsContext, get_dataset_rows_context
from app.statistics.linear_model import (
    LinearModelColumn,
    LinearModelError,
    calculate_linear_model,
)
from app.statistics.pearson import (
    PearsonCorrelationColumn,
    PearsonCorrelationError,
    calculate_pearson_correlation,
)
from app.statistics.xy_correlation import (
    XyCorrelationColumn,
    XyCorrelationError,
    calculate_xy_correlation,
)
from app.storage.atomic import atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    DatasetColumnRecord,
    RegressionModelRecord,
    insert_analysis_run_record_with_artifacts_and_regression_model,
)

REGRESSION_MODEL_MANIFEST_SCHEMA_VERSION = 2
REGRESSION_MODEL_ARTIFACT_KIND = "regression_model_manifest"
REGRESSION_MODEL_MEDIA_TYPE = "application/json"
MAX_LINEAR_MODEL_PREDICTORS = 20
MAX_XY_CORRELATION_X_COLUMNS = 20
MAX_XY_CORRELATION_Y_COLUMNS = 20


def run_pearson_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Pearson 상관 분석 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_pearson_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    x_column, y_column = _selected_pearson_columns(context, options)
    alpha = _pearson_alpha(options)
    confidence_level = _pearson_confidence_level(options)
    _pearson_missing_policy(options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    try:
        try:
            result = calculate_pearson_correlation(
                _iter_rows_for_snapshot(context, row_snapshot),
                x_column,
                y_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
            )
        except PearsonCorrelationError as exc:
            raise _pearson_api_error(exc.code) from exc
        warnings = _pearson_warnings(result)
        return _store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=warnings,
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_pearson_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return PearsonOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_pearson_options",
            message="Pearson 상관 분석 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_pearson_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[PearsonCorrelationColumn, PearsonCorrelationColumn]:
    x_column_id = options.get("x_column_id")
    y_column_id = options.get("y_column_id")
    if not isinstance(x_column_id, str) or not x_column_id:
        raise ApiError(
            code="pearson_x_column_required",
            message="Pearson 상관 분석 X 컬럼을 선택해야 합니다.",
        )
    if not isinstance(y_column_id, str) or not y_column_id:
        raise ApiError(
            code="pearson_y_column_required",
            message="Pearson 상관 분석 Y 컬럼을 선택해야 합니다.",
        )
    if x_column_id == y_column_id:
        raise ApiError(
            code="pearson_same_x_and_y_column",
            message="Pearson 상관 분석 X/Y 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    x_column = columns_by_id.get(x_column_id)
    y_column = columns_by_id.get(y_column_id)
    if x_column is None:
        raise ApiError(
            code="pearson_x_column_not_found",
            message="요청한 Pearson 상관 분석 X 컬럼을 찾을 수 없습니다.",
        )
    if y_column is None:
        raise ApiError(
            code="pearson_y_column_not_found",
            message="요청한 Pearson 상관 분석 Y 컬럼을 찾을 수 없습니다.",
        )
    _validate_pearson_column(x_column, axis="x")
    _validate_pearson_column(y_column, axis="y")
    return (
        PearsonCorrelationColumn(
            column_id=x_column.column_id,
            column_index=x_column.column_index,
            display_name=x_column.display_name,
            data_type=x_column.data_type,
            measurement_level=x_column.measurement_level,
            role=x_column.role,
            unit=x_column.unit,
        ),
        PearsonCorrelationColumn(
            column_id=y_column.column_id,
            column_index=y_column.column_index,
            display_name=y_column.display_name,
            data_type=y_column.data_type,
            measurement_level=y_column.measurement_level,
            role=y_column.role,
            unit=y_column.unit,
        ),
    )


def _validate_pearson_column(
    column: DatasetColumnRecord,
    *,
    axis: str,
) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"pearson_{axis}_column_is_id",
            message="ID 컬럼은 Pearson 상관 분석 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"pearson_{axis}_column_not_numeric",
            message="Pearson 상관 분석 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _pearson_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_pearson_alpha",
            message="Pearson 상관 분석 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_pearson_alpha",
            message="Pearson 상관 분석 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _pearson_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_pearson_confidence_level",
            message="Pearson 상관 분석 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_pearson_confidence_level",
            message="Pearson 상관 분석 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _pearson_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="pearson_missing_policy_unsupported",
            message="Pearson 상관 분석은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _pearson_api_error(code: str) -> ApiError:
    messages = {
        "invalid_pearson_alpha": "Pearson 상관 분석 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_pearson_confidence_level": (
            "Pearson 상관 분석 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "pearson_n_too_small": "Pearson 상관 분석에는 complete-case 수치 쌍이 최소 4개 필요합니다.",
        "pearson_x_constant": "X 컬럼의 사용 값이 모두 같아 Pearson 상관을 계산할 수 없습니다.",
        "pearson_y_constant": "Y 컬럼의 사용 값이 모두 같아 Pearson 상관을 계산할 수 없습니다.",
        "pearson_result_not_finite": "Pearson 상관 분석 결과가 유한하지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Pearson 상관 분석을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _pearson_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "pearson_correlation_not_causation" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_correlation_not_causation",
                severity="info",
                message="상관은 인과를 의미하지 않습니다. 설계와 도메인 근거를 별도로 확인하세요.",
            ),
        )
    if "pearson_linear_relationship_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_linear_relationship_assumption",
                severity="info",
                message=(
                    "Pearson 상관은 선형 관계 요약입니다. 비선형 패턴은 별도 진단이 " "필요합니다."
                ),
            ),
        )
    if "pearson_outlier_sensitive" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_outlier_sensitive",
                severity="info",
                message=(
                    "Pearson 상관은 이상값에 민감합니다. 산점도와 영향점 후보를 함께 " "확인하세요."
                ),
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="X 또는 Y 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="X 또는 Y 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "pearson_perfect_sample_correlation_ci_unavailable" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_perfect_sample_correlation_ci_unavailable",
                severity="warning",
                message="표본 상관이 완전하여 Fisher z 신뢰구간을 계산하지 않았습니다.",
            ),
        )
    return warnings


def run_xy_correlation_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="X-Y 상관행렬 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_xy_correlation_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    x_columns, y_columns = _selected_xy_correlation_columns(context, options)
    alpha = _xy_correlation_alpha(options)
    confidence_level = _xy_correlation_confidence_level(options)
    _xy_correlation_missing_policy(options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    try:
        try:
            result = calculate_xy_correlation(
                _iter_rows_for_snapshot(context, row_snapshot),
                x_columns,
                y_columns,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
            )
        except XyCorrelationError as exc:
            raise _xy_correlation_api_error(exc.code) from exc
        warnings = _xy_correlation_warnings(result)
        return _store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=warnings,
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_xy_correlation_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return XyCorrelationOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_xy_correlation_options",
            message="X-Y 상관행렬 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_xy_correlation_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[list[XyCorrelationColumn], list[XyCorrelationColumn]]:
    x_column_ids = _column_id_list(
        options.get("x_column_ids"),
        required_code="xy_correlation_x_columns_required",
        invalid_code="invalid_xy_correlation_x_columns",
        duplicate_code="duplicate_xy_correlation_x_column",
        max_count=MAX_XY_CORRELATION_X_COLUMNS,
        too_many_code="too_many_xy_correlation_x_columns",
    )
    y_column_ids = _column_id_list(
        options.get("y_column_ids"),
        required_code="xy_correlation_y_columns_required",
        invalid_code="invalid_xy_correlation_y_columns",
        duplicate_code="duplicate_xy_correlation_y_column",
        max_count=MAX_XY_CORRELATION_Y_COLUMNS,
        too_many_code="too_many_xy_correlation_y_columns",
    )

    columns_by_id = {column.column_id: column for column in context.columns}
    x_columns = [
        _xy_correlation_column(
            columns_by_id,
            column_id,
            axis="x",
        )
        for column_id in x_column_ids
    ]
    y_columns = [
        _xy_correlation_column(
            columns_by_id,
            column_id,
            axis="y",
        )
        for column_id in y_column_ids
    ]
    return (x_columns, y_columns)


def _column_id_list(
    value: object,
    *,
    required_code: str,
    invalid_code: str,
    duplicate_code: str,
    max_count: int,
    too_many_code: str,
) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ApiError(
            code=required_code,
            message="분석에 사용할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(value) > max_count:
        raise ApiError(
            code=too_many_code,
            message="한 번에 요청한 X-Y 상관행렬 컬럼 수가 허용 범위를 초과했습니다.",
        )

    column_ids: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item:
            raise ApiError(
                code=invalid_code,
                message="컬럼 ID 목록이 올바르지 않습니다.",
            )
        if item in seen:
            raise ApiError(
                code=duplicate_code,
                message="컬럼 ID가 중복되었습니다.",
            )
        seen.add(item)
        column_ids.append(item)
    return column_ids


def _xy_correlation_column(
    columns_by_id: dict[str, DatasetColumnRecord],
    column_id: str,
    *,
    axis: str,
) -> XyCorrelationColumn:
    column = columns_by_id.get(column_id)
    if column is None:
        raise ApiError(
            code=f"xy_correlation_{axis}_column_not_found",
            message="요청한 X-Y 상관행렬 컬럼을 찾을 수 없습니다.",
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"xy_correlation_{axis}_column_is_id",
            message="ID 컬럼은 X-Y 상관행렬 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"xy_correlation_{axis}_column_not_numeric",
            message="X-Y 상관행렬 변수는 현재 숫자형 컬럼만 지원합니다.",
        )
    return XyCorrelationColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _xy_correlation_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_xy_correlation_alpha",
            message="X-Y 상관행렬 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_xy_correlation_alpha",
            message="X-Y 상관행렬 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _xy_correlation_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_xy_correlation_confidence_level",
            message="X-Y 상관행렬 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_xy_correlation_confidence_level",
            message="X-Y 상관행렬 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _xy_correlation_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "pairwise_complete_case")
    if raw_value != "pairwise_complete_case":
        raise ApiError(
            code="xy_correlation_missing_policy_unsupported",
            message="X-Y 상관행렬은 현재 pairwise complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _xy_correlation_api_error(code: str) -> ApiError:
    messages = {
        "invalid_xy_correlation_alpha": "X-Y 상관행렬 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_xy_correlation_confidence_level": (
            "X-Y 상관행렬 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "xy_correlation_columns_required": "X-Y 상관행렬에는 X/Y 컬럼이 필요합니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "X-Y 상관행렬을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _xy_correlation_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "xy_correlation_not_causation": (
            "상관은 인과를 의미하지 않습니다. 설계와 도메인 근거를 별도로 확인하세요."
        ),
        "xy_correlation_linear_relationship_assumption": (
            "Pearson 상관은 선형 관계 요약입니다. 비선형 패턴은 별도 진단이 필요합니다."
        ),
        "xy_correlation_outlier_sensitive": (
            "Pearson 상관은 이상값에 민감합니다. 산점도와 영향점 후보를 함께 확인하세요."
        ),
        "xy_correlation_pair_failed": (
            "일부 X/Y 조합은 표본 부족, 상수열, 비유한 결과 때문에 r/p 값을 만들지 않았습니다."
        ),
        "xy_correlation_pairwise_n_varies": (
            "pairwise complete-case 처리로 X/Y 조합마다 사용 N이 다를 수 있습니다."
        ),
        "xy_correlation_overlapping_x_y_columns": (
            "X 변수 집합과 Y 변수 집합에 같은 컬럼이 포함되어 자기상관 셀이 생길 수 있습니다."
        ),
        "missing_values_excluded": "결측 행은 해당 X/Y 조합에서 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 값은 해당 X/Y 조합에서 제외했습니다.",
        "xy_correlation_perfect_sample_correlation_ci_unavailable": (
            "표본 상관이 완전한 셀은 Fisher z 신뢰구간을 계산하지 않았습니다."
        ),
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "xy_correlation_not_causation": "info",
        "xy_correlation_linear_relationship_assumption": "info",
        "xy_correlation_outlier_sensitive": "info",
        "xy_correlation_overlapping_x_y_columns": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        severity: Literal["info", "warning", "error"] = severities.get(code, "warning")
        warnings.append(
            AnalysisWarning(
                code=code,
                severity=severity,
                message=message,
            ),
        )
    return warnings


def run_linear_model_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="회귀모형 적합에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_linear_model_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, predictor_columns = _selected_linear_model_columns(context, options)
    alpha = _linear_model_alpha(options)
    confidence_level = _linear_model_confidence_level(options)
    quadratic_terms = _linear_model_quadratic_terms(options, predictor_columns)
    interaction_terms = _linear_model_interaction_terms(options, predictor_columns)
    _linear_model_missing_policy(options)
    _linear_model_include_intercept(options)
    _linear_model_covariance_type(options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    try:
        try:
            result = calculate_linear_model(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                predictor_columns,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                quadratic_terms=quadratic_terms,
                interaction_terms=interaction_terms,
            )
        except LinearModelError as exc:
            raise _linear_model_api_error(exc.code) from exc
        warnings = _linear_model_warnings(result)
        return _store_succeeded_linear_model_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=warnings,
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_linear_model_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return LinearModelOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_linear_model_options",
            message="회귀모형 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _store_succeeded_linear_model_result(
    *,
    settings: Settings,
    request: AnalysisRunRequest,
    context: DatasetRowsContext,
    analysis_id: UUID,
    completed_at: str,
    row_snapshot: _RowSnapshotArtifact,
    result: dict[str, object],
    warnings: list[AnalysisWarning],
) -> AnalysisResultEnvelope:
    result_path: Path | None = None
    manifest_path: Path | None = None
    model_id = uuid4()
    manifest_relative_path = _regression_model_manifest_relative_path(
        str(analysis_id),
        str(model_id),
    )

    try:
        manifest_payload = _linear_model_manifest_payload(
            model_id=str(model_id),
            analysis_id=str(analysis_id),
            context=context,
            request=request,
            result=result,
            row_snapshot=row_snapshot,
            created_at=completed_at,
        )
        manifest_bytes = _canonical_json_bytes(manifest_payload)
        manifest_path = settings.workspace_root / manifest_relative_path
        atomic_write_bytes(manifest_path, manifest_bytes)
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        result_payload = dict(result)
        result_payload.pop("prediction_basis", None)
        result_payload["model_manifest"] = {
            "model_id": str(model_id),
            "manifest_schema_version": REGRESSION_MODEL_MANIFEST_SCHEMA_VERSION,
            "manifest_sha256": manifest_sha256,
        }
        provenance = _analysis_provenance(settings, request, context, row_snapshot)
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result_payload,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        model_artifact = AnalysisArtifactRecord(
            artifact_id=str(uuid4()),
            analysis_id=str(analysis_id),
            kind=REGRESSION_MODEL_ARTIFACT_KIND,
            path=manifest_relative_path.as_posix(),
            sha256=manifest_sha256,
            media_type=REGRESSION_MODEL_MEDIA_TYPE,
            created_at=completed_at,
        )
        insert_analysis_run_record_with_artifacts_and_regression_model(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
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
    except Exception:
        if manifest_path is not None:
            _remove_file_if_exists(manifest_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_linear_model_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[LinearModelColumn, list[LinearModelColumn]]:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="linear_model_response_column_required",
            message="회귀모형 반응 컬럼을 선택해야 합니다.",
        )
    predictor_column_ids = _linear_model_predictor_ids(options.get("predictor_column_ids"))
    if response_column_id in predictor_column_ids:
        raise ApiError(
            code="linear_model_response_predictor_overlap",
            message="회귀모형 반응 컬럼은 예측변수에 동시에 포함할 수 없습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_record = columns_by_id.get(response_column_id)
    if response_record is None:
        raise ApiError(
            code="linear_model_response_column_not_found",
            message="요청한 회귀모형 반응 컬럼을 찾을 수 없습니다.",
        )
    _validate_linear_model_column(response_record, role="response")

    predictor_columns: list[LinearModelColumn] = []
    for predictor_column_id in predictor_column_ids:
        predictor_record = columns_by_id.get(predictor_column_id)
        if predictor_record is None:
            raise ApiError(
                code="linear_model_predictor_column_not_found",
                message="요청한 회귀모형 예측 컬럼을 찾을 수 없습니다.",
            )
        _validate_linear_model_column(predictor_record, role="predictor")
        predictor_columns.append(_linear_model_column(predictor_record))

    return (_linear_model_column(response_record), predictor_columns)


def _linear_model_predictor_ids(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ApiError(
            code="linear_model_predictors_required",
            message="회귀모형 예측 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(value) > MAX_LINEAR_MODEL_PREDICTORS:
        raise ApiError(
            code="too_many_linear_model_predictors",
            message="한 번에 요청한 회귀모형 예측 컬럼 수가 허용 범위를 초과했습니다.",
        )

    predictor_ids: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item:
            raise ApiError(
                code="invalid_linear_model_predictors",
                message="회귀모형 예측 컬럼 ID 목록이 올바르지 않습니다.",
            )
        if item in seen:
            raise ApiError(
                code="duplicate_linear_model_predictor",
                message="회귀모형 예측 컬럼 ID가 중복되었습니다.",
            )
        seen.add(item)
        predictor_ids.append(item)
    return predictor_ids


def _validate_linear_model_column(
    column: DatasetColumnRecord,
    *,
    role: str,
) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"linear_model_{role}_column_is_id",
            message="ID 컬럼은 회귀모형 변수로 사용할 수 없습니다.",
        )
    if role == "response" and column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"linear_model_{role}_column_not_numeric",
            message="회귀모형 반응 변수는 숫자형 컬럼이어야 합니다.",
        )
    if role == "predictor" and not _linear_model_predictor_supported(column):
        raise ApiError(
            code="linear_model_predictor_column_unsupported_type",
            message="회귀모형 예측변수는 숫자형 또는 범주형 factor 컬럼만 지원합니다.",
        )


def _linear_model_predictor_supported(column: DatasetColumnRecord) -> bool:
    if column.data_type in NUMERIC_DATA_TYPES and column.measurement_level not in {
        "nominal",
        "binary",
        "ordinal",
    }:
        return column.role != "factor"
    return column.data_type != "datetime" and (
        column.data_type in {"text", "boolean"}
        or column.measurement_level in {"nominal", "binary", "ordinal"}
        or column.role == "factor"
    )


def _linear_model_column(column: DatasetColumnRecord) -> LinearModelColumn:
    return LinearModelColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _linear_model_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_linear_model_alpha",
            message="회귀모형 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_linear_model_alpha",
            message="회귀모형 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _linear_model_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_linear_model_confidence_level",
            message="회귀모형 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_linear_model_confidence_level",
            message="회귀모형 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _linear_model_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="linear_model_missing_policy_unsupported",
            message="회귀모형은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _linear_model_include_intercept(options: dict[str, Any]) -> bool:
    raw_value = options.get("include_intercept", True)
    if raw_value is not True:
        raise ApiError(
            code="linear_model_no_intercept_unsupported",
            message="이번 회귀모형 slice는 intercept 포함 OLS만 지원합니다.",
        )
    return True


def _linear_model_covariance_type(options: dict[str, Any]) -> str:
    raw_value = options.get("covariance_type", "standard")
    if raw_value != "standard":
        raise ApiError(
            code="linear_model_covariance_type_unsupported",
            message="이번 회귀모형 slice는 standard covariance만 지원합니다.",
        )
    return raw_value


def _linear_model_quadratic_terms(
    options: dict[str, Any],
    predictor_columns: Sequence[LinearModelColumn],
) -> list[str]:
    raw_value = options.get("quadratic_terms", [])
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise ApiError(
            code="invalid_linear_model_quadratic_terms",
            message="회귀모형 2차항 목록이 올바르지 않습니다.",
        )
    selected_columns = {column.column_id: column for column in predictor_columns}
    terms: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        if not isinstance(item, str) or not item:
            raise ApiError(
                code="invalid_linear_model_quadratic_terms",
                message="회귀모형 2차항 목록이 올바르지 않습니다.",
            )
        if item in seen:
            raise ApiError(
                code="duplicate_linear_model_quadratic_term",
                message="회귀모형 2차항이 중복되었습니다.",
            )
        column = selected_columns.get(item)
        if column is None:
            raise ApiError(
                code="linear_model_term_predictor_not_selected",
                message="2차항은 선택된 예측변수에서만 만들 수 있습니다.",
            )
        if not _linear_model_numeric_predictor(column):
            raise ApiError(
                code="linear_model_term_requires_numeric_predictor",
                message="2차항은 숫자형 예측변수에서만 만들 수 있습니다.",
            )
        seen.add(item)
        terms.append(item)
    return terms


def _linear_model_interaction_terms(
    options: dict[str, Any],
    predictor_columns: Sequence[LinearModelColumn],
) -> list[tuple[str, str]]:
    raw_value = options.get("interaction_terms", [])
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise ApiError(
            code="invalid_linear_model_interaction_terms",
            message="회귀모형 상호작용 항 목록이 올바르지 않습니다.",
        )
    selected_columns = {column.column_id: column for column in predictor_columns}
    predictor_order = {column.column_id: index for index, column in enumerate(predictor_columns)}
    terms: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in raw_value:
        if not isinstance(item, dict):
            raise ApiError(
                code="invalid_linear_model_interaction_terms",
                message="회귀모형 상호작용 항 목록이 올바르지 않습니다.",
            )
        left_column_id = item.get("left_column_id")
        right_column_id = item.get("right_column_id")
        if (
            not isinstance(left_column_id, str)
            or not left_column_id
            or not isinstance(right_column_id, str)
            or not right_column_id
        ):
            raise ApiError(
                code="invalid_linear_model_interaction_terms",
                message="회귀모형 상호작용 항 목록이 올바르지 않습니다.",
            )
        if left_column_id == right_column_id:
            raise ApiError(
                code="linear_model_interaction_same_predictor",
                message="상호작용 항은 서로 다른 두 예측변수로만 만들 수 있습니다.",
            )
        seen_key = tuple(sorted((left_column_id, right_column_id)))
        if len(seen_key) != 2:
            raise ApiError(
                code="invalid_linear_model_interaction_terms",
                message="회귀모형 상호작용 항 목록이 올바르지 않습니다.",
            )
        typed_seen_key = (seen_key[0], seen_key[1])
        if typed_seen_key in seen:
            raise ApiError(
                code="duplicate_linear_model_interaction_term",
                message="회귀모형 상호작용 항이 중복되었습니다.",
            )
        if predictor_order.get(left_column_id, 10**9) <= predictor_order.get(
            right_column_id,
            10**9,
        ):
            ordered = (left_column_id, right_column_id)
        else:
            ordered = (right_column_id, left_column_id)
        left_column = selected_columns.get(ordered[0])
        right_column = selected_columns.get(ordered[1])
        if left_column is None or right_column is None:
            raise ApiError(
                code="linear_model_term_predictor_not_selected",
                message="상호작용 항은 선택된 예측변수에서만 만들 수 있습니다.",
            )
        if not _linear_model_numeric_predictor(left_column) or not _linear_model_numeric_predictor(
            right_column,
        ):
            raise ApiError(
                code="linear_model_term_requires_numeric_predictor",
                message="이번 slice의 상호작용 항은 숫자형 예측변수끼리만 지원합니다.",
            )
        seen.add(typed_seen_key)
        terms.append((ordered[0], ordered[1]))
    return terms


def _linear_model_numeric_predictor(column: LinearModelColumn) -> bool:
    return (
        column.data_type in NUMERIC_DATA_TYPES
        and column.measurement_level not in {"nominal", "binary", "ordinal"}
        and column.role != "factor"
    )


def _linear_model_api_error(code: str) -> ApiError:
    messages = {
        "invalid_linear_model_options": "회귀모형 옵션 계약이 올바르지 않습니다.",
        "invalid_linear_model_alpha": "회귀모형 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_linear_model_confidence_level": "회귀모형 신뢰수준이 허용 범위를 벗어났습니다.",
        "linear_model_predictors_required": "회귀모형 예측 컬럼을 하나 이상 선택해야 합니다.",
        "linear_model_residual_df_too_small": (
            "회귀모형에는 예측변수 수보다 충분히 많은 complete-case 행이 필요합니다."
        ),
        "linear_model_response_constant": (
            "반응 컬럼의 사용 값이 모두 같아 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_predictor_constant": (
            "예측 컬럼 중 사용 값이 모두 같은 컬럼이 있어 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_factor_single_level": (
            "사용 가능한 범주형 예측변수에 수준이 하나만 남아 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_factor_too_many_levels": (
            "범주형 예측변수 수준 수가 현재 회귀모형 slice의 허용 범위를 초과했습니다."
        ),
        "linear_model_predictor_column_unsupported_type": (
            "회귀모형 예측변수는 숫자형 또는 범주형 factor 컬럼만 지원합니다."
        ),
        "invalid_linear_model_quadratic_terms": "회귀모형 2차항 목록이 올바르지 않습니다.",
        "duplicate_linear_model_quadratic_term": "회귀모형 2차항이 중복되었습니다.",
        "invalid_linear_model_interaction_terms": "회귀모형 상호작용 항 목록이 올바르지 않습니다.",
        "duplicate_linear_model_interaction_term": "회귀모형 상호작용 항이 중복되었습니다.",
        "linear_model_interaction_same_predictor": (
            "상호작용 항은 서로 다른 두 예측변수로만 만들 수 있습니다."
        ),
        "linear_model_term_predictor_not_selected": (
            "추가 회귀 항은 선택된 예측변수에서만 만들 수 있습니다."
        ),
        "linear_model_term_requires_numeric_predictor": (
            "이번 slice의 2차항과 상호작용 항은 숫자형 예측변수만 지원합니다."
        ),
        "linear_model_quadratic_term_constant": (
            "2차항 값이 모두 같아 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_interaction_term_constant": (
            "상호작용 항 값이 모두 같아 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_design_rank_deficient": (
            "회귀 설계행렬이 rank deficient입니다. "
            "중복되거나 완전히 선형 종속인 예측변수를 제거하세요."
        ),
        "linear_model_residual_variance_zero": (
            "잔차 분산이 0이어서 계수 표준오차와 검정을 안정적으로 계산할 수 없습니다."
        ),
        "linear_model_standard_error_not_finite": "회귀 계수 표준오차가 유한하지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "회귀모형을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _linear_model_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "linear_model_not_causation": (
            "회귀계수는 관찰 데이터만으로 인과 효과를 의미하지 않습니다."
        ),
        "linear_model_linearity_assumption": (
            "OLS는 반응과 예측변수의 평균 관계가 선형이라는 가정을 사용합니다."
        ),
        "linear_model_independence_assumption": (
            "관측 독립성은 소프트웨어가 증명할 수 없으며 연구 설계로 확인해야 합니다."
        ),
        "linear_model_homoscedasticity_assumption": (
            "OLS 계수 검정은 잔차 분산이 일정하다는 가정에 민감할 수 있습니다."
        ),
        "linear_model_residual_normality_assumption": (
            "작은 표본에서는 잔차 정규성 위반이 계수 검정과 CI에 영향을 줄 수 있습니다."
        ),
        "linear_model_outlier_influence_sensitive": (
            "OLS는 이상점과 영향점에 민감합니다. 잔차와 leverage 진단을 함께 확인하세요."
        ),
        "linear_model_categorical_treatment_coding": (
            "범주형 예측변수는 첫 수준을 기준으로 하는 treatment coding으로 적합했습니다."
        ),
        "linear_model_quadratic_terms_selected": (
            "선택한 숫자형 2차항은 탐색적 모형 항이며, 해석에는 설계 근거가 필요합니다."
        ),
        "linear_model_interaction_terms_selected": (
            "선택한 숫자형 상호작용 항은 주효과와 함께 해석해야 합니다."
        ),
        "linear_model_high_condition_number": (
            "condition number가 높아 계수 추정이 다중공선성 또는 스케일 차이에 민감할 수 있습니다."
        ),
        "linear_model_high_vif": ("일부 예측변수의 VIF가 높아 계수 해석이 불안정할 수 있습니다."),
        "linear_model_large_standardized_residual": (
            "표준화 잔차가 큰 행이 있어 이상점 후보를 확인해야 합니다."
        ),
        "linear_model_high_leverage": (
            "leverage가 높은 행이 있어 적합선에 큰 영향을 줄 수 있습니다."
        ),
        "linear_model_high_cooks_distance": (
            "Cook's distance가 큰 행이 있어 영향점 후보를 확인해야 합니다."
        ),
        "missing_values_excluded": "결측 행은 complete-case 정책으로 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 행은 제외했습니다.",
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "linear_model_not_causation": "info",
        "linear_model_linearity_assumption": "info",
        "linear_model_independence_assumption": "info",
        "linear_model_homoscedasticity_assumption": "info",
        "linear_model_residual_normality_assumption": "info",
        "linear_model_outlier_influence_sensitive": "info",
        "linear_model_categorical_treatment_coding": "info",
        "linear_model_quadratic_terms_selected": "info",
        "linear_model_interaction_terms_selected": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        severity: Literal["info", "warning", "error"] = severities.get(code, "warning")
        warnings.append(AnalysisWarning(code=code, severity=severity, message=message))
    return warnings


def _linear_model_manifest_payload(
    *,
    model_id: str,
    analysis_id: str,
    context: DatasetRowsContext,
    request: AnalysisRunRequest,
    result: dict[str, object],
    row_snapshot: _RowSnapshotArtifact,
    created_at: str,
) -> dict[str, Any]:
    return {
        "manifest_schema_version": REGRESSION_MODEL_MANIFEST_SCHEMA_VERSION,
        "model_id": model_id,
        "analysis_id": analysis_id,
        "model_family": "linear_regression_ols",
        "method_id": request.method_id,
        "method_version": request.method_version,
        "app_version": APP_VERSION,
        "created_at": created_at,
        "dataset_version_id": context.version.version_id,
        "source_schema_hash": context.version.schema_hash,
        "source_canonical_artifact_sha256": context.canonical_rows_artifact.sha256,
        "filter_snapshot_sha256": row_snapshot.payload["filter_snapshot_sha256"],
        "row_snapshot_sha256": row_snapshot.record.sha256,
        "row_count_total": context.version.row_count,
        "row_count_included": row_snapshot.payload["selection"]["row_count_included"],
        "linear_model_result_schema_version": result.get("schema_version"),
        "response": result.get("response"),
        "predictors": result.get("predictors"),
        "model_specification": result.get("model_specification"),
        "coefficients": result.get("coefficients"),
        "sample": result.get("sample"),
        "prediction_basis": result.get("prediction_basis"),
        "fit": result.get("fit"),
        "diagnostics_summary": _linear_model_manifest_diagnostics(result.get("diagnostics")),
        "missing_policy": result.get("missing_policy"),
        "alpha": result.get("alpha"),
        "confidence_level": result.get("confidence_level"),
        "package_versions": result.get("package_versions"),
        "limitations": [
            "This manifest stores only app-created JSON model metadata, not pickle or joblib.",
            "Prediction is limited to schema-checked app-created OLS manifests.",
            (
                "Regression coefficients from observational data must not be interpreted "
                "as causal effects."
            ),
        ],
    }


def _linear_model_manifest_diagnostics(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None

    return {
        "rank": value.get("rank"),
        "parameter_count": value.get("parameter_count"),
        "condition_number": value.get("condition_number"),
        "max_vif": value.get("max_vif"),
        "residual_summary": _copy_without_keys(
            value.get("residual_summary"),
            {"large_standardized_row_indices"},
        ),
        "leverage": _copy_without_keys(value.get("leverage"), {"high_row_indices"}),
        "influence": _copy_without_keys(
            value.get("influence"),
            {"high_cooks_distance_row_indices"},
        ),
    }


def _copy_without_keys(value: object, excluded_keys: set[str]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items() if str(key) not in excluded_keys}


def _regression_model_manifest_relative_path(analysis_id: str, model_id: str) -> Path:
    return Path("workspaces") / "analyses" / analysis_id / f"model-{model_id}.json"
