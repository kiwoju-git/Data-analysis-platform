import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.analyses import (
    RegressionModelDeleteRequest,
    RegressionModelDeleteResponse,
    RegressionModelDeletionCounts,
    RegressionModelDeletionPreflightResponse,
)
from app.api.v1.schemas.quality import (
    AttributeControlLimitSetDeleteRequest,
    AttributeControlLimitSetDeleteResponse,
    AttributeControlLimitSetDeletionCounts,
    AttributeControlLimitSetDeletionPreflightResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import canonical_json_bytes, utc_now
from app.services.analysis_run_results import load_analysis_run_result_base
from app.services.attribute_control_limit_sets import (
    validate_attribute_control_limit_set_for_retention,
)
from app.services.regression_models import get_regression_model_manifest
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    AttributeControlLimitSetRecord,
    RegressionModelRecord,
    WorkspaceAssetStorageConflict,
    count_attribute_control_phase_2_records_by_limit_set,
    count_regression_prediction_records_by_source,
    delete_attribute_control_limit_set_record,
    delete_regression_model_record,
    get_analysis_run_record,
    get_attribute_control_limit_set_record,
    get_regression_model_record,
    list_analysis_artifact_records,
)

REGRESSION_MODEL_DELETION_PREFLIGHT_SCHEMA_VERSION: Literal[1] = 1
REGRESSION_MODEL_DELETION_SCHEMA_VERSION: Literal[1] = 1
ATTRIBUTE_CONTROL_LIMIT_SET_DELETION_PREFLIGHT_SCHEMA_VERSION: Literal[1] = 1
ATTRIBUTE_CONTROL_LIMIT_SET_DELETION_SCHEMA_VERSION: Literal[1] = 1
_MODEL_ARTIFACT_KIND = "regression_model_manifest"
_MODEL_MEDIA_TYPE = "application/json"
_MODEL_QUARANTINE_PATTERN = re.compile(r"^\.delete-m-([0-9a-fA-F-]{36})-([0-9a-f]{16})\.q$")
_LIMIT_SET_QUARANTINE_PATTERN = re.compile(r"^\.delete-l-([0-9a-fA-F-]{36})-([0-9a-f]{16})\.q$")


@dataclass(frozen=True)
class WorkspaceAssetQuarantineRecovery:
    restored_file_count: int
    deleted_file_count: int
    pending_file_count: int


@dataclass(frozen=True)
class _RegressionModelDeletionContext:
    model: RegressionModelRecord
    source_run: AnalysisRunRecord
    artifact: AnalysisArtifactRecord
    path: Path
    size_bytes: int
    blockers: list[str]
    counts: RegressionModelDeletionCounts
    deletion_manifest_sha256: str


@dataclass(frozen=True)
class _LimitSetDeletionContext:
    limit_set: AttributeControlLimitSetRecord
    source_run: AnalysisRunRecord
    path: Path
    size_bytes: int
    blockers: list[str]
    counts: AttributeControlLimitSetDeletionCounts
    deletion_manifest_sha256: str


def get_regression_model_deletion_preflight(
    settings: Settings,
    model_id: UUID,
) -> RegressionModelDeletionPreflightResponse:
    return _regression_model_preflight_response(_regression_model_context(settings, model_id))


def delete_stored_regression_model(
    settings: Settings,
    model_id: UUID,
    body: RegressionModelDeleteRequest,
) -> RegressionModelDeleteResponse:
    if body.confirmation_model_id != model_id:
        raise _model_confirmation_error()
    context = _regression_model_context(settings, model_id)
    preflight = _regression_model_preflight_response(context)
    if not preflight.deletion_ready:
        raise ApiError(
            code="regression_model_deletion_blocked",
            message="이 회귀 모델을 사용하는 예측 결과가 있어 삭제할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=",".join(preflight.blockers),
        )
    if body.expected_deletion_manifest_sha256 != preflight.deletion_manifest_sha256:
        raise _model_confirmation_error()
    quarantine = context.path.with_name(f".delete-m-{context.model.model_id}-{uuid4().hex[:16]}.q")
    try:
        os.replace(context.path, quarantine)
        if not _file_matches(quarantine, context.model.manifest_sha256, context.size_bytes):
            raise _model_conflict()
        delete_regression_model_record(
            settings.workspace_root,
            expected_model=context.model,
            expected_source_run=context.source_run,
            expected_artifact=context.artifact,
        )
    except WorkspaceAssetStorageConflict as exc:
        _restore_file(quarantine, context.path)
        code = (
            "regression_model_deletion_blocked"
            if exc.code == "regression_model_deletion_blocked"
            else "regression_model_deletion_conflict"
        )
        raise ApiError(
            code=code,
            message="삭제 확인 후 회귀 모델의 참조 관계가 변경되었습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    except OSError as exc:
        _restore_file(quarantine, context.path)
        raise ApiError(
            code="regression_model_quarantine_failed",
            message="회귀 모델 파일을 안전한 삭제 대기 상태로 옮길 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    except Exception:
        _restore_file(quarantine, context.path)
        raise
    cleanup_status = _cleanup_quarantine(quarantine)
    return RegressionModelDeleteResponse(
        deletion_schema_version=REGRESSION_MODEL_DELETION_SCHEMA_VERSION,
        model_id=model_id,
        source_analysis_id=UUID(context.model.analysis_id),
        deletion_manifest_sha256=preflight.deletion_manifest_sha256,
        deleted_at=utc_now(),
        deleted_counts=preflight.counts,
        cleanup_status=cleanup_status,
    )


def get_attribute_control_limit_set_deletion_preflight(
    settings: Settings,
    limit_set_id: UUID,
) -> AttributeControlLimitSetDeletionPreflightResponse:
    return _limit_set_preflight_response(_limit_set_context(settings, limit_set_id))


def delete_stored_attribute_control_limit_set(
    settings: Settings,
    limit_set_id: UUID,
    body: AttributeControlLimitSetDeleteRequest,
) -> AttributeControlLimitSetDeleteResponse:
    if body.confirmation_limit_set_id != limit_set_id:
        raise _limit_set_confirmation_error()
    context = _limit_set_context(settings, limit_set_id)
    preflight = _limit_set_preflight_response(context)
    if not preflight.deletion_ready:
        raise ApiError(
            code="attribute_control_limit_set_deletion_blocked",
            message="이 관리한계 세트를 사용하는 Phase II 분석이 있어 삭제할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=",".join(preflight.blockers),
        )
    if body.expected_deletion_manifest_sha256 != preflight.deletion_manifest_sha256:
        raise _limit_set_confirmation_error()
    quarantine = context.path.with_name(
        f".delete-l-{context.limit_set.limit_set_id}-{uuid4().hex[:16]}.q"
    )
    try:
        os.replace(context.path, quarantine)
        if not _file_matches(quarantine, context.limit_set.asset_sha256, context.size_bytes):
            raise _limit_set_conflict()
        delete_attribute_control_limit_set_record(
            settings.workspace_root,
            expected_limit_set=context.limit_set,
            expected_source_run=context.source_run,
        )
    except WorkspaceAssetStorageConflict as exc:
        _restore_file(quarantine, context.path)
        code = (
            "attribute_control_limit_set_deletion_blocked"
            if exc.code == "attribute_control_limit_set_deletion_blocked"
            else "attribute_control_limit_set_deletion_conflict"
        )
        raise ApiError(
            code=code,
            message="삭제 확인 후 관리한계 세트의 참조 관계가 변경되었습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    except OSError as exc:
        _restore_file(quarantine, context.path)
        raise ApiError(
            code="attribute_control_limit_set_quarantine_failed",
            message="관리한계 세트 파일을 안전한 삭제 대기 상태로 옮길 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    except Exception:
        _restore_file(quarantine, context.path)
        raise
    cleanup_status = _cleanup_quarantine(quarantine)
    return AttributeControlLimitSetDeleteResponse(
        deletion_schema_version=ATTRIBUTE_CONTROL_LIMIT_SET_DELETION_SCHEMA_VERSION,
        limit_set_id=limit_set_id,
        source_analysis_id=UUID(context.limit_set.source_analysis_id),
        deletion_manifest_sha256=preflight.deletion_manifest_sha256,
        deleted_at=utc_now(),
        deleted_counts=preflight.counts,
        cleanup_status=cleanup_status,
    )


def recover_workspace_asset_quarantine_files(
    workspace_root: Path,
) -> WorkspaceAssetQuarantineRecovery:
    candidates = list((workspace_root / "workspaces" / "analyses").glob("*/.delete-m-*.q"))
    candidates.extend(
        (workspace_root / "artifacts" / "attribute-control-limit-sets").glob("*/.delete-l-*.q")
    )
    restored = deleted = pending = 0
    for path in candidates:
        outcome = _recover_model_quarantine(workspace_root, path)
        if outcome == "pending":
            outcome = _recover_limit_set_quarantine(workspace_root, path)
        if outcome == "restored":
            restored += 1
        elif outcome == "deleted":
            deleted += 1
        else:
            pending += 1
    return WorkspaceAssetQuarantineRecovery(restored, deleted, pending)


def _regression_model_context(
    settings: Settings,
    model_id: UUID,
) -> _RegressionModelDeletionContext:
    record = get_regression_model_record(settings.workspace_root, str(model_id))
    if record is None:
        raise ApiError(
            code="regression_model_not_found",
            message="요청한 회귀 모델을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    source_run = get_analysis_run_record(settings.workspace_root, record.analysis_id)
    if (
        source_run is None
        or source_run.method_id != "regression.linear_model"
        or source_run.method_version != record.method_version
        or source_run.dataset_version_id != record.dataset_version_id
        or source_run.status != "succeeded"
    ):
        raise _model_artifact_error("regression_model_source_analysis_invalid")
    artifacts = [
        item
        for item in list_analysis_artifact_records(settings.workspace_root, record.analysis_id)
        if item.kind == _MODEL_ARTIFACT_KIND
    ]
    if len(artifacts) != 1:
        raise _model_artifact_error("regression_model_artifact_mismatch")
    artifact = artifacts[0]
    expected_relative = (
        Path("workspaces") / "analyses" / record.analysis_id / f"model-{record.model_id}.json"
    )
    if not (
        artifact.analysis_id == record.analysis_id
        and artifact.path == record.manifest_path == expected_relative.as_posix()
        and artifact.sha256 == record.manifest_sha256
        and artifact.media_type == _MODEL_MEDIA_TYPE
    ):
        raise _model_artifact_error("regression_model_artifact_mismatch")
    stored = load_analysis_run_result_base(settings, UUID(record.analysis_id))
    result = stored.envelope.result
    result_model = result.get("model_manifest") if isinstance(result, dict) else None
    if not (
        isinstance(result_model, dict)
        and result_model.get("model_id") == record.model_id
        and result_model.get("manifest_sha256") == record.manifest_sha256
        and stored.envelope.method_id == record.method_id
        and stored.envelope.method_version == record.method_version
    ):
        raise _model_artifact_error("regression_model_source_result_mismatch")
    response = get_regression_model_manifest(settings, model_id)
    manifest = response.manifest
    if not (
        str(response.analysis_id) == record.analysis_id
        and str(response.dataset_version_id) == record.dataset_version_id
        and response.method_id == record.method_id == "regression.linear_model"
        and response.method_version == record.method_version
        and response.schema_hash == record.schema_hash
        and manifest.get("model_id") == record.model_id
        and manifest.get("analysis_id") == record.analysis_id
        and manifest.get("dataset_version_id") == record.dataset_version_id
        and manifest.get("method_id") == record.method_id
        and manifest.get("method_version") == record.method_version
        and manifest.get("source_schema_hash") == record.schema_hash
    ):
        raise _model_artifact_error("regression_model_artifact_mismatch")
    path, size_bytes = _validated_file(
        settings.workspace_root,
        record.manifest_path,
        expected_relative,
        record.manifest_sha256,
        "regression_model_artifact_mismatch",
    )
    dependent_count = count_regression_prediction_records_by_source(
        settings.workspace_root,
        source_analysis_id=record.analysis_id,
        model_id=record.model_id,
    )
    blockers = ["regression_model_deletion_prediction_dependency"] if dependent_count else []
    counts = RegressionModelDeletionCounts(
        regression_model_count=1,
        manifest_artifact_count=1,
        manifest_file_count=1,
        manifest_file_bytes=size_bytes,
        metadata_record_count=2,
        dependent_prediction_count=dependent_count,
    )
    manifest_payload = {
        "preflight_schema_version": REGRESSION_MODEL_DELETION_PREFLIGHT_SCHEMA_VERSION,
        "model": record.__dict__,
        "source_run": source_run.__dict__,
        "artifact": artifact.__dict__,
        "blockers": blockers,
        "counts": counts.model_dump(mode="json"),
        "file": {
            "relative_path": record.manifest_path,
            "sha256": record.manifest_sha256,
            "size_bytes": size_bytes,
        },
    }
    return _RegressionModelDeletionContext(
        record,
        source_run,
        artifact,
        path,
        size_bytes,
        blockers,
        counts,
        hashlib.sha256(canonical_json_bytes(manifest_payload)).hexdigest(),
    )


def _limit_set_context(settings: Settings, limit_set_id: UUID) -> _LimitSetDeletionContext:
    record = get_attribute_control_limit_set_record(settings.workspace_root, str(limit_set_id))
    if record is None:
        raise ApiError(
            code="attribute_control_chart_limit_set_missing",
            message="요청한 관리한계 세트를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    source_run = get_analysis_run_record(settings.workspace_root, record.source_analysis_id)
    if source_run is None:
        raise _limit_set_conflict()
    response = validate_attribute_control_limit_set_for_retention(settings, record)
    if (
        str(response.source_analysis_id) != source_run.analysis_id
        or response.asset_sha256 != record.asset_sha256
    ):
        raise _limit_set_conflict()
    expected_relative = (
        Path("artifacts") / "attribute-control-limit-sets" / record.limit_set_id / "limit-set.json"
    )
    path, size_bytes = _validated_file(
        settings.workspace_root,
        record.asset_path,
        expected_relative,
        record.asset_sha256,
        "attribute_control_limit_set_artifact_mismatch",
    )
    dependent_count = count_attribute_control_phase_2_records_by_limit_set(
        settings.workspace_root, record.limit_set_id
    )
    blockers = (
        ["attribute_control_limit_set_deletion_phase_2_dependency"] if dependent_count else []
    )
    counts = AttributeControlLimitSetDeletionCounts(
        limit_set_count=1,
        asset_file_count=1,
        asset_file_bytes=size_bytes,
        metadata_record_count=1,
        dependent_phase_2_analysis_count=dependent_count,
    )
    manifest_payload = {
        "preflight_schema_version": (ATTRIBUTE_CONTROL_LIMIT_SET_DELETION_PREFLIGHT_SCHEMA_VERSION),
        "limit_set": record.__dict__,
        "source_run": source_run.__dict__,
        "blockers": blockers,
        "counts": counts.model_dump(mode="json"),
        "file": {
            "relative_path": record.asset_path,
            "sha256": record.asset_sha256,
            "size_bytes": size_bytes,
        },
    }
    return _LimitSetDeletionContext(
        record,
        source_run,
        path,
        size_bytes,
        blockers,
        counts,
        hashlib.sha256(canonical_json_bytes(manifest_payload)).hexdigest(),
    )


def _regression_model_preflight_response(
    context: _RegressionModelDeletionContext,
) -> RegressionModelDeletionPreflightResponse:
    return RegressionModelDeletionPreflightResponse(
        preflight_schema_version=REGRESSION_MODEL_DELETION_PREFLIGHT_SCHEMA_VERSION,
        model_id=UUID(context.model.model_id),
        source_analysis_id=UUID(context.model.analysis_id),
        method_id=cast(Literal["regression.linear_model"], context.model.method_id),
        method_version=context.model.method_version,
        deletion_ready=not context.blockers,
        blockers=context.blockers,
        counts=context.counts,
        deletion_manifest_sha256=context.deletion_manifest_sha256,
    )


def _limit_set_preflight_response(
    context: _LimitSetDeletionContext,
) -> AttributeControlLimitSetDeletionPreflightResponse:
    return AttributeControlLimitSetDeletionPreflightResponse(
        preflight_schema_version=ATTRIBUTE_CONTROL_LIMIT_SET_DELETION_PREFLIGHT_SCHEMA_VERSION,
        limit_set_id=UUID(context.limit_set.limit_set_id),
        source_analysis_id=UUID(context.limit_set.source_analysis_id),
        method_id="quality.attribute_control_chart",
        source_method_version=cast(
            Literal["0.1.0", "0.2.0"], context.limit_set.source_method_version
        ),
        deletion_ready=not context.blockers,
        blockers=context.blockers,
        counts=context.counts,
        deletion_manifest_sha256=context.deletion_manifest_sha256,
    )


def _validated_file(
    workspace_root: Path,
    stored_path: str,
    expected_relative: Path,
    expected_sha256: str,
    code: str,
) -> tuple[Path, int]:
    relative = Path(stored_path)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.as_posix() != expected_relative.as_posix()
    ):
        raise ApiError(code=code, message="저장 자산 경로가 유효하지 않습니다.", status_code=409)
    path = workspace_root / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise _file_error(code)
        size_bytes = path.stat().st_size
        if not _file_matches(path, expected_sha256, size_bytes):
            raise _file_error(code)
    except OSError as exc:
        raise _file_error(code) from exc
    return path, size_bytes


def _file_matches(path: Path, sha256: str, size_bytes: int) -> bool:
    try:
        return (
            path.is_file()
            and not path.is_symlink()
            and path.stat().st_size == size_bytes
            and _file_sha256(path) == sha256
        )
    except OSError:
        return False


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _restore_file(quarantine: Path, original: Path) -> None:
    try:
        if quarantine.exists() and not original.exists():
            os.replace(quarantine, original)
    except OSError:
        return


def _cleanup_quarantine(
    quarantine: Path,
) -> Literal["deleted", "quarantined_pending_cleanup"]:
    try:
        quarantine.unlink()
        return "deleted"
    except OSError:
        return "quarantined_pending_cleanup"


def _recover_model_quarantine(
    workspace_root: Path,
    path: Path,
) -> Literal["restored", "deleted", "pending"]:
    match = _MODEL_QUARANTINE_PATTERN.fullmatch(path.name)
    if match is None:
        return "pending"
    model = get_regression_model_record(workspace_root, match.group(1))
    if model is None:
        analysis_id = path.parent.name
        expected_path = (
            Path("workspaces") / "analyses" / analysis_id / f"model-{match.group(1)}.json"
        ).as_posix()
        if any(
            artifact.kind == _MODEL_ARTIFACT_KIND or artifact.path == expected_path
            for artifact in list_analysis_artifact_records(workspace_root, analysis_id)
        ):
            return "pending"
        try:
            path.unlink()
            return "deleted"
        except OSError:
            return "pending"
    original = workspace_root / Path(model.manifest_path)
    try:
        if original.exists() or _file_sha256(path) != model.manifest_sha256:
            return "pending"
        os.replace(path, original)
        return "restored"
    except OSError:
        return "pending"


def _recover_limit_set_quarantine(
    workspace_root: Path,
    path: Path,
) -> Literal["restored", "deleted", "pending"]:
    match = _LIMIT_SET_QUARANTINE_PATTERN.fullmatch(path.name)
    if match is None:
        return "pending"
    limit_set = get_attribute_control_limit_set_record(workspace_root, match.group(1))
    if limit_set is None:
        try:
            path.unlink()
            return "deleted"
        except OSError:
            return "pending"
    original = workspace_root / Path(limit_set.asset_path)
    try:
        if original.exists() or _file_sha256(path) != limit_set.asset_sha256:
            return "pending"
        os.replace(path, original)
        return "restored"
    except OSError:
        return "pending"


def _model_confirmation_error() -> ApiError:
    return ApiError(
        code="regression_model_deletion_confirmation_mismatch",
        message="회귀 모델 삭제 확인 정보가 현재 preflight와 일치하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _limit_set_confirmation_error() -> ApiError:
    return ApiError(
        code="attribute_control_limit_set_deletion_confirmation_mismatch",
        message="관리한계 세트 삭제 확인 정보가 현재 preflight와 일치하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _model_artifact_error(code: str) -> ApiError:
    return ApiError(code=code, message="회귀 모델 자산 관계를 검증할 수 없습니다.", status_code=409)


def _model_conflict() -> ApiError:
    return ApiError(
        code="regression_model_deletion_conflict",
        message="회귀 모델 삭제 대상이 preflight 이후 변경되었습니다.",
        status_code=409,
    )


def _limit_set_conflict() -> ApiError:
    return ApiError(
        code="attribute_control_limit_set_deletion_conflict",
        message="관리한계 세트 삭제 대상이 preflight 이후 변경되었습니다.",
        status_code=409,
    )


def _file_error(code: str) -> ApiError:
    return ApiError(code=code, message="저장 자산 파일을 검증할 수 없습니다.", status_code=409)
