"""Source-locked candidate revisions, fitted model views and ordered selections."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.api.v1.schemas.bayesian import BayesianConstraintEvaluationResponse
from app.api.v1.schemas.bayesian_desirability import DesirabilityObjective
from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityCurveReviewRequest,
    DesirabilityFitReviewRequest,
    DesirabilityOrderedReviewRequest,
)
from app.api.v1.schemas.bo_curve_policy import VersionedCurveObjective
from app.api.v1.schemas.bo_desirability_batch_calculation import _PlanningProof, _Sampler
from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityMomentResult,
    Identifier,
    _Acquisition,
    _Incumbent,
    _ResponseModelResult,
    _ResponsePrediction,
    _SharedObservationView,
)
from app.api.v1.schemas.bo_fit_quality import _ResponseModel

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Numeric = Annotated[FiniteFloat, Field(strict=True)]
Coordinates = Annotated[dict[Identifier, Numeric], Field(min_length=1, max_length=10)]
PlanningFitOptions = Annotated[
    DesirabilityOrderedReviewRequest
    | DesirabilityFitReviewRequest
    | DesirabilityCurveReviewRequest,
    Field(discriminator="schema_version"),
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanningModelCreateRequest(_Model):
    request_id: UUID
    fit: PlanningFitOptions


class PlanningModelSummary(_Model):
    schema_version: Literal[1] = 1
    model_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    history_sha256: Sha256
    definition_sha256: Sha256
    snapshot_sha256: Sha256
    config_sha256: Sha256
    created_at: str
    source_is_current: bool


class PlanningModelDetail(PlanningModelSummary):
    fit: PlanningFitOptions
    objective: DesirabilityObjective | VersionedCurveObjective
    response_models: list[_ResponseModelResult | _ResponseModel] = Field(min_length=1, max_length=4)
    incumbent: _Incumbent
    observation_view: _SharedObservationView
    warnings: list[str] = Field(max_length=64)
    model_reusable_without_refit: Literal[True] = True


class PlanningModelList(_Model):
    items: list[PlanningModelSummary] = Field(max_length=32)


class PlanningSourceRequest(_Model):
    model_id: UUID
    expected_model_sha256: Sha256
    expected_history_revision_id: UUID
    expected_history_sha256: Sha256
    expected_trial_count: int = Field(ge=1, le=200, strict=True)


class CandidateGeneration(_Model):
    kind: Literal["seeded_uniform"]
    count: int = Field(ge=1, le=10000, strict=True)
    seed: int = Field(ge=0, le=2_147_483_647, strict=True)


class CandidateImport(_Model):
    kind: Literal["explicit_rows"]
    points: list[Coordinates] = Field(min_length=1, max_length=10000)


class CandidateAppend(_Model):
    kind: Literal["append_rows"]
    points: list[Coordinates] = Field(min_length=1, max_length=100)


class CandidateRemove(_Model):
    kind: Literal["remove_rows"]
    row_ids: list[Sha256] = Field(min_length=1, max_length=100)


class CandidateRevisionCreateRequest(PlanningSourceRequest):
    request_id: UUID
    candidate_set_id: UUID
    name: str = Field(min_length=1, max_length=120)
    expected_head_revision_id: UUID | None
    source: Annotated[
        CandidateGeneration | CandidateImport | CandidateAppend | CandidateRemove,
        Field(discriminator="kind"),
    ]
    include_constraint_violations: bool = False

    @model_validator(mode="after")
    def patch_needs_parent(self) -> CandidateRevisionCreateRequest:
        if (
            self.source.kind in {"append_rows", "remove_rows"}
            and self.expected_head_revision_id is None
        ):
            raise ValueError("bayesian_candidate_revision_conflict")
        return self


class CandidateRow(_Model):
    row_id: Sha256
    source_row_number: int = Field(ge=1, le=10000)
    input_coordinates: Coordinates
    canonical_level_indices: dict[Identifier, int | None]
    actual_coordinates: Coordinates
    normalized_coordinates: Coordinates
    constraint_evaluations: list[BayesianConstraintEvaluationResponse] = Field(max_length=16)
    constraints_satisfied: bool
    nearest_existing_distance: FiniteFloat | None = Field(ge=0)
    novel: bool
    eligible: bool


class EvaluatedCandidateRow(CandidateRow):
    response_predictions: list[_ResponsePrediction] = Field(min_length=1, max_length=4)
    desirability_moments: DesirabilityMomentResult
    acquisition: _Acquisition
    prediction_source: Literal["completed_observations_base_posterior"]


class CandidateRevisionSummary(_Model):
    schema_version: Literal[1] = 1
    candidate_set_id: UUID
    name: str
    revision_id: UUID
    revision_number: int = Field(ge=1, le=64)
    parent_revision_id: UUID | None
    model_id: UUID
    model_sha256: Sha256
    rows_sha256: Sha256
    config_sha256: Sha256
    excluded_coordinates_sha256: Sha256
    source_trial_count: int = Field(ge=1, le=200)
    row_count: int = Field(ge=1, le=10000)
    eligible_count: int = Field(ge=0, le=10000)
    created_at: str
    source_is_current: bool


class CandidateSetList(_Model):
    items: list[CandidateRevisionSummary] = Field(max_length=32)


class CandidatePage(_Model):
    revision: CandidateRevisionSummary
    offset: int = Field(ge=0, le=10000)
    limit: int = Field(ge=1, le=100)
    items: list[CandidateRow] = Field(max_length=100)


class PlanningEvaluationRequest(_Model):
    expected_model_sha256: Sha256
    points: list[Coordinates] = Field(min_length=1, max_length=100)
    time_budget_ms: int = Field(default=60000, ge=1000, le=60000, strict=True)


class PlanningEvaluationResponse(_Model):
    schema_version: Literal[1] = 1
    model_id: UUID
    model_sha256: Sha256
    request_sha256: Sha256
    items: list[EvaluatedCandidateRow] = Field(min_length=1, max_length=100)
    source_is_current: bool
    eligibility_source_trial_count: int = Field(ge=1, le=200)
    eligibility_coordinates_sha256: Sha256
    eligibility_is_current: bool
    model_refit: Literal[False] = False


class PlanningSelectionCreateRequest(PlanningSourceRequest):
    request_id: UUID
    candidate_revision_id: UUID
    expected_rows_sha256: Sha256
    row_ids: list[Sha256] = Field(min_length=1, max_length=8)
    total_trial_budget: int = Field(ge=2, le=200, strict=True)

    @model_validator(mode="after")
    def unique_ordered_rows(self) -> PlanningSelectionCreateRequest:
        if len(set(self.row_ids)) != len(self.row_ids):
            raise ValueError("bayesian_planning_selection_invalid")
        return self


class ManualPlanningScore(_Model):
    score: FiniteFloat = Field(ge=0, le=1)
    mc_standard_error: FiniteFloat = Field(ge=0, le=0.5)
    sampler: _Sampler
    conditional_variance_raw: dict[Identifier, FiniteFloat]
    proof: _PlanningProof


class PlanningSelectionItem(CandidateRow):
    rank: int = Field(ge=1, le=8)
    nearest_selected_distance: FiniteFloat | None = Field(ge=0)
    response_predictions: list[_ResponsePrediction] = Field(min_length=1, max_length=4)
    desirability_moments: DesirabilityMomentResult
    acquisition: _Acquisition
    planning: ManualPlanningScore


class PlanningSelectionCalculation(_Model):
    schema_version: Literal[1]
    selection_policy: Literal["manual_ordered_fixed_model_v1"]
    model_refit: Literal[False]
    items: list[PlanningSelectionItem] = Field(min_length=1, max_length=8)
    moment_evaluations: int = Field(ge=1, le=65536)
    max_moment_evaluations: int = Field(ge=1, le=65536)

    @model_validator(mode="after")
    def check_order(self) -> PlanningSelectionCalculation:
        if (
            [item.rank for item in self.items] != list(range(1, len(self.items) + 1))
            or len({item.row_id for item in self.items}) != len(self.items)
            or self.moment_evaluations > self.max_moment_evaluations
            or any(not item.eligible for item in self.items)
        ):
            raise ValueError("bayesian_planning_selection_invalid")
        return self


class PlanningSelectionResponse(_Model):
    schema_version: Literal[1] = 1
    selection_id: UUID
    study_id: UUID
    study_version_id: UUID
    model_id: UUID
    model_sha256: Sha256
    candidate_revision_id: UUID
    rows_sha256: Sha256
    config_sha256: Sha256
    result_sha256: Sha256
    request: PlanningSelectionCreateRequest
    calculation: PlanningSelectionCalculation
    created_at: str
    source_is_current: bool
    confirmed_batch_id: UUID | None


class PlanningSelectionSummary(_Model):
    selection_id: UUID
    study_id: UUID
    study_version_id: UUID
    model_id: UUID
    candidate_revision_id: UUID
    config_sha256: Sha256
    result_sha256: Sha256
    selected_count: int = Field(ge=1, le=8, strict=True)
    created_at: str
    source_is_current: bool
    confirmed_batch_id: UUID | None


class PlanningSelectionList(_Model):
    items: list[PlanningSelectionSummary] = Field(max_length=32)


class PlanningConfirmRequest(_Model):
    expected_config_sha256: Sha256
    expected_result_sha256: Sha256
