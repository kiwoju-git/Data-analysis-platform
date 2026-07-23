from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, File, Query, Request, UploadFile, status

from app.api.v1.schemas.datasets import (
    DatasetParsingConfirmationRequest,
    DatasetProfileResponse,
    DatasetRowsPreviewResponse,
    DatasetSchemaResponse,
    DatasetSchemaUpdateRequest,
    DatasetUploadResponse,
    DatasetVersionCatalogResponse,
    DatasetVersionDeleteRequest,
    DatasetVersionDeleteResponse,
    DatasetVersionDeletionPreflightResponse,
    DatasetVersionListResponse,
    DatasetVersionMetadataResponse,
    DatasetVersionMetadataUpdateRequest,
    DatasetVersionResponse,
    PastedDatasetRequest,
)
from app.services.dataset_profiles import get_dataset_profile
from app.services.dataset_upload import create_dataset_from_pasted_text, create_dataset_from_upload
from app.services.dataset_version_retention import (
    delete_stored_dataset_version,
    get_dataset_version_deletion_preflight,
)
from app.services.dataset_versions import (
    confirm_dataset_parsing,
    get_dataset_rows_preview,
    get_dataset_schema,
    get_dataset_version,
    list_dataset_version_catalog,
    list_dataset_versions,
    update_dataset_schema,
    update_dataset_version_metadata,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])
version_router = APIRouter(prefix="/dataset-versions", tags=["dataset-versions"])


@version_router.get("", response_model=DatasetVersionCatalogResponse)
def list_dataset_version_catalog_route(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    visibility: Literal["visible", "archived", "all"] = Query(default="visible"),
) -> DatasetVersionCatalogResponse:
    return list_dataset_version_catalog(
        settings=request.app.state.settings,
        limit=limit,
        offset=offset,
        visibility=visibility,
    )


@router.post(
    "",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset(
    request: Request,
    file: Annotated[UploadFile, File(...)],
) -> DatasetUploadResponse:
    return await create_dataset_from_upload(
        upload_file=file,
        settings=request.app.state.settings,
    )


@router.post(
    "/paste",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset_from_paste_route(
    request: Request,
    body: PastedDatasetRequest,
) -> DatasetUploadResponse:
    return create_dataset_from_pasted_text(
        request=body,
        settings=request.app.state.settings,
    )


@router.post(
    "/{dataset_id}/confirm-parsing",
    response_model=DatasetVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_dataset_parsing_route(
    request: Request,
    dataset_id: UUID,
    body: DatasetParsingConfirmationRequest,
) -> DatasetVersionResponse:
    return confirm_dataset_parsing(
        settings=request.app.state.settings,
        dataset_id=dataset_id,
        request=body,
    )


@router.get(
    "/{dataset_id}/versions",
    response_model=DatasetVersionListResponse,
)
def list_dataset_versions_route(
    request: Request,
    dataset_id: UUID,
) -> DatasetVersionListResponse:
    return list_dataset_versions(
        settings=request.app.state.settings,
        dataset_id=dataset_id,
    )


@version_router.get(
    "/{version_id}",
    response_model=DatasetVersionResponse,
)
def get_dataset_version_route(
    request: Request,
    version_id: UUID,
) -> DatasetVersionResponse:
    return get_dataset_version(
        settings=request.app.state.settings,
        version_id=version_id,
    )


@version_router.patch(
    "/{version_id}/metadata",
    response_model=DatasetVersionMetadataResponse,
)
def update_dataset_version_metadata_route(
    request: Request,
    version_id: UUID,
    body: DatasetVersionMetadataUpdateRequest,
) -> DatasetVersionMetadataResponse:
    return update_dataset_version_metadata(
        settings=request.app.state.settings,
        version_id=version_id,
        body=body,
    )


@version_router.get(
    "/{version_id}/deletion-preflight",
    response_model=DatasetVersionDeletionPreflightResponse,
)
def get_dataset_version_deletion_preflight_route(
    request: Request,
    version_id: UUID,
) -> DatasetVersionDeletionPreflightResponse:
    return get_dataset_version_deletion_preflight(
        settings=request.app.state.settings,
        version_id=version_id,
    )


@version_router.delete(
    "/{version_id}/deletion",
    response_model=DatasetVersionDeleteResponse,
)
def delete_dataset_version_route(
    request: Request,
    version_id: UUID,
    body: DatasetVersionDeleteRequest,
) -> DatasetVersionDeleteResponse:
    return delete_stored_dataset_version(
        settings=request.app.state.settings,
        version_id=version_id,
        body=body,
    )


@version_router.get(
    "/{version_id}/schema",
    response_model=DatasetSchemaResponse,
)
def get_dataset_schema_route(
    request: Request,
    version_id: UUID,
) -> DatasetSchemaResponse:
    return get_dataset_schema(
        settings=request.app.state.settings,
        version_id=version_id,
    )


@version_router.patch(
    "/{version_id}/schema",
    response_model=DatasetSchemaResponse,
)
def update_dataset_schema_route(
    request: Request,
    version_id: UUID,
    body: DatasetSchemaUpdateRequest,
) -> DatasetSchemaResponse:
    return update_dataset_schema(
        settings=request.app.state.settings,
        version_id=version_id,
        request=body,
    )


@version_router.get(
    "/{version_id}/rows",
    response_model=DatasetRowsPreviewResponse,
)
def get_dataset_rows_preview_route(
    request: Request,
    version_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> DatasetRowsPreviewResponse:
    return get_dataset_rows_preview(
        settings=request.app.state.settings,
        version_id=version_id,
        offset=offset,
        limit=limit,
    )


@version_router.get(
    "/{version_id}/profile",
    response_model=DatasetProfileResponse,
)
def get_dataset_profile_route(
    request: Request,
    version_id: UUID,
) -> DatasetProfileResponse:
    return get_dataset_profile(
        settings=request.app.state.settings,
        version_id=version_id,
    )
