import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from app.main import create_app
from app.services.analysis_method_handlers import METHOD_EXECUTION_HANDLER_SPECS


@dataclass(frozen=True)
class OperationContract:
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
    array_item_refs: tuple[tuple[str, str], ...] = ()
    property_consts: tuple[tuple[str, object], ...] = ()
    additional_properties: bool | None = False


@dataclass(frozen=True)
class FrontendResultTypeFileContract:
    path: str
    summary_types: frozenset[str]


# This is the backend-side contract for frontend/src/api/routes.ts.
# It intentionally tracks only the routes used by the typed frontend client.
FRONTEND_ROUTE_CONTRACTS = [
    OperationContract(
        method="get",
        path="/api/v1/health",
        success_status="200",
        response_schema="HealthResponse",
    ),
    OperationContract(
        method="post",
        path="/api/v1/datasets",
        success_status="201",
        response_schema="DatasetUploadResponse",
        request_media_types=frozenset({"multipart/form-data"}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/datasets/paste",
        success_status="201",
        response_schema="DatasetUploadResponse",
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/datasets/{dataset_id}/confirm-parsing",
        success_status="201",
        response_schema="DatasetVersionResponse",
        parameters=frozenset({("dataset_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        method="patch",
        path="/api/v1/dataset-versions/{version_id}/schema",
        success_status="200",
        response_schema="DatasetSchemaResponse",
        parameters=frozenset({("version_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/dataset-versions/{version_id}/rows",
        success_status="200",
        response_schema="DatasetRowsPreviewResponse",
        parameters=frozenset({("version_id", "path"), ("offset", "query"), ("limit", "query")}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/dataset-versions/{version_id}/profile",
        success_status="200",
        response_schema="DatasetProfileResponse",
        parameters=frozenset({("version_id", "path")}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/analysis-methods",
        success_status="200",
        response_schema="AnalysisMethodListResponse",
    ),
    OperationContract(
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
        method="post",
        path="/api/v1/analysis-runs",
        success_status="201",
        response_schema="AnalysisResultEnvelope",
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/analysis-runs/comparison",
        success_status="200",
        response_schema="AnalysisRunComparisonResponse",
        parameters=frozenset({("left_analysis_id", "query"), ("right_analysis_id", "query")}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/analysis-runs/{analysis_id}/result",
        success_status="200",
        response_schema="AnalysisResultEnvelope",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/analysis-runs/{analysis_id}/exports/json",
        success_status="201",
        response_schema="AnalysisResultJsonExportResponse",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/analysis-runs/{analysis_id}/exports/csv",
        success_status="201",
        response_schema="AnalysisResultCsvExportResponse",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/analysis-runs/{analysis_id}/exports/html",
        success_status="201",
        response_schema="AnalysisResultHtmlReportResponse",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/analysis-runs/{analysis_id}/exports",
        success_status="200",
        response_schema="AnalysisResultExportListResponse",
        parameters=frozenset({("analysis_id", "path")}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/analysis-runs/{analysis_id}/exports/{export_id}/download",
        success_status="200",
        response_schema=None,
        parameters=frozenset({("analysis_id", "path"), ("export_id", "path")}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/doe-designs/factorial",
        success_status="201",
        response_schema="FactorialDesignResponse",
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/doe-designs/{design_id}",
        success_status="200",
        response_schema="FactorialDesignResponse",
        parameters=frozenset({("design_id", "path")}),
    ),
    OperationContract(
        method="put",
        path="/api/v1/doe-designs/{design_id}/responses",
        success_status="200",
        response_schema="DoeDesignResponsesResponse",
        parameters=frozenset({("design_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        method="get",
        path="/api/v1/doe-designs/{design_id}/responses",
        success_status="200",
        response_schema="DoeDesignResponsesResponse",
        parameters=frozenset({("design_id", "path")}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/regression-models/{model_id}/prediction-preflight",
        success_status="200",
        response_schema="RegressionPredictionPreflightResponse",
        parameters=frozenset({("model_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/regression-models/{model_id}/predictions",
        success_status="200",
        response_schema="RegressionPredictionResponse",
        parameters=frozenset({("model_id", "path")}),
        request_media_types=frozenset({"application/json"}),
    ),
    OperationContract(
        method="post",
        path="/api/v1/quality/gage-rr/preflight",
        success_status="200",
        response_schema="GageRrPreflightResponse",
        request_media_types=frozenset({"application/json"}),
    ),
]


# This is a field-level guard for the frontend/src/api/types/* surface.
# It intentionally checks only high-value fields the UI relies on; full
# TypeScript generation remains a separate, larger task.
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
        property_refs=(("provenance", "AnalysisProvenance"),),
        array_item_refs=(("warnings", "AnalysisWarning"),),
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
]

NON_ANALYSIS_RUN_RESULT_SUMMARY_TYPES = frozenset({"gage_rr_preflight"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _frontend_summary_type_literals(relative_path: str) -> frozenset[str]:
    text = (_repo_root() / relative_path).read_text(encoding="utf-8")
    return frozenset(re.findall(r'summary_type:\s*"([^"]+)";', text))


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
