from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WorkspaceAssetType = Literal[
    "dataset_version",
    "analysis_run",
    "regression_model",
    "doe_design",
    "bayesian_study",
]


class WorkspaceAssetOpenTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    label: str


class WorkspaceAssetDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    asset_type: WorkspaceAssetType
    subtype: str
    method_id: str | None
    display_name: str
    secondary_text: str
    status: str
    created_at: str
    updated_at: str
    pinned: bool
    note: str | None
    dependency_count: int = Field(ge=0)
    open_target: WorkspaceAssetOpenTarget


class WorkspaceAssetCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[WorkspaceAssetDescriptor]
