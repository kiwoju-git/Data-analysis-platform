"""Immutable, bounded plot assets owned by an exact stored RSM analysis."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.api.v1.schemas.doe import DoeResponseSurfaceAnalysisResponse
from app.api.v1.schemas.rsm_plots import (
    RsmPlotSource,
    RsmPlotViewDescriptor,
    RsmPlotViewRequest,
    RsmPlotViewResponse,
    RsmPlotViewSaveRequest,
    RsmSavedPlotView,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import utc_now
from app.services.doe_response_surface_analysis import get_response_surface_analysis
from app.services.response_surface_designs import get_response_surface_design
from app.services.rsm_plot_builder import build_rsm_plot_bundle
from app.storage import factorial_analysis_assets as storage
from app.storage.metadata import (
    WorkspaceAssetStorageConflict,
    get_experiment_design_analysis_record,
)


def plot_source(settings: Settings, design_id: UUID, analysis_id: UUID) -> RsmPlotSource:
    analysis = get_response_surface_analysis(settings, design_id, analysis_id)
    return _source(settings, analysis)


def _source(settings: Settings, analysis: DoeResponseSurfaceAnalysisResponse) -> RsmPlotSource:
    record = get_experiment_design_analysis_record(
        settings.workspace_root, str(analysis.analysis_id)
    )
    if record is None:
        raise _error("doe_rsm_plot_source_changed")
    return RsmPlotSource(
        expected_result_sha256=record.result_sha256,
        response_revision_id=analysis.response_revision_id,
        response_revision_sha256=analysis.response_revision_sha256,
    )


def create_rsm_plot_view(
    settings: Settings, design_id: UUID, analysis_id: UUID, body: RsmPlotViewRequest
) -> RsmPlotViewResponse:
    analysis = get_response_surface_analysis(settings, design_id, analysis_id)
    source = _source(settings, analysis)
    if source != RsmPlotSource.model_validate(
        body.model_dump(include=set(RsmPlotSource.model_fields))
    ):
        raise _error("doe_rsm_plot_source_changed")
    basis = analysis.result.final_basis
    if basis is None:
        raise _error("doe_rsm_plot_legacy_basis_unavailable")
    design = get_response_surface_design(settings, design_id)
    try:
        bundle = build_rsm_plot_bundle(
            design,
            basis,
            body.settings,
            response_name=analysis.result.response.name,
            response_unit=analysis.result.response.unit,
        )
    except ValueError as exc:
        code = str(exc)
        if not code.startswith("doe_rsm_"):
            code = "doe_rsm_plot_invalid"
        raise _error(code) from exc
    digest = hashlib.sha256(_json(bundle.model_dump(mode="json"))).hexdigest()
    return RsmPlotViewResponse(
        **source.model_dump(),
        design_id=design_id,
        design_version_id=design.design_version_id,
        design_sha256=design.design_sha256,
        analysis_id=analysis_id,
        view_sha256=digest,
        bundle=bundle,
    )


def save_rsm_plot_view(
    settings: Settings, design_id: UUID, analysis_id: UUID, body: RsmPlotViewSaveRequest
) -> RsmSavedPlotView:
    # Re-evaluate the deterministic view from the verified final basis, never accept
    # client geometry. Expected hash ensures this is the view the user actually saw.
    view = create_rsm_plot_view(
        settings,
        design_id,
        analysis_id,
        RsmPlotViewRequest.model_validate(body.model_dump(exclude={"expected_view_sha256"})),
    )
    if view.view_sha256 != body.expected_view_sha256:
        raise _error("doe_rsm_plot_view_changed")
    content = _json(view.model_dump(mode="json"))
    asset_id, created = uuid4(), utc_now()
    digest = hashlib.sha256(content).hexdigest()
    record = storage.FactorialAnalysisAsset(
        str(asset_id),
        str(analysis_id),
        "plot_view",
        1,
        None,
        view.expected_result_sha256,
        digest,
        "application/json",
        len(content),
        created,
    )
    try:
        storage.insert_asset(settings.workspace_root, record, content)
    except WorkspaceAssetStorageConflict as exc:
        raise _error(exc.code) from exc
    return RsmSavedPlotView(asset_id=asset_id, sha256=digest, created_at=created, view=view)


def read_rsm_plot_view(
    settings: Settings,
    design_id: UUID,
    analysis_id: UUID,
    asset_id: UUID,
    expected_sha256: str | None = None,
) -> RsmSavedPlotView:
    analysis = get_response_surface_analysis(settings, design_id, analysis_id)
    source = _source(settings, analysis)
    try:
        asset = storage.get_asset(settings.workspace_root, str(analysis_id), str(asset_id))
    except WorkspaceAssetStorageConflict as exc:
        raise _error(exc.code) from exc
    if asset is None or asset[0].kind != "plot_view":
        raise _error("doe_rsm_plot_view_not_found", 404)
    record, content = asset
    if record.schema_version != 1:
        raise _error("doe_rsm_plot_view_schema_unsupported")
    try:
        view = RsmPlotViewResponse.model_validate_json(content)
    except ValidationError as exc:
        raise _error("doe_rsm_plot_view_invalid") from exc
    if (
        (expected_sha256 is not None and record.sha256 != expected_sha256)
        or record.source_analysis_sha256 != source.expected_result_sha256
        or view.analysis_id != analysis_id
        or view.design_id != design_id
        or view.design_version_id != analysis.design_version_id
        or view.design_sha256 != analysis.design_sha256
        or RsmPlotSource.model_validate(view.model_dump(include=set(RsmPlotSource.model_fields)))
        != source
        or view.view_sha256
        != hashlib.sha256(_json(view.bundle.model_dump(mode="json"))).hexdigest()
    ):
        raise _error("doe_rsm_plot_source_changed")
    return RsmSavedPlotView(
        asset_id=asset_id, sha256=record.sha256, created_at=record.created_at, view=view
    )


def list_rsm_plot_views(
    settings: Settings, design_id: UUID, analysis_id: UUID
) -> list[RsmPlotViewDescriptor]:
    plot_source(settings, design_id, analysis_id)
    return [
        RsmPlotViewDescriptor(
            asset_id=UUID(record.asset_id), sha256=record.sha256, created_at=record.created_at
        )
        for record in storage.list_assets(settings.workspace_root, str(analysis_id), "plot_view")
    ]


def delete_rsm_plot_view(
    settings: Settings, design_id: UUID, analysis_id: UUID, asset_id: UUID, expected_sha256: str
) -> None:
    read_rsm_plot_view(settings, design_id, analysis_id, asset_id, expected_sha256)
    try:
        storage.delete_asset(
            settings.workspace_root, str(analysis_id), str(asset_id), expected_sha256
        )
    except WorkspaceAssetStorageConflict as exc:
        raise _error(exc.code) from exc


def _json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _error(code: str, status_code: int = 409) -> ApiError:
    return ApiError(
        code=code,
        message="The stored RSM source or plot settings are not valid for this view.",
        status_code=status_code,
    )
