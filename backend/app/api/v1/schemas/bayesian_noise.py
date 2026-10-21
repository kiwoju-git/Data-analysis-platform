"""Noise-aware BO contracts; legacy schemas remain byte-for-byte readers."""

from __future__ import annotations

from typing import Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.api.v1.schemas.bayesian import (
    BayesianBatchAcquisitionRequest,
    BayesianConstraintEvaluationResponse,
    BayesianExecutionMode,
    BayesianRecommendationBatchResponse,
    BayesianRecommendationCurrentTrialResponse,
    BayesianRecommendationSearchRequest,
    BayesianTrialResponse,
)

NOISE_BATCH_POLICY: Final = "greedy_mc_joint_latent_improvement_v2"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BayesianSurrogatePolicyRequest(_StrictModel):
    noise_mode: Literal["estimate", "fixed", "near_noiseless"] = "estimate"
    initial_noise_variance_scaled: FiniteFloat = Field(default=1e-2, gt=0)
    lower_noise_variance_scaled: FiniteFloat = Field(default=1e-6, gt=0)
    upper_noise_variance_scaled: FiniteFloat = Field(default=1.0, gt=0)
    fixed_noise_sd: FiniteFloat | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_noise(self) -> BayesianSurrogatePolicyRequest:
        if not (
            self.lower_noise_variance_scaled < self.upper_noise_variance_scaled
            and self.lower_noise_variance_scaled
            <= self.initial_noise_variance_scaled
            <= self.upper_noise_variance_scaled
        ):
            raise ValueError("noise initial value must be inside increasing bounds")
        if (self.noise_mode == "fixed") != (self.fixed_noise_sd is not None):
            raise ValueError("fixed noise requires a positive raw-unit measurement SD only")
        return self


class BayesianObservationPolicyRequest(_StrictModel):
    mode: Literal["retain_raw", "exact_replicates", "nearby_diagnostics"] = "retain_raw"
    nearby_tolerances: dict[str, FiniteFloat] | None = None
    nearby_units: Literal["actual", "normalized"] = "actual"

    @model_validator(mode="after")
    def validate_nearby(self) -> BayesianObservationPolicyRequest:
        if self.mode == "nearby_diagnostics":
            if not self.nearby_tolerances or any(
                value < 0 for value in self.nearby_tolerances.values()
            ):
                raise ValueError("nearby diagnostics require explicit nonnegative tolerances")
        elif self.nearby_tolerances is not None:
            raise ValueError("nearby tolerances are only valid for nearby diagnostics")
        return self


class BayesianMonteCarloBatchOptions(_StrictModel):
    posterior_sample_count: int = Field(default=64, ge=16, le=256)
    min_batch_distance_normalized: FiniteFloat = Field(default=0, ge=0)


class BayesianNoiseBatchSearchRequest(_StrictModel):
    random_seed: int = Field(default=20260715, ge=0, le=2_147_483_647)
    candidate_count_per_step: int = Field(default=256, ge=32, le=4096)
    local_start_count_per_step: int = Field(default=4, ge=0, le=16)
    max_iterations_per_step: int = Field(default=100, ge=1, le=500)
    max_evaluations_total: int = Field(default=4096, ge=32, le=160_000)
    model_max_iterations: int = Field(default=50, ge=1, le=200)
    model_max_evaluations: int = Field(default=200, ge=2, le=2000)
    hyperparameter_restart_count: int = Field(default=0, ge=0, le=3)
    time_budget_ms: int = Field(default=15_000, ge=1000, le=60_000)
    jitter: FiniteFloat = Field(default=1e-8, ge=1e-12, le=1e-3)
    duplicate_tolerance: FiniteFloat = Field(default=1e-6, ge=1e-12, le=0.1)
    total_trial_budget: int = Field(default=50, ge=2, le=200)
    batch_policy: Literal["greedy_mc_joint_latent_improvement_v2"] = NOISE_BATCH_POLICY


class BayesianNoiseBatchCreateRequest(_StrictModel):
    schema_version: Literal[2]
    expected_history_revision_id: UUID
    expected_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_mode: BayesianExecutionMode = "sequential_single"
    batch_size: int = Field(default=1, ge=1, le=8)
    acquisition: BayesianBatchAcquisitionRequest
    search: BayesianNoiseBatchSearchRequest = Field(default_factory=BayesianNoiseBatchSearchRequest)
    surrogate: BayesianSurrogatePolicyRequest = Field(
        default_factory=BayesianSurrogatePolicyRequest
    )
    observation_policy: BayesianObservationPolicyRequest = Field(
        default_factory=BayesianObservationPolicyRequest
    )
    batch_options: BayesianMonteCarloBatchOptions = Field(
        default_factory=BayesianMonteCarloBatchOptions
    )

    @model_validator(mode="after")
    def validate_batch(self) -> BayesianNoiseBatchCreateRequest:
        if self.execution_mode == "sequential_single" and self.batch_size != 1:
            raise ValueError("sequential_single requires one experiment")
        if self.execution_mode == "parallel_batch" and self.batch_size < 2:
            raise ValueError("parallel_batch requires two through eight experiments")
        if (
            self.search.max_evaluations_total
            < self.search.candidate_count_per_step * self.batch_size
        ):
            raise ValueError("evaluation budget must cover all candidate pools")
        return self


class BayesianNoiseSingleCreateRequest(_StrictModel):
    schema_version: Literal[2]
    expected_history_revision_id: UUID
    expected_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    search: BayesianRecommendationSearchRequest = Field(
        default_factory=BayesianRecommendationSearchRequest
    )
    surrogate: BayesianSurrogatePolicyRequest = Field(
        default_factory=BayesianSurrogatePolicyRequest
    )
    observation_policy: BayesianObservationPolicyRequest = Field(
        default_factory=BayesianObservationPolicyRequest
    )
    batch_options: BayesianMonteCarloBatchOptions = Field(
        default_factory=BayesianMonteCarloBatchOptions
    )


class BayesianSignalKernel(_StrictModel):
    kind: Literal["constant_times_matern_5_2_ard"]
    amplitude: FiniteFloat = Field(gt=0)
    length_scales: list[FiniteFloat] = Field(min_length=1, max_length=10)
    amplitude_bounds: tuple[FiniteFloat, FiniteFloat]
    length_scale_bounds: tuple[FiniteFloat, FiniteFloat]


class BayesianFittedNoise(_StrictModel):
    mode: Literal["estimate", "fixed", "near_noiseless"]
    initial_variance_scaled: FiniteFloat = Field(ge=0)
    bounds_scaled: tuple[FiniteFloat, FiniteFloat] | None
    fixed_sd_raw: FiniteFloat | None
    fitted_variance_scaled: FiniteFloat = Field(ge=0)


class BayesianNoiseNormalization(_StrictModel):
    mean: FiniteFloat
    scale: FiniteFloat = Field(gt=0)
    ddof: Literal[0]
    direction_multiplier: FiniteFloat

    @model_validator(mode="after")
    def validate_direction(self) -> BayesianNoiseNormalization:
        if self.direction_multiplier not in {-1.0, 1.0}:
            raise ValueError("direction multiplier must be -1 or 1")
        return self


class BayesianOptimizerStart(_StrictModel):
    success: bool
    status: int
    termination_reason: str
    iterations: int = Field(ge=0)
    evaluations: int = Field(ge=0)
    initial_log_parameters: list[FiniteFloat]
    final_log_parameters: list[FiniteFloat]
    negative_log_likelihood: FiniteFloat


class BayesianNoiseOptimizer(_StrictModel):
    name: Literal["L-BFGS-B"]
    optimized: bool
    seed: int = Field(ge=0)
    restarts: int = Field(ge=0, le=3)
    max_iterations: int = Field(ge=1, le=200)
    max_evaluations: int = Field(ge=2, le=2000)
    ftol: FiniteFloat = Field(gt=0)
    evaluations: int = Field(ge=0)
    starts: list[BayesianOptimizerStart]


class BayesianNoiseSharedModel(_StrictModel):
    schema_version: Literal[3]
    policy_version: Literal["bo_noise_latent_v2"]
    signal_kernel: BayesianSignalKernel
    noise: BayesianFittedNoise
    observation_noise_sd_raw: FiniteFloat = Field(ge=0)
    jitter: FiniteFloat = Field(ge=1e-12, le=1e-3)
    normalization: BayesianNoiseNormalization
    optimizer: BayesianNoiseOptimizer
    log_marginal_likelihood: FiniteFloat
    raw_observation_count: int = Field(ge=2, le=200)
    effective_training_count: int = Field(ge=2, le=200)
    training_group_counts: list[int]
    fit_elapsed_ms: FiniteFloat = Field(ge=0)
    package_versions: dict[str, str]
    objective_goal_type: Literal["maximize", "minimize", "match_target"]
    target_scaled: FiniteFloat | None


class BayesianLatentIncumbent(_StrictModel):
    incumbent_policy: Literal["posterior_mean_at_completed_locations_v2"]
    incumbent_kind: Literal["latent_target_distance", "directional_latent_mean"]
    best_observed_objective: FiniteFloat
    best_observed_trial_id: UUID
    best_observed_target_distance_raw: FiniteFloat | None
    latent_incumbent_value_scaled: FiniteFloat
    latent_incumbent_value_raw: FiniteFloat
    latent_incumbent_distance_scaled: FiniteFloat | None
    latent_incumbent_distance_raw: FiniteFloat | None
    latent_incumbent_trial_id: UUID
    latent_incumbent_coordinates_normalized: list[FiniteFloat]
    target_scaled: FiniteFloat | None
    xi_standardized: FiniteFloat = Field(ge=0)
    xi_raw: FiniteFloat = Field(ge=0)


class BayesianObservationGroupSummary(_StrictModel):
    member_trial_ids: list[UUID]
    member_indices: list[int]
    canonical_actual_coordinates: dict[str, FiniteFloat]
    canonical_level_indices: dict[str, int | None]
    condition_key: str | None
    n: int = Field(ge=1, le=200)
    mean: FiniteFloat
    within_ss: FiniteFloat = Field(ge=0)
    sample_variance: FiniteFloat | None


class BayesianObservationNormalization(_StrictModel):
    source: Literal["raw_observations"]
    mean: FiniteFloat
    scale: FiniteFloat = Field(gt=0)
    ddof: Literal[0]
    constant_response_scale_fallback: bool


class BayesianNearbyGroupSummary(_StrictModel):
    member_trial_ids: list[UUID]
    maximum_normalized_distance: FiniteFloat = Field(ge=0)
    maximum_axis_distances: dict[str, FiniteFloat]
    response_range: tuple[FiniteFloat, FiniteFloat]
    response_sample_variance: FiniteFloat = Field(ge=0)


class BayesianNearbyDiagnostics(_StrictModel):
    changes_training_data: Literal[False]
    grouping_policy: Literal["deterministic_complete_link_v1"]
    units: Literal["actual", "normalized"]
    tolerances: dict[str, FiniteFloat] | None
    groups: list[BayesianNearbyGroupSummary]


class BayesianObservationViewSummary(_StrictModel):
    policy_version: Literal[1]
    mode: Literal["retain_raw", "exact_replicates", "nearby_diagnostics"]
    raw_observation_count: int = Field(ge=2, le=200)
    unique_condition_count: int = Field(ge=2, le=200)
    unique_coordinate_count: int = Field(ge=2, le=200)
    effective_training_count: int = Field(ge=2, le=200)
    normalization: BayesianObservationNormalization
    groups: list[BayesianObservationGroupSummary]
    nearby_diagnostics: BayesianNearbyDiagnostics


class BayesianBatchPlanning(_StrictModel):
    policy_version: Literal["greedy_mc_joint_latent_improvement_v2"]
    root_seed: int = Field(ge=0)
    sample_seed: str = Field(pattern=r"^[0-9]+$")
    seed_stage: Literal["latent_selected_samples"]
    batch_step: int = Field(ge=0, le=7)
    requested_sample_count: int = Field(ge=16, le=256)
    effective_sample_count: int = Field(ge=0, le=256)
    conditioned_on_selected_ranks: list[int]
    selected_covariance_adjustment_scaled: FiniteFloat = Field(ge=0)
    covariance_roundoff_scale: FiniteFloat = Field(ge=0)
    covariance_adjustment_is_measurement_noise: Literal[False]
    representative_prediction_source: Literal["completed_observations_base_posterior"]
    common_random_numbers: Literal[True]
    conditional_latent_sd_scaled: FiniteFloat = Field(ge=0)
    conditional_variance_adjustment_max_scaled: FiniteFloat = Field(ge=0)


class BayesianDiscreteAssignment(_StrictModel):
    level_indices: dict[str, int]
    actual_coordinates: dict[str, FiniteFloat]


class BayesianLocalSearchStatus(_StrictModel):
    success: bool
    status: int
    iterations: int = Field(ge=0)
    feasible: bool


class BayesianMixedSearchSummary(_StrictModel):
    policy: Literal["fixed_discrete_continuous_slsqp_v1"]
    space_kind: Literal["mixed", "discrete", "continuous"]
    discrete_assignment_count: int = Field(ge=1)
    enumerated_all_discrete_assignments: bool
    visited_discrete_assignments: list[BayesianDiscreteAssignment]
    neighbor_assignments_evaluated: int = Field(ge=0)
    local_starts: int = Field(ge=0, le=16)
    local_successes: int = Field(ge=0, le=16)
    local_statuses: list[BayesianLocalSearchStatus]
    feasible_pool_size: int = Field(ge=1)
    evaluations: int = Field(ge=1)
    termination_reason: str
    all_acquisitions_zero: bool
    selected_from: Literal["feasible_pool", "local_refinement"]
    nearest_existing_distance: FiniteFloat | None
    nearest_selected_distance: FiniteFloat | None
    global_optimum_guaranteed: Literal[False]


class BayesianNoiseSearchBudget(_StrictModel):
    max_evaluations_total: int = Field(ge=32, le=160_000)
    evaluations_consumed: int = Field(ge=1)
    evaluation_unit: Literal["candidate_or_64_conditional_acquisition_samples"]
    raw_candidate_evaluations: int = Field(ge=1)
    conditional_acquisition_sample_evaluations: int = Field(ge=1)
    time_budget_ms: int = Field(ge=1000, le=60_000)
    elapsed_ms: FiniteFloat = Field(ge=0)
    min_batch_distance_normalized: FiniteFloat = Field(ge=0)
    searches: list[BayesianMixedSearchSummary]
    termination_reason: Literal["search_completed"]


class BayesianNoiseCalculatedItem(_StrictModel):
    rank: int = Field(ge=1, le=8)
    actual_coordinates: dict[str, FiniteFloat]
    normalized_coordinates: dict[str, FiniteFloat]
    predicted_objective_mean: FiniteFloat
    latent_standard_deviation: FiniteFloat = Field(ge=0)
    predictive_standard_deviation: FiniteFloat = Field(ge=0)
    acquisition_kind: Literal["expected_improvement", "expected_target_improvement"]
    acquisition_value_standardized: FiniteFloat = Field(ge=0)
    acquisition_value_raw: FiniteFloat = Field(ge=0)
    planning: BayesianBatchPlanning
    nearest_existing_distance: FiniteFloat | None
    nearest_selected_distance: FiniteFloat | None
    constraint_evaluations: list[BayesianConstraintEvaluationResponse]


class BayesianNoiseCalculation(_StrictModel):
    schema_version: Literal[2]
    batch_policy: Literal["greedy_mc_joint_latent_improvement_v2"]
    batch_size: int = Field(ge=1, le=8)
    shared_model: BayesianNoiseSharedModel
    incumbent: BayesianLatentIncumbent
    observation_view: BayesianObservationViewSummary
    items: list[BayesianNoiseCalculatedItem]
    search_budget: BayesianNoiseSearchBudget
    warnings: list[str]
    limitations: list[str]


class BayesianNoiseBatchItem(BayesianNoiseCalculatedItem):
    item_id: UUID
    batch_id: UUID
    trial: BayesianTrialResponse
    current_trial: BayesianRecommendationCurrentTrialResponse


class BayesianNoiseBatchProvenance(_StrictModel):
    study_id: UUID
    study_version_id: UUID
    batch_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str
    definition_sha256: str
    method_id: Literal["doe.bayesian_optimization"]
    method_version: Literal["0.7.0"]
    config_schema_version: Literal[2]
    result_schema_version: Literal[2]
    model_schema_version: Literal[3]
    item_schema_version: Literal[2]
    app_version: str
    python_version: str
    platform: str
    build_commit: str | None
    package_versions: dict[str, str]
    created_at: str


class BayesianNoiseBatchResponse(_StrictModel):
    batch_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str
    definition_sha256: str
    method_id: Literal["doe.bayesian_optimization"]
    method_version: Literal["0.7.0"]
    config_schema_version: Literal[2]
    result_schema_version: Literal[2]
    model_schema_version: Literal[3]
    item_schema_version: Literal[2]
    batch_policy: Literal["greedy_mc_joint_latent_improvement_v2"]
    execution_mode: BayesianExecutionMode
    batch_size: int = Field(ge=1, le=8)
    acquisition: BayesianBatchAcquisitionRequest
    shared_model: BayesianNoiseSharedModel
    incumbent: BayesianLatentIncumbent
    observation_view: BayesianObservationViewSummary
    search_budget: BayesianNoiseSearchBudget
    items: list[BayesianNoiseBatchItem]
    warnings: list[str]
    limitations: list[str]
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: BayesianNoiseBatchProvenance
    created_at: str
    is_latest: bool = False
    batch_state: Literal[
        "pending", "partially_completed", "completed", "abandoned", "closed_mixed"
    ] = "pending"
    requested_total_trial_budget: int = Field(ge=2, le=200)


BayesianAnyBatchResponse = BayesianRecommendationBatchResponse | BayesianNoiseBatchResponse


class BayesianAnyBatchListResponse(_StrictModel):
    study_id: UUID
    study_version_id: UUID
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[BayesianAnyBatchResponse]


class BayesianAnyLatestBatchResponse(_StrictModel):
    study_id: UUID
    study_version_id: UUID
    item: BayesianAnyBatchResponse | None
