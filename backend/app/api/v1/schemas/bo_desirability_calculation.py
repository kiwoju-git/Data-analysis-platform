"""Typed calculation payloads shared by the worker and q1 review API."""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.api.v1.schemas.bayesian import BayesianConstraintEvaluationResponse
from app.api.v1.schemas.bayesian_desirability import (
    DesirabilityObjective,
)
from app.api.v1.schemas.bayesian_noise import (
    BayesianFittedNoise,
    BayesianKernelRequest,
    BayesianMixedSearchSummary,
    BayesianNoiseNormalization,
    BayesianNoiseOptimizer,
    BayesianObservationPolicyRequest,
    BayesianObservationViewSummary,
    BayesianSelectedSignalKernel,
    BayesianSurrogatePolicyRequest,
)
from app.statistics.bayesian_optimization import (
    BayesianOptimizationError,
    _validated_constraints,
    _validated_factors,
)

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")]
TrialId = Annotated[UUID, Field(strict=False)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DesirabilityFactor(_StrictModel):
    factor_id: Identifier
    low: FiniteFloat
    high: FiniteFloat
    domain_kind: Literal["continuous", "discrete_numeric"] = "continuous"
    step: FiniteFloat | None = None
    display_decimals: int | None = Field(default=None, ge=0, le=12)


class _ConstraintTerm(_StrictModel):
    factor_id: Identifier
    coefficient: FiniteFloat


class _Constraint(_StrictModel):
    constraint_id: Identifier
    name: str = Field(default="Constraint", min_length=1, max_length=80)
    terms: list[_ConstraintTerm] = Field(min_length=1, max_length=10)
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    bound: FiniteFloat


class DesirabilityObservation(_StrictModel):
    trial_id: TrialId
    actual_coordinates: dict[Identifier, FiniteFloat] = Field(min_length=1, max_length=10)
    normalized_coordinates: dict[Identifier, FiniteFloat] = Field(min_length=1, max_length=10)
    response_values: dict[Identifier, FiniteFloat] = Field(min_length=1, max_length=4)
    condition_key: str | None = Field(default=None, max_length=128)


class _StrictNoise(BayesianSurrogatePolicyRequest):
    model_config = ConfigDict(extra="forbid", strict=True)


class _StrictObservationPolicy(BayesianObservationPolicyRequest):
    model_config = ConfigDict(extra="forbid", strict=True)


class DesirabilityResponseModelRequest(_StrictModel):
    response_id: Identifier
    kernel: BayesianKernelRequest
    surrogate: _StrictNoise


class DesirabilitySearch(_StrictModel):
    random_seed: int = Field(ge=0, le=2_147_483_647)
    candidate_count_per_step: int = Field(ge=32, le=4096)
    local_start_count_per_step: int = Field(ge=0, le=16)
    max_iterations_per_step: int = Field(ge=1, le=500)
    max_evaluations_total: int = Field(ge=32, le=160_000)
    model_max_iterations: int = Field(ge=1, le=200)
    model_max_evaluations: int = Field(ge=2, le=2000)
    hyperparameter_restart_count: int = Field(ge=0, le=3)
    time_budget_ms: int = Field(ge=1000, le=60_000)
    jitter: FiniteFloat = Field(ge=1e-12, le=1e-3)
    duplicate_tolerance: FiniteFloat = Field(ge=1e-12, le=0.1)

    @model_validator(mode="after")
    def validate_budget(self) -> DesirabilitySearch:
        if self.max_evaluations_total < self.candidate_count_per_step:
            raise ValueError("bayesian_optimization_invalid_options")
        return self


class _CalculationRequestFields(_StrictModel):
    batch_size: Literal[1] = 1
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
    def strict_versions(cls, value: Any) -> Any:
        if isinstance(value, dict) and (
            type(value.get("schema_version")) is not int
            or type(value.get("batch_size", 1)) is not int
        ):
            raise ValueError("bayesian_desirability_input_invalid")
        return value

    @model_validator(mode="after")
    def validate_relationships(self) -> _CalculationRequestFields:
        response_ids = {r.response_id for r in self.objective.responses}
        model_ids = [m.response_id for m in self.response_models]
        trial_ids = [o.trial_id for o in self.observations]
        factor_ids = {f.factor_id for f in self.factors}
        if (
            len(model_ids) != len(set(model_ids))
            or set(model_ids) != response_ids
            or len(trial_ids) != len(set(trial_ids))
        ):
            raise ValueError("bayesian_desirability_response_mapping_invalid")
        try:
            factors = _validated_factors([f.model_dump() for f in self.factors])
            _validated_constraints([c.model_dump() for c in self.constraints], factors)
        except BayesianOptimizationError as exc:
            raise ValueError(exc.code) from exc
        if any(
            len(point) != len(factors) or any(not 0 <= v <= 1 for v in point)
            for point in self.excluded_normalized
        ):
            raise ValueError("bayesian_optimization_factor_space_invalid")
        for observation in self.observations:
            if (
                set(observation.response_values) != response_ids
                or set(observation.actual_coordinates) != factor_ids
                or set(observation.normalized_coordinates) != factor_ids
            ):
                raise ValueError("bayesian_desirability_response_mapping_invalid")
            point = []
            for factor in factors:
                actual = observation.actual_coordinates[factor["factor_id"]]
                normalized = observation.normalized_coordinates[factor["factor_id"]]
                expected = (actual - factor["low"]) / (factor["high"] - factor["low"])
                if not (
                    factor["low"] <= actual <= factor["high"]
                    and 0 <= normalized <= 1
                    and math.isclose(normalized, expected, rel_tol=1e-12, abs_tol=1e-12)
                ):
                    raise ValueError("bayesian_optimization_factor_space_invalid")
                point.append(normalized)
            if not any(
                math.dist(point, excluded) <= 2e-12 for excluded in self.excluded_normalized
            ):
                raise ValueError("bayesian_desirability_excluded_observation_missing")
        from app.statistics.bo_observation_groups import (
            BoObservationGroupsError,
            prepare_bo_observation_view,
        )

        try:
            prepare_bo_observation_view(
                [
                    {
                        **o.model_dump(mode="json", exclude={"response_values"}),
                        "objective_value": o.response_values[
                            self.objective.responses[0].response_id
                        ],
                    }
                    for o in self.observations
                ],
                factors,
                **self.observation_policy.model_dump(),
            )
        except BoObservationGroupsError as exc:
            raise ValueError(exc.code) from exc
        return self

    def worker_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class DesirabilityCalculationRequest(_CalculationRequestFields):
    schema_version: Literal[4]
    objective: DesirabilityObjective


class DesirabilityMomentResult(_StrictModel):
    mean: FiniteFloat = Field(ge=0, le=1)
    second_moment: FiniteFloat = Field(ge=0, le=1)
    variance: FiniteFloat = Field(ge=0, le=0.25)
    estimated_absolute_error: FiniteFloat = Field(ge=0)
    normal_tail_bound: FiniteFloat = Field(ge=0)
    integration_evaluations: int = Field(ge=0, le=80_000)

    @model_validator(mode="after")
    def validate_moments(self) -> DesirabilityMomentResult:
        tolerance = 64 * math.ulp(max(self.mean, self.second_moment, self.variance))
        if (
            self.variance > self.mean * (1 - self.mean) + tolerance
            or abs(self.second_moment - (self.mean**2 + self.variance)) > tolerance
        ):
            raise ValueError("bayesian_desirability_moments_invalid")
        return self


class _RawResponseModelFields(_StrictModel):
    factor_ids: list[Identifier] = Field(min_length=1, max_length=10)
    signal_kernel: BayesianSelectedSignalKernel
    noise: BayesianFittedNoise
    observation_noise_sd_raw: FiniteFloat = Field(ge=0)
    jitter: FiniteFloat = Field(ge=1e-12, le=1e-3)
    normalization: BayesianNoiseNormalization
    optimizer: BayesianNoiseOptimizer
    log_marginal_likelihood: FiniteFloat
    raw_observation_count: int = Field(ge=2, le=200)
    effective_training_count: int = Field(ge=2, le=200)
    training_group_counts: list[int] = Field(min_length=2, max_length=200)
    fit_elapsed_ms: FiniteFloat = Field(ge=0)
    package_versions: dict[str, str] = Field(max_length=10)


class DesirabilityRawResponseModel(_RawResponseModelFields):
    schema_version: Literal[4]
    policy_version: Literal["bo_noise_latent_kernels_v3"]


class _ResponseModelResult(_StrictModel):
    response_id: Identifier
    model: DesirabilityRawResponseModel
    observation_view: BayesianObservationViewSummary


class _Weight(_StrictModel):
    response_id: Identifier
    weight: FiniteFloat = Field(gt=0, le=1)


class _SharedModelFields(_StrictModel):
    policy_version: Literal[1]
    factor_ids: list[Identifier] = Field(min_length=1, max_length=10)
    response_ids: list[Identifier] = Field(min_length=1, max_length=4)
    normalized_importance: list[_Weight] = Field(min_length=1, max_length=4)
    curve_policy: Literal["derringer_suich_linear_v1"]
    moment_policy: Literal["independent_latent_gaussian_split_quadrature_v1"]
    independence_assumption: Literal[True]


class _SharedModel(_SharedModelFields):
    schema_version: Literal[5]
    response_models: list[_ResponseModelResult] = Field(min_length=1, max_length=4)


class _ObservedDesirability(_StrictModel):
    trial_id: TrialId
    value: FiniteFloat = Field(ge=0, le=1)


class _PosteriorDesirability(_StrictModel):
    trial_id: TrialId
    moments: DesirabilityMomentResult


class _Incumbent(_StrictModel):
    policy: Literal["max_posterior_expected_desirability_at_observed_coordinates_v1"]
    best_observed_desirability: FiniteFloat = Field(ge=0, le=1)
    best_observed_trial_id: TrialId
    latent_incumbent_value: FiniteFloat = Field(ge=0, le=1)
    latent_incumbent_trial_id: TrialId
    latent_incumbent_normalized_coordinates: dict[Identifier, FiniteFloat]
    observed_trial_desirabilities: list[_ObservedDesirability] = Field(min_length=2, max_length=200)
    training_posterior_desirabilities: list[_PosteriorDesirability] = Field(
        min_length=2, max_length=200
    )


class _SharedObservationGroup(_StrictModel):
    member_trial_ids: list[TrialId] = Field(min_length=1, max_length=200)
    member_indices: list[int] = Field(min_length=1, max_length=200)
    canonical_actual_coordinates: dict[Identifier, FiniteFloat]
    canonical_level_indices: dict[Identifier, int | None]
    condition_key: str | None
    n: int = Field(ge=1, le=200)


class _SharedObservationView(_StrictModel):
    mode: Literal["retain_raw", "exact_replicates", "nearby_diagnostics"]
    raw_observation_count: int = Field(ge=2, le=200)
    unique_condition_count: int = Field(ge=2, le=200)
    unique_coordinate_count: int = Field(ge=2, le=200)
    effective_training_count: int = Field(ge=2, le=200)
    groups: list[_SharedObservationGroup] = Field(min_length=2, max_length=200)


class _ResponsePrediction(_StrictModel):
    response_id: Identifier
    mean_raw: FiniteFloat
    latent_standard_deviation_raw: FiniteFloat = Field(ge=0)
    predictive_standard_deviation_raw: FiniteFloat = Field(ge=0)


class _Acquisition(_StrictModel):
    kind: Literal["desirability_beta_expected_improvement"]
    value: FiniteFloat = Field(ge=0, le=1)
    threshold: FiniteFloat = Field(ge=0)
    distribution: Literal["point_mass", "bernoulli_limit", "beta_moment_match"]
    alpha: FiniteFloat | None = Field(gt=0)
    beta: FiniteFloat | None = Field(gt=0)
    xi_desirability: FiniteFloat = Field(ge=0)


class _Candidate(_StrictModel):
    rank: Literal[1]
    actual_coordinates: dict[Identifier, FiniteFloat]
    normalized_coordinates: dict[Identifier, FiniteFloat]
    response_predictions: list[_ResponsePrediction] = Field(min_length=1, max_length=4)
    desirability_moments: DesirabilityMomentResult
    acquisition: _Acquisition
    nearest_existing_distance: FiniteFloat = Field(ge=0)
    constraint_evaluations: list[BayesianConstraintEvaluationResponse] = Field(max_length=16)


class _Budget(_StrictModel):
    max_evaluations_total: int = Field(ge=32, le=160_000)
    evaluations_consumed: int = Field(ge=1)
    evaluation_unit: Literal["candidate_with_all_response_desirability_moments"]
    posterior_evaluations: int = Field(ge=1)
    integrand_evaluations: int = Field(ge=0)
    response_fit_count: int = Field(ge=1, le=4)
    model_max_evaluations_total: int = Field(ge=2, le=2000)
    model_evaluations_consumed: int = Field(ge=0, le=2000)
    final_factorizations: int = Field(ge=1, le=4)
    time_budget_ms: int = Field(ge=1000, le=60_000)
    elapsed_ms: FiniteFloat = Field(ge=0)
    searches: list[BayesianMixedSearchSummary] = Field(min_length=1, max_length=1)
    termination_reason: str = Field(min_length=1, max_length=100)


class DesirabilityCalculationResult(_StrictModel):
    schema_version: Literal[4]
    batch_size: Literal[1]
    policy: Literal["independent_latent_desirability_beta_ei_v1"]
    objective: DesirabilityObjective
    shared_model: _SharedModel
    incumbent: _Incumbent
    observation_view: _SharedObservationView
    items: list[_Candidate] = Field(min_length=1, max_length=1)
    search_budget: _Budget
    warnings: list[str] = Field(max_length=64)
    limitations: list[str] = Field(max_length=32)
