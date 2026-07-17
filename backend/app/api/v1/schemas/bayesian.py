from __future__ import annotations

from typing import Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

MAX_BAYESIAN_TRIALS: Final = 200
MAX_COMPLETED_OBSERVATIONS: Final = 200
MAX_HISTORY_REVISIONS: Final = MAX_COMPLETED_OBSERVATIONS + 1
DEFAULT_TOTAL_TRIAL_BUDGET: Final = 50


def minimum_bayesian_initial_design_size(factor_count: int) -> int:
    return max(2, factor_count + 1)


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
    predecessor_study_id: UUID | None = None


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


BayesianStudyStatus = Literal["active", "completed", "abandoned"]
BayesianStudyCloseReason = Literal[
    "objective_satisfied",
    "budget_reached",
    "confirmation_complete",
    "unsafe_or_infeasible",
    "resources_unavailable",
    "study_cancelled",
]


class BayesianStudyLifecycleEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    lifecycle_event_id: UUID
    study_id: UUID
    study_version_id: UUID
    lifecycle_revision: Literal[1]
    previous_status: Literal["active"]
    resulting_status: Literal["completed", "abandoned"]
    reason_code: BayesianStudyCloseReason
    note: str | None
    request_id: UUID
    final_history_revision_id: UUID
    final_observation_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_trial_count: int = Field(ge=1, le=MAX_BAYESIAN_TRIALS)
    final_completed_trial_count: int = Field(ge=0, le=MAX_COMPLETED_OBSERVATIONS)
    final_abandoned_trial_count: int = Field(ge=0, le=MAX_BAYESIAN_TRIALS)
    latest_recommendation_id: UUID | None
    definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    closed_at: str
    created_at: str
    app_version: str
    build_commit: str | None


class BayesianStudyCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_status: Literal["completed", "abandoned"]
    reason_code: BayesianStudyCloseReason
    note: str | None = Field(default=None, max_length=500)
    request_id: UUID
    expected_study_version_id: UUID
    expected_history_revision_id: UUID
    expected_observation_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_reason_for_status(self) -> BayesianStudyCloseRequest:
        completion_reasons = {
            "objective_satisfied",
            "budget_reached",
            "confirmation_complete",
        }
        abandonment_reasons = {
            "unsafe_or_infeasible",
            "resources_unavailable",
            "study_cancelled",
        }
        allowed = completion_reasons if self.target_status == "completed" else abandonment_reasons
        if self.reason_code not in allowed:
            raise ValueError("reason_code does not match target_status")
        if self.note is not None and not self.note.strip():
            self.note = None
        return self


class BayesianTrialAbandonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_history_revision_id: UUID | None = None
    intent: Literal["continue_study", "close_study"] = "continue_study"

    @model_validator(mode="after")
    def require_history_for_close_intent(self) -> BayesianTrialAbandonRequest:
        if self.intent == "close_study" and self.expected_history_revision_id is None:
            raise ValueError("close_study intent requires expected_history_revision_id")
        return self


class BayesianStudyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    version_number: int = Field(ge=1)
    study_schema_version: Literal[1]
    method_id: Literal["doe.bayesian_optimization"]
    method_version: str
    name: str
    status: BayesianStudyStatus
    predecessor_study_id: UUID | None
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
    recommendation_minimum_completed_observations: int = Field(ge=2, le=7)
    recommendation_hard_trial_limit: int = Field(ge=1)
    recommendation_blockers: list[
        Literal[
            "bayesian_optimization_history_incomplete",
            "bayesian_optimization_pending_recommendation_exists",
            "bayesian_optimization_budget_exhausted",
            "bayesian_study_not_active",
        ]
    ]
    lifecycle_event: BayesianStudyLifecycleEventResponse | None


class BayesianStudyCloseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study: BayesianStudyResponse
    lifecycle_event: BayesianStudyLifecycleEventResponse


class BayesianStudyDeletionCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_count: Literal[1]
    study_version_count: int = Field(ge=1)
    trial_count: int = Field(ge=1, le=MAX_BAYESIAN_TRIALS)
    history_revision_count: int = Field(ge=1, le=MAX_HISTORY_REVISIONS)
    history_head_count: int = Field(ge=1)
    recommendation_count: int = Field(ge=0, le=MAX_BAYESIAN_TRIALS)
    lifecycle_event_count: int = Field(ge=0, le=1)
    metadata_record_count: int = Field(ge=4)
    file_count: Literal[0]
    file_bytes: Literal[0]


class BayesianStudyDeletionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_schema_version: Literal[1]
    study_id: UUID
    study_version_id: UUID
    status: BayesianStudyStatus
    eligible: bool
    blockers: list[
        Literal[
            "bayesian_study_deletion_active",
            "bayesian_study_deletion_referenced",
        ]
    ]
    successor_study_count: int = Field(ge=0)
    counts: BayesianStudyDeletionCounts
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BayesianStudyDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_study_id: UUID
    expected_deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BayesianStudyDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deletion_schema_version: Literal[1]
    study_id: UUID
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deleted_at: str
    deleted_counts: BayesianStudyDeletionCounts


class BayesianStudySummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    method_id: Literal["doe.bayesian_optimization"]
    method_version: str
    name: str
    status: BayesianStudyStatus
    predecessor_study_id: UUID | None
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
    total_trial_budget: int = Field(
        default=DEFAULT_TOTAL_TRIAL_BUDGET,
        ge=2,
        le=MAX_BAYESIAN_TRIALS,
    )

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
    completed_observation_count: int = Field(ge=2, le=MAX_COMPLETED_OBSERVATIONS)
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


class BayesianRecommendationCurrentTrialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_id: UUID
    state: Literal["pending", "completed", "abandoned"]
    objective_value: float | None
    closed_at: str | None


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
    current_trial: BayesianRecommendationCurrentTrialResponse | None = None
    is_latest: bool = False
    requested_total_trial_budget: int | None = Field(
        default=None,
        ge=2,
        le=MAX_BAYESIAN_TRIALS,
    )


class BayesianRecommendationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[BayesianRecommendationResponse]


class BayesianLatestRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    item: BayesianRecommendationResponse | None
