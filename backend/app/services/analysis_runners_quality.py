from math import isfinite
from typing import Any, Literal
from uuid import uuid4

from fastapi import status
from pydantic import ValidationError

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisWarning,
    CapabilityOptions,
    GageRrOptions,
    GageRunChartOptions,
    IndividualsChartOptions,
    RunChartOptions,
    SubgroupChartOptions,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    NUMERIC_DATA_TYPES,
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
from app.services.gage_rr import (
    gage_rr_api_error,
    gage_rr_column_payload,
    select_gage_rr_columns,
)
from app.statistics.capability import (
    CapabilityColumn,
    CapabilityError,
    calculate_normal_capability,
)
from app.statistics.gage_rr import GageRrError, calculate_gage_rr_anova
from app.statistics.gage_run_chart import (
    GageRunChartColumn,
    GageRunChartError,
    calculate_gage_run_chart,
)
from app.statistics.individuals_chart import (
    IndividualsChartColumn,
    IndividualsChartError,
    calculate_individuals_chart,
)
from app.statistics.run_chart import (
    RunChartColumn,
    RunChartError,
    calculate_run_chart,
)
from app.statistics.subgroup_chart import (
    SubgroupChartColumn,
    SubgroupChartError,
    calculate_subgroup_chart,
)
from app.storage.metadata import (
    DatasetColumnRecord,
)

MAX_RUN_CHART_POINT_LIMIT = 5000
RUN_CHART_ORDER_DATA_TYPES = {"integer", "decimal", "datetime"}
SUBGROUP_CHART_SUBGROUP_DATA_TYPES = {"integer", "decimal", "text", "boolean"}


def run_individuals_chart_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="개별값 관리도 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_individuals_chart_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    value_column = _selected_individuals_chart_column(context, options)
    order_column = _selected_individuals_chart_order_column(
        context,
        options,
        value_column,
    )
    missing_policy = _individuals_chart_missing_policy(options)
    same_side_min_length = _individuals_chart_same_side_min_length(options)
    trend_min_length = _individuals_chart_trend_min_length(options)
    point_limit = _individuals_chart_point_limit(options)
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
            result = calculate_individuals_chart(
                _iter_rows_for_snapshot(context, row_snapshot),
                value_column,
                order_column=order_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                missing_policy=missing_policy,
                same_side_min_length=same_side_min_length,
                trend_min_length=trend_min_length,
                point_limit=point_limit,
            )
        except IndividualsChartError as exc:
            raise _individuals_chart_api_error(exc.code) from exc
        warnings = _individuals_chart_warnings(result)
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


def _validate_individuals_chart_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return IndividualsChartOptions.model_validate(options).model_dump(exclude_none=True)
    except ValidationError as exc:
        raise ApiError(
            code="invalid_individuals_chart_options",
            message="개별값 관리도 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_individuals_chart_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> IndividualsChartColumn:
    value_column_id = options.get("value_column_id")
    if not isinstance(value_column_id, str) or not value_column_id:
        raise ApiError(
            code="individuals_chart_value_column_required",
            message="개별값 관리도 측정값 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    column = columns_by_id.get(value_column_id)
    if column is None:
        raise ApiError(
            code="individuals_chart_value_column_not_found",
            message="요청한 개별값 관리도 측정값 컬럼을 찾을 수 없습니다.",
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="individuals_chart_value_column_is_id",
            message="ID 컬럼은 개별값 관리도 측정값으로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="individuals_chart_value_column_not_numeric",
            message="개별값 관리도 측정값은 현재 숫자형 컬럼만 지원합니다.",
        )
    return IndividualsChartColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _selected_individuals_chart_order_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
    value_column: IndividualsChartColumn,
) -> IndividualsChartColumn | None:
    order_column_id = options.get("order_column_id")
    if order_column_id is None or order_column_id == "":
        return None
    if not isinstance(order_column_id, str):
        raise ApiError(
            code="invalid_individuals_chart_order_column",
            message="개별값 관리도 순서 컬럼 ID가 올바르지 않습니다.",
        )
    if order_column_id == value_column.column_id:
        raise ApiError(
            code="individuals_chart_order_column_same_as_value",
            message="개별값 관리도 순서 컬럼은 측정값 컬럼과 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    column = columns_by_id.get(order_column_id)
    if column is None:
        raise ApiError(
            code="individuals_chart_order_column_not_found",
            message="요청한 개별값 관리도 순서 컬럼을 찾을 수 없습니다.",
        )
    if column.data_type not in RUN_CHART_ORDER_DATA_TYPES:
        raise ApiError(
            code="individuals_chart_order_column_not_numeric",
            message="개별값 관리도 순서 컬럼은 현재 숫자형 또는 날짜시간 컬럼만 지원합니다.",
        )
    return IndividualsChartColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _individuals_chart_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="individuals_chart_missing_policy_unsupported",
            message="개별값 관리도는 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _individuals_chart_point_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("point_limit", 1000)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_individuals_chart_point_limit",
            message="개별값 관리도 point limit이 올바르지 않습니다.",
        )
    if raw_value <= 0 or raw_value > MAX_RUN_CHART_POINT_LIMIT:
        raise ApiError(
            code="invalid_individuals_chart_point_limit",
            message="개별값 관리도 point limit이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _individuals_chart_same_side_min_length(options: dict[str, Any]) -> int:
    raw_value = options.get("same_side_min_length", 9)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_individuals_chart_same_side_min_length",
            message="개별값 관리도 same-side rule 길이가 올바르지 않습니다.",
        )
    if raw_value < 3 or raw_value > 30:
        raise ApiError(
            code="invalid_individuals_chart_same_side_min_length",
            message="개별값 관리도 same-side rule 길이가 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _individuals_chart_trend_min_length(options: dict[str, Any]) -> int:
    raw_value = options.get("trend_min_length", 6)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_individuals_chart_trend_min_length",
            message="개별값 관리도 trend rule 길이가 올바르지 않습니다.",
        )
    if raw_value < 3 or raw_value > 20:
        raise ApiError(
            code="invalid_individuals_chart_trend_min_length",
            message="개별값 관리도 trend rule 길이가 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _individuals_chart_api_error(code: str) -> ApiError:
    messages = {
        "individuals_chart_missing_policy_unsupported": (
            "개별값 관리도는 현재 complete-case 결측 처리만 지원합니다."
        ),
        "invalid_individuals_chart_point_limit": (
            "개별값 관리도 point limit이 허용 범위를 벗어났습니다."
        ),
        "invalid_individuals_chart_same_side_min_length": (
            "개별값 관리도 same-side rule 길이가 허용 범위를 벗어났습니다."
        ),
        "invalid_individuals_chart_trend_min_length": (
            "개별값 관리도 trend rule 길이가 허용 범위를 벗어났습니다."
        ),
        "invalid_individuals_chart_order_column": (
            "개별값 관리도 순서 컬럼 ID가 올바르지 않습니다."
        ),
        "individuals_chart_order_column_same_as_value": (
            "개별값 관리도 순서 컬럼은 측정값 컬럼과 달라야 합니다."
        ),
        "individuals_chart_order_column_not_found": (
            "요청한 개별값 관리도 순서 컬럼을 찾을 수 없습니다."
        ),
        "individuals_chart_order_column_not_numeric": (
            "개별값 관리도 순서 컬럼은 현재 숫자형 또는 날짜시간 컬럼만 지원합니다."
        ),
        "individuals_chart_order_mixed_timezone_awareness": (
            "개별값 관리도 날짜시간 순서 컬럼에 timezone 포함 값과 미포함 값이 섞여 있습니다."
        ),
        "individuals_chart_n_too_small": (
            "개별값 관리도에는 사용 가능한 숫자 값이 최소 3개 필요합니다."
        ),
        "individuals_chart_zero_moving_range": (
            "모든 moving range가 0이라 관리한계를 추정할 수 없습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "개별값 관리도를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _individuals_chart_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "individuals_chart_uses_canonical_row_order": (
            "이번 slice의 개별값 관리도는 canonical row 순서를 실행 순서로 사용합니다."
        ),
        "individuals_chart_uses_numeric_order_column": (
            "개별값 관리도는 선택한 숫자형 순서 컬럼을 오름차순으로 정렬해 실행 순서로 사용합니다."
        ),
        "individuals_chart_uses_datetime_order_column": (
            "개별값 관리도는 선택한 날짜시간 순서 컬럼을 오름차순으로 정렬해 "
            "실행 순서로 사용합니다."
        ),
        "individuals_chart_control_limits_estimated_from_moving_range": (
            "관리한계는 인접 moving range 평균과 d2=1.128 상수로 추정했습니다."
        ),
        "individuals_chart_process_stability_not_proven": (
            "공정 안정성, 독립성, 합리적 시간 순서는 소프트웨어가 증명할 수 없으므로 "
            "사용자가 설계상 확인해야 합니다."
        ),
        "missing_values_excluded": "측정값 결측 행은 complete-case 정책으로 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 측정값은 제외했습니다.",
        "individuals_chart_order_missing_excluded": (
            "순서 컬럼 결측 행은 complete-case 정책으로 제외했습니다."
        ),
        "individuals_chart_order_non_numeric_excluded": (
            "숫자로 해석할 수 없는 순서 컬럼 값은 제외했습니다."
        ),
        "individuals_chart_order_invalid_datetime_excluded": (
            "날짜시간으로 해석할 수 없는 순서 컬럼 값은 제외했습니다."
        ),
        "individuals_chart_order_ties_stable_sorted": (
            "순서 컬럼 값이 같은 행은 canonical row position으로 안정 정렬했습니다."
        ),
        "individuals_chart_i_limit_signal_detected": (
            "I chart에서 3-sigma 관리한계 밖 점이 감지되었습니다."
        ),
        "individuals_chart_mr_limit_signal_detected": (
            "MR chart에서 moving range UCL 초과 점이 감지되었습니다."
        ),
        "individuals_chart_i_same_side_signal_detected": (
            "I chart에서 중심선 한쪽에 연속된 점 신호가 감지되었습니다."
        ),
        "individuals_chart_i_trend_signal_detected": (
            "I chart에서 연속 증가/감소 trend 신호가 감지되었습니다."
        ),
        "individuals_chart_i_alternating_signal_detected": (
            "I chart에서 연속 상승/하락이 교대로 반복되는 신호가 감지되었습니다."
        ),
        "individuals_chart_i_two_of_three_signal_detected": (
            "I chart에서 2-sigma 밖 같은 쪽 2-of-3 zone 신호가 감지되었습니다."
        ),
        "individuals_chart_i_four_of_five_signal_detected": (
            "I chart에서 1-sigma 밖 같은 쪽 4-of-5 zone 신호가 감지되었습니다."
        ),
        "individuals_chart_i_fifteen_within_1_sigma_signal_detected": (
            "I chart에서 1-sigma 안쪽에 연속 15점이 모이는 신호가 감지되었습니다."
        ),
        "individuals_chart_i_eight_outside_1_sigma_signal_detected": (
            "I chart에서 1-sigma 안쪽을 모두 벗어난 연속 8점 신호가 감지되었습니다."
        ),
        "individuals_chart_points_truncated": (
            "개별값 관리도 point payload는 결정적 방식으로 제한했습니다."
        ),
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "individuals_chart_uses_canonical_row_order": "info",
        "individuals_chart_uses_numeric_order_column": "info",
        "individuals_chart_uses_datetime_order_column": "info",
        "individuals_chart_control_limits_estimated_from_moving_range": "info",
        "individuals_chart_process_stability_not_proven": "info",
        "individuals_chart_order_ties_stable_sorted": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        warnings.append(
            AnalysisWarning(
                code=code,
                severity=severities.get(code, "warning"),
                message=message,
            ),
        )
    return warnings


def run_subgroup_chart_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="부분군 관리도 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_subgroup_chart_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    value_column = _selected_subgroup_chart_value_column(context, options)
    subgroup_column = _selected_subgroup_chart_subgroup_column(
        context,
        options,
        value_column,
    )
    chart_type = _subgroup_chart_type(options)
    missing_policy = _subgroup_chart_missing_policy(options)
    point_limit = _subgroup_chart_point_limit(options)
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
            result = calculate_subgroup_chart(
                _iter_rows_for_snapshot(context, row_snapshot),
                value_column,
                subgroup_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                chart_type=chart_type,
                missing_policy=missing_policy,
                point_limit=point_limit,
            )
        except SubgroupChartError as exc:
            raise _subgroup_chart_api_error(exc.code) from exc
        warnings = _subgroup_chart_warnings(result)
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


def _validate_subgroup_chart_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return SubgroupChartOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_subgroup_chart_options",
            message="부분군 관리도 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_subgroup_chart_value_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> SubgroupChartColumn:
    value_column_id = options.get("value_column_id")
    if not isinstance(value_column_id, str) or not value_column_id:
        raise ApiError(
            code="subgroup_chart_value_column_required",
            message="부분군 관리도 측정값 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    column = columns_by_id.get(value_column_id)
    if column is None:
        raise ApiError(
            code="subgroup_chart_value_column_not_found",
            message="요청한 부분군 관리도 측정값 컬럼을 찾을 수 없습니다.",
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="subgroup_chart_value_column_is_id",
            message="ID 컬럼은 부분군 관리도 측정값으로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="subgroup_chart_value_column_not_numeric",
            message="부분군 관리도 측정값은 현재 숫자형 컬럼만 지원합니다.",
        )
    return SubgroupChartColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _selected_subgroup_chart_subgroup_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
    value_column: SubgroupChartColumn,
) -> SubgroupChartColumn:
    subgroup_column_id = options.get("subgroup_column_id")
    if not isinstance(subgroup_column_id, str) or not subgroup_column_id:
        raise ApiError(
            code="subgroup_chart_subgroup_column_required",
            message="부분군 관리도 부분군 컬럼을 선택해야 합니다.",
        )
    if subgroup_column_id == value_column.column_id:
        raise ApiError(
            code="subgroup_chart_subgroup_column_same_as_value",
            message="부분군 관리도 부분군 컬럼은 측정값 컬럼과 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    column = columns_by_id.get(subgroup_column_id)
    if column is None:
        raise ApiError(
            code="subgroup_chart_subgroup_column_not_found",
            message="요청한 부분군 관리도 부분군 컬럼을 찾을 수 없습니다.",
        )
    if column.data_type not in SUBGROUP_CHART_SUBGROUP_DATA_TYPES:
        raise ApiError(
            code="subgroup_chart_subgroup_column_unsupported_type",
            message="부분군 컬럼은 현재 숫자형, 텍스트, 불리언 컬럼만 지원합니다.",
        )
    return SubgroupChartColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _subgroup_chart_type(options: dict[str, Any]) -> str:
    raw_value = options.get("chart_type", "xbar_r")
    if raw_value not in {"xbar_r", "xbar_s"}:
        raise ApiError(
            code="subgroup_chart_type_unsupported",
            message="부분군 관리도는 현재 고정 크기 Xbar-R 또는 Xbar-S만 지원합니다.",
        )
    return raw_value


def _subgroup_chart_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="subgroup_chart_missing_policy_unsupported",
            message="부분군 관리도는 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _subgroup_chart_point_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("point_limit", 1000)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_subgroup_chart_point_limit",
            message="부분군 관리도 point limit이 올바르지 않습니다.",
        )
    if raw_value <= 0 or raw_value > MAX_RUN_CHART_POINT_LIMIT:
        raise ApiError(
            code="invalid_subgroup_chart_point_limit",
            message="부분군 관리도 point limit이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _subgroup_chart_api_error(code: str) -> ApiError:
    messages = {
        "subgroup_chart_type_unsupported": (
            "부분군 관리도는 현재 고정 크기 Xbar-R 또는 Xbar-S만 지원합니다."
        ),
        "subgroup_chart_missing_policy_unsupported": (
            "부분군 관리도는 현재 complete-case 결측 처리만 지원합니다."
        ),
        "invalid_subgroup_chart_point_limit": (
            "부분군 관리도 point limit이 허용 범위를 벗어났습니다."
        ),
        "subgroup_chart_subgroup_count_too_small": (
            "부분군 관리도에는 사용 가능한 부분군이 최소 2개 필요합니다."
        ),
        "subgroup_chart_subgroup_size_too_small": (
            "Xbar-R/Xbar-S 관리도에는 각 부분군에 최소 2개 관측값이 필요합니다."
        ),
        "subgroup_chart_varying_subgroup_size_unsupported": (
            "이번 slice는 부분군 크기가 모두 같은 Xbar-R/Xbar-S 관리도만 지원합니다."
        ),
        "subgroup_chart_subgroup_size_unsupported": (
            "이번 slice는 부분군 크기 2부터 10까지의 Xbar-R/Xbar-S 상수만 지원합니다."
        ),
        "subgroup_chart_zero_average_range": (
            "평균 부분군 범위가 0이라 Xbar-R 관리한계를 추정할 수 없습니다."
        ),
        "subgroup_chart_zero_average_stddev": (
            "평균 부분군 표본표준편차가 0이라 Xbar-S 관리한계를 추정할 수 없습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "부분군 관리도를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _subgroup_chart_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "subgroup_chart_uses_canonical_subgroup_order": (
            "부분군은 canonical row에서 처음 나타난 순서로 표시됩니다."
        ),
        "subgroup_chart_control_limits_estimated_from_xbar_r_constants": (
            "관리한계는 고정 부분군 크기 Xbar-R 상수로 추정했습니다."
        ),
        "subgroup_chart_control_limits_estimated_from_xbar_s_constants": (
            "관리한계는 고정 부분군 크기 Xbar-S 상수로 추정했습니다."
        ),
        "subgroup_chart_rational_subgroups_not_proven": (
            "합리적 부분군 구성, 공정 순서, 독립성은 소프트웨어가 증명할 수 없으므로 "
            "사용자가 설계상 확인해야 합니다."
        ),
        "missing_values_excluded": "측정값 결측 행은 complete-case 정책으로 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 측정값은 제외했습니다.",
        "subgroup_chart_subgroup_missing_excluded": (
            "부분군 컬럼 결측 행은 complete-case 정책으로 제외했습니다."
        ),
        "subgroup_chart_xbar_limit_signal_detected": (
            "Xbar chart에서 관리한계 밖 부분군 평균이 감지되었습니다."
        ),
        "subgroup_chart_r_limit_signal_detected": (
            "R chart에서 관리한계 밖 부분군 범위가 감지되었습니다."
        ),
        "subgroup_chart_s_limit_signal_detected": (
            "S chart에서 관리한계 밖 부분군 표본표준편차가 감지되었습니다."
        ),
        "subgroup_chart_points_truncated": (
            "부분군 관리도 point payload는 결정적 방식으로 제한했습니다."
        ),
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "subgroup_chart_uses_canonical_subgroup_order": "info",
        "subgroup_chart_control_limits_estimated_from_xbar_r_constants": "info",
        "subgroup_chart_control_limits_estimated_from_xbar_s_constants": "info",
        "subgroup_chart_rational_subgroups_not_proven": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        warnings.append(
            AnalysisWarning(
                code=code,
                severity=severities.get(code, "warning"),
                message=message,
            ),
        )
    return warnings


def run_capability_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="공정능력 분석 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_capability_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    value_column = _selected_capability_column(context, options)
    lsl = _optional_capability_spec_limit(options, "lsl")
    usl = _optional_capability_spec_limit(options, "usl")
    target = _optional_capability_spec_limit(options, "target")
    missing_policy = _capability_missing_policy(options)
    histogram_bin_limit = _capability_histogram_bin_limit(options)
    if lsl is None and usl is None:
        raise ApiError(
            code="capability_spec_limit_required",
            message="공정능력 분석에는 LSL 또는 USL 중 최소 하나가 필요합니다.",
        )
    if lsl is not None and usl is not None and lsl >= usl:
        raise ApiError(
            code="capability_spec_limits_invalid",
            message="공정능력 분석의 LSL은 USL보다 작아야 합니다.",
        )
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
            result = calculate_normal_capability(
                _iter_rows_for_snapshot(context, row_snapshot),
                value_column,
                lsl=lsl,
                usl=usl,
                target=target,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                missing_policy=missing_policy,
                histogram_bin_limit=histogram_bin_limit,
            )
        except CapabilityError as exc:
            raise _capability_api_error(exc.code) from exc
        warnings = _capability_warnings(result)
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


def _validate_capability_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return CapabilityOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_capability_options",
            message="공정능력 분석 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_capability_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> CapabilityColumn:
    value_column_id = options.get("value_column_id")
    if not isinstance(value_column_id, str) or not value_column_id:
        raise ApiError(
            code="capability_value_column_required",
            message="공정능력 분석 측정값 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    column = columns_by_id.get(value_column_id)
    if column is None:
        raise ApiError(
            code="capability_value_column_not_found",
            message="요청한 공정능력 분석 측정값 컬럼을 찾을 수 없습니다.",
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="capability_value_column_is_id",
            message="ID 컬럼은 공정능력 분석 측정값으로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="capability_value_column_not_numeric",
            message="공정능력 분석 측정값은 현재 숫자형 컬럼만 지원합니다.",
        )
    return CapabilityColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _optional_capability_spec_limit(options: dict[str, Any], key: str) -> float | None:
    raw_value = options.get(key)
    if raw_value is None:
        return None
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="capability_spec_limits_invalid",
            message="공정능력 분석 spec limit은 숫자여야 합니다.",
        )
    value = float(raw_value)
    if not isfinite(value):
        raise ApiError(
            code="capability_spec_limits_invalid",
            message="공정능력 분석 spec limit은 유한한 숫자여야 합니다.",
        )
    return value


def _capability_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="capability_missing_policy_unsupported",
            message="공정능력 분석은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _capability_histogram_bin_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("histogram_bin_limit", 30)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_capability_histogram_bin_limit",
            message="공정능력 분석 histogram bin limit이 올바르지 않습니다.",
        )
    if raw_value <= 0 or raw_value > 30:
        raise ApiError(
            code="invalid_capability_histogram_bin_limit",
            message="공정능력 분석 histogram bin limit이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _capability_api_error(code: str) -> ApiError:
    messages = {
        "invalid_capability_options": "공정능력 분석 옵션 계약이 올바르지 않습니다.",
        "capability_missing_policy_unsupported": (
            "공정능력 분석은 현재 complete-case 결측 처리만 지원합니다."
        ),
        "capability_spec_limit_required": (
            "공정능력 분석에는 LSL 또는 USL 중 최소 하나가 필요합니다."
        ),
        "capability_spec_limits_invalid": "공정능력 분석의 LSL은 USL보다 작아야 합니다.",
        "capability_target_outside_spec": "목표값은 지정된 spec limit 안에 있어야 합니다.",
        "capability_n_too_small": ("공정능력 분석에는 사용 가능한 숫자 값이 최소 2개 필요합니다."),
        "capability_zero_overall_sigma": (
            "전체 표본 표준편차가 0이라 공정능력 지수를 계산할 수 없습니다."
        ),
        "capability_zero_within_sigma": (
            "within sigma 추정값이 0이라 공정능력 지수를 계산할 수 없습니다."
        ),
        "invalid_capability_histogram_bin_limit": (
            "공정능력 분석 histogram bin limit이 허용 범위를 벗어났습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "공정능력 분석을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _capability_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "capability_normal_model_assumed": (
            "이 첫 slice는 정규분포 기반 capability 지수와 기대 비규격률만 계산합니다."
        ),
        "capability_control_limits_not_spec_limits": (
            "Spec limit은 고객/공정 요구 한계이며 관리한계와 다릅니다."
        ),
        "capability_process_stability_not_proven": (
            "공정 안정성이 확인되지 않으면 capability 지수의 장기 해석이 부적절할 수 있습니다."
        ),
        "capability_measurement_system_not_verified": (
            "측정시스템 적합성이 부족하면 capability 지수도 왜곡될 수 있습니다."
        ),
        "capability_within_sigma_uses_canonical_moving_range": (
            "within sigma는 canonical row 순서의 인접 moving range로 추정했습니다."
        ),
        "capability_point_estimates_without_ci": (
            "이번 slice는 capability 지수의 점추정만 제공하며 신뢰구간은 아직 제공하지 않습니다."
        ),
        "capability_one_sided_spec": (
            "한쪽 spec만 지정되어 양측 capability 지수는 계산하지 않았습니다."
        ),
        "capability_target_recorded_cpm_not_computed": (
            "목표값은 기록하지만 Cpm은 이번 slice에서 계산하지 않습니다."
        ),
        "missing_values_excluded": "측정값 결측 행은 complete-case 정책으로 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 측정값은 제외했습니다.",
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "capability_normal_model_assumed": "info",
        "capability_control_limits_not_spec_limits": "info",
        "capability_point_estimates_without_ci": "info",
        "capability_one_sided_spec": "info",
        "capability_target_recorded_cpm_not_computed": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        warnings.append(
            AnalysisWarning(
                code=code,
                severity=severities.get(code, "warning"),
                message=message,
            ),
        )
    return warnings


def run_gage_rr_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Gage R&R 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_gage_rr_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    measurement_column_id = _gage_rr_required_column_id(options, "measurement_column_id")
    part_column_id = _gage_rr_required_column_id(options, "part_column_id")
    operator_column_id = _gage_rr_required_column_id(options, "operator_column_id")
    replicate_column_id = _gage_rr_required_column_id(options, "replicate_column_id")
    missing_policy = _gage_rr_missing_policy(options)
    (
        measurement_column,
        part_column,
        operator_column,
        replicate_column,
    ) = _select_gage_run_chart_columns(
        context.columns,
        measurement_column_id=measurement_column_id,
        part_column_id=part_column_id,
        operator_column_id=operator_column_id,
        replicate_column_id=replicate_column_id,
    )
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
            result = calculate_gage_rr_anova(
                _iter_rows_for_snapshot(context, row_snapshot),
                measurement_column=gage_rr_column_payload(measurement_column),
                part_column=gage_rr_column_payload(part_column),
                operator_column=gage_rr_column_payload(operator_column),
                replicate_column=gage_rr_column_payload(replicate_column),
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                missing_policy=missing_policy,
            )
        except GageRrError as exc:
            raise gage_rr_api_error(exc.code) from exc
        warnings = _gage_rr_warnings(result)
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


def _validate_gage_rr_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return GageRrOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_gage_rr_options",
            message="Gage R&R 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _gage_rr_required_column_id(options: dict[str, Any], key: str) -> str:
    raw_value = options.get(key)
    if isinstance(raw_value, str) and raw_value:
        return raw_value
    codes = {
        "measurement_column_id": "gage_rr_measurement_column_required",
        "part_column_id": "gage_rr_part_column_required",
        "operator_column_id": "gage_rr_operator_column_required",
        "replicate_column_id": "gage_rr_replicate_column_required",
    }
    messages = {
        "measurement_column_id": "Gage R&R 측정값 컬럼을 선택해야 합니다.",
        "part_column_id": "Gage R&R 부품 컬럼을 선택해야 합니다.",
        "operator_column_id": "Gage R&R 측정자 컬럼을 선택해야 합니다.",
        "replicate_column_id": "Gage R&R 반복 컬럼을 선택해야 합니다.",
    }
    raise ApiError(
        code=codes[key],
        message=messages[key],
    )


def _gage_rr_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="gage_rr_missing_policy_unsupported",
            message="Gage R&R은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _gage_rr_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "gage_rr_balanced_crossed_anova_assumed": (
            "이번 slice는 balanced crossed ANOVA Gage R&R만 계산합니다."
        ),
        "gage_rr_interaction_not_pooled": (
            "부품-측정자 interaction은 pooling하지 않고 별도 component로 보존했습니다."
        ),
        "gage_rr_independence_not_proven": (
            "부품 선정, 측정자 독립성, 반복 측정 순서는 소프트웨어가 증명할 수 없습니다."
        ),
        "gage_rr_labels_redacted": (
            "부품, 측정자, 반복 식별값 원문은 결과 payload에 포함하지 않았습니다."
        ),
        "gage_rr_negative_variance_component_clamped": (
            "음수 raw variance component가 있어 final variance는 0으로 제한하고 "
            "raw estimate를 함께 기록했습니다."
        ),
        "missing_values_excluded": "측정값 결측 행은 complete-case 정책으로 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 측정값은 제외했습니다.",
        "gage_rr_identifier_missing_excluded": (
            "부품, 측정자, 반복 ID 결측 행은 complete-case 정책으로 제외했습니다."
        ),
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "gage_rr_balanced_crossed_anova_assumed": "info",
        "gage_rr_interaction_not_pooled": "info",
        "gage_rr_independence_not_proven": "info",
        "gage_rr_labels_redacted": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        warnings.append(
            AnalysisWarning(
                code=code,
                severity=severities.get(code, "warning"),
                message=message,
            ),
        )
    return warnings


def run_gage_run_chart_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Gage Run Chart 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_gage_run_chart_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    measurement_column_id = _gage_run_chart_required_column_id(
        options,
        "measurement_column_id",
    )
    part_column_id = _gage_run_chart_required_column_id(options, "part_column_id")
    operator_column_id = _gage_run_chart_required_column_id(options, "operator_column_id")
    replicate_column_id = _gage_run_chart_required_column_id(options, "replicate_column_id")
    missing_policy = _gage_run_chart_missing_policy(options)
    point_limit = _gage_run_chart_point_limit(options)
    measurement_column, part_column, operator_column, replicate_column = select_gage_rr_columns(
        context.columns,
        measurement_column_id=measurement_column_id,
        part_column_id=part_column_id,
        operator_column_id=operator_column_id,
        replicate_column_id=replicate_column_id,
    )
    order_column = _selected_gage_run_chart_order_column(
        context,
        options,
        excluded_column_ids={
            measurement_column.column_id,
            part_column.column_id,
            operator_column.column_id,
            replicate_column.column_id,
        },
    )
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
            result = calculate_gage_run_chart(
                _iter_rows_for_snapshot(context, row_snapshot),
                measurement_column=_gage_run_chart_column_payload(measurement_column),
                part_column=_gage_run_chart_column_payload(part_column),
                operator_column=_gage_run_chart_column_payload(operator_column),
                replicate_column=_gage_run_chart_column_payload(replicate_column),
                order_column=(
                    _gage_run_chart_column_payload(order_column)
                    if order_column is not None
                    else None
                ),
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                missing_policy=missing_policy,
                point_limit=point_limit,
            )
        except GageRunChartError as exc:
            raise _gage_run_chart_api_error(exc.code) from exc
        warnings = _gage_run_chart_warnings(result)
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


def _validate_gage_run_chart_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return GageRunChartOptions.model_validate(options).model_dump(exclude_none=True)
    except ValidationError as exc:
        raise ApiError(
            code="invalid_gage_run_chart_options",
            message="Gage Run Chart 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _select_gage_run_chart_columns(
    columns: list[DatasetColumnRecord],
    *,
    measurement_column_id: str,
    part_column_id: str,
    operator_column_id: str,
    replicate_column_id: str,
) -> tuple[DatasetColumnRecord, DatasetColumnRecord, DatasetColumnRecord, DatasetColumnRecord]:
    selected_column_ids = [
        measurement_column_id,
        part_column_id,
        operator_column_id,
        replicate_column_id,
    ]
    if len(set(selected_column_ids)) != len(selected_column_ids):
        raise ApiError(
            code="gage_run_chart_distinct_columns_required",
            message="Gage Run Chart 측정값, 부품, 측정자, 반복 컬럼은 서로 달라야 합니다.",
        )
    return (
        _selected_gage_run_chart_measurement_column(columns, measurement_column_id),
        _selected_gage_run_chart_identifier_column(columns, part_column_id, "part"),
        _selected_gage_run_chart_identifier_column(columns, operator_column_id, "operator"),
        _selected_gage_run_chart_identifier_column(columns, replicate_column_id, "replicate"),
    )


def _selected_gage_run_chart_measurement_column(
    columns: list[DatasetColumnRecord],
    column_id: str,
) -> DatasetColumnRecord:
    column = next((candidate for candidate in columns if candidate.column_id == column_id), None)
    if column is None:
        raise ApiError(
            code="gage_run_chart_measurement_column_not_found",
            message="요청한 Gage Run Chart 측정값 컬럼을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="gage_run_chart_measurement_column_not_numeric",
            message="Gage Run Chart 측정값은 현재 숫자형 컬럼만 지원합니다.",
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="gage_run_chart_measurement_column_is_id",
            message="ID 컬럼은 Gage Run Chart 측정값으로 사용할 수 없습니다.",
        )
    return column


def _selected_gage_run_chart_identifier_column(
    columns: list[DatasetColumnRecord],
    column_id: str,
    role_name: str,
) -> DatasetColumnRecord:
    column = next((candidate for candidate in columns if candidate.column_id == column_id), None)
    if column is None:
        raise ApiError(
            code=f"gage_run_chart_{role_name}_column_not_found",
            message="요청한 Gage Run Chart 식별 컬럼을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if column.data_type not in {"integer", "decimal", "text", "boolean"}:
        raise ApiError(
            code=f"gage_run_chart_{role_name}_column_not_supported",
            message=(
                "Gage Run Chart 부품, 측정자, 반복 컬럼은 현재 숫자, 텍스트, "
                "boolean만 지원합니다."
            ),
        )
    return column


def _gage_run_chart_required_column_id(options: dict[str, Any], key: str) -> str:
    raw_value = options.get(key)
    if isinstance(raw_value, str) and raw_value:
        return raw_value
    codes = {
        "measurement_column_id": "gage_run_chart_measurement_column_required",
        "part_column_id": "gage_run_chart_part_column_required",
        "operator_column_id": "gage_run_chart_operator_column_required",
        "replicate_column_id": "gage_run_chart_replicate_column_required",
    }
    messages = {
        "measurement_column_id": "Gage Run Chart 측정값 컬럼을 선택해야 합니다.",
        "part_column_id": "Gage Run Chart 부품 컬럼을 선택해야 합니다.",
        "operator_column_id": "Gage Run Chart 측정자 컬럼을 선택해야 합니다.",
        "replicate_column_id": "Gage Run Chart 반복 컬럼을 선택해야 합니다.",
    }
    raise ApiError(code=codes[key], message=messages[key])


def _selected_gage_run_chart_order_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
    *,
    excluded_column_ids: set[str],
) -> DatasetColumnRecord | None:
    order_column_id = options.get("order_column_id")
    if order_column_id is None or order_column_id == "":
        return None
    if not isinstance(order_column_id, str):
        raise ApiError(
            code="invalid_gage_run_chart_order_column",
            message="Gage Run Chart 순서 컬럼 ID가 올바르지 않습니다.",
        )
    if order_column_id in excluded_column_ids:
        raise ApiError(
            code="gage_run_chart_order_column_conflicts_with_role",
            message="Gage Run Chart 순서 컬럼은 측정값/부품/측정자/반복 컬럼과 달라야 합니다.",
        )
    columns_by_id = {column.column_id: column for column in context.columns}
    column = columns_by_id.get(order_column_id)
    if column is None:
        raise ApiError(
            code="gage_run_chart_order_column_not_found",
            message="요청한 Gage Run Chart 순서 컬럼을 찾을 수 없습니다.",
        )
    if column.data_type not in {"integer", "decimal", "datetime"}:
        raise ApiError(
            code="gage_run_chart_order_column_unsupported_type",
            message="Gage Run Chart 순서 컬럼은 현재 숫자형 또는 날짜시간 컬럼만 지원합니다.",
        )
    return column


def _gage_run_chart_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="gage_run_chart_missing_policy_unsupported",
            message="Gage Run Chart는 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _gage_run_chart_point_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("point_limit", 1000)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_gage_run_chart_point_limit",
            message="Gage Run Chart point limit이 올바르지 않습니다.",
        )
    if raw_value <= 0 or raw_value > MAX_RUN_CHART_POINT_LIMIT:
        raise ApiError(
            code="invalid_gage_run_chart_point_limit",
            message="Gage Run Chart point limit이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _gage_run_chart_column_payload(column: DatasetColumnRecord) -> GageRunChartColumn:
    return GageRunChartColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _gage_run_chart_api_error(code: str) -> ApiError:
    messages = {
        "gage_run_chart_missing_policy_unsupported": (
            "Gage Run Chart는 현재 complete-case 결측 처리만 지원합니다."
        ),
        "invalid_gage_run_chart_point_limit": (
            "Gage Run Chart point limit이 허용 범위를 벗어났습니다."
        ),
        "gage_run_chart_no_usable_measurements": (
            "Gage Run Chart에 사용할 수 있는 측정 행이 없습니다."
        ),
        "gage_run_chart_part_count_too_small": ("Gage Run Chart에는 최소 2개 부품이 필요합니다."),
        "gage_run_chart_operator_count_too_small": (
            "Gage Run Chart에는 최소 2명 이상의 측정자가 필요합니다."
        ),
        "gage_run_chart_replicate_count_too_small": (
            "Gage Run Chart에는 각 부품-측정자 조합당 최소 2회 반복이 필요합니다."
        ),
        "gage_run_chart_crossed_cells_missing": (
            "Gage Run Chart는 현재 모든 부품-측정자 조합이 있는 crossed 설계만 지원합니다."
        ),
        "gage_run_chart_unbalanced_crossed_design": (
            "Gage Run Chart는 현재 모든 부품-측정자 조합의 반복 ID가 같은 "
            "balanced crossed 설계만 지원합니다."
        ),
        "gage_run_chart_duplicate_replicates_per_cell": (
            "같은 부품-측정자 조합 안에 중복 반복 ID가 있습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Gage Run Chart를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _gage_run_chart_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []
    messages = {
        "gage_run_chart_diagnostic_only": (
            "Gage Run Chart는 측정시스템 패턴을 보는 진단 차트이며 Gage R&R "
            "분산성분 결과를 대체하지 않습니다."
        ),
        "gage_run_chart_requires_gage_design": (
            "단순 Run Chart로 자동 전환하지 않고 Gage 설계 역할과 균형성을 요구했습니다."
        ),
        "gage_run_chart_labels_redacted": (
            "부품, 측정자, 반복 식별값 원문은 결과 payload에 포함하지 않았습니다."
        ),
        "gage_run_chart_uses_canonical_row_order": (
            "순서 컬럼이 없어 canonical row 순서를 Gage Run Chart 순서로 사용했습니다."
        ),
        "gage_run_chart_uses_order_column": (
            "선택한 순서 컬럼을 오름차순으로 정렬하고 canonical row position으로 "
            "동률을 정렬했습니다."
        ),
        "missing_values_excluded": "측정값 결측 행은 complete-case 정책으로 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 측정값은 제외했습니다.",
        "gage_run_chart_identifier_missing_excluded": (
            "부품, 측정자, 반복 ID 결측 행은 complete-case 정책으로 제외했습니다."
        ),
        "gage_run_chart_order_missing_excluded": (
            "순서 컬럼 결측 행은 complete-case 정책으로 제외했습니다."
        ),
        "gage_run_chart_order_invalid_excluded": (
            "순서 컬럼 값이 현재 지원 형식으로 해석되지 않아 제외했습니다."
        ),
        "gage_run_chart_points_truncated": (
            "Gage Run Chart point payload는 결정적 방식으로 제한했습니다."
        ),
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "gage_run_chart_diagnostic_only": "info",
        "gage_run_chart_requires_gage_design": "info",
        "gage_run_chart_labels_redacted": "info",
        "gage_run_chart_uses_canonical_row_order": "info",
        "gage_run_chart_uses_order_column": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        warnings.append(
            AnalysisWarning(
                code=code,
                severity=severities.get(code, "warning"),
                message=message,
            ),
        )
    return warnings


def run_run_chart_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="런 차트 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_run_chart_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    value_column = _selected_run_chart_column(context, options)
    order_column = _selected_run_chart_order_column(context, options, value_column)
    center_method = _run_chart_center_method(options)
    missing_policy = _run_chart_missing_policy(options)
    trend_min_length = _run_chart_trend_min_length(options)
    oscillation_min_length = _run_chart_oscillation_min_length(options)
    runs_test_alpha = _run_chart_runs_test_alpha(options)
    point_limit = _run_chart_point_limit(options)
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
            result = calculate_run_chart(
                _iter_rows_for_snapshot(context, row_snapshot),
                value_column,
                order_column=order_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                center_method=center_method,
                missing_policy=missing_policy,
                trend_min_length=trend_min_length,
                oscillation_min_length=oscillation_min_length,
                runs_test_alpha=runs_test_alpha,
                point_limit=point_limit,
            )
        except RunChartError as exc:
            raise _run_chart_api_error(exc.code) from exc
        warnings = _run_chart_warnings(result)
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


def _validate_run_chart_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return RunChartOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_run_chart_options",
            message="런 차트 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_run_chart_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> RunChartColumn:
    value_column_id = options.get("value_column_id")
    if not isinstance(value_column_id, str) or not value_column_id:
        raise ApiError(
            code="run_chart_value_column_required",
            message="런 차트 측정값 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    column = columns_by_id.get(value_column_id)
    if column is None:
        raise ApiError(
            code="run_chart_value_column_not_found",
            message="요청한 런 차트 측정값 컬럼을 찾을 수 없습니다.",
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="run_chart_value_column_is_id",
            message="ID 컬럼은 런 차트 측정값으로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="run_chart_value_column_not_numeric",
            message="런 차트 측정값은 현재 숫자형 컬럼만 지원합니다.",
        )
    return RunChartColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _selected_run_chart_order_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
    value_column: RunChartColumn,
) -> RunChartColumn | None:
    order_column_id = options.get("order_column_id")
    if order_column_id is None or order_column_id == "":
        return None
    if not isinstance(order_column_id, str):
        raise ApiError(
            code="invalid_run_chart_order_column",
            message="런 차트 순서 컬럼 ID가 올바르지 않습니다.",
        )
    if order_column_id == value_column.column_id:
        raise ApiError(
            code="run_chart_order_column_same_as_value",
            message="런 차트 순서 컬럼은 측정값 컬럼과 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    column = columns_by_id.get(order_column_id)
    if column is None:
        raise ApiError(
            code="run_chart_order_column_not_found",
            message="요청한 런 차트 순서 컬럼을 찾을 수 없습니다.",
        )
    if column.data_type not in RUN_CHART_ORDER_DATA_TYPES:
        raise ApiError(
            code="run_chart_order_column_not_numeric",
            message="런 차트 순서 컬럼은 현재 숫자형 또는 날짜시간 컬럼만 지원합니다.",
        )
    return RunChartColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _run_chart_center_method(options: dict[str, Any]) -> str:
    raw_value = options.get("center_method", "median")
    if raw_value != "median":
        raise ApiError(
            code="invalid_run_chart_center_method",
            message="런 차트 중심선은 현재 median만 지원합니다.",
        )
    return raw_value


def _run_chart_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="run_chart_missing_policy_unsupported",
            message="런 차트는 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _run_chart_trend_min_length(options: dict[str, Any]) -> int:
    raw_value = options.get("trend_min_length", 6)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_run_chart_trend_min_length",
            message="런 차트 trend rule 길이가 올바르지 않습니다.",
        )
    if raw_value < 3 or raw_value > 20:
        raise ApiError(
            code="invalid_run_chart_trend_min_length",
            message="런 차트 trend rule 길이가 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _run_chart_oscillation_min_length(options: dict[str, Any]) -> int:
    raw_value = options.get("oscillation_min_length", 14)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_run_chart_oscillation_min_length",
            message="런 차트 oscillation rule 길이가 올바르지 않습니다.",
        )
    if raw_value < 4 or raw_value > 30:
        raise ApiError(
            code="invalid_run_chart_oscillation_min_length",
            message="런 차트 oscillation rule 길이가 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _run_chart_runs_test_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("runs_test_alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_run_chart_runs_test_alpha",
            message="런 차트 runs test 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if not isfinite(alpha) or alpha <= 0 or alpha >= 0.5:
        raise ApiError(
            code="invalid_run_chart_runs_test_alpha",
            message="런 차트 runs test 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _run_chart_point_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("point_limit", 1000)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_run_chart_point_limit",
            message="런 차트 point limit이 올바르지 않습니다.",
        )
    if raw_value <= 0 or raw_value > MAX_RUN_CHART_POINT_LIMIT:
        raise ApiError(
            code="invalid_run_chart_point_limit",
            message="런 차트 point limit이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _run_chart_api_error(code: str) -> ApiError:
    messages = {
        "invalid_run_chart_options": "런 차트 옵션 계약이 올바르지 않습니다.",
        "invalid_run_chart_center_method": "런 차트 중심선은 현재 median만 지원합니다.",
        "run_chart_missing_policy_unsupported": (
            "런 차트는 현재 complete-case 결측 처리만 지원합니다."
        ),
        "invalid_run_chart_tie_policy": "런 차트 tie 처리 정책이 올바르지 않습니다.",
        "invalid_run_chart_trend_min_length": "런 차트 trend rule 길이가 허용 범위를 벗어났습니다.",
        "invalid_run_chart_oscillation_min_length": (
            "런 차트 oscillation rule 길이가 허용 범위를 벗어났습니다."
        ),
        "invalid_run_chart_runs_test_alpha": (
            "런 차트 runs test 유의수준이 허용 범위를 벗어났습니다."
        ),
        "invalid_run_chart_point_limit": "런 차트 point limit이 허용 범위를 벗어났습니다.",
        "invalid_run_chart_order_column": "런 차트 순서 컬럼 ID가 올바르지 않습니다.",
        "run_chart_order_column_same_as_value": (
            "런 차트 순서 컬럼은 측정값 컬럼과 달라야 합니다."
        ),
        "run_chart_order_column_not_found": "요청한 런 차트 순서 컬럼을 찾을 수 없습니다.",
        "run_chart_order_column_not_numeric": (
            "런 차트 순서 컬럼은 현재 숫자형 또는 날짜시간 컬럼만 지원합니다."
        ),
        "run_chart_order_mixed_timezone_awareness": (
            "런 차트 날짜시간 순서 컬럼에 timezone 포함 값과 미포함 값이 섞여 있습니다."
        ),
        "run_chart_n_too_small": "런 차트에는 사용 가능한 숫자 값이 최소 3개 필요합니다.",
        "run_chart_all_values_tied_to_center": (
            "모든 값이 중심선과 같아 런 차트 run을 계산할 수 없습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "런 차트를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _run_chart_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "run_chart_not_control_chart": (
            "런 차트는 관리한계를 계산하지 않으며, 신호를 관리도 out-of-control로 "
            "해석하지 않습니다."
        ),
        "run_chart_uses_canonical_row_order": (
            "이번 slice의 런 차트는 canonical row 순서를 실행 순서로 사용합니다."
        ),
        "run_chart_uses_numeric_order_column": (
            "런 차트는 선택한 숫자형 순서 컬럼을 오름차순으로 정렬해 실행 순서로 사용합니다."
        ),
        "run_chart_uses_datetime_order_column": (
            "런 차트는 선택한 날짜시간 순서 컬럼을 오름차순으로 정렬해 실행 순서로 사용합니다."
        ),
        "run_chart_trend_rule_defined": (
            "trend 신호는 연속 6개 이상 값이 엄격히 증가하거나 감소할 때만 표시합니다."
        ),
        "run_chart_oscillation_rule_defined": (
            "oscillation 신호는 연속 값의 증가/감소 방향이 엄격히 교대할 때만 표시합니다."
        ),
        "run_chart_runs_test_defined": (
            "clustering/mixture 신호는 median 위/아래 run 개수의 exact 조건부 분포로만 "
            "평가합니다."
        ),
        "run_chart_runs_test_unavailable": (
            "above/below 한쪽이 없거나 exact 계산 한도를 넘어 clustering/mixture 신호를 "
            "계산하지 않았습니다."
        ),
        "missing_values_excluded": "측정값 결측 행은 complete-case 정책으로 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 측정값은 제외했습니다.",
        "run_chart_order_missing_excluded": (
            "순서 컬럼 결측 행은 complete-case 정책으로 제외했습니다."
        ),
        "run_chart_order_non_numeric_excluded": (
            "숫자로 해석할 수 없는 순서 컬럼 값은 제외했습니다."
        ),
        "run_chart_order_invalid_datetime_excluded": (
            "날짜시간으로 해석할 수 없는 순서 컬럼 값은 제외했습니다."
        ),
        "run_chart_order_ties_stable_sorted": (
            "순서 컬럼 값이 같은 행은 canonical row position으로 안정 정렬했습니다."
        ),
        "run_chart_ties_excluded_from_runs": (
            "중심선과 같은 값은 차트에는 표시하지만 above/below run 계산에서는 제외했습니다."
        ),
        "run_chart_trend_signal_detected": "명시 정의된 trend 신호가 감지되었습니다.",
        "run_chart_oscillation_signal_detected": ("명시 정의된 oscillation 신호가 감지되었습니다."),
        "run_chart_clustering_signal_detected": (
            "median 위/아래 run 개수가 exact 분포의 낮은 꼬리에 있어 "
            "clustering 신호로 표시했습니다."
        ),
        "run_chart_mixture_signal_detected": (
            "median 위/아래 run 개수가 exact 분포의 높은 꼬리에 있어 mixture 신호로 표시했습니다."
        ),
        "run_chart_points_truncated": "런 차트 point payload는 결정적 방식으로 제한했습니다.",
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "run_chart_not_control_chart": "info",
        "run_chart_uses_canonical_row_order": "info",
        "run_chart_uses_numeric_order_column": "info",
        "run_chart_uses_datetime_order_column": "info",
        "run_chart_order_ties_stable_sorted": "info",
        "run_chart_trend_rule_defined": "info",
        "run_chart_oscillation_rule_defined": "info",
        "run_chart_runs_test_defined": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        warnings.append(
            AnalysisWarning(
                code=code,
                severity=severities.get(code, "warning"),
                message=message,
            ),
        )
    return warnings
