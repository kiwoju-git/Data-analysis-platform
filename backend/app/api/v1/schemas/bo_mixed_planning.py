"""Internal mixed-factor planning; category codes never imply numeric distance."""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictFloat,
    StrictStr,
    model_validator,
)

from app.api.v1.schemas.bayesian import BayesianLinearConstraintRequest
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_desirability_batch_calculation import _PlanningProof, _Sampler
from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityMomentResult,
    DesirabilityResponseModelRequest,
    DesirabilitySearch,
    Identifier,
    _Acquisition,
    _ResponsePrediction,
)
from app.api.v1.schemas.bo_mixed_studies import (
    MixedFactorRequest,
    mixed_constraint_definitions,
    mixed_factor_domains,
)
from app.statistics.bo_factor_domains import BoCategoricalFactorDomain, encode_bo_point
from app.statistics.bo_mixed_initial_design import (
    mixed_constraints_satisfied,
    validate_mixed_constraints,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


ActualPoint = Annotated[
    dict[Identifier, StrictFloat | StrictStr], Field(min_length=1, max_length=10)
]
EncodedPoint = Annotated[dict[Identifier, FiniteFloat], Field(min_length=1, max_length=10)]


class MixedPlanningObservation(_Model):
    trial_id: Annotated[UUID, Field(strict=False)]
    actual_coordinates: ActualPoint
    encoded_coordinates: EncodedPoint
    response_values: dict[Identifier, FiniteFloat] = Field(min_length=1, max_length=4)
    condition_key: str | None = Field(default=None, max_length=128)


class MixedPlanningObservationPolicy(_Model):
    mode: Literal["retain_raw", "exact_replicates"]
    nearby_tolerances: None = None
    nearby_units: Literal["actual", "normalized"] = "normalized"


class MixedPlanningFitPolicy(_Model):
    policy: Literal["bounded_typed_factor_starts_v1"] = "bounded_typed_factor_starts_v1"
    deterministic_start_count: int = Field(default=3, ge=1, le=3)


class MixedPlanningCalculationRequest(_Model):
    schema_version: Literal[8]
    factors: list[MixedFactorRequest] = Field(min_length=1, max_length=10)
    constraints: list[BayesianLinearConstraintRequest] = Field(max_length=16)
    observations: list[MixedPlanningObservation] = Field(min_length=2, max_length=200)
    excluded_encoded: list[Annotated[list[FiniteFloat], Field(min_length=1, max_length=10)]] = (
        Field(max_length=200)
    )
    objective: AnyDesirabilityObjective
    response_models: list[DesirabilityResponseModelRequest] = Field(min_length=1, max_length=4)
    observation_policy: MixedPlanningObservationPolicy
    xi_desirability: FiniteFloat = Field(ge=0)
    search: DesirabilitySearch
    fit_policy: MixedPlanningFitPolicy = Field(default_factory=MixedPlanningFitPolicy)
    max_moment_evaluations: int = Field(default=4096, ge=1, le=65536)

    @model_validator(mode="before")
    @classmethod
    def version_is_integer(cls, value: Any) -> Any:
        if isinstance(value, dict) and type(value.get("schema_version")) is not int:
            raise ValueError("bayesian_mixed_planning_input_invalid")
        return value

    @model_validator(mode="after")
    def exact_source(self) -> MixedPlanningCalculationRequest:
        domains = mixed_factor_domains(self.factors)
        constraints = mixed_constraint_definitions(self.constraints)
        validate_mixed_constraints(domains, constraints)
        keys = [domain.factor_id for domain in domains]
        response_ids = {goal.response_id for goal in self.objective.responses}
        model_ids = [model.response_id for model in self.response_models]
        if len(set(model_ids)) != len(model_ids) or set(model_ids) != response_ids:
            raise ValueError("bayesian_desirability_response_mapping_invalid")
        trial_ids = [row.trial_id for row in self.observations]
        if len(set(trial_ids)) != len(trial_ids):
            raise ValueError("bayesian_observation_identity_invalid")
        unique = set()
        for row in self.observations:
            encoded = encode_bo_point(domains, row.actual_coordinates)
            if (
                set(row.encoded_coordinates) != set(keys)
                or set(row.response_values) != response_ids
            ):
                raise ValueError("bayesian_observation_identity_invalid")
            for index, key in enumerate(keys):
                supplied = row.encoded_coordinates[key]
                same = (
                    supplied == encoded[index]
                    if isinstance(domains[index], BoCategoricalFactorDomain)
                    else math.isclose(
                        supplied, encoded[index], rel_tol=0, abs_tol=16 * math.ulp(encoded[index])
                    )
                )
                if not same:
                    raise ValueError("bayesian_observation_identity_invalid")
            if not mixed_constraints_satisfied(row.actual_coordinates, constraints):
                raise ValueError("bayesian_candidate_constraint_violation")
            unique.add(tuple(row.actual_coordinates[key] for key in keys))
        if len(unique) < max(2, len(domains) + 1):
            raise ValueError("bayesian_unique_conditions_insufficient")
        for point in self.excluded_encoded:
            if len(point) != len(domains):
                raise ValueError("bayesian_point_shape_invalid")
            for domain, value in zip(domains, point, strict=True):
                domain.decode(value)
        return self

    def worker_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MixedConstraintEvaluation(_Model):
    constraint_id: str
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    lhs: FiniteFloat
    bound: FiniteFloat
    slack: FiniteFloat
    satisfied: bool


class MixedCandidateRow(_Model):
    schema_version: Literal[2]
    row_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_row_number: int = Field(ge=1, le=10000)
    input_coordinates: ActualPoint
    actual_coordinates: ActualPoint
    encoded_coordinates: EncodedPoint
    coordinate_encoding: Literal["numeric_normalized_category_index_v1"]
    distance_policy: Literal[
        "numeric_normalized_category_hamming_v1",
        "numeric_normalized_nominal_hamming_ordinal_rank_v1",
    ]
    ordinal_rank_distance: bool
    canonical_level_indices: dict[Identifier, int | None]
    constraint_evaluations: list[MixedConstraintEvaluation] = Field(max_length=16)
    constraints_satisfied: bool
    nearest_existing_distance: FiniteFloat | None = Field(ge=0)
    novel: bool
    eligible: bool

    @model_validator(mode="after")
    def coherent_row(self) -> MixedCandidateRow:
        expected = (
            "numeric_normalized_nominal_hamming_ordinal_rank_v1"
            if self.ordinal_rank_distance
            else "numeric_normalized_category_hamming_v1"
        )
        if self.distance_policy != expected or self.eligible != (
            self.novel and self.constraints_satisfied
        ):
            raise ValueError("bayesian_mixed_candidate_invalid")
        return self


class EvaluatedMixedCandidateRow(MixedCandidateRow):
    response_predictions: list[_ResponsePrediction] = Field(min_length=1, max_length=4)
    desirability_moments: DesirabilityMomentResult
    acquisition: _Acquisition | None
    prediction_source: Literal["completed_observations_base_posterior"]


class MixedPlanningSampler(_Sampler):
    coordinate_encoding: Literal["numeric_normalized_category_index_v1"]


class MixedManualPlanningScore(_Model):
    score: FiniteFloat = Field(ge=0, le=1)
    mc_standard_error: FiniteFloat = Field(ge=0, le=0.5)
    sampler: MixedPlanningSampler
    conditional_variance_raw: dict[Identifier, FiniteFloat] = Field(min_length=1, max_length=4)
    proof: _PlanningProof


class MixedPlanningSelectionItem(EvaluatedMixedCandidateRow):
    acquisition: _Acquisition
    rank: int = Field(ge=1, le=8)
    nearest_selected_distance: FiniteFloat | None = Field(ge=0)
    planning: MixedManualPlanningScore


class MixedPlanningSelectionCalculation(_Model):
    schema_version: Literal[2]
    selection_policy: Literal["manual_ordered_mixed_model_v1"]
    model_refit: Literal[False]
    distance_policy: Literal[
        "numeric_normalized_category_hamming_v1",
        "numeric_normalized_nominal_hamming_ordinal_rank_v1",
    ]
    ordinal_rank_distance: bool
    items: list[MixedPlanningSelectionItem] = Field(min_length=1, max_length=8)
    moment_evaluations: int = Field(ge=1, le=65536)
    max_moment_evaluations: int = Field(ge=1, le=65536)

    @model_validator(mode="after")
    def ordered_complete_selection(self) -> MixedPlanningSelectionCalculation:
        if (
            [item.rank for item in self.items] != list(range(1, len(self.items) + 1))
            or len({item.row_id for item in self.items}) != len(self.items)
            or any(not item.eligible for item in self.items)
            or any(
                item.distance_policy != self.distance_policy
                or item.ordinal_rank_distance != self.ordinal_rank_distance
                for item in self.items
            )
            or self.moment_evaluations > self.max_moment_evaluations
        ):
            raise ValueError("bayesian_planning_selection_invalid")
        return self
