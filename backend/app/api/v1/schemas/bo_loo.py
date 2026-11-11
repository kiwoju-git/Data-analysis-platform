"""Source-locked conditional row-LOO view; no change to saved model schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.api.v1.schemas.bo_desirability_calculation import Identifier
from app.api.v1.schemas.bo_planning import Sha256


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LooRequest(_Model):
    expected_model_sha256: Sha256
    expected_history_sha256: Sha256


class LooPoint(_Model):
    trial_id: UUID
    observation_index: int = Field(ge=1, le=200, strict=True)
    observed: FiniteFloat
    predicted: FiniteFloat
    residual: FiniteFloat


class LooResponseDiagnostic(_Model):
    response_id: Identifier
    raw_observation_count: int = Field(ge=2, le=200, strict=True)
    effective_training_count: int = Field(ge=1, le=200, strict=True)
    n_scored: int = Field(ge=2, le=200, strict=True)
    rmse: FiniteFloat = Field(ge=0)
    r_squared: FiniteFloat | None = Field(le=1)
    r_squared_reason: Literal["constant_observations"] | None
    points: list[LooPoint] = Field(min_length=2, max_length=200)

    @model_validator(mode="after")
    def complete_rows(self) -> "LooResponseDiagnostic":
        if (
            self.n_scored != self.raw_observation_count
            or len(self.points) != self.n_scored
            or self.effective_training_count > self.raw_observation_count
            or [point.observation_index for point in self.points]
            != list(range(1, self.n_scored + 1))
            or len({point.trial_id for point in self.points}) != self.n_scored
            or (self.r_squared is None) != (self.r_squared_reason is not None)
        ):
            raise ValueError("bayesian_loo_diagnostic_invalid")
        return self


class LooCalculation(_Model):
    schema_version: Literal[1]
    policy: Literal["fixed_full_fit_parameters_row_loo_v1"]
    evaluation_unit: Literal["individual_observed_trial"]
    normalization_policy: Literal["frozen_full_fit_mean_scale"]
    r_squared_policy: Literal["one_minus_press_over_raw_centered_tss"]
    model_refit: Literal[False]
    auto_routing_applied: Literal[False]
    warnings: list[
        Literal[
            "full_fit_parameters_include_held_out_observation",
            "not_external_validation",
            "repeats_are_not_new_condition_validation",
            "category_vocabulary_and_parameters_frozen",
        ]
    ] = Field(min_length=3, max_length=4)
    responses: list[LooResponseDiagnostic] = Field(min_length=1, max_length=4)


class LooSnapshot(_Model):
    schema_version: Literal[1] = 1
    study_id: UUID
    model_id: UUID
    model_sha256: Sha256
    config_sha256: Sha256
    source_history_revision_id: UUID
    history_sha256: Sha256
    calculation_sha256: Sha256
    calculation: LooCalculation


class LooView(LooSnapshot):
    source_is_current: bool
