from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from app.api.v1.schemas.analyses import (
    AnalysisResultCsvExportResponse,
    AnalysisResultEnvelope,
    AnalysisResultExportListResponse,
    AnalysisResultHtmlReportResponse,
    AnalysisResultJsonExportResponse,
    AnalysisRunComparisonResponse,
    AnalysisRunListResponse,
    AnalysisRunRequest,
    AnalysisRunState,
    AnalysisRunStatusResponse,
)
from app.services.analysis_runs import (
    compare_analysis_runs,
    create_analysis_result_csv_export,
    create_analysis_result_html_report_export,
    create_analysis_result_json_export,
    create_analysis_run,
    get_analysis_result_export_download,
    get_analysis_run_result,
    get_analysis_run_status,
    list_analysis_result_exports,
    list_analysis_runs,
    request_analysis_run_cancellation,
)

router = APIRouter(prefix="/analysis-runs", tags=["analysis-runs"])


@router.get("", response_model=AnalysisRunListResponse)
def list_analysis_runs_route(
    request: Request,
    dataset_version_id: UUID | None = None,
    method_id: Annotated[str | None, Query(min_length=1)] = None,
    run_status: Annotated[AnalysisRunState | None, Query(alias="status")] = None,
    stale: bool | None = None,
    result_available: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AnalysisRunListResponse:
    return list_analysis_runs(
        workspace_root=request.app.state.settings.workspace_root,
        dataset_version_id=dataset_version_id,
        method_id=method_id,
        run_status=run_status,
        stale=stale,
        result_available=result_available,
        limit=limit,
        offset=offset,
    )


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


@router.get("/comparison", response_model=AnalysisRunComparisonResponse)
def compare_analysis_runs_route(
    request: Request,
    left_analysis_id: UUID,
    right_analysis_id: UUID,
) -> AnalysisRunComparisonResponse:
    return compare_analysis_runs(
        settings=request.app.state.settings,
        left_analysis_id=left_analysis_id,
        right_analysis_id=right_analysis_id,
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


@router.get("/{analysis_id}/exports", response_model=AnalysisResultExportListResponse)
def list_analysis_result_exports_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisResultExportListResponse:
    return list_analysis_result_exports(
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
