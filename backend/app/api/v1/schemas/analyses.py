from enum import Enum
from math import isfinite
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    DEDICATED = "dedicated"


class AnalysisSourcePrerequisite(str, Enum):
    REGRESSION_MODEL = "regression_model"
    RESPONSE_SURFACE_ANALYSIS = "response_surface_analysis"


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
    source_prerequisite: AnalysisSourcePrerequisite | None = None
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


class DescriptiveOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_ids: list[str] = Field(min_length=1)
    missing_policy: Literal["available_case_by_column"] = "available_case_by_column"

    @field_validator("column_ids", mode="before")
    @classmethod
    def require_column_ids(cls, value: object) -> object:
        if not isinstance(value, list) or not value:
            raise ValueError("must be a non-empty list")
        if any(not isinstance(column_id, str) or not column_id for column_id in value):
            raise ValueError("must contain non-empty string column IDs")
        return value


class GraphicalSummaryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_ids: list[str] = Field(min_length=1)
    histogram_bin_count: int | None = None
    point_limit: int = 1000

    @field_validator("column_ids", mode="before")
    @classmethod
    def require_column_ids(cls, value: object) -> object:
        if not isinstance(value, list) or not value:
            raise ValueError("must be a non-empty list")
        if any(not isinstance(column_id, str) or not column_id for column_id in value):
            raise ValueError("must contain non-empty string column IDs")
        return value

    @field_validator("histogram_bin_count", mode="before")
    @classmethod
    def require_optional_integer(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value

    @field_validator("point_limit", mode="before")
    @classmethod
    def require_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value


class NormalityOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_ids: list[str] = Field(min_length=1)
    group_column_id: str | None = None
    alpha: float = 0.05
    include_qq_points: bool = True
    qq_point_limit: int = 1000
    missing_policy: str = "available_case_by_column"

    @field_validator("column_ids", mode="before")
    @classmethod
    def require_column_ids(cls, value: object) -> object:
        if not isinstance(value, list) or not value:
            raise ValueError("must be a non-empty list")
        if any(not isinstance(column_id, str) or not column_id for column_id in value):
            raise ValueError("must contain non-empty string column IDs")
        return value

    @field_validator("group_column_id", mode="before")
    @classmethod
    def require_optional_string(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("must be a string")
        return value

    @field_validator("alpha", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value

    @field_validator("include_qq_points", mode="before")
    @classmethod
    def require_boolean(cls, value: object) -> object:
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return value

    @field_validator("qq_point_limit", mode="before")
    @classmethod
    def require_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value


class EqualVariancesOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    group_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    missing_policy: str = "complete_case"

    @field_validator("response_column_id", "group_column_id", mode="before")
    @classmethod
    def require_column_id(cls, value: object) -> object:
        if not isinstance(value, str) or not value:
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("alpha", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class OneSampleTOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    confidence_level: float = 0.95
    alternative: Literal["two_sided", "greater", "less"] = "two_sided"
    null_mean: float = 0.0
    missing_policy: str = "complete_case"

    @field_validator("alpha", "confidence_level", "null_mean", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class PairedTOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before_column_id: str = Field(min_length=1)
    after_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    confidence_level: float = 0.95
    alternative: Literal["two_sided", "greater", "less"] = "two_sided"
    null_difference: float = 0.0
    missing_policy: str = "complete_pair"

    @field_validator("alpha", "confidence_level", "null_difference", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class TwoSampleTOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    group_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    confidence_level: float = 0.95
    alternative: Literal["two_sided", "greater", "less"] = "two_sided"
    variance_assumption: Literal["welch", "pooled"] = "welch"
    null_difference: float = 0.0
    missing_policy: str = "complete_case"

    @field_validator("alpha", "confidence_level", "null_difference", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class EquivalenceTostOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str | None = Field(default=None, min_length=1)
    design: str = Field(min_length=1)
    reference_mean: float
    lower_bound: float
    upper_bound: float
    alpha: float = 0.05
    missing_policy: str = "complete_case"

    @field_validator("reference_mean", "lower_bound", "upper_bound", "alpha", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class OneSampleWilcoxonOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    alternative: Literal["two_sided", "greater", "less"] = "two_sided"
    null_location: float = 0.0
    method: Literal["auto", "exact", "asymptotic"] = "auto"
    zero_method: Literal["wilcox", "pratt", "zsplit"] = "wilcox"
    missing_policy: str = "complete_case"

    @field_validator("alpha", "null_location", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class MannWhitneyOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    group_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    alternative: Literal["two_sided", "greater", "less"] = "two_sided"
    method: Literal["auto", "exact", "asymptotic"] = "auto"
    missing_policy: str = "complete_case"

    @field_validator("alpha", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class LinearModelInteractionTermOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_column_id: str = Field(min_length=1)
    right_column_id: str = Field(min_length=1)


class PearsonOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x_column_id: str = Field(min_length=1)
    y_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    confidence_level: float = 0.95
    missing_policy: Literal["complete_case"] = "complete_case"

    @field_validator("x_column_id", "y_column_id", mode="before")
    @classmethod
    def require_column_id(cls, value: object) -> object:
        if not isinstance(value, str) or not value:
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("alpha", "confidence_level", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class XyCorrelationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x_column_ids: list[str] = Field(min_length=1)
    y_column_ids: list[str] = Field(min_length=1)
    alpha: float = 0.05
    confidence_level: float = 0.95
    missing_policy: Literal["pairwise_complete_case"] = "pairwise_complete_case"

    @field_validator("x_column_ids", "y_column_ids", mode="before")
    @classmethod
    def require_column_ids(cls, value: object) -> object:
        if not isinstance(value, list) or not value:
            raise ValueError("must be a non-empty list")
        if any(not isinstance(column_id, str) or not column_id for column_id in value):
            raise ValueError("must contain non-empty string column IDs")
        return value

    @field_validator("alpha", "confidence_level", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class LinearModelOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    predictor_column_ids: list[str] = Field(min_length=1)
    quadratic_terms: list[str] | None = None
    interaction_terms: list[LinearModelInteractionTermOption] | None = None
    alpha: float = 0.05
    confidence_level: float = 0.95
    missing_policy: str = "complete_case"
    include_intercept: bool = True
    covariance_type: str = "standard"

    @field_validator("alpha", "confidence_level", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value

    @field_validator("include_intercept", mode="before")
    @classmethod
    def require_boolean(cls, value: object) -> object:
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return value


class GageRrOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measurement_column_id: str = Field(min_length=1)
    part_column_id: str = Field(min_length=1)
    operator_column_id: str = Field(min_length=1)
    replicate_column_id: str = Field(min_length=1)
    missing_policy: str = "complete_case"


class IndividualsChartOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value_column_id: str = Field(min_length=1)
    order_column_id: str | None = None
    missing_policy: str = "complete_case"
    same_side_min_length: int = 9
    trend_min_length: int = 6
    point_limit: int = 1000

    @field_validator("value_column_id", mode="before")
    @classmethod
    def require_column_id(cls, value: object) -> object:
        if not isinstance(value, str) or not value:
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("order_column_id", mode="before")
    @classmethod
    def require_optional_string(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("must be a string")
        return value

    @field_validator("same_side_min_length", "trend_min_length", "point_limit", mode="before")
    @classmethod
    def require_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value


class AttributeControlChartOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: Literal["phase_1", "phase_2"] = "phase_1"
    limit_set_id: UUID | None = None
    chart_type: Literal["p", "np", "c", "u"]
    count_definition: Literal["defectives", "defects"]
    count_column_id: str = Field(min_length=1)
    denominator_column_id: str | None = None
    constant_opportunity_confirmed: bool = False
    missing_policy: Literal["complete_case"] = "complete_case"
    point_limit: int = 1000

    @field_validator("count_column_id", mode="before")
    @classmethod
    def require_count_column_id(cls, value: object) -> object:
        if not isinstance(value, str) or not value:
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("denominator_column_id", mode="before")
    @classmethod
    def require_optional_denominator_column_id(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("constant_opportunity_confirmed", mode="before")
    @classmethod
    def require_constant_opportunity_boolean(cls, value: object) -> object:
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return value

    @field_validator("point_limit", mode="before")
    @classmethod
    def require_point_limit_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value

    @model_validator(mode="after")
    def validate_phase_dependency(self) -> "AttributeControlChartOptions":
        if self.phase == "phase_1" and self.limit_set_id is not None:
            raise ValueError("phase_1 must not include limit_set_id")
        if self.phase == "phase_2" and self.limit_set_id is None:
            raise ValueError("phase_2 requires limit_set_id")
        return self


class SubgroupChartOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value_column_id: str = Field(min_length=1)
    subgroup_column_id: str = Field(min_length=1)
    chart_type: str = "xbar_r"
    missing_policy: str = "complete_case"
    point_limit: int = 1000

    @field_validator("value_column_id", "subgroup_column_id", mode="before")
    @classmethod
    def require_column_id(cls, value: object) -> object:
        if not isinstance(value, str) or not value:
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("point_limit", mode="before")
    @classmethod
    def require_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value


class GageRunChartOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measurement_column_id: str = Field(min_length=1)
    part_column_id: str = Field(min_length=1)
    operator_column_id: str = Field(min_length=1)
    replicate_column_id: str = Field(min_length=1)
    order_column_id: str | None = None
    missing_policy: str = "complete_case"
    point_limit: int = 1000

    @field_validator(
        "measurement_column_id",
        "part_column_id",
        "operator_column_id",
        "replicate_column_id",
        mode="before",
    )
    @classmethod
    def require_column_id(cls, value: object) -> object:
        if not isinstance(value, str) or not value:
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("order_column_id", mode="before")
    @classmethod
    def require_optional_string(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("must be a string")
        return value

    @field_validator("point_limit", mode="before")
    @classmethod
    def require_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value


class OneProportionOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    event_level: str = Field(min_length=1)
    null_proportion: float = 0.5
    alpha: float = 0.05
    confidence_level: float = 0.95
    alternative: Literal["two_sided", "greater", "less"] = "two_sided"
    ci_method: Literal["wilson", "clopper_pearson"] = "wilson"
    missing_policy: str = "complete_case"

    @field_validator("null_proportion", "alpha", "confidence_level", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class TwoProportionOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    group_column_id: str = Field(min_length=1)
    event_level: str = Field(min_length=1)
    alpha: float = 0.05
    confidence_level: float = 0.95
    alternative: Literal["two_sided", "greater", "less"] = "two_sided"
    missing_policy: str = "complete_case"

    @field_validator("alpha", "confidence_level", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class ChiSquareAssociationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_column_id: str = Field(min_length=1)
    column_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    missing_policy: str = "complete_case"

    @field_validator("alpha", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class CapabilityOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value_column_id: str = Field(min_length=1)
    lsl: float | None = None
    usl: float | None = None
    target: float | None = None
    missing_policy: str = "complete_case"
    histogram_bin_limit: int = 30

    @field_validator("lsl", "usl", "target", mode="before")
    @classmethod
    def require_optional_finite_number(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value

    @field_validator("histogram_bin_limit", mode="before")
    @classmethod
    def require_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value


class OneWayAnovaOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    group_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    confidence_level: float = 0.95
    anova_type: str = "standard"
    posthoc_method: str = "tukey_kramer"
    posthoc_policy: str = "after_significant"
    missing_policy: str = "complete_case"

    @field_validator("alpha", "confidence_level", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class KruskalWallisOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_column_id: str = Field(min_length=1)
    group_column_id: str = Field(min_length=1)
    alpha: float = 0.05
    posthoc_method: str = "dunn_holm"
    posthoc_policy: str = "after_significant"
    missing_policy: str = "complete_case"

    @field_validator("alpha", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


class RunChartOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value_column_id: str = Field(min_length=1)
    order_column_id: str | None = None
    center_method: str = "median"
    missing_policy: str = "complete_case"
    trend_min_length: int = 6
    oscillation_min_length: int = 14
    runs_test_alpha: float = 0.05
    point_limit: int = 1000

    @field_validator("trend_min_length", "oscillation_min_length", "point_limit", mode="before")
    @classmethod
    def require_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value

    @field_validator("runs_test_alpha", mode="before")
    @classmethod
    def require_finite_number(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a finite number")
        if not isfinite(float(value)):
            raise ValueError("must be a finite number")
        return value


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


class AnalysisRunListItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    method_id: str
    method_version: str
    dataset_version_id: UUID | None
    status: AnalysisRunState
    stale: bool
    result_available: bool
    artifact_count: int = Field(ge=0)
    created_at: str
    updated_at: str
    completed_at: str | None


class AnalysisRunListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version_id: UUID | None
    method_id: str | None = None
    status: AnalysisRunState | None = None
    stale: bool | None = None
    result_available: bool | None = None
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    has_more: bool
    runs: list[AnalysisRunListItemResponse]


class AnalysisRunDeletionCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_run_count: Literal[1]
    analysis_artifact_count: int = Field(ge=0)
    result_file_count: int = Field(ge=0, le=1)
    artifact_file_count: int = Field(ge=0)
    export_file_count: int = Field(ge=0)
    total_file_count: int = Field(ge=0)
    file_bytes: int = Field(ge=0)
    metadata_record_count: int = Field(ge=1)
    regression_model_count: int = Field(ge=0)
    regression_prediction_count: int = Field(ge=0)
    attribute_control_limit_set_count: int = Field(ge=0)
    job_reference_count: int = Field(ge=0)


class AnalysisRunDeletionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_schema_version: Literal[1]
    analysis_id: UUID
    method_id: str
    method_version: str
    status: AnalysisRunState
    stale: bool
    deletion_ready: bool
    blockers: list[str]
    counts: AnalysisRunDeletionCounts
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AnalysisRunDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_analysis_id: UUID
    expected_deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AnalysisRunDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deletion_schema_version: Literal[1]
    analysis_id: UUID
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deleted_at: str
    deleted_counts: AnalysisRunDeletionCounts
    cleanup_status: Literal["deleted", "quarantined_pending_cleanup"]


class AnalysisRunComparisonSideResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    method_id: str
    method_version: str
    dataset_version_id: UUID | None
    status: Literal["succeeded", "failed", "cancelled"]
    stale: bool
    result_sha256: str = Field(min_length=64, max_length=64)
    warning_count: int = Field(ge=0)
    summary_type: str | None = None
    row_count_total: int | None = Field(default=None, ge=0)
    row_count_included: int | None = Field(default=None, ge=0)
    source_schema_hash: str | None = None
    filter_snapshot_sha256: str | None = None
    row_snapshot_sha256: str | None = None
    created_at: str
    completed_at: str | None


class AnalysisRunComparisonCompatibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    same_method_id: bool
    same_method_version: bool
    same_dataset_version_id: bool
    same_summary_type: bool


class AnalysisRunComparisonDifference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    left: str | int | bool | None
    right: str | int | bool | None


class DescriptiveMetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    left: int | float | None
    right: int | float | None
    delta: float | None


class DescriptiveColumnComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: str
    display_name: str
    metrics: list[DescriptiveMetricComparison]


class DescriptiveStatisticsComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_type: Literal["descriptive_statistics"]
    columns: list[DescriptiveColumnComparison]
    left_only_column_ids: list[str]
    right_only_column_ids: list[str]


class OneSampleTMetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    left: int | float | None
    right: int | float | None
    delta: float | None


class OneSampleTSettingComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setting: str
    left: str | int | float | bool | None
    right: str | int | float | bool | None
    same: bool


class OneSampleTTestComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_type: Literal["one_sample_t_test"]
    left_response_column_id: str | None
    right_response_column_id: str | None
    response_display_name: str | None
    same_response_column: bool
    settings: list[OneSampleTSettingComparison]
    metrics: list[OneSampleTMetricComparison]


class TwoSampleTMetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    left: int | float | None
    right: int | float | None
    delta: float | None


class TwoSampleTSettingComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setting: str
    left: str | int | float | bool | None
    right: str | int | float | bool | None
    same: bool


class TwoSampleTTestComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_type: Literal["two_sample_t_test"]
    left_response_column_id: str | None
    right_response_column_id: str | None
    response_display_name: str | None
    same_response_column: bool
    left_group_column_id: str | None
    right_group_column_id: str | None
    group_display_name: str | None
    same_group_column: bool
    same_group_label_set: bool
    same_group_label_order: bool
    settings: list[TwoSampleTSettingComparison]
    metrics: list[TwoSampleTMetricComparison]


class PairedTMetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    left: int | float | None
    right: int | float | None
    delta: float | None


class PairedTSettingComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setting: str
    left: str | int | float | bool | None
    right: str | int | float | bool | None
    same: bool


class PairedTTestComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_type: Literal["paired_t_test"]
    left_before_column_id: str | None
    right_before_column_id: str | None
    before_display_name: str | None
    same_before_column: bool
    left_after_column_id: str | None
    right_after_column_id: str | None
    after_display_name: str | None
    same_after_column: bool
    settings: list[PairedTSettingComparison]
    metrics: list[PairedTMetricComparison]


class EquivalenceTostMetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    left: int | float | None
    right: int | float | None
    delta: float | None


class EquivalenceTostSettingComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setting: str
    left: str | int | float | bool | None
    right: str | int | float | bool | None
    same: bool


class EquivalenceTostComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_type: Literal["equivalence_tost"]
    left_response_column_id: str | None
    right_response_column_id: str | None
    response_display_name: str | None
    same_response_column: bool
    settings: list[EquivalenceTostSettingComparison]
    metrics: list[EquivalenceTostMetricComparison]


class OneWayAnovaMetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    left: int | float | None
    right: int | float | None
    delta: float | None


class OneWayAnovaSettingComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setting: str
    left: str | int | float | bool | None
    right: str | int | float | bool | None
    same: bool


class OneWayAnovaComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_type: Literal["one_way_anova"]
    left_response_column_id: str | None
    right_response_column_id: str | None
    response_display_name: str | None
    same_response_column: bool
    left_group_column_id: str | None
    right_group_column_id: str | None
    group_display_name: str | None
    same_group_column: bool
    same_group_label_set: bool
    same_group_label_order: bool
    settings: list[OneWayAnovaSettingComparison]
    metrics: list[OneWayAnovaMetricComparison]


class KruskalWallisMetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    left: int | float | None
    right: int | float | None
    delta: float | None


class KruskalWallisSettingComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setting: str
    left: str | int | float | bool | None
    right: str | int | float | bool | None
    same: bool


class KruskalWallisComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_type: Literal["kruskal_wallis_test"]
    left_response_column_id: str | None
    right_response_column_id: str | None
    response_display_name: str | None
    same_response_column: bool
    left_group_column_id: str | None
    right_group_column_id: str | None
    group_display_name: str | None
    same_group_column: bool
    same_group_label_set: bool
    same_group_label_order: bool
    settings: list[KruskalWallisSettingComparison]
    metrics: list[KruskalWallisMetricComparison]


class AnalysisRunMethodSpecificComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descriptive_statistics: DescriptiveStatisticsComparison | None = None
    one_sample_t_test: OneSampleTTestComparison | None = None
    two_sample_t_test: TwoSampleTTestComparison | None = None
    paired_t_test: PairedTTestComparison | None = None
    equivalence_tost: EquivalenceTostComparison | None = None
    one_way_anova: OneWayAnovaComparison | None = None
    kruskal_wallis: KruskalWallisComparison | None = None


class AnalysisRunComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: AnalysisRunComparisonSideResponse
    right: AnalysisRunComparisonSideResponse
    comparable: bool
    compatibility: AnalysisRunComparisonCompatibility
    differences: list[AnalysisRunComparisonDifference]
    method_specific: AnalysisRunMethodSpecificComparison | None = None


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


class RegressionPredictionProvenance(AnalysisProvenance):
    model_config = ConfigDict(extra="forbid")

    source_analysis_id: UUID
    source_analysis_stale_at_prediction: bool
    source_dataset_version_id: UUID
    source_schema_hash_at_fit: str
    source_schema_hash_current: str
    target_dataset_version_id: UUID
    target_schema_hash: str
    model_id: UUID
    model_manifest_sha256: str
    prediction_schema_version: int = Field(ge=1)
    model_manifest_schema_version: int = Field(ge=1)
    missing_policy: Literal["complete_case"]
    confidence_level: float = Field(gt=0.0, lt=1.0)
    include_intervals: bool
    source_canonical_artifact_sha256: str
    target_canonical_artifact_sha256: str
    created_at: str


class AnalysisResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    method_id: str
    method_version: str
    dataset_version_id: UUID | None
    status: Literal["succeeded", "failed", "cancelled"]
    warnings: list[AnalysisWarning]
    provenance: AnalysisProvenance | RegressionPredictionProvenance
    result: dict[str, Any] | None = None


class AnalysisResultJsonExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    export_id: UUID
    analysis_id: UUID
    format: Literal["analysis_result_json"]
    artifact_kind: Literal["analysis_result_json_export"]
    media_type: Literal["application/json"]
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    source_result_sha256: str = Field(min_length=64, max_length=64)
    stale: bool
    created_at: str
    result: AnalysisResultEnvelope


class AnalysisResultCsvExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    export_id: UUID
    analysis_id: UUID
    format: Literal["analysis_result_csv"]
    artifact_kind: Literal["analysis_result_csv_export"]
    media_type: Literal["text/csv"]
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    source_result_sha256: str = Field(min_length=64, max_length=64)
    stale: bool
    created_at: str
    columns: list[str]
    row_count: int = Field(ge=0)
    preview_rows: list[list[str]]


class AnalysisResultHtmlReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    export_id: UUID
    analysis_id: UUID
    format: Literal["analysis_result_html_report"]
    artifact_kind: Literal["analysis_result_html_report"]
    media_type: Literal["text/html"]
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    source_result_sha256: str = Field(min_length=64, max_length=64)
    stale: bool
    created_at: str
    title: str
    section_count: int = Field(ge=0)


class AnalysisResultExportListItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_id: UUID
    analysis_id: UUID
    artifact_kind: str
    media_type: str
    sha256: str = Field(min_length=64, max_length=64)
    created_at: str
    download_url: str


class AnalysisResultExportListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    exports: list[AnalysisResultExportListItemResponse]


class AnalysisResultExportDeletionCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata_record_count: Literal[1]
    file_count: Literal[1]
    file_bytes: int = Field(ge=0)


class AnalysisResultExportDeletionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_schema_version: Literal[1]
    analysis_id: UUID
    export_id: UUID
    artifact_kind: Literal[
        "analysis_result_json_export",
        "analysis_result_csv_export",
        "analysis_result_html_report",
        "regression_prediction_csv_export",
    ]
    media_type: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    counts: AnalysisResultExportDeletionCounts
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AnalysisResultExportDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_analysis_id: UUID
    confirmation_export_id: UUID
    expected_deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AnalysisResultExportDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deletion_schema_version: Literal[1]
    analysis_id: UUID
    export_id: UUID
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deleted_at: str
    deleted_counts: AnalysisResultExportDeletionCounts
    cleanup_status: Literal["deleted", "quarantined_pending_cleanup"]


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


class RegressionModelCatalogResponseColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: UUID
    display_name: str
    data_type: str
    measurement_level: str
    unit: str | None


class RegressionModelCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: UUID
    source_analysis_id: UUID
    source_dataset_version_id: UUID
    method_id: Literal["regression.linear_model"]
    method_version: str
    schema_hash: str
    response: RegressionModelCatalogResponseColumn | None
    predictor_count: int | None = Field(ge=1)
    created_at: str
    availability: Literal["available", "source_stale", "integrity_error"]
    availability_code: str | None


class RegressionModelCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models: list[RegressionModelCatalogItem]
    total: int = Field(ge=0)
    returned: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_previous: bool
    has_next: bool


class RegressionModelDeletionCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regression_model_count: Literal[1]
    manifest_artifact_count: Literal[1]
    manifest_file_count: Literal[1]
    manifest_file_bytes: int = Field(ge=0)
    metadata_record_count: Literal[2]
    dependent_prediction_count: int = Field(ge=0)


class RegressionModelDeletionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_schema_version: Literal[1]
    model_id: UUID
    source_analysis_id: UUID
    method_id: Literal["regression.linear_model"]
    method_version: str
    deletion_ready: bool
    blockers: list[str]
    counts: RegressionModelDeletionCounts
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RegressionModelDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_model_id: UUID
    expected_deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RegressionModelDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deletion_schema_version: Literal[1]
    model_id: UUID
    source_analysis_id: UUID
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deleted_at: str
    deleted_counts: RegressionModelDeletionCounts
    cleanup_status: Literal["deleted", "quarantined_pending_cleanup"]


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
    training_min: float | None
    training_max: float | None
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
    source_schema_hash_current: str | None
    source_analysis_stale: bool | None
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
    source_analysis_id: UUID
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
    provenance: RegressionPredictionProvenance
    columns: list[RegressionPredictionColumnMapping]
    rows: list[RegressionPredictionRow]


class RegressionPredictionRowsPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_id: UUID
    model_id: UUID
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
    returned: int = Field(ge=0)
    has_previous: bool
    has_next: bool
    rows: list[RegressionPredictionRow]


class RegressionPredictionCsvExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    export_id: UUID
    prediction_id: UUID
    format: Literal["regression_prediction_csv"]
    artifact_kind: Literal["regression_prediction_csv_export"]
    media_type: Literal["text/csv"]
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    source_result_sha256: str = Field(min_length=64, max_length=64)
    stale: bool
    created_at: str
    columns: list[str]
    row_count: int = Field(ge=0)
    preview_rows: list[list[str]]
