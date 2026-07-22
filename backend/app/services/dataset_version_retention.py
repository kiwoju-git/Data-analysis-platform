import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.datasets import (
    DatasetVersionDeleteRequest,
    DatasetVersionDeleteResponse,
    DatasetVersionDeletionCounts,
    DatasetVersionDeletionPreflightResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import canonical_json_bytes, utc_now
from app.storage.metadata import (
    DatasetVersionDeletionSnapshot,
    DatasetVersionStorageConflict,
    delete_dataset_version_records,
    get_dataset_version_deletion_snapshot,
    list_dataset_artifact_records_by_id_prefix,
    list_dataset_records_by_id_prefix,
)

DATASET_VERSION_DELETION_PREFLIGHT_SCHEMA_VERSION: Literal[1] = 1
DATASET_VERSION_DELETION_SCHEMA_VERSION: Literal[1] = 1
_ARTIFACT_QUARANTINE = re.compile(r"^\.delete-d-([0-9a-f]{12})-([0-9a-f]{8})\.q$")
_RAW_QUARANTINE = re.compile(r"^\.delete-u-([0-9a-f]{12})-([0-9a-f]{8})\.q$")


@dataclass(frozen=True)
class DatasetVersionQuarantineRecovery:
    restored_file_count: int
    deleted_file_count: int
    pending_file_count: int


@dataclass(frozen=True)
class _OwnedFile:
    owner_id: str
    kind: Literal["artifact", "raw_upload"]
    path: Path
    relative_path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class _QuarantinedFile:
    owned: _OwnedFile
    path: Path


@dataclass(frozen=True)
class _DeletionContext:
    snapshot: DatasetVersionDeletionSnapshot
    files: tuple[_OwnedFile, ...]
    blockers: tuple[str, ...]
    counts: DatasetVersionDeletionCounts
    deletion_scope: Literal["version_only", "dataset_root"]
    manifest_sha256: str


def get_dataset_version_deletion_preflight(
    settings: Settings,
    version_id: UUID,
) -> DatasetVersionDeletionPreflightResponse:
    return _preflight_response(_deletion_context(settings, version_id))


def delete_stored_dataset_version(
    settings: Settings,
    version_id: UUID,
    body: DatasetVersionDeleteRequest,
) -> DatasetVersionDeleteResponse:
    if body.confirmation_version_id != version_id:
        raise _confirmation_error()
    context = _deletion_context(settings, version_id)
    preflight = _preflight_response(context)
    if not preflight.deletion_ready:
        raise ApiError(
            code="dataset_version_deletion_blocked",
            message="이 데이터셋 버전을 참조하는 저장 자산이 있어 삭제할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=",".join(preflight.blockers),
        )
    if body.expected_deletion_manifest_sha256 != context.manifest_sha256:
        raise _confirmation_error()

    quarantined: list[_QuarantinedFile] = []
    try:
        for owned in context.files:
            marker = "d" if owned.kind == "artifact" else "u"
            owner_token = owned.owner_id.replace("-", "")[:12].lower()
            quarantine = owned.path.with_name(f".delete-{marker}-{owner_token}-{uuid4().hex[:8]}.q")
            os.replace(owned.path, quarantine)
            quarantined.append(_QuarantinedFile(owned=owned, path=quarantine))
            if not _file_matches(quarantine, owned.sha256, owned.size_bytes):
                raise DatasetVersionStorageConflict("dataset_version_artifact_mismatch")
        delete_dataset_version_records(
            settings.workspace_root,
            expected_snapshot=context.snapshot,
        )
    except DatasetVersionStorageConflict as exc:
        _restore_or_raise(quarantined)
        error_code = (
            "dataset_version_deletion_blocked"
            if exc.code == "dataset_version_deletion_blocked"
            else "dataset_version_deletion_conflict"
        )
        raise ApiError(
            code=error_code,
            message="삭제 확인 후 데이터셋 버전의 파일 또는 참조 관계가 변경되었습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    except OSError as exc:
        _restore_or_raise(quarantined)
        raise ApiError(
            code="dataset_version_quarantine_failed",
            message="데이터셋 파일을 안전한 삭제 대기 상태로 옮길 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    except Exception:
        _restore_or_raise(quarantined)
        raise

    cleanup_status: Literal["deleted", "quarantined_pending_cleanup"] = "deleted"
    for item in quarantined:
        try:
            item.path.unlink(missing_ok=True)
        except OSError:
            cleanup_status = "quarantined_pending_cleanup"
    _remove_empty_owned_directories(settings.workspace_root, context)
    return DatasetVersionDeleteResponse(
        deletion_schema_version=DATASET_VERSION_DELETION_SCHEMA_VERSION,
        version_id=version_id,
        dataset_id=UUID(context.snapshot.dataset.dataset_id),
        deletion_scope=context.deletion_scope,
        deletion_manifest_sha256=context.manifest_sha256,
        deleted_at=utc_now(),
        deleted_counts=context.counts,
        cleanup_status=cleanup_status,
    )


def recover_dataset_version_quarantine_files(
    workspace_root: Path,
) -> DatasetVersionQuarantineRecovery:
    root = workspace_root / "workspaces" / "datasets"
    if not root.exists():
        return DatasetVersionQuarantineRecovery(0, 0, 0)
    candidates = list(root.rglob(".delete-d-*.q"))
    candidates.extend(root.rglob(".delete-u-*.q"))
    restored = deleted = pending = 0
    for path in candidates:
        outcome = _recover_quarantine(workspace_root, path)
        if outcome == "restored":
            restored += 1
        elif outcome == "deleted":
            deleted += 1
        else:
            pending += 1
    return DatasetVersionQuarantineRecovery(restored, deleted, pending)


def _deletion_context(settings: Settings, version_id: UUID) -> _DeletionContext:
    snapshot = get_dataset_version_deletion_snapshot(settings.workspace_root, str(version_id))
    if snapshot is None:
        raise ApiError(
            code="dataset_version_not_found",
            message="요청한 데이터셋 버전을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if (
        snapshot.version.source_sha256 != snapshot.dataset.sha256
        or len(snapshot.columns) != snapshot.version.column_count
    ):
        raise _artifact_error("dataset_version_artifact_mismatch")
    required_kinds = {"canonical_rows", "canonical_manifest"}
    artifact_kinds = {artifact.kind for artifact in snapshot.artifacts}
    if not required_kinds.issubset(artifact_kinds):
        raise _artifact_error("dataset_version_artifact_mismatch")

    files: list[_OwnedFile] = []
    seen_paths: set[Path] = set()
    artifact_bytes = 0
    expected_parent = (
        Path("workspaces")
        / "datasets"
        / snapshot.dataset.dataset_id
        / "versions"
        / snapshot.version.version_id
    )
    for artifact in snapshot.artifacts:
        if artifact.version_id != snapshot.version.version_id:
            raise _artifact_error("dataset_version_artifact_mismatch")
        path = _validated_owned_path(
            settings.workspace_root,
            artifact.path,
            expected_parent=expected_parent,
            sha256=artifact.sha256,
            size_bytes=artifact.size_bytes,
        )
        if path in seen_paths:
            raise _artifact_error("dataset_version_path_invalid")
        seen_paths.add(path)
        artifact_bytes += artifact.size_bytes
        files.append(
            _OwnedFile(
                owner_id=artifact.artifact_id,
                kind="artifact",
                path=path,
                relative_path=artifact.path,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
            )
        )

    last_version = snapshot.sibling_version_count == 0
    raw_bytes = 0
    if last_version:
        suffix = Path(snapshot.dataset.safe_filename).suffix.lower()
        if suffix not in {".csv", ".tsv", ".txt", ".xlsx"}:
            suffix = ".upload"
        expected_raw = (
            Path("workspaces")
            / "datasets"
            / snapshot.dataset.dataset_id
            / "raw"
            / f"source{suffix}"
        )
        if snapshot.dataset.stored_path != expected_raw.as_posix():
            raise _artifact_error("dataset_version_path_invalid")
        raw_path = _validated_owned_path(
            settings.workspace_root,
            snapshot.dataset.stored_path,
            expected_parent=expected_raw.parent,
            sha256=snapshot.dataset.sha256,
            size_bytes=snapshot.dataset.size_bytes,
        )
        if raw_path in seen_paths:
            raise _artifact_error("dataset_version_path_invalid")
        raw_bytes = snapshot.dataset.size_bytes
        files.append(
            _OwnedFile(
                owner_id=snapshot.dataset.dataset_id,
                kind="raw_upload",
                path=raw_path,
                relative_path=snapshot.dataset.stored_path,
                sha256=snapshot.dataset.sha256,
                size_bytes=snapshot.dataset.size_bytes,
            )
        )

    dependencies = snapshot.dependencies
    blockers: list[str] = []
    if dependencies.analysis_run_count or dependencies.analysis_export_count:
        blockers.append("dataset_version_deletion_analysis_dependency")
    if dependencies.regression_model_count:
        blockers.append("dataset_version_deletion_regression_model_dependency")
    if dependencies.prediction_source_count or dependencies.prediction_target_count:
        blockers.append("dataset_version_deletion_prediction_dependency")
    if dependencies.attribute_control_limit_set_count or dependencies.phase_2_analysis_count:
        blockers.append("dataset_version_deletion_limit_set_dependency")
    if dependencies.job_count:
        blockers.append("dataset_version_deletion_job_dependency")
    counts = DatasetVersionDeletionCounts(
        dataset_version_count=1,
        dataset_root_count=1 if last_version else 0,
        dataset_column_count=len(snapshot.columns),
        dataset_artifact_count=len(snapshot.artifacts),
        artifact_file_count=len(snapshot.artifacts),
        artifact_file_bytes=artifact_bytes,
        raw_upload_file_count=1 if last_version else 0,
        raw_upload_file_bytes=raw_bytes,
        sibling_version_count=snapshot.sibling_version_count,
        **dependencies.__dict__,
    )
    scope: Literal["version_only", "dataset_root"] = (
        "dataset_root" if last_version else "version_only"
    )
    manifest_payload = {
        "preflight_schema_version": DATASET_VERSION_DELETION_PREFLIGHT_SCHEMA_VERSION,
        "version": snapshot.version.__dict__,
        "dataset": {
            "dataset_id": snapshot.dataset.dataset_id,
            "stored_path": snapshot.dataset.stored_path,
            "sha256": snapshot.dataset.sha256,
            "size_bytes": snapshot.dataset.size_bytes,
        },
        "columns": [column.__dict__ for column in snapshot.columns],
        "artifacts": [artifact.__dict__ for artifact in snapshot.artifacts],
        "user_metadata": None
        if snapshot.user_metadata is None
        else snapshot.user_metadata.__dict__,
        "deletion_scope": scope,
        "blockers": blockers,
        "counts": counts.model_dump(mode="json"),
    }
    return _DeletionContext(
        snapshot=snapshot,
        files=tuple(files),
        blockers=tuple(blockers),
        counts=counts,
        deletion_scope=scope,
        manifest_sha256=hashlib.sha256(canonical_json_bytes(manifest_payload)).hexdigest(),
    )


def _preflight_response(context: _DeletionContext) -> DatasetVersionDeletionPreflightResponse:
    version = context.snapshot.version
    return DatasetVersionDeletionPreflightResponse(
        preflight_schema_version=DATASET_VERSION_DELETION_PREFLIGHT_SCHEMA_VERSION,
        version_id=UUID(version.version_id),
        dataset_id=UUID(version.dataset_id),
        row_count=version.row_count,
        column_count=version.column_count,
        version_number=version.version_number,
        deletion_scope=context.deletion_scope,
        deletion_ready=not context.blockers,
        blockers=list(context.blockers),
        counts=context.counts,
        deletion_manifest_sha256=context.manifest_sha256,
    )


def _validated_owned_path(
    workspace_root: Path,
    relative_value: str,
    *,
    expected_parent: Path,
    sha256: str,
    size_bytes: int,
) -> Path:
    relative = Path(relative_value)
    if relative.is_absolute() or ".." in relative.parts or relative.parent != expected_parent:
        raise _artifact_error("dataset_version_path_invalid")
    root = workspace_root.resolve()
    path = workspace_root / relative
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != root):
        raise _artifact_error("dataset_version_path_invalid")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, ValueError) as exc:
        code = (
            "dataset_version_file_missing" if not path.exists() else "dataset_version_path_invalid"
        )
        raise _artifact_error(code) from exc
    if not resolved.is_file():
        raise _artifact_error("dataset_version_path_invalid")
    if not _file_matches(resolved, sha256, size_bytes):
        raise _artifact_error("dataset_version_artifact_mismatch")
    return resolved


def _file_matches(path: Path, sha256: str, size_bytes: int) -> bool:
    try:
        if not path.is_file() or path.stat().st_size != size_bytes:
            return False
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == sha256
    except OSError:
        return False


def _restore_or_raise(items: list[_QuarantinedFile]) -> None:
    failed = False
    for item in reversed(items):
        if not item.path.exists():
            continue
        try:
            if item.owned.path.exists() or not _file_matches(
                item.path, item.owned.sha256, item.owned.size_bytes
            ):
                failed = True
                continue
            os.replace(item.path, item.owned.path)
        except OSError:
            failed = True
    if failed:
        raise ApiError(
            code="dataset_version_restore_failed",
            message="삭제 중 오류가 발생했고 일부 파일을 원래 위치로 복원하지 못했습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )


def _recover_quarantine(
    workspace_root: Path,
    quarantine: Path,
) -> Literal["restored", "deleted", "pending"]:
    artifact_match = _ARTIFACT_QUARANTINE.fullmatch(quarantine.name)
    raw_match = _RAW_QUARANTINE.fullmatch(quarantine.name)
    if artifact_match is not None:
        artifact_records = list_dataset_artifact_records_by_id_prefix(
            workspace_root, artifact_match.group(1)
        )
        if not artifact_records:
            return _unlink_recovery_file(quarantine)
        if len(artifact_records) != 1:
            return "pending"
        record = artifact_records[0]
        original = workspace_root / Path(record.path)
        if original.parent != quarantine.parent or original.exists():
            return "pending"
        if not _file_matches(quarantine, record.sha256, record.size_bytes):
            return "pending"
        try:
            os.replace(quarantine, original)
            return "restored"
        except OSError:
            return "pending"
    if raw_match is not None:
        dataset_records = list_dataset_records_by_id_prefix(workspace_root, raw_match.group(1))
        if not dataset_records:
            return _unlink_recovery_file(quarantine)
        if len(dataset_records) != 1:
            return "pending"
        dataset_record = dataset_records[0]
        original = workspace_root / Path(dataset_record.stored_path)
        if original.parent != quarantine.parent or original.exists():
            return "pending"
        if not _file_matches(quarantine, dataset_record.sha256, dataset_record.size_bytes):
            return "pending"
        try:
            os.replace(quarantine, original)
            return "restored"
        except OSError:
            return "pending"
    return "pending"


def _unlink_recovery_file(path: Path) -> Literal["deleted", "pending"]:
    try:
        path.unlink(missing_ok=True)
        return "deleted"
    except OSError:
        return "pending"


def _remove_empty_owned_directories(workspace_root: Path, context: _DeletionContext) -> None:
    version_root = (
        workspace_root
        / "workspaces"
        / "datasets"
        / context.snapshot.dataset.dataset_id
        / "versions"
        / context.snapshot.version.version_id
    )
    candidates = sorted(
        {item.path.parent for item in context.files if version_root in item.path.parents},
        key=lambda path: len(path.parts),
        reverse=True,
    )
    candidates.extend([version_root / "p", version_root])
    if context.deletion_scope == "dataset_root":
        dataset_root = version_root.parents[1]
        candidates.extend([dataset_root / "raw", dataset_root / "versions", dataset_root])
    for directory in candidates:
        try:
            directory.rmdir()
        except OSError:
            pass


def _confirmation_error() -> ApiError:
    return ApiError(
        code="dataset_version_deletion_confirmation_mismatch",
        message="데이터셋 버전 삭제 확인 정보가 현재 preflight와 일치하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _artifact_error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="데이터셋 버전 파일의 무결성 또는 소유권을 확인할 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )
