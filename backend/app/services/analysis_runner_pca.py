from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import status
from pydantic import ValidationError

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisWarning,
    PrincipalComponentsOptions,
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
from app.statistics.principal_components import (
    PrincipalComponentsColumn,
    PrincipalComponentsError,
    calculate_principal_components,
)
from app.statistics.principal_components import (
    PrincipalComponentsOptions as StatisticsOptions,
)
from app.storage.metadata import DatasetColumnRecord


def run_principal_components_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise _api_error("dataset_version_required")
    options = _validate_options(request.options)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    columns = _selected_columns(context, options)
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
            result = calculate_principal_components(
                iter_rows_for_snapshot(context, row_snapshot),
                columns,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                options=StatisticsOptions(
                    matrix_type=options.matrix_type,
                    component_selection=options.component_selection,
                    component_count=options.component_count,
                    cumulative_threshold=options.cumulative_threshold,
                    outlier_alpha=options.outlier_alpha,
                    plot_point_limit=options.plot_point_limit,
                ),
            )
        except PrincipalComponentsError as exc:
            raise _api_error(exc.code) from exc
        return store_succeeded_analysis_result(
            settings=settings,
            request=request,
            context=context,
            analysis_id=analysis_id,
            completed_at=completed_at,
            row_snapshot=row_snapshot,
            result=result,
            warnings=_analysis_warnings(result),
        )
    except Exception:
        remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        raise


def _validate_options(value: dict[str, Any]) -> PrincipalComponentsOptions:
    try:
        return PrincipalComponentsOptions.model_validate(value)
    except ValidationError as exc:
        raise ApiError(
            code="invalid_principal_components_options",
            message="The Principal Components Analysis options are invalid.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


def _selected_columns(
    context: DatasetRowsContext,
    options: PrincipalComponentsOptions,
) -> list[PrincipalComponentsColumn]:
    columns_by_id = {column.column_id: column for column in context.columns}
    selected: list[PrincipalComponentsColumn] = []
    for column_id in options.column_ids:
        column = columns_by_id.get(column_id)
        if column is None:
            raise _api_error("pca_variable_not_found")
        _validate_column(column)
        selected.append(
            PrincipalComponentsColumn(
                column_id=column.column_id,
                column_index=column.column_index,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            )
        )
    return selected


def _validate_column(column: DatasetColumnRecord) -> None:
    if (
        column.data_type not in NUMERIC_DATA_TYPES
        or column.role == "id"
        or column.measurement_level == "id"
    ):
        raise _api_error("pca_variable_type_unsupported")


def _analysis_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    values = result.get("warnings")
    if not isinstance(values, list):
        return []
    return [
        AnalysisWarning(code=code, severity="warning", message=_warning_message(code))
        for code in values
        if isinstance(code, str)
    ]


def _warning_message(code: str) -> str:
    messages = {
        "pca_complete_case_rows_excluded": (
            "Rows with missing or non-numeric selected values were excluded."
        ),
        "pca_chart_points_limited": (
            "Charts use a deterministic bounded preview; calculations use every usable row."
        ),
        "pca_variables_not_less_than_rows": (
            "The number of variables is not less than the usable row count; "
            "some components are rank limited."
        ),
    }
    return messages.get(code, "Review the Principal Components Analysis warning.")


def _api_error(code: str) -> ApiError:
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    messages = {
        "dataset_version_required": "Principal Components Analysis requires a dataset version.",
        "pca_variable_not_found": "A selected PCA variable no longer exists.",
        "pca_variable_type_unsupported": "PCA currently supports numeric non-ID variables only.",
        "pca_variable_count_invalid": "Select between 2 and 50 numeric variables.",
        "pca_usable_rows_too_few": "PCA requires at least three complete usable rows.",
        "pca_usable_rows_limit": "PCA supports at most 20,000 usable rows.",
        "pca_constant_variable": "PCA cannot include a constant variable.",
        "pca_matrix_type_invalid": "The PCA matrix type is invalid.",
        "pca_component_count_invalid": "The requested component count is invalid for these data.",
        "pca_cumulative_threshold_invalid": (
            "The cumulative explained-variance threshold is invalid."
        ),
        "pca_component_selection_invalid": "The PCA component-selection mode is invalid.",
        "pca_plot_point_limit_invalid": "The PCA chart point limit is invalid.",
        "pca_eigendecomposition_failed": "The PCA eigen-decomposition could not be completed.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "PCA calculation failed."),
        status_code=status_code,
    )
