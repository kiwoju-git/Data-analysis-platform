from typing import Any, Literal
from uuid import uuid4

from fastapi import status
from pydantic import ValidationError

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisWarning,
    AttributeControlChartOptions,
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
from app.services.attribute_control_limit_sets import get_attribute_control_limit_set
from app.services.attribute_control_phase_2 import (
    phase_2_dependency_payloads,
    validate_attribute_control_phase_2_target,
)
from app.services.dataset_rows import DatasetRowsContext, get_dataset_rows_context
from app.statistics.attribute_control_chart import (
    AttributeControlChartColumn,
    AttributeControlChartError,
    calculate_attribute_control_chart,
    calculate_attribute_control_chart_phase_2,
)
from app.storage.metadata import DatasetColumnRecord

MAX_ATTRIBUTE_CHART_POINT_LIMIT = 5000


def run_attribute_control_chart_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="계수형 관리도 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    count_column = _selected_count_column(context, options)
    denominator_column = _selected_denominator_column(context, options, count_column)
    point_limit = _point_limit(options)
    limit_set = None
    if options["phase"] == "phase_2":
        limit_set_id = options.get("limit_set_id")
        if limit_set_id is None:
            raise _api_error("attribute_control_chart_limit_set_required")
        limit_set = get_attribute_control_limit_set(settings, limit_set_id)
        validate_attribute_control_phase_2_target(
            asset=limit_set,
            context=context,
            chart_type=str(options["chart_type"]),
            count_definition=str(options["count_definition"]),
            count_column_id=count_column.column_id,
            denominator_column_id=(
                None if denominator_column is None else denominator_column.column_id
            ),
            constant_opportunity_confirmed=bool(options["constant_opportunity_confirmed"]),
        )
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
            if limit_set is None:
                result = calculate_attribute_control_chart(
                    iter_rows_for_snapshot(context, row_snapshot),
                    count_column,
                    denominator_column,
                    chart_type=str(options["chart_type"]),
                    count_definition=str(options["count_definition"]),
                    constant_opportunity_confirmed=bool(options["constant_opportunity_confirmed"]),
                    decimal=context.parsing.decimal,
                    thousands=context.parsing.thousands,
                    missing_policy=str(options["missing_policy"]),
                    point_limit=point_limit,
                )
                result["schema_version"] = 2
                result["phase"] = "phase_1"
                result["limit_set_dependency"] = None
            else:
                result = calculate_attribute_control_chart_phase_2(
                    iter_rows_for_snapshot(context, row_snapshot),
                    count_column,
                    denominator_column,
                    chart_type=str(options["chart_type"]),
                    count_definition=str(options["count_definition"]),
                    frozen_center_line=limit_set.frozen_center_line,
                    fixed_sample_size=limit_set.fixed_sample_size,
                    constant_opportunity_confirmed=bool(options["constant_opportunity_confirmed"]),
                    decimal=context.parsing.decimal,
                    thousands=context.parsing.thousands,
                    missing_policy=str(options["missing_policy"]),
                    point_limit=point_limit,
                )
                limit_dependency, target_dependency = phase_2_dependency_payloads(
                    asset=limit_set,
                    context=context,
                    row_snapshot=row_snapshot,
                    count_column_id=count_column.column_id,
                    denominator_column_id=(
                        None if denominator_column is None else denominator_column.column_id
                    ),
                )
                result["limit_set_dependency"] = limit_dependency
                result["target_dependency"] = target_dependency
        except AttributeControlChartError as exc:
            raise _api_error(exc.code) from exc
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return AttributeControlChartOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_attribute_control_chart_options",
            message="계수형 관리도 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_count_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> AttributeControlChartColumn:
    column_id = options.get("count_column_id")
    if not isinstance(column_id, str) or not column_id:
        raise ApiError(
            code="attribute_control_chart_count_column_required",
            message="계수형 관리도의 결함 또는 불량 수 컬럼을 선택해야 합니다.",
        )
    column = _column_by_id(context, column_id)
    if column is None:
        raise ApiError(
            code="attribute_control_chart_count_column_not_found",
            message="요청한 계수형 관리도 계수 컬럼을 찾을 수 없습니다.",
        )
    _validate_numeric_column(column, purpose="count")
    return _column_payload(column)


def _selected_denominator_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
    count_column: AttributeControlChartColumn,
) -> AttributeControlChartColumn | None:
    chart_type = options.get("chart_type")
    column_id = options.get("denominator_column_id")
    if chart_type == "c":
        if column_id is not None:
            raise _api_error("attribute_control_chart_c_denominator_not_allowed")
        return None
    if not isinstance(column_id, str) or not column_id:
        raise _api_error("attribute_control_chart_denominator_required")
    if column_id == count_column.column_id:
        raise ApiError(
            code="attribute_control_chart_denominator_same_as_count",
            message="계수와 표본 크기/검사 기회 컬럼은 달라야 합니다.",
        )
    column = _column_by_id(context, column_id)
    if column is None:
        raise ApiError(
            code="attribute_control_chart_denominator_column_not_found",
            message="요청한 표본 크기 또는 검사 기회 컬럼을 찾을 수 없습니다.",
        )
    _validate_numeric_column(column, purpose="denominator")
    return _column_payload(column)


def _column_by_id(
    context: DatasetRowsContext,
    column_id: str,
) -> DatasetColumnRecord | None:
    return next((column for column in context.columns if column.column_id == column_id), None)


def _validate_numeric_column(column: DatasetColumnRecord, *, purpose: str) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"attribute_control_chart_{purpose}_column_is_id",
            message="ID 컬럼은 계수형 관리도의 계수 또는 분모로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"attribute_control_chart_{purpose}_column_not_numeric",
            message="계수형 관리도의 계수와 분모는 숫자형 컬럼이어야 합니다.",
        )


def _column_payload(column: DatasetColumnRecord) -> AttributeControlChartColumn:
    return AttributeControlChartColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _point_limit(options: dict[str, Any]) -> int:
    value = options.get("point_limit", 1000)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _api_error("invalid_attribute_control_chart_point_limit")
    if value <= 0 or value > MAX_ATTRIBUTE_CHART_POINT_LIMIT:
        raise _api_error("invalid_attribute_control_chart_point_limit")
    return value


def _api_error(code: str) -> ApiError:
    messages = {
        "attribute_control_chart_type_unsupported": "P, NP, C, U 관리도 중 하나를 선택해야 합니다.",
        "attribute_control_chart_count_definition_mismatch": (
            "P/NP는 불량품 수, C/U는 결점 수로 정의해야 합니다."
        ),
        "attribute_control_chart_denominator_required": (
            "P/NP에는 표본 크기, U에는 검사 기회 컬럼이 필요합니다."
        ),
        "attribute_control_chart_c_denominator_not_allowed": (
            "C 관리도는 동일한 검사 기회를 전제로 하므로 분모 컬럼을 사용하지 않습니다."
        ),
        "attribute_control_chart_c_constant_opportunity_required": (
            "C 관리도 실행 전 모든 관측의 검사 기회가 같음을 확인해야 합니다."
        ),
        "attribute_control_chart_missing_policy_unsupported": (
            "계수형 관리도는 현재 complete-case 결측 처리만 지원합니다."
        ),
        "invalid_attribute_control_chart_point_limit": (
            "계수형 관리도 point limit이 허용 범위를 벗어났습니다."
        ),
        "attribute_control_chart_negative_count": (
            "결함 또는 불량 수에는 음수를 사용할 수 없습니다."
        ),
        "attribute_control_chart_non_integer_count": (
            "결함 또는 불량 수는 0 이상의 정수여야 합니다."
        ),
        "attribute_control_chart_count_not_finite": ("결함 또는 불량 수는 유한한 정수여야 합니다."),
        "attribute_control_chart_denominator_not_positive": (
            "표본 크기 또는 검사 기회는 0보다 커야 합니다."
        ),
        "attribute_control_chart_denominator_not_finite": (
            "표본 크기 또는 검사 기회는 유한한 숫자여야 합니다."
        ),
        "attribute_control_chart_sample_size_not_integer": (
            "P/NP 관리도의 표본 크기는 양의 정수여야 합니다."
        ),
        "attribute_control_chart_defectives_exceed_sample_size": (
            "불량품 수는 해당 관측의 표본 크기를 초과할 수 없습니다."
        ),
        "attribute_control_chart_point_count_too_small": (
            "계수형 관리도에는 필터와 제외 후 유효 관측이 최소 2개 필요합니다."
        ),
        "attribute_control_chart_np_varying_sample_size": (
            "NP 관리도는 모든 관측의 표본 크기가 같아야 합니다. "
            "가변 표본 크기에는 P 관리도를 선택하세요."
        ),
        "attribute_control_chart_zero_variation": (
            "기준선의 추정 분산이 0이라 관리한계를 계산할 수 없습니다."
        ),
        "attribute_control_chart_center_invalid": "계수형 관리도 중심선을 계산할 수 없습니다.",
        "attribute_control_chart_limit_set_required": (
            "Phase II 관리도에는 검증된 limit set이 필요합니다."
        ),
        "attribute_control_chart_phase_2_np_sample_size_mismatch": (
            "NP Phase II 대상의 모든 표본 크기는 기준선의 고정 표본 크기와 같아야 합니다."
        ),
        "attribute_control_chart_phase_2_c_opportunity_confirmation_required": (
            "C Phase II 대상의 검사 기회가 기준선과 동일함을 확인해야 합니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "계수형 관리도를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    codes = result.get("warnings")
    if not isinstance(codes, list):
        return []
    messages = {
        "attribute_control_chart_uses_canonical_row_order": (
            "관측점은 필터 후 canonical row 순서로 표시됩니다."
        ),
        "attribute_control_chart_phase_1_limits_estimated_from_data": (
            "Phase I 중심선과 3-sigma 관리한계는 필터 후 유효 관측 전체에서 추정했습니다."
        ),
        "attribute_control_chart_phase_2_limits_frozen_from_verified_asset": (
            "중심선과 3-sigma 관리한계는 검증된 immutable limit set에서 고정 적용되었습니다."
        ),
        "attribute_control_chart_process_assumptions_not_proven": (
            "관측 독립성, 시간 순서, 공정 안정성, 결함 기회의 동질성은 "
            "사용자가 설계상 확인해야 합니다."
        ),
        "attribute_control_chart_c_constant_opportunity_user_confirmed": (
            "C 관리도는 모든 관측의 검사 기회가 같다는 사용자 확인을 기록했습니다."
        ),
        "attribute_control_chart_baseline_small": (
            "Phase I 기준선 유효점이 20개 미만이므로 관리한계 추정의 불확실성이 큽니다."
        ),
        "attribute_control_chart_normal_approximation_weak": (
            "일부 관측에서 3-sigma 정규근사의 기대 계수가 작아 관리한계 해석에 주의가 필요합니다."
        ),
        "attribute_control_chart_overdispersion_detected": (
            "Pearson dispersion ratio가 2를 초과했습니다. 군집, 기회 차이 또는 "
            "공정 혼합을 검토하세요. 관리한계는 자동 보정하지 않았습니다."
        ),
        "attribute_control_chart_lcl_truncated_to_zero": (
            "자연 하한보다 낮은 LCL은 0으로 절단했습니다."
        ),
        "attribute_control_chart_ucl_truncated_to_natural_bound": (
            "P/NP UCL이 자연 상한을 넘는 경우 비율 1 또는 표본 크기로 절단했습니다."
        ),
        "attribute_control_chart_missing_count_excluded": (
            "계수 컬럼 결측 행은 complete-case 정책으로 제외했습니다."
        ),
        "attribute_control_chart_non_numeric_count_excluded": (
            "숫자로 해석할 수 없는 계수 값은 제외하고 제외 수를 기록했습니다."
        ),
        "attribute_control_chart_missing_denominator_excluded": (
            "표본 크기/검사 기회 결측 행은 complete-case 정책으로 제외했습니다."
        ),
        "attribute_control_chart_non_numeric_denominator_excluded": (
            "숫자로 해석할 수 없는 표본 크기/검사 기회 값은 제외하고 제외 수를 기록했습니다."
        ),
        "attribute_control_chart_limit_signal_detected": (
            "3-sigma 관리한계 밖 관측점이 감지되었습니다. 원인을 확인하세요."
        ),
        "attribute_control_chart_points_truncated": (
            "계수형 관리도 point payload는 결정적 방식으로 제한했습니다."
        ),
    }
    info_codes = {
        "attribute_control_chart_uses_canonical_row_order",
        "attribute_control_chart_phase_1_limits_estimated_from_data",
        "attribute_control_chart_phase_2_limits_frozen_from_verified_asset",
        "attribute_control_chart_process_assumptions_not_proven",
        "attribute_control_chart_c_constant_opportunity_user_confirmed",
    }
    warnings: list[AnalysisWarning] = []
    for code in codes:
        if not isinstance(code, str) or code not in messages:
            continue
        severity: Literal["info", "warning", "error"] = "info" if code in info_codes else "warning"
        warnings.append(AnalysisWarning(code=code, severity=severity, message=messages[code]))
    return warnings
