from enum import Enum
from typing import TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DatasetId: TypeAlias = UUID
AnalysisId: TypeAlias = UUID
ModelId: TypeAlias = UUID
ReportId: TypeAlias = UUID
ResultId: TypeAlias = UUID
JobId: TypeAlias = UUID


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"


class JobReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: JobId
    state: JobState


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: JobId
    analysis_id: AnalysisId | None
    job_type: str
    state: JobState
    progress: float = Field(ge=0, le=1)
    cancel_requested: bool
    error_code: str | None
    created_at: str
    updated_at: str
    completed_at: str | None


class DatasetReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: DatasetId


class AnalysisReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: AnalysisId


class ResultReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: ResultId


class WorkspaceSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visible_dataset_version_count: int = Field(ge=0)
    archived_dataset_version_count: int = Field(ge=0)
    regression_model_count: int = Field(ge=0)
    stored_analysis_count: int = Field(ge=0)
    export_report_count: int = Field(ge=0)
