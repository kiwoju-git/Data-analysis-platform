"""Separate augmentation policies, stored exact rows and nullable model provenance."""

from __future__ import annotations

import math
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityMomentResult,
    _Acquisition,
    _ResponsePrediction,
)
from app.api.v1.schemas.bo_planning import CandidateRow, Sha256

AugmentationPolicy = Literal[
    "greedy_incremental_maxpro_v1",
    "greedy_mixed_maximin_v1",
    "refine_ei_then_desirability_sd_v1",
    "confirm_mean_then_competitive_sd_v1",
    "refine_ei_alternating_desirability_response_sd_v2",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AugmentationSelectionRequest(_Model):
    schema_version: Literal[2]
    request_id: UUID
    expected_study_version_id: UUID
    expected_definition_sha256: Sha256
    expected_history_revision_id: UUID
    expected_history_sha256: Sha256
    expected_trial_count: int = Field(ge=1, le=200, strict=True)
    candidate_revision_id: UUID
    expected_rows_sha256: Sha256
    model_id: UUID | None
    expected_model_sha256: Sha256 | None
    policy: AugmentationPolicy
    batch_size: int = Field(ge=1, le=8, strict=True)
    total_trial_budget: int = Field(ge=2, le=200, strict=True)
    duplicate_tolerance: FiniteFloat = Field(default=1e-6, ge=1e-12, le=0.1)
    min_batch_distance_normalized: FiniteFloat = Field(default=0, ge=0)
    max_evaluations: int = Field(default=100000, ge=1, le=100000, strict=True)
    max_moment_evaluations: int = Field(default=65536, ge=1, le=65536, strict=True)
    time_budget_ms: int = Field(default=60000, ge=1000, le=60000, strict=True)

    @model_validator(mode="after")
    def model_policy(self) -> AugmentationSelectionRequest:
        model_free = self.policy in {"greedy_incremental_maxpro_v1", "greedy_mixed_maximin_v1"}
        if (self.model_id is None) != (self.expected_model_sha256 is None) or model_free != (
            self.model_id is None
        ):
            raise ValueError("bayesian_augmentation_model_policy_mismatch")
        return self


class AugmentationSource(_Model):
    model_snapshot_id: UUID | None
    model_snapshot_sha256: Sha256 | None
    candidate_revision_id: UUID
    candidate_revision_sha256: Sha256
    history_sha256: Sha256


class AugmentationStep(_Model):
    rank: int = Field(ge=1, le=8)
    row_id: Sha256
    criterion: str
    score: FiniteFloat
    score_scale: Literal["natural_log", "original"]
    optimization_direction: Literal["minimize", "maximize"]
    nearest_existing_distance: FiniteFloat = Field(ge=0)
    nearest_selected_distance: FiniteFloat | None = Field(ge=0)
    compared_candidate_count: int = Field(ge=1, le=10000)
    competitive_threshold: FiniteFloat | None = Field(ge=0, le=1)


class UnscorableCandidate(_Model):
    row_id: Sha256
    first_rank: int = Field(ge=1, le=8)
    score: None
    status: Literal["projection_collision"]


class ResponseUncertaintyScale(_Model):
    response_id: str = Field(min_length=1, max_length=128)
    normalization_scale: FiniteFloat = Field(gt=0)
    normalized_importance: FiniteFloat = Field(gt=0, le=1)


class ResponseUncertainty(_Model):
    policy: Literal["importance_weighted_rms_normalized_latent_sd_v1"]
    variance_kind: Literal["latent"]
    scale: Literal["dimensionless"]
    context: list[ResponseUncertaintyScale] = Field(min_length=1, max_length=4)
    schedule: Literal["first_ei_then_alternating_desirability_sd_response_sd"]

    @model_validator(mode="after")
    def exact_response_context(self) -> ResponseUncertainty:
        identifiers = [item.response_id for item in self.context]
        if identifiers != sorted(set(identifiers)) or not math.isclose(
            math.fsum(item.normalized_importance for item in self.context),
            1.0,
            rel_tol=0,
            abs_tol=16 * math.ulp(1.0),
        ):
            raise ValueError("bayesian_augmentation_result_invalid")
        return self


class AugmentationTrace(_Model):
    schema_version: Literal[1]
    policy: AugmentationPolicy
    source: AugmentationSource
    selected_row_ids: list[Sha256] = Field(min_length=1, max_length=8)
    steps: list[AugmentationStep] = Field(min_length=1, max_length=8)
    distance_policy: Literal["normalized_numeric_hamming_nominal_explicit_ordinal_rank_v1"]
    ordinal_rank_distance: bool
    tie_break: Literal["row_id_ascending"]
    competitive_set_policy: Literal["mean_at_least_observed_location_latent_incumbent"] | None
    reference_count: int = Field(ge=1, le=400)
    raw_reference_count: int = Field(ge=1, le=400)
    eligible_candidate_count: int = Field(ge=1, le=10000)
    projection_collisions: int = Field(ge=0)
    unscorable_candidates: list[UnscorableCandidate] = Field(max_length=10000)
    evaluations: int = Field(ge=1, le=100000)
    max_evaluations: int = Field(ge=1, le=100000)
    pair_comparisons: int = Field(ge=0)
    time_budget_ms: int = Field(ge=1000, le=60000)
    model_refit: Literal[False]
    fantasy_observations: Literal[False]
    warnings: list[str] = Field(max_length=32)
    response_uncertainty: ResponseUncertainty | None = None

    @model_validator(mode="after")
    def uncertainty_policy(self) -> AugmentationTrace:
        if (self.response_uncertainty is not None) != (
            self.policy == "refine_ei_alternating_desirability_response_sd_v2"
        ):
            raise ValueError("bayesian_augmentation_result_invalid")
        return self

    @model_validator(mode="after")
    def ordered_trace(self) -> AugmentationTrace:
        if (
            len(set(self.selected_row_ids)) != len(self.selected_row_ids)
            or [step.row_id for step in self.steps] != self.selected_row_ids
            or [step.rank for step in self.steps] != list(range(1, len(self.steps) + 1))
            or self.evaluations > self.max_evaluations
        ):
            raise ValueError("bayesian_augmentation_result_invalid")
        return self


class AugmentationPredictedRow(CandidateRow):
    response_predictions: list[_ResponsePrediction] = Field(min_length=1, max_length=4)
    desirability_moments: DesirabilityMomentResult
    acquisition: _Acquisition | None
    prediction_source: Literal["completed_observations_base_posterior"]


class AugmentationCalculation(_Model):
    schema_version: Literal[1]
    augmentation: AugmentationTrace
    selected_rows: list[CandidateRow | AugmentationPredictedRow] = Field(min_length=1, max_length=8)
    source_row_count: int = Field(ge=1, le=10000)
    prediction_evaluations: int = Field(ge=0, le=10000)
    max_moment_evaluations: int = Field(ge=1, le=65536)
    time_budget_ms: int = Field(ge=1000, le=60000)
    model_refit: Literal[False]

    @model_validator(mode="after")
    def exact_rows(self) -> AugmentationCalculation:
        if [row.row_id for row in self.selected_rows] != self.augmentation.selected_row_ids or any(
            not row.eligible for row in self.selected_rows
        ):
            raise ValueError("bayesian_augmentation_result_invalid")
        model_free = self.augmentation.source.model_snapshot_id is None
        if any(
            isinstance(row, AugmentationPredictedRow) == model_free for row in self.selected_rows
        ):
            raise ValueError("bayesian_augmentation_model_policy_mismatch")
        if model_free and self.prediction_evaluations != 0:
            raise ValueError("bayesian_augmentation_model_policy_mismatch")
        return self


class AugmentationSelectionResponse(_Model):
    schema_version: Literal[2] = 2
    selection_id: UUID
    study_id: UUID
    study_version_id: UUID
    model_id: UUID | None
    candidate_revision_id: UUID
    config_sha256: Sha256
    result_sha256: Sha256
    request: AugmentationSelectionRequest
    calculation: AugmentationCalculation
    created_at: str
    source_is_current: bool
    confirmed_batch_id: UUID | None
