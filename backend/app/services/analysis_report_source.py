"""Read immutable report dependencies without reopening canonical data rows."""

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_results import (
    StoredAnalysisRunResult,
    load_analysis_run_result_base,
)
from app.storage.metadata import (
    get_analysis_artifact_record,
    get_analysis_run_record,
    get_attribute_control_limit_set_record,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_analysis_report_source(settings: Settings, analysis_id: UUID) -> StoredAnalysisRunResult:
    stored = _load_owned_result(settings, analysis_id)
    config = _validate_owner(stored, analysis_id)
    snapshot = _validate_snapshot(settings, stored, config)
    payload = stored.envelope.result or {}
    if stored.record.method_id == "quality.attribute_control_chart":
        options = config.get("options")
        configured_phase = options.get("phase", "phase_1") if isinstance(options, dict) else None
        result_phase = payload.get("phase", "phase_1")
        if configured_phase != result_phase:
            raise _mismatch()
        if result_phase == "phase_2":
            _validate_frozen_control_dependency(settings, stored, config, snapshot)
    return stored


def _load_owned_result(settings: Settings, analysis_id: UUID) -> StoredAnalysisRunResult:
    # The normal calculation reader retains its own freshness policy. Report-only
    # reads reject link aliases before its base reader opens an immutable result.
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is not None and record.result_path is not None:
        _safe_owned_path(settings.workspace_root, record.result_path, require_file=False)
    stored = load_analysis_run_result_base(settings, analysis_id)
    if record is not None and (
        stored.record.result_path != record.result_path
        or stored.record.result_sha256 != record.result_sha256
    ):
        raise _mismatch()
    return stored


def _validate_owner(stored: StoredAnalysisRunResult, analysis_id: UUID) -> dict[str, Any]:
    record, envelope = stored.record, stored.envelope
    provenance = envelope.provenance
    dataset_id = None if envelope.dataset_version_id is None else str(envelope.dataset_version_id)
    if (
        record.analysis_id != str(analysis_id)
        or str(envelope.analysis_id) != record.analysis_id
        or envelope.method_id != record.method_id
        or envelope.method_version != record.method_version
        or dataset_id != record.dataset_version_id
        or envelope.status != record.status
        or provenance.method_id != envelope.method_id
        or provenance.method_version != envelope.method_version
        or provenance.dataset_version_id != envelope.dataset_version_id
    ):
        raise _mismatch()
    try:
        config = json.loads(record.config_json)
    except (ValueError, TypeError) as exc:
        raise _mismatch() from exc
    if not isinstance(config, dict):
        raise _mismatch()
    for key, expected in (
        ("method_id", record.method_id),
        ("method_version", record.method_version),
        ("dataset_version_id", record.dataset_version_id),
    ):
        if key in config and config[key] != expected:
            raise _mismatch()
    return config


def _validate_snapshot(
    settings: Settings, stored: StoredAnalysisRunResult, config: dict[str, Any]
) -> dict[str, Any] | None:
    reference = config.get("row_snapshot")
    provenance = stored.envelope.provenance
    if reference is None and provenance.row_snapshot_sha256 is None:
        return None  # Older result envelopes did not promise a row-selection artifact.
    if not isinstance(reference, dict) or not isinstance(reference.get("artifact_id"), str):
        raise _mismatch()
    artifact = get_analysis_artifact_record(
        settings.workspace_root, stored.record.analysis_id, reference["artifact_id"]
    )
    if (
        artifact is None
        or artifact.kind != "analysis_row_snapshot"
        or artifact.analysis_id != stored.record.analysis_id
        or artifact.sha256 != provenance.row_snapshot_sha256
        or any(
            reference.get(key) != getattr(artifact, key)
            for key in ("kind", "path", "sha256", "media_type")
        )
    ):
        raise _mismatch()
    path = _safe_owned_path(settings.workspace_root, artifact.path)
    try:
        data = path.read_bytes()
        payload = json.loads(data)
    except (OSError, ValueError) as exc:
        raise _mismatch() from exc
    if hashlib.sha256(data).hexdigest() != artifact.sha256 or not isinstance(payload, dict):
        raise _mismatch()
    selection, canonical = payload.get("selection"), payload.get("source_canonical_artifact")
    filters = payload.get("filter_snapshot")
    if (
        not isinstance(selection, dict)
        or not isinstance(canonical, dict)
        or not isinstance(filters, dict)
    ):
        raise _mismatch()
    try:
        filter_hash = hashlib.sha256(
            json.dumps(
                filters, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        ).hexdigest()
    except (TypeError, ValueError) as exc:
        raise _mismatch() from exc
    if (
        type(payload.get("artifact_schema_version")) is not int
        or payload["artifact_schema_version"] != 1
        or payload.get("artifact_kind") != "analysis_row_snapshot"
        or artifact.media_type != "application/json"
        or payload.get("analysis_id") != stored.record.analysis_id
        or payload.get("dataset_version_id") != stored.record.dataset_version_id
        or payload.get("source_schema_hash") != provenance.source_schema_hash
        or payload.get("filter_snapshot_sha256") != provenance.filter_snapshot_sha256
        or config.get("filter_snapshot_sha256") != provenance.filter_snapshot_sha256
        or filter_hash != provenance.filter_snapshot_sha256
        or config.get("filter_snapshot") != filters
        or payload.get("row_identity") != {"kind": "canonical_row_index", "base": 0}
        or type(payload["row_identity"]["base"]) is not int
        or not _selection_is_valid(selection)
        or canonical.get("kind") != "canonical_rows"
        or canonical.get("media_type") != "application/x-ndjson"
        or not isinstance(canonical.get("sha256"), str)
        or not _SHA256.fullmatch(canonical["sha256"])
        or type(canonical.get("size_bytes")) is not int
        or canonical["size_bytes"] < 0
        or selection.get("row_count_total") != provenance.row_count_total
        or selection.get("row_count_included") != provenance.row_count_included
        or selection.get("row_count_total") != reference.get("row_count_total")
        or selection.get("row_count_included") != reference.get("row_count_included")
    ):
        raise _mismatch()
    return payload


def _selection_is_valid(selection: dict[str, Any]) -> bool:
    total, included, excluded = (
        selection.get(key)
        for key in ("row_count_total", "row_count_included", "row_count_excluded")
    )
    if type(total) is not int or type(included) is not int or type(excluded) is not int:
        return False
    if min(total, included, excluded) < 0:
        return False
    if included + excluded != total:
        return False
    if selection.get("kind") == "all_rows":
        return bool(included == total and "row_ranges" not in selection)
    ranges = selection.get("row_ranges")
    if selection.get("kind") != "row_ranges" or not isinstance(ranges, list):
        return False
    count, previous = 0, 0
    for interval in ranges:
        if not isinstance(interval, dict) or set(interval) != {"start", "end"}:
            return False
        start, end = interval["start"], interval["end"]
        if (
            type(start) is not int
            or type(end) is not int
            or start < previous
            or end <= start
            or end > total
        ):
            return False
        count += end - start
        previous = end
    return bool(count == included)


def _validate_frozen_control_dependency(
    settings: Settings,
    stored: StoredAnalysisRunResult,
    config: dict[str, Any],
    snapshot: dict[str, Any] | None,
) -> None:
    from app.services.attribute_control_limit_sets import (
        validate_attribute_control_limit_set_for_retention,
    )

    payload = stored.envelope.result or {}
    options = config.get("options")
    dependency = payload.get("limit_set_dependency")
    target = payload.get("target_dependency")
    if (
        snapshot is None
        or not isinstance(options, dict)
        or not isinstance(dependency, dict)
        or not isinstance(target, dict)
        or not isinstance(options.get("limit_set_id"), str)
        or options.get("phase") != "phase_2"
    ):
        raise _mismatch()
    asset_record = get_attribute_control_limit_set_record(
        settings.workspace_root, options["limit_set_id"]
    )
    if asset_record is None:
        raise _mismatch()
    _safe_owned_path(settings.workspace_root, asset_record.asset_path)
    asset = validate_attribute_control_limit_set_for_retention(settings, asset_record)
    source = _load_owned_result(settings, asset.source_analysis_id)
    source_config = _validate_owner(source, asset.source_analysis_id)
    source_snapshot = _validate_snapshot(settings, source, source_config)
    source_payload = source.envelope.result or {}
    if (
        source_snapshot is None
        or source.record.result_sha256 != asset.source_result_sha256
        or source.envelope.method_id != asset.method_id
        or source.envelope.method_version != asset.source_method_version
        or source.envelope.dataset_version_id != asset.source_dataset_version_id
        or (source.envelope.result or {}).get("schema_version")
        != asset.source_result_schema_version
        or source.envelope.provenance.row_snapshot_sha256 != asset.row_snapshot_sha256
        or source.envelope.provenance.filter_snapshot_sha256 != asset.filter_snapshot_sha256
        or source.envelope.provenance.source_schema_hash != asset.source_schema_hash
        or source_snapshot["source_canonical_artifact"]["sha256"] != asset.source_canonical_sha256
        or source_payload.get("phase", "phase_1") != "phase_1"
        or stored.record.method_version != asset.phase2_method_version
    ):
        raise _mismatch()
    expected_limit = {
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
    canonical = snapshot.get("source_canonical_artifact")
    selection = snapshot.get("selection")
    if not isinstance(canonical, dict) or not isinstance(selection, dict):
        raise _mismatch()
    expected_target = {
        "dataset_version_id": stored.record.dataset_version_id,
        "schema_hash": stored.envelope.provenance.source_schema_hash,
        "canonical_sha256": canonical.get("sha256"),
        "filter_snapshot_sha256": stored.envelope.provenance.filter_snapshot_sha256,
        "row_snapshot_sha256": stored.envelope.provenance.row_snapshot_sha256,
        "row_count_total": selection.get("row_count_total"),
        "row_count_included": selection.get("row_count_included"),
        "count_column_id": options.get("count_column_id"),
        "denominator_column_id": options.get("denominator_column_id"),
    }
    if (
        dependency != expected_limit
        or target != expected_target
        or payload.get("center_line") != asset.frozen_center_line
        or payload.get("chart_type") != asset.chart_type
        or payload.get("count_definition") != asset.count_definition
        or payload.get("control_limit_method") != "phase_2_frozen_three_sigma"
        or payload.get("baseline") != "verified_immutable_limit_set"
        or payload.get("n_total") != expected_target["row_count_included"]
        or not isinstance(payload.get("count"), dict)
        or payload["count"].get("column_id") != options.get("count_column_id")
        or (payload.get("denominator") is not None and not isinstance(payload["denominator"], dict))
        or (payload.get("denominator") or {}).get("column_id")
        != options.get("denominator_column_id")
    ):
        raise _mismatch()


def _safe_owned_path(root: Path, stored_path: str, *, require_file: bool = True) -> Path:
    if not isinstance(stored_path, str):
        raise _mismatch()
    relative = Path(stored_path)
    if relative.anchor or relative.drive or not relative.parts or ".." in relative.parts:
        raise _mismatch()
    try:
        canonical_root = root.resolve()
        candidate = canonical_root
        for part in relative.parts:
            candidate /= part
            if candidate.exists() or candidate.is_symlink():
                info = candidate.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
                    stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
                ):
                    raise _mismatch()
        path = candidate.resolve()
        if not path.is_relative_to(canonical_root) or (require_file and not path.is_file()):
            raise _mismatch()
        return path
    except (OSError, ValueError) as exc:
        raise _mismatch() from exc


def _mismatch() -> ApiError:
    return ApiError(
        code="analysis_report_source_dependency_mismatch",
        message="The stored report source or its immutable dependencies do not match.",
        status_code=409,
    )
