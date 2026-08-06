import hashlib
import json
from uuid import UUID

from fastapi import status

from app.api.v1.schemas.doe import (
    DoeDesignDeleteRequest,
    DoeDesignDeleteResponse,
    DoeDesignDeletionCounts,
    DoeDesignDeletionPreflightResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import utc_now
from app.storage.metadata import (
    ExperimentDesignDeletionSnapshot,
    WorkspaceAssetStorageConflict,
    delete_experiment_design_record,
    get_experiment_design_deletion_snapshot,
)


def get_doe_design_deletion_preflight(
    settings: Settings, design_id: UUID
) -> DoeDesignDeletionPreflightResponse:
    snapshot = get_experiment_design_deletion_snapshot(settings.workspace_root, str(design_id))
    if snapshot is None:
        raise _not_found()
    counts = _counts(snapshot)
    return DoeDesignDeletionPreflightResponse(
        preflight_schema_version=1,
        design_id=design_id,
        method_id=snapshot.design.method_id,
        status=snapshot.design.status,
        counts=counts,
        deletion_manifest_sha256=_manifest(snapshot),
    )


def delete_doe_design(
    settings: Settings, design_id: UUID, body: DoeDesignDeleteRequest
) -> DoeDesignDeleteResponse:
    if body.confirmation_design_id != design_id:
        raise _conflict()
    snapshot = get_experiment_design_deletion_snapshot(settings.workspace_root, str(design_id))
    if snapshot is None:
        raise _not_found()
    manifest = _manifest(snapshot)
    if body.expected_deletion_manifest_sha256 != manifest:
        raise _conflict()
    counts_tuple = (
        snapshot.version_count,
        snapshot.run_count,
        snapshot.response_count,
        snapshot.response_revision_count,
        snapshot.analysis_count,
    )
    try:
        deleted = delete_experiment_design_record(
            settings.workspace_root,
            design_id=str(design_id),
            expected_design_sha256=snapshot.design_sha256,
            expected_counts=counts_tuple,
        )
    except WorkspaceAssetStorageConflict as exc:
        raise _conflict() from exc
    return DoeDesignDeleteResponse(
        deletion_schema_version=1,
        design_id=design_id,
        deletion_manifest_sha256=manifest,
        deleted_at=utc_now(),
        deleted_counts=_counts(deleted),
    )


def _counts(snapshot: ExperimentDesignDeletionSnapshot) -> DoeDesignDeletionCounts:
    return DoeDesignDeletionCounts(
        version_count=snapshot.version_count,
        run_count=snapshot.run_count,
        response_count=snapshot.response_count,
        response_revision_count=snapshot.response_revision_count,
        analysis_count=snapshot.analysis_count,
    )


def _manifest(snapshot: ExperimentDesignDeletionSnapshot) -> str:
    payload = {
        "schema_version": 1,
        "design_id": snapshot.design.design_id,
        "design_sha256": snapshot.design_sha256,
        "method_id": snapshot.design.method_id,
        "status": snapshot.design.status,
        "counts": _counts(snapshot).model_dump(mode="json"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _not_found() -> ApiError:
    return ApiError(
        code="doe_design_not_found",
        message="The requested DOE design was not found.",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def _conflict() -> ApiError:
    return ApiError(
        code="doe_design_deletion_conflict",
        message="The DOE design changed after deletion preflight.",
        status_code=status.HTTP_409_CONFLICT,
    )
