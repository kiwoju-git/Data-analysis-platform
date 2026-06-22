from enum import Enum
from typing import TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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


class DatasetReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: DatasetId


class AnalysisReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: AnalysisId


class ResultReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: ResultId
