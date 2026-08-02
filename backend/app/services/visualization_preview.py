import hashlib
import json
from collections import defaultdict
from collections.abc import Iterator
from typing import Any, Literal

from app.api.v1.schemas.visualizations import (
    GraphPreviewPanel,
    GraphPreviewRequest,
    GraphPreviewResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import freeze_row_indices
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
)
from app.statistics.graphical_summary import (
    GraphicalSummaryColumn,
    summarize_numeric_graphics,
)
from app.statistics.individual_value_plot import (
    GraphPointColumn,
    GraphPointError,
    calculate_individual_value_points,
    calculate_scatter_points,
)
from app.statistics.individuals_chart import (
    IndividualsChartColumn,
    IndividualsChartError,
    calculate_individuals_chart,
)
from app.statistics.run_chart import RunChartColumn, RunChartError, calculate_run_chart
from app.storage.metadata import DatasetColumnRecord

NUMERIC_DATA_TYPES = {"integer", "decimal"}
MAX_GROUP_LEVELS = 20


def create_graph_preview(
    settings: Settings,
    request: GraphPreviewRequest,
) -> GraphPreviewResponse:
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    included_indices = freeze_row_indices(context, request.filter_snapshot)
    included_count = (
        context.version.row_count if included_indices is None else len(included_indices)
    )
    columns_by_id = {column.column_id: column for column in context.columns}
    warnings: list[str] = []

    missing_group_row_count = 0
    if request.graph_type == "scatter_plot":
        panels = _scatter_panels(context, request, columns_by_id, included_indices)
    elif request.graph_type == "individual_value_plot":
        panels, missing_group_row_count = _individual_value_panels(
            context, request, columns_by_id, included_indices
        )
    elif request.graph_type in {"run_chart", "imr_chart"}:
        panels, missing_group_row_count = _sequence_panels(
            context, request, columns_by_id, included_indices
        )
    else:
        panels, graphical_warnings, missing_group_row_count = _graphical_summary_panels(
            context,
            request,
            columns_by_id,
            included_indices,
        )
        warnings.extend(graphical_warnings)
    if missing_group_row_count > 0:
        warnings.append("graph_preview_missing_group_rows_excluded")
    if any(panel.status == "failed" for panel in panels):
        warnings.append("graph_preview_partial_panel_failure")

    filter_payload = request.filter_snapshot.model_dump(mode="json")
    config_payload = request.model_dump(mode="json")
    return GraphPreviewResponse(
        graph_type=request.graph_type,
        dataset_version_id=request.dataset_version_id,
        source_schema_hash=context.version.schema_hash,
        filter_snapshot_sha256=_payload_hash(filter_payload),
        preview_config_sha256=_payload_hash(config_payload),
        row_count_total=context.version.row_count,
        row_count_included=included_count,
        warnings=warnings,
        layout=request.layout,
        comparison_mode=request.comparison_mode,
        group_order_policy=request.group_order_policy,
        missing_group_policy=request.missing_group_policy,
        missing_group_row_count=missing_group_row_count,
        panels=panels,
    )


def _graphical_summary_panels(
    context: DatasetRowsContext,
    request: GraphPreviewRequest,
    columns_by_id: dict[str, DatasetColumnRecord],
    included_indices: tuple[int, ...] | None,
) -> tuple[list[GraphPreviewPanel], list[str], int]:
    selected = _numeric_columns(columns_by_id, request.value_column_ids)
    warnings: list[str] = []
    if request.layout in {"combined", "overlay"} and len(selected) > 1:
        explicit_units = {column.unit for column in selected if column.unit}
        if len(explicit_units) > 1:
            raise ApiError(
                code="graph_preview_unit_mismatch",
                message="단위가 다른 변수는 같은 축에서 직접 비교할 수 없습니다.",
            )
        if not explicit_units:
            warnings.append("graph_preview_units_missing")

    group = _optional_group_column(columns_by_id, request.group_column_id)
    if group is not None:
        grouped_rows, missing_group_row_count = _rows_by_group(
            context, included_indices, group
        )
        panels: list[GraphPreviewPanel] = []
        selected_column = selected[0]
        for index, (group_label, rows) in enumerate(grouped_rows.items()):
            result = summarize_numeric_graphics(
                rows,
                [_graphical_column(selected_column)],
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                histogram_bin_count=request.histogram_bin_count,
                point_limit=request.point_limit,
            )
            column_result = _only_summary_column(result)
            column_result = {
                **column_result,
                "column_id": f"{selected_column.column_id}:group:{index}",
                "display_name": group_label,
                "group_label": group_label,
                "response_display_name": selected_column.display_name,
            }
            panels.append(
                GraphPreviewPanel(
                    panel_id=f"group-{index + 1}",
                    kind="graphical_summary",
                    label=f"{selected_column.display_name} · {group_label}",
                    unit=selected_column.unit,
                    status="succeeded",
                    result=column_result,
                )
            )
        return panels, warnings, missing_group_row_count

    result = summarize_numeric_graphics(
        _iter_filtered_rows(context, included_indices),
        [_graphical_column(column) for column in selected],
        decimal=context.parsing.decimal,
        thousands=context.parsing.thousands,
        histogram_bin_count=request.histogram_bin_count,
        point_limit=request.point_limit,
    )
    columns = result.get("columns")
    assert isinstance(columns, list)
    panels = [
        GraphPreviewPanel(
            panel_id=f"column-{index + 1}",
            kind="graphical_summary",
            label=column.display_name,
            unit=column.unit,
            status="succeeded",
            result=column_result,
        )
        for index, (column, column_result) in enumerate(zip(selected, columns, strict=True))
        if isinstance(column_result, dict)
    ]
    return panels, warnings, 0


def _individual_value_panels(
    context: DatasetRowsContext,
    request: GraphPreviewRequest,
    columns_by_id: dict[str, DatasetColumnRecord],
    included_indices: tuple[int, ...] | None,
) -> tuple[list[GraphPreviewPanel], int]:
    selected = _numeric_columns(columns_by_id, request.value_column_ids)
    group = _optional_group_column(columns_by_id, request.group_column_id)
    try:
        result = calculate_individual_value_points(
            _iter_filtered_rows(context, included_indices),
            [_point_column(column) for column in selected],
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            point_limit=request.point_limit,
            group_column_index=None if group is None else group.column_index,
        )
    except GraphPointError as exc:
        raise ApiError(code=exc.code, message=_point_error_message(exc.code)) from exc
    panels = [
        GraphPreviewPanel(
            panel_id="individual-values",
            kind="individual_values",
            label="Individual Value Plot",
            unit=selected[0].unit if len({column.unit for column in selected}) == 1 else None,
            status="succeeded",
            result=result,
        )
    ]
    missing_group = result.get("n_missing_group", 0)
    return panels, int(missing_group) if isinstance(missing_group, int) else 0


def _scatter_panels(
    context: DatasetRowsContext,
    request: GraphPreviewRequest,
    columns_by_id: dict[str, DatasetColumnRecord],
    included_indices: tuple[int, ...] | None,
) -> list[GraphPreviewPanel]:
    assert request.x_column_id is not None
    x_column = _numeric_columns(columns_by_id, [request.x_column_id])[0]
    y_columns = _numeric_columns(columns_by_id, request.y_column_ids)
    group = _optional_group_column(columns_by_id, request.group_column_id)
    try:
        result = calculate_scatter_points(
            _iter_filtered_rows(context, included_indices),
            _point_column(x_column),
            [_point_column(column) for column in y_columns],
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            point_limit=request.point_limit,
            group_column_index=None if group is None else group.column_index,
        )
    except GraphPointError as exc:
        raise ApiError(code=exc.code, message=_point_error_message(exc.code)) from exc
    points = result["points"]
    assert isinstance(points, list)
    return [
        GraphPreviewPanel(
            panel_id=f"scatter-{index + 1}",
            kind="scatter",
            label=f"{y_column.display_name} vs {x_column.display_name}",
            unit=y_column.unit,
            status="succeeded",
            result={
                **result,
                "x_column": _safe_column_payload(x_column),
                "y_column": _safe_column_payload(y_column),
                "points": [
                    point
                    for point in points
                    if isinstance(point, dict) and point.get("series_id") == y_column.column_id
                ],
            },
        )
        for index, y_column in enumerate(y_columns)
    ]


def _sequence_panels(
    context: DatasetRowsContext,
    request: GraphPreviewRequest,
    columns_by_id: dict[str, DatasetColumnRecord],
    included_indices: tuple[int, ...] | None,
) -> tuple[list[GraphPreviewPanel], int]:
    selected = _numeric_columns(columns_by_id, request.value_column_ids)
    order = _optional_order_column(columns_by_id, request.order_column_id)
    panels: list[GraphPreviewPanel] = []
    group = _optional_group_column(columns_by_id, request.group_column_id)
    if group is not None:
        grouped_rows, missing_group_row_count = _rows_by_group(
            context, included_indices, group
        )
        column = selected[0]
        for group_index, (group_label, rows) in enumerate(grouped_rows.items()):
            try:
                result = calculate_individuals_chart(
                    rows,
                    _individuals_column(column),
                    order_column=None if order is None else _individuals_column(order),
                    decimal=context.parsing.decimal,
                    thousands=context.parsing.thousands,
                    point_limit=request.point_limit,
                )
                result = {
                    **result,
                    "group_label": group_label,
                    "group_order": group_index,
                    "group_boundary_policy": "independent_within_group",
                }
                panels.append(
                    GraphPreviewPanel(
                        panel_id=f"sequence-group-{group_index + 1}",
                        kind="imr_chart",
                        label=f"{column.display_name} · {group_label}",
                        unit=column.unit,
                        status="succeeded",
                        result=result,
                    )
                )
            except IndividualsChartError as exc:
                panels.append(
                    GraphPreviewPanel(
                        panel_id=f"sequence-group-{group_index + 1}",
                        kind="imr_chart",
                        label=f"{column.display_name} · {group_label}",
                        unit=column.unit,
                        status="failed",
                        error_code=exc.code,
                    )
                )
        return panels, missing_group_row_count
    for index, column in enumerate(selected):
        try:
            if request.graph_type == "run_chart":
                result = calculate_run_chart(
                    _iter_filtered_rows(context, included_indices),
                    _run_column(column),
                    order_column=None if order is None else _run_column(order),
                    decimal=context.parsing.decimal,
                    thousands=context.parsing.thousands,
                    point_limit=request.point_limit,
                )
                kind: Literal["run_chart", "imr_chart"] = "run_chart"
            else:
                result = calculate_individuals_chart(
                    _iter_filtered_rows(context, included_indices),
                    _individuals_column(column),
                    order_column=None if order is None else _individuals_column(order),
                    decimal=context.parsing.decimal,
                    thousands=context.parsing.thousands,
                    point_limit=request.point_limit,
                )
                kind = "imr_chart"
            panels.append(
                GraphPreviewPanel(
                    panel_id=f"sequence-{index + 1}",
                    kind=kind,
                    label=column.display_name,
                    unit=column.unit,
                    status="succeeded",
                    result=result,
                )
            )
        except (RunChartError, IndividualsChartError) as exc:
            panels.append(
                GraphPreviewPanel(
                    panel_id=f"sequence-{index + 1}",
                    kind="run_chart" if request.graph_type == "run_chart" else "imr_chart",
                    label=column.display_name,
                    unit=column.unit,
                    status="failed",
                    error_code=exc.code,
                )
            )
    return panels, 0


def _numeric_columns(
    columns_by_id: dict[str, DatasetColumnRecord],
    column_ids: list[str],
) -> list[DatasetColumnRecord]:
    if len(set(column_ids)) != len(column_ids):
        raise ApiError(
            code="graph_preview_duplicate_column", message="같은 컬럼을 중복 선택했습니다."
        )
    selected: list[DatasetColumnRecord] = []
    for column_id in column_ids:
        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="graph_preview_column_not_found", message="선택한 컬럼을 찾을 수 없습니다."
            )
        if column.role == "id" or column.measurement_level == "id":
            raise ApiError(
                code="graph_preview_column_is_id",
                message="ID 컬럼은 그래프 수치 역할로 사용할 수 없습니다.",
            )
        if column.data_type not in NUMERIC_DATA_TYPES:
            raise ApiError(
                code="graph_preview_column_not_numeric", message="수치형 컬럼을 선택하세요."
            )
        selected.append(column)
    return selected


def _optional_group_column(
    columns_by_id: dict[str, DatasetColumnRecord],
    column_id: str | None,
) -> DatasetColumnRecord | None:
    if column_id is None:
        return None
    column = columns_by_id.get(column_id)
    if column is None:
        raise ApiError(
            code="graph_preview_group_column_not_found", message="그룹 컬럼을 찾을 수 없습니다."
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="graph_preview_group_column_is_id",
            message="ID 컬럼은 그룹 역할로 사용할 수 없습니다.",
        )
    return column


def _optional_order_column(
    columns_by_id: dict[str, DatasetColumnRecord],
    column_id: str | None,
) -> DatasetColumnRecord | None:
    if column_id is None:
        return None
    column = columns_by_id.get(column_id)
    if column is None:
        raise ApiError(
            code="graph_preview_order_column_not_found", message="순서 컬럼을 찾을 수 없습니다."
        )
    if column.data_type not in NUMERIC_DATA_TYPES | {"datetime"}:
        raise ApiError(
            code="graph_preview_order_column_invalid",
            message="숫자형 또는 날짜시간 순서 컬럼을 선택하세요.",
        )
    return column


def _rows_by_group(
    context: DatasetRowsContext,
    included_indices: tuple[int, ...] | None,
    group: DatasetColumnRecord,
) -> tuple[dict[str, list[list[str | None]]], int]:
    grouped: dict[str, list[list[str | None]]] = defaultdict(list)
    missing_group_row_count = 0
    for row in _iter_filtered_rows(context, included_indices):
        raw_value = row[group.column_index] if group.column_index < len(row) else None
        if raw_value is None or raw_value.strip() == "":
            missing_group_row_count += 1
            continue
        label = raw_value.strip()
        grouped[label].append(row)
        if len(grouped) > MAX_GROUP_LEVELS:
            raise ApiError(
                code="graph_preview_group_level_limit_exceeded",
                message="그룹 수준은 최대 20개까지 표시할 수 있습니다.",
            )
    return dict(grouped), missing_group_row_count


def _iter_filtered_rows(
    context: DatasetRowsContext,
    included_indices: tuple[int, ...] | None,
) -> Iterator[list[str | None]]:
    if included_indices is None:
        yield from iter_dataset_rows(context)
        return
    included = set(included_indices)
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if row_index in included:
            yield row


def _graphical_column(column: DatasetColumnRecord) -> GraphicalSummaryColumn:
    return GraphicalSummaryColumn(**_column_kwargs(column))


def _run_column(column: DatasetColumnRecord) -> RunChartColumn:
    return RunChartColumn(**_column_kwargs(column))


def _individuals_column(column: DatasetColumnRecord) -> IndividualsChartColumn:
    return IndividualsChartColumn(**_column_kwargs(column))


def _point_column(column: DatasetColumnRecord) -> GraphPointColumn:
    return GraphPointColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        unit=column.unit,
    )


def _column_kwargs(column: DatasetColumnRecord) -> dict[str, Any]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _safe_column_payload(column: DatasetColumnRecord) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "display_name": column.display_name,
        "unit": column.unit,
    }


def _only_summary_column(result: dict[str, object]) -> dict[str, Any]:
    columns = result.get("columns")
    if not isinstance(columns, list) or len(columns) != 1 or not isinstance(columns[0], dict):
        raise RuntimeError("graphical summary did not return one column")
    return columns[0]


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _point_error_message(code: str) -> str:
    if code == "individual_value_point_limit_exceeded":
        return (
            "Individual Value Plot은 현재 최대 2,000개 점을 표시합니다. "
            "필터를 적용하거나 Box Plot/Histogram을 사용하세요."
        )
    if code == "scatter_point_limit_exceeded":
        return "Scatter Plot 점 수가 표시 한도를 초과했습니다. 필터를 적용하세요."
    return "그룹 수준은 최대 20개까지 표시할 수 있습니다."
