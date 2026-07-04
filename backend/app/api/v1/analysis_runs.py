from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from app.api.v1.schemas.analyses import (
    AnalysisResultCsvExportResponse,
    AnalysisResultEnvelope,
    AnalysisResultHtmlReportResponse,
    AnalysisResultJsonExportResponse,
    AnalysisRunRequest,
    AnalysisRunStatusResponse,
)
from app.services.analysis_runs import (
    create_analysis_result_csv_export,
    create_analysis_result_html_report_export,
    create_analysis_result_json_export,
    create_analysis_run,
    get_analysis_result_export_download,
    get_analysis_run_result,
    get_analysis_run_status,
    request_analysis_run_cancellation,
)

router = APIRouter(prefix="/analysis-runs", tags=["analysis-runs"])


@router.post(
    "",
    response_model=AnalysisResultEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_run_route(
    request: Request,
    body: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    return create_analysis_run(
        settings=request.app.state.settings,
        request=body,
    )


@router.get("/{analysis_id}/result", response_model=AnalysisResultEnvelope)
def get_analysis_run_result_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisResultEnvelope:
    return get_analysis_run_result(
        settings=request.app.state.settings,
        analysis_id=analysis_id,
    )


@router.post(
    "/{analysis_id}/exports/json",
    response_model=AnalysisResultJsonExportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_result_json_export_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisResultJsonExportResponse:
    return create_analysis_result_json_export(
        settings=request.app.state.settings,
        analysis_id=analysis_id,
    )


@router.post(
    "/{analysis_id}/exports/csv",
    response_model=AnalysisResultCsvExportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_result_csv_export_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisResultCsvExportResponse:
    return create_analysis_result_csv_export(
        settings=request.app.state.settings,
        analysis_id=analysis_id,
    )


@router.post(
    "/{analysis_id}/exports/html",
    response_model=AnalysisResultHtmlReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_result_html_report_export_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisResultHtmlReportResponse:
    return create_analysis_result_html_report_export(
        settings=request.app.state.settings,
        analysis_id=analysis_id,
    )


@router.get("/{analysis_id}/exports/{export_id}/download")
def download_analysis_result_export_route(
    request: Request,
    analysis_id: UUID,
    export_id: UUID,
) -> Response:
    download = get_analysis_result_export_download(
        settings=request.app.state.settings,
        analysis_id=analysis_id,
        export_id=export_id,
    )
    return Response(
        content=download.content,
        media_type=download.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{download.filename}"',
            "ETag": f'"sha256:{download.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{analysis_id}", response_model=AnalysisRunStatusResponse)
def get_analysis_run_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    return get_analysis_run_status(
        workspace_root=request.app.state.settings.workspace_root,
        analysis_id=analysis_id,
    )


@router.delete("/{analysis_id}", response_model=AnalysisRunStatusResponse)
def cancel_analysis_run_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    return request_analysis_run_cancellation(
        workspace_root=request.app.state.settings.workspace_root,
        analysis_id=analysis_id,
    )
