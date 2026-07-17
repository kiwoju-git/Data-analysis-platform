from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.schemas.analyses import (
    GageRrPreflightRequest,
    GageRrPreflightResponse,
)
from app.api.v1.schemas.quality import (
    AttributeControlLimitSetCreateRequest,
    AttributeControlLimitSetDeleteRequest,
    AttributeControlLimitSetDeleteResponse,
    AttributeControlLimitSetDeletionPreflightResponse,
    AttributeControlLimitSetListResponse,
    AttributeControlLimitSetResponse,
    AttributeControlMonitoringPreflightRequest,
    AttributeControlMonitoringPreflightResponse,
)
from app.services.attribute_control_limit_sets import (
    create_attribute_control_limit_set,
    get_attribute_control_limit_set,
    list_attribute_control_limit_sets,
)
from app.services.attribute_control_phase_2 import get_attribute_control_monitoring_preflight
from app.services.gage_rr import get_gage_rr_preflight
from app.services.workspace_asset_retention import (
    delete_stored_attribute_control_limit_set,
    get_attribute_control_limit_set_deletion_preflight,
)

router = APIRouter(prefix="/quality", tags=["quality"])


@router.post(
    "/attribute-control-limit-sets",
    response_model=AttributeControlLimitSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attribute_control_limit_set_route(
    request: Request,
    body: AttributeControlLimitSetCreateRequest,
) -> AttributeControlLimitSetResponse:
    return create_attribute_control_limit_set(
        settings=request.app.state.settings,
        source_analysis_id=body.source_analysis_id,
    )


@router.get(
    "/attribute-control-limit-sets",
    response_model=AttributeControlLimitSetListResponse,
)
def list_attribute_control_limit_sets_route(
    request: Request,
    source_dataset_version_id: UUID | None = None,
    chart_type: Annotated[Literal["p", "np", "c", "u"] | None, Query()] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AttributeControlLimitSetListResponse:
    return list_attribute_control_limit_sets(
        settings=request.app.state.settings,
        source_dataset_version_id=source_dataset_version_id,
        chart_type=chart_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/attribute-control-limit-sets/{limit_set_id}",
    response_model=AttributeControlLimitSetResponse,
)
def get_attribute_control_limit_set_route(
    request: Request,
    limit_set_id: UUID,
) -> AttributeControlLimitSetResponse:
    return get_attribute_control_limit_set(
        settings=request.app.state.settings,
        limit_set_id=limit_set_id,
    )


@router.get(
    "/attribute-control-limit-sets/{limit_set_id}/deletion-preflight",
    response_model=AttributeControlLimitSetDeletionPreflightResponse,
)
def get_attribute_control_limit_set_deletion_preflight_route(
    request: Request,
    limit_set_id: UUID,
) -> AttributeControlLimitSetDeletionPreflightResponse:
    return get_attribute_control_limit_set_deletion_preflight(
        settings=request.app.state.settings,
        limit_set_id=limit_set_id,
    )


@router.delete(
    "/attribute-control-limit-sets/{limit_set_id}",
    response_model=AttributeControlLimitSetDeleteResponse,
)
def delete_attribute_control_limit_set_route(
    request: Request,
    limit_set_id: UUID,
    body: AttributeControlLimitSetDeleteRequest,
) -> AttributeControlLimitSetDeleteResponse:
    return delete_stored_attribute_control_limit_set(
        settings=request.app.state.settings,
        limit_set_id=limit_set_id,
        body=body,
    )


@router.post(
    "/attribute-control-limit-sets/{limit_set_id}/monitoring-preflight",
    response_model=AttributeControlMonitoringPreflightResponse,
)
def get_attribute_control_monitoring_preflight_route(
    request: Request,
    limit_set_id: UUID,
    body: AttributeControlMonitoringPreflightRequest,
) -> AttributeControlMonitoringPreflightResponse:
    return get_attribute_control_monitoring_preflight(
        settings=request.app.state.settings,
        limit_set_id=limit_set_id,
        body=body,
    )


@router.post("/gage-rr/preflight", response_model=GageRrPreflightResponse)
def get_gage_rr_preflight_route(
    request: Request,
    body: GageRrPreflightRequest,
) -> GageRrPreflightResponse:
    return get_gage_rr_preflight(
        settings=request.app.state.settings,
        body=body,
    )
