"""Managed exports of immutable workflow sources, separate from calculation APIs."""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from app.api.v1.schemas.reports import (
    CreateManagedReportRequest,
    ManagedReportActionRequest,
    ManagedReportDescriptor,
    ManagedReportList,
    ReportSourceKind,
    ReportSourceList,
    ReportSourceQuery,
    StoredReportCapability,
    StoredSourceSnapshot,
)
from app.core.errors import ApiError
from app.services.report_exports import (
    create_report,
    delete_report,
    download_report,
    get_report,
    list_reports,
)
from app.services.report_source_contract import report_source_sha256
from app.services.report_sources import (
    list_report_sources,
    prepare_report_source,
    report_capability,
)
from app.storage.managed_report_artifacts import ManagedReportStorageError
from app.storage.metadata import WorkspaceAssetStorageConflict
from app.storage.source_bound_artifacts import SourceBoundArtifactError

router = APIRouter(prefix="/reports", tags=["reports"])


@contextmanager
def _storage_errors() -> Iterator[None]:
    try:
        yield
    except (
        ManagedReportStorageError,
        SourceBoundArtifactError,
        WorkspaceAssetStorageConflict,
    ) as exc:
        code = exc.code
        raise ApiError(
            code=code,
            message="The saved report or its exact source could not be verified.",
            status_code=404 if code.endswith("not_found") else 409,
        ) from exc


@router.get("/sources", response_model=ReportSourceList)
def sources_route(
    request: Request,
    source_kind: ReportSourceKind,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ReportSourceList:
    with _storage_errors():
        return list_report_sources(
            request.app.state.settings, source_kind=source_kind, limit=limit, offset=offset
        )


@router.post("/capability", response_model=StoredReportCapability)
def capability_route(request: Request, body: ReportSourceQuery) -> StoredReportCapability:
    with _storage_errors():
        verified = prepare_report_source(request.app.state.settings, body.source, body.locale)
        return report_capability(verified, body.locale)


@router.post("", response_model=ManagedReportDescriptor, status_code=201)
def create_route(request: Request, body: CreateManagedReportRequest) -> ManagedReportDescriptor:
    with _storage_errors():
        return create_report(request.app.state.settings, body)


@router.post("/source-snapshot", response_model=StoredSourceSnapshot)
def source_snapshot_route(request: Request, body: ReportSourceQuery) -> StoredSourceSnapshot:
    with _storage_errors():
        verified = prepare_report_source(request.app.state.settings, body.source, body.locale)
        return StoredSourceSnapshot(
            source=verified.source,
            source_ref_sha256=report_source_sha256(verified.source),
            locale=body.locale,
            title=verified.title,
            created_at=verified.created_at,
            stale=verified.stale,
            payload=verified.payload,
        )


@router.post("/artifacts/query", response_model=ManagedReportList)
def list_route(request: Request, body: ReportSourceQuery) -> ManagedReportList:
    with _storage_errors():
        return list_reports(request.app.state.settings, body)


@router.get("/{export_id}", response_model=ManagedReportDescriptor)
def get_route(request: Request, export_id: UUID) -> ManagedReportDescriptor:
    with _storage_errors():
        return get_report(request.app.state.settings, export_id)


@router.post("/{export_id}/download")
def download_route(request: Request, export_id: UUID, body: ManagedReportActionRequest) -> Response:
    with _storage_errors():
        content = download_report(request.app.state.settings, export_id, body)
    return Response(
        content=content,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="statistical-twin-report-{export_id}.html"'
            ),
            "X-Content-SHA256": body.expected_sha256,
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
                "base-uri 'none'; form-action 'none'"
            ),
        },
    )


@router.delete("/{export_id}")
def delete_route(
    request: Request, export_id: UUID, body: ManagedReportActionRequest
) -> dict[str, bool]:
    with _storage_errors():
        delete_report(request.app.state.settings, export_id, body)
    return {"deleted": True}
