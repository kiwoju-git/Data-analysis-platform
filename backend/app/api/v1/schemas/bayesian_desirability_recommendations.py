"""Versioned q1/ordered-batch reviews and immutable recommendation bundles."""

from typing import Any, Literal, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.api.v1.schemas.bayesian import BayesianTrialResponse, BayesianVectorTrialResponse
from app.api.v1.schemas.bayesian_noise import BayesianObservationPolicyRequest
from app.api.v1.schemas.bo_curve_calculation import DesirabilityCurveCalculationResult
from app.api.v1.schemas.bo_desirability_batch_calculation import (
    DesirabilityBatchCalculationResult,
    DesirabilityBatchOptions,
)
from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityCalculationResult,
    DesirabilityResponseModelRequest,
    DesirabilitySearch,
)
from app.api.v1.schemas.bo_fit_quality import BayesianFitPolicy, DesirabilityFitCalculationResult


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _strict_request_versions(value: Any) -> Any:
    if isinstance(value, dict) and any(
        key in value and type(value[key]) is not int for key in ("schema_version", "batch_size")
    ):
        raise ValueError("bayesian_desirability_input_invalid")
    return value


class DesirabilityReviewRequest(_Model):
    schema_version: Literal[4] = 4
    batch_size: Literal[1] = 1
    expected_history_revision_id: UUID
    expected_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_models: list[DesirabilityResponseModelRequest] = Field(min_length=1, max_length=4)
    observation_policy: BayesianObservationPolicyRequest
    xi_desirability: FiniteFloat = Field(ge=0, strict=True)
    total_trial_budget: int = Field(ge=2, le=200, strict=True)
    search: DesirabilitySearch

    @model_validator(mode="before")
    @classmethod
    def strict_versions(cls, value: Any) -> Any:
        return _strict_request_versions(value)


class DesirabilityReviewResponse(_Model):
    schema_version: Literal[2] = 2
    review_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_at: str
    calculation: DesirabilityCalculationResult


class DesirabilityBatchItem(_Model):
    item_id: UUID
    batch_id: UUID
    rank: Literal[1] = 1
    trial: BayesianTrialResponse
    current_trial: BayesianTrialResponse | BayesianVectorTrialResponse


class DesirabilityProvenance(_Model):
    app_version: str
    python_version: str
    platform: str
    build_commit: str | None
    package_versions: dict[str, str]


class DesirabilityBatchResponse(_Model):
    method_id: Literal["doe.bayesian_optimization"] = "doe.bayesian_optimization"
    method_version: Literal["0.9.0"] = "0.9.0"
    config_schema_version: Literal[4] = 4
    result_schema_version: Literal[4] = 4
    model_schema_version: Literal[5] = 5
    item_schema_version: Literal[3] = 3
    batch_size: Literal[1] = 1
    batch_policy: Literal["independent_latent_desirability_beta_ei_v1"] = (
        "independent_latent_desirability_beta_ei_v1"
    )
    batch_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation: DesirabilityCalculationResult
    items: list[DesirabilityBatchItem] = Field(min_length=1, max_length=1)
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: str
    is_latest: bool = False
    batch_state: Literal["pending", "completed", "abandoned"] = "pending"
    requested_total_trial_budget: int = Field(ge=2, le=200)
    provenance: DesirabilityProvenance


class DesirabilityLatestResponse(_Model):
    item: DesirabilityBatchResponse | None


class _OrderedReviewRequestFields(_Model):
    batch_size: int = Field(ge=1, le=8, strict=True)
    batch_options: DesirabilityBatchOptions
    expected_history_revision_id: UUID
    expected_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_models: list[DesirabilityResponseModelRequest] = Field(min_length=1, max_length=4)
    observation_policy: BayesianObservationPolicyRequest
    xi_desirability: FiniteFloat = Field(ge=0, strict=True)
    total_trial_budget: int = Field(ge=2, le=200, strict=True)
    search: DesirabilitySearch

    @model_validator(mode="before")
    @classmethod
    def strict_versions(cls, value: Any) -> Any:
        return _strict_request_versions(value)


class DesirabilityOrderedReviewRequest(_OrderedReviewRequestFields):
    schema_version: Literal[5]


class DesirabilityFitReviewRequest(_OrderedReviewRequestFields):
    schema_version: Literal[6]
    fit_policy: BayesianFitPolicy


class DesirabilityCurveReviewRequest(_OrderedReviewRequestFields):
    schema_version: Literal[7]
    fit_policy: BayesianFitPolicy | None


class _OrderedReviewResponseFields(_Model):
    review_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_at: str


class DesirabilityOrderedReviewResponse(_OrderedReviewResponseFields):
    schema_version: Literal[3] = 3
    calculation: DesirabilityBatchCalculationResult


class DesirabilityFitReviewResponse(_OrderedReviewResponseFields):
    schema_version: Literal[4] = 4
    calculation: DesirabilityFitCalculationResult


class DesirabilityCurveReviewResponse(_OrderedReviewResponseFields):
    schema_version: Literal[5] = 5
    calculation: DesirabilityCurveCalculationResult


class DesirabilityOrderedBatchItem(_Model):
    item_id: UUID
    batch_id: UUID
    rank: int = Field(ge=1, le=8, strict=True)
    trial: BayesianTrialResponse
    current_trial: BayesianTrialResponse | BayesianVectorTrialResponse


class _OrderedBatchResponseFields(_Model):
    method_id: Literal["doe.bayesian_optimization"] = "doe.bayesian_optimization"
    item_schema_version: Literal[4] = 4
    batch_size: int = Field(ge=1, le=8, strict=True)
    batch_policy: Literal["conditional_mc_desirability_beta_marginal_v1"] = (
        "conditional_mc_desirability_beta_marginal_v1"
    )
    batch_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation: Any
    items: list[DesirabilityOrderedBatchItem] = Field(min_length=1, max_length=8)
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: str
    is_latest: bool = False
    batch_state: Literal[
        "pending", "partially_completed", "completed", "abandoned", "closed_mixed"
    ] = "pending"
    requested_total_trial_budget: int = Field(ge=2, le=200)
    provenance: DesirabilityProvenance

    @model_validator(mode="after")
    def complete_ordered_items(self) -> "_OrderedBatchResponseFields":
        if (
            len(self.items) != self.batch_size
            or self.calculation.batch_size != self.batch_size
            or [item.rank for item in self.items] != list(range(1, self.batch_size + 1))
            or len({item.item_id for item in self.items}) != self.batch_size
            or len({item.trial.trial_id for item in self.items}) != self.batch_size
        ):
            raise ValueError("bayesian_desirability_result_invalid")
        return self


class DesirabilityOrderedBatchResponse(_OrderedBatchResponseFields):
    method_version: Literal["0.10.0"] = "0.10.0"
    config_schema_version: Literal[5] = 5
    result_schema_version: Literal[5] = 5
    model_schema_version: Literal[5] = 5
    calculation: DesirabilityBatchCalculationResult


class DesirabilityFitBatchResponse(_OrderedBatchResponseFields):
    method_version: Literal["0.11.0"] = "0.11.0"
    config_schema_version: Literal[6] = 6
    result_schema_version: Literal[6] = 6
    model_schema_version: Literal[6] = 6
    calculation: DesirabilityFitCalculationResult


class DesirabilityCurveBatchResponse(_OrderedBatchResponseFields):
    method_version: Literal["0.12.0"] = "0.12.0"
    config_schema_version: Literal[7] = 7
    result_schema_version: Literal[7] = 7
    model_schema_version: Literal[7] = 7
    calculation: DesirabilityCurveCalculationResult


DesirabilityAnyReviewRequest: TypeAlias = (
    DesirabilityReviewRequest
    | DesirabilityOrderedReviewRequest
    | DesirabilityFitReviewRequest
    | DesirabilityCurveReviewRequest
)
DesirabilityAnyReviewResponse: TypeAlias = (
    DesirabilityReviewResponse
    | DesirabilityOrderedReviewResponse
    | DesirabilityFitReviewResponse
    | DesirabilityCurveReviewResponse
)
DesirabilityAnyBatchResponse: TypeAlias = (
    DesirabilityBatchResponse
    | DesirabilityOrderedBatchResponse
    | DesirabilityFitBatchResponse
    | DesirabilityCurveBatchResponse
)


class DesirabilityAnyLatestResponse(_Model):
    item: DesirabilityAnyBatchResponse | None


def parse_desirability_request(value: Any) -> DesirabilityAnyReviewRequest:
    if isinstance(value, dict) and value.get("schema_version") == 7:
        return DesirabilityCurveReviewRequest.model_validate(value)
    if isinstance(value, dict) and value.get("schema_version") == 6:
        return DesirabilityFitReviewRequest.model_validate(value)
    if isinstance(value, dict) and value.get("schema_version") == 5:
        return DesirabilityOrderedReviewRequest.model_validate(value)
    return DesirabilityReviewRequest.model_validate(value)


def parse_desirability_review(value: Any) -> DesirabilityAnyReviewResponse:
    if isinstance(value, dict) and value.get("schema_version") == 5:
        return DesirabilityCurveReviewResponse.model_validate(value)
    if isinstance(value, dict) and value.get("schema_version") == 4:
        return DesirabilityFitReviewResponse.model_validate(value)
    if isinstance(value, dict) and value.get("schema_version") == 3:
        return DesirabilityOrderedReviewResponse.model_validate(value)
    return DesirabilityReviewResponse.model_validate(value)


def parse_desirability_batch(value: Any) -> DesirabilityAnyBatchResponse:
    if isinstance(value, dict) and value.get("result_schema_version") == 7:
        return DesirabilityCurveBatchResponse.model_validate(value)
    if isinstance(value, dict) and value.get("result_schema_version") == 6:
        return DesirabilityFitBatchResponse.model_validate(value)
    if isinstance(value, dict) and value.get("result_schema_version") == 5:
        return DesirabilityOrderedBatchResponse.model_validate(value)
    return DesirabilityBatchResponse.model_validate(value)
