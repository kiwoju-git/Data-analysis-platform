import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from app.analyses.registry import METHODS
from app.api.v1.schemas.analyses import MethodAvailability
from app.main import create_app
from app.services.analysis_method_handlers import METHOD_EXECUTION_HANDLER_SPECS


@dataclass(frozen=True)
class OperationContract:
    route_name: str
    method: str
    path: str
    success_status: str
    response_schema: str | None
    parameters: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    request_media_types: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SchemaComponentContract:
    name: str
    properties: frozenset[str] = field(default_factory=frozenset)
    required_fields: frozenset[str] = field(default_factory=frozenset)
    enum_values: frozenset[str] | None = None
    property_refs: tuple[tuple[str, str], ...] = ()
    property_any_of_refs: tuple[tuple[str, frozenset[str]], ...] = ()
    array_item_refs: tuple[tuple[str, str], ...] = ()
    property_consts: tuple[tuple[str, object], ...] = ()
    additional_properties: bool | None = False


@dataclass(frozen=True)
class FrontendResultTypeFileContract:
    path: str
    summary_types: frozenset[str]


# This is the backend-side contract for frontend/src/api/routes.ts.
# It intentionally tracks only the routes used by the typed frontend client.
# When a frontend API route is added to `apiRoutes`, add the matching
# OperationContract here in the same change so backend pytest catches route drift.
FRONTEND_ROUTE_CONTRACTS = [
    OperationContract(
        route_name="health",
        method="get",
        path="/api/v1/health",
        success_status="200",
        response_schema="HealthResponse",
    ),
    OperationContract(
        route_name="datasets",
        method="post",
        path="/api/v1/datasets",
        success_status="201",
        response_schema="DatasetUploadResponse",
        request_media_types=frozenset({"multipart/form-data"}),
    ),
    OperationContract(
        route_name="datasetPaste",
        method="post",
        path="/api/v1/datasets/paste",
        success_status="201",
        response_schema="DatasetUploadResponse",
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="datasetConfirmParsing",
        method="post",
        path="/api/v1/datasets/{dataset_id}/confirm-parsing",
        success_status="201",
        response_schema="DatasetVersionResponse",
        parameters=frozenset({("dataset_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="datasetVersionSchema",
        method="patch",
        path="/api/v1/dataset-versions/{version_id}/schema",
        success_status="200",
        response_schema="DatasetSchemaResponse",
        parameters=frozenset({("version_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="datasetVersionRows",
        method="get",
        path="/api/v1/dataset-versions/{version_id}/rows",
        success_status="200",
        response_schema="DatasetRowsPreviewResponse",
        parameters=frozenset({("version_id", "path"), ("offset", "query"), ("limit", "query")}),
    ),
    OperationContract(
        route_name="datasetVersions",
        method="get",
        path="/api/v1/dataset-versions",
        success_status="200",
        response_schema="DatasetVersionCatalogResponse",
        parameters=frozenset({("limit", "query"), ("offset", "query")}),
    ),
    OperationContract(
        route_name="datasetVersionProfile",
        method="get",
        path="/api/v1/dataset-versions/{version_id}/profile",
        success_status="200",
        response_schema="DatasetProfileResponse",
        parameters=frozenset({("version_id", "path")}),
    ),
    OperationContract(
        route_name="analysisMethods",
        method="get",
        path="/api/v1/analysis-methods",
        success_status="200",
        response_schema="AnalysisMethodListResponse",
    ),
    OperationContract(
        route_name="analysisRuns",
        method="get",
        path="/api/v1/analysis-runs",
        success_status="200",
        response_schema="AnalysisRunListResponse",
        parameters=frozenset(
            {
                ("dataset_version_id", "query"),
                ("method_id", "query"),
                ("status", "query"),
                ("stale", "query"),
                ("result_available", "query"),
                ("limit", "query"),
                ("offset", "query"),
            }
        ),
    ),
    OperationContract(
        route_name="analysisRunsBase",
        method="post",
        path="/api/v1/analysis-runs",
        success_status="201",
        response_schema="AnalysisResultEnvelope",
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="analysisRunComparison",
        method="get",
        path="/api/v1/analysis-runs/comparison",
        success_status="200",
        response_schema="AnalysisRunComparisonResponse",
        parameters=frozenset({("left_analysis_id", "query"), ("right_analysis_id", "query")}),
    ),
    OperationContract(
        route_name="analysisRunResult",
        method="get",
        path="/api/v1/analysis-runs/{analysis_id}/result",
        success_status="200",
        response_schema="AnalysisResultEnvelope",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        route_name="analysisRunExportJson",
        method="post",
        path="/api/v1/analysis-runs/{analysis_id}/exports/json",
        success_status="201",
        response_schema="AnalysisResultJsonExportResponse",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        route_name="analysisRunExportCsv",
        method="post",
        path="/api/v1/analysis-runs/{analysis_id}/exports/csv",
        success_status="201",
        response_schema="AnalysisResultCsvExportResponse",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        route_name="analysisRunExportHtml",
        method="post",
        path="/api/v1/analysis-runs/{analysis_id}/exports/html",
        success_status="201",
        response_schema="AnalysisResultHtmlReportResponse",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        route_name="analysisRunExports",
        method="get",
        path="/api/v1/analysis-runs/{analysis_id}/exports",
        success_status="200",
        response_schema="AnalysisResultExportListResponse",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        route_name="analysisRunExportDownload",
        method="get",
        path="/api/v1/analysis-runs/{analysis_id}/exports/{export_id}/download",
        success_status="200",
        response_schema=None,
        parameters=frozenset({("analysis_id", "path"), ("export_id", "path")}),
    ),
    OperationContract(
        route_name="doeFactorialDesign",
        method="post",
        path="/api/v1/doe-designs/factorial",
        success_status="201",
        response_schema="FactorialDesignResponse",
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="doeResponseSurfaceDesign",
        method="post",
        path="/api/v1/doe-designs/response-surface",
        success_status="201",
        response_schema="ResponseSurfaceDesignResponse",
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="doeResponseSurfaceDesignById",
        method="get",
        path="/api/v1/doe-designs/response-surface/{design_id}",
        success_status="200",
        response_schema="ResponseSurfaceDesignResponse",
        parameters=frozenset({("design_id", "path")}),
    ),
    OperationContract(
        route_name="doeResponseSurfaceResponses",
        method="put",
        path="/api/v1/doe-designs/response-surface/{design_id}/responses",
        success_status="200",
        response_schema="DoeDesignResponsesResponse",
        parameters=frozenset({("design_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="doeResponseSurfaceAnalyses",
        method="post",
        path="/api/v1/doe-designs/response-surface/{design_id}/analyses",
        success_status="201",
        response_schema="DoeResponseSurfaceAnalysisResponse",
        parameters=frozenset({("design_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="doeResponseSurfaceAnalysis",
        method="get",
        path=("/api/v1/doe-designs/response-surface/{design_id}/analyses/{analysis_id}"),
        success_status="200",
        response_schema="DoeResponseSurfaceAnalysisResponse",
        parameters=frozenset({("design_id", "path"), ("analysis_id", "path")}),
    ),
    OperationContract(
        route_name="doeResponseSurfaceOptimizations",
        method="post",
        path="/api/v1/doe-designs/response-surface/{design_id}/optimizations",
        success_status="201",
        response_schema="ResponseOptimizerResponse",
        parameters=frozenset({("design_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="doeResponseSurfaceOptimization",
        method="get",
        path=(
            "/api/v1/doe-designs/response-surface/{design_id}/optimizations/" "{optimization_id}"
        ),
        success_status="200",
        response_schema="ResponseOptimizerResponse",
        parameters=frozenset({("design_id", "path"), ("optimization_id", "path")}),
    ),
    OperationContract(
        route_name="doeDesign",
        method="get",
        path="/api/v1/doe-designs/{design_id}",
        success_status="200",
        response_schema="FactorialDesignResponse",
        parameters=frozenset({("design_id", "path")}),
    ),
    OperationContract(
        route_name="doeDesignResponses",
        method="put",
        path="/api/v1/doe-designs/{design_id}/responses",
        success_status="200",
        response_schema="DoeDesignResponsesResponse",
        parameters=frozenset({("design_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="doeDesignResponses",
        method="get",
        path="/api/v1/doe-designs/{design_id}/responses",
        success_status="200",
        response_schema="DoeDesignResponsesResponse",
        parameters=frozenset({("design_id", "path")}),
    ),
    OperationContract(
        route_name="doeDesignAnalyses",
        method="post",
        path="/api/v1/doe-designs/{design_id}/analyses",
        success_status="201",
        response_schema="DoeFactorialAnalysisResponse",
        parameters=frozenset({("design_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="doeDesignAnalysis",
        method="get",
        path="/api/v1/doe-designs/{design_id}/analyses/{analysis_id}",
        success_status="200",
        response_schema="DoeFactorialAnalysisResponse",
        parameters=frozenset({("design_id", "path"), ("analysis_id", "path")}),
    ),
    OperationContract(
        route_name="regressionPredictionPreflight",
        method="post",
        path="/api/v1/regression-models/{model_id}/prediction-preflight",
        success_status="200",
        response_schema="RegressionPredictionPreflightResponse",
        parameters=frozenset({("model_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="regressionPredictions",
        method="post",
        path="/api/v1/regression-models/{model_id}/predictions",
        success_status="200",
        response_schema="RegressionPredictionResponse",
        parameters=frozenset({("model_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        route_name="regressionPredictionRows",
        method="get",
        path="/api/v1/regression-models/predictions/{prediction_id}/rows",
        success_status="200",
        response_schema="RegressionPredictionRowsPageResponse",
        parameters=frozenset({("prediction_id", "path"), ("limit", "query"), ("offset", "query")}),
    ),
    OperationContract(
        route_name="regressionPredictionCsvExport",
        method="post",
        path="/api/v1/regression-models/predictions/{prediction_id}/exports/csv",
        success_status="201",
        response_schema="RegressionPredictionCsvExportResponse",
        parameters=frozenset({("prediction_id", "path")}),
    ),
    OperationContract(
        route_name="gageRrPreflight",
        method="post",
        path="/api/v1/quality/gage-rr/preflight",
        success_status="200",
        response_schema="GageRrPreflightResponse",
        request_media_types=frozenset({"application/json"}),
    ),
]


# This is a field-level guard for the frontend/src/api/types/* surface.
# It intentionally checks only high-value fields the UI relies on. It is not
# full Pydantic-to-TypeScript generation and it permits additive backend fields;
# broader schema generation/diffing remains a separate hardening task.
FRONTEND_SCHEMA_COMPONENT_CONTRACTS = [
    SchemaComponentContract(
        name="HealthResponse",
        properties=frozenset({"status", "service", "version"}),
        required_fields=frozenset({"status", "service", "version"}),
        property_consts=(("status", "ready"), ("service", "datalab-studio-api")),
    ),
    SchemaComponentContract(
        name="AnalysisRunState",
        enum_values=frozenset(
            {"queued", "running", "succeeded", "failed", "cancel_requested", "cancelled"}
        ),
        additional_properties=None,
    ),
    SchemaComponentContract(
        name="AnalysisWarning",
        properties=frozenset({"code", "severity", "message"}),
        required_fields=frozenset({"code", "severity", "message"}),
    ),
    SchemaComponentContract(
        name="AnalysisProvenance",
        properties=frozenset(
            {
                "method_id",
                "method_version",
                "dataset_version_id",
                "source_schema_hash",
                "filter_snapshot_sha256",
                "row_snapshot_sha256",
                "row_count_total",
                "row_count_included",
                "app_version",
                "python_version",
                "platform",
                "build_commit",
                "package_versions",
            }
        ),
        required_fields=frozenset(
            {"method_id", "method_version", "dataset_version_id", "app_version"}
        ),
    ),
    SchemaComponentContract(
        name="DatasetColumnResponse",
        properties=frozenset(
            {
                "column_id",
                "version_id",
                "column_index",
                "original_name",
                "display_name",
                "data_type",
                "measurement_level",
                "role",
                "unit",
            }
        ),
        required_fields=frozenset(
            {
                "column_id",
                "version_id",
                "column_index",
                "original_name",
                "display_name",
                "data_type",
                "measurement_level",
                "role",
                "unit",
            }
        ),
        property_refs=(
            ("data_type", "DatasetColumnDataType"),
            ("measurement_level", "DatasetMeasurementLevel"),
            ("role", "DatasetColumnRole"),
        ),
    ),
    SchemaComponentContract(
        name="DatasetArtifactResponse",
        properties=frozenset(
            {
                "artifact_id",
                "version_id",
                "kind",
                "path",
                "sha256",
                "media_type",
                "size_bytes",
                "created_at",
            }
        ),
        required_fields=frozenset(
            {
                "artifact_id",
                "version_id",
                "kind",
                "path",
                "sha256",
                "media_type",
                "size_bytes",
                "created_at",
            }
        ),
    ),
    SchemaComponentContract(
        name="DatasetUploadResponse",
        properties=frozenset(
            {
                "dataset_id",
                "original_filename",
                "size_bytes",
                "sha256",
                "detected_format",
                "parsing",
                "warnings",
                "next_step",
            }
        ),
        required_fields=frozenset(
            {
                "dataset_id",
                "original_filename",
                "size_bytes",
                "sha256",
                "detected_format",
                "parsing",
                "warnings",
                "next_step",
            }
        ),
        property_refs=(("detected_format", "DatasetFormat"), ("parsing", "ParsingSuggestion")),
        array_item_refs=(("warnings", "UploadWarning"),),
        property_consts=(("next_step", "confirm_schema"),),
    ),
    SchemaComponentContract(
        name="DatasetVersionResponse",
        properties=frozenset(
            {
                "version_id",
                "dataset_id",
                "version_number",
                "row_count",
                "column_count",
                "schema_hash",
                "created_at",
                "source_sha256",
                "parsing",
                "columns",
                "canonical_artifact",
            }
        ),
        required_fields=frozenset(
            {
                "version_id",
                "dataset_id",
                "version_number",
                "row_count",
                "column_count",
                "schema_hash",
                "created_at",
                "source_sha256",
                "parsing",
                "columns",
                "canonical_artifact",
            }
        ),
        property_refs=(("parsing", "ConfirmedParsingOptions"),),
        array_item_refs=(("columns", "DatasetColumnResponse"),),
    ),
    SchemaComponentContract(
        name="DatasetRowsPreviewResponse",
        properties=frozenset(
            {"version_id", "offset", "limit", "total_rows", "returned_rows", "columns", "rows"}
        ),
        required_fields=frozenset(
            {"version_id", "offset", "limit", "total_rows", "returned_rows", "columns", "rows"}
        ),
        array_item_refs=(("columns", "DatasetColumnResponse"), ("rows", "DatasetPreviewRow")),
    ),
    SchemaComponentContract(
        name="DatasetPreviewRow",
        properties=frozenset({"row_index", "values"}),
        required_fields=frozenset({"row_index", "values"}),
    ),
    SchemaComponentContract(
        name="AnalysisMethodDescriptor",
        properties=frozenset(
            {
                "method_id",
                "method_version",
                "module_id",
                "label_ko",
                "label_en",
                "availability",
                "execution_mode",
                "requires_dataset",
                "order",
                "disabled_reason",
            }
        ),
        required_fields=frozenset(
            {
                "method_id",
                "method_version",
                "module_id",
                "label_ko",
                "label_en",
                "availability",
                "execution_mode",
                "requires_dataset",
                "order",
            }
        ),
        property_refs=(
            ("module_id", "AnalysisModuleId"),
            ("availability", "MethodAvailability"),
            ("execution_mode", "AnalysisExecutionMode"),
        ),
    ),
    SchemaComponentContract(
        name="AnalysisMethodListResponse",
        properties=frozenset({"modules", "methods"}),
        required_fields=frozenset({"modules", "methods"}),
        array_item_refs=(
            ("modules", "AnalysisModuleDescriptor"),
            ("methods", "AnalysisMethodDescriptor"),
        ),
    ),
    SchemaComponentContract(
        name="AnalysisRunListItemResponse",
        properties=frozenset(
            {
                "analysis_id",
                "method_id",
                "method_version",
                "dataset_version_id",
                "status",
                "stale",
                "result_available",
                "artifact_count",
                "created_at",
                "updated_at",
                "completed_at",
            }
        ),
        required_fields=frozenset(
            {
                "analysis_id",
                "method_id",
                "method_version",
                "dataset_version_id",
                "status",
                "stale",
                "result_available",
                "artifact_count",
                "created_at",
                "updated_at",
                "completed_at",
            }
        ),
        property_refs=(("status", "AnalysisRunState"),),
    ),
    SchemaComponentContract(
        name="AnalysisRunListResponse",
        properties=frozenset(
            {
                "dataset_version_id",
                "method_id",
                "status",
                "stale",
                "result_available",
                "limit",
                "offset",
                "returned_count",
                "has_more",
                "runs",
            }
        ),
        required_fields=frozenset(
            {"dataset_version_id", "limit", "offset", "returned_count", "has_more", "runs"}
        ),
        array_item_refs=(("runs", "AnalysisRunListItemResponse"),),
    ),
    SchemaComponentContract(
        name="AnalysisResultEnvelope",
        properties=frozenset(
            {
                "analysis_id",
                "method_id",
                "method_version",
                "dataset_version_id",
                "status",
                "warnings",
                "provenance",
                "result",
            }
        ),
        required_fields=frozenset(
            {
                "analysis_id",
                "method_id",
                "method_version",
                "dataset_version_id",
                "status",
                "warnings",
                "provenance",
            }
        ),
        property_any_of_refs=(
            (
                "provenance",
                frozenset({"AnalysisProvenance", "RegressionPredictionProvenance"}),
            ),
        ),
        array_item_refs=(("warnings", "AnalysisWarning"),),
    ),
    SchemaComponentContract(
        name="DoeFactorialAnalysisCreateRequest",
        properties=frozenset(
            {"response_name", "max_interaction_order", "confidence_level", "point_limit"}
        ),
        required_fields=frozenset({"response_name"}),
    ),
    SchemaComponentContract(
        name="DoeFactorialAnalysisResponse",
        properties=frozenset(
            {
                "analysis_id",
                "design_id",
                "design_version_id",
                "design_version_number",
                "method_id",
                "method_version",
                "analysis_schema_version",
                "design_sha256",
                "response_sha256",
                "response_name",
                "created_at",
                "app_version",
                "python_version",
                "platform",
                "build_commit",
                "package_versions",
                "result",
            }
        ),
        required_fields=frozenset(
            {
                "analysis_id",
                "design_id",
                "design_version_id",
                "design_version_number",
                "method_id",
                "method_version",
                "analysis_schema_version",
                "design_sha256",
                "response_sha256",
                "response_name",
                "created_at",
                "app_version",
                "python_version",
                "platform",
                "build_commit",
                "package_versions",
                "result",
            }
        ),
        property_refs=(("result", "DoeFactorialAnalysisResult"),),
    ),
    SchemaComponentContract(
        name="DoeFactorialAnalysisResult",
        properties=frozenset(
            {
                "schema_version",
                "summary_type",
                "method",
                "response",
                "factor_names",
                "coding",
                "model_policy",
                "sample",
                "fit",
                "terms",
                "ranked_effects",
                "anova",
                "diagnostics",
                "plots",
                "warnings",
            }
        ),
        required_fields=frozenset(
            {
                "schema_version",
                "summary_type",
                "method",
                "response",
                "factor_names",
                "coding",
                "model_policy",
                "sample",
                "fit",
                "terms",
                "ranked_effects",
                "anova",
                "diagnostics",
                "plots",
                "warnings",
            }
        ),
        property_consts=(("schema_version", 1), ("summary_type", "factorial_analysis")),
    ),
    SchemaComponentContract(
        name="ResponseSurfaceDesignCreateRequest",
        properties=frozenset(
            {
                "name",
                "factors",
                "alpha_mode",
                "factorial_replicates",
                "axial_replicates",
                "center_points",
                "randomize",
                "randomization_seed",
            }
        ),
        required_fields=frozenset({"factors", "randomization_seed"}),
        array_item_refs=(("factors", "DoeFactorRequest"),),
    ),
    SchemaComponentContract(
        name="ResponseSurfaceDesignResponse",
        properties=frozenset(
            {
                "design_id",
                "design_version_id",
                "version_number",
                "method_id",
                "method_version",
                "family",
                "name",
                "status",
                "created_at",
                "updated_at",
                "app_version",
                "factors",
                "options",
                "run_count",
                "design_sha256",
                "runs",
            }
        ),
        required_fields=frozenset(
            {
                "design_id",
                "design_version_id",
                "version_number",
                "method_id",
                "method_version",
                "family",
                "name",
                "status",
                "created_at",
                "updated_at",
                "app_version",
                "factors",
                "options",
                "run_count",
                "design_sha256",
                "runs",
            }
        ),
        property_refs=(("options", "ResponseSurfaceDesignOptionsResponse"),),
        array_item_refs=(
            ("factors", "DoeFactorResponse"),
            ("runs", "ResponseSurfaceDesignRunResponse"),
        ),
        property_consts=(
            ("method_id", "doe.response_surface"),
            ("family", "central_composite_inscribed"),
        ),
    ),
    SchemaComponentContract(
        name="DoeResponseSurfaceAnalysisCreateRequest",
        properties=frozenset(
            {"response_name", "confidence_level", "point_limit", "contour_grid_size"}
        ),
        required_fields=frozenset({"response_name"}),
    ),
    SchemaComponentContract(
        name="DoeResponseSurfaceAnalysisResponse",
        properties=frozenset(
            {
                "analysis_id",
                "design_id",
                "design_version_id",
                "design_version_number",
                "method_id",
                "method_version",
                "analysis_schema_version",
                "design_sha256",
                "response_sha256",
                "response_name",
                "created_at",
                "app_version",
                "python_version",
                "platform",
                "build_commit",
                "package_versions",
                "result",
            }
        ),
        required_fields=frozenset(
            {
                "analysis_id",
                "design_id",
                "design_version_id",
                "design_version_number",
                "method_id",
                "method_version",
                "analysis_schema_version",
                "design_sha256",
                "response_sha256",
                "response_name",
                "created_at",
                "app_version",
                "python_version",
                "platform",
                "build_commit",
                "package_versions",
                "result",
            }
        ),
        property_refs=(("result", "DoeResponseSurfaceAnalysisResult"),),
        property_consts=(("method_id", "doe.response_surface"),),
    ),
    SchemaComponentContract(
        name="DoeResponseSurfaceAnalysisResult",
        properties=frozenset(
            {
                "schema_version",
                "summary_type",
                "method",
                "response",
                "factor_names",
                "coding",
                "model_policy",
                "sample",
                "fit",
                "terms",
                "anova",
                "stationary_point",
                "contour",
                "diagnostics",
                "warnings",
            }
        ),
        required_fields=frozenset(
            {
                "schema_version",
                "summary_type",
                "method",
                "response",
                "factor_names",
                "coding",
                "model_policy",
                "sample",
                "fit",
                "terms",
                "anova",
                "stationary_point",
                "contour",
                "diagnostics",
                "warnings",
            }
        ),
        property_refs=(
            ("stationary_point", "DoeResponseSurfaceStationaryPointResponse"),
            ("contour", "DoeResponseSurfaceContourResponse"),
        ),
        array_item_refs=(("terms", "DoeResponseSurfaceTermResponse"),),
        property_consts=(
            ("schema_version", 1),
            ("summary_type", "response_surface_analysis"),
            ("method", "full_quadratic_ordinary_least_squares"),
        ),
    ),
    SchemaComponentContract(
        name="ResponseOptimizerCreateRequest",
        properties=frozenset({"objectives", "factor_bounds", "linear_constraints", "search"}),
        required_fields=frozenset({"objectives"}),
        property_refs=(("search", "ResponseOptimizerSearchOptionsRequest"),),
        array_item_refs=(
            ("objectives", "ResponseOptimizerObjectiveRequest"),
            ("factor_bounds", "ResponseOptimizerFactorBoundRequest"),
            ("linear_constraints", "ResponseOptimizerLinearConstraintRequest"),
        ),
    ),
    SchemaComponentContract(
        name="ResponseOptimizerObjectiveRequest",
        properties=frozenset(
            {
                "source_analysis_id",
                "goal",
                "lower",
                "target",
                "upper",
                "lower_weight",
                "upper_weight",
                "importance",
            }
        ),
        required_fields=frozenset({"source_analysis_id", "goal"}),
    ),
    SchemaComponentContract(
        name="ResponseOptimizerSearchOptionsRequest",
        properties=frozenset(
            {
                "random_seed",
                "random_candidate_count",
                "multi_start_count",
                "max_iterations",
                "max_evaluations",
                "time_budget_ms",
            }
        ),
    ),
    SchemaComponentContract(
        name="ResponseOptimizerResponse",
        properties=frozenset(
            {
                "optimization_id",
                "design_id",
                "design_version_id",
                "design_version_number",
                "method_id",
                "method_version",
                "config_schema_version",
                "result_schema_version",
                "config_sha256",
                "design_sha256",
                "source_analysis_ids",
                "source_bundle_sha256",
                "created_at",
                "app_version",
                "python_version",
                "platform",
                "build_commit",
                "package_versions",
                "result",
            }
        ),
        required_fields=frozenset(
            {
                "optimization_id",
                "design_id",
                "design_version_id",
                "design_version_number",
                "method_id",
                "method_version",
                "config_schema_version",
                "result_schema_version",
                "config_sha256",
                "design_sha256",
                "source_analysis_ids",
                "source_bundle_sha256",
                "created_at",
                "app_version",
                "python_version",
                "platform",
                "build_commit",
                "package_versions",
                "result",
            }
        ),
        property_refs=(("result", "ResponseOptimizerResult"),),
        property_consts=(("method_id", "regression.response_optimizer"),),
    ),
    SchemaComponentContract(
        name="ResponseOptimizerResult",
        properties=frozenset(
            {
                "schema_version",
                "summary_type",
                "method",
                "model_policy",
                "factor_region",
                "objectives",
                "recommendation",
                "search",
                "warnings",
            }
        ),
        required_fields=frozenset(
            {
                "schema_version",
                "summary_type",
                "method",
                "model_policy",
                "factor_region",
                "objectives",
                "recommendation",
                "search",
                "warnings",
            }
        ),
        property_refs=(
            ("model_policy", "ResponseOptimizerModelPolicyResponse"),
            ("factor_region", "ResponseOptimizerFactorRegionResponse"),
            ("recommendation", "ResponseOptimizerRecommendationResponse"),
            ("search", "ResponseOptimizerSearchResponse"),
        ),
        array_item_refs=(("objectives", "ResponseOptimizerObjectiveResponse"),),
        property_consts=(
            ("schema_version", 1),
            ("summary_type", "response_optimizer"),
            ("method", "derringer_suich_bounded_multistart_slsqp"),
        ),
    ),
    SchemaComponentContract(
        name="RegressionPredictionProvenance",
        properties=frozenset(
            {
                "method_id",
                "method_version",
                "dataset_version_id",
                "app_version",
                "python_version",
                "platform",
                "build_commit",
                "package_versions",
                "source_analysis_id",
                "source_analysis_stale_at_prediction",
                "source_dataset_version_id",
                "source_schema_hash_at_fit",
                "source_schema_hash_current",
                "target_dataset_version_id",
                "target_schema_hash",
                "model_id",
                "model_manifest_sha256",
                "prediction_schema_version",
                "model_manifest_schema_version",
                "missing_policy",
                "confidence_level",
                "include_intervals",
                "source_canonical_artifact_sha256",
                "target_canonical_artifact_sha256",
                "created_at",
            }
        ),
        required_fields=frozenset(
            {
                "method_id",
                "method_version",
                "dataset_version_id",
                "app_version",
                "source_analysis_id",
                "source_analysis_stale_at_prediction",
                "source_dataset_version_id",
                "source_schema_hash_at_fit",
                "source_schema_hash_current",
                "target_dataset_version_id",
                "target_schema_hash",
                "model_id",
                "model_manifest_sha256",
                "prediction_schema_version",
                "model_manifest_schema_version",
                "missing_policy",
                "confidence_level",
                "include_intervals",
                "source_canonical_artifact_sha256",
                "target_canonical_artifact_sha256",
                "created_at",
            }
        ),
    ),
    SchemaComponentContract(
        name="AnalysisResultExportListItemResponse",
        properties=frozenset(
            {
                "export_id",
                "analysis_id",
                "artifact_kind",
                "media_type",
                "sha256",
                "created_at",
                "download_url",
            }
        ),
        required_fields=frozenset(
            {
                "export_id",
                "analysis_id",
                "artifact_kind",
                "media_type",
                "sha256",
                "created_at",
                "download_url",
            }
        ),
    ),
    SchemaComponentContract(
        name="AnalysisResultExportListResponse",
        properties=frozenset({"analysis_id", "exports"}),
        required_fields=frozenset({"analysis_id", "exports"}),
        array_item_refs=(("exports", "AnalysisResultExportListItemResponse"),),
    ),
]


FRONTEND_RESULT_TYPE_FILE_CONTRACTS = [
    FrontendResultTypeFileContract(
        path="frontend/src/api/types/analysisResultsExploration.ts",
        summary_types=frozenset(
            {
                "descriptive_statistics",
                "graphical_summary",
                "normality_test",
                "equal_variances_test",
            }
        ),
    ),
    FrontendResultTypeFileContract(
        path="frontend/src/api/types/analysisResultsHypothesis.ts",
        summary_types=frozenset(
            {
                "one_sample_t_test",
                "paired_t_test",
                "one_sample_wilcoxon_signed_rank_test",
                "two_sample_t_test",
                "mann_whitney_u_test",
                "kruskal_wallis_test",
                "one_way_anova",
                "equivalence_tost",
            }
        ),
    ),
    FrontendResultTypeFileContract(
        path="frontend/src/api/types/analysisResultsCategorical.ts",
        summary_types=frozenset(
            {"one_proportion_test", "two_proportion_test", "chi_square_association"}
        ),
    ),
    FrontendResultTypeFileContract(
        path="frontend/src/api/types/analysisResultsRegression.ts",
        summary_types=frozenset({"pearson_correlation", "xy_correlation_matrix", "linear_model"}),
    ),
    FrontendResultTypeFileContract(
        path="frontend/src/api/types/analysisResultsQuality.ts",
        summary_types=frozenset(
            {
                "attribute_control_chart",
                "individuals_chart",
                "subgroup_chart",
                "run_chart",
                "capability_analysis",
                "gage_rr",
                "gage_run_chart",
                "gage_rr_preflight",
            }
        ),
    ),
    FrontendResultTypeFileContract(
        path="frontend/src/api/types/doe.ts",
        summary_types=frozenset(
            {"factorial_analysis", "response_surface_analysis", "response_optimizer"}
        ),
    ),
]

NON_ANALYSIS_RUN_RESULT_SUMMARY_TYPES = frozenset(
    {
        "factorial_analysis",
        "response_surface_analysis",
        "response_optimizer",
        "gage_rr_preflight",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _frontend_api_route_names() -> frozenset[str]:
    text = (_repo_root() / "frontend/src/api/routes.ts").read_text(encoding="utf-8")
    route_map_match = re.search(r"export const apiRoutes = \{(?P<body>.*)\n\};", text, re.DOTALL)
    assert route_map_match is not None
    return frozenset(
        re.findall(r"^\s{2}([A-Za-z][A-Za-z0-9]*)\(", route_map_match.group("body"), re.MULTILINE)
    )


def _frontend_summary_type_literals(relative_path: str) -> frozenset[str]:
    text = (_repo_root() / relative_path).read_text(encoding="utf-8")
    return frozenset(re.findall(r'summary_type:\s*"([^"]+)";', text))


def _markdown_h2_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    assert match is not None, f"Missing markdown section: {heading}"
    return match.group("body")


def _markdown_table_cells_for_method(text: str, method_id: str) -> list[str]:
    match = re.search(
        rf"^\| `{re.escape(method_id)}` \|(?P<row>.*)\|$",
        text,
        re.MULTILINE,
    )
    assert match is not None, f"Missing markdown table row for {method_id}"
    return [cell.strip() for cell in match.group(0).strip().strip("|").split("|")]


def _operation_parameters(operation: dict[str, Any]) -> frozenset[tuple[str, str]]:
    return frozenset(
        (parameter["name"], parameter["in"]) for parameter in operation.get("parameters", [])
    )


def _request_media_types(operation: dict[str, Any]) -> frozenset[str]:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return frozenset()
    content = request_body.get("content")
    if not isinstance(content, dict):
        return frozenset()
    return frozenset(content.keys())


def _json_response_ref(operation: dict[str, Any], status_code: str) -> str | None:
    response = operation["responses"][status_code]
    content = response.get("content")
    if not isinstance(content, dict):
        return None
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return None
    schema = json_content.get("schema")
    if not isinstance(schema, dict):
        return None
    ref = schema.get("$ref")
    return ref if isinstance(ref, str) else None


def _schema_ref_name(schema: dict[str, Any]) -> str | None:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return None
    return ref.removeprefix("#/components/schemas/")


def _schema_any_of_ref_names(schema: dict[str, Any]) -> frozenset[str]:
    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return frozenset()
    return frozenset(
        ref_name
        for candidate in any_of
        if isinstance(candidate, dict)
        if (ref_name := _schema_ref_name(candidate)) is not None
    )


def _array_item_ref_name(schema: dict[str, Any]) -> str | None:
    items = schema.get("items")
    if not isinstance(items, dict):
        return None
    return _schema_ref_name(items)


@pytest.fixture(scope="module")
def openapi_schema() -> dict[str, Any]:
    return create_app().openapi()


@pytest.mark.parametrize(
    "contract",
    FRONTEND_ROUTE_CONTRACTS,
    ids=lambda contract: f"{contract.method.upper()} {contract.path}",
)
def test_frontend_route_contract_is_present_in_openapi(
    openapi_schema: dict[str, Any],
    contract: OperationContract,
) -> None:
    paths = openapi_schema["paths"]

    assert contract.path in paths
    assert contract.method in paths[contract.path]

    operation = paths[contract.path][contract.method]
    assert _operation_parameters(operation) == contract.parameters
    assert _request_media_types(operation) == contract.request_media_types
    assert contract.success_status in operation["responses"]

    if contract.response_schema is None:
        return

    expected_ref = f"#/components/schemas/{contract.response_schema}"
    assert _json_response_ref(operation, contract.success_status) == expected_ref
    assert contract.response_schema in openapi_schema["components"]["schemas"]


def test_frontend_route_map_names_are_covered_by_openapi_contracts() -> None:
    route_map_names = _frontend_api_route_names()
    contracted_route_names = frozenset(contract.route_name for contract in FRONTEND_ROUTE_CONTRACTS)

    assert route_map_names == contracted_route_names


def test_frontend_api_modules_use_central_route_map() -> None:
    frontend_api_root = _repo_root() / "frontend/src/api"
    direct_endpoint_files = []
    for path in sorted(frontend_api_root.glob("*.ts")):
        if path.name == "routes.ts":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"""["'`]/api/v1""", text):
            direct_endpoint_files.append(path.relative_to(_repo_root()).as_posix())

    assert direct_endpoint_files == []


def test_workbench_saved_result_state_is_owned_by_dedicated_hooks() -> None:
    app_text = (_repo_root() / "frontend/src/App.tsx").read_text(encoding="utf-8")
    shell_text = (_repo_root() / "frontend/src/AnalysisShell.tsx").read_text(encoding="utf-8")
    workbench_text = (_repo_root() / "frontend/src/AnalysisWorkbench.tsx").read_text(
        encoding="utf-8",
    )
    hook_imports = {
        "useAnalysisComparisonState": "frontend/src/useAnalysisComparisonState.ts",
        "useAnalysisExportState": "frontend/src/useAnalysisExportState.ts",
        "useAnalysisHistoryState": "frontend/src/useAnalysisHistoryState.ts",
        "useRestoredAnalysisResultState": "frontend/src/useRestoredAnalysisResultState.ts",
    }

    for hook_name in hook_imports:
        assert f'import {{ {hook_name} }} from "./{hook_name}";' in app_text

    expected_grouped_app_props = {
        "workbenchComparisonState: analysisComparisonState",
        "workbenchExportState: analysisExportState",
        "workbenchHistoryState: analysisHistoryState",
        "workbenchRestoredState: restoredAnalysisResultState",
    }
    for grouped_prop in expected_grouped_app_props:
        assert grouped_prop in app_text

    forbidden_app_spreads = {
        "...analysisComparisonState",
        "...analysisExportState",
        "...analysisHistoryState",
        "...restoredAnalysisResultState",
    }
    for spread in forbidden_app_spreads:
        assert spread not in app_text

    expected_shell_grouped_props = {
        "comparisonState={workbenchComparisonState}",
        "exportState={workbenchExportState}",
        "historyState={workbenchHistoryState}",
        "restoredState={workbenchRestoredState}",
    }
    for grouped_prop in expected_shell_grouped_props:
        assert grouped_prop in shell_text

    expected_workbench_state_types = {
        "export interface AnalysisWorkbenchComparisonState",
        "export interface AnalysisWorkbenchExportState",
        "export interface AnalysisWorkbenchHistoryState",
        "export interface AnalysisWorkbenchRestoredState",
    }
    for type_name in expected_workbench_state_types:
        assert type_name in workbench_text

    forbidden_legacy_saved_result_props = {
        "analysisHistory?:",
        "analysisComparison?:",
        "analysisResultExportList?:",
        "analysisResultJsonExport?:",
        "restoredAnalysisResult?:",
        "onRefreshAnalysisHistory?:",
        "onRestoreAnalysisRun?:",
    }
    shell_props = shell_text.split("export interface AnalysisShellProps", 1)[1].split(
        "export function AnalysisShell",
        1,
    )[0]
    workbench_props = workbench_text.split("interface AnalysisWorkbenchProps", 1)[1].split(
        "const workbenchSteps",
        1,
    )[0]
    for legacy_prop in forbidden_legacy_saved_result_props:
        assert legacy_prop not in shell_props
        assert legacy_prop not in workbench_props

    forbidden_app_api_symbols = {
        "fetchAnalysisRuns",
        "fetchAnalysisRunResult",
        "fetchAnalysisRunComparison",
        "fetchAnalysisResultExports",
        "createAnalysisResultJsonExport",
        "createAnalysisResultCsvExport",
        "createAnalysisResultHtmlReport",
        "downloadAnalysisResultExport",
        "AnalysisRunListResponse",
        "AnalysisRunComparisonResponse",
        "AnalysisResultExportListResponse",
        "AnalysisResultJsonExportResponse",
        "AnalysisResultCsvExportResponse",
        "AnalysisResultHtmlReportResponse",
    }
    app_api_import = re.search(r'import \{(?P<body>.*?)\} from "\./api";', app_text, re.DOTALL)
    assert app_api_import is not None
    app_api_import_body = app_api_import.group("body")
    for symbol in forbidden_app_api_symbols:
        assert symbol not in app_api_import_body

    expected_hook_api_symbols = {
        "frontend/src/useAnalysisHistoryState.ts": {"fetchAnalysisRuns"},
        "frontend/src/useAnalysisExportState.ts": {
            "createAnalysisResultCsvExport",
            "createAnalysisResultHtmlReport",
            "createAnalysisResultJsonExport",
            "downloadAnalysisResultExport",
            "fetchAnalysisResultExports",
        },
        "frontend/src/useAnalysisComparisonState.ts": {"fetchAnalysisRunComparison"},
        "frontend/src/useRestoredAnalysisResultState.ts": {"fetchAnalysisRunResult"},
    }
    expected_hook_state_markers = {
        "frontend/src/useAnalysisHistoryState.ts": {
            "resetAnalysisHistoryState",
            "onRefreshAnalysisHistory",
            "ANALYSIS_HISTORY_PAGE_SIZE",
            "useEffect(() =>",
            "resetKey",
        },
        "frontend/src/useAnalysisExportState.ts": {
            "resetAnalysisExportState",
            "clearAnalysisExportErrors",
            "onRefreshAnalysisResultExports",
            "useEffect(() =>",
            "resetKey",
        },
        "frontend/src/useAnalysisComparisonState.ts": {
            "resetAnalysisComparisonState",
            "analysis_comparison_requires_two_runs",
            "onCompareAnalysisRuns",
            "useEffect(() =>",
            "resetKey",
        },
        "frontend/src/useRestoredAnalysisResultState.ts": {
            "resetRestoredAnalysisResultState",
            "onRestoreAnalysisRun",
            "onRefreshAnalysisResultExports",
            "onSelectMethod",
            "useEffect(() =>",
            "resetKey",
        },
    }
    expected_hook_cleanup_markers = {
        "frontend/src/useAnalysisHistoryState.ts": {
            "historyRequest.cancel(request)",
            "setIsLoadingAnalysisHistory(false)",
        },
        "frontend/src/useAnalysisExportState.ts": {
            "cancelAnalysisExportRequests",
            "return cancelAnalysisExportRequests",
        },
        "frontend/src/useAnalysisComparisonState.ts": {
            "comparisonRequest.cancel()",
            "setIsComparingAnalysisRuns(false)",
        },
        "frontend/src/useRestoredAnalysisResultState.ts": {
            "restoreRequest.cancel()",
            "setIsRestoringAnalysisResult(false)",
        },
    }
    all_saved_result_api_symbols = set().union(*expected_hook_api_symbols.values())
    for relative_path, symbols in expected_hook_api_symbols.items():
        hook_text = (_repo_root() / relative_path).read_text(encoding="utf-8")
        for symbol in symbols:
            assert symbol in hook_text
        for symbol in all_saved_result_api_symbols - symbols:
            assert symbol not in hook_text
        for marker in expected_hook_state_markers[relative_path]:
            assert marker in hook_text
        assert 'from "./latestRequest"' in hook_text
        assert ".isCurrent(" in hook_text
        assert ".cancel(" in hook_text
        for marker in expected_hook_cleanup_markers[relative_path]:
            assert marker in hook_text


def test_ci_e2e_diagnostics_contract_preserves_safe_artifact_scope() -> None:
    workflow_text = (_repo_root() / ".github/workflows/ci.yml").read_text(
        encoding="utf-8",
    )
    e2e_script_text = (_repo_root() / "scripts/e2e.ps1").read_text(encoding="utf-8")
    critical_path_text = (_repo_root() / "tests/e2e/critical_path.py").read_text(
        encoding="utf-8",
    )

    assert "workflow_dispatch:" in workflow_text
    assert "e2e:" in workflow_text
    assert "needs: windows" in workflow_text
    assert "DATALAB_E2E_ROOT:" in workflow_text
    assert "DATALAB_E2E_DIAGNOSTICS_ROOT:" in workflow_text
    assert '-WorkspaceRoot "${{ env.DATALAB_E2E_ROOT }}"' in workflow_text
    assert '-DiagnosticsRoot "${{ env.DATALAB_E2E_DIAGNOSTICS_ROOT }}"' in workflow_text
    assert "name: e2e-logs" in workflow_text

    artifact_upload_block = workflow_text.split("name: e2e-logs", 1)[1]
    assert "${{ env.DATALAB_E2E_DIAGNOSTICS_ROOT }}\\**\\logs\\*.log" in artifact_upload_block
    assert (
        "${{ env.DATALAB_E2E_DIAGNOSTICS_ROOT }}\\**\\screenshots\\*.png" in artifact_upload_block
    )
    assert "${{ env.DATALAB_E2E_DIAGNOSTICS_ROOT }}\\**\\html\\*.html" in artifact_upload_block
    assert "if-no-files-found: ignore" in artifact_upload_block
    assert "env.DATALAB_E2E_ROOT" not in artifact_upload_block

    assert "[string]$DiagnosticsRoot" in e2e_script_text
    assert '"--diagnostics-root", "$DiagnosticsRoot"' in e2e_script_text
    assert '"--workspace-root", "$WorkspaceRoot"' in e2e_script_text

    assert 'parser.add_argument("--diagnostics-root"' in critical_path_text
    assert 'diagnostics.record("E2E diagnostics initialized")' in critical_path_text
    assert "class ManagedProcess" in critical_path_text
    assert "current_step_slug" in critical_path_text
    assert "failure-{step_slug}-" in critical_path_text
    assert "describe_page(page)" in critical_path_text
    assert "readiness timed out" in critical_path_text
    assert (
        critical_path_text.count(
            "print_log_tail(managed_process.log_path, managed_process.label)",
        )
        >= 2
    )


def test_ci_status_doc_tracks_remote_verification_checklist() -> None:
    workflow_text = (_repo_root() / ".github/workflows/ci.yml").read_text(
        encoding="utf-8",
    )
    ci_status_text = (_repo_root() / "docs/ci_status.md").read_text(encoding="utf-8")
    workflow_section = _markdown_h2_section(ci_status_text, "Workflow Configuration")
    local_validation_section = _markdown_h2_section(ci_status_text, "Local Validation")
    historical_validation_section = _markdown_h2_section(
        ci_status_text,
        "Historical Local Validation",
    )
    remote_section = _markdown_h2_section(
        ci_status_text,
        "Remote GitHub Actions Verification",
    )

    assert "workflow_dispatch:" in workflow_text
    assert "needs: windows" in workflow_text
    assert "name: e2e-logs" in workflow_text
    for phrase in (
        "workflow_dispatch",
        "pull_request",
        "push",
        "`windows-latest`",
        "Python `3.10`",
        "Node `22`",
        "scripts\\check.ps1",
        "scripts\\e2e.ps1",
        "`e2e-logs`",
    ):
        assert phrase in workflow_section

    assert "latest recorded backend pytest count is 564" in local_validation_section
    assert "latest recorded frontend Vitest count is 86" in local_validation_section
    assert "The latest run passed backend ruff check" not in local_validation_section
    assert "That 2026-07-09 run passed backend ruff check" in historical_validation_section
    assert "That 2026-07-07 run passed backend ruff check" in historical_validation_section

    for phrase in (
        "has not been directly verified",
        "could not be performed here",
        "Branch protection and repository settings were not changed",
        "gh auth status --hostname github.com",
        "gh run list --repo kiwoju-git/Data-analysis-platform",
        "--workflow ci.yml",
        "gh run view <run-id>",
        "--json status,conclusion,headSha,workflowName,jobs",
        "gh run download <run-id>",
        "--name e2e-logs",
        "gh workflow run ci.yml",
        "--ref main",
        "windows",
        "e2e",
        "needs: windows",
        "workflow_dispatch",
        "Do not change repository settings",
    ):
        assert phrase in remote_section


def test_e2e_coverage_doc_tracks_current_smoke_step_markers() -> None:
    critical_path_text = (_repo_root() / "tests/e2e/critical_path.py").read_text(
        encoding="utf-8",
    )
    coverage_doc_text = (_repo_root() / "docs/e2e_coverage.md").read_text(
        encoding="utf-8",
    )

    code_step_markers = re.findall(
        r'diagnostics\.step\("([^"]+)"\)',
        critical_path_text,
    )
    section_match = re.search(
        r"## Current Step Markers\n\n(?P<body>.*?)(?:\n## |\Z)",
        coverage_doc_text,
        re.DOTALL,
    )

    assert code_step_markers
    assert section_match is not None
    documented_step_markers = re.findall(r"- `([^`]+)`", section_match.group("body"))
    assert documented_step_markers == code_step_markers


def test_e2e_critical_path_keeps_linear_model_prediction_browser_flow() -> None:
    critical_path_text = (_repo_root() / "tests/e2e/critical_path.py").read_text(
        encoding="utf-8",
    )
    helper = critical_path_text.split(
        "def verify_linear_model_fit_and_prediction(page: Page) -> None:",
        maxsplit=1,
    )[1].split("\ndef ", maxsplit=1)[0]

    assert "REGRESSION_SAMPLE_DATA" in critical_path_text
    assert "REGRESSION_TARGET_DATA" in critical_path_text
    for required_contract in (
        'row_label="12행", column_label="3컬럼"',
        'name=re.compile(r"상관관계 및 회귀분석")',
        'name=re.compile(r"^회귀모형 적합")',
        'select_option(label="y")',
        'name="회귀모형 적합 실행"',
        'get_by_label("예측 대상 데이터셋 버전")',
        'has_text="4행 × 3열"',
        'get_by_label("예측 사전점검 요약")',
        'to_contain_text("예측 준비 가능")',
        'to_contain_text("4 / 4")',
        'to_contain_text("다름")',
        'name="예측 실행"',
        'get_by_label("예측 결과 요약")',
        "to_have_count(4)",
        'has_text="Prediction interval"',
        'name="전체 예측 CSV 생성"',
        'name="전체 예측 CSV 다운로드"',
        'suggested_filename.endswith(".csv")',
    ):
        assert required_contract in helper


def test_beginner_usability_walkthrough_keeps_required_qa_checklist_scope() -> None:
    text = (_repo_root() / "docs/beginner_usability_walkthrough.md").read_text(
        encoding="utf-8",
    )
    expected_scenarios = {
        "Two Group Mean Comparison": "`hypothesis.two_sample_t`",
        "Process Stability Check": "`quality.individuals_chart`",
        "Specification Capability Check": "`quality.capability`",
        "Measurement System Reliability Check": "`quality.gage_rr`",
        "Experiment Condition Table": "`doe.factorial_design`",
    }
    required_labels = {
        "User question",
        "Purpose helper card",
        "Needed roles",
        "Easy wrong roles",
        "Preflight checks",
        "Read first in results",
        "Cannot say",
        "QA pass criteria",
        "Fail examples",
        "UX copy that must remain visible",
        "UI element to inspect",
        "Recovery from wrong role",
    }
    required_ui_surfaces = {
        "`MethodPurposeHelper`",
        "`StatisticalRoleGuide`",
        "`PreflightExplanationPanel`",
    }

    for scenario, method_id in expected_scenarios.items():
        section = _markdown_h2_section(text, scenario)
        assert method_id in section
        for label in required_labels:
            assert f"{label}:" in section
        for ui_surface in required_ui_surfaces:
            assert ui_surface in section


def test_independent_reference_backlog_keeps_actionable_fixture_plan() -> None:
    text = (_repo_root() / "docs/statistical_method_audit_matrix.md").read_text(
        encoding="utf-8",
    )
    backlog = _markdown_h2_section(text, "Independent Reference Backlog")
    expected_fixture_plans = {
        "quality.capability": {
            "quality_capability_normal_reference.json",
            "Cp",
            "Cpk",
            "Pp",
            "Ppk",
            "warning codes",
            "provenance",
        },
        "quality.gage_rr": {
            "quality_gage_rr_crossed_reference.json",
            "ANOVA",
            "variance components",
            "ndc",
            "redacted label",
            "warnings",
        },
        "quality.gage_run_chart": {
            "quality_gage_run_chart_ordering_reference.json",
            "point ordering",
            "redacted labels",
            "truncation",
            "warnings",
            "provenance",
        },
        "doe.factorial_design": {
            "doe_factorial_design_reference.json",
            "doe_factorial_analysis_nist_reference.json",
            "standard order",
            "published responses",
            "saturated coefficients",
            "effect=2*coefficient",
            "provenance",
        },
        "regression.linear_model": {
            "regression_linear_model_reference.json",
            "coefficients",
            "prediction interval",
            "manifest checksum",
            "provenance",
            "treatment coding",
        },
    }

    for method_id, required_phrases in expected_fixture_plans.items():
        cells = _markdown_table_cells_for_method(backlog, method_id)
        assert len(cells) == 6
        first_fixture, source, tolerance, fields, license_check = cells[1:]
        assert first_fixture
        assert source
        assert tolerance
        assert fields
        assert license_check
        assert "TODO" not in " ".join(cells)
        assert "TBD" not in " ".join(cells)
        assert any(
            review_state in license_check
            for review_state in ("Confirm", "Confirmed", "Verify", "Verified")
        )
        assert "1e-" in tolerance or "Exact equality" in tolerance
        row_text = " | ".join(cells)
        for phrase in required_phrases:
            assert phrase in row_text


def test_registry_progress_docs_match_catalog_and_generic_handler_counts() -> None:
    available_count = sum(method.availability == MethodAvailability.AVAILABLE for method in METHODS)
    stable_count = len(METHODS)
    generic_handler_count = len(METHOD_EXECUTION_HANDLER_SPECS)
    required_count_phrases = {
        f"{stable_count} stable catalog IDs",
        f"{available_count} available IDs",
        f"{generic_handler_count} generic `MethodExecutionHandler` entries",
    }
    progress_text = re.sub(
        r"\s+",
        " ",
        (_repo_root() / "docs/progress_gate_b.md").read_text(encoding="utf-8"),
    )

    for phrase in required_count_phrases:
        assert phrase in progress_text


def test_openapi_typescript_generation_review_stays_planning_only() -> None:
    todo_text = (_repo_root() / "to_do_list.md").read_text(encoding="utf-8")
    package_text = (_repo_root() / "frontend/package.json").read_text(encoding="utf-8")
    lockfile_text = (_repo_root() / "frontend/package-lock.json").read_text(
        encoding="utf-8",
    )
    review_section = _markdown_h2_section(
        todo_text,
        "Progress Update 139 - OpenAPI TypeScript Generation Review Plan",
    )
    candidate_tools = {
        "openapi-typescript",
        "openapi-fetch",
        "orval",
        "@openapitools/openapi-generator-cli",
    }
    required_review_phrases = {
        "Current guard coverage",
        "Not covered",
        "Candidate tools for a later spike",
        "Review before adoption",
        "Windows and current Node LTS compatibility",
        "package-lock.json",
        "CI install time",
        "Generated file commit policy",
        "Schema naming stability",
        "manually curated domain types",
        "No generator dependency is added in this PR",
    }

    for phrase in required_review_phrases:
        assert phrase in review_section
    for tool_name in candidate_tools:
        assert tool_name in review_section
        assert tool_name not in package_text
        assert tool_name not in lockfile_text


@pytest.mark.parametrize(
    "contract",
    FRONTEND_SCHEMA_COMPONENT_CONTRACTS,
    ids=lambda contract: contract.name,
)
def test_frontend_schema_component_contract_is_present_in_openapi(
    openapi_schema: dict[str, Any],
    contract: SchemaComponentContract,
) -> None:
    schemas = openapi_schema["components"]["schemas"]

    assert contract.name in schemas
    schema = schemas[contract.name]

    if contract.enum_values is not None:
        assert frozenset(schema.get("enum", [])) == contract.enum_values
        return

    properties = schema.get("properties")
    assert isinstance(properties, dict)
    assert contract.properties <= frozenset(properties.keys())
    assert contract.required_fields <= frozenset(schema.get("required", []))

    if contract.additional_properties is not None:
        assert schema.get("additionalProperties") is contract.additional_properties

    for field_name, ref_name in contract.property_refs:
        assert _schema_ref_name(properties[field_name]) == ref_name
        assert ref_name in schemas

    for field_name, ref_names in contract.property_any_of_refs:
        assert _schema_any_of_ref_names(properties[field_name]) == ref_names
        assert ref_names <= frozenset(schemas)

    for field_name, ref_name in contract.array_item_refs:
        assert _array_item_ref_name(properties[field_name]) == ref_name
        assert ref_name in schemas

    for field_name, const_value in contract.property_consts:
        assert properties[field_name].get("const") == const_value


@pytest.mark.parametrize(
    "contract",
    FRONTEND_RESULT_TYPE_FILE_CONTRACTS,
    ids=lambda contract: contract.path,
)
def test_frontend_result_type_file_owns_expected_summary_literals(
    contract: FrontendResultTypeFileContract,
) -> None:
    assert _frontend_summary_type_literals(contract.path) == contract.summary_types


def test_frontend_result_summary_literals_match_backend_handler_specs() -> None:
    frontend_summary_types: set[str] = set()
    for contract in FRONTEND_RESULT_TYPE_FILE_CONTRACTS:
        frontend_summary_types.update(_frontend_summary_type_literals(contract.path))

    backend_summary_types = {
        spec.result_summary_type for spec in METHOD_EXECUTION_HANDLER_SPECS
    } | set(NON_ANALYSIS_RUN_RESULT_SUMMARY_TYPES)

    assert frontend_summary_types == backend_summary_types
