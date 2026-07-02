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
    filter_snapshot_sha256: str | None = None
    row_snapshot_sha256: str | None = None
    row_count_total: int | None = Field(default=None, ge=0)
    row_count_included: int | None = Field(default=None, ge=0)
    app_version: str
    python_version: str | None = None
    platform: str | None = None
    build_commit: str | None = None
    package_versions: dict[str, str] | None = None


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


class GageRrPreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version_id: UUID
    measurement_column_id: str = Field(min_length=1)
    part_column_id: str = Field(min_length=1)
    operator_column_id: str = Field(min_length=1)
    replicate_column_id: str = Field(min_length=1)
    missing_policy: Literal["complete_case"] = "complete_case"


class GageRrPreflightColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: str
    column_index: int = Field(ge=0)
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None = None


class GageRrPreflightSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_total: int = Field(ge=0)
    n_used: int = Field(ge=0)
    n_excluded: int = Field(ge=0)
    n_excluded_missing_measurement: int = Field(ge=0)
    n_excluded_non_numeric_measurement: int = Field(ge=0)
    n_excluded_missing_part: int = Field(ge=0)
    n_excluded_missing_operator: int = Field(ge=0)
    n_excluded_missing_replicate: int = Field(ge=0)
    n_excluded_missing_identifier: int = Field(ge=0)


class GageRrCellReplicateCount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replicate_count: int = Field(ge=0)
    cell_count: int = Field(ge=0)


class GageRrPreflightDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_type: Literal["crossed"]
    balanced: bool
    ready_for_anova: bool
    part_count: int = Field(ge=0)
    operator_count: int = Field(ge=0)
    replicate_level_count: int = Field(ge=0)
    expected_cell_count: int = Field(ge=0)
    observed_cell_count: int = Field(ge=0)
    missing_cell_count: int = Field(ge=0)
    min_replicates_per_cell: int = Field(ge=0)
    max_replicates_per_cell: int = Field(ge=0)
    expected_replicates_per_cell: int | None = Field(default=None, ge=0)
    replicate_set_consistent: bool
    duplicate_replicates_per_cell: int = Field(ge=0)
    cell_replicate_count_distribution: list[GageRrCellReplicateCount]


class GageRrPreflightIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    count: int | None = Field(default=None, ge=0)


class GageRrPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    method_id: Literal["quality.gage_rr"]
    preflight_type: Literal["balanced_crossed_anova"]
    dataset_version_id: UUID
    schema_hash: str
    row_count_total: int = Field(ge=0)
    summary_type: Literal["gage_rr_preflight"]
    method: Literal["balanced_crossed_anova_preflight"]
    missing_policy: Literal["complete_case"]
    columns: dict[
        Literal["measurement", "part", "operator", "replicate"],
        GageRrPreflightColumn,
    ]
    sample: GageRrPreflightSample
    design: GageRrPreflightDesign
    issues: list[GageRrPreflightIssue]
    next_step: Literal["ready_for_balanced_crossed_anova", "fix_design_before_gage_rr"]


class RegressionModelManifestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: UUID
    analysis_id: UUID
    dataset_version_id: UUID
    method_id: str
    method_version: str
    schema_hash: str
    manifest_sha256: str
    created_at: str
    app_version: str
    manifest: dict[str, Any]


class RegressionPredictionPreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version_id: UUID


class RegressionPredictionPreflightIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    source_column_id: str | None = None
    target_column_id: str | None = None
    display_name: str | None = None
    count: int | None = Field(default=None, ge=0)


class RegressionPredictionColumnMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_column_id: str
    display_name: str
    predictor_kind: Literal["numeric", "categorical"]
    target_column_id: str | None
    match_type: Literal["column_id", "display_name", "missing", "ambiguous"]
    status: Literal["ok", "warning", "error"]


class RegressionPredictionNumericCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_column_id: str
    target_column_id: str
    display_name: str
    n_valid: int = Field(ge=0)
    n_missing: int = Field(ge=0)
    n_non_numeric: int = Field(ge=0)
    n_below_training_range: int = Field(ge=0)
    n_above_training_range: int = Field(ge=0)


class RegressionPredictionCategoricalCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_column_id: str
    target_column_id: str
    display_name: str
    training_level_count: int = Field(ge=0)
    n_valid: int = Field(ge=0)
    n_missing: int = Field(ge=0)
    n_unseen_level: int = Field(ge=0)


class RegressionPredictionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: UUID
    analysis_id: UUID
    source_dataset_version_id: UUID
    target_dataset_version_id: UUID
    model_manifest_sha256: str
    source_schema_hash: str
    target_schema_hash: str
    schema_hash_match: bool
    row_count_total: int = Field(ge=0)
    row_count_usable: int = Field(ge=0)
    prediction_ready: bool
    required_columns: list[RegressionPredictionColumnMapping]
    numeric_checks: list[RegressionPredictionNumericCheck]
    categorical_checks: list[RegressionPredictionCategoricalCheck]
    issues: list[RegressionPredictionPreflightIssue]


class RegressionPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version_id: UUID
    confidence_level: float = Field(default=0.95, gt=0.0, lt=1.0)
    missing_policy: Literal["complete_case"] = "complete_case"
    include_intervals: bool = True


class RegressionPredictionWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    count: int | None = Field(default=None, ge=0)


class RegressionPredictionInterval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["t"]
    level: float = Field(gt=0.0, lt=1.0)
    lower: float
    upper: float


class RegressionPredictionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_index: int = Field(ge=0)
    predicted_mean: float
    mean_confidence_interval: RegressionPredictionInterval | None = None
    prediction_interval: RegressionPredictionInterval | None = None
    warnings: list[str] = Field(default_factory=list)


class RegressionPredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_id: UUID
    model_id: UUID
    analysis_id: UUID
    source_dataset_version_id: UUID
    target_dataset_version_id: UUID
    model_manifest_sha256: str
    target_schema_hash: str
    row_count_total: int = Field(ge=0)
    row_count_predicted: int = Field(ge=0)
    row_count_excluded: int = Field(ge=0)
    row_count_omitted: int = Field(ge=0)
    row_limit: int = Field(ge=1)
    truncated: bool
    confidence_level: float = Field(gt=0.0, lt=1.0)
    warnings: list[RegressionPredictionWarning]
    provenance: dict[str, Any]
    columns: list[RegressionPredictionColumnMapping]
    rows: list[RegressionPredictionRow]
