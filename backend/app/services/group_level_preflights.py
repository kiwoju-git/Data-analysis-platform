from __future__ import annotations

import hashlib
from collections import OrderedDict
from uuid import UUID

from app.api.v1.schemas.analyses import (
    GroupLevelPreflightItem,
    GroupLevelPreflightRequest,
    GroupLevelPreflightResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import canonical_json_bytes, freeze_row_indices
from app.services.dataset_rows import get_dataset_rows_context, iter_dataset_rows

GROUP_DISPLAY_LABEL_MAX_LENGTH = 120


def get_group_level_preflight(
    settings: Settings,
    dataset_version_id: UUID,
    body: GroupLevelPreflightRequest,
) -> GroupLevelPreflightResponse:
    context = get_dataset_rows_context(settings, dataset_version_id)
    columns_by_id = {column.column_id: column for column in context.columns}
    group_column = columns_by_id.get(body.group_column_id)
    if group_column is None:
        raise ApiError(
            code="group_level_column_not_found",
            message="그룹 변수를 찾을 수 없습니다.",
        )
    if group_column.role == "id" or group_column.measurement_level == "id":
        raise ApiError(
            code="group_level_column_is_id",
            message="ID 변수는 그룹 수준 조회에 사용할 수 없습니다.",
        )

    included_indices = freeze_row_indices(context, body.filter_snapshot)
    included = None if included_indices is None else set(included_indices)
    counts: OrderedDict[str, int] = OrderedDict()
    missing_count = 0
    truncated = False
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if included is not None and row_index not in included:
            continue
        raw = row[group_column.column_index] if group_column.column_index < len(row) else None
        if raw is None or raw.strip() == "":
            missing_count += 1
            continue
        value = raw.strip()
        if value in counts:
            counts[value] += 1
            continue
        if len(counts) >= body.maximum_levels:
            truncated = True
            continue
        counts[value] = 1

    filter_payload = body.filter_snapshot.model_dump(mode="json")
    return GroupLevelPreflightResponse(
        dataset_version_id=dataset_version_id,
        source_schema_hash=context.version.schema_hash,
        filter_snapshot_sha256=hashlib.sha256(canonical_json_bytes(filter_payload)).hexdigest(),
        group_column_id=body.group_column_id,
        levels=[
            GroupLevelPreflightItem(
                value=value,
                display_label=_display_label(value),
                n_used=count,
            )
            for value, count in counts.items()
        ],
        missing_count=missing_count,
        truncated=truncated,
    )


def _display_label(value: str) -> str:
    if len(value) <= GROUP_DISPLAY_LABEL_MAX_LENGTH:
        return value
    return f"{value[: GROUP_DISPLAY_LABEL_MAX_LENGTH - 3]}..."
