from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from app.api.v1.schemas.doe import (
    DoeDesignResponsesResponse,
    DoeDesignResponsesUpsertRequest,
    FactorialDesignCreateRequest,
    FactorialDesignResponse,
)
from app.services.doe_designs import (
    create_factorial_design,
    get_factorial_design,
    get_factorial_design_html_report,
    list_factorial_design_responses,
    save_factorial_design_responses,
)

router = APIRouter(prefix="/doe-designs", tags=["doe-designs"])


@router.post(
    "/factorial",
    response_model=FactorialDesignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_factorial_design_route(
    request: Request,
    body: FactorialDesignCreateRequest,
) -> FactorialDesignResponse:
    return create_factorial_design(
        settings=request.app.state.settings,
        body=body,
    )


@router.get("/{design_id}", response_model=FactorialDesignResponse)
def get_factorial_design_route(
    request: Request,
    design_id: UUID,
) -> FactorialDesignResponse:
    return get_factorial_design(
        settings=request.app.state.settings,
        design_id=design_id,
    )


@router.get("/{design_id}/report.html")
def download_factorial_design_html_report_route(
    request: Request,
    design_id: UUID,
) -> Response:
    report = get_factorial_design_html_report(
        settings=request.app.state.settings,
        design_id=design_id,
    )
    return Response(
        content=report.content,
        media_type=report.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{report.filename}"',
            "ETag": f'"sha256:{report.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.put("/{design_id}/responses", response_model=DoeDesignResponsesResponse)
def save_factorial_design_responses_route(
    request: Request,
    design_id: UUID,
    body: DoeDesignResponsesUpsertRequest,
) -> DoeDesignResponsesResponse:
    return save_factorial_design_responses(
        settings=request.app.state.settings,
        design_id=design_id,
        body=body,
    )


@router.get("/{design_id}/responses", response_model=DoeDesignResponsesResponse)
def list_factorial_design_responses_route(
    request: Request,
    design_id: UUID,
) -> DoeDesignResponsesResponse:
    return list_factorial_design_responses(
        settings=request.app.state.settings,
        design_id=design_id,
    )
