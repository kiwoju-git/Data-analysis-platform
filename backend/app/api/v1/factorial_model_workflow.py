from uuid import UUID

from fastapi import APIRouter, Request, Response

from app.api.v1.schemas.doe_model_workflow import (
    DoeAnalysisAssetDeleteRequest,
    DoeAnalysisAssetDeleteResponse,
    DoeAnalysisAssetDescriptor,
    DoeAnalysisAssetList,
    DoeAnalysisDeleteRequest,
    DoeAnalysisDeletionPreflight,
    DoeAnalysisHtmlExportRequest,
    DoePredictionCreateRequest,
    DoePredictionPreflightRequest,
    DoePredictionPreflightResponse,
    DoePredictionResponse,
)
from app.services.factorial_analysis_assets import (
    create_factorial_html_report,
    delete_factorial_analysis,
    delete_factorial_analysis_asset,
    download_factorial_analysis_asset,
    factorial_analysis_asset_deletion_preflight,
    factorial_analysis_deletion_preflight,
    list_factorial_analysis_assets,
)
from app.services.factorial_prediction import (
    create_factorial_prediction,
    factorial_prediction_preflight,
    get_factorial_prediction,
)

router = APIRouter(prefix="/{design_id}/analyses/{analysis_id}")


@router.post("/exports/html", response_model=DoeAnalysisAssetDescriptor, status_code=201)
def create_report_route(
    request: Request, design_id: UUID, analysis_id: UUID, body: DoeAnalysisHtmlExportRequest
) -> DoeAnalysisAssetDescriptor:
    return create_factorial_html_report(request.app.state.settings, design_id, analysis_id, body)


@router.get("/exports", response_model=DoeAnalysisAssetList)
def list_reports_route(
    request: Request, design_id: UUID, analysis_id: UUID
) -> DoeAnalysisAssetList:
    return list_factorial_analysis_assets(
        request.app.state.settings, design_id, analysis_id, "html_report"
    )


@router.get("/predictions", response_model=DoeAnalysisAssetList)
def list_predictions_route(
    request: Request, design_id: UUID, analysis_id: UUID
) -> DoeAnalysisAssetList:
    return list_factorial_analysis_assets(
        request.app.state.settings, design_id, analysis_id, "prediction"
    )


@router.get("/exports/{asset_id}/download")
def download_report_route(
    request: Request, design_id: UUID, analysis_id: UUID, asset_id: UUID
) -> Response:
    descriptor, content = download_factorial_analysis_asset(
        request.app.state.settings, design_id, analysis_id, asset_id
    )
    suffix = "html" if descriptor.kind == "html_report" else "json"
    return Response(
        content=content,
        media_type=descriptor.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="factorial-analysis-{asset_id}.{suffix}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        },
    )


@router.get("/exports/{asset_id}/deletion-preflight", response_model=DoeAnalysisAssetDescriptor)
def asset_deletion_preflight_route(
    request: Request, design_id: UUID, analysis_id: UUID, asset_id: UUID
) -> DoeAnalysisAssetDescriptor:
    return factorial_analysis_asset_deletion_preflight(
        request.app.state.settings, design_id, analysis_id, asset_id
    )


@router.delete("/exports/{asset_id}", response_model=DoeAnalysisAssetDeleteResponse)
def delete_asset_route(
    request: Request,
    design_id: UUID,
    analysis_id: UUID,
    asset_id: UUID,
    body: DoeAnalysisAssetDeleteRequest,
) -> DoeAnalysisAssetDeleteResponse:
    return delete_factorial_analysis_asset(
        request.app.state.settings, design_id, analysis_id, asset_id, body
    )


@router.get("/deletion-preflight", response_model=DoeAnalysisDeletionPreflight)
def analysis_deletion_preflight_route(
    request: Request, design_id: UUID, analysis_id: UUID
) -> DoeAnalysisDeletionPreflight:
    return factorial_analysis_deletion_preflight(request.app.state.settings, design_id, analysis_id)


@router.delete("", response_model=DoeAnalysisDeletionPreflight)
def delete_analysis_route(
    request: Request, design_id: UUID, analysis_id: UUID, body: DoeAnalysisDeleteRequest
) -> DoeAnalysisDeletionPreflight:
    return delete_factorial_analysis(request.app.state.settings, design_id, analysis_id, body)


@router.post("/prediction-preflight", response_model=DoePredictionPreflightResponse)
def prediction_preflight_route(
    request: Request, design_id: UUID, analysis_id: UUID, body: DoePredictionPreflightRequest
) -> DoePredictionPreflightResponse:
    return factorial_prediction_preflight(request.app.state.settings, design_id, analysis_id, body)


@router.post("/predictions", response_model=DoePredictionResponse, status_code=201)
def create_prediction_route(
    request: Request, design_id: UUID, analysis_id: UUID, body: DoePredictionCreateRequest
) -> DoePredictionResponse:
    return create_factorial_prediction(request.app.state.settings, design_id, analysis_id, body)


@router.get("/predictions/{prediction_id}", response_model=DoePredictionResponse)
def get_prediction_route(
    request: Request, design_id: UUID, analysis_id: UUID, prediction_id: UUID
) -> DoePredictionResponse:
    return get_factorial_prediction(
        request.app.state.settings, design_id, analysis_id, prediction_id
    )
