from fastapi import status

from app.api.v1.schemas.analyses import (
    GageRrPreflightRequest,
    GageRrPreflightResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.dataset_rows import get_dataset_rows_context, iter_dataset_rows
from app.statistics.gage_rr_preflight import (
    GageRrColumn,
    GageRrPreflightError,
    calculate_gage_rr_preflight,
)
from app.storage.metadata import DatasetColumnRecord

NUMERIC_DATA_TYPES = {"integer", "decimal"}
GAGE_ID_DATA_TYPES = {"integer", "decimal", "text", "boolean"}


def get_gage_rr_preflight(
    settings: Settings,
    body: GageRrPreflightRequest,
) -> GageRrPreflightResponse:
    if body.missing_policy != "complete_case":
        raise ApiError(
            code="gage_rr_missing_policy_unsupported",
            message="Gage R&R 사전점검은 현재 complete-case 결측 처리만 지원합니다.",
        )

    context = get_dataset_rows_context(settings, body.dataset_version_id)
    measurement_column, part_column, operator_column, replicate_column = select_gage_rr_columns(
        context.columns,
        measurement_column_id=body.measurement_column_id,
        part_column_id=body.part_column_id,
        operator_column_id=body.operator_column_id,
        replicate_column_id=body.replicate_column_id,
    )

    try:
        result = calculate_gage_rr_preflight(
            iter_dataset_rows(context),
            measurement_column=gage_rr_column_payload(measurement_column),
            part_column=gage_rr_column_payload(part_column),
            operator_column=gage_rr_column_payload(operator_column),
            replicate_column=gage_rr_column_payload(replicate_column),
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            missing_policy=body.missing_policy,
        )
    except GageRrPreflightError as exc:
        raise gage_rr_api_error(exc.code) from exc

    return GageRrPreflightResponse.model_validate(
        {
            "schema_version": 1,
            "method_id": "quality.gage_rr",
            "preflight_type": "balanced_crossed_anova",
            "dataset_version_id": str(body.dataset_version_id),
            "schema_hash": context.version.schema_hash,
            "row_count_total": context.version.row_count,
            **result,
        },
    )


def select_gage_rr_columns(
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
            code="gage_rr_distinct_columns_required",
            message="측정값, 부품, 측정자, 반복 컬럼은 서로 달라야 합니다.",
        )
    return (
        _selected_measurement_column(columns, measurement_column_id),
        _selected_identifier_column(columns, part_column_id, "part"),
        _selected_identifier_column(columns, operator_column_id, "operator"),
        _selected_identifier_column(columns, replicate_column_id, "replicate"),
    )


def _selected_measurement_column(
    columns: list[DatasetColumnRecord],
    column_id: str,
) -> DatasetColumnRecord:
    column = _column_by_id(columns, column_id)
    if column is None:
        raise ApiError(
            code="gage_rr_measurement_column_not_found",
            message="요청한 Gage R&R 측정값 컬럼을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="gage_rr_measurement_column_not_numeric",
            message="Gage R&R 측정값은 현재 숫자형 컬럼만 지원합니다.",
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="gage_rr_measurement_column_is_id",
            message="ID 컬럼은 Gage R&R 측정값으로 사용할 수 없습니다.",
        )
    return column


def _selected_identifier_column(
    columns: list[DatasetColumnRecord],
    column_id: str,
    role_name: str,
) -> DatasetColumnRecord:
    column = _column_by_id(columns, column_id)
    if column is None:
        raise ApiError(
            code=f"gage_rr_{role_name}_column_not_found",
            message="요청한 Gage R&R 식별 컬럼을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if column.data_type not in GAGE_ID_DATA_TYPES:
        raise ApiError(
            code=f"gage_rr_{role_name}_column_not_supported",
            message="Gage R&R 부품, 측정자, 반복 컬럼은 현재 숫자, 텍스트, boolean만 지원합니다.",
        )
    return column


def _column_by_id(
    columns: list[DatasetColumnRecord],
    column_id: str,
) -> DatasetColumnRecord | None:
    return next((column for column in columns if column.column_id == column_id), None)


def gage_rr_column_payload(column: DatasetColumnRecord) -> GageRrColumn:
    return GageRrColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def gage_rr_api_error(code: str) -> ApiError:
    messages = {
        "gage_rr_missing_policy_unsupported": (
            "Gage R&R 사전점검은 현재 complete-case 결측 처리만 지원합니다."
        ),
        "gage_rr_identifier_missing": "Gage R&R 식별 컬럼에 결측값이 있습니다.",
        "gage_rr_no_usable_measurements": "Gage R&R에 사용할 수 있는 측정 행이 없습니다.",
        "gage_rr_part_count_too_small": "Gage R&R에는 최소 2개 부품이 필요합니다.",
        "gage_rr_operator_count_too_small": "Gage R&R에는 최소 2명 이상의 측정자가 필요합니다.",
        "gage_rr_replicate_count_too_small": (
            "각 부품-측정자 조합에는 최소 2회 반복 측정이 필요합니다."
        ),
        "gage_rr_crossed_cells_missing": (
            "일부 부품-측정자 조합이 없어 crossed 설계가 완전하지 않습니다."
        ),
        "gage_rr_unbalanced_crossed_design": (
            "부품-측정자 조합별 반복 수 또는 반복 ID 집합이 일치하지 않습니다."
        ),
        "gage_rr_duplicate_replicates_per_cell": (
            "같은 부품-측정자 조합 안에 중복 반복 ID가 있습니다."
        ),
        "gage_rr_zero_total_variation": (
            "총 변동이 0이라 Gage R&R variance component를 계산할 수 없습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Gage R&R을 수행할 수 없습니다."),
    )
