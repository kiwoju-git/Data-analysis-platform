"""Schema-7 study contracts; legacy scalar/numeric response classes stay unchanged."""

from __future__ import annotations

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

from app.api.v1.schemas.bayesian import (
    BayesianFactorRequest,
    BayesianFactorResponse,
    BayesianHistoryRevisionResponse,
    BayesianLinearConstraintRequest,
    BayesianLinearConstraintResponse,
    BayesianStudyLifecycleEventResponse,
    BayesianStudyStatus,
)
from app.api.v1.schemas.bayesian_desirability import ResponseValues
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_dataset_source import DatasetImportedInitialDesign
from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoCorrelationPolicy,
    BoFactorDomain,
    BoNumericFactorDomain,
    validate_bo_factor_domains,
)
from app.statistics.bo_mixed_initial_design import MixedLinearConstraint, validate_mixed_constraints
from app.statistics.doe_factor_domain import DoeFactorDomain

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class MixedCategoricalFactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
    name: str = Field(min_length=1, max_length=80)
    unit: str | None = Field(default=None, max_length=40)
    domain_kind: Literal["nominal", "ordinal"]
    levels: list[StrictStr] = Field(min_length=2, max_length=32)
    correlation_policy: BoCorrelationPolicy

    @model_validator(mode="after")
    def validate_domain(self) -> MixedCategoricalFactorRequest:
        BoCategoricalFactorDomain(
            self.factor_id, self.domain_kind, tuple(self.levels), self.correlation_policy
        )
        return self


class MixedCategoricalFactorResponse(MixedCategoricalFactorRequest):
    order: int = Field(ge=1, le=10)
    encoding_rule: Literal["declared_level_index_v1"] = "declared_level_index_v1"


MixedFactorRequest = Annotated[
    BayesianFactorRequest | MixedCategoricalFactorRequest, Field(discriminator="domain_kind")
]
MixedFactorResponse = Annotated[
    BayesianFactorResponse | MixedCategoricalFactorResponse, Field(discriminator="domain_kind")
]


def mixed_factor_domains(factors: Any) -> tuple[BoFactorDomain, ...]:
    domains: list[BoFactorDomain] = []
    for item in factors:
        if isinstance(item, MixedCategoricalFactorRequest):
            domains.append(
                BoCategoricalFactorDomain(
                    item.factor_id, item.domain_kind, tuple(item.levels), item.correlation_policy
                )
            )
        else:
            domains.append(
                BoNumericFactorDomain(
                    item.factor_id,
                    DoeFactorDomain(
                        item.low, item.high, item.domain_kind, item.step, item.display_decimals
                    ),
                )
            )
    result = tuple(domains)
    validate_bo_factor_domains(result)
    if not any(isinstance(item, BoCategoricalFactorDomain) for item in result):
        raise ValueError("bayesian_mixed_factor_required")
    return result


def mixed_constraint_definitions(constraints: Any) -> tuple[MixedLinearConstraint, ...]:
    return tuple(
        MixedLinearConstraint(
            item.constraint_id,
            tuple((term.factor_id, float(term.coefficient)) for term in item.terms),
            item.relation,
            float(item.bound),
        )
        for item in constraints
    )


class MixedStudyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[7]
    name: str = Field(min_length=1, max_length=120)
    factors: list[MixedFactorRequest] = Field(min_length=1, max_length=10)
    objective: AnyDesirabilityObjective
    constraints: list[BayesianLinearConstraintRequest] = Field(default_factory=list, max_length=16)
    initial_design_seed: int = Field(ge=0, le=2**31 - 1, strict=True)
    initial_design_size: int = Field(ge=2, le=64, strict=True)
    initial_design_policy: Literal["sha256_counter_mixed_uniform_feasible_v1"] = (
        "sha256_counter_mixed_uniform_feasible_v1"
    )
    predecessor_study_id: UUID | None = None

    @model_validator(mode="after")
    def validate_source(self) -> MixedStudyCreateRequest:
        domains = mixed_factor_domains(self.factors)
        validate_mixed_constraints(domains, mixed_constraint_definitions(self.constraints))
        if not self.name.strip() or any(not item.name.strip() for item in self.factors):
            raise ValueError("bayesian_study_name_invalid")
        if self.initial_design_size < max(2, len(domains) + 1):
            raise ValueError("bayesian_study_initial_design_too_small")
        return self


class MixedInitialDesignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    policy: Literal["sha256_counter_mixed_uniform_feasible_v1"]
    seed: int = Field(ge=0, le=2**31 - 1)
    requested_size: int = Field(ge=2, le=64)
    generated_size: int = Field(ge=2, le=64)
    attempt_limit: int = Field(ge=1, le=64_000)
    attempts_consumed: int = Field(ge=1, le=64_000)
    rejected_duplicate_count: int = Field(ge=0)
    rejected_infeasible_count: int = Field(ge=0)
    coordinate_encoding: Literal["numeric_normalized_category_index_v1"]
    category_level_counts: dict[str, list[int]]
    unobserved_level_indices: dict[str, list[int]]
    warnings: list[Literal["bayesian_initial_category_levels_uncovered"]]


class MixedTrialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_id: UUID
    study_version_id: UUID
    trial_number: int = Field(ge=1, le=200)
    origin: Literal["initial_design", "recommendation", "replicate"]
    state: Literal["pending", "completed", "abandoned"]
    actual_coordinates: dict[str, StrictFloat | StrictStr]
    encoded_coordinates: dict[str, FiniteFloat]
    coordinate_encoding: Literal["numeric_normalized_category_index_v1"] = (
        "numeric_normalized_category_index_v1"
    )
    coordinates_sha256: Hash
    objective_value: None = None
    response_values: ResponseValues | None
    created_at: str
    closed_at: str | None
    replicate_of_trial_id: UUID | None = None


class MixedStudyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: UUID
    study_version_id: UUID
    version_number: Literal[1]
    study_schema_version: Literal[7]
    method_id: Literal["doe.bayesian_optimization"]
    method_version: str
    name: str
    status: BayesianStudyStatus
    predecessor_study_id: UUID | None
    created_at: str
    updated_at: str
    app_version: str
    definition_sha256: Hash
    factors: list[MixedFactorResponse]
    objective: AnyDesirabilityObjective
    constraints: list[BayesianLinearConstraintResponse]
    initial_design: MixedInitialDesignResponse | DatasetImportedInitialDesign
    trial_count: int = Field(ge=1, le=200)
    pending_trial_count: int = Field(ge=0, le=200)
    completed_trial_count: int = Field(ge=0, le=200)
    abandoned_trial_count: int = Field(ge=0, le=200)
    observation_history: BayesianHistoryRevisionResponse
    trials: list[MixedTrialResponse]
    surrogate_available: bool
    recommendation_available: bool
    recommendation_workflow: Literal["fixed_candidate_mixed_planning_v1"] = (
        "fixed_candidate_mixed_planning_v1"
    )
    recommendation_minimum_completed_observations: int = Field(ge=2, le=11)
    recommendation_hard_trial_limit: Literal[200] = 200
    recommendation_blockers: list[str]
    lifecycle_event: BayesianStudyLifecycleEventResponse | None


class MixedObservationBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_schema_version: Literal[2] = 2
    study: MixedStudyResponse
    completed_trial_ids: list[UUID]
    completed_trial_count: int = Field(ge=1, le=200)
    observation_history: BayesianHistoryRevisionResponse
    request_id: UUID
    created_at: str


class MixedTrialListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study_id: UUID
    study_version_id: UUID
    total: int = Field(ge=0, le=200)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[MixedTrialResponse]


class MixedTrialTransitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study_id: UUID
    trial: MixedTrialResponse
    observation_history: BayesianHistoryRevisionResponse


class MixedStudyCloseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study: MixedStudyResponse
    lifecycle_event: BayesianStudyLifecycleEventResponse


class MixedReplicateCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[2] = 2
    study_id: UUID
    study_version_id: UUID
    request_id: UUID
    parent_trial_id: UUID
    source_history_revision_id: UUID
    source_history_sha256: Hash
    request_sha256: Hash
    trials: list[MixedTrialResponse] = Field(min_length=1, max_length=8)
    replayed: bool
