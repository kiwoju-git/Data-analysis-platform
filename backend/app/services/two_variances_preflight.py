from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Any

from app.api.v1.schemas.analyses import (
    AnalysisFilterSnapshot,
    TwoVariancesPreflightGroup,
    TwoVariancesPreflightRequest,
    TwoVariancesPreflightResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    NUMERIC_DATA_TYPES,
    canonical_json_bytes,
    freeze_row_indices,
)
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
)
from app.statistics.two_variances import ParsedGroups, TwoVariancesError, parse_two_variance_groups
from app.storage.metadata import DatasetColumnRecord


def two_variances_error(code: str) -> ApiError:
    messages = {
        "two_variances_exactly_two_groups_required": (
            "Filter the data to exactly two usable independent groups."
        ),
        "two_variances_group_n_too_small": (
            "Each group needs at least 3 values for Brown-Forsythe or 2 for F."
        ),
        "two_variances_usable_rows_limit": "Two Variances supports at most 20,000 usable rows.",
        "two_variances_zero_variance": "Both groups must have positive sample variance.",
        "two_variances_preflight_changed": (
            "The source or group configuration changed. Check groups again."
        ),
        "two_variances_groups_changed": (
            "Selected numerator and denominator do not match the usable groups."
        ),
        "two_variances_degenerate_absolute_deviations": (
            "Within-group absolute deviations are degenerate; inference is unavailable."
        ),
        "two_variances_columns_invalid": (
            "Select a numeric non-ID response and a distinct non-ID group column."
        ),
        "two_variances_nonfinite_result": (
            "The requested variance calculation exceeds the supported numerical range."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Invalid Two Variances configuration or input."),
        status_code=422,
    )


def selected_columns(
    context: DatasetRowsContext, response_id: str, group_id: str
) -> tuple[DatasetColumnRecord, DatasetColumnRecord]:
    columns = {column.column_id: column for column in context.columns}
    response, group = columns.get(response_id), columns.get(group_id)
    if (
        response is None
        or group is None
        or response_id == group_id
        or response.data_type not in NUMERIC_DATA_TYPES
        or any(
            column.role == "id" or column.measurement_level == "id" for column in (response, group)
        )
    ):
        raise two_variances_error("two_variances_columns_invalid")
    return response, group


def column_payload(column: DatasetColumnRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in asdict(column).items()
        if key
        in (
            "column_id",
            "display_name",
            "data_type",
            "measurement_level",
            "role",
            "unit",
        )
    }


def preflight_payload(
    context: DatasetRowsContext,
    response_id: str,
    group_id: str,
    filters: AnalysisFilterSnapshot,
    parsed: ParsedGroups,
) -> TwoVariancesPreflightResponse:
    fingerprint = hashlib.sha256(
        canonical_json_bytes(
            {
                "version_id": str(context.version.version_id),
                "schema": context.version.schema_hash,
                "response": response_id,
                "group": group_id,
                "filter": filters.model_dump(mode="json"),
                "groups": {key: len(values) for key, values in parsed.values.items()},
                "sample": parsed.sample(),
            }
        )
    ).hexdigest()
    reasons = []
    if len(parsed.values) != 2:
        reasons.append("two_variances_exactly_two_groups_required")
    elif any(len(values) < 2 for values in parsed.values.values()):
        reasons.append("two_variances_group_n_too_small")
    return TwoVariancesPreflightResponse(
        fingerprint=fingerprint,
        groups=[
            TwoVariancesPreflightGroup(
                key=key,
                display_label=key if len(key) <= 120 else key[:117] + "...",
                n_used=len(values),
            )
            for key, values in parsed.values.items()
        ],
        n_total=parsed.n_total,
        n_used=parsed.n_used,
        n_excluded=parsed.n_total - parsed.n_used,
        eligible=not reasons,
        reason_codes=reasons,
    )


def get_two_variances_preflight(
    settings: Settings, request: TwoVariancesPreflightRequest
) -> TwoVariancesPreflightResponse:
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response, group = selected_columns(context, request.response_column_id, request.group_column_id)
    included_indices = freeze_row_indices(context, request.filter_snapshot)
    included = None if included_indices is None else set(included_indices)
    rows = (
        row
        for index, row in enumerate(iter_dataset_rows(context))
        if included is None or index in included
    )
    try:
        parsed = parse_two_variance_groups(
            rows,
            response.column_index,
            group.column_index,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
        )
    except TwoVariancesError as exc:
        raise two_variances_error(exc.code) from exc
    return preflight_payload(
        context, response.column_id, group.column_id, request.filter_snapshot, parsed
    )
