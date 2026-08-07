from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    metadata_updated_at: str | None
    dependency_count: int = Field(ge=0)
    open_target: WorkspaceAssetOpenTarget


class WorkspaceAssetCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[WorkspaceAssetDescriptor]


EditableWorkspaceAssetType = Literal["analysis_run", "doe_design", "bayesian_study"]


class WorkspaceAssetMetadataUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_label: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    pinned: bool | None = None
    expected_metadata_updated_at: str | None = None

    @field_validator("user_label", "note", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
            raise ValueError("asset_metadata_control_character")
        return normalized or None


class WorkspaceAssetMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_type: EditableWorkspaceAssetType
    asset_id: str
    user_label: str | None
    note: str | None
    pinned: bool
    metadata_updated_at: str
