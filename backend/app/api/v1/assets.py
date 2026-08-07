from typing import Literal

from fastapi import APIRouter, Query, Request

from app.api.v1.schemas.assets import (
    EditableWorkspaceAssetType,
    WorkspaceAssetCatalogResponse,
    WorkspaceAssetMetadataResponse,
    WorkspaceAssetMetadataUpdateRequest,
)
from app.services.workspace_assets import list_workspace_assets, update_workspace_asset_metadata

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=WorkspaceAssetCatalogResponse)
def list_workspace_assets_route(
    request: Request,
    category: Literal["datasets", "analyses", "models", "designs"] | None = None,
    method_id: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    pinned: bool | None = None,
    search: str | None = Query(default=None, max_length=120),
    sort: Literal["updated_desc", "created_desc", "name_asc"] = "updated_desc",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> WorkspaceAssetCatalogResponse:
    return list_workspace_assets(
        request.app.state.settings,
        category=category,
        method_id=method_id,
        status_filter=status_filter,
        pinned=pinned,
        search=search,
        sort=sort,
        offset=offset,
        limit=limit,
    )


@router.patch(
    "/{asset_type}/{asset_id}/metadata",
    response_model=WorkspaceAssetMetadataResponse,
)
def update_workspace_asset_metadata_route(
    request: Request,
    asset_type: EditableWorkspaceAssetType,
    asset_id: str,
    body: WorkspaceAssetMetadataUpdateRequest,
) -> WorkspaceAssetMetadataResponse:
    return update_workspace_asset_metadata(
        request.app.state.settings,
        asset_type=asset_type,
        asset_id=asset_id,
        body=body,
    )
