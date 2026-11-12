"""Versioned measured-data receipt, independent of generated-design receipts."""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.analyses import AnalysisFilterSnapshot

ImportHash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class DatasetImportSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: UUID
    dataset_version_id: UUID
    schema_hash: ImportHash
    canonical_sha256: ImportHash
    raw_sha256: ImportHash
    filter_sha256: ImportHash


class DatasetImportCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_total: int = Field(ge=0)
    n_filtered: int = Field(ge=0)
    n_missing: int = Field(ge=0)
    n_used: int = Field(ge=1, le=200)
    unique_coordinate_count: int = Field(ge=1, le=200)
    repeated_coordinate_count: int = Field(ge=0, le=199)
    conflicting_coordinate_count: int = Field(ge=0, le=100)
    warnings: list[str]


class DatasetImportPreflightResponse(DatasetImportCounts):
    schema_version: Literal[1] = 1
    source: DatasetImportSource
    preflight_sha256: ImportHash


class DatasetImportedInitialDesign(DatasetImportCounts):
    policy: Literal["dataset_observations_v1"] = "dataset_observations_v1"
    import_schema_version: Literal[1] = 1
    requested_size: int = Field(ge=1, le=200)
    generated_size: int = Field(ge=1, le=200)
    source: DatasetImportSource
    source_row_indices: list[int] = Field(min_length=1, max_length=200)
    factor_columns: dict[str, str]
    response_columns: dict[str, str]
    missing_policy: Literal["reject", "complete_case"]
    filter_snapshot: AnalysisFilterSnapshot
    preflight_sha256: ImportHash
    observations_sha256: ImportHash
    request_id: UUID
    request_sha256: ImportHash
    runtime_provenance: dict[str, Any]
