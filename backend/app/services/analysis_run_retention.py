import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.analyses import (
    AnalysisRunDeleteRequest,
    AnalysisRunDeleteResponse,
    AnalysisRunDeletionCounts,
    AnalysisRunDeletionPreflightResponse,
    AnalysisRunState,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    ROW_SNAPSHOT_ARTIFACT_KIND,
    ROW_SNAPSHOT_MEDIA_TYPE,
    analysis_result_relative_path,
    canonical_json_bytes,
    row_snapshot_relative_path,
    utc_now,
)
from app.services.analysis_run_exports import (
    ANALYSIS_RESULT_EXPORT_DOWNLOAD_KINDS,
    analysis_export_expected_media_type,
    analysis_export_expected_relative_path,
)
from app.services.analysis_run_results import load_analysis_run_result
from app.services.regression_models import (
    REGRESSION_PREDICTION_METHOD_ID,
    REGRESSION_PREDICTION_ROWS_ARTIFACT_KIND,
    REGRESSION_PREDICTION_ROWS_MEDIA_TYPE,
    validate_regression_prediction_consistency,
)
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    AnalysisRunStorageConflict,
    RegressionModelRecord,
    count_job_records_by_analysis,
    count_regression_prediction_records_by_source,
    delete_analysis_run_record,
    get_analysis_artifact_record,
    get_analysis_run_record,
    get_attribute_control_limit_set_record_by_source_analysis,
    get_regression_model_record_by_analysis,
    list_analysis_artifact_records,
)

ANALYSIS_RUN_DELETION_PREFLIGHT_SCHEMA_VERSION: Literal[1] = 1
ANALYSIS_RUN_DELETION_SCHEMA_VERSION: Literal[1] = 1
REGRESSION_MODEL_ARTIFACT_KIND = "regression_model_manifest"
REGRESSION_MODEL_MEDIA_TYPE = "application/json"
_RESULT_QUARANTINE_PATTERN = re.compile(r"^\.delete-r-([0-9a-f]{16})\.q$")
_ARTIFACT_QUARANTINE_PATTERN = re.compile(r"^\.delete-a-([0-9a-fA-F-]{36})-([0-9a-f]{16})\.q$")


@dataclass(frozen=True)
class AnalysisRunQuarantineRecovery:
    restored_file_count: int
    deleted_file_count: int
    pending_file_count: int


@dataclass(frozen=True)
class _OwnedFile:
    key: str
    kind: str
    path: Path
    sha256: str
    size_bytes: int
    artifact_id: str | None


@dataclass(frozen=True)
class _AnalysisRunDeletionContext:
    run: AnalysisRunRecord
    artifacts: list[AnalysisArtifactRecord]
    files: list[_OwnedFile]
    blockers: list[str]
    counts: AnalysisRunDeletionCounts
    deletion_manifest_sha256: str


def get_analysis_run_deletion_preflight(
    settings: Settings,
    analysis_id: UUID,
) -> AnalysisRunDeletionPreflightResponse:
    return _preflight_response(_deletion_context(settings, analysis_id))


def delete_stored_analysis_run(
    settings: Settings,
    analysis_id: UUID,
    body: AnalysisRunDeleteRequest,
) -> AnalysisRunDeleteResponse:
    if body.confirmation_analysis_id != analysis_id:
        raise _confirmation_error()
    context = _deletion_context(settings, analysis_id)
    preflight = _preflight_response(context)
    if not preflight.deletion_ready:
        raise ApiError(
            code="analysis_run_deletion_blocked",
            message="참조 중이거나 지원 범위를 벗어난 분석 실행은 삭제할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=",".join(preflight.blockers),
        )
    if body.expected_deletion_manifest_sha256 != preflight.deletion_manifest_sha256:
        raise _confirmation_error()

    moved: list[tuple[_OwnedFile, Path]] = []
    try:
        for owned_file in context.files:
            quarantine_path = _quarantine_path(analysis_id, owned_file)
            try:
                os.replace(owned_file.path, quarantine_path)
            except OSError as exc:
                raise ApiError(
                    code="analysis_run_quarantine_failed",
                    message="분석 파일을 안전한 삭제 대기 상태로 옮길 수 없습니다.",
                    status_code=status.HTTP_409_CONFLICT,
                ) from exc
            moved.append((owned_file, quarantine_path))
            if not _file_matches(quarantine_path, owned_file.sha256, owned_file.size_bytes):
                raise ApiError(
                    code="analysis_run_deletion_conflict",
                    message="삭제 확인 이후 분석 파일이 변경되었습니다.",
                    status_code=status.HTTP_409_CONFLICT,
                )

        delete_analysis_run_record(
            settings.workspace_root,
            expected_run=context.run,
            expected_artifacts=context.artifacts,
        )
    except AnalysisRunStorageConflict as exc:
        _restore_moved_files(moved)
        code = (
            "analysis_run_not_found"
            if exc.code == "analysis_run_not_found"
            else "analysis_run_deletion_conflict"
        )
        raise ApiError(
            code=code,
            message="삭제 확인 이후 분석 실행의 소유 관계가 변경되었습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    except Exception:
        _restore_moved_files(moved)
        raise

    cleanup_status: Literal["deleted", "quarantined_pending_cleanup"] = "deleted"
    for _, quarantine_path in moved:
        try:
            quarantine_path.unlink()
        except OSError:
            cleanup_status = "quarantined_pending_cleanup"
    return AnalysisRunDeleteResponse(
        deletion_schema_version=ANALYSIS_RUN_DELETION_SCHEMA_VERSION,
        analysis_id=analysis_id,
        deletion_manifest_sha256=preflight.deletion_manifest_sha256,
        deleted_at=utc_now(),
        deleted_counts=preflight.counts,
        cleanup_status=cleanup_status,
    )


def recover_analysis_run_quarantine_files(
    workspace_root: Path,
) -> AnalysisRunQuarantineRecovery:
    analyses_root = workspace_root / "workspaces" / "analyses"
    if not analyses_root.exists():
        return AnalysisRunQuarantineRecovery(0, 0, 0)
    restored = 0
    deleted = 0
    pending = 0
    candidates = list(analyses_root.glob("*/.delete-r-*.q"))
    candidates.extend(analyses_root.glob("*/.delete-a-*.q"))
    candidates.extend(analyses_root.glob("*/exports/.delete-a-*.q"))
    for quarantine_path in candidates:
        outcome = _recover_quarantine_file(workspace_root, quarantine_path)
        if outcome == "restored":
            restored += 1
        elif outcome == "deleted":
            deleted += 1
        else:
            pending += 1
    return AnalysisRunQuarantineRecovery(restored, deleted, pending)


def _deletion_context(
    settings: Settings,
    analysis_id: UUID,
) -> _AnalysisRunDeletionContext:
    run = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if run is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    artifacts = list_analysis_artifact_records(settings.workspace_root, str(analysis_id))
    regression_model = get_regression_model_record_by_analysis(
        settings.workspace_root, str(analysis_id)
    )
    limit_set = get_attribute_control_limit_set_record_by_source_analysis(
        settings.workspace_root, str(analysis_id)
    )
    job_count = count_job_records_by_analysis(settings.workspace_root, str(analysis_id))
    prediction_count = count_regression_prediction_records_by_source(
        settings.workspace_root,
        source_analysis_id=str(analysis_id),
        model_id=None if regression_model is None else regression_model.model_id,
    )
    blockers: list[str] = []
    if run.status != AnalysisRunState.SUCCEEDED.value:
        blockers.append("analysis_run_deletion_status_unsupported")
    if run.result_path is None or run.result_sha256 is None:
        blockers.append("analysis_run_deletion_result_unavailable")
    if regression_model is not None:
        blockers.append("analysis_run_deletion_regression_model_dependency")
    if prediction_count > 0:
        blockers.append("analysis_run_deletion_regression_prediction_dependency")
    if limit_set is not None:
        blockers.append("analysis_run_deletion_limit_set_dependency")
    if job_count > 0:
        blockers.append("analysis_run_deletion_job_dependency")

    files = _validated_owned_files(settings, run, artifacts, regression_model)
    export_count = sum(
        artifact.kind in ANALYSIS_RESULT_EXPORT_DOWNLOAD_KINDS for artifact in artifacts
    )
    counts = AnalysisRunDeletionCounts(
        analysis_run_count=1,
        analysis_artifact_count=len(artifacts),
        result_file_count=sum(item.artifact_id is None for item in files),
        artifact_file_count=len(artifacts),
        export_file_count=export_count,
        total_file_count=len(files),
        file_bytes=sum(item.size_bytes for item in files),
        metadata_record_count=1 + len(artifacts),
        regression_model_count=1 if regression_model is not None else 0,
        regression_prediction_count=prediction_count,
        attribute_control_limit_set_count=1 if limit_set is not None else 0,
        job_reference_count=job_count,
    )
    manifest = {
        "preflight_schema_version": ANALYSIS_RUN_DELETION_PREFLIGHT_SCHEMA_VERSION,
        "analysis_id": str(analysis_id),
        "method_id": run.method_id,
        "method_version": run.method_version,
        "dataset_version_id": run.dataset_version_id,
        "config_sha256": hashlib.sha256(run.config_json.encode("utf-8")).hexdigest(),
        "status": run.status,
        "stale": run.stale,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "completed_at": run.completed_at,
        "app_version": run.app_version,
        "blockers": blockers,
        "counts": counts.model_dump(mode="json"),
        "files": [
            {
                "key": item.key,
                "kind": item.kind,
                "relative_path": item.path.relative_to(settings.workspace_root).as_posix(),
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "artifact_id": item.artifact_id,
            }
            for item in files
        ],
        "artifacts": [
            {
                "artifact_id": artifact.artifact_id,
                "kind": artifact.kind,
                "path": artifact.path,
                "sha256": artifact.sha256,
                "media_type": artifact.media_type,
                "created_at": artifact.created_at,
            }
            for artifact in artifacts
        ],
    }
    return _AnalysisRunDeletionContext(
        run=run,
        artifacts=artifacts,
        files=files,
        blockers=blockers,
        counts=counts,
        deletion_manifest_sha256=hashlib.sha256(canonical_json_bytes(manifest)).hexdigest(),
    )


def _validated_owned_files(
    settings: Settings,
    run: AnalysisRunRecord,
    artifacts: list[AnalysisArtifactRecord],
    regression_model: RegressionModelRecord | None,
) -> list[_OwnedFile]:
    files: list[_OwnedFile] = []
    if run.result_path is not None and run.result_sha256 is not None:
        expected_result = analysis_result_relative_path(run.analysis_id)
        result_path = _exact_workspace_path(
            settings.workspace_root,
            run.result_path,
            expected_result,
            "analysis_run_result_path_invalid",
        )
        files.append(
            _validated_file(
                key="result",
                kind="analysis_result",
                path=result_path,
                sha256=run.result_sha256,
                artifact_id=None,
            )
        )
        stored = load_analysis_run_result(settings, UUID(run.analysis_id))
        envelope = stored.envelope
        if not (
            str(envelope.analysis_id) == run.analysis_id
            and envelope.method_id == run.method_id
            and envelope.method_version == run.method_version
            and (None if envelope.dataset_version_id is None else str(envelope.dataset_version_id))
            == run.dataset_version_id
            and envelope.status == run.status
        ):
            raise _artifact_error("analysis_run_result_metadata_mismatch")

    paths = {item.path for item in files}
    for artifact in artifacts:
        expected_path, expected_media_type = _expected_artifact_contract(
            run, artifact, regression_model
        )
        if artifact.media_type != expected_media_type:
            raise _artifact_error("analysis_run_artifact_metadata_invalid")
        artifact_path = _exact_workspace_path(
            settings.workspace_root,
            artifact.path,
            expected_path,
            "analysis_run_artifact_path_invalid",
        )
        if artifact_path in paths:
            raise _artifact_error("analysis_run_artifact_path_invalid")
        paths.add(artifact_path)
        files.append(
            _validated_file(
                key=f"artifact:{artifact.artifact_id}",
                kind=artifact.kind,
                path=artifact_path,
                sha256=artifact.sha256,
                artifact_id=artifact.artifact_id,
            )
        )
    if run.status == AnalysisRunState.SUCCEEDED.value:
        if run.method_id == REGRESSION_PREDICTION_METHOD_ID:
            validate_regression_prediction_consistency(
                settings, UUID(run.analysis_id), verify_rows=True
            )
        else:
            _validate_row_snapshot_relation(run, artifacts)
    return files


def _expected_artifact_contract(
    run: AnalysisRunRecord,
    artifact: AnalysisArtifactRecord,
    regression_model: RegressionModelRecord | None,
) -> tuple[Path, str]:
    if artifact.kind == ROW_SNAPSHOT_ARTIFACT_KIND:
        return row_snapshot_relative_path(run.analysis_id), ROW_SNAPSHOT_MEDIA_TYPE
    if artifact.kind == REGRESSION_PREDICTION_ROWS_ARTIFACT_KIND:
        if run.method_id != REGRESSION_PREDICTION_METHOD_ID:
            raise _artifact_error("analysis_run_artifact_metadata_invalid")
        return (
            Path("workspaces") / "analyses" / run.analysis_id / "prediction_rows.jsonl",
            REGRESSION_PREDICTION_ROWS_MEDIA_TYPE,
        )
    if artifact.kind == REGRESSION_MODEL_ARTIFACT_KIND:
        if regression_model is None or regression_model.analysis_id != run.analysis_id:
            raise _artifact_error("analysis_run_artifact_metadata_invalid")
        expected = (
            Path("workspaces")
            / "analyses"
            / run.analysis_id
            / f"model-{regression_model.model_id}.json"
        )
        if (
            artifact.path != regression_model.manifest_path
            or artifact.sha256 != regression_model.manifest_sha256
        ):
            raise _artifact_error("analysis_run_artifact_metadata_invalid")
        return expected, REGRESSION_MODEL_MEDIA_TYPE
    if artifact.kind in ANALYSIS_RESULT_EXPORT_DOWNLOAD_KINDS:
        try:
            export_id = str(UUID(artifact.artifact_id))
            return (
                analysis_export_expected_relative_path(run.analysis_id, export_id, artifact.kind),
                analysis_export_expected_media_type(artifact.kind),
            )
        except (ValueError, ApiError) as exc:
            raise _artifact_error("analysis_run_artifact_metadata_invalid") from exc
    raise _artifact_error("analysis_run_artifact_kind_unsupported")


def _validate_row_snapshot_relation(
    run: AnalysisRunRecord,
    artifacts: list[AnalysisArtifactRecord],
) -> None:
    snapshots = [item for item in artifacts if item.kind == ROW_SNAPSHOT_ARTIFACT_KIND]
    if len(snapshots) != 1:
        raise _artifact_error("analysis_run_row_snapshot_mismatch")
    try:
        config = json.loads(run.config_json)
    except json.JSONDecodeError as exc:
        raise _artifact_error("analysis_run_metadata_invalid") from exc
    if not isinstance(config, dict) or not isinstance(config.get("row_snapshot"), dict):
        raise _artifact_error("analysis_run_row_snapshot_mismatch")
    snapshot = snapshots[0]
    stored = config["row_snapshot"]
    if not (
        stored.get("artifact_id") == snapshot.artifact_id
        and stored.get("kind") == snapshot.kind
        and stored.get("path") == snapshot.path
        and stored.get("sha256") == snapshot.sha256
        and stored.get("media_type") == snapshot.media_type
    ):
        raise _artifact_error("analysis_run_row_snapshot_mismatch")


def _validated_file(
    *,
    key: str,
    kind: str,
    path: Path,
    sha256: str,
    artifact_id: str | None,
) -> _OwnedFile:
    try:
        if path.is_symlink():
            raise _artifact_error("analysis_run_artifact_path_invalid")
        if not path.exists() or not path.is_file():
            raise _artifact_error("analysis_run_file_missing")
        size_bytes = path.stat().st_size
        if _file_sha256(path) != sha256:
            raise _artifact_error("analysis_run_file_checksum_mismatch")
    except OSError as exc:
        raise _artifact_error("analysis_run_file_unavailable") from exc
    return _OwnedFile(key, kind, path, sha256, size_bytes, artifact_id)


def _exact_workspace_path(
    workspace_root: Path,
    stored_path: str,
    expected_path: Path,
    code: str,
) -> Path:
    relative_path = Path(stored_path)
    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.as_posix() != expected_path.as_posix()
    ):
        raise _artifact_error(code)
    return workspace_root / relative_path


def _preflight_response(
    context: _AnalysisRunDeletionContext,
) -> AnalysisRunDeletionPreflightResponse:
    return AnalysisRunDeletionPreflightResponse(
        preflight_schema_version=ANALYSIS_RUN_DELETION_PREFLIGHT_SCHEMA_VERSION,
        analysis_id=UUID(context.run.analysis_id),
        method_id=context.run.method_id,
        method_version=context.run.method_version,
        status=AnalysisRunState(context.run.status),
        stale=context.run.stale,
        deletion_ready=not context.blockers,
        blockers=context.blockers,
        counts=context.counts,
        deletion_manifest_sha256=context.deletion_manifest_sha256,
    )


def _quarantine_path(analysis_id: UUID, owned_file: _OwnedFile) -> Path:
    del analysis_id
    nonce = uuid4().hex[:16]
    if owned_file.artifact_id is None:
        return owned_file.path.with_name(f".delete-r-{nonce}.q")
    return owned_file.path.with_name(f".delete-a-{owned_file.artifact_id}-{nonce}.q")


def _restore_moved_files(moved: list[tuple[_OwnedFile, Path]]) -> None:
    failed = False
    for owned_file, quarantine_path in reversed(moved):
        if owned_file.path.exists():
            failed = True
            continue
        try:
            os.replace(quarantine_path, owned_file.path)
        except OSError:
            failed = True
    if failed:
        raise ApiError(
            code="analysis_run_restore_failed",
            message="삭제 실패 후 분석 파일을 안전하게 원위치로 복구하지 못했습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )


def _recover_quarantine_file(
    workspace_root: Path,
    quarantine_path: Path,
) -> Literal["restored", "deleted", "pending"]:
    if quarantine_path.is_symlink() or not quarantine_path.is_file():
        return "pending"
    analysis_dir = (
        quarantine_path.parent.parent
        if quarantine_path.parent.name == "exports"
        else quarantine_path.parent
    )
    try:
        analysis_id = UUID(analysis_dir.name)
    except ValueError:
        return "pending"
    result_match = _RESULT_QUARANTINE_PATTERN.fullmatch(quarantine_path.name)
    artifact_match = _ARTIFACT_QUARANTINE_PATTERN.fullmatch(quarantine_path.name)
    if result_match is None and artifact_match is None:
        return "pending"
    run = get_analysis_run_record(workspace_root, str(analysis_id))
    if run is None:
        try:
            quarantine_path.unlink()
            return "deleted"
        except OSError:
            return "pending"

    if result_match is not None:
        if run.result_sha256 is None:
            return "pending"
        expected = analysis_result_relative_path(str(analysis_id))
        if run.result_path != expected.as_posix():
            return "pending"
        original_path = workspace_root / expected
        expected_sha256 = run.result_sha256
    elif artifact_match is not None:
        artifact_id = artifact_match.group(1)
        artifact = get_analysis_artifact_record(workspace_root, str(analysis_id), artifact_id)
        if artifact is None:
            return "pending"
        model = get_regression_model_record_by_analysis(workspace_root, str(analysis_id))
        try:
            expected, expected_media_type = _expected_artifact_contract(run, artifact, model)
        except ApiError:
            return "pending"
        if artifact.path != expected.as_posix() or artifact.media_type != expected_media_type:
            return "pending"
        original_path = workspace_root / expected
        expected_sha256 = artifact.sha256
    else:
        return "pending"
    try:
        if original_path.exists() or _file_sha256(quarantine_path) != expected_sha256:
            return "pending"
    except OSError:
        return "pending"
    try:
        os.replace(quarantine_path, original_path)
        return "restored"
    except OSError:
        return "pending"


def _file_matches(path: Path, sha256: str, size_bytes: int) -> bool:
    try:
        return (
            not path.is_symlink()
            and path.is_file()
            and path.stat().st_size == size_bytes
            and _file_sha256(path) == sha256
        )
    except OSError:
        return False


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _confirmation_error() -> ApiError:
    return ApiError(
        code="analysis_run_deletion_confirmation_mismatch",
        message="분석 실행 삭제 확인 대상 또는 영향 정보가 변경되었습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _artifact_error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="저장된 분석 실행의 파일 소유 관계를 안전하게 검증할 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )
