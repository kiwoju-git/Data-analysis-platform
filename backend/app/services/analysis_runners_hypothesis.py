from math import isfinite
from typing import Any
from uuid import uuid4

from fastapi import status

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisWarning,
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
from app.statistics.equivalence_tost import (
    EquivalenceTostColumn,
    EquivalenceTostError,
    calculate_equivalence_tost,
)
from app.statistics.kruskal_wallis import (
    KruskalWallisError,
    KruskalWallisGroupColumn,
    KruskalWallisResponseColumn,
    calculate_kruskal_wallis,
)
from app.statistics.mann_whitney import (
    MannWhitneyError,
    MannWhitneyGroupColumn,
    MannWhitneyResponseColumn,
    calculate_mann_whitney,
)
from app.statistics.one_sample_t import (
    OneSampleTColumn,
    OneSampleTError,
    calculate_one_sample_t,
)
from app.statistics.one_sample_wilcoxon import (
    OneSampleWilcoxonColumn,
    OneSampleWilcoxonError,
    calculate_one_sample_wilcoxon,
)
from app.statistics.one_way_anova import (
    OneWayAnovaError,
    OneWayAnovaGroupColumn,
    OneWayAnovaResponseColumn,
    calculate_one_way_anova,
)
from app.statistics.paired_t import PairedTColumn, PairedTError, calculate_paired_t
from app.statistics.two_sample_t import (
    TwoSampleTError,
    TwoSampleTGroupColumn,
    TwoSampleTResponseColumn,
    calculate_two_sample_t,
)
from app.storage.metadata import (
    DatasetColumnRecord,
)


def run_one_sample_t_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="1-표본 t-검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column = _selected_one_sample_t_column(context, request.options)
    alpha = _one_sample_t_alpha(request.options)
    confidence_level = _one_sample_t_confidence_level(request.options)
    alternative = _one_sample_t_alternative(request.options)
    null_mean = _one_sample_t_null_mean(request.options)
    _one_sample_t_missing_policy(request.options)
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
            result = calculate_one_sample_t(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
                null_mean=null_mean,
            )
        except OneSampleTError as exc:
            raise _one_sample_t_api_error(exc.code) from exc
        warnings = _one_sample_t_warnings(result)
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


def _selected_one_sample_t_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> OneSampleTColumn:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="one_sample_t_response_required",
            message="1-표본 t-검정 반응 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="one_sample_t_response_column_not_found",
            message="요청한 1-표본 t-검정 반응 컬럼을 찾을 수 없습니다.",
        )

    _validate_one_sample_t_response_column(response_column)
    return OneSampleTColumn(
        column_id=response_column.column_id,
        column_index=response_column.column_index,
        display_name=response_column.display_name,
        data_type=response_column.data_type,
        measurement_level=response_column.measurement_level,
        role=response_column.role,
        unit=response_column.unit,
    )


def _validate_one_sample_t_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="one_sample_t_response_column_is_id",
            message="ID 컬럼은 1-표본 t-검정 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="one_sample_t_response_column_not_numeric",
            message="1-표본 t-검정 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _one_sample_t_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_t_alpha",
            message="1-표본 t-검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_one_sample_t_alpha",
            message="1-표본 t-검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _one_sample_t_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_t_confidence_level",
            message="1-표본 t-검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise ApiError(
            code="invalid_one_sample_t_confidence_level",
            message="1-표본 t-검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _one_sample_t_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_one_sample_t_alternative",
            message="1-표본 t-검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_sample_t_null_mean(options: dict[str, Any]) -> float:
    raw_value = options.get("null_mean", 0.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_t_null_mean",
            message="1-표본 t-검정 기준 평균이 올바르지 않습니다.",
        )
    null_mean = float(raw_value)
    if not isfinite(null_mean):
        raise ApiError(
            code="invalid_one_sample_t_null_mean",
            message="1-표본 t-검정 기준 평균이 유한하지 않습니다.",
        )
    return null_mean


def _one_sample_t_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="one_sample_t_missing_policy_unsupported",
            message="1-표본 t-검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _one_sample_t_api_error(code: str) -> ApiError:
    messages = {
        "one_sample_t_n_too_small": "1-표본 t-검정에는 최소 2개 사용 값이 필요합니다.",
        "one_sample_t_standard_error_zero": (
            "평균 차이의 표준오차가 0이어서 1-표본 t-검정을 계산할 수 없습니다."
        ),
        "invalid_one_sample_t_alternative": "1-표본 t-검정 대립가설이 올바르지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "1-표본 t-검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _one_sample_t_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "one_sample_t_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_t_design_assumption",
                severity="info",
                message="독립성 및 표본 설계는 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "one_sample_t_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_t_not_auto_switched",
                severity="info",
                message="정규성 진단 결과로 1-표본 t-검정을 자동 전환하지 않습니다.",
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
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    return warnings


def run_equivalence_tost_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="동등성 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column = _selected_equivalence_tost_column(context, request.options)
    design = _equivalence_tost_design(request.options)
    alpha = _equivalence_tost_alpha(request.options)
    reference_mean = _equivalence_tost_reference_mean(request.options)
    lower_bound = _equivalence_tost_lower_bound(request.options)
    upper_bound = _equivalence_tost_upper_bound(request.options)
    _equivalence_tost_missing_policy(request.options)
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
            result = calculate_equivalence_tost(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                design=design,
                reference_mean=reference_mean,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                alpha=alpha,
            )
        except EquivalenceTostError as exc:
            raise _equivalence_tost_api_error(exc.code) from exc
        warnings = _equivalence_tost_warnings(result)
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


def _selected_equivalence_tost_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> EquivalenceTostColumn:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="equivalence_tost_response_required",
            message="동등성 검정 반응 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="equivalence_tost_response_column_not_found",
            message="요청한 동등성 검정 반응 컬럼을 찾을 수 없습니다.",
        )

    _validate_equivalence_tost_response_column(response_column)
    return EquivalenceTostColumn(
        column_id=response_column.column_id,
        column_index=response_column.column_index,
        display_name=response_column.display_name,
        data_type=response_column.data_type,
        measurement_level=response_column.measurement_level,
        role=response_column.role,
        unit=response_column.unit,
    )


def _validate_equivalence_tost_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="equivalence_tost_response_column_is_id",
            message="ID 컬럼은 동등성 검정 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="equivalence_tost_response_column_not_numeric",
            message="동등성 검정 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _equivalence_tost_design(options: dict[str, Any]) -> str:
    raw_value = options.get("design")
    if raw_value != "one_sample_mean":
        raise ApiError(
            code="equivalence_tost_design_unsupported",
            message="현재 동등성 검정은 1표본 평균 설계만 지원합니다.",
        )
    return str(raw_value)


def _equivalence_tost_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_equivalence_tost_alpha",
            message="동등성 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 0.5:
        raise ApiError(
            code="invalid_equivalence_tost_alpha",
            message="동등성 검정 유의수준은 0보다 크고 0.5보다 작아야 합니다.",
        )
    return alpha


def _equivalence_tost_reference_mean(options: dict[str, Any]) -> float:
    return _required_finite_float(
        options,
        "reference_mean",
        code="invalid_equivalence_tost_reference_mean",
        message="동등성 검정 기준 평균을 입력해야 합니다.",
    )


def _equivalence_tost_lower_bound(options: dict[str, Any]) -> float:
    return _required_finite_float(
        options,
        "lower_bound",
        code="invalid_equivalence_tost_bounds",
        message="동등성 검정 하한을 입력해야 합니다.",
    )


def _equivalence_tost_upper_bound(options: dict[str, Any]) -> float:
    return _required_finite_float(
        options,
        "upper_bound",
        code="invalid_equivalence_tost_bounds",
        message="동등성 검정 상한을 입력해야 합니다.",
    )


def _required_finite_float(
    options: dict[str, Any],
    key: str,
    *,
    code: str,
    message: str,
) -> float:
    raw_value = options.get(key)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(code=code, message=message)
    value = float(raw_value)
    if not isfinite(value):
        raise ApiError(code=code, message=message)
    return value


def _equivalence_tost_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="equivalence_tost_missing_policy_unsupported",
            message="동등성 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _equivalence_tost_api_error(code: str) -> ApiError:
    messages = {
        "equivalence_tost_design_unsupported": "현재 동등성 검정은 1표본 평균 설계만 지원합니다.",
        "invalid_equivalence_tost_reference_mean": ("동등성 검정 기준 평균이 올바르지 않습니다."),
        "invalid_equivalence_tost_bounds": "동등성 검정 한계값이 올바르지 않습니다.",
        "equivalence_tost_bounds_order_invalid": "동등성 하한은 상한보다 작아야 합니다.",
        "invalid_equivalence_tost_alpha": (
            "동등성 검정 유의수준은 0보다 크고 0.5보다 작아야 합니다."
        ),
        "equivalence_tost_n_too_small": "동등성 검정에는 최소 2개 사용 값이 필요합니다.",
        "equivalence_tost_standard_error_zero": (
            "평균 차이의 표준오차가 0이어서 동등성 검정을 계산할 수 없습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "동등성 검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _equivalence_tost_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "equivalence_tost_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="equivalence_tost_design_assumption",
                severity="info",
                message="독립성 및 1표본 평균 설계는 사용자가 확인해야 하는 설계 가정입니다.",
            ),
        )
    if "equivalence_bounds_user_defined" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="equivalence_bounds_user_defined",
                severity="info",
                message="동등성 한계는 앱이 추정하지 않으며 사용자가 사전에 정의해야 합니다.",
            ),
        )
    if "non_significance_is_not_equivalence" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_significance_is_not_equivalence",
                severity="info",
                message="일반 차이검정의 비유의성은 동등성 근거가 아닙니다.",
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
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    return warnings


def run_paired_t_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="대응표본 t-검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    before_column, after_column = _selected_paired_t_columns(context, request.options)
    alpha = _paired_t_alpha(request.options)
    confidence_level = _paired_t_confidence_level(request.options)
    alternative = _paired_t_alternative(request.options)
    null_difference = _paired_t_null_difference(request.options)
    _paired_t_missing_policy(request.options)
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
            result = calculate_paired_t(
                _iter_rows_for_snapshot(context, row_snapshot),
                before_column,
                after_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
                null_difference=null_difference,
            )
        except PairedTError as exc:
            raise _paired_t_api_error(exc.code) from exc
        warnings = _paired_t_warnings(result)
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


def _selected_paired_t_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[PairedTColumn, PairedTColumn]:
    before_column_id = options.get("before_column_id")
    after_column_id = options.get("after_column_id")
    if not isinstance(before_column_id, str) or not before_column_id:
        raise ApiError(
            code="paired_t_before_column_required",
            message="대응표본 t-검정의 첫 번째 측정 컬럼을 선택해야 합니다.",
        )
    if not isinstance(after_column_id, str) or not after_column_id:
        raise ApiError(
            code="paired_t_after_column_required",
            message="대응표본 t-검정의 두 번째 측정 컬럼을 선택해야 합니다.",
        )
    if before_column_id == after_column_id:
        raise ApiError(
            code="paired_t_same_before_and_after_column",
            message="대응표본 t-검정의 두 측정 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    before_column = columns_by_id.get(before_column_id)
    if before_column is None:
        raise ApiError(
            code="paired_t_before_column_not_found",
            message="요청한 대응표본 t-검정 첫 번째 측정 컬럼을 찾을 수 없습니다.",
        )
    after_column = columns_by_id.get(after_column_id)
    if after_column is None:
        raise ApiError(
            code="paired_t_after_column_not_found",
            message="요청한 대응표본 t-검정 두 번째 측정 컬럼을 찾을 수 없습니다.",
        )

    _validate_paired_t_column(before_column, code_prefix="before")
    _validate_paired_t_column(after_column, code_prefix="after")
    return (
        _paired_t_column(before_column),
        _paired_t_column(after_column),
    )


def _validate_paired_t_column(column: DatasetColumnRecord, *, code_prefix: str) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"paired_t_{code_prefix}_column_is_id",
            message="ID 컬럼은 대응표본 t-검정 측정 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"paired_t_{code_prefix}_column_not_numeric",
            message="대응표본 t-검정 측정 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _paired_t_column(column: DatasetColumnRecord) -> PairedTColumn:
    return PairedTColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _paired_t_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_paired_t_alpha",
            message="대응표본 t-검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_paired_t_alpha",
            message="대응표본 t-검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _paired_t_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_paired_t_confidence_level",
            message="대응표본 t-검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise ApiError(
            code="invalid_paired_t_confidence_level",
            message="대응표본 t-검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _paired_t_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_paired_t_alternative",
            message="대응표본 t-검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _paired_t_null_difference(options: dict[str, Any]) -> float:
    raw_value = options.get("null_difference", 0.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_paired_t_null_difference",
            message="대응표본 t-검정 기준 차이가 올바르지 않습니다.",
        )
    null_difference = float(raw_value)
    if not isfinite(null_difference):
        raise ApiError(
            code="invalid_paired_t_null_difference",
            message="대응표본 t-검정 기준 차이가 유한하지 않습니다.",
        )
    return null_difference


def _paired_t_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_pair")
    if raw_value != "complete_pair":
        raise ApiError(
            code="paired_t_missing_policy_unsupported",
            message="대응표본 t-검정은 현재 complete-pair 결측 처리만 지원합니다.",
        )
    return raw_value


def _paired_t_api_error(code: str) -> ApiError:
    messages = {
        "paired_t_n_too_small": "대응표본 t-검정에는 최소 2개 완전한 pair가 필요합니다.",
        "paired_t_standard_error_zero": (
            "pair 차이의 표준오차가 0이어서 대응표본 t-검정을 계산할 수 없습니다."
        ),
        "invalid_paired_t_alternative": "대응표본 t-검정 대립가설이 올바르지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "대응표본 t-검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _paired_t_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "paired_t_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="paired_t_design_assumption",
                severity="info",
                message=(
                    "각 행이 같은 subject/pair의 두 측정값이라는 설계 가정은 "
                    "사용자가 확인해야 합니다."
                ),
            ),
        )
    if "paired_t_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="paired_t_not_auto_switched",
                severity="info",
                message="정규성 진단 결과로 대응표본 t-검정을 자동 전환하지 않습니다.",
            ),
        )
    if "incomplete_pairs_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="incomplete_pairs_excluded",
                severity="warning",
                message="한쪽 측정값이 없는 incomplete pair는 complete-pair 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_pairs_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_pairs_excluded",
                severity="warning",
                message="두 측정값 중 숫자로 해석할 수 없는 값이 있는 pair는 제외했습니다.",
            ),
        )
    return warnings


def run_one_sample_wilcoxon_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="1-표본 Wilcoxon 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column = _selected_one_sample_wilcoxon_column(context, request.options)
    alpha = _one_sample_wilcoxon_alpha(request.options)
    alternative = _one_sample_wilcoxon_alternative(request.options)
    null_location = _one_sample_wilcoxon_null_location(request.options)
    method = _one_sample_wilcoxon_method(request.options)
    zero_method = _one_sample_wilcoxon_zero_method(request.options)
    _one_sample_wilcoxon_missing_policy(request.options)
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
            result = calculate_one_sample_wilcoxon(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                alternative=alternative,
                null_location=null_location,
                method=method,
                zero_method=zero_method,
            )
        except OneSampleWilcoxonError as exc:
            raise _one_sample_wilcoxon_api_error(exc.code) from exc
        warnings = _one_sample_wilcoxon_warnings(result)
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


def _selected_one_sample_wilcoxon_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> OneSampleWilcoxonColumn:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="one_sample_wilcoxon_response_required",
            message="1-표본 Wilcoxon 반응 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="one_sample_wilcoxon_response_column_not_found",
            message="요청한 1-표본 Wilcoxon 반응 컬럼을 찾을 수 없습니다.",
        )

    _validate_one_sample_wilcoxon_response_column(response_column)
    return OneSampleWilcoxonColumn(
        column_id=response_column.column_id,
        column_index=response_column.column_index,
        display_name=response_column.display_name,
        data_type=response_column.data_type,
        measurement_level=response_column.measurement_level,
        role=response_column.role,
        unit=response_column.unit,
    )


def _validate_one_sample_wilcoxon_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="one_sample_wilcoxon_response_column_is_id",
            message="ID 컬럼은 1-표본 Wilcoxon 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="one_sample_wilcoxon_response_column_not_numeric",
            message="1-표본 Wilcoxon 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _one_sample_wilcoxon_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_wilcoxon_alpha",
            message="1-표본 Wilcoxon 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_one_sample_wilcoxon_alpha",
            message="1-표본 Wilcoxon 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _one_sample_wilcoxon_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_one_sample_wilcoxon_alternative",
            message="1-표본 Wilcoxon 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_sample_wilcoxon_null_location(options: dict[str, Any]) -> float:
    raw_value = options.get("null_location", 0.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_wilcoxon_null_location",
            message="1-표본 Wilcoxon 기준 위치가 올바르지 않습니다.",
        )
    null_location = float(raw_value)
    if not isfinite(null_location):
        raise ApiError(
            code="invalid_one_sample_wilcoxon_null_location",
            message="1-표본 Wilcoxon 기준 위치가 유한하지 않습니다.",
        )
    return null_location


def _one_sample_wilcoxon_method(options: dict[str, Any]) -> str:
    raw_value = options.get("method", "auto")
    if raw_value not in {"auto", "exact", "asymptotic"}:
        raise ApiError(
            code="invalid_one_sample_wilcoxon_method",
            message="1-표본 Wilcoxon p-value 계산 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_sample_wilcoxon_zero_method(options: dict[str, Any]) -> str:
    raw_value = options.get("zero_method", "wilcox")
    if raw_value not in {"wilcox", "pratt", "zsplit"}:
        raise ApiError(
            code="invalid_one_sample_wilcoxon_zero_method",
            message="1-표본 Wilcoxon zero difference 처리 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_sample_wilcoxon_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="one_sample_wilcoxon_missing_policy_unsupported",
            message="1-표본 Wilcoxon은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _one_sample_wilcoxon_api_error(code: str) -> ApiError:
    messages = {
        "one_sample_wilcoxon_no_nonzero_differences": (
            "기준 위치와 다른 사용 값이 없어 1-표본 Wilcoxon을 계산할 수 없습니다."
        ),
        "one_sample_wilcoxon_exact_with_zeros_or_ties": (
            "zero difference 또는 동률 절대차가 있을 때는 exact 1-표본 "
            "Wilcoxon p-value를 계산하지 않습니다."
        ),
        "one_sample_wilcoxon_statistic_not_finite": (
            "1-표본 Wilcoxon 통계량 또는 p-value가 유한하지 않습니다."
        ),
        "invalid_one_sample_wilcoxon_alternative": (
            "1-표본 Wilcoxon 대립가설이 올바르지 않습니다."
        ),
        "invalid_one_sample_wilcoxon_method": (
            "1-표본 Wilcoxon p-value 계산 방식이 올바르지 않습니다."
        ),
        "invalid_one_sample_wilcoxon_zero_method": (
            "1-표본 Wilcoxon zero difference 처리 방식이 올바르지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "1-표본 Wilcoxon을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _one_sample_wilcoxon_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "one_sample_wilcoxon_symmetry_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_wilcoxon_symmetry_assumption",
                severity="info",
                message="차이값 분포의 대칭성은 설계/진단 가정이며 자동 검증하지 않습니다.",
            ),
        )
    if "one_sample_wilcoxon_not_median_test" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_wilcoxon_not_median_test",
                severity="info",
                message=(
                    "대칭성 가정 없이 1-표본 Wilcoxon을 단순 중앙값 검정으로 " "단정하지 않습니다."
                ),
            ),
        )
    if "one_sample_wilcoxon_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_wilcoxon_not_auto_switched",
                severity="info",
                message="정규성 진단 결과로 1-표본 Wilcoxon을 자동 선택하지 않습니다.",
            ),
        )
    if "zero_differences_detected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="zero_differences_detected",
                severity="warning",
                message=(
                    "기준 위치와 같은 값이 있어 zero difference 처리 방식을 함께 "
                    "확인해야 합니다."
                ),
            ),
        )
    if "signed_rank_ties_detected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="signed_rank_ties_detected",
                severity="warning",
                message="동률 절대차가 있어 p-value 방식과 rank 해석을 함께 확인해야 합니다.",
            ),
        )
    if "one_sample_wilcoxon_auto_asymptotic_due_to_zeros_or_ties" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_wilcoxon_auto_asymptotic_due_to_zeros_or_ties",
                severity="info",
                message=(
                    "auto 방식에서 zero difference 또는 동률을 감지해 asymptotic "
                    "p-value를 사용했습니다."
                ),
            ),
        )
    if "small_nonzero_n" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_nonzero_n",
                severity="info",
                message="기준 위치와 다른 사용 값 수가 작아 p-value 방식과 설계를 함께 확인하세요.",
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
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    return warnings


def run_two_sample_t_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="2-표본 t-검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_two_sample_t_columns(context, request.options)
    alpha = _two_sample_t_alpha(request.options)
    confidence_level = _two_sample_t_confidence_level(request.options)
    alternative = _two_sample_t_alternative(request.options)
    variance_assumption = _two_sample_t_variance_assumption(request.options)
    null_difference = _two_sample_t_null_difference(request.options)
    _two_sample_t_missing_policy(request.options)
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
            result = calculate_two_sample_t(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
                variance_assumption=variance_assumption,
                null_difference=null_difference,
            )
        except TwoSampleTError as exc:
            raise _two_sample_t_api_error(exc.code) from exc
        warnings = _two_sample_t_warnings(result)
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


def _selected_two_sample_t_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[TwoSampleTResponseColumn, TwoSampleTGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="two_sample_t_response_required",
            message="2-표본 t-검정 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="two_sample_t_group_required",
            message="2-표본 t-검정 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="two_sample_t_same_response_and_group",
            message="반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="two_sample_t_response_column_not_found",
            message="요청한 2-표본 t-검정 반응 컬럼을 찾을 수 없습니다.",
        )
    group_column = columns_by_id.get(group_column_id)
    if group_column is None:
        raise ApiError(
            code="two_sample_t_group_column_not_found",
            message="요청한 2-표본 t-검정 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_two_sample_t_response_column(response_column)
    _validate_two_sample_t_group_column(group_column)
    return (
        TwoSampleTResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        TwoSampleTGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_two_sample_t_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="two_sample_t_response_column_is_id",
            message="ID 컬럼은 2-표본 t-검정 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="two_sample_t_response_column_not_numeric",
            message="2-표본 t-검정 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_two_sample_t_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="two_sample_t_group_column_is_id",
            message="ID 컬럼은 2-표본 t-검정 그룹 변수로 사용할 수 없습니다.",
        )


def _two_sample_t_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_sample_t_alpha",
            message="2-표본 t-검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_two_sample_t_alpha",
            message="2-표본 t-검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _two_sample_t_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_sample_t_confidence_level",
            message="2-표본 t-검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise ApiError(
            code="invalid_two_sample_t_confidence_level",
            message="2-표본 t-검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _two_sample_t_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_two_sample_t_alternative",
            message="2-표본 t-검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _two_sample_t_variance_assumption(options: dict[str, Any]) -> str:
    raw_value = options.get("variance_assumption", "welch")
    if raw_value not in {"welch", "pooled"}:
        raise ApiError(
            code="invalid_two_sample_t_variance_assumption",
            message="2-표본 t-검정 분산 가정이 올바르지 않습니다.",
        )
    return str(raw_value)


def _two_sample_t_null_difference(options: dict[str, Any]) -> float:
    raw_value = options.get("null_difference", 0.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_sample_t_null_difference",
            message="2-표본 t-검정 기준 평균 차이가 올바르지 않습니다.",
        )
    null_difference = float(raw_value)
    if not isfinite(null_difference):
        raise ApiError(
            code="invalid_two_sample_t_null_difference",
            message="2-표본 t-검정 기준 평균 차이가 유한하지 않습니다.",
        )
    return null_difference


def _two_sample_t_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="two_sample_t_missing_policy_unsupported",
            message="2-표본 t-검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _two_sample_t_api_error(code: str) -> ApiError:
    messages = {
        "two_sample_t_requires_exactly_two_groups": (
            "2-표본 t-검정에는 사용 가능한 그룹이 정확히 2개 필요합니다."
        ),
        "two_sample_t_group_n_too_small": "각 그룹에는 최소 2개 사용 값이 필요합니다.",
        "two_sample_t_standard_error_zero": (
            "평균 차이의 표준오차가 0이어서 2-표본 t-검정을 계산할 수 없습니다."
        ),
        "invalid_two_sample_t_alternative": "2-표본 t-검정 대립가설이 올바르지 않습니다.",
        "invalid_two_sample_t_variance_assumption": (
            "2-표본 t-검정 분산 가정이 올바르지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "2-표본 t-검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _two_sample_t_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "two_sample_t_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_sample_t_independence_assumption",
                severity="info",
                message="독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "two_sample_t_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_sample_t_not_auto_switched",
                severity="info",
                message="정규성/등분산 진단 결과로 2-표본 t-검정 방식을 자동 전환하지 않습니다.",
            ),
        )
    if "pooled_variance_assumption_selected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pooled_variance_assumption_selected",
                severity="warning",
                message="pooled Student 방식은 사용자가 명시적으로 선택한 경우에만 실행합니다.",
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
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "constant_group" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="constant_group",
                severity="warning",
                message="하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
            ),
        )
    return warnings


def run_mann_whitney_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Mann-Whitney U 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_mann_whitney_columns(context, request.options)
    alpha = _mann_whitney_alpha(request.options)
    alternative = _mann_whitney_alternative(request.options)
    method = _mann_whitney_method(request.options)
    _mann_whitney_missing_policy(request.options)
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
            result = calculate_mann_whitney(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                alternative=alternative,
                method=method,
            )
        except MannWhitneyError as exc:
            raise _mann_whitney_api_error(exc.code) from exc
        warnings = _mann_whitney_warnings(result)
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


def _selected_mann_whitney_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[MannWhitneyResponseColumn, MannWhitneyGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="mann_whitney_response_required",
            message="Mann-Whitney U 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="mann_whitney_group_required",
            message="Mann-Whitney U 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="mann_whitney_same_response_and_group",
            message="반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="mann_whitney_response_column_not_found",
            message="요청한 Mann-Whitney U 반응 컬럼을 찾을 수 없습니다.",
        )
    group_column = columns_by_id.get(group_column_id)
    if group_column is None:
        raise ApiError(
            code="mann_whitney_group_column_not_found",
            message="요청한 Mann-Whitney U 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_mann_whitney_response_column(response_column)
    _validate_mann_whitney_group_column(group_column)
    return (
        MannWhitneyResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        MannWhitneyGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_mann_whitney_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="mann_whitney_response_column_is_id",
            message="ID 컬럼은 Mann-Whitney U 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="mann_whitney_response_column_not_numeric",
            message="Mann-Whitney U 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_mann_whitney_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="mann_whitney_group_column_is_id",
            message="ID 컬럼은 Mann-Whitney U 그룹 변수로 사용할 수 없습니다.",
        )


def _mann_whitney_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_mann_whitney_alpha",
            message="Mann-Whitney U 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_mann_whitney_alpha",
            message="Mann-Whitney U 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _mann_whitney_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_mann_whitney_alternative",
            message="Mann-Whitney U 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _mann_whitney_method(options: dict[str, Any]) -> str:
    raw_value = options.get("method", "auto")
    if raw_value not in {"auto", "exact", "asymptotic"}:
        raise ApiError(
            code="invalid_mann_whitney_method",
            message="Mann-Whitney U p-value 계산 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _mann_whitney_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="mann_whitney_missing_policy_unsupported",
            message="Mann-Whitney U는 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _mann_whitney_api_error(code: str) -> ApiError:
    messages = {
        "mann_whitney_requires_exactly_two_groups": (
            "Mann-Whitney U에는 사용 가능한 그룹이 정확히 2개 필요합니다."
        ),
        "mann_whitney_group_n_too_small": "각 그룹에는 최소 1개 사용 값이 필요합니다.",
        "mann_whitney_exact_with_ties": (
            "동률 값이 있을 때는 exact Mann-Whitney U p-value를 계산하지 않습니다."
        ),
        "mann_whitney_statistic_not_finite": (
            "Mann-Whitney U 통계량 또는 p-value가 유한하지 않습니다."
        ),
        "invalid_mann_whitney_alternative": "Mann-Whitney U 대립가설이 올바르지 않습니다.",
        "invalid_mann_whitney_method": "Mann-Whitney U p-value 계산 방식이 올바르지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Mann-Whitney U를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _mann_whitney_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "mann_whitney_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="mann_whitney_independence_assumption",
                severity="info",
                message="독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "mann_whitney_not_median_test" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="mann_whitney_not_median_test",
                severity="info",
                message="Mann-Whitney U 결과를 단순 중앙값 차이 검정으로 해석하지 않습니다.",
            ),
        )
    if "mann_whitney_ties_detected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="mann_whitney_ties_detected",
                severity="warning",
                message="동률 값이 있어 p-value 방식과 rank 해석을 함께 확인해야 합니다.",
            ),
        )
    if "mann_whitney_auto_asymptotic_due_to_ties" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="mann_whitney_auto_asymptotic_due_to_ties",
                severity="info",
                message="auto 방식에서 동률 값을 감지해 asymptotic p-value를 사용했습니다.",
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
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "constant_group" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="constant_group",
                severity="warning",
                message="하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
            ),
        )
    if "small_group_size" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_group_size",
                severity="info",
                message="그룹 표본 수가 작아 exact/asymptotic 방식과 설계를 함께 확인하세요.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
            ),
        )
    return warnings


def run_kruskal_wallis_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Kruskal-Wallis 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_kruskal_wallis_columns(
        context,
        request.options,
    )
    alpha = _kruskal_wallis_alpha(request.options)
    posthoc_method = _kruskal_wallis_posthoc_method(request.options)
    posthoc_policy = _kruskal_wallis_posthoc_policy(request.options)
    _kruskal_wallis_missing_policy(request.options)
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
            result = calculate_kruskal_wallis(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                posthoc_method=posthoc_method,
                posthoc_policy=posthoc_policy,
            )
        except KruskalWallisError as exc:
            raise _kruskal_wallis_api_error(exc.code) from exc
        warnings = _kruskal_wallis_warnings(result)
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


def _selected_kruskal_wallis_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[KruskalWallisResponseColumn, KruskalWallisGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="kruskal_wallis_response_required",
            message="Kruskal-Wallis 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="kruskal_wallis_group_required",
            message="Kruskal-Wallis 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="kruskal_wallis_same_response_and_group",
            message="반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="kruskal_wallis_response_column_not_found",
            message="요청한 Kruskal-Wallis 반응 컬럼을 찾을 수 없습니다.",
        )
    group_column = columns_by_id.get(group_column_id)
    if group_column is None:
        raise ApiError(
            code="kruskal_wallis_group_column_not_found",
            message="요청한 Kruskal-Wallis 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_kruskal_wallis_response_column(response_column)
    _validate_kruskal_wallis_group_column(group_column)
    return (
        KruskalWallisResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        KruskalWallisGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_kruskal_wallis_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="kruskal_wallis_response_column_is_id",
            message="ID 컬럼은 Kruskal-Wallis 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="kruskal_wallis_response_column_not_numeric",
            message="Kruskal-Wallis 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_kruskal_wallis_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="kruskal_wallis_group_column_is_id",
            message="ID 컬럼은 Kruskal-Wallis 그룹 변수로 사용할 수 없습니다.",
        )


def _kruskal_wallis_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_kruskal_wallis_alpha",
            message="Kruskal-Wallis 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_kruskal_wallis_alpha",
            message="Kruskal-Wallis 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _kruskal_wallis_posthoc_method(options: dict[str, Any]) -> str:
    raw_value = options.get("posthoc_method", "dunn_holm")
    if raw_value not in {"dunn_holm", "none"}:
        raise ApiError(
            code="invalid_kruskal_wallis_posthoc_method",
            message="Kruskal-Wallis 사후검정 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _kruskal_wallis_posthoc_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("posthoc_policy", "after_significant")
    if raw_value != "after_significant":
        raise ApiError(
            code="invalid_kruskal_wallis_posthoc_policy",
            message="Kruskal-Wallis 사후검정 정책이 올바르지 않습니다.",
        )
    return str(raw_value)


def _kruskal_wallis_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="kruskal_wallis_missing_policy_unsupported",
            message="Kruskal-Wallis는 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _kruskal_wallis_api_error(code: str) -> ApiError:
    messages = {
        "kruskal_wallis_requires_at_least_three_groups": (
            "Kruskal-Wallis에는 사용 가능한 그룹이 최소 3개 필요합니다."
        ),
        "kruskal_wallis_group_n_too_small": ("각 그룹에는 최소 1개 사용 값이 필요합니다."),
        "kruskal_wallis_all_values_identical": (
            "전체 반응 값이 모두 동일해 Kruskal-Wallis 통계량을 계산할 수 없습니다."
        ),
        "kruskal_wallis_statistic_not_finite": (
            "Kruskal-Wallis 통계량 또는 p-value가 유한하지 않습니다."
        ),
        "kruskal_wallis_posthoc_variance_zero": (
            "Dunn 사후검정의 rank 분산이 0이어서 계산할 수 없습니다."
        ),
        "invalid_kruskal_wallis_posthoc_method": (
            "Kruskal-Wallis 사후검정 방식이 올바르지 않습니다."
        ),
        "invalid_kruskal_wallis_posthoc_policy": (
            "Kruskal-Wallis 사후검정 정책이 올바르지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Kruskal-Wallis를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _kruskal_wallis_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "kruskal_wallis_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="kruskal_wallis_independence_assumption",
                severity="info",
                message="독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "kruskal_wallis_not_median_test" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="kruskal_wallis_not_median_test",
                severity="info",
                message="Kruskal-Wallis 결과를 단순 중앙값 차이 검정으로 해석하지 않습니다.",
            ),
        )
    if "dunn_holm_after_significant" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="dunn_holm_after_significant",
                severity="info",
                message="overall 검정이 유의한 경우에만 Dunn 사후검정과 Holm 보정을 수행했습니다.",
            ),
        )
    if "posthoc_skipped_overall_not_significant" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="posthoc_skipped_overall_not_significant",
                severity="info",
                message="overall 검정이 유의하지 않아 Dunn 사후검정을 실행하지 않았습니다.",
            ),
        )
    if "kruskal_wallis_ties_detected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="kruskal_wallis_ties_detected",
                severity="warning",
                message="동률 값이 있어 tie correction과 rank 해석을 함께 확인해야 합니다.",
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
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "constant_group" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="constant_group",
                severity="warning",
                message="하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
            ),
        )
    if "small_group_size" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_group_size",
                severity="info",
                message="그룹 표본 수가 작아 rank 기반 근사와 설계를 함께 확인하세요.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
            ),
        )
    return warnings


def run_one_way_anova_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="일원분산분석 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_one_way_anova_columns(
        context,
        request.options,
    )
    alpha = _one_way_anova_alpha(request.options)
    confidence_level = _one_way_anova_confidence_level(request.options)
    anova_type = _one_way_anova_type(request.options)
    posthoc_method = _one_way_anova_posthoc_method(request.options)
    posthoc_policy = _one_way_anova_posthoc_policy(request.options)
    _one_way_anova_missing_policy(request.options)
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
            result = calculate_one_way_anova(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                anova_type=anova_type,
                posthoc_method=posthoc_method,
                posthoc_policy=posthoc_policy,
            )
        except OneWayAnovaError as exc:
            raise _one_way_anova_api_error(exc.code) from exc
        warnings = _one_way_anova_warnings(result)
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


def _selected_one_way_anova_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[OneWayAnovaResponseColumn, OneWayAnovaGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="one_way_anova_response_required",
            message="일원분산분석 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="one_way_anova_group_required",
            message="일원분산분석 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="one_way_anova_same_response_and_group",
            message="일원분산분석 반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    group_column = columns_by_id.get(group_column_id)
    if response_column is None:
        raise ApiError(
            code="one_way_anova_response_column_not_found",
            message="요청한 일원분산분석 반응 컬럼을 찾을 수 없습니다.",
        )
    if group_column is None:
        raise ApiError(
            code="one_way_anova_group_column_not_found",
            message="요청한 일원분산분석 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_one_way_anova_response_column(response_column)
    _validate_one_way_anova_group_column(group_column)
    return (
        OneWayAnovaResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        OneWayAnovaGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_one_way_anova_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="one_way_anova_response_column_is_id",
            message="ID 컬럼은 일원분산분석 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="one_way_anova_response_column_not_numeric",
            message="일원분산분석 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_one_way_anova_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="one_way_anova_group_column_is_id",
            message="ID 컬럼은 일원분산분석 그룹 변수로 사용할 수 없습니다.",
        )


def _one_way_anova_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_way_anova_alpha",
            message="일원분산분석 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_one_way_anova_alpha",
            message="일원분산분석 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _one_way_anova_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_way_anova_confidence_level",
            message="일원분산분석 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_one_way_anova_confidence_level",
            message="일원분산분석 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _one_way_anova_type(options: dict[str, Any]) -> str:
    raw_value = options.get("anova_type", "standard")
    if raw_value != "standard":
        raise ApiError(
            code="invalid_one_way_anova_type",
            message="이번 slice는 표준 일원분산분석만 지원합니다.",
        )
    return str(raw_value)


def _one_way_anova_posthoc_method(options: dict[str, Any]) -> str:
    raw_value = options.get("posthoc_method", "tukey_kramer")
    if raw_value not in {"tukey_kramer", "none"}:
        raise ApiError(
            code="invalid_one_way_anova_posthoc_method",
            message="일원분산분석 사후검정 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_way_anova_posthoc_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("posthoc_policy", "after_significant")
    if raw_value != "after_significant":
        raise ApiError(
            code="invalid_one_way_anova_posthoc_policy",
            message="일원분산분석 사후검정 정책이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_way_anova_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="one_way_anova_missing_policy_unsupported",
            message="일원분산분석은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _one_way_anova_api_error(code: str) -> ApiError:
    messages = {
        "invalid_one_way_anova_type": "이번 slice는 표준 일원분산분석만 지원합니다.",
        "invalid_one_way_anova_alpha": "일원분산분석 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_one_way_anova_confidence_level": (
            "일원분산분석 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "invalid_one_way_anova_posthoc_method": ("일원분산분석 사후검정 방식이 올바르지 않습니다."),
        "invalid_one_way_anova_posthoc_policy": ("일원분산분석 사후검정 정책이 올바르지 않습니다."),
        "one_way_anova_requires_at_least_two_groups": (
            "일원분산분석에는 사용 가능한 그룹이 최소 2개 필요합니다."
        ),
        "one_way_anova_group_n_too_small": (
            "일원분산분석의 각 그룹에는 최소 2개 사용 값이 필요합니다."
        ),
        "one_way_anova_all_values_identical": (
            "전체 반응 값이 모두 동일해 일원분산분석을 계산할 수 없습니다."
        ),
        "one_way_anova_degrees_of_freedom_invalid": ("일원분산분석 자유도가 유효하지 않습니다."),
        "one_way_anova_zero_residual_variance": (
            "잔차 분산이 0이어서 일원분산분석 F 통계량을 계산할 수 없습니다."
        ),
        "one_way_anova_statistic_not_finite": (
            "일원분산분석 통계량 또는 p-value가 유한하지 않습니다."
        ),
        "one_way_anova_posthoc_standard_error_zero": (
            "Tukey-Kramer 사후비교 표준오차가 0이어서 계산할 수 없습니다."
        ),
        "one_way_anova_posthoc_not_finite": ("Tukey-Kramer 사후비교 결과가 유한하지 않습니다."),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "일원분산분석을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _one_way_anova_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "one_way_anova_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_way_anova_independence_assumption",
                severity="info",
                message="독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "one_way_anova_normality_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_way_anova_normality_assumption",
                severity="info",
                message="잔차 정규성은 별도 진단과 설계 맥락으로 확인해야 합니다.",
            ),
        )
    if "one_way_anova_equal_variance_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_way_anova_equal_variance_assumption",
                severity="info",
                message="표준 일원분산분석은 등분산 가정을 사용합니다.",
            ),
        )
    if "one_way_anova_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_way_anova_not_auto_switched",
                severity="info",
                message="진단 결과만으로 Welch ANOVA나 비모수 검정으로 자동 전환하지 않습니다.",
            ),
        )
    if "tukey_kramer_after_standard_anova" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="tukey_kramer_after_standard_anova",
                severity="info",
                message="표준 ANOVA가 유의한 경우 Tukey-Kramer 사후비교를 수행했습니다.",
            ),
        )
    if "posthoc_skipped_overall_not_significant" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="posthoc_skipped_overall_not_significant",
                severity="info",
                message="overall ANOVA가 유의하지 않아 사후비교를 실행하지 않았습니다.",
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
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "constant_group" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="constant_group",
                severity="warning",
                message="하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
            ),
        )
    if "small_group_size" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_group_size",
                severity="info",
                message="그룹 표본 수가 작아 ANOVA 가정과 영향점을 함께 확인하세요.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
            ),
        )
    if "two_group_anova_equivalent_to_t_test" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_group_anova_equivalent_to_t_test",
                severity="info",
                message="그룹이 2개인 ANOVA는 표준 2표본 t-검정과 동등한 구조입니다.",
            ),
        )
    return warnings
