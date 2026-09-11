from __future__ import annotations

import hashlib
from dataclasses import asdict
from uuid import UUID, uuid4

from app.api.v1.schemas.doe_model_workflow import (
    DoeAnalysisAssetDeleteRequest,
    DoeAnalysisAssetDeleteResponse,
    DoeAnalysisAssetDescriptor,
    DoeAnalysisAssetList,
    DoeAnalysisDeleteRequest,
    DoeAnalysisDeletionPreflight,
    DoeAnalysisHtmlExportRequest,
)
from app.core.config import Settings
from app.services.analysis_run_execution import utc_now
from app.services.factorial_analysis_report import render_factorial_analysis_report
from app.services.factorial_prediction import (
    get_factorial_prediction,
    load_factorial_model_source,
    workflow_error,
)
from app.storage import factorial_analysis_assets as storage
from app.storage.metadata import WorkspaceAssetStorageConflict


def create_factorial_html_report(
    settings: Settings, design_id: UUID, analysis_id: UUID, body: DoeAnalysisHtmlExportRequest
) -> DoeAnalysisAssetDescriptor:
    source = load_factorial_model_source(settings, design_id, analysis_id, require_model=False)
    predictions = storage.list_assets(settings.workspace_root, str(analysis_id), "prediction")
    latest_prediction = (
        get_factorial_prediction(settings, design_id, analysis_id, UUID(predictions[0].asset_id))
        if predictions
        else None
    )
    content = render_factorial_analysis_report(source, body.locale, latest_prediction)
    record = storage.FactorialAnalysisAsset(
        str(uuid4()),
        str(analysis_id),
        "html_report",
        1,
        body.locale,
        source.sha256,
        hashlib.sha256(content).hexdigest(),
        "text/html",
        len(content),
        utc_now(),
    )
    try:
        storage.insert_asset(settings.workspace_root, record, content)
    except WorkspaceAssetStorageConflict as exc:
        raise workflow_error(exc.code) from exc
    return DoeAnalysisAssetDescriptor.model_validate(asdict(record))


def list_factorial_analysis_assets(
    settings: Settings, design_id: UUID, analysis_id: UUID, kind: storage.AssetKind | None = None
) -> DoeAnalysisAssetList:
    load_factorial_model_source(settings, design_id, analysis_id, require_model=False)
    return DoeAnalysisAssetList(
        analysis_id=analysis_id,
        items=[
            DoeAnalysisAssetDescriptor.model_validate(asdict(record))
            for record in storage.list_assets(settings.workspace_root, str(analysis_id), kind)
        ],
    )


def download_factorial_analysis_asset(
    settings: Settings, design_id: UUID, analysis_id: UUID, asset_id: UUID
) -> tuple[DoeAnalysisAssetDescriptor, bytes]:
    source = load_factorial_model_source(settings, design_id, analysis_id, require_model=False)
    try:
        stored = storage.get_asset(settings.workspace_root, str(analysis_id), str(asset_id))
    except WorkspaceAssetStorageConflict as exc:
        raise workflow_error(exc.code) from exc
    if stored is None:
        raise workflow_error("doe_analysis_asset_not_found", 404)
    record, content = stored
    if record.source_analysis_sha256 != source.sha256:
        raise workflow_error("doe_factorial_prediction_source_changed")
    return DoeAnalysisAssetDescriptor.model_validate(asdict(record)), content


def factorial_analysis_asset_deletion_preflight(
    settings: Settings, design_id: UUID, analysis_id: UUID, asset_id: UUID
) -> DoeAnalysisAssetDescriptor:
    assets = list_factorial_analysis_assets(settings, design_id, analysis_id)
    item = next((item for item in assets.items if item.asset_id == asset_id), None)
    if item is None:
        raise workflow_error("doe_analysis_asset_not_found", 404)
    return item


def delete_factorial_analysis_asset(
    settings: Settings,
    design_id: UUID,
    analysis_id: UUID,
    asset_id: UUID,
    body: DoeAnalysisAssetDeleteRequest,
) -> DoeAnalysisAssetDeleteResponse:
    descriptor = factorial_analysis_asset_deletion_preflight(
        settings, design_id, analysis_id, asset_id
    )
    if body.confirmation_asset_id != asset_id or body.expected_sha256 != descriptor.sha256:
        raise workflow_error("doe_analysis_asset_deletion_conflict")
    try:
        storage.delete_asset(
            settings.workspace_root, str(analysis_id), str(asset_id), body.expected_sha256
        )
    except WorkspaceAssetStorageConflict as exc:
        raise workflow_error(exc.code) from exc
    return DoeAnalysisAssetDeleteResponse(asset_id=asset_id)


def factorial_analysis_deletion_preflight(
    settings: Settings, design_id: UUID, analysis_id: UUID
) -> DoeAnalysisDeletionPreflight:
    load_factorial_model_source(settings, design_id, analysis_id, require_model=False)
    snapshot = storage.analysis_deletion_snapshot(settings.workspace_root, str(analysis_id))
    if snapshot is None:
        raise workflow_error("doe_factorial_analysis_not_found", 404)
    return DoeAnalysisDeletionPreflight(
        analysis_id=analysis_id,
        deletion_manifest_sha256=snapshot[0],
        prediction_count=snapshot[1],
        report_count=snapshot[2],
    )


def delete_factorial_analysis(
    settings: Settings, design_id: UUID, analysis_id: UUID, body: DoeAnalysisDeleteRequest
) -> DoeAnalysisDeletionPreflight:
    snapshot = factorial_analysis_deletion_preflight(settings, design_id, analysis_id)
    if (
        body.confirmation_analysis_id != analysis_id
        or body.expected_deletion_manifest_sha256 != snapshot.deletion_manifest_sha256
    ):
        raise workflow_error("doe_analysis_deletion_conflict")
    try:
        storage.delete_analysis(
            settings.workspace_root, str(analysis_id), body.expected_deletion_manifest_sha256
        )
    except WorkspaceAssetStorageConflict as exc:
        raise workflow_error(exc.code) from exc
    return snapshot
