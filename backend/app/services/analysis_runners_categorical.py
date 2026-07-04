from math import isfinite
from typing import Any
from uuid import uuid4

from fastapi import status
from pydantic import ValidationError

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisWarning,
    ChiSquareAssociationOptions,
    OneProportionOptions,
    TwoProportionOptions,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    create_row_snapshot_artifact,
    iter_rows_for_snapshot,
    remove_file_if_exists,
    store_succeeded_analysis_result,
    utc_now,
)
from app.services.dataset_rows import DatasetRowsContext, get_dataset_rows_context
from app.statistics.chi_square_association import (
    ChiSquareAssociationColumn,
    ChiSquareAssociationError,
    calculate_chi_square_association,
)
from app.statistics.one_proportion import (
    OneProportionColumn,
    OneProportionError,
    calculate_one_proportion,
)
from app.statistics.two_proportion import (
    TwoProportionError,
    TwoProportionGroupColumn,
    TwoProportionResponseColumn,
    calculate_two_proportion,
)
from app.storage.metadata import DatasetColumnRecord


def run_one_proportion_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="1-비율 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_one_proportion_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column = _selected_one_proportion_column(context, options)
    event_level = _one_proportion_event_level(options)
    null_proportion = _one_proportion_null_proportion(options)
    alpha = _one_proportion_alpha(options)
    confidence_level = _one_proportion_confidence_level(options)
    alternative = _one_proportion_alternative(options)
    ci_method = _one_proportion_ci_method(options)
    _one_proportion_missing_policy(options)
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
            result = calculate_one_proportion(
                iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                event_level=event_level,
                null_proportion=null_proportion,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
                ci_method=ci_method,
            )
        except OneProportionError as exc:
            raise _one_proportion_api_error(exc.code) from exc
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_one_proportion_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_one_proportion_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return OneProportionOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_one_proportion_options",
            message="1-비율 검정 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_one_proportion_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> OneProportionColumn:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="one_proportion_response_required",
            message="1-비율 검정 반응 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="one_proportion_response_column_not_found",
            message="요청한 1-비율 검정 반응 컬럼을 찾을 수 없습니다.",
        )
    if response_column.role == "id" or response_column.measurement_level == "id":
        raise ApiError(
            code="one_proportion_response_column_is_id",
            message="ID 컬럼은 1-비율 검정 반응 변수로 사용할 수 없습니다.",
        )
    return OneProportionColumn(
        column_id=response_column.column_id,
        column_index=response_column.column_index,
        display_name=response_column.display_name,
        data_type=response_column.data_type,
        measurement_level=response_column.measurement_level,
        role=response_column.role,
        unit=response_column.unit,
    )


def _one_proportion_event_level(options: dict[str, Any]) -> str:
    raw_value = options.get("event_level")
    if not isinstance(raw_value, str) or raw_value.strip() == "":
        raise ApiError(
            code="one_proportion_event_level_required",
            message="1-비율 검정 사건 수준을 입력해야 합니다.",
        )
    return raw_value.strip()


def _one_proportion_null_proportion(options: dict[str, Any]) -> float:
    raw_value = options.get("null_proportion", 0.5)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_proportion_null_proportion",
            message="1-비율 검정 기준 비율이 올바르지 않습니다.",
        )
    null_proportion = float(raw_value)
    if null_proportion <= 0.0 or null_proportion >= 1.0 or not isfinite(null_proportion):
        raise ApiError(
            code="invalid_one_proportion_null_proportion",
            message="1-비율 검정 기준 비율이 허용 범위를 벗어났습니다.",
        )
    return null_proportion


def _one_proportion_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_proportion_alpha",
            message="1-비율 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_one_proportion_alpha",
            message="1-비율 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _one_proportion_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_proportion_confidence_level",
            message="1-비율 검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise ApiError(
            code="invalid_one_proportion_confidence_level",
            message="1-비율 검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _one_proportion_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_one_proportion_alternative",
            message="1-비율 검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_proportion_ci_method(options: dict[str, Any]) -> str:
    raw_value = options.get("ci_method", "wilson")
    if raw_value not in {"wilson", "clopper_pearson"}:
        raise ApiError(
            code="invalid_one_proportion_ci_method",
            message="1-비율 검정 신뢰구간 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_proportion_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="one_proportion_missing_policy_unsupported",
            message="1-비율 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _one_proportion_api_error(code: str) -> ApiError:
    messages = {
        "invalid_one_proportion_options": "1-비율 검정 옵션 계약이 올바르지 않습니다.",
        "one_proportion_n_too_small": "1-비율 검정에는 최소 1개 사용 값이 필요합니다.",
        "one_proportion_requires_binary_column": (
            "1-비율 검정 반응 컬럼은 사건 수준과 하나의 비사건 수준만 포함해야 합니다."
        ),
        "one_proportion_p_value_not_finite": ("1-비율 검정 p-value가 유한하지 않습니다."),
        "one_proportion_ci_not_finite": ("1-비율 검정 신뢰구간이 유한하지 않습니다."),
        "invalid_one_proportion_alternative": "1-비율 검정 대립가설이 올바르지 않습니다.",
        "invalid_one_proportion_ci_method": "1-비율 검정 신뢰구간 방식이 올바르지 않습니다.",
        "invalid_one_proportion_null_proportion": (
            "1-비율 검정 기준 비율이 허용 범위를 벗어났습니다."
        ),
        "invalid_one_proportion_alpha": "1-비율 검정 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_one_proportion_confidence_level": (
            "1-비율 검정 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "one_proportion_event_level_required": "1-비율 검정 사건 수준을 입력해야 합니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "1-비율 검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _one_proportion_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "one_proportion_binary_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_proportion_binary_design_assumption",
                severity="info",
                message=(
                    "이 컬럼이 분석 목적상 이진 사건/비사건 변수라는 가정은 "
                    "사용자가 확인해야 합니다."
                ),
            ),
        )
    if "one_proportion_exact_binomial" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_proportion_exact_binomial",
                severity="info",
                message="p-value는 exact binomial test로 계산했습니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "event_level_not_observed" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="event_level_not_observed",
                severity="warning",
                message="선택한 사건 수준이 사용 데이터에서 관측되지 않았습니다.",
            ),
        )
    if "all_events_or_no_events" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="all_events_or_no_events",
                severity="info",
                message="사용 데이터가 모두 사건 또는 모두 비사건입니다.",
            ),
        )
    if "single_observed_level" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="single_observed_level",
                severity="info",
                message="사용 데이터에서 하나의 수준만 관측되었습니다.",
            ),
        )
    return warnings


def run_two_proportion_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="2-비율 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_two_proportion_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_two_proportion_columns(
        context,
        options,
    )
    event_level = _two_proportion_event_level(options)
    alpha = _two_proportion_alpha(options)
    confidence_level = _two_proportion_confidence_level(options)
    alternative = _two_proportion_alternative(options)
    _two_proportion_missing_policy(options)
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
            result = calculate_two_proportion(
                iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                event_level=event_level,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
            )
        except TwoProportionError as exc:
            raise _two_proportion_api_error(exc.code) from exc
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_two_proportion_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_two_proportion_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return TwoProportionOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_two_proportion_options",
            message="2-비율 검정 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_two_proportion_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[TwoProportionResponseColumn, TwoProportionGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="two_proportion_response_required",
            message="2-비율 검정 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="two_proportion_group_required",
            message="2-비율 검정 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="two_proportion_same_response_and_group",
            message="2-비율 검정 반응 컬럼과 그룹 컬럼은 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    group_column = columns_by_id.get(group_column_id)
    if response_column is None:
        raise ApiError(
            code="two_proportion_response_column_not_found",
            message="요청한 2-비율 검정 반응 컬럼을 찾을 수 없습니다.",
        )
    if group_column is None:
        raise ApiError(
            code="two_proportion_group_column_not_found",
            message="요청한 2-비율 검정 그룹 컬럼을 찾을 수 없습니다.",
        )
    if response_column.role == "id" or response_column.measurement_level == "id":
        raise ApiError(
            code="two_proportion_response_column_is_id",
            message="ID 컬럼은 2-비율 검정 반응 변수로 사용할 수 없습니다.",
        )
    if group_column.role == "id" or group_column.measurement_level == "id":
        raise ApiError(
            code="two_proportion_group_column_is_id",
            message="ID 컬럼은 2-비율 검정 그룹 변수로 사용할 수 없습니다.",
        )
    return (
        TwoProportionResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        TwoProportionGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _two_proportion_event_level(options: dict[str, Any]) -> str:
    raw_value = options.get("event_level")
    if not isinstance(raw_value, str) or raw_value.strip() == "":
        raise ApiError(
            code="two_proportion_event_level_required",
            message="2-비율 검정 사건 수준을 입력해야 합니다.",
        )
    return raw_value.strip()


def _two_proportion_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_proportion_alpha",
            message="2-비율 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_two_proportion_alpha",
            message="2-비율 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _two_proportion_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_proportion_confidence_level",
            message="2-비율 검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_two_proportion_confidence_level",
            message="2-비율 검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _two_proportion_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_two_proportion_alternative",
            message="2-비율 검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _two_proportion_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="two_proportion_missing_policy_unsupported",
            message="2-비율 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _two_proportion_api_error(code: str) -> ApiError:
    messages = {
        "invalid_two_proportion_options": "2-비율 검정 옵션 계약이 올바르지 않습니다.",
        "invalid_two_proportion_alternative": "2-비율 검정 대립가설이 올바르지 않습니다.",
        "invalid_two_proportion_alpha": "2-비율 검정 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_two_proportion_confidence_level": (
            "2-비율 검정 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "two_proportion_event_level_required": "2-비율 검정 사건 수준을 입력해야 합니다.",
        "two_proportion_requires_exactly_two_groups": (
            "2-비율 검정에는 정확히 2개의 사용 가능한 그룹이 필요합니다."
        ),
        "two_proportion_group_n_too_small": (
            "2-비율 검정의 각 그룹에는 최소 1개 사용 값이 필요합니다."
        ),
        "two_proportion_requires_binary_response": (
            "2-비율 검정 반응 컬럼은 사건 수준과 하나의 비사건 수준만 포함해야 합니다."
        ),
        "two_proportion_p_value_not_finite": "2-비율 검정 p-value가 유한하지 않습니다.",
        "two_proportion_ci_not_finite": "2-비율 검정 신뢰구간이 유한하지 않습니다.",
        "two_proportion_effect_ci_not_finite": (
            "2-비율 검정 효과크기 신뢰구간이 유한하지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "2-비율 검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _two_proportion_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "two_proportion_binary_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_proportion_binary_design_assumption",
                severity="info",
                message="반응 컬럼이 이진 사건/비사건 변수라는 가정은 사용자가 확인해야 합니다.",
            ),
        )
    if "two_proportion_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_proportion_independence_assumption",
                severity="info",
                message="두 그룹 관측치의 독립성은 설계 가정이며 자동 검증하지 않습니다.",
            ),
        )
    if "two_proportion_fisher_exact" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_proportion_fisher_exact",
                severity="info",
                message="p-value는 2x2 Fisher exact test로 계산했습니다.",
            ),
        )
    if "small_expected_counts" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_expected_counts",
                severity="info",
                message="기대도수가 작은 셀이 있어 exact test 결과와 설계를 함께 확인하세요.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 또는 그룹 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "zero_cell_effect_ci_unavailable" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="zero_cell_effect_ci_unavailable",
                severity="warning",
                message="0 cell이 있어 일부 효과크기 CI는 계산하지 않았습니다.",
            ),
        )
    if "event_level_not_observed" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="event_level_not_observed",
                severity="warning",
                message="선택한 사건 수준이 사용 데이터에서 관측되지 않았습니다.",
            ),
        )
    if "all_events_or_no_events" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="all_events_or_no_events",
                severity="info",
                message="사용 데이터가 모두 사건 또는 모두 비사건입니다.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계를 함께 확인하세요.",
            ),
        )
    return warnings


def run_chi_square_association_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="카이제곱 독립성 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    options = _validate_chi_square_association_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    row_column, column_column = _selected_chi_square_association_columns(
        context,
        options,
    )
    alpha = _chi_square_association_alpha(options)
    _chi_square_association_missing_policy(options)
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
            result = calculate_chi_square_association(
                iter_rows_for_snapshot(context, row_snapshot),
                row_column,
                column_column,
                alpha=alpha,
            )
        except ChiSquareAssociationError as exc:
            raise _chi_square_association_api_error(exc.code) from exc
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_chi_square_association_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_chi_square_association_options(options: dict[str, Any]) -> dict[str, Any]:
    try:
        return ChiSquareAssociationOptions.model_validate(options).model_dump()
    except ValidationError as exc:
        raise ApiError(
            code="invalid_chi_square_options",
            message="카이제곱 독립성 검정 옵션 계약이 올바르지 않습니다.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_chi_square_association_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[ChiSquareAssociationColumn, ChiSquareAssociationColumn]:
    row_column_id = options.get("row_column_id")
    column_column_id = options.get("column_column_id")
    if not isinstance(row_column_id, str) or not row_column_id:
        raise ApiError(
            code="chi_square_row_column_required",
            message="카이제곱 독립성 검정 행 변수를 선택해야 합니다.",
        )
    if not isinstance(column_column_id, str) or not column_column_id:
        raise ApiError(
            code="chi_square_column_column_required",
            message="카이제곱 독립성 검정 열 변수를 선택해야 합니다.",
        )
    if row_column_id == column_column_id:
        raise ApiError(
            code="chi_square_same_row_and_column",
            message="카이제곱 독립성 검정 행 변수와 열 변수는 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    row_column = columns_by_id.get(row_column_id)
    column_column = columns_by_id.get(column_column_id)
    if row_column is None:
        raise ApiError(
            code="chi_square_row_column_not_found",
            message="요청한 카이제곱 독립성 검정 행 변수를 찾을 수 없습니다.",
        )
    if column_column is None:
        raise ApiError(
            code="chi_square_column_column_not_found",
            message="요청한 카이제곱 독립성 검정 열 변수를 찾을 수 없습니다.",
        )
    _validate_chi_square_association_column(row_column, axis="row")
    _validate_chi_square_association_column(column_column, axis="column")
    return (
        ChiSquareAssociationColumn(
            column_id=row_column.column_id,
            column_index=row_column.column_index,
            display_name=row_column.display_name,
            data_type=row_column.data_type,
            measurement_level=row_column.measurement_level,
            role=row_column.role,
            unit=row_column.unit,
        ),
        ChiSquareAssociationColumn(
            column_id=column_column.column_id,
            column_index=column_column.column_index,
            display_name=column_column.display_name,
            data_type=column_column.data_type,
            measurement_level=column_column.measurement_level,
            role=column_column.role,
            unit=column_column.unit,
        ),
    )


def _validate_chi_square_association_column(
    column: DatasetColumnRecord,
    *,
    axis: str,
) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"chi_square_{axis}_column_is_id",
            message="ID 컬럼은 카이제곱 독립성 검정 변수로 사용할 수 없습니다.",
        )


def _chi_square_association_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_chi_square_alpha",
            message="카이제곱 독립성 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_chi_square_alpha",
            message="카이제곱 독립성 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _chi_square_association_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="chi_square_missing_policy_unsupported",
            message="카이제곱 독립성 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _chi_square_association_api_error(code: str) -> ApiError:
    messages = {
        "invalid_chi_square_options": "카이제곱 독립성 검정 옵션 계약이 올바르지 않습니다.",
        "invalid_chi_square_alpha": ("카이제곱 독립성 검정 유의수준이 허용 범위를 벗어났습니다."),
        "chi_square_requires_at_least_two_row_levels": (
            "카이제곱 독립성 검정에는 행 변수의 사용 가능한 수준이 최소 2개 필요합니다."
        ),
        "chi_square_requires_at_least_two_column_levels": (
            "카이제곱 독립성 검정에는 열 변수의 사용 가능한 수준이 최소 2개 필요합니다."
        ),
        "chi_square_too_many_row_levels": (
            "카이제곱 독립성 검정 행 변수 수준 수가 허용 범위를 초과했습니다."
        ),
        "chi_square_too_many_column_levels": (
            "카이제곱 독립성 검정 열 변수 수준 수가 허용 범위를 초과했습니다."
        ),
        "chi_square_statistic_not_finite": (
            "카이제곱 독립성 검정 통계량 또는 p-value가 유한하지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "카이제곱 독립성 검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _chi_square_association_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "chi_square_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="chi_square_independence_assumption",
                severity="info",
                message="관측치 독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "pearson_chi_square_no_continuity_correction" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_chi_square_no_continuity_correction",
                severity="info",
                message="Pearson 카이제곱 검정은 연속성 보정 없이 계산했습니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="행 또는 열 변수 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "small_expected_counts" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_expected_counts",
                severity="warning",
                message="기대도수가 작은 셀이 있어 카이제곱 근사 해석에 주의가 필요합니다.",
            ),
        )
    if "two_by_two_table" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_by_two_table",
                severity="info",
                message="2x2 분할표입니다. Fisher exact 검정 필요 여부를 함께 확인하세요.",
            ),
        )
    if "fisher_exact_recommended_for_sparse_2x2" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="fisher_exact_recommended_for_sparse_2x2",
                severity="warning",
                message=(
                    "희소한 2x2 분할표입니다. 이번 slice는 Fisher exact로 자동 전환하지 않고 "
                    "권장 대안으로만 기록합니다."
                ),
            ),
        )
    if "large_contingency_table" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="large_contingency_table",
                severity="info",
                message="분할표 셀 수가 많아 residual 해석과 표시 비용을 함께 확인하세요.",
            ),
        )
    return warnings
