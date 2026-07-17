import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from math import isclose, isfinite, sqrt
from pathlib import Path
from typing import Any, Final, Literal, cast
from uuid import UUID, uuid4

from fastapi import status
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, ValidationError

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.quality import (
    AttributeControlLimitSetAsset,
    AttributeControlLimitSetColumnDependency,
    AttributeControlLimitSetCreatorProvenance,
    AttributeControlLimitSetEligibility,
    AttributeControlLimitSetListResponse,
    AttributeControlLimitSetResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    APP_VERSION,
    canonical_json_bytes,
    runtime_build_provenance,
    utc_now,
)
from app.services.analysis_run_results import load_analysis_run_result_base
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    verify_canonical_rows_artifact,
)
from app.storage.atomic import atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    AttributeControlLimitSetRecord,
    DatasetColumnRecord,
    count_attribute_control_limit_set_records,
    get_analysis_artifact_record,
    get_analysis_run_record,
    get_attribute_control_limit_set_record,
    get_attribute_control_limit_set_record_by_source_analysis,
    insert_attribute_control_limit_set_record,
    list_attribute_control_limit_set_records,
)

ATTRIBUTE_CONTROL_METHOD_ID: Final = "quality.attribute_control_chart"
ATTRIBUTE_CONTROL_LIMIT_SET_ASSET_SCHEMA_VERSION: Final[Literal[1]] = 1
ATTRIBUTE_CONTROL_PHASE2_METHOD_VERSION: Final[Literal["0.3.0"]] = cast(
    Literal["0.3.0"], METHOD_VERSIONS[ATTRIBUTE_CONTROL_METHOD_ID]
)
ATTRIBUTE_CONTROL_LIMIT_SET_CALCULATION_POLICY: Final[Literal["phase_2_frozen_three_sigma_v1"]] = (
    "phase_2_frozen_three_sigma_v1"
)
ATTRIBUTE_CONTROL_LIMIT_SET_ELIGIBILITY_POLICY: Final[
    Literal["phase_2_baseline_eligibility_v1"]
] = "phase_2_baseline_eligibility_v1"
MINIMUM_PHASE2_BASELINE_POINT_COUNT: Final = 20
_ROW_SNAPSHOT_KIND: Final = "analysis_row_snapshot"
_SUPPORTED_PHASE1_SOURCE_RESULTS: Final = {
    ("0.1.0", 1),
    ("0.2.0", 2),
    ("0.3.0", 3),
}


class _ResultColumn(BaseModel):
    model_config = ConfigDict(extra="allow")

    column_id: UUID
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


class _ResultPoint(BaseModel):
    model_config = ConfigDict(extra="allow")

    position: int = Field(ge=1)
    canonical_position: int = Field(ge=1)
    count: int = Field(ge=0)
    denominator: FiniteFloat | None
    value: FiniteFloat
    lcl: FiniteFloat
    ucl: FiniteFloat
    signal_codes: list[str]


class _ResultChart(BaseModel):
    model_config = ConfigDict(extra="allow")

    point_count: int = Field(ge=2)
    points_truncated: bool
    points: list[_ResultPoint]


class _ResultDispersion(BaseModel):
    model_config = ConfigDict(extra="allow")

    ratio: FiniteFloat
    used_to_adjust_limits: Literal[False]


class _PhaseOneResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: Literal[1, 2, 3]
    phase: Literal["phase_1"] | None = None
    summary_type: Literal["attribute_control_chart"]
    chart_type: Literal["p", "np", "c", "u"]
    count_definition: Literal["defectives", "defects"]
    control_limit_method: Literal["phase_1_estimated_three_sigma"]
    baseline: Literal["all_filtered_valid_points"]
    missing_policy: Literal["complete_case"]
    constant_opportunity_confirmed: bool
    warnings: list[str]
    count: _ResultColumn
    denominator: _ResultColumn | None
    denominator_role: Literal["sample_size", "inspection_opportunity"] | None
    n_used: int = Field(ge=2)
    total_count: int = Field(ge=0)
    total_denominator: FiniteFloat | None
    center_line: FiniteFloat
    dispersion: _ResultDispersion
    chart: _ResultChart
    signals: list[dict[str, Any]]


@dataclass(frozen=True)
class _ValidatedBaseline:
    record: AnalysisRunRecord
    context: DatasetRowsContext
    result: _PhaseOneResult
    config_sha256: str
    filter_snapshot_sha256: str
    row_snapshot: AnalysisArtifactRecord
    fixed_sample_size: int | None
    count_column: DatasetColumnRecord
    denominator_column: DatasetColumnRecord | None


def create_attribute_control_limit_set(
    settings: Settings,
    source_analysis_id: UUID,
) -> AttributeControlLimitSetResponse:
    existing = get_attribute_control_limit_set_record_by_source_analysis(
        settings.workspace_root, str(source_analysis_id)
    )
    if existing is not None:
        return _load_limit_set(settings, existing)

    baseline = _validate_source_baseline(settings, source_analysis_id)
    limit_set_id = uuid4()
    created_at = utc_now()
    runtime = runtime_build_provenance(settings)
    asset = AttributeControlLimitSetAsset(
        asset_schema_version=ATTRIBUTE_CONTROL_LIMIT_SET_ASSET_SCHEMA_VERSION,
        limit_set_id=limit_set_id,
        status="closed",
        method_id=ATTRIBUTE_CONTROL_METHOD_ID,
        source_method_version=cast(
            Literal["0.1.0", "0.2.0", "0.3.0"], baseline.record.method_version
        ),
        phase2_method_version=ATTRIBUTE_CONTROL_PHASE2_METHOD_VERSION,
        source_result_schema_version=baseline.result.schema_version,
        source_analysis_id=source_analysis_id,
        source_dataset_version_id=UUID(baseline.context.version.version_id),
        source_schema_hash=baseline.context.version.schema_hash,
        source_canonical_sha256=baseline.context.canonical_rows_artifact.sha256,
        source_config_sha256=baseline.config_sha256,
        source_result_sha256=cast(str, baseline.record.result_sha256),
        filter_snapshot_sha256=baseline.filter_snapshot_sha256,
        row_snapshot_sha256=baseline.row_snapshot.sha256,
        chart_type=baseline.result.chart_type,
        count_definition=baseline.result.count_definition,
        count=_column_dependency(baseline.count_column),
        denominator=(
            None
            if baseline.denominator_column is None
            else _column_dependency(baseline.denominator_column)
        ),
        denominator_role=baseline.result.denominator_role,
        baseline_point_count=baseline.result.n_used,
        total_count=baseline.result.total_count,
        total_denominator=baseline.result.total_denominator,
        frozen_center_line=baseline.result.center_line,
        fixed_sample_size=baseline.fixed_sample_size,
        constant_opportunity_confirmed=baseline.result.constant_opportunity_confirmed,
        sigma_multiplier=3.0,
        calculation_policy=ATTRIBUTE_CONTROL_LIMIT_SET_CALCULATION_POLICY,
        natural_bound_policy=_natural_bound_policy(baseline.result.chart_type),
        eligibility=AttributeControlLimitSetEligibility(
            eligible=True,
            policy=ATTRIBUTE_CONTROL_LIMIT_SET_ELIGIBILITY_POLICY,
            minimum_point_count=MINIMUM_PHASE2_BASELINE_POINT_COUNT,
            checks_passed=[
                "minimum_point_count",
                "no_phase_1_limit_signals",
                "usable_normal_approximation",
                "pearson_dispersion_not_above_two",
                "complete_untruncated_point_payload",
            ],
        ),
        creator_provenance=AttributeControlLimitSetCreatorProvenance(
            app_version=APP_VERSION,
            python_version=str(runtime["python_version"]),
            platform=str(runtime["platform"]),
            build_commit=cast(str | None, runtime["build_commit"]),
            package_versions=cast(dict[str, str], runtime["package_versions"]),
        ),
        created_at=created_at,
        closed_at=created_at,
    )
    asset_bytes = canonical_json_bytes(asset.model_dump(mode="json"))
    asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()
    relative_path = _asset_relative_path(str(limit_set_id))
    asset_path = settings.workspace_root / relative_path
    record = _record_from_asset(asset, relative_path=relative_path, asset_sha256=asset_sha256)
    try:
        atomic_write_bytes(asset_path, asset_bytes)
        insert_attribute_control_limit_set_record(settings.workspace_root, record)
    except sqlite3.IntegrityError:
        _remove_file_if_exists(asset_path)
        concurrent = get_attribute_control_limit_set_record_by_source_analysis(
            settings.workspace_root, str(source_analysis_id)
        )
        if concurrent is not None:
            return _load_limit_set(settings, concurrent)
        raise
    except Exception:
        _remove_file_if_exists(asset_path)
        raise
    return AttributeControlLimitSetResponse(
        **asset.model_dump(mode="python"), asset_sha256=asset_sha256
    )


def get_attribute_control_limit_set(
    settings: Settings,
    limit_set_id: UUID,
) -> AttributeControlLimitSetResponse:
    record = get_attribute_control_limit_set_record(settings.workspace_root, str(limit_set_id))
    if record is None:
        raise _error(
            "attribute_control_chart_limit_set_missing",
            "요청한 계수형 관리도 limit set을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return _load_limit_set(settings, record)


def list_attribute_control_limit_sets(
    settings: Settings,
    *,
    source_dataset_version_id: UUID | None,
    chart_type: Literal["p", "np", "c", "u"] | None,
    limit: int,
    offset: int,
) -> AttributeControlLimitSetListResponse:
    dataset_id = None if source_dataset_version_id is None else str(source_dataset_version_id)
    records = list_attribute_control_limit_set_records(
        settings.workspace_root,
        source_dataset_version_id=dataset_id,
        chart_type=chart_type,
        limit=limit,
        offset=offset,
    )
    return AttributeControlLimitSetListResponse(
        total=count_attribute_control_limit_set_records(
            settings.workspace_root,
            source_dataset_version_id=dataset_id,
            chart_type=chart_type,
        ),
        offset=offset,
        limit=limit,
        items=[_load_limit_set(settings, record) for record in records],
    )


def _validate_source_baseline(settings: Settings, source_analysis_id: UUID) -> _ValidatedBaseline:
    record = get_analysis_run_record(settings.workspace_root, str(source_analysis_id))
    if record is None:
        raise _error(
            "attribute_control_chart_limit_set_source_analysis_missing",
            "source Phase I 분석을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    if (
        record.method_id != ATTRIBUTE_CONTROL_METHOD_ID
        or record.status != "succeeded"
        or record.completed_at is None
        or record.dataset_version_id is None
        or record.result_sha256 is None
    ):
        raise _source_invalid()
    if record.stale:
        raise _error(
            "attribute_control_chart_limit_set_source_analysis_stale",
            "stale Phase I 분석은 limit set으로 승격할 수 없습니다.",
        )
    try:
        stored = load_analysis_run_result_base(settings, source_analysis_id)
    except ApiError as exc:
        raise _error(
            "attribute_control_chart_limit_set_source_artifact_mismatch",
            "source Phase I 결과 자산을 검증할 수 없습니다.",
        ) from exc
    envelope = stored.envelope
    if (
        str(envelope.analysis_id) != record.analysis_id
        or envelope.method_id != record.method_id
        or envelope.method_version != record.method_version
        or envelope.status != "succeeded"
        or envelope.dataset_version_id is None
        or str(envelope.dataset_version_id) != record.dataset_version_id
        or envelope.provenance.method_id != record.method_id
        or envelope.provenance.method_version != record.method_version
        or envelope.provenance.dataset_version_id != envelope.dataset_version_id
        or envelope.result is None
    ):
        raise _source_invalid()
    try:
        result = _PhaseOneResult.model_validate(envelope.result)
        dataset_version_id = UUID(record.dataset_version_id)
    except (ValidationError, ValueError) as exc:
        raise _source_invalid() from exc
    if (record.method_version, result.schema_version) not in _SUPPORTED_PHASE1_SOURCE_RESULTS:
        raise _source_invalid()
    if result.schema_version == 1 and result.phase is not None:
        raise _source_invalid()
    if result.schema_version in {2, 3} and result.phase != "phase_1":
        raise _source_invalid()
    try:
        context = get_dataset_rows_context(settings, dataset_version_id)
        verify_canonical_rows_artifact(context)
    except ApiError as exc:
        raise _error(
            "attribute_control_chart_limit_set_source_artifact_mismatch",
            "source dataset canonical 자산을 검증할 수 없습니다.",
        ) from exc
    provenance = envelope.provenance
    if (
        context.version.schema_hash != provenance.source_schema_hash
        or context.version.version_id != record.dataset_version_id
        or provenance.row_count_total != context.version.row_count
        or provenance.row_count_included != result.n_used
        or provenance.filter_snapshot_sha256 is None
        or provenance.row_snapshot_sha256 is None
    ):
        raise _error(
            "attribute_control_chart_limit_set_source_schema_mismatch",
            "source Phase I 분석의 schema 또는 row dependency가 현재 metadata와 다릅니다.",
        )
    config, config_sha256 = _load_config(record)
    row_snapshot = _validate_row_snapshot(
        settings,
        record=record,
        context=context,
        config=config,
        expected_filter_sha256=provenance.filter_snapshot_sha256,
        expected_row_sha256=provenance.row_snapshot_sha256,
        expected_row_count=result.n_used,
    )
    count_column = _column_by_id(context, str(result.count.column_id))
    denominator_column = (
        None
        if result.denominator is None
        else _column_by_id(context, str(result.denominator.column_id))
    )
    _validate_result_config_and_columns(
        result=result,
        config=config,
        count_column=count_column,
        denominator_column=denominator_column,
    )
    fixed_sample_size = _validate_phase2_eligibility(result)
    baseline = _ValidatedBaseline(
        record=record,
        context=context,
        result=result,
        config_sha256=config_sha256,
        filter_snapshot_sha256=provenance.filter_snapshot_sha256,
        row_snapshot=row_snapshot,
        fixed_sample_size=fixed_sample_size,
        count_column=count_column,
        denominator_column=denominator_column,
    )
    return baseline


def _load_config(record: AnalysisRunRecord) -> tuple[dict[str, Any], str]:
    try:
        config = json.loads(record.config_json)
    except json.JSONDecodeError as exc:
        raise _source_invalid() from exc
    if not isinstance(config, dict) or config.get("schema_version") != 2:
        raise _source_invalid()
    return config, hashlib.sha256(record.config_json.encode("utf-8")).hexdigest()


def _validate_row_snapshot(
    settings: Settings,
    *,
    record: AnalysisRunRecord,
    context: DatasetRowsContext,
    config: dict[str, Any],
    expected_filter_sha256: str,
    expected_row_sha256: str,
    expected_row_count: int,
) -> AnalysisArtifactRecord:
    snapshot = config.get("row_snapshot")
    if not isinstance(snapshot, dict):
        raise _source_invalid()
    artifact_id = snapshot.get("artifact_id")
    if not isinstance(artifact_id, str):
        raise _source_invalid()
    artifact = get_analysis_artifact_record(
        settings.workspace_root, record.analysis_id, artifact_id
    )
    if artifact is None:
        raise _source_artifact_mismatch()
    if (
        artifact.kind != _ROW_SNAPSHOT_KIND
        or artifact.media_type != "application/json"
        or artifact.sha256 != expected_row_sha256
        or snapshot.get("kind") != artifact.kind
        or snapshot.get("sha256") != artifact.sha256
        or snapshot.get("media_type") != artifact.media_type
        or snapshot.get("row_count_total") != context.version.row_count
        or snapshot.get("row_count_included") != expected_row_count
        or config.get("filter_snapshot_sha256") != expected_filter_sha256
    ):
        raise _source_artifact_mismatch()
    path = _safe_asset_path(settings.workspace_root, artifact.path, _source_artifact_mismatch)
    if not path.exists():
        raise _source_artifact_mismatch()
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != artifact.sha256:
        raise _source_artifact_mismatch()
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise _source_artifact_mismatch() from exc
    selection = payload.get("selection") if isinstance(payload, dict) else None
    source = payload.get("source_canonical_artifact") if isinstance(payload, dict) else None
    if (
        not isinstance(selection, dict)
        or not isinstance(source, dict)
        or payload.get("artifact_schema_version") != 1
        or payload.get("artifact_kind") != _ROW_SNAPSHOT_KIND
        or payload.get("analysis_id") != record.analysis_id
        or payload.get("dataset_version_id") != context.version.version_id
        or payload.get("source_schema_hash") != context.version.schema_hash
        or source.get("sha256") != context.canonical_rows_artifact.sha256
        or payload.get("filter_snapshot_sha256") != expected_filter_sha256
        or selection.get("row_count_total") != context.version.row_count
        or selection.get("row_count_included") != expected_row_count
    ):
        raise _source_artifact_mismatch()
    return artifact


def _validate_result_config_and_columns(
    *,
    result: _PhaseOneResult,
    config: dict[str, Any],
    count_column: DatasetColumnRecord,
    denominator_column: DatasetColumnRecord | None,
) -> None:
    options = config.get("options")
    if not isinstance(options, dict):
        raise _source_invalid()
    if options.get("phase", "phase_1") != "phase_1" or options.get("limit_set_id") is not None:
        raise _source_invalid()
    expected_denominator_id = None if denominator_column is None else denominator_column.column_id
    if (
        options.get("chart_type") != result.chart_type
        or options.get("count_definition") != result.count_definition
        or options.get("count_column_id") != count_column.column_id
        or options.get("denominator_column_id") != expected_denominator_id
        or options.get("missing_policy", "complete_case") != result.missing_policy
        or bool(options.get("constant_opportunity_confirmed", False))
        != result.constant_opportunity_confirmed
        or not _result_column_matches(result.count, count_column)
        or (
            result.denominator is not None
            and denominator_column is not None
            and not _result_column_matches(result.denominator, denominator_column)
        )
    ):
        raise _source_invalid()
    if result.chart_type == "c":
        if denominator_column is not None or result.denominator_role is not None:
            raise _source_invalid()
    elif denominator_column is None or result.denominator_role is None:
        raise _source_invalid()


def _validate_phase2_eligibility(result: _PhaseOneResult) -> int | None:
    points = result.chart.points
    if (
        result.n_used < MINIMUM_PHASE2_BASELINE_POINT_COUNT
        or result.chart.points_truncated
        or result.chart.point_count != result.n_used
        or len(points) != result.n_used
    ):
        raise _source_ineligible()
    if result.signals:
        raise _source_ineligible()
    if [point.position for point in points] != list(range(1, result.n_used + 1)):
        raise _source_invalid()
    canonical_positions = [point.canonical_position for point in points]
    if canonical_positions != sorted(set(canonical_positions)):
        raise _source_invalid()
    if sum(point.count for point in points) != result.total_count:
        raise _source_invalid()
    denominators = [point.denominator for point in points]
    if result.chart_type == "c":
        if any(value is not None for value in denominators) or result.total_denominator is not None:
            raise _source_invalid()
        expected_center = result.total_count / result.n_used
        _validate_recomputed_point_payload(result, center_line=expected_center)
        _validate_recomputed_dispersion(result, center_line=expected_center)
        if expected_center < 5.0:
            raise _source_ineligible()
        return None
    numeric_denominators = [value for value in denominators if value is not None]
    if len(numeric_denominators) != len(points) or result.total_denominator is None:
        raise _source_invalid()
    if not isclose(
        sum(numeric_denominators),
        float(result.total_denominator),
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise _source_invalid()
    expected_rate = result.total_count / float(result.total_denominator)
    if result.chart_type in {"p", "np"}:
        fixed_sample_size: int | None = None
        if result.chart_type == "np":
            if any(not float(value).is_integer() for value in numeric_denominators):
                raise _source_invalid()
            sample_sizes = {int(value) for value in numeric_denominators}
            if len(sample_sizes) != 1:
                raise _source_invalid()
            fixed_sample_size = next(iter(sample_sizes))
            expected_center = fixed_sample_size * expected_rate
            pbar = expected_rate
        else:
            expected_center = expected_rate
            pbar = expected_rate
        _validate_recomputed_point_payload(result, center_line=expected_center)
        _validate_recomputed_dispersion(result, center_line=expected_center)
        if not 0.0 < pbar < 1.0:
            raise _source_ineligible()
        if any(value * pbar < 5.0 or value * (1.0 - pbar) < 5.0 for value in numeric_denominators):
            raise _source_ineligible()
        return fixed_sample_size
    _validate_recomputed_point_payload(result, center_line=expected_rate)
    _validate_recomputed_dispersion(result, center_line=expected_rate)
    if expected_rate <= 0.0 or any(value * expected_rate < 5.0 for value in numeric_denominators):
        raise _source_ineligible()
    return None


def _validate_recomputed_point_payload(
    result: _PhaseOneResult,
    *,
    center_line: float,
) -> None:
    if not isclose(result.center_line, center_line, rel_tol=1e-12, abs_tol=1e-12):
        raise _source_invalid()
    for point in result.chart.points:
        value, lcl, ucl = _phase_one_point_values(
            chart_type=result.chart_type,
            center_line=center_line,
            count=point.count,
            denominator=point.denominator,
        )
        if not all(
            isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
            for actual, expected in (
                (point.value, value),
                (point.lcl, lcl),
                (point.ucl, ucl),
            )
        ):
            raise _source_invalid()
        if value < lcl or value > ucl or point.signal_codes:
            raise _source_ineligible()


def _phase_one_point_values(
    *,
    chart_type: Literal["p", "np", "c", "u"],
    center_line: float,
    count: int,
    denominator: float | None,
) -> tuple[float, float, float]:
    if chart_type == "p":
        if denominator is None:
            raise _source_invalid()
        spread = 3.0 * sqrt(center_line * (1.0 - center_line) / denominator)
        return count / denominator, max(0.0, center_line - spread), min(1.0, center_line + spread)
    if chart_type == "np":
        if denominator is None:
            raise _source_invalid()
        pbar = center_line / denominator
        spread = 3.0 * sqrt(denominator * pbar * (1.0 - pbar))
        return float(count), max(0.0, center_line - spread), min(denominator, center_line + spread)
    if chart_type == "c":
        spread = 3.0 * sqrt(center_line)
        return float(count), max(0.0, center_line - spread), center_line + spread
    if denominator is None:
        raise _source_invalid()
    spread = 3.0 * sqrt(center_line / denominator)
    return count / denominator, max(0.0, center_line - spread), center_line + spread


def _validate_recomputed_dispersion(
    result: _PhaseOneResult,
    *,
    center_line: float,
) -> None:
    contributions: list[float] = []
    for point in result.chart.points:
        if result.chart_type == "c":
            expected = center_line
            variance = center_line
        elif result.chart_type == "u":
            if point.denominator is None:
                raise _source_invalid()
            expected = point.denominator * center_line
            variance = expected
        else:
            if point.denominator is None:
                raise _source_invalid()
            pbar = center_line / point.denominator if result.chart_type == "np" else center_line
            expected = point.denominator * pbar
            variance = point.denominator * pbar * (1.0 - pbar)
        if variance <= 0.0:
            raise _source_ineligible()
        contributions.append((point.count - expected) ** 2 / variance)
    ratio = sum(contributions) / (result.n_used - 1)
    if not isclose(result.dispersion.ratio, ratio, rel_tol=1e-12, abs_tol=1e-12):
        raise _source_invalid()
    if ratio > 2.0 or ratio < 0.0:
        raise _source_ineligible()


def _load_limit_set(
    settings: Settings,
    record: AttributeControlLimitSetRecord,
) -> AttributeControlLimitSetResponse:
    response = validate_attribute_control_limit_set_for_retention(settings, record)
    asset = AttributeControlLimitSetAsset.model_validate(
        response.model_dump(mode="python", exclude={"asset_sha256"})
    )
    baseline = _validate_source_baseline(settings, asset.source_analysis_id)
    if not _asset_matches_source(asset, baseline):
        raise _error(
            "attribute_control_chart_limit_set_source_dependency_mismatch",
            "계수형 관리도 limit set의 source dependency가 현재 검증 결과와 다릅니다.",
        )
    return response


def validate_attribute_control_limit_set_for_retention(
    settings: Settings,
    record: AttributeControlLimitSetRecord,
) -> AttributeControlLimitSetResponse:
    """Validate the immutable asset without requiring a currently fresh source."""
    path = _safe_asset_path(
        settings.workspace_root,
        record.asset_path,
        lambda: _error(
            "attribute_control_chart_limit_set_invalid",
            "계수형 관리도 limit set metadata가 올바르지 않습니다.",
        ),
    )
    if not path.exists():
        raise _error(
            "attribute_control_chart_limit_set_invalid",
            "계수형 관리도 limit set 자산을 찾을 수 없습니다.",
        )
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != record.asset_sha256:
        raise _error(
            "attribute_control_chart_limit_set_checksum_mismatch",
            "계수형 관리도 limit set checksum이 metadata와 일치하지 않습니다.",
        )
    try:
        asset = AttributeControlLimitSetAsset.model_validate_json(data)
    except ValidationError as exc:
        raise _error(
            "attribute_control_chart_limit_set_invalid",
            "계수형 관리도 limit set 형식이 올바르지 않습니다.",
        ) from exc
    if not _asset_matches_record(asset, record):
        raise _error(
            "attribute_control_chart_limit_set_metadata_invalid",
            "계수형 관리도 limit set 자산과 metadata 관계가 일치하지 않습니다.",
        )
    current_source = get_analysis_run_record(settings.workspace_root, str(asset.source_analysis_id))
    if (
        current_source is None
        or current_source.result_sha256 != asset.source_result_sha256
        or hashlib.sha256(current_source.config_json.encode("utf-8")).hexdigest()
        != asset.source_config_sha256
    ):
        raise _error(
            "attribute_control_chart_limit_set_source_dependency_mismatch",
            "계수형 관리도 limit set의 source dependency가 현재 metadata와 다릅니다.",
        )
    return AttributeControlLimitSetResponse(**asset.model_dump(mode="python"), asset_sha256=digest)


def _asset_matches_record(
    asset: AttributeControlLimitSetAsset,
    record: AttributeControlLimitSetRecord,
) -> bool:
    denominator_id = None if asset.denominator is None else str(asset.denominator.column_id)
    return (
        str(asset.limit_set_id) == record.limit_set_id
        and str(asset.source_analysis_id) == record.source_analysis_id
        and str(asset.source_dataset_version_id) == record.source_dataset_version_id
        and asset.asset_schema_version == record.asset_schema_version
        and asset.method_id == record.method_id
        and asset.source_method_version == record.source_method_version
        and asset.phase2_method_version == record.phase2_method_version
        and asset.chart_type == record.chart_type
        and asset.count_definition == record.count_definition
        and str(asset.count.column_id) == record.count_column_id
        and denominator_id == record.denominator_column_id
        and asset.source_schema_hash == record.source_schema_hash
        and asset.source_canonical_sha256 == record.source_canonical_sha256
        and asset.source_config_sha256 == record.source_config_sha256
        and asset.source_result_sha256 == record.source_result_sha256
        and asset.filter_snapshot_sha256 == record.filter_snapshot_sha256
        and asset.row_snapshot_sha256 == record.row_snapshot_sha256
        and asset.baseline_point_count == record.baseline_point_count
        and asset.total_count == record.total_count
        and _optional_float_equal(asset.total_denominator, record.total_denominator)
        and isclose(asset.frozen_center_line, record.center_line, rel_tol=0.0, abs_tol=0.0)
        and asset.fixed_sample_size == record.fixed_sample_size
        and asset.constant_opportunity_confirmed == record.constant_opportunity_confirmed
        and isclose(asset.sigma_multiplier, record.sigma_multiplier, rel_tol=0.0, abs_tol=0.0)
        and asset.calculation_policy == record.calculation_policy
        and asset.natural_bound_policy == record.natural_bound_policy
        and asset.created_at == record.created_at
        and asset.closed_at == record.closed_at
        and asset.creator_provenance.app_version == record.app_version
    )


def _asset_matches_source(
    asset: AttributeControlLimitSetAsset,
    baseline: _ValidatedBaseline,
) -> bool:
    denominator_id = (
        None if baseline.denominator_column is None else baseline.denominator_column.column_id
    )
    return (
        asset.source_method_version == baseline.record.method_version
        and asset.source_result_schema_version == baseline.result.schema_version
        and str(asset.source_dataset_version_id) == baseline.context.version.version_id
        and asset.source_schema_hash == baseline.context.version.schema_hash
        and asset.source_canonical_sha256 == baseline.context.canonical_rows_artifact.sha256
        and asset.source_config_sha256 == baseline.config_sha256
        and asset.source_result_sha256 == baseline.record.result_sha256
        and asset.filter_snapshot_sha256 == baseline.filter_snapshot_sha256
        and asset.row_snapshot_sha256 == baseline.row_snapshot.sha256
        and asset.chart_type == baseline.result.chart_type
        and asset.count_definition == baseline.result.count_definition
        and str(asset.count.column_id) == baseline.count_column.column_id
        and (None if asset.denominator is None else str(asset.denominator.column_id))
        == denominator_id
        and asset.baseline_point_count == baseline.result.n_used
        and asset.total_count == baseline.result.total_count
        and _optional_float_equal(asset.total_denominator, baseline.result.total_denominator)
        and isclose(
            asset.frozen_center_line,
            baseline.result.center_line,
            rel_tol=0.0,
            abs_tol=0.0,
        )
        and asset.fixed_sample_size == baseline.fixed_sample_size
    )


def _record_from_asset(
    asset: AttributeControlLimitSetAsset,
    *,
    relative_path: Path,
    asset_sha256: str,
) -> AttributeControlLimitSetRecord:
    return AttributeControlLimitSetRecord(
        limit_set_id=str(asset.limit_set_id),
        source_analysis_id=str(asset.source_analysis_id),
        source_dataset_version_id=str(asset.source_dataset_version_id),
        asset_schema_version=asset.asset_schema_version,
        method_id=asset.method_id,
        source_method_version=asset.source_method_version,
        phase2_method_version=asset.phase2_method_version,
        chart_type=asset.chart_type,
        count_definition=asset.count_definition,
        count_column_id=str(asset.count.column_id),
        denominator_column_id=(
            None if asset.denominator is None else str(asset.denominator.column_id)
        ),
        source_schema_hash=asset.source_schema_hash,
        source_canonical_sha256=asset.source_canonical_sha256,
        source_config_sha256=asset.source_config_sha256,
        source_result_sha256=asset.source_result_sha256,
        filter_snapshot_sha256=asset.filter_snapshot_sha256,
        row_snapshot_sha256=asset.row_snapshot_sha256,
        baseline_point_count=asset.baseline_point_count,
        total_count=asset.total_count,
        total_denominator=asset.total_denominator,
        center_line=asset.frozen_center_line,
        fixed_sample_size=asset.fixed_sample_size,
        constant_opportunity_confirmed=asset.constant_opportunity_confirmed,
        sigma_multiplier=asset.sigma_multiplier,
        calculation_policy=asset.calculation_policy,
        natural_bound_policy=asset.natural_bound_policy,
        asset_path=relative_path.as_posix(),
        asset_sha256=asset_sha256,
        created_at=asset.created_at,
        closed_at=asset.closed_at,
        app_version=asset.creator_provenance.app_version,
    )


def _column_by_id(context: DatasetRowsContext, column_id: str) -> DatasetColumnRecord:
    column = next((item for item in context.columns if item.column_id == column_id), None)
    if column is None:
        raise _source_invalid()
    return column


def _result_column_matches(result: _ResultColumn, column: DatasetColumnRecord) -> bool:
    return (
        str(result.column_id) == column.column_id
        and result.data_type == column.data_type
        and result.measurement_level == column.measurement_level
        and result.role == column.role
        and result.unit == column.unit
    )


def _column_dependency(column: DatasetColumnRecord) -> AttributeControlLimitSetColumnDependency:
    return AttributeControlLimitSetColumnDependency(
        column_id=UUID(column.column_id),
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _natural_bound_policy(
    chart_type: Literal["p", "np", "c", "u"],
) -> Literal["binomial_zero_one", "binomial_zero_fixed_sample_size", "poisson_zero"]:
    if chart_type == "p":
        return "binomial_zero_one"
    if chart_type == "np":
        return "binomial_zero_fixed_sample_size"
    return "poisson_zero"


def _asset_relative_path(limit_set_id: str) -> Path:
    return Path("artifacts") / "attribute-control-limit-sets" / limit_set_id / "limit-set.json"


def _safe_asset_path(
    workspace_root: Path,
    stored_path: str,
    error_factory: Callable[[], ApiError],
) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise error_factory()
    return workspace_root / relative_path


def _optional_float_equal(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return isfinite(left) and isfinite(right) and isclose(left, right, rel_tol=0.0, abs_tol=0.0)


def _remove_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _source_invalid() -> ApiError:
    return _error(
        "attribute_control_chart_limit_set_source_analysis_invalid",
        "source Phase I 분석 계약이 limit set 승격 요구사항과 일치하지 않습니다.",
    )


def _source_artifact_mismatch() -> ApiError:
    return _error(
        "attribute_control_chart_limit_set_source_artifact_mismatch",
        "source Phase I 분석 자산 관계를 검증할 수 없습니다.",
    )


def _source_ineligible() -> ApiError:
    return _error(
        "attribute_control_chart_limit_set_source_ineligible",
        "Phase II baseline은 20점 이상이며 기존 신호, 약한 근사, 과산포가 없어야 합니다.",
    )


def _error(code: str, message: str, status_code: int = status.HTTP_409_CONFLICT) -> ApiError:
    return ApiError(code=code, message=message, status_code=status_code)
