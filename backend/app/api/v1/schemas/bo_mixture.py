"""Opt-in study-8 mixture contracts; legacy study payloads remain unchanged."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    JsonValue,
    RootModel,
    model_validator,
)

from app.api.v1.schemas.bayesian import (
    BayesianHistoryRevisionResponse,
    BayesianLinearConstraintRequest,
)
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityMomentResult,
    _Acquisition,
    _ResponsePrediction,
)
from app.api.v1.schemas.bo_mixed_studies import (
    MixedCategoricalFactorRequest,
    MixedFactorRequest,
    mixed_constraint_definitions,
)
from app.api.v1.schemas.bo_mixed_workflow import MixedCandidateImport, MixedSourceRequest
from app.api.v1.schemas.bo_planning import CandidateGeneration, Sha256
from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoFactorDomain,
    BoNumericFactorDomain,
)
from app.statistics.bo_mixture_design import BoMixtureDesign
from app.statistics.bo_mixture_domain import BoMixtureComponent, BoMixtureDomain
from app.statistics.doe_factor_domain import DoeFactorDomain


class MixtureComponentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    name: str = Field(min_length=1, max_length=80)
    low: FiniteFloat = Field(ge=0, strict=True)
    high: FiniteFloat = Field(ge=0, strict=True)
    unit: str = Field(min_length=1, max_length=40)


class MixtureGroupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: FiniteFloat = Field(gt=0, strict=True)
    coding: Literal["lower", "upper", "auto"]
    components: list[MixtureComponentRequest] = Field(min_length=2, max_length=8)

    def domain(self) -> BoMixtureDomain:
        return BoMixtureDomain(
            tuple(BoMixtureComponent(c.factor_id, c.low, c.high, c.unit) for c in self.components),
            self.total,
            self.coding,
        )

    @model_validator(mode="after")
    def valid_domain(self) -> MixtureGroupRequest:
        self.domain()
        if any(not c.name.strip() for c in self.components):
            raise ValueError("bayesian_study_name_invalid")
        return self


class MixtureStudyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[8]
    name: str = Field(min_length=1, max_length=120)
    mixture: MixtureGroupRequest
    process_factors: list[MixedFactorRequest] = Field(default_factory=list, max_length=8)
    objective: AnyDesirabilityObjective
    constraints: list[BayesianLinearConstraintRequest] = Field(default_factory=list, max_length=16)

    @model_validator(mode="before")
    @classmethod
    def integer_version(cls, value: Any) -> Any:
        if isinstance(value, dict) and type(value.get("schema_version")) is not int:
            raise ValueError("bayesian_mixture_study_version_invalid")
        return value

    def domain(self) -> BoMixtureDesign:
        process: list[BoFactorDomain] = []
        for factor in self.process_factors:
            if isinstance(factor, MixedCategoricalFactorRequest):
                process.append(
                    BoCategoricalFactorDomain(
                        factor.factor_id,
                        factor.domain_kind,
                        tuple(factor.levels),
                        factor.correlation_policy,
                    )
                )
            else:
                process.append(
                    BoNumericFactorDomain(
                        factor.factor_id,
                        DoeFactorDomain(
                            factor.low,
                            factor.high,
                            factor.domain_kind,
                            factor.step,
                            factor.display_decimals,
                        ),
                    )
                )
        return BoMixtureDesign(
            self.mixture.domain(), tuple(process), mixed_constraint_definitions(self.constraints)
        )

    @model_validator(mode="after")
    def valid_study(self) -> MixtureStudyDefinition:
        self.domain()
        if not self.name.strip() or any(not f.name.strip() for f in self.process_factors):
            raise ValueError("bayesian_study_name_invalid")
        return self


class MixtureStudyCreateRequest(MixtureStudyDefinition):
    initial_design_seed: int = Field(ge=0, le=2**31 - 1, strict=True)
    initial_design_size: int = Field(ge=2, le=64, strict=True)

    @model_validator(mode="after")
    def valid_initial_size(self) -> MixtureStudyCreateRequest:
        if self.initial_design_size < max(2, len(self.domain().keys)):
            raise ValueError("bayesian_study_initial_design_too_small")
        return self


class MixtureTrialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_id: UUID
    study_version_id: UUID
    trial_number: int = Field(ge=1, le=200)
    origin: Literal["initial_design", "recommendation", "replicate"]
    state: Literal["pending", "completed", "abandoned"]
    actual_coordinates: dict[str, float | str]
    encoded_coordinates: dict[str, FiniteFloat]
    coordinate_encoding: Literal["mixture_pseudocomponents_process_v1"] = (
        "mixture_pseudocomponents_process_v1"
    )
    coordinates_sha256: str
    objective_value: None = None
    response_values: dict[str, FiniteFloat] | None
    created_at: str
    closed_at: str | None
    replicate_of_trial_id: UUID | None = None


class MixtureStudyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    version_number: Literal[1] = 1
    study_schema_version: Literal[8] = 8
    method_id: Literal["doe.bayesian_optimization"] = "doe.bayesian_optimization"
    method_version: str
    name: str
    status: Literal["active", "completed", "abandoned"]
    predecessor_study_id: None = None
    created_at: str
    updated_at: str
    app_version: str
    definition_sha256: str
    mixture: MixtureGroupRequest
    process_factors: list[MixedFactorRequest]
    factors: list[dict[str, JsonValue]]
    design_domain: dict[str, JsonValue]
    objective: AnyDesirabilityObjective
    constraints: list[BayesianLinearConstraintRequest]
    initial_design: dict[str, JsonValue]
    trial_count: int = Field(ge=1, le=200)
    pending_trial_count: int = Field(ge=0, le=200)
    completed_trial_count: int = Field(ge=0, le=200)
    abandoned_trial_count: int = Field(ge=0, le=200)
    observation_history: BayesianHistoryRevisionResponse
    trials: list[MixtureTrialResponse]
    surrogate_available: bool
    recommendation_available: bool
    recommendation_workflow: Literal["fixed_candidate_mixture_planning_v1"] = (
        "fixed_candidate_mixture_planning_v1"
    )
    recommendation_minimum_completed_observations: int
    recommendation_hard_trial_limit: Literal[200] = 200
    recommendation_blockers: list[str]
    lifecycle_event: dict[str, JsonValue] | None


class MixtureSourceRequest(MixedSourceRequest):
    @model_validator(mode="before")
    @classmethod
    def integer_version(cls, value: Any) -> Any:
        if (
            isinstance(value, dict)
            and "schema_version" in value
            and type(value["schema_version"]) is not int
        ):
            raise ValueError("bayesian_mixture_planning_input_invalid")
        return value


class MixtureCandidateCreateRequest(MixtureSourceRequest):
    schema_version: Literal[4] = 4
    request_id: UUID
    candidate_set_id: UUID
    name: str = Field(min_length=1, max_length=120)
    expected_head_revision_id: UUID | None = None
    model_id: UUID
    expected_model_sha256: Sha256
    source: CandidateGeneration | MixedCandidateImport
    time_budget_ms: int = Field(default=60000, ge=1000, le=60000, strict=True)
    max_moment_evaluations: int = Field(default=16384, ge=1, le=65536, strict=True)


class MixtureSelectionCreateRequest(MixtureSourceRequest):
    schema_version: Literal[6] = 6
    request_id: UUID
    candidate_revision_id: UUID
    expected_rows_sha256: Sha256
    model_id: UUID
    expected_model_sha256: Sha256
    policy: Literal["manual_mixture_base_posterior_v1", "greedy_mixture_maximin_v1"]
    row_ids: list[Sha256] = Field(default_factory=list, max_length=8)
    batch_size: int = Field(ge=1, le=8, strict=True)
    total_trial_budget: int = Field(ge=2, le=200, strict=True)
    min_batch_distance: FiniteFloat = Field(default=0, ge=0)
    time_budget_ms: int = Field(default=60000, ge=1000, le=60000, strict=True)
    max_moment_evaluations: int = Field(default=16384, ge=1, le=65536, strict=True)

    @model_validator(mode="after")
    def coherent_selection(self) -> MixtureSelectionCreateRequest:
        if self.policy == "manual_mixture_base_posterior_v1":
            if len(self.row_ids) != self.batch_size or len(set(self.row_ids)) != self.batch_size:
                raise ValueError("bayesian_planning_selection_invalid")
        elif self.row_ids:
            raise ValueError("bayesian_planning_selection_invalid")
        return self


class MixtureArtifactResponse(RootModel[dict[str, JsonValue]]):
    """Server-owned artifact envelope; calculation rows have strict DTOs below."""


class MixtureEvaluatedRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[4]
    row_id: Sha256
    source_row_number: int = Field(ge=1, le=10000)
    input_coordinates: dict[str, float | str]
    actual_coordinates: dict[str, float | str]
    encoded_coordinates: dict[str, FiniteFloat]
    coordinate_encoding: Literal["mixture_pseudocomponents_process_v1"]
    distance_policy: Literal["mixture_actual_bound_width_process_v1"]
    constraints_satisfied: bool
    nearest_existing_distance: FiniteFloat | None = Field(ge=0)
    novel: bool
    eligible: bool
    response_predictions: list[_ResponsePrediction] = Field(min_length=1, max_length=4)
    desirability_moments: DesirabilityMomentResult
    acquisition: _Acquisition | None
    prediction_source: Literal["completed_observations_base_posterior"]

    @model_validator(mode="after")
    def coherent_eligibility(self) -> MixtureEvaluatedRow:
        if self.eligible != (self.novel and self.constraints_satisfied):
            raise ValueError("bayesian_mixture_planning_input_invalid")
        return self


class MixtureSelectionItem(MixtureEvaluatedRow):
    rank: int = Field(ge=1, le=8)
    nearest_selected_distance: FiniteFloat | None = Field(ge=0)


class MixtureSelectionCalculation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[13]
    selection_policy: Literal["manual_mixture_base_posterior_v1", "greedy_mixture_maximin_v1"]
    model_refit: Literal[False]
    distance_policy: Literal["mixture_actual_bound_width_process_v1"]
    joint_improvement_claimed: Literal[False]
    items: list[MixtureSelectionItem] = Field(min_length=1, max_length=8)
