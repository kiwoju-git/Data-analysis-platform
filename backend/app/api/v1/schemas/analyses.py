from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalysisModuleId(str, Enum):
    EXPLORATION = "exploration"
    HYPOTHESIS = "hypothesis"
    CATEGORICAL = "categorical"
    REGRESSION = "regression"
    QUALITY = "quality"
    DOE = "doe"


class MethodAvailability(str, Enum):
    AVAILABLE = "available"
    PLANNED = "planned"
    DISABLED = "disabled"


class AnalysisExecutionMode(str, Enum):
    INLINE = "inline"
    JOB = "job"


class AnalysisRunState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"


class AnalysisModuleDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: AnalysisModuleId
    label_ko: str
    label_en: str
    order: int


class AnalysisMethodDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method_id: str
    method_version: str
    module_id: AnalysisModuleId
    label_ko: str
    label_en: str
    availability: MethodAvailability
    execution_mode: AnalysisExecutionMode
    requires_dataset: bool
    order: int
    disabled_reason: str | None = None


class AnalysisMethodListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modules: list[AnalysisModuleDescriptor]
    methods: list[AnalysisMethodDescriptor]


class AnalysisFilterSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression_version: int = Field(default=1, ge=1)
    conditions: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method_id: str = Field(min_length=1, max_length=120)
    method_version: str = Field(min_length=1, max_length=40)
    dataset_version_id: UUID | None = None
    filter_snapshot: AnalysisFilterSnapshot = Field(default_factory=AnalysisFilterSnapshot)
    roles: dict[str, str] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class AnalysisRunStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    method_id: str
    method_version: str
    dataset_version_id: UUID | None
    status: AnalysisRunState
    config_schema_version: int = Field(ge=1)
    result_available: bool
    artifact_count: int = Field(ge=0)
    stale: bool
    created_at: str
    updated_at: str
    completed_at: str | None


class AnalysisWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["info", "warning", "error"]
    message: str


class AnalysisProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method_id: str
    method_version: str
    dataset_version_id: UUID | None
    source_schema_hash: str | None = None
    app_version: str


class AnalysisResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    method_id: str
    method_version: str
    dataset_version_id: UUID | None
    status: Literal["succeeded", "failed", "cancelled"]
    warnings: list[AnalysisWarning]
    provenance: AnalysisProvenance
    result: dict[str, Any] | None = None
