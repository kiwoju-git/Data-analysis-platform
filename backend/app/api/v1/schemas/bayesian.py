from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator


class BayesianFactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    name: str = Field(min_length=1, max_length=80)
    low: FiniteFloat
    high: FiniteFloat
    unit: str | None = Field(default=None, max_length=40)


class BayesianObjectiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    unit: str | None = Field(default=None, max_length=40)
    direction: Literal["minimize", "maximize"]
    observation_policy: Literal["manual_single_observation"] = "manual_single_observation"


class BayesianConstraintTermRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    coefficient: FiniteFloat


class BayesianLinearConstraintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    name: str = Field(min_length=1, max_length=80)
    terms: list[BayesianConstraintTermRequest] = Field(min_length=1, max_length=6)
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    bound: FiniteFloat


class BayesianStudyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Bayesian study", min_length=1, max_length=120)
    factors: list[BayesianFactorRequest] = Field(min_length=1, max_length=6)
    objective: BayesianObjectiveRequest
    constraints: list[BayesianLinearConstraintRequest] = Field(default_factory=list, max_length=16)
    initial_design_seed: int = Field(ge=0, le=2_147_483_647)
    initial_design_size: int = Field(ge=1, le=64)


class BayesianFactorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    name: str
    low: float
    high: float
    unit: str | None
    order: int = Field(ge=1)
    scaling_rule: Literal["linear_0_1"]


class BayesianObjectiveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    unit: str | None
    direction: Literal["minimize", "maximize"]
    observation_policy: Literal["manual_single_observation"]


class BayesianConstraintTermResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    coefficient: float


class BayesianLinearConstraintResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    name: str
    terms: list[BayesianConstraintTermResponse]
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    bound: float


class BayesianInitialDesignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: Literal["sha256_counter_uniform_feasible_v1"]
    seed: int = Field(ge=0)
    requested_size: int = Field(ge=1, le=64)
    generated_size: int = Field(ge=1, le=64)
    attempt_limit: int = Field(ge=1)
    attempts_consumed: int = Field(ge=1)


class BayesianTrialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_id: UUID
    study_version_id: UUID
    trial_number: int = Field(ge=1)
    origin: Literal["initial_design", "recommendation"]
    state: Literal["pending", "completed", "abandoned"]
    actual_coordinates: dict[str, float]
    normalized_coordinates: dict[str, float]
    coordinates_sha256: str
    objective_value: float | None
    created_at: str
    closed_at: str | None


class BayesianHistoryRevisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    history_revision_id: UUID
    study_version_id: UUID
    revision_number: int = Field(ge=1)
    schema_version: Literal[1]
    completed_trial_ids: list[UUID]
    completed_trial_count: int = Field(ge=0)
    observation_history_sha256: str
    previous_history_sha256: str | None
    created_at: str


class BayesianStudyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    version_number: int = Field(ge=1)
    study_schema_version: Literal[1]
    method_id: Literal["doe.bayesian_optimization"]
    method_version: str
    name: str
    status: Literal["active", "completed", "abandoned"]
    created_at: str
    updated_at: str
    app_version: str
    definition_sha256: str
    factors: list[BayesianFactorResponse]
    objective: BayesianObjectiveResponse
    constraints: list[BayesianLinearConstraintResponse]
    initial_design: BayesianInitialDesignResponse
    trial_count: int = Field(ge=1)
    pending_trial_count: int = Field(ge=0)
    completed_trial_count: int = Field(ge=0)
    abandoned_trial_count: int = Field(ge=0)
    observation_history: BayesianHistoryRevisionResponse
    trials: list[BayesianTrialResponse]
    surrogate_available: bool
    recommendation_available: bool


class BayesianStudySummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    method_id: Literal["doe.bayesian_optimization"]
    method_version: str
    name: str
    status: Literal["active", "completed", "abandoned"]
    updated_at: str
    definition_sha256: str
    pending_trial_count: int = Field(ge=0)
    completed_trial_count: int = Field(ge=0)
    abandoned_trial_count: int = Field(ge=0)
    observation_history_sha256: str


class BayesianStudyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[BayesianStudySummaryResponse]


class BayesianTrialListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[BayesianTrialResponse]


class BayesianObservationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_value: FiniteFloat
    expected_history_revision_id: UUID


class BayesianTrialTransitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    trial: BayesianTrialResponse
    observation_history: BayesianHistoryRevisionResponse


class BayesianHistoryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[BayesianHistoryRevisionResponse]


class BayesianRecommendationSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    random_seed: int = Field(default=20260715, ge=0, le=2_147_483_647)
    xi: FiniteFloat = Field(default=0.01, ge=0.0, le=10.0)
    candidate_count: int = Field(default=256, ge=32, le=4096)
    local_start_count: int = Field(default=4, ge=0, le=16)
    max_iterations: int = Field(default=100, ge=1, le=500)
    max_evaluations: int = Field(default=4096, ge=32, le=20_000)
    model_max_iterations: int = Field(default=50, ge=1, le=200)
    model_max_evaluations: int = Field(default=200, ge=2, le=2000)
    hyperparameter_restart_count: int = Field(default=0, ge=0, le=3)
    time_budget_ms: int = Field(default=15_000, ge=1000, le=60_000)
    jitter: FiniteFloat = Field(default=1e-8, ge=1e-12, le=1e-3)
    duplicate_tolerance: FiniteFloat = Field(default=1e-6, ge=1e-12, le=0.1)
    total_trial_budget: int = Field(default=50, ge=2, le=200)

    @model_validator(mode="after")
    def require_candidate_budget(self) -> BayesianRecommendationSearchRequest:
        if self.max_evaluations < self.candidate_count:
            raise ValueError("max_evaluations must cover candidate_count")
        return self


class BayesianRecommendationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_history_revision_id: UUID
    search: BayesianRecommendationSearchRequest = Field(
        default_factory=BayesianRecommendationSearchRequest
    )


class BayesianConstraintEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_id: str
    name: str
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    lhs: float
    bound: float
    slack: float
    satisfied: bool


class BayesianSurrogateModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    kernel_policy: Literal["constant_times_matern_5_2_ard_v1"]
    fitted_kernel: str
    constant_value: float
    length_scales: list[float]
    log_marginal_likelihood: float
    objective_direction_multiplier: float
    objective_normalization_mean: float
    objective_normalization_scale: float = Field(gt=0.0)
    jitter: float = Field(gt=0.0)
    completed_observation_count: int = Field(ge=2, le=200)
    hyperparameter_restart_count: int = Field(ge=0, le=3)
    model_evaluations: int = Field(ge=0)
    fit_elapsed_ms: float = Field(ge=0.0)
    package_versions: dict[str, str]


class BayesianRecommendationBudgetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_count_requested: int = Field(ge=32, le=4096)
    feasible_candidate_count: int = Field(ge=1)
    local_start_count_requested: int = Field(ge=0, le=16)
    local_starts_attempted: int = Field(ge=0, le=16)
    local_success_count: int = Field(ge=0, le=16)
    local_iterations: int = Field(ge=0)
    max_evaluations: int = Field(ge=32, le=20_000)
    evaluations_consumed: int = Field(ge=0)
    model_max_iterations: int = Field(ge=1, le=200)
    model_max_evaluations: int = Field(ge=2, le=2000)
    model_evaluations_consumed: int = Field(ge=0)
    time_budget_ms: int = Field(ge=1000, le=60_000)
    elapsed_ms: float = Field(ge=0.0)
    termination_reason: Literal["search_completed", "evaluation_budget", "time_budget"]


class BayesianRecommendationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    recommended_actual_coordinates: dict[str, float]
    recommended_normalized_coordinates: dict[str, float]
    predicted_objective_mean: float
    posterior_standard_deviation: float = Field(ge=0.0)
    expected_improvement: float = Field(ge=0.0)
    incumbent_objective: float
    objective_direction: Literal["minimize", "maximize"]
    constraint_evaluations: list[BayesianConstraintEvaluationResponse]
    model: BayesianSurrogateModelResponse
    budget: BayesianRecommendationBudgetResponse
    warnings: list[str]
    limitations: list[str]


class BayesianRecommendationProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    recommendation_id: UUID
    recommendation_trial_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str
    definition_sha256: str
    method_id: Literal["doe.bayesian_optimization"]
    method_version: str
    config_schema_version: Literal[1]
    result_schema_version: Literal[1]
    model_schema_version: Literal[1]
    app_version: str
    python_version: str
    platform: str
    build_commit: str | None
    package_versions: dict[str, str]
    created_at: str


class BayesianRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str
    definition_sha256: str
    method_id: Literal["doe.bayesian_optimization"]
    method_version: str
    config_schema_version: Literal[1]
    result_schema_version: Literal[1]
    model_schema_version: Literal[1]
    config_sha256: str
    result_payload_sha256: str
    created_at: str
    trial: BayesianTrialResponse
    result: BayesianRecommendationResult
    provenance: BayesianRecommendationProvenance


class BayesianRecommendationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[BayesianRecommendationResponse]
