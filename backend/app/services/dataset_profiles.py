import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final, Literal
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.datasets import (
    DatasetArtifactResponse,
    DatasetColumnDataType,
    DatasetColumnProfile,
    DatasetColumnRole,
    DatasetMeasurementLevel,
    DatasetProfileIssue,
    DatasetProfilePreflight,
    DatasetProfileResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.canonical_artifacts import CANONICAL_ROWS_KIND
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
)
from app.storage.atomic import atomic_write_bytes
from app.storage.metadata import (
    DatasetArtifactRecord,
    DatasetColumnRecord,
    get_dataset_artifact_record,
    upsert_dataset_artifact_record,
)

PROFILE_SCHEMA_VERSION: Final = 3
PROFILE_ARTIFACT_SCHEMA_VERSION: Final = 1
PROFILE_ARTIFACT_KIND: Final = "profile_summary"
PROFILE_ARTIFACT_MEDIA_TYPE: Final = "application/json"
UNIQUE_COUNT_LIMIT: Final = 1000
DUPLICATE_ROW_CHECK_LIMIT: Final = 100_000
MEMORY_PREFLIGHT_WARNING_BYTES: Final = 512 * 1024 * 1024
ESTIMATED_BYTES_PER_CELL: Final = 64
HIGH_MISSING_RATE_THRESHOLD: Final = 0.5
NUMERIC_DATA_TYPES: Final = {"integer", "decimal"}


@dataclass
class _ColumnAccumulator:
    column: DatasetColumnRecord
    n_total: int = 0
    n_present: int = 0
    n_missing: int = 0
    n_numeric: int = 0
    n_non_numeric: int = 0
    numeric_sum: Decimal = Decimal("0")
    numeric_min: Decimal | None = None
    numeric_max: Decimal | None = None
    unique_values: set[str] = field(default_factory=set)
    unique_count_capped: bool = False

    def observe(self, value: str | None, *, decimal: str, thousands: str | None) -> None:
        self.n_total += 1
        if value is None:
            self.n_missing += 1
            return

        self.n_present += 1
        self._observe_unique(value)
        parsed = _parse_decimal(value.strip(), decimal=decimal, thousands=thousands)
        if parsed is None:
            self.n_non_numeric += 1
            return

        self.n_numeric += 1
        self.numeric_sum += parsed
        self.numeric_min = parsed if self.numeric_min is None else min(self.numeric_min, parsed)
        self.numeric_max = parsed if self.numeric_max is None else max(self.numeric_max, parsed)

    def _observe_unique(self, value: str) -> None:
        if self.unique_count_capped:
            return
        self.unique_values.add(value)
        if len(self.unique_values) > UNIQUE_COUNT_LIMIT:
            self.unique_count_capped = True
            self.unique_values.clear()


@dataclass
class _PreflightAccumulator:
    duplicate_row_count: int = 0
    duplicate_row_count_capped: bool = False
    _seen_row_signatures: set[str] = field(default_factory=set)

    def observe_row(self, values: list[str | None]) -> None:
        if self.duplicate_row_count_capped:
            return

        signature = hashlib.sha256(
            json.dumps(
                values,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8"),
        ).hexdigest()
        if signature in self._seen_row_signatures:
            self.duplicate_row_count += 1
            return

        self._seen_row_signatures.add(signature)
        if len(self._seen_row_signatures) > DUPLICATE_ROW_CHECK_LIMIT:
            self.duplicate_row_count_capped = True
            self._seen_row_signatures.clear()


def get_dataset_profile(settings: Settings, version_id: UUID) -> DatasetProfileResponse:
    context = get_dataset_rows_context(settings, version_id)
    accumulators = [_ColumnAccumulator(column=column) for column in context.columns]
    preflight_accumulator = _PreflightAccumulator()
    canonical_artifact = get_dataset_artifact_record(
        settings.workspace_root,
        str(version_id),
        CANONICAL_ROWS_KIND,
    )

    for row in iter_dataset_rows(context):
        preflight_accumulator.observe_row(row)
        for column_index, accumulator in enumerate(accumulators):
            value = row[column_index] if column_index < len(row) else None
            accumulator.observe(
                value,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
            )

    columns = [_column_profile(accumulator) for accumulator in accumulators]
    preflight = _profile_preflight(context, preflight_accumulator, canonical_artifact)
    warnings = _dataset_warnings(columns, context, preflight)
    warnings.extend(_canonical_artifact_warnings(settings, canonical_artifact))
    profile = DatasetProfileResponse(
        profile_schema_version=PROFILE_SCHEMA_VERSION,
        version_id=UUID(context.version.version_id),
        dataset_id=UUID(context.version.dataset_id),
        row_count=context.version.row_count,
        column_count=context.version.column_count,
        schema_hash=context.version.schema_hash,
        computed_at=_utc_now(),
        unique_count_limit=UNIQUE_COUNT_LIMIT,
        canonical_artifact=_dataset_artifact_response(canonical_artifact),
        profile_artifact=None,
        preflight=preflight,
        columns=columns,
        warnings=warnings,
    )
    profile_artifact = _persist_profile_artifact(settings, profile)
    return profile.model_copy(
        update={"profile_artifact": _dataset_artifact_response(profile_artifact)},
    )


def _column_profile(accumulator: _ColumnAccumulator) -> DatasetColumnProfile:
    column = accumulator.column
    missing_rate = accumulator.n_missing / accumulator.n_total if accumulator.n_total > 0 else 0.0
    unique_count = (
        UNIQUE_COUNT_LIMIT if accumulator.unique_count_capped else len(accumulator.unique_values)
    )
    constant = (
        accumulator.n_present > 0 and not accumulator.unique_count_capped and unique_count == 1
    )
    numeric_mean = (
        accumulator.numeric_sum / accumulator.n_numeric if accumulator.n_numeric > 0 else None
    )

    return DatasetColumnProfile(
        column_id=UUID(column.column_id),
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=DatasetColumnDataType(column.data_type),
        measurement_level=DatasetMeasurementLevel(column.measurement_level),
        role=DatasetColumnRole(column.role),
        n_total=accumulator.n_total,
        n_present=accumulator.n_present,
        n_missing=accumulator.n_missing,
        missing_rate=missing_rate,
        unique_count=unique_count,
        unique_count_capped=accumulator.unique_count_capped,
        n_numeric=accumulator.n_numeric,
        n_non_numeric=accumulator.n_non_numeric,
        numeric_min=_float_or_none(accumulator.numeric_min),
        numeric_max=_float_or_none(accumulator.numeric_max),
        numeric_mean=_float_or_none(numeric_mean),
        constant=constant,
        warnings=_column_warnings(accumulator, unique_count, constant, missing_rate),
    )


def _column_warnings(
    accumulator: _ColumnAccumulator,
    unique_count: int,
    constant: bool,
    missing_rate: float,
) -> list[DatasetProfileIssue]:
    warnings: list[DatasetProfileIssue] = []
    column = accumulator.column

    if accumulator.n_present == 0:
        warnings.append(
            _issue("all_missing", "warning", "모든 값이 결측입니다."),
        )
    elif constant:
        warnings.append(
            _issue("constant_column", "warning", "결측을 제외한 값이 모두 같습니다."),
        )

    if missing_rate >= HIGH_MISSING_RATE_THRESHOLD and accumulator.n_missing > 0:
        warnings.append(
            _issue("high_missing_rate", "warning", "결측 비율이 50% 이상입니다."),
        )

    if (
        column.data_type in NUMERIC_DATA_TYPES
        and accumulator.n_non_numeric > 0
        and accumulator.n_present > 0
    ):
        warnings.append(
            _issue(
                "non_numeric_values_in_numeric_column",
                "warning",
                "수치형 컬럼에 숫자로 해석할 수 없는 값이 있습니다.",
            ),
        )

    if accumulator.unique_count_capped:
        warnings.append(
            _issue(
                "unique_count_capped",
                "info",
                "고유값 수가 많아 정확한 개수 계산을 제한했습니다.",
            ),
        )

    if (
        accumulator.n_total >= 2
        and accumulator.n_missing == 0
        and not accumulator.unique_count_capped
        and unique_count == accumulator.n_total
        and column.role != DatasetColumnRole.ID.value
        and column.measurement_level != DatasetMeasurementLevel.ID.value
    ):
        warnings.append(
            _issue(
                "possible_identifier",
                "info",
                "모든 행의 값이 고유합니다. ID 컬럼인지 확인하세요.",
            ),
        )

    return warnings


def _dataset_warnings(
    columns: list[DatasetColumnProfile],
    context: DatasetRowsContext,
    preflight: DatasetProfilePreflight,
) -> list[DatasetProfileIssue]:
    warnings: list[DatasetProfileIssue] = []
    if any(column.unique_count_capped for column in columns):
        warnings.append(
            _issue(
                "profile_unique_counts_capped",
                "info",
                "일부 컬럼은 고유값 수가 제한치에 도달해 정확한 고유값 수를 반환하지 않았습니다.",
            ),
        )

    if len(columns) != context.version.column_count:
        warnings.append(
            _issue(
                "profile_column_count_mismatch",
                "error",
                "프로파일 컬럼 수가 데이터셋 버전 메타데이터와 일치하지 않습니다.",
            ),
        )

    if preflight.duplicate_row_count > 0:
        warnings.append(
            _issue(
                "duplicate_rows_detected",
                "warning",
                "완전히 동일한 행이 감지되었습니다. 분석 전 중복 여부를 확인하세요.",
            ),
        )

    if preflight.duplicate_row_count_capped:
        warnings.append(
            _issue(
                "duplicate_row_check_capped",
                "info",
                "중복 행 점검이 제한치에 도달해 이후 행의 중복 여부를 계산하지 않았습니다.",
            ),
        )

    if preflight.estimated_memory_bytes >= MEMORY_PREFLIGHT_WARNING_BYTES:
        warnings.append(
            _issue(
                "estimated_memory_high",
                "warning",
                "데이터셋을 메모리에 적재할 때 큰 메모리가 필요할 수 있습니다.",
            ),
        )
    return warnings


def _profile_preflight(
    context: DatasetRowsContext,
    preflight_accumulator: _PreflightAccumulator,
    canonical_artifact: DatasetArtifactRecord | None,
) -> DatasetProfilePreflight:
    canonical_size = canonical_artifact.size_bytes if canonical_artifact is not None else 0
    estimated_memory_bytes = max(
        context.dataset.size_bytes,
        canonical_size,
        (
            context.version.row_count
            * max(context.version.column_count, 1)
            * ESTIMATED_BYTES_PER_CELL
        )
        + (context.version.row_count * 16)
        + (context.version.column_count * 1024),
    )
    return DatasetProfilePreflight(
        estimated_memory_bytes=estimated_memory_bytes,
        duplicate_row_count=preflight_accumulator.duplicate_row_count,
        duplicate_row_count_capped=preflight_accumulator.duplicate_row_count_capped,
        duplicate_row_check_limit=DUPLICATE_ROW_CHECK_LIMIT,
    )


def _canonical_artifact_warnings(
    settings: Settings,
    canonical_artifact: DatasetArtifactRecord | None,
) -> list[DatasetProfileIssue]:
    if canonical_artifact is None:
        return [
            _issue(
                "canonical_artifact_missing",
                "error",
                "canonical parsed artifact 메타데이터가 없습니다.",
            ),
        ]

    artifact_path = _safe_artifact_path(settings.workspace_root, canonical_artifact.path)
    if not artifact_path.exists():
        return [
            _issue(
                "canonical_artifact_file_missing",
                "error",
                "canonical parsed artifact 파일을 찾을 수 없습니다.",
            ),
        ]

    if artifact_path.stat().st_size != canonical_artifact.size_bytes:
        return [
            _issue(
                "canonical_artifact_size_mismatch",
                "error",
                "canonical parsed artifact 파일 크기가 메타데이터와 일치하지 않습니다.",
            ),
        ]
    return []


def _dataset_artifact_response(
    artifact: DatasetArtifactRecord | None,
) -> DatasetArtifactResponse | None:
    if artifact is None:
        return None
    return DatasetArtifactResponse(
        artifact_id=UUID(artifact.artifact_id),
        version_id=UUID(artifact.version_id),
        kind=artifact.kind,
        path=artifact.path,
        sha256=artifact.sha256,
        media_type=artifact.media_type,
        size_bytes=artifact.size_bytes,
        created_at=artifact.created_at,
    )


def _persist_profile_artifact(
    settings: Settings,
    profile: DatasetProfileResponse,
) -> DatasetArtifactRecord:
    artifact_id = str(uuid4())
    relative_path = _profile_artifact_relative_path(
        dataset_id=str(profile.dataset_id),
        version_id=str(profile.version_id),
        artifact_id=artifact_id,
    )
    payload = {
        "artifact_schema_version": PROFILE_ARTIFACT_SCHEMA_VERSION,
        "artifact_kind": PROFILE_ARTIFACT_KIND,
        "profile": profile.model_dump(mode="json", exclude={"profile_artifact"}),
    }
    artifact_bytes = _canonical_json_bytes(payload)
    artifact_path = settings.workspace_root / relative_path
    atomic_write_bytes(artifact_path, artifact_bytes)

    record = DatasetArtifactRecord(
        artifact_id=artifact_id,
        version_id=str(profile.version_id),
        kind=PROFILE_ARTIFACT_KIND,
        path=relative_path.as_posix(),
        sha256=hashlib.sha256(artifact_bytes).hexdigest(),
        media_type=PROFILE_ARTIFACT_MEDIA_TYPE,
        size_bytes=len(artifact_bytes),
        created_at=profile.computed_at,
    )
    try:
        previous_record = get_dataset_artifact_record(
            settings.workspace_root,
            str(profile.version_id),
            PROFILE_ARTIFACT_KIND,
        )
        upsert_dataset_artifact_record(settings.workspace_root, record)
    except Exception:
        _remove_file_if_exists(artifact_path)
        raise

    if previous_record is not None and previous_record.path != record.path:
        _remove_file_if_exists(_safe_artifact_path(settings.workspace_root, previous_record.path))
    return record


def _profile_artifact_relative_path(
    *,
    dataset_id: str,
    version_id: str,
    artifact_id: str,
) -> Path:
    return (
        Path("workspaces")
        / "datasets"
        / dataset_id
        / "versions"
        / version_id
        / "profiles"
        / f"{artifact_id}.profile.json"
    )


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _remove_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _safe_artifact_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="dataset_artifact_path_invalid",
            message="저장된 dataset artifact 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return workspace_root / relative_path


def _parse_decimal(value: str, *, decimal: str, thousands: str | None) -> Decimal | None:
    if value == "":
        return None
    normalized = value
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


def _float_or_none(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _issue(
    code: str,
    severity: Literal["info", "warning", "error"],
    message: str,
) -> DatasetProfileIssue:
    return DatasetProfileIssue(
        code=code,
        severity=severity,
        message=message,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
