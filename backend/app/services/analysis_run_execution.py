import hashlib
import json
import os
import platform as platform_module
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.analyses import (
    AnalysisFilterSnapshot,
    AnalysisProvenance,
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisRunState,
    AnalysisWarning,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.dataset_rows import DatasetRowsContext, iter_dataset_rows
from app.storage.atomic import atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    DatasetColumnRecord,
    insert_analysis_run_record_with_artifacts,
)

APP_VERSION = "0.1.0"
CONFIG_SCHEMA_VERSION = 2
ROW_SNAPSHOT_SCHEMA_VERSION = 1
ROW_SNAPSHOT_ARTIFACT_KIND = "analysis_row_snapshot"
ROW_SNAPSHOT_MEDIA_TYPE = "application/json"
MAX_FILTER_CONDITIONS = 20
MAX_FILTER_STRING_LENGTH = 200
NUMERIC_DATA_TYPES = {"integer", "decimal"}
FILTER_OPERATORS = {
    "is_missing",
    "is_not_missing",
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
}
NUMERIC_FILTER_OPERATORS = {"gt", "gte", "lt", "lte"}


@dataclass(frozen=True)
class RowSnapshotArtifact:
    record: AnalysisArtifactRecord
    relative_path: Path
    payload: dict[str, Any]
    included_row_indices: tuple[int, ...] | None


@dataclass(frozen=True)
class FilterCondition:
    column: DatasetColumnRecord
    operator: str
    value: object | None = None


def analysis_provenance(
    settings: Settings,
    request: AnalysisRunRequest,
    context: DatasetRowsContext,
    row_snapshot: RowSnapshotArtifact,
) -> AnalysisProvenance:
    runtime = runtime_build_provenance(settings)
    return AnalysisProvenance(
        method_id=request.method_id,
        method_version=request.method_version,
        dataset_version_id=request.dataset_version_id,
        source_schema_hash=context.version.schema_hash,
        filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
        row_snapshot_sha256=row_snapshot.record.sha256,
        row_count_total=context.version.row_count,
        row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
        app_version=APP_VERSION,
        **runtime,
    )


def runtime_build_provenance(settings: Settings) -> dict[str, Any]:
    return {
        "python_version": _runtime_python_version(),
        "platform": _runtime_platform(),
        "build_commit": _build_commit(settings),
        "package_versions": _dependency_versions(),
    }


def create_row_snapshot_artifact(
    *,
    settings: Settings,
    analysis_id: str,
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
    created_at: str,
) -> RowSnapshotArtifact:
    filter_snapshot_payload = filter_snapshot.model_dump(mode="json")
    filter_snapshot_sha256 = hashlib.sha256(
        canonical_json_bytes(filter_snapshot_payload),
    ).hexdigest()
    included_row_indices = freeze_row_indices(context, filter_snapshot)
    row_count_included = (
        context.version.row_count if included_row_indices is None else len(included_row_indices)
    )
    row_count_excluded = context.version.row_count - row_count_included
    selection: dict[str, Any] = {
        "kind": "all_rows" if included_row_indices is None else "row_ranges",
        "row_count_total": context.version.row_count,
        "row_count_included": row_count_included,
        "row_count_excluded": row_count_excluded,
    }
    if included_row_indices is not None:
        selection["row_ranges"] = row_ranges(included_row_indices)

    artifact_id = str(uuid4())
    relative_path = row_snapshot_relative_path(analysis_id)
    payload: dict[str, Any] = {
        "artifact_schema_version": ROW_SNAPSHOT_SCHEMA_VERSION,
        "artifact_kind": ROW_SNAPSHOT_ARTIFACT_KIND,
        "analysis_id": analysis_id,
        "dataset_version_id": context.version.version_id,
        "source_schema_hash": context.version.schema_hash,
        "source_canonical_artifact": {
            "kind": context.canonical_rows_artifact.kind,
            "sha256": context.canonical_rows_artifact.sha256,
            "media_type": context.canonical_rows_artifact.media_type,
            "size_bytes": context.canonical_rows_artifact.size_bytes,
        },
        "filter_snapshot": filter_snapshot_payload,
        "filter_snapshot_sha256": filter_snapshot_sha256,
        "row_identity": {
            "kind": "canonical_row_index",
            "base": 0,
        },
        "selection": selection,
        "created_at": created_at,
    }
    artifact_bytes = canonical_json_bytes(payload)
    artifact_path = settings.workspace_root / relative_path
    atomic_write_bytes(artifact_path, artifact_bytes)

    return RowSnapshotArtifact(
        record=AnalysisArtifactRecord(
            artifact_id=artifact_id,
            analysis_id=analysis_id,
            kind=ROW_SNAPSHOT_ARTIFACT_KIND,
            path=relative_path.as_posix(),
            sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            media_type=ROW_SNAPSHOT_MEDIA_TYPE,
            created_at=created_at,
        ),
        relative_path=relative_path,
        payload=payload,
        included_row_indices=included_row_indices,
    )


def freeze_row_indices(
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
) -> tuple[int, ...] | None:
    if not filter_snapshot.conditions:
        return None

    conditions = parse_filter_conditions(context, filter_snapshot)
    included_row_indices: list[int] = []
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if all(row_matches_condition(row, condition, context) for condition in conditions):
            included_row_indices.append(row_index)
    return tuple(included_row_indices)


def parse_filter_conditions(
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
) -> list[FilterCondition]:
    if filter_snapshot.expression_version != 1:
        raise ApiError(
            code="filter_expression_version_unsupported",
            message="지원하지 않는 필터 표현식 버전입니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    if len(filter_snapshot.conditions) > MAX_FILTER_CONDITIONS:
        raise ApiError(
            code="too_many_filter_conditions",
            message="필터 조건 수가 허용 범위를 초과했습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    conditions: list[FilterCondition] = []
    for raw_condition in filter_snapshot.conditions:
        if not isinstance(raw_condition, dict):
            raise invalid_filter_condition()

        column_id = raw_condition.get("column_id")
        operator = raw_condition.get("operator")
        if not isinstance(column_id, str) or not column_id:
            raise invalid_filter_condition()
        if not isinstance(operator, str) or operator not in FILTER_OPERATORS:
            raise ApiError(
                code="filter_operator_not_supported",
                message="지원하지 않는 필터 연산자입니다.",
            )

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="filter_column_not_found",
                message="필터 컬럼을 찾을 수 없습니다.",
            )

        if operator in {"is_missing", "is_not_missing"}:
            conditions.append(FilterCondition(column=column, operator=operator))
            continue

        if "value" not in raw_condition:
            raise ApiError(
                code="filter_value_required",
                message="필터 조건 값이 필요합니다.",
            )
        value = raw_condition["value"]
        validate_filter_value(column, operator, value)
        conditions.append(FilterCondition(column=column, operator=operator, value=value))

    return conditions


def validate_filter_value(
    column: DatasetColumnRecord,
    operator: str,
    value: object,
) -> None:
    if value is None:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    if operator in NUMERIC_FILTER_OPERATORS and column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="filter_operator_not_supported_for_column",
            message="이 컬럼에는 요청한 필터 연산자를 사용할 수 없습니다.",
        )
    if column.data_type in NUMERIC_DATA_TYPES:
        filter_decimal_value(value)
        return
    if not isinstance(value, str) or len(value) > MAX_FILTER_STRING_LENGTH:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )


def row_matches_condition(
    row: list[str | None],
    condition: FilterCondition,
    context: DatasetRowsContext,
) -> bool:
    value = row[condition.column.column_index] if condition.column.column_index < len(row) else None
    missing = value is None or value.strip() == ""

    if condition.operator == "is_missing":
        return missing
    if condition.operator == "is_not_missing":
        return not missing
    if missing:
        return False
    assert value is not None

    if condition.column.data_type in NUMERIC_DATA_TYPES:
        row_value = parse_filter_decimal(
            value,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
        )
        filter_value = filter_decimal_value(condition.value)
        if row_value is None:
            return False
        return compare_values(row_value, filter_value, condition.operator)

    string_filter_value = condition.value
    if not isinstance(string_filter_value, str):
        return False
    return compare_values(value, string_filter_value, condition.operator)


def iter_rows_for_snapshot(
    context: DatasetRowsContext,
    row_snapshot: RowSnapshotArtifact,
) -> Iterator[list[str | None]]:
    if row_snapshot.included_row_indices is None:
        yield from iter_dataset_rows(context)
        return

    included = set(row_snapshot.included_row_indices)
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if row_index in included:
            yield row


def compare_values(left: Any, right: Any, operator: str) -> bool:
    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    return False


def parse_filter_decimal(
    value: str,
    *,
    decimal: str,
    thousands: str | None,
) -> Decimal | None:
    normalized = value.strip()
    if normalized == "":
        return None
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    return parsed


def filter_decimal_value(value: object) -> Decimal:
    if isinstance(value, bool):
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    if not isinstance(value, int | float | str):
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    try:
        parsed = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        ) from exc
    if not parsed.is_finite():
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    return parsed


def row_ranges(row_indices: tuple[int, ...]) -> list[dict[str, int]]:
    if not row_indices:
        return []

    ranges: list[dict[str, int]] = []
    range_start = row_indices[0]
    previous = row_indices[0]
    for row_index in row_indices[1:]:
        if row_index == previous + 1:
            previous = row_index
            continue
        ranges.append({"start": range_start, "end": previous + 1})
        range_start = row_index
        previous = row_index
    ranges.append({"start": range_start, "end": previous + 1})
    return ranges


def invalid_filter_condition() -> ApiError:
    return ApiError(
        code="invalid_filter_condition",
        message="필터 조건 형식이 올바르지 않습니다.",
    )


def analysis_config_json(
    request: AnalysisRunRequest,
    row_snapshot: RowSnapshotArtifact,
) -> str:
    return json.dumps(
        {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "filter_snapshot": request.filter_snapshot.model_dump(mode="json"),
            "filter_snapshot_sha256": row_snapshot.payload["filter_snapshot_sha256"],
            "row_snapshot": {
                "artifact_id": row_snapshot.record.artifact_id,
                "kind": row_snapshot.record.kind,
                "path": row_snapshot.record.path,
                "sha256": row_snapshot.record.sha256,
                "media_type": row_snapshot.record.media_type,
                "row_count_total": row_snapshot.payload["selection"]["row_count_total"],
                "row_count_included": row_snapshot.payload["selection"]["row_count_included"],
            },
            "roles": request.roles,
            "options": request.options,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def store_succeeded_analysis_result(
    *,
    settings: Settings,
    request: AnalysisRunRequest,
    context: DatasetRowsContext,
    analysis_id: UUID,
    completed_at: str,
    row_snapshot: RowSnapshotArtifact,
    result: dict[str, object],
    warnings: list[AnalysisWarning],
) -> AnalysisResultEnvelope:
    envelope = AnalysisResultEnvelope(
        analysis_id=analysis_id,
        method_id=request.method_id,
        method_version=request.method_version,
        dataset_version_id=request.dataset_version_id,
        status=AnalysisRunState.SUCCEEDED.value,
        warnings=warnings,
        provenance=analysis_provenance(settings, request, context, row_snapshot),
        result=result,
    )

    result_bytes = canonical_json_bytes(envelope.model_dump(mode="json"))
    result_relative_path = analysis_result_relative_path(str(analysis_id))
    result_path: Path | None = None
    try:
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        if result_path is not None:
            remove_file_if_exists(result_path)
        raise
    return envelope


def analysis_result_relative_path(analysis_id: str) -> Path:
    return Path("workspaces") / "analyses" / analysis_id / "result.json"


def row_snapshot_relative_path(analysis_id: str) -> Path:
    return Path("workspaces") / "analyses" / analysis_id / "row_snapshot.json"


def remove_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _runtime_python_version() -> str:
    return sys.version.split()[0]


def _runtime_platform() -> str:
    return platform_module.platform()


def _build_commit(settings: Settings) -> str | None:
    return settings.git_commit or os.environ.get("DATALAB_GIT_COMMIT") or None


@lru_cache(maxsize=1)
def _dependency_versions() -> dict[str, str]:
    packages = ("numpy", "scipy")
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            continue
    return versions
