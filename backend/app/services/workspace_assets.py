from typing import cast

from app.api.v1.schemas.assets import (
    WorkspaceAssetCatalogResponse,
    WorkspaceAssetDescriptor,
    WorkspaceAssetOpenTarget,
    WorkspaceAssetType,
)
from app.core.config import Settings
from app.storage.metadata import (
    WorkspaceAssetCatalogRecord,
    list_workspace_asset_catalog_records,
)


def list_workspace_assets(
    settings: Settings,
    *,
    category: str | None,
    method_id: str | None,
    status_filter: str | None,
    pinned: bool | None,
    search: str | None,
    sort: str,
    offset: int,
    limit: int,
) -> WorkspaceAssetCatalogResponse:
    total, records = list_workspace_asset_catalog_records(
        settings.workspace_root,
        category=category,
        method_id=method_id.strip() if method_id and method_id.strip() else None,
        status_filter=(status_filter.strip() if status_filter and status_filter.strip() else None),
        pinned=pinned,
        search=search.strip() if search and search.strip() else None,
        sort=sort,
        offset=offset,
        limit=limit,
    )
    return WorkspaceAssetCatalogResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[_descriptor(record) for record in records],
    )


def _descriptor(record: WorkspaceAssetCatalogRecord) -> WorkspaceAssetDescriptor:
    return WorkspaceAssetDescriptor(
        asset_id=record.asset_id,
        asset_type=cast(WorkspaceAssetType, record.asset_type),
        subtype=record.subtype,
        method_id=record.method_id,
        display_name=record.display_name,
        secondary_text=record.secondary_text,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        pinned=record.pinned,
        note=record.note,
        dependency_count=record.dependency_count,
        open_target=_open_target(record),
    )


def _open_target(record: WorkspaceAssetCatalogRecord) -> WorkspaceAssetOpenTarget:
    if record.asset_type == "dataset_version":
        return WorkspaceAssetOpenTarget(
            path=f"/datasets?version_id={record.asset_id}", label="데이터셋에서 열기"
        )
    if record.asset_type == "analysis_run":
        return WorkspaceAssetOpenTarget(
            path=f"/reports?analysis_id={record.asset_id}", label="리포트에서 열기"
        )
    if record.asset_type == "regression_model":
        return WorkspaceAssetOpenTarget(
            path=f"/analysis/regression/regression.linear_model?model_id={record.asset_id}",
            label="예측 입력 열기",
        )
    if record.asset_type == "bayesian_study":
        return WorkspaceAssetOpenTarget(
            path=("/analysis/doe/doe.bayesian_optimization" f"?study_id={record.asset_id}"),
            label="Bayesian에서 열기",
        )
    method_path = {
        "doe.factorial_design": "doe.factorial_design",
        "doe.general_factorial_design": "doe.factorial_design",
        "doe.latin_hypercube": "doe.latin_hypercube",
        "doe.response_surface": "doe.response_surface",
    }.get(record.method_id or "", "doe.factorial_design")
    design_kind = "general" if record.method_id == "doe.general_factorial_design" else "two_level"
    return WorkspaceAssetOpenTarget(
        path=(
            f"/analysis/doe/{method_path}?design_id={record.asset_id}" f"&design_kind={design_kind}"
        ),
        label="실험 설계에서 열기",
    )
