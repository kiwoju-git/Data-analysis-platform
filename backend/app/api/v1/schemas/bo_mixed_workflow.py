"""Public typed mixed-factor planning, distinct from legacy numeric contracts."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, JsonValue, model_validator

from app.api.v1.schemas.bo_augmentation import AugmentationPolicy, AugmentationTrace
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityMomentResult,
    DesirabilityResponseModelRequest,
    DesirabilitySearch,
)
from app.api.v1.schemas.bo_mixed_planning import (
    ActualPoint,
    EncodedPoint,
    EvaluatedMixedCandidateRow,
    MixedCandidateRow,
    MixedPlanningFitPolicy,
    MixedPlanningObservationPolicy,
    MixedPlanningSelectionCalculation,
)
from app.api.v1.schemas.bo_planning import CandidateGeneration, CandidateRemove, Sha256


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MixedSourceRequest(_Model):
    expected_study_version_id: UUID
    expected_definition_sha256: Sha256
    expected_history_revision_id: UUID
    expected_history_sha256: Sha256
    expected_trial_count: int = Field(ge=1, le=200, strict=True)


class MixedFitOptions(_Model):
    response_models: list[DesirabilityResponseModelRequest] = Field(min_length=1, max_length=4)
    observation_policy: MixedPlanningObservationPolicy
    xi_desirability: FiniteFloat = Field(ge=0)
    search: DesirabilitySearch
    fit_policy: MixedPlanningFitPolicy = Field(default_factory=MixedPlanningFitPolicy)
    max_moment_evaluations: int = Field(default=4096, ge=1, le=65536, strict=True)


class MixedModelCreateRequest(MixedSourceRequest):
    request_id: UUID
    fit: MixedFitOptions


class MixedModelSummary(_Model):
    schema_version: Literal[2] = 2
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


class MixedObservedDesirability(_Model):
    trial_id: UUID
    value: FiniteFloat = Field(ge=0, le=1)


class MixedTrainingDesirability(_Model):
    trial_id: UUID
    moments: DesirabilityMomentResult


class MixedIncumbent(_Model):
    policy: Literal["max_posterior_expected_desirability_at_observed_coordinates_v1"]
    best_observed_desirability: FiniteFloat = Field(ge=0, le=1)
    best_observed_trial_id: UUID
    latent_incumbent_value: FiniteFloat = Field(ge=0, le=1)
    latent_incumbent_trial_id: UUID
    latent_incumbent_encoded_coordinates: EncodedPoint
    coordinate_encoding: Literal["numeric_normalized_category_index_v1"]
    observed_trial_desirabilities: list[MixedObservedDesirability] = Field(max_length=200)
    training_posterior_desirabilities: list[MixedTrainingDesirability] = Field(max_length=200)


class MixedResponseModel(_Model):
    response_id: str
    # Each versioned kernel/fit receipt is validated by the safe snapshot reader.
    model: dict[str, JsonValue]
    observation_view: dict[str, JsonValue]


class MixedModelDetail(MixedModelSummary):
    fit: MixedFitOptions
    objective: AnyDesirabilityObjective
    response_models: list[MixedResponseModel] = Field(min_length=1, max_length=4)
    incumbent: MixedIncumbent
    observation_view: dict[str, JsonValue]
    warnings: list[str] = Field(max_length=128)
    model_reusable_without_refit: Literal[True] = True


class MixedModelList(_Model):
    items: list[MixedModelSummary] = Field(max_length=32)


class MixedEvaluationRequest(_Model):
    expected_model_sha256: Sha256
    points: list[ActualPoint] = Field(min_length=1, max_length=100)
    time_budget_ms: int = Field(default=60000, ge=1000, le=60000, strict=True)
    max_moment_evaluations: int = Field(default=4096, ge=1, le=65536, strict=True)


class MixedEvaluationResponse(_Model):
    model_id: UUID
    snapshot_sha256: Sha256
    items: list[EvaluatedMixedCandidateRow] = Field(min_length=1, max_length=100)
    model_refit: Literal[False] = False
    eligibility_history_sha256: Sha256
    eligibility_is_current: bool


class MixedCandidateImport(_Model):
    kind: Literal["explicit_rows"]
    points: list[ActualPoint] = Field(min_length=1, max_length=10000)


class MixedCandidateAppend(_Model):
    kind: Literal["append_rows"]
    points: list[ActualPoint] = Field(min_length=1, max_length=100)


class MixedCandidateCreateRequest(MixedSourceRequest):
    schema_version: Literal[3] = 3
    request_id: UUID
    candidate_set_id: UUID
    name: str = Field(min_length=1, max_length=120)
    expected_head_revision_id: UUID | None
    model_id: UUID | None = None
    expected_model_sha256: Sha256 | None = None
    duplicate_tolerance: FiniteFloat = Field(default=1e-6, ge=1e-12, le=0.1)
    ordinal_rank_distance: bool = False
    include_constraint_violations: bool = False
    source: Annotated[
        CandidateGeneration | MixedCandidateImport | MixedCandidateAppend | CandidateRemove,
        Field(discriminator="kind"),
    ]

    @model_validator(mode="after")
    def source_contract(self) -> "MixedCandidateCreateRequest":
        if (self.model_id is None) != (self.expected_model_sha256 is None):
            raise ValueError("bayesian_planning_model_mismatch")
        if (
            self.source.kind in {"append_rows", "remove_rows"}
            and self.expected_head_revision_id is None
        ):
            raise ValueError("bayesian_candidate_revision_conflict")
        return self


class MixedCandidateSummary(_Model):
    schema_version: Literal[3] = 3
    candidate_set_id: UUID
    name: str
    revision_id: UUID
    revision_number: int = Field(ge=1, le=64)
    parent_revision_id: UUID | None
    model_id: UUID | None
    model_sha256: Sha256 | None
    study_version_id: UUID
    source_history_revision_id: UUID
    definition_sha256: Sha256
    history_sha256: Sha256
    rows_sha256: Sha256
    config_sha256: Sha256
    excluded_coordinates_sha256: Sha256
    source_trial_count: int = Field(ge=1, le=200)
    duplicate_tolerance: FiniteFloat = Field(ge=1e-12, le=0.1)
    ordinal_rank_distance: bool
    row_count: int = Field(ge=1, le=10000)
    eligible_count: int = Field(ge=0, le=10000)
    created_at: str
    source_is_current: bool


class MixedCandidatePage(_Model):
    revision: MixedCandidateSummary
    offset: int = Field(ge=0, le=10000)
    limit: int = Field(ge=1, le=100)
    items: list[MixedCandidateRow] = Field(max_length=100)


class MixedCandidateList(_Model):
    items: list[MixedCandidateSummary] = Field(max_length=32)


class MixedSelectionRequest(MixedSourceRequest):
    schema_version: Literal[3] = 3
    request_id: UUID
    kind: Literal["manual_ordered", "augmentation"]
    candidate_revision_id: UUID
    expected_rows_sha256: Sha256
    model_id: UUID | None
    expected_model_sha256: Sha256 | None
    row_ids: list[Sha256] = Field(default_factory=list, max_length=8)
    policy: AugmentationPolicy | None = None
    batch_size: int = Field(ge=1, le=8, strict=True)
    total_trial_budget: int = Field(ge=2, le=200, strict=True)
    duplicate_tolerance: FiniteFloat = Field(default=1e-6, ge=1e-12, le=0.1)
    ordinal_rank_distance: bool = False
    min_batch_distance: FiniteFloat = Field(default=0, ge=0)
    sample_count: int = Field(default=64, ge=16, le=256, strict=True)
    max_evaluations: int = Field(default=100000, ge=1, le=100000, strict=True)
    max_moment_evaluations: int = Field(default=8192, ge=1, le=65536, strict=True)
    time_budget_ms: int = Field(default=60000, ge=1000, le=60000, strict=True)

    @model_validator(mode="after")
    def coherent_selection(self) -> "MixedSelectionRequest":
        if (self.model_id is None) != (self.expected_model_sha256 is None):
            raise ValueError("bayesian_planning_model_mismatch")
        if self.kind == "manual_ordered":
            if (
                self.model_id is None
                or self.policy is not None
                or len(self.row_ids) != self.batch_size
                or len(set(self.row_ids)) != self.batch_size
            ):
                raise ValueError("bayesian_planning_selection_invalid")
        else:
            model_free = self.policy in {"greedy_incremental_maxpro_v1", "greedy_mixed_maximin_v1"}
            if self.policy is None or self.row_ids or model_free != (self.model_id is None):
                raise ValueError("bayesian_augmentation_model_policy_mismatch")
        return self


class MixedAugmentationCalculation(_Model):
    schema_version: Literal[3] = 3
    augmentation: AugmentationTrace
    selected_rows: list[EvaluatedMixedCandidateRow | MixedCandidateRow] = Field(
        min_length=1, max_length=8
    )
    source_row_count: int = Field(ge=1, le=10000)
    prediction_evaluations: int = Field(ge=0, le=10000)
    max_moment_evaluations: int = Field(ge=1, le=65536)
    time_budget_ms: int = Field(ge=1000, le=60000)
    model_refit: Literal[False] = False

    @model_validator(mode="after")
    def exact_selection(self) -> "MixedAugmentationCalculation":
        model_free = self.augmentation.source.model_snapshot_id is None
        if (
            [row.row_id for row in self.selected_rows] != self.augmentation.selected_row_ids
            or any(not row.eligible for row in self.selected_rows)
            or any(
                isinstance(row, EvaluatedMixedCandidateRow) == model_free
                for row in self.selected_rows
            )
            or model_free
            and self.prediction_evaluations != 0
        ):
            raise ValueError("bayesian_augmentation_result_invalid")
        return self


MixedSelectionCalculation = Annotated[
    MixedPlanningSelectionCalculation | MixedAugmentationCalculation,
    Field(discriminator="schema_version"),
]


class MixedSelectionResponse(_Model):
    schema_version: Literal[3] = 3
    selection_id: UUID
    study_id: UUID
    study_version_id: UUID
    model_id: UUID | None
    candidate_revision_id: UUID
    config_sha256: Sha256
    result_sha256: Sha256
    request: MixedSelectionRequest
    calculation: MixedSelectionCalculation
    created_at: str
    source_is_current: bool
    confirmed_batch_id: UUID | None


class MixedSelectionSummary(_Model):
    schema_version: Literal[3] = 3
    selection_id: UUID
    study_id: UUID
    study_version_id: UUID
    model_id: UUID | None
    candidate_revision_id: UUID
    config_sha256: Sha256
    result_sha256: Sha256
    kind: Literal["manual_ordered", "augmentation"]
    policy: AugmentationPolicy | None
    selected_count: int = Field(ge=1, le=8)
    created_at: str
    source_is_current: bool
    confirmed_batch_id: UUID | None


class MixedSelectionList(_Model):
    items: list[MixedSelectionSummary] = Field(max_length=64)
