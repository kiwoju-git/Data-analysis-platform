"""Internal schema5 batch calculation; not registered as a public API request."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, FiniteFloat, model_validator

from app.api.v1.schemas.bayesian import BayesianConstraintEvaluationResponse
from app.api.v1.schemas.bayesian_desirability import DesirabilityObjective
from app.api.v1.schemas.bayesian_noise import BayesianMixedSearchSummary
from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityCalculationRequest,
    DesirabilityFactor,
    DesirabilityMomentResult,
    DesirabilityObservation,
    DesirabilityResponseModelRequest,
    DesirabilitySearch,
    Identifier,
    _Acquisition,
    _Budget,
    _Constraint,
    _Incumbent,
    _NumericalPolicyFields,
    _ResponsePrediction,
    _SharedModel,
    _SharedObservationView,
    _StrictModel,
    _StrictObservationPolicy,
)


class DesirabilityBatchOptions(_StrictModel):
    sample_count: int = Field(default=64, ge=16, le=256)
    max_moment_evaluations: int = Field(default=8192, ge=1, le=65536)
    min_batch_distance_normalized: FiniteFloat = Field(default=0.0, ge=0)


class _BatchCalculationRequestFields(_StrictModel):
    batch_size: int = Field(ge=1, le=8)
    batch_options: DesirabilityBatchOptions
    factors: list[DesirabilityFactor] = Field(min_length=1, max_length=10)
    constraints: list[_Constraint] = Field(max_length=16)
    observations: list[DesirabilityObservation] = Field(min_length=2, max_length=200)
    excluded_normalized: list[list[FiniteFloat]] = Field(min_length=1, max_length=200)
    objective: Any
    response_models: list[DesirabilityResponseModelRequest] = Field(min_length=1, max_length=4)
    observation_policy: _StrictObservationPolicy
    xi_desirability: FiniteFloat = Field(ge=0)
    search: DesirabilitySearch

    @model_validator(mode="before")
    @classmethod
    def strict_version(cls, value: Any) -> Any:
        if isinstance(value, dict) and type(value.get("schema_version")) is not int:
            raise ValueError("bayesian_desirability_batch_input_invalid")
        return value

    @model_validator(mode="after")
    def validate_shared_input(self) -> _BatchCalculationRequestFields:
        self.q1_request()
        return self

    def q1_request(self) -> Any:
        # A read-only projection to the unchanged common fit/goal contract. It is
        # never persisted or substituted for the original schema5 request digest.
        raw = self.model_dump(mode="python", exclude={"batch_options", "fit_policy"})
        raw.update(schema_version=4, batch_size=1)
        return DesirabilityCalculationRequest.model_validate(raw)

    def worker_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class DesirabilityBatchCalculationRequest(_BatchCalculationRequestFields):
    schema_version: Literal[5]
    objective: DesirabilityObjective


class _CovarianceSummary(_StrictModel):
    rank: int = Field(ge=0, le=7)
    negative_eigenvalue_adjustment_scaled: FiniteFloat = Field(ge=0)
    negative_eigenvalue_adjustment_raw: FiniteFloat = Field(ge=0)
    roundoff_scale: FiniteFloat = Field(gt=0)
    conditional_variance_adjustment_max_scaled: FiniteFloat = Field(ge=0)


class _Sampler(_NumericalPolicyFields):
    policy_version: Literal["conditional_mc_desirability_beta_marginal_v1"]
    root_seed: int = Field(ge=0, le=2_147_483_647)
    response_sample_seeds: dict[Identifier, str] = Field(min_length=1, max_length=4)
    batch_step: int = Field(ge=0, le=7)
    requested_sample_count: int = Field(ge=16, le=256)
    effective_sample_count: int = Field(ge=0, le=256)
    conditioned_on_selected_ranks: list[int] = Field(max_length=7)
    baseline_threshold: FiniteFloat = Field(ge=0)
    representative_prediction_source: Literal["completed_observations_base_posterior"]
    common_random_numbers: Literal[True]
    response_independence_assumption: Literal[True]
    score_is_exact_joint_ei: Literal[False]
    mc_standard_error_excludes_beta_approximation_error: Literal[True]
    covariance_adjustment_is_measurement_noise: Literal[False]
    selected_covariance: dict[Identifier, _CovarianceSummary] = Field(max_length=4)
    moment_evaluation_unit: Literal["joint_response_desirability_moments"]
    max_moment_evaluations: int = Field(ge=1, le=65536)
    moment_evaluations: int = Field(ge=1, le=65536)
    response_moment_evaluations: int = Field(ge=1, le=262144)
    integration_evaluations: int = Field(ge=0)
    candidate_evaluations: int = Field(ge=1)
    exact_selected_evaluations: int = Field(ge=0)


class _ResponseProof(_StrictModel):
    selected_mean_scaled: list[FiniteFloat] = Field(min_length=1, max_length=7)
    selected_covariance_scaled: list[list[FiniteFloat]] = Field(min_length=1, max_length=7)
    candidate_mean_scaled: FiniteFloat
    candidate_variance_scaled: FiniteFloat = Field(ge=0)
    cross_covariance_scaled: list[FiniteFloat] = Field(min_length=1, max_length=7)


class _PlanningProof(_StrictModel):
    response_proofs: dict[Identifier, _ResponseProof] = Field(max_length=4)
    thresholds: list[FiniteFloat] = Field(max_length=256)
    sample_moments: list[DesirabilityMomentResult] = Field(max_length=256)


class _Planning(_StrictModel):
    score: FiniteFloat = Field(ge=0, le=1)
    mc_standard_error: FiniteFloat = Field(ge=0, le=0.5)
    conditional_variance_raw: dict[Identifier, FiniteFloat] = Field(min_length=1, max_length=4)
    search_seed: int = Field(ge=0, le=2**32 - 1)
    sampler: _Sampler
    proof: _PlanningProof


class DesirabilityBatchCandidate(_StrictModel):
    rank: int = Field(ge=1, le=8)
    actual_coordinates: dict[Identifier, FiniteFloat]
    normalized_coordinates: dict[Identifier, FiniteFloat]
    response_predictions: list[_ResponsePrediction] = Field(min_length=1, max_length=4)
    desirability_moments: DesirabilityMomentResult
    acquisition: _Acquisition
    nearest_existing_distance: FiniteFloat = Field(ge=0)
    constraint_evaluations: list[BayesianConstraintEvaluationResponse] = Field(max_length=16)
    nearest_selected_distance: FiniteFloat | None = Field(ge=0)
    planning: _Planning


class _BatchBudget(_Budget):
    searches: list[BayesianMixedSearchSummary] = Field(min_length=1, max_length=8)
    max_moment_evaluations: int = Field(ge=1, le=65536)
    moment_evaluations: int = Field(ge=1, le=65536)
    incumbent_moment_evaluations: int = Field(ge=1, le=200)
    response_moment_evaluations: int = Field(ge=1, le=262144)
    initial_pool_upper_bound_per_step: int = Field(ge=1, le=4416)
    preflight_moment_allowance: int = Field(ge=1, le=65536)


class _BatchCalculationResultFields(_StrictModel):
    batch_size: int = Field(ge=1, le=8)
    policy: Literal["conditional_mc_desirability_beta_marginal_v1"]
    batch_options: DesirabilityBatchOptions
    objective: Any
    incumbent: _Incumbent
    observation_view: _SharedObservationView
    items: list[DesirabilityBatchCandidate] = Field(min_length=1, max_length=8)
    search_budget: _BatchBudget
    warnings: list[str] = Field(max_length=64)
    limitations: list[str] = Field(max_length=32)


class DesirabilityBatchCalculationResult(_BatchCalculationResultFields):
    schema_version: Literal[5]
    objective: DesirabilityObjective
    shared_model: _SharedModel
