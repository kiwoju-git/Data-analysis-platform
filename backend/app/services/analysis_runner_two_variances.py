from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisWarning,
    TwoVariancesOptions,
)
from app.core.config import Settings
from app.services.analysis_run_execution import (
    create_row_snapshot_artifact,
    iter_rows_for_snapshot,
    remove_file_if_exists,
    store_succeeded_analysis_result,
    utc_now,
)
from app.services.dataset_rows import get_dataset_rows_context
from app.services.two_variances_preflight import (
    column_payload,
    preflight_payload,
    selected_columns,
    two_variances_error,
)
from app.services.two_variances_report import two_variances_warning
from app.statistics.two_variances import (
    MAX_PLOT_POINTS,
    TwoVariancesError,
    calculate_two_variances,
    parse_two_variance_groups,
)
from app.statistics.two_variances import TwoVariancesOptions as StatisticsOptions


def run_two_variances_analysis(
    settings: Settings, request: AnalysisRunRequest
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise two_variances_error("dataset_version_required")
    try:
        options = TwoVariancesOptions.model_validate(request.options)
    except ValidationError as exc:
        raise two_variances_error("invalid_two_variances_options") from exc
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response, group = selected_columns(context, options.response_column_id, options.group_column_id)
    analysis_id, completed_at = uuid4(), utc_now()
    snapshot = create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    try:
        parsed = parse_two_variance_groups(
            iter_rows_for_snapshot(context, snapshot),
            response.column_index,
            group.column_index,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
        )
        preflight = preflight_payload(
            context, response.column_id, group.column_id, request.filter_snapshot, parsed
        )
        if not preflight.eligible:
            raise two_variances_error(preflight.reason_codes[0])
        if (
            options.preflight_fingerprint is not None
            and options.preflight_fingerprint != preflight.fingerprint
        ):
            raise two_variances_error("two_variances_preflight_changed")
        keys = [options.numerator_group_key, options.denominator_group_key]
        if set(keys) != set(parsed.values):
            raise two_variances_error("two_variances_groups_changed")
        result = calculate_two_variances(
            parsed.values[keys[0]],
            parsed.values[keys[1]],
            StatisticsOptions(
                method=options.method,
                ratio_scale=options.ratio_scale,
                hypothesized_ratio=options.hypothesized_ratio,
                alternative=options.alternative,
                confidence_level=options.confidence_level,
            ),
        )
        result.update(
            response=column_payload(response),
            group_column=column_payload(group),
            sample=parsed.sample(),
            source_fingerprint=preflight.fingerprint,
        )
        plot_groups: list[dict[str, Any]] = []
        for index, key in enumerate(keys):
            result["groups"][index].update(
                key=key, label=key, role="numerator" if index == 0 else "denominator"
            )
            values, rows = parsed.values[key], parsed.row_indices[key]
            count = min(len(values), MAX_PLOT_POINTS)
            indices = [i * (len(values) - 1) // (count - 1) for i in range(count)]
            plot_groups.append(
                {
                    "key": key,
                    "n_total": len(values),
                    "n_displayed": count,
                    "points": [{"row_number": rows[i], "value": values[i]} for i in indices],
                }
            )
        result["plot"] = {
            "row_identity": "filtered_analysis_row",
            "groups": plot_groups,
            "point_limit_per_group": MAX_PLOT_POINTS,
        }
        if parsed.n_total != parsed.n_used:
            result["warnings"].append("two_variances_complete_case_exclusions")
        if any(item["n_displayed"] < item["n_total"] for item in plot_groups):
            result["warnings"].append("two_variances_display_points_limited")
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=snapshot,
            result=result,
            warnings=[
                AnalysisWarning(code=code, severity="warning", message=two_variances_warning(code))
                for code in result["warnings"]
            ],
        )
    except Exception as exc:
        remove_file_if_exists(settings.workspace_root / snapshot.relative_path)
        if isinstance(exc, TwoVariancesError):
            raise two_variances_error(exc.code) from exc
        raise
