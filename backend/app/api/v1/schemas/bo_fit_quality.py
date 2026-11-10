"""New fit-policy schema only; no defaults are injected into legacy artifacts."""

from typing import Literal

from pydantic import Field, FiniteFloat, model_validator

from app.api.v1.schemas.bayesian_desirability import DesirabilityObjective
from app.api.v1.schemas.bayesian_noise import BayesianObservationViewSummary
from app.api.v1.schemas.bo_desirability_batch_calculation import (
    _BatchCalculationRequestFields,
    _BatchCalculationResultFields,
)
from app.api.v1.schemas.bo_desirability_calculation import (
    Identifier,
    _RawResponseModelFields,
    _SharedModelFields,
    _StrictModel,
)


class BayesianFitPolicy(_StrictModel):
    kind: Literal["bounded_multiscale_starts_v1"]
    deterministic_start_count: int = Field(ge=1, le=3)


class _Screen(_StrictModel):
    log_parameters: list[FiniteFloat] = Field(min_length=2, max_length=12)
    negative_log_likelihood: FiniteFloat


class _Selected(_Screen):
    stage: Literal["screen", "local_evaluation"]
    screen_index: int | None = Field(ge=0, le=8)
    start_index: int | None = Field(ge=0, le=5)

    @model_validator(mode="after")
    def check_origin(self) -> "_Selected":
        if (self.stage == "screen") != (self.screen_index is not None) or (
            self.stage == "local_evaluation"
        ) != (self.start_index is not None):
            raise ValueError("bayesian_fit_diagnostics_invalid")
        return self


class _Evaluation(_Screen):
    evaluation_index: int = Field(ge=0, le=1999)


class _BoundHit(_StrictModel):
    parameter: Literal["signal_amplitude", "length_scale", "measurement_variance"]
    factor_index: int | None = Field(ge=0, le=9)
    side: Literal["lower", "upper"]
    value: FiniteFloat = Field(gt=0)
    bound: FiniteFloat = Field(gt=0)


class BayesianFitDiagnostics(_StrictModel):
    schema_version: Literal[1]
    policy: Literal["bounded_multiscale_starts_v1"]
    deterministic_start_count: int = Field(ge=1, le=3)
    screening: list[_Screen] = Field(min_length=9, max_length=9)
    refined_screen_indices: list[int] = Field(min_length=1, max_length=3)
    start_initial_negative_log_likelihoods: list[FiniteFloat] = Field(min_length=1, max_length=6)
    start_best_evaluations: list[_Evaluation] = Field(min_length=1, max_length=6)
    selected: _Selected
    bound_hits: list[_BoundHit] = Field(max_length=12)
    global_optimum_guaranteed: Literal[False]


class DesirabilityFittedRawModel(_RawResponseModelFields):
    schema_version: Literal[5]
    policy_version: Literal["bo_noise_latent_fit_v4"]
    fit_diagnostics: BayesianFitDiagnostics


class _ResponseModel(_StrictModel):
    response_id: Identifier
    model: DesirabilityFittedRawModel
    observation_view: BayesianObservationViewSummary


class DesirabilityFittedSharedModel(_SharedModelFields):
    schema_version: Literal[6]
    response_models: list[_ResponseModel] = Field(min_length=1, max_length=4)


class DesirabilityFitCalculationRequest(_BatchCalculationRequestFields):
    schema_version: Literal[6]
    objective: DesirabilityObjective
    fit_policy: BayesianFitPolicy


class DesirabilityFitCalculationResult(_BatchCalculationResultFields):
    schema_version: Literal[6]
    objective: DesirabilityObjective
    shared_model: DesirabilityFittedSharedModel
