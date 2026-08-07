from datetime import datetime, timezone
from typing import cast

from fastapi import status

from app.api.v1.schemas.assets import (
    EditableWorkspaceAssetType,
    WorkspaceAssetCatalogResponse,
    WorkspaceAssetDescriptor,
    WorkspaceAssetMetadataResponse,
    WorkspaceAssetMetadataUpdateRequest,
    WorkspaceAssetOpenTarget,
    WorkspaceAssetType,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.storage.metadata import (
    WorkspaceAssetCatalogRecord,
    WorkspaceAssetStorageConflict,
    get_workspace_asset_user_metadata,
    list_workspace_asset_catalog_records,
    upsert_workspace_asset_user_metadata,
)


def list_workspace_assets(
    settings: Settings,
    *,
    category: str | None,
    method_id: str | None,
    status_filter: str | None,
    pinned: bool | None,
    search: str | None,
    sort: str,
    offset: int,
    limit: int,
) -> WorkspaceAssetCatalogResponse:
    total, records = list_workspace_asset_catalog_records(
        settings.workspace_root,
        category=category,
        method_id=method_id.strip() if method_id and method_id.strip() else None,
        status_filter=(status_filter.strip() if status_filter and status_filter.strip() else None),
        pinned=pinned,
        search=search.strip() if search and search.strip() else None,
        sort=sort,
        offset=offset,
        limit=limit,
    )
    return WorkspaceAssetCatalogResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[_descriptor(record) for record in records],
    )


def _descriptor(record: WorkspaceAssetCatalogRecord) -> WorkspaceAssetDescriptor:
    return WorkspaceAssetDescriptor(
        asset_id=record.asset_id,
        asset_type=cast(WorkspaceAssetType, record.asset_type),
        subtype=record.subtype,
        method_id=record.method_id,
        display_name=record.display_name,
        secondary_text=record.secondary_text,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        pinned=record.pinned,
        note=record.note,
        metadata_updated_at=record.metadata_updated_at,
        dependency_count=record.dependency_count,
        open_target=_open_target(record),
    )


def update_workspace_asset_metadata(
    settings: Settings,
    *,
    asset_type: EditableWorkspaceAssetType,
    asset_id: str,
    body: WorkspaceAssetMetadataUpdateRequest,
) -> WorkspaceAssetMetadataResponse:
    current = get_workspace_asset_user_metadata(
        settings.workspace_root, owner_type=asset_type, owner_id=asset_id
    )
    fields = body.model_fields_set
    user_label = (
        body.user_label if "user_label" in fields else current.user_label if current else None
    )
    note = body.note if "note" in fields else current.note if current else None
    pinned = body.pinned if "pinned" in fields else current.pinned if current else False
    updated_at = datetime.now(timezone.utc).isoformat()
    try:
        metadata = upsert_workspace_asset_user_metadata(
            settings.workspace_root,
            owner_type=asset_type,
            owner_id=asset_id,
            user_label=user_label,
            note=note,
            pinned=bool(pinned),
            updated_at=updated_at,
            expected_updated_at=body.expected_metadata_updated_at,
        )
    except KeyError as exc:
        raise ApiError(
            code="workspace_asset_not_found",
            message="The requested workspace asset was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        ) from exc
    except WorkspaceAssetStorageConflict as exc:
        raise ApiError(
            code=exc.code,
            message="The asset metadata changed in another view. Refresh the catalog and retry.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    return WorkspaceAssetMetadataResponse(
        asset_type=asset_type,
        asset_id=asset_id,
        user_label=metadata.user_label,
        note=metadata.note,
        pinned=metadata.pinned,
        metadata_updated_at=metadata.updated_at,
    )


def _open_target(record: WorkspaceAssetCatalogRecord) -> WorkspaceAssetOpenTarget:
    if record.asset_type == "dataset_version":
        return WorkspaceAssetOpenTarget(
            path=f"/datasets?version_id={record.asset_id}", label="데이터셋에서 열기"
        )
    if record.asset_type == "analysis_run":
        return WorkspaceAssetOpenTarget(
            path=f"/reports?analysis_id={record.asset_id}", label="리포트에서 열기"
        )
    if record.asset_type == "regression_model":
        return WorkspaceAssetOpenTarget(
            path=f"/analysis/regression/regression.linear_model?model_id={record.asset_id}",
            label="예측 입력 열기",
        )
    if record.asset_type == "bayesian_study":
        return WorkspaceAssetOpenTarget(
            path=("/analysis/doe/doe.bayesian_optimization" f"?study_id={record.asset_id}"),
            label="Bayesian에서 열기",
        )
    method_path = {
        "doe.factorial_design": "doe.factorial_design",
        "doe.general_factorial_design": "doe.factorial_design",
        "doe.latin_hypercube": "doe.latin_hypercube",
        "doe.response_surface": "doe.response_surface",
    }.get(record.method_id or "", "doe.factorial_design")
    design_kind = "general" if record.method_id == "doe.general_factorial_design" else "two_level"
    return WorkspaceAssetOpenTarget(
        path=(
            f"/analysis/doe/{method_path}?design_id={record.asset_id}" f"&design_kind={design_kind}"
        ),
        label="실험 설계에서 열기",
    )
