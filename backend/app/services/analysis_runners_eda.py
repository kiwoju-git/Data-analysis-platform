from typing import Any
from uuid import uuid4

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisWarning,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    NUMERIC_DATA_TYPES,
    create_row_snapshot_artifact,
    iter_rows_for_snapshot,
    remove_file_if_exists,
    store_succeeded_analysis_result,
    utc_now,
)
from app.services.dataset_rows import DatasetRowsContext, get_dataset_rows_context
from app.statistics.descriptive import DescriptiveColumn, describe_numeric_columns
from app.statistics.equal_variances import (
    EqualVarianceGroupColumn,
    EqualVarianceResponseColumn,
    calculate_equal_variances,
)
from app.statistics.graphical_summary import (
    GraphicalSummaryColumn,
    summarize_numeric_graphics,
)
from app.statistics.normality import NormalityColumn, calculate_normality
from app.storage.metadata import DatasetColumnRecord

MAX_DESCRIPTIVE_COLUMNS = 100
MAX_GRAPHICAL_SUMMARY_COLUMNS = 20
MAX_GRAPHICAL_POINT_LIMIT = 5000
MAX_GRAPHICAL_HISTOGRAM_BINS = 200
MAX_NORMALITY_COLUMNS = 20
MAX_NORMALITY_QQ_POINT_LIMIT = 5000


def run_descriptive_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="기술통계 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    selected_columns = _selected_descriptive_columns(context, request.options)
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
        result = describe_numeric_columns(
            iter_rows_for_snapshot(context, row_snapshot),
            selected_columns,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
        )
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_descriptive_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _selected_descriptive_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> list[DescriptiveColumn]:
    column_ids = options.get("column_ids")
    if not isinstance(column_ids, list) or not column_ids:
        raise ApiError(
            code="descriptive_columns_required",
            message="기술통계를 계산할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(column_ids) > MAX_DESCRIPTIVE_COLUMNS:
        raise ApiError(
            code="too_many_descriptive_columns",
            message="한 번에 요청한 기술통계 컬럼 수가 허용 범위를 초과했습니다.",
        )
    if any(not isinstance(column_id, str) or not column_id for column_id in column_ids):
        raise ApiError(
            code="invalid_descriptive_columns",
            message="기술통계 컬럼 ID 목록이 올바르지 않습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    seen: set[str] = set()
    selected: list[DescriptiveColumn] = []
    for column_id in column_ids:
        if column_id in seen:
            raise ApiError(
                code="duplicate_descriptive_column",
                message="기술통계 컬럼 ID가 중복되었습니다.",
            )
        seen.add(column_id)

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="descriptive_column_not_found",
                message="요청한 기술통계 컬럼을 찾을 수 없습니다.",
            )
        _validate_descriptive_column(column)
        selected.append(
            DescriptiveColumn(
                column_id=column.column_id,
                column_index=column.column_index,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            ),
        )
    return selected


def _validate_descriptive_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="descriptive_column_is_id",
            message="ID 컬럼은 기술통계 계산 대상에서 제외해야 합니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="descriptive_column_not_numeric",
            message="기술통계는 현재 숫자형 컬럼만 지원합니다.",
        )


def _descriptive_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    columns = result.get("columns")
    if not isinstance(columns, list):
        return warnings

    for column in columns:
        if not isinstance(column, dict):
            continue
        column_warnings = column.get("warnings")
        display_name = column.get("display_name")
        if not isinstance(column_warnings, list) or not isinstance(display_name, str):
            continue
        if "non_numeric_values_excluded" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message=f"{display_name}: 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "no_numeric_values" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="no_numeric_values",
                    severity="warning",
                    message=f"{display_name}: 사용할 수 있는 숫자 값이 없습니다.",
                ),
            )
        if "constant_column" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="constant_column",
                    severity="info",
                    message=f"{display_name}: 모든 사용 값이 동일합니다.",
                ),
            )
    return warnings


def run_graphical_summary_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="그래프 요약 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    selected_columns = _selected_graphical_summary_columns(context, request.options)
    histogram_bin_count = _graphical_histogram_bin_count(request.options)
    point_limit = _graphical_point_limit(request.options)
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
        result = summarize_numeric_graphics(
            iter_rows_for_snapshot(context, row_snapshot),
            selected_columns,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            histogram_bin_count=histogram_bin_count,
            point_limit=point_limit,
        )
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_graphical_summary_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _selected_graphical_summary_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> list[GraphicalSummaryColumn]:
    column_ids = options.get("column_ids")
    if not isinstance(column_ids, list) or not column_ids:
        raise ApiError(
            code="graphical_summary_columns_required",
            message="그래프 요약을 계산할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(column_ids) > MAX_GRAPHICAL_SUMMARY_COLUMNS:
        raise ApiError(
            code="too_many_graphical_summary_columns",
            message="한 번에 요청한 그래프 요약 컬럼 수가 허용 범위를 초과했습니다.",
        )
    if any(not isinstance(column_id, str) or not column_id for column_id in column_ids):
        raise ApiError(
            code="invalid_graphical_summary_columns",
            message="그래프 요약 컬럼 ID 목록이 올바르지 않습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    seen: set[str] = set()
    selected: list[GraphicalSummaryColumn] = []
    for column_id in column_ids:
        if column_id in seen:
            raise ApiError(
                code="duplicate_graphical_summary_column",
                message="그래프 요약 컬럼 ID가 중복되었습니다.",
            )
        seen.add(column_id)

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="graphical_summary_column_not_found",
                message="요청한 그래프 요약 컬럼을 찾을 수 없습니다.",
            )
        _validate_graphical_summary_column(column)
        selected.append(
            GraphicalSummaryColumn(
                column_id=column.column_id,
                column_index=column.column_index,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            ),
        )
    return selected


def _validate_graphical_summary_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="graphical_summary_column_is_id",
            message="ID 컬럼은 그래프 요약 계산 대상에서 제외해야 합니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="graphical_summary_column_not_numeric",
            message="그래프 요약은 현재 숫자형 컬럼만 지원합니다.",
        )


def _graphical_histogram_bin_count(options: dict[str, Any]) -> int | None:
    raw_value = options.get("histogram_bin_count")
    if raw_value is None:
        return None
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_histogram_bin_count",
            message="히스토그램 bin 수가 올바르지 않습니다.",
        )
    if raw_value < 1 or raw_value > MAX_GRAPHICAL_HISTOGRAM_BINS:
        raise ApiError(
            code="invalid_histogram_bin_count",
            message="히스토그램 bin 수가 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _graphical_point_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("point_limit", 1000)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_graphical_point_limit",
            message="그래프 점 제한 값이 올바르지 않습니다.",
        )
    if raw_value < 10 or raw_value > MAX_GRAPHICAL_POINT_LIMIT:
        raise ApiError(
            code="invalid_graphical_point_limit",
            message="그래프 점 제한 값이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _graphical_summary_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    columns = result.get("columns")
    if not isinstance(columns, list):
        return warnings

    for column in columns:
        if not isinstance(column, dict):
            continue
        column_warnings = column.get("warnings")
        display_name = column.get("display_name")
        if not isinstance(column_warnings, list) or not isinstance(display_name, str):
            continue
        if "non_numeric_values_excluded" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message=f"{display_name}: 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "no_numeric_values" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="no_numeric_values",
                    severity="warning",
                    message=f"{display_name}: 사용할 수 있는 숫자 값이 없습니다.",
                ),
            )
        if "constant_column" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="constant_column",
                    severity="info",
                    message=f"{display_name}: 모든 사용 값이 동일합니다.",
                ),
            )
        if "graphical_points_truncated" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="graphical_points_truncated",
                    severity="info",
                    message=f"{display_name}: Q-Q/ECDF 점은 결정적 방식으로 제한했습니다.",
                ),
            )
    return warnings


def run_normality_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="정규성 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    _reject_normality_grouping(request)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    selected_columns = _selected_normality_columns(context, request.options)
    alpha = _normality_alpha(request.options)
    include_qq_points = _normality_include_qq_points(request.options)
    qq_point_limit = _normality_qq_point_limit(request.options)
    _normality_missing_policy(request.options)
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
        result = calculate_normality(
            iter_rows_for_snapshot(context, row_snapshot),
            selected_columns,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            alpha=alpha,
            include_qq_points=include_qq_points,
            qq_point_limit=qq_point_limit,
        )
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_normality_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _selected_normality_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> list[NormalityColumn]:
    column_ids = options.get("column_ids")
    if not isinstance(column_ids, list) or not column_ids:
        raise ApiError(
            code="normality_columns_required",
            message="정규성을 검정할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(column_ids) > MAX_NORMALITY_COLUMNS:
        raise ApiError(
            code="too_many_normality_columns",
            message="한 번에 요청한 정규성 검정 컬럼 수가 허용 범위를 초과했습니다.",
        )
    if any(not isinstance(column_id, str) or not column_id for column_id in column_ids):
        raise ApiError(
            code="invalid_normality_columns",
            message="정규성 검정 컬럼 ID 목록이 올바르지 않습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    seen: set[str] = set()
    selected: list[NormalityColumn] = []
    for column_id in column_ids:
        if column_id in seen:
            raise ApiError(
                code="duplicate_normality_column",
                message="정규성 검정 컬럼 ID가 중복되었습니다.",
            )
        seen.add(column_id)

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="normality_column_not_found",
                message="요청한 정규성 검정 컬럼을 찾을 수 없습니다.",
            )
        _validate_normality_column(column)
        selected.append(
            NormalityColumn(
                column_id=column.column_id,
                column_index=column.column_index,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            ),
        )
    return selected


def _validate_normality_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="normality_column_is_id",
            message="ID 컬럼은 정규성 검정 대상에서 제외해야 합니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="normality_column_not_numeric",
            message="정규성 검정은 현재 숫자형 컬럼만 지원합니다.",
        )


def _reject_normality_grouping(request: AnalysisRunRequest) -> None:
    if "group" in request.roles or request.options.get("group_column_id") is not None:
        raise ApiError(
            code="normality_grouping_not_supported",
            message="이번 정규성 검정 slice는 그룹별 실행을 아직 지원하지 않습니다.",
        )


def _normality_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_normality_alpha",
            message="정규성 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_normality_alpha",
            message="정규성 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _normality_include_qq_points(options: dict[str, Any]) -> bool:
    raw_value = options.get("include_qq_points", True)
    if not isinstance(raw_value, bool):
        raise ApiError(
            code="invalid_normality_include_qq_points",
            message="Q-Q 점 포함 옵션이 올바르지 않습니다.",
        )
    return raw_value


def _normality_qq_point_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("qq_point_limit", 1000)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_normality_qq_point_limit",
            message="Q-Q 점 제한 값이 올바르지 않습니다.",
        )
    if raw_value < 10 or raw_value > MAX_NORMALITY_QQ_POINT_LIMIT:
        raise ApiError(
            code="invalid_normality_qq_point_limit",
            message="Q-Q 점 제한 값이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _normality_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "available_case_by_column")
    if raw_value != "available_case_by_column":
        raise ApiError(
            code="normality_missing_policy_unsupported",
            message="정규성 검정은 현재 컬럼별 available-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _normality_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings = [
        AnalysisWarning(
            code="normality_not_method_switch",
            severity="info",
            message="정규성 검정 결과만으로 후속 모수/비모수 검정을 자동 전환하지 않습니다.",
        ),
    ]
    columns = result.get("columns")
    if not isinstance(columns, list):
        return warnings

    for column in columns:
        if not isinstance(column, dict):
            continue
        column_warnings = column.get("warnings")
        display_name = column.get("display_name")
        if not isinstance(column_warnings, list) or not isinstance(display_name, str):
            continue
        if "non_numeric_values_excluded" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message=f"{display_name}: 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "no_numeric_values" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="no_numeric_values",
                    severity="warning",
                    message=f"{display_name}: 사용할 수 있는 숫자 값이 없습니다.",
                ),
            )
        if "normality_insufficient_observations" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="normality_insufficient_observations",
                    severity="warning",
                    message=(
                        f"{display_name}: Shapiro-Wilk/Anderson-Darling에는 "
                        "최소 3개 사용 값이 필요합니다."
                    ),
                ),
            )
        if "constant_column" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="constant_column",
                    severity="warning",
                    message=(
                        f"{display_name}: 모든 사용 값이 동일해 정규성 검정을 "
                        "계산하지 않았습니다."
                    ),
                ),
            )
        if "shapiro_large_n_pvalue_limitation" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="shapiro_large_n_pvalue_limitation",
                    severity="warning",
                    message=(
                        f"{display_name}: Shapiro-Wilk p-value는 N>5000에서 "
                        "정확도 제한이 있습니다."
                    ),
                ),
            )
        if "normality_qq_points_truncated" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="normality_qq_points_truncated",
                    severity="info",
                    message=f"{display_name}: Q-Q 점은 결정적 방식으로 제한했습니다.",
                ),
            )
    return warnings


def run_equal_variances_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="등분산 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_equal_variances_columns(
        context,
        request.options,
    )
    alpha = _equal_variances_alpha(request.options)
    _equal_variances_missing_policy(request.options)
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
        result = calculate_equal_variances(
            iter_rows_for_snapshot(context, row_snapshot),
            response_column,
            group_column,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            alpha=alpha,
        )
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_equal_variances_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _selected_equal_variances_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[EqualVarianceResponseColumn, EqualVarianceGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="equal_variances_response_required",
            message="등분산 검정 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="equal_variances_group_required",
            message="등분산 검정 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="equal_variances_same_response_and_group",
            message="반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="equal_variances_response_column_not_found",
            message="요청한 등분산 검정 반응 컬럼을 찾을 수 없습니다.",
        )
    group_column = columns_by_id.get(group_column_id)
    if group_column is None:
        raise ApiError(
            code="equal_variances_group_column_not_found",
            message="요청한 등분산 검정 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_equal_variances_response_column(response_column)
    _validate_equal_variances_group_column(group_column)
    return (
        EqualVarianceResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        EqualVarianceGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_equal_variances_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="equal_variances_response_column_is_id",
            message="ID 컬럼은 등분산 검정 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="equal_variances_response_column_not_numeric",
            message="등분산 검정 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_equal_variances_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="equal_variances_group_column_is_id",
            message="ID 컬럼은 등분산 검정 그룹 변수로 사용할 수 없습니다.",
        )


def _equal_variances_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_equal_variances_alpha",
            message="등분산 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_equal_variances_alpha",
            message="등분산 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _equal_variances_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="equal_variances_missing_policy_unsupported",
            message="등분산 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _equal_variances_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings = [
        AnalysisWarning(
            code="equal_variances_not_method_switch",
            severity="info",
            message=(
                "등분산 검정 결과만으로 후속 pooled/Welch 또는 ANOVA 방식을 "
                "자동 전환하지 않습니다."
            ),
        ),
    ]
    result_warning_codes = result.get("warnings")
    if isinstance(result_warning_codes, list):
        if "missing_values_excluded" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="missing_values_excluded",
                    severity="warning",
                    message="반응 또는 그룹 결측 행은 complete-case 정책으로 제외했습니다.",
                ),
            )
        if "non_numeric_values_excluded" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "equal_variances_insufficient_groups" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="equal_variances_insufficient_groups",
                    severity="warning",
                    message="등분산 검정에는 사용 가능한 그룹이 2개 이상 필요합니다.",
                ),
            )
        if "equal_variances_group_n_too_small" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="equal_variances_group_n_too_small",
                    severity="warning",
                    message="각 그룹에는 최소 2개 사용 값이 필요합니다.",
                ),
            )
        if "constant_response" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="constant_response",
                    severity="warning",
                    message="모든 사용 반응 값이 동일해 등분산 검정을 계산하지 않았습니다.",
                ),
            )
    tests = result.get("tests")
    if not isinstance(tests, list):
        return warnings
    for test in tests:
        if not isinstance(test, dict):
            continue
        test_warnings = test.get("warnings")
        if not isinstance(test_warnings, list):
            continue
        if "equal_variances_statistic_not_finite" in test_warnings:
            warnings.append(
                AnalysisWarning(
                    code="equal_variances_statistic_not_finite",
                    severity="warning",
                    message="등분산 검정 통계량이 유한하지 않아 결과를 계산하지 않았습니다.",
                ),
            )
            break
    return warnings
