from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from app.api.v1.schemas.doe import (
    DoeDesignResponsesResponse,
    DoeDesignResponsesUpsertRequest,
    DoeFactorialAnalysisCreateRequest,
    DoeFactorialAnalysisResponse,
    DoeResponseRevisionCreateRequest,
    DoeResponseRevisionHistoryResponse,
    DoeResponseRevisionResponse,
    DoeResponseSurfaceAnalysisCatalogResponse,
    DoeResponseSurfaceAnalysisCreateRequest,
    DoeResponseSurfaceAnalysisResponse,
    FactorialDesignCreateRequest,
    FactorialDesignResponse,
    ResponseOptimizerCreateRequest,
    ResponseOptimizerResponse,
    ResponseSurfaceDesignCreateRequest,
    ResponseSurfaceDesignResponse,
)
from app.services.doe_designs import (
    create_factorial_design,
    get_factorial_design,
    get_factorial_design_html_report,
    list_factorial_design_responses,
    save_factorial_design_responses,
)
from app.services.doe_factorial_analysis import create_factorial_analysis, get_factorial_analysis
from app.services.doe_response_revisions import (
    abandon_response_revision,
    create_response_revision,
    get_response_revision,
    list_response_revisions,
)
from app.services.doe_response_surface_analysis import (
    create_response_surface_analysis,
    get_response_surface_analysis,
)
from app.services.response_optimizer import (
    create_response_optimizer,
    get_response_optimizer,
    list_response_surface_analysis_catalog,
)
from app.services.response_surface_designs import (
    create_response_surface_design,
    get_response_surface_design,
    list_response_surface_responses,
    save_response_surface_responses,
)

router = APIRouter(prefix="/doe-designs", tags=["doe-designs"])


@router.get(
    "/response-surface-analyses",
    response_model=DoeResponseSurfaceAnalysisCatalogResponse,
)
def list_response_surface_analysis_catalog_route(
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> DoeResponseSurfaceAnalysisCatalogResponse:
    return list_response_surface_analysis_catalog(
        settings=request.app.state.settings,
        offset=offset,
        limit=limit,
    )


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


@router.post(
    "/response-surface",
    response_model=ResponseSurfaceDesignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_response_surface_design_route(
    request: Request,
    body: ResponseSurfaceDesignCreateRequest,
) -> ResponseSurfaceDesignResponse:
    return create_response_surface_design(settings=request.app.state.settings, body=body)


@router.get(
    "/response-surface/{design_id}",
    response_model=ResponseSurfaceDesignResponse,
)
def get_response_surface_design_route(
    request: Request,
    design_id: UUID,
) -> ResponseSurfaceDesignResponse:
    return get_response_surface_design(request.app.state.settings, design_id)


@router.put(
    "/response-surface/{design_id}/responses",
    response_model=DoeDesignResponsesResponse,
)
def save_response_surface_responses_route(
    request: Request,
    design_id: UUID,
    body: DoeDesignResponsesUpsertRequest,
) -> DoeDesignResponsesResponse:
    return save_response_surface_responses(request.app.state.settings, design_id, body)


@router.get(
    "/response-surface/{design_id}/responses",
    response_model=DoeDesignResponsesResponse,
)
def list_response_surface_responses_route(
    request: Request,
    design_id: UUID,
) -> DoeDesignResponsesResponse:
    return list_response_surface_responses(request.app.state.settings, design_id)


@router.post(
    "/response-surface/{design_id}/analyses",
    response_model=DoeResponseSurfaceAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_response_surface_analysis_route(
    request: Request,
    design_id: UUID,
    body: DoeResponseSurfaceAnalysisCreateRequest,
) -> DoeResponseSurfaceAnalysisResponse:
    return create_response_surface_analysis(request.app.state.settings, design_id, body)


@router.get(
    "/response-surface/{design_id}/analyses/{analysis_id}",
    response_model=DoeResponseSurfaceAnalysisResponse,
)
def get_response_surface_analysis_route(
    request: Request,
    design_id: UUID,
    analysis_id: UUID,
) -> DoeResponseSurfaceAnalysisResponse:
    return get_response_surface_analysis(request.app.state.settings, design_id, analysis_id)


@router.post(
    "/response-surface/{design_id}/optimizations",
    response_model=ResponseOptimizerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_response_optimizer_route(
    request: Request,
    design_id: UUID,
    body: ResponseOptimizerCreateRequest,
) -> ResponseOptimizerResponse:
    return create_response_optimizer(request.app.state.settings, design_id, body)


@router.get(
    "/response-surface/{design_id}/optimizations/{optimization_id}",
    response_model=ResponseOptimizerResponse,
)
def get_response_optimizer_route(
    request: Request,
    design_id: UUID,
    optimization_id: UUID,
) -> ResponseOptimizerResponse:
    return get_response_optimizer(
        request.app.state.settings,
        design_id,
        optimization_id,
    )


@router.post(
    "/{design_id}/response-revisions",
    response_model=DoeResponseRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_response_revision_route(
    request: Request,
    design_id: UUID,
    body: DoeResponseRevisionCreateRequest,
) -> DoeResponseRevisionResponse:
    return create_response_revision(
        request.app.state.settings,
        design_id,
        body,
        allow_analyzed=True,
        require_explicit_supersedes=True,
    )


@router.get(
    "/{design_id}/response-revisions",
    response_model=DoeResponseRevisionHistoryResponse,
)
def list_response_revisions_route(
    request: Request,
    design_id: UUID,
    response_name: str = Query(min_length=1, max_length=80),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> DoeResponseRevisionHistoryResponse:
    return list_response_revisions(
        request.app.state.settings,
        design_id,
        response_name,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{design_id}/response-revisions/{response_revision_id}",
    response_model=DoeResponseRevisionResponse,
)
def get_response_revision_route(
    request: Request,
    design_id: UUID,
    response_revision_id: UUID,
) -> DoeResponseRevisionResponse:
    return get_response_revision(request.app.state.settings, design_id, response_revision_id)


@router.post(
    "/{design_id}/response-revisions/{response_revision_id}/abandon",
    response_model=DoeResponseRevisionResponse,
)
def abandon_response_revision_route(
    request: Request,
    design_id: UUID,
    response_revision_id: UUID,
) -> DoeResponseRevisionResponse:
    return abandon_response_revision(request.app.state.settings, design_id, response_revision_id)


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


@router.post(
    "/{design_id}/analyses",
    response_model=DoeFactorialAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_factorial_analysis_route(
    request: Request,
    design_id: UUID,
    body: DoeFactorialAnalysisCreateRequest,
) -> DoeFactorialAnalysisResponse:
    return create_factorial_analysis(
        settings=request.app.state.settings,
        design_id=design_id,
        body=body,
    )


@router.get(
    "/{design_id}/analyses/{analysis_id}",
    response_model=DoeFactorialAnalysisResponse,
)
def get_factorial_analysis_route(
    request: Request,
    design_id: UUID,
    analysis_id: UUID,
) -> DoeFactorialAnalysisResponse:
    return get_factorial_analysis(
        settings=request.app.state.settings,
        design_id=design_id,
        analysis_id=analysis_id,
    )
