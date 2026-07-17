import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Any, Final, Literal, cast
from uuid import UUID

from fastapi import status

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.quality import (
    AttributeControlLimitSetResponse,
    AttributeControlMonitoringPreflightIssue,
    AttributeControlMonitoringPreflightRequest,
    AttributeControlMonitoringPreflightResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import RowSnapshotArtifact
from app.services.analysis_run_results import StoredAnalysisRunResult
from app.services.attribute_control_limit_sets import get_attribute_control_limit_set
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    verify_canonical_rows_artifact,
)
from app.storage.metadata import (
    DatasetColumnRecord,
    get_analysis_artifact_record,
)

ATTRIBUTE_CONTROL_METHOD_ID: Final = "quality.attribute_control_chart"
ATTRIBUTE_CONTROL_PHASE2_METHOD_VERSION: Final[Literal["0.3.0"]] = cast(
    Literal["0.3.0"], METHOD_VERSIONS[ATTRIBUTE_CONTROL_METHOD_ID]
)
_SUPPORTED_PHASE2_RESULTS: Final = {"0.2.0": 2, "0.3.0": 3}
_SUPPORTED_LIMIT_SET_METHOD_VERSIONS: Final = {"0.2.0", "0.3.0"}
_NUMERIC_DATA_TYPES: Final = {"integer", "decimal"}
_ROW_SNAPSHOT_KIND: Final = "analysis_row_snapshot"
_COMPATIBILITY_CODES: Final = {
    "attribute_control_chart_limit_set_method_version_mismatch",
    "attribute_control_chart_limit_set_chart_type_mismatch",
    "attribute_control_chart_limit_set_count_definition_mismatch",
    "attribute_control_chart_phase_2_target_schema_mismatch",
    "attribute_control_chart_phase_2_c_opportunity_confirmation_required",
}


def get_attribute_control_monitoring_preflight(
    settings: Settings,
    *,
    limit_set_id: UUID,
    body: AttributeControlMonitoringPreflightRequest,
) -> AttributeControlMonitoringPreflightResponse:
    asset = get_attribute_control_limit_set(settings, limit_set_id)
    context = get_dataset_rows_context(settings, body.target_dataset_version_id)
    verify_canonical_rows_artifact(context)
    issue: AttributeControlMonitoringPreflightIssue | None = None
    try:
        validate_attribute_control_phase_2_target(
            asset=asset,
            context=context,
            chart_type=body.chart_type,
            count_definition=body.count_definition,
            count_column_id=str(body.count_column_id),
            denominator_column_id=(
                None if body.denominator_column_id is None else str(body.denominator_column_id)
            ),
            constant_opportunity_confirmed=body.constant_opportunity_confirmed,
        )
    except ApiError as exc:
        if exc.code not in _COMPATIBILITY_CODES:
            raise
        issue = AttributeControlMonitoringPreflightIssue(
            code=exc.code,
            severity="error",
            message=exc.message,
        )
    return AttributeControlMonitoringPreflightResponse(
        schema_version=2,
        method_id=ATTRIBUTE_CONTROL_METHOD_ID,
        method_version=ATTRIBUTE_CONTROL_PHASE2_METHOD_VERSION,
        phase="phase_2",
        limit_set_id=asset.limit_set_id,
        limit_set_asset_sha256=asset.asset_sha256,
        target_dataset_version_id=body.target_dataset_version_id,
        target_schema_hash=context.version.schema_hash,
        target_canonical_sha256=context.canonical_rows_artifact.sha256,
        chart_type=asset.chart_type,
        count_definition=asset.count_definition,
        validation_scope="schema_and_dependency_only",
        row_data_validated=False,
        ready=issue is None,
        issues=[] if issue is None else [issue],
    )


def validate_attribute_control_phase_2_target(
    *,
    asset: AttributeControlLimitSetResponse,
    context: DatasetRowsContext,
    chart_type: str,
    count_definition: str,
    count_column_id: str,
    denominator_column_id: str | None,
    constant_opportunity_confirmed: bool,
) -> tuple[DatasetColumnRecord, DatasetColumnRecord | None]:
    if (
        asset.phase2_method_version not in _SUPPORTED_LIMIT_SET_METHOD_VERSIONS
        or METHOD_VERSIONS[ATTRIBUTE_CONTROL_METHOD_ID] != ATTRIBUTE_CONTROL_PHASE2_METHOD_VERSION
    ):
        raise _error(
            "attribute_control_chart_limit_set_method_version_mismatch",
            "선택한 limit set은 현재 Phase II 관리도 버전과 호환되지 않습니다.",
        )
    if chart_type != asset.chart_type:
        raise _error(
            "attribute_control_chart_limit_set_chart_type_mismatch",
            "선택한 limit set과 같은 관리도 유형을 사용해야 합니다.",
        )
    if count_definition != asset.count_definition:
        raise _error(
            "attribute_control_chart_limit_set_count_definition_mismatch",
            "선택한 limit set과 계수 정의가 일치해야 합니다.",
        )
    count_column = _compatible_column(context, count_column_id, asset.count)
    if asset.denominator is None:
        if denominator_column_id is not None:
            raise _target_schema_mismatch()
        denominator_column = None
    else:
        if denominator_column_id is None or denominator_column_id == count_column_id:
            raise _target_schema_mismatch()
        denominator_column = _compatible_column(
            context,
            denominator_column_id,
            asset.denominator,
        )
    if asset.chart_type == "c" and not constant_opportunity_confirmed:
        raise _error(
            "attribute_control_chart_phase_2_c_opportunity_confirmation_required",
            "현재 모니터링 관측의 검사 기회가 기준선과 동일함을 확인해야 합니다.",
        )
    return count_column, denominator_column


def phase_2_dependency_payloads(
    *,
    asset: AttributeControlLimitSetResponse,
    context: DatasetRowsContext,
    row_snapshot: RowSnapshotArtifact,
    count_column_id: str,
    denominator_column_id: str | None,
) -> tuple[dict[str, object], dict[str, object]]:
    limit_set_dependency: dict[str, object] = {
        "limit_set_id": str(asset.limit_set_id),
        "asset_schema_version": asset.asset_schema_version,
        "asset_sha256": asset.asset_sha256,
        "source_analysis_id": str(asset.source_analysis_id),
        "source_method_version": asset.source_method_version,
        "source_result_schema_version": asset.source_result_schema_version,
        "source_dataset_version_id": str(asset.source_dataset_version_id),
        "source_schema_hash": asset.source_schema_hash,
        "source_canonical_sha256": asset.source_canonical_sha256,
        "source_result_sha256": asset.source_result_sha256,
        "baseline_closed_at": asset.closed_at,
        "baseline_point_count": asset.baseline_point_count,
        "frozen_center_line": asset.frozen_center_line,
        "fixed_sample_size": asset.fixed_sample_size,
        "calculation_policy": asset.calculation_policy,
    }
    target_dependency: dict[str, object] = {
        "dataset_version_id": context.version.version_id,
        "schema_hash": context.version.schema_hash,
        "canonical_sha256": context.canonical_rows_artifact.sha256,
        "filter_snapshot_sha256": row_snapshot.payload["filter_snapshot_sha256"],
        "row_snapshot_sha256": row_snapshot.record.sha256,
        "row_count_total": row_snapshot.payload["selection"]["row_count_total"],
        "row_count_included": row_snapshot.payload["selection"]["row_count_included"],
        "count_column_id": count_column_id,
        "denominator_column_id": denominator_column_id,
    }
    return limit_set_dependency, target_dependency


def validate_attribute_control_phase_2_consistency(
    settings: Settings,
    analysis_id: UUID,
    *,
    stored_result: StoredAnalysisRunResult,
) -> None:
    record = stored_result.record
    envelope = stored_result.envelope
    if record.method_id != ATTRIBUTE_CONTROL_METHOD_ID:
        return
    expected_result_schema = _SUPPORTED_PHASE2_RESULTS.get(record.method_version)
    if expected_result_schema is None:
        return
    result = envelope.result
    if not isinstance(result, dict) or result.get("phase") != "phase_2":
        return
    try:
        config = json.loads(record.config_json)
    except json.JSONDecodeError as exc:
        raise _dependency_mismatch() from exc
    options = config.get("options") if isinstance(config, dict) else None
    limit_dependency = result.get("limit_set_dependency")
    target_dependency = result.get("target_dependency")
    if not all(isinstance(value, dict) for value in (options, limit_dependency, target_dependency)):
        raise _dependency_mismatch()
    assert isinstance(options, dict)
    assert isinstance(limit_dependency, dict)
    assert isinstance(target_dependency, dict)
    limit_set_id = options.get("limit_set_id")
    if not isinstance(limit_set_id, str):
        raise _dependency_mismatch()
    try:
        asset = get_attribute_control_limit_set(settings, UUID(limit_set_id))
        dataset_version_id = UUID(str(record.dataset_version_id))
        context = get_dataset_rows_context(settings, dataset_version_id)
        verify_canonical_rows_artifact(context)
    except (ApiError, ValueError) as exc:
        raise _dependency_mismatch() from exc
    if not _envelope_relationships_match(stored_result, analysis_id, context):
        raise _dependency_mismatch()
    denominator_id = options.get("denominator_column_id")
    if denominator_id is not None and not isinstance(denominator_id, str):
        raise _dependency_mismatch()
    try:
        validate_attribute_control_phase_2_target(
            asset=asset,
            context=context,
            chart_type=str(options.get("chart_type")),
            count_definition=str(options.get("count_definition")),
            count_column_id=str(options.get("count_column_id")),
            denominator_column_id=denominator_id,
            constant_opportunity_confirmed=bool(
                options.get("constant_opportunity_confirmed", False)
            ),
        )
    except ApiError as exc:
        raise _dependency_mismatch() from exc
    expected_limit, expected_target = _expected_dependency_payloads(
        asset=asset,
        context=context,
        config=config,
        options=options,
    )
    if limit_dependency != expected_limit or target_dependency != expected_target:
        raise _dependency_mismatch()
    provenance = envelope.provenance
    count_result = result.get("count")
    denominator_result = result.get("denominator")
    if (
        not isinstance(count_result, dict)
        or count_result.get("column_id") != options.get("count_column_id")
        or (denominator_result is None and options.get("denominator_column_id") is not None)
        or (denominator_result is not None and not isinstance(denominator_result, dict))
        or (
            isinstance(denominator_result, dict)
            and denominator_result.get("column_id") != options.get("denominator_column_id")
        )
        or provenance.filter_snapshot_sha256 != target_dependency.get("filter_snapshot_sha256")
        or provenance.row_snapshot_sha256 != target_dependency.get("row_snapshot_sha256")
        or provenance.row_count_included != target_dependency.get("row_count_included")
    ):
        raise _dependency_mismatch()
    if (
        result.get("schema_version") != expected_result_schema
        or result.get("control_limit_method") != "phase_2_frozen_three_sigma"
        or result.get("baseline") != "verified_immutable_limit_set"
        or result.get("chart_type") != asset.chart_type
        or result.get("count_definition") != asset.count_definition
        or result.get("center_line") != asset.frozen_center_line
        or result.get("n_total") != target_dependency.get("row_count_included")
    ):
        raise _dependency_mismatch()
    if expected_result_schema == 3 and not _valid_dispersion_relationship(result):
        raise _dependency_mismatch()
    _validate_row_snapshot_dependency(settings, record.analysis_id, config, context)


def _valid_dispersion_relationship(result: dict[str, Any]) -> bool:
    n_used = result.get("n_used")
    dispersion = result.get("dispersion")
    if isinstance(n_used, bool) or not isinstance(n_used, int) or n_used < 1:
        return False
    if not isinstance(dispersion, dict):
        return False
    degrees_of_freedom = dispersion.get("degrees_of_freedom")
    if degrees_of_freedom != n_used - 1 or dispersion.get("used_to_adjust_limits") is not False:
        return False
    if n_used == 1:
        return bool(
            dispersion.get("available") is False
            and dispersion.get("ratio") is None
            and dispersion.get("reason_code")
            == "attribute_control_chart_dispersion_insufficient_points"
        )
    ratio = dispersion.get("ratio")
    return bool(
        dispersion.get("available") is True
        and dispersion.get("reason_code") is None
        and not isinstance(ratio, bool)
        and isinstance(ratio, int | float)
        and isfinite(float(ratio))
    )


def _expected_dependency_payloads(
    *,
    asset: AttributeControlLimitSetResponse,
    context: DatasetRowsContext,
    config: dict[str, Any],
    options: dict[str, Any],
) -> tuple[dict[str, object], dict[str, object]]:
    row_snapshot = config.get("row_snapshot")
    if not isinstance(row_snapshot, dict):
        raise _dependency_mismatch()
    expected_limit: dict[str, object] = {
        "limit_set_id": str(asset.limit_set_id),
        "asset_schema_version": asset.asset_schema_version,
        "asset_sha256": asset.asset_sha256,
        "source_analysis_id": str(asset.source_analysis_id),
        "source_method_version": asset.source_method_version,
        "source_result_schema_version": asset.source_result_schema_version,
        "source_dataset_version_id": str(asset.source_dataset_version_id),
        "source_schema_hash": asset.source_schema_hash,
        "source_canonical_sha256": asset.source_canonical_sha256,
        "source_result_sha256": asset.source_result_sha256,
        "baseline_closed_at": asset.closed_at,
        "baseline_point_count": asset.baseline_point_count,
        "frozen_center_line": asset.frozen_center_line,
        "fixed_sample_size": asset.fixed_sample_size,
        "calculation_policy": asset.calculation_policy,
    }
    expected_target: dict[str, object] = {
        "dataset_version_id": context.version.version_id,
        "schema_hash": context.version.schema_hash,
        "canonical_sha256": context.canonical_rows_artifact.sha256,
        "filter_snapshot_sha256": config.get("filter_snapshot_sha256"),
        "row_snapshot_sha256": row_snapshot.get("sha256"),
        "row_count_total": row_snapshot.get("row_count_total"),
        "row_count_included": row_snapshot.get("row_count_included"),
        "count_column_id": options.get("count_column_id"),
        "denominator_column_id": options.get("denominator_column_id"),
    }
    return expected_limit, expected_target


def _envelope_relationships_match(
    stored: StoredAnalysisRunResult,
    analysis_id: UUID,
    context: DatasetRowsContext,
) -> bool:
    record = stored.record
    envelope = stored.envelope
    return bool(
        str(envelope.analysis_id) == record.analysis_id == str(analysis_id)
        and envelope.method_id == record.method_id == ATTRIBUTE_CONTROL_METHOD_ID
        and envelope.method_version == record.method_version
        and record.method_version in _SUPPORTED_PHASE2_RESULTS
        and envelope.dataset_version_id is not None
        and str(envelope.dataset_version_id) == record.dataset_version_id
        and record.dataset_version_id == context.version.version_id
        and envelope.provenance.method_id == envelope.method_id
        and envelope.provenance.method_version == envelope.method_version
        and envelope.provenance.dataset_version_id == envelope.dataset_version_id
        and envelope.provenance.source_schema_hash == context.version.schema_hash
        and envelope.provenance.row_count_total == context.version.row_count
    )


def _validate_row_snapshot_dependency(
    settings: Settings,
    analysis_id: str,
    config: dict[str, Any],
    context: DatasetRowsContext,
) -> None:
    snapshot = config.get("row_snapshot")
    if not isinstance(snapshot, dict):
        raise _dependency_mismatch()
    artifact_id = snapshot.get("artifact_id")
    if not isinstance(artifact_id, str):
        raise _dependency_mismatch()
    record = get_analysis_artifact_record(settings.workspace_root, analysis_id, artifact_id)
    if record is None or record.kind != _ROW_SNAPSHOT_KIND:
        raise _dependency_mismatch()
    if (
        snapshot.get("sha256") != record.sha256
        or snapshot.get("kind") != record.kind
        or snapshot.get("media_type") != record.media_type
    ):
        raise _dependency_mismatch()
    path = _safe_relative_path(settings.workspace_root, record.path)
    if not path.exists():
        raise _dependency_mismatch()
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != record.sha256:
        raise _dependency_mismatch()
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise _dependency_mismatch() from exc
    source = payload.get("source_canonical_artifact") if isinstance(payload, dict) else None
    selection = payload.get("selection") if isinstance(payload, dict) else None
    if (
        not isinstance(source, dict)
        or not isinstance(selection, dict)
        or payload.get("analysis_id") != analysis_id
        or payload.get("dataset_version_id") != context.version.version_id
        or payload.get("source_schema_hash") != context.version.schema_hash
        or source.get("sha256") != context.canonical_rows_artifact.sha256
        or payload.get("filter_snapshot_sha256") != config.get("filter_snapshot_sha256")
        or selection.get("row_count_total") != snapshot.get("row_count_total")
        or selection.get("row_count_included") != snapshot.get("row_count_included")
    ):
        raise _dependency_mismatch()


def _compatible_column(
    context: DatasetRowsContext,
    column_id: str,
    source: Any,
) -> DatasetColumnRecord:
    column = next((item for item in context.columns if item.column_id == column_id), None)
    if (
        column is None
        or column.data_type not in _NUMERIC_DATA_TYPES
        or column.role == "id"
        or column.measurement_level == "id"
        or column.measurement_level != source.measurement_level
        or column.role != source.role
        or column.unit != source.unit
    ):
        raise _target_schema_mismatch()
    return column


def _safe_relative_path(workspace_root: Path, stored_path: str) -> Path:
    relative = Path(stored_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise _dependency_mismatch()
    return workspace_root / relative


def _target_schema_mismatch() -> ApiError:
    return _error(
        "attribute_control_chart_phase_2_target_schema_mismatch",
        "대상 데이터셋의 계수·분모 열 의미가 선택한 limit set과 호환되지 않습니다.",
    )


def _dependency_mismatch() -> ApiError:
    return _error(
        "attribute_control_chart_phase_2_dependency_mismatch",
        "저장된 Phase II 관리도 의존성 관계를 검증할 수 없습니다.",
    )


def _error(code: str, message: str) -> ApiError:
    return ApiError(code=code, message=message, status_code=status.HTTP_409_CONFLICT)
