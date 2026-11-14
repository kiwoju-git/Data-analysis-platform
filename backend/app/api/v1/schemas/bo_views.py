"""Immutable, server-evaluated BO diagnostic views without live eligibility."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, JsonValue, model_validator

from app.api.v1.schemas.bayesian import BayesianLinearConstraintRequest
from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityMomentResult,
    Identifier,
    _ResponsePrediction,
)
from app.api.v1.schemas.bo_loo import LooCalculation
from app.api.v1.schemas.bo_mixed_planning import ActualPoint
from app.api.v1.schemas.bo_planning import Sha256


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfilerMatrixRequest(_Model):
    kind: Literal["profiler_matrix"]
    expected_model_sha256: Sha256
    expected_history_sha256: Sha256
    holds: ActualPoint
    points_per_axis: int = Field(default=21, ge=2, le=100, strict=True)
    time_budget_ms: int = Field(default=120000, ge=1000, le=120000, strict=True)


class ConditionalLooRequest(_Model):
    kind: Literal["conditional_loo"]
    expected_model_sha256: Sha256
    expected_history_sha256: Sha256


ViewEvaluationRequest = Annotated[
    ProfilerMatrixRequest | ConditionalLooRequest, Field(discriminator="kind")
]


class ViewSource(_Model):
    study_id: UUID
    study_version_id: UUID
    definition_sha256: Sha256
    model_id: UUID
    model_sha256: Sha256
    model_config_sha256: Sha256
    history_revision_id: UUID
    history_sha256: Sha256


class ViewResponse(_Model):
    response_id: Identifier
    name: str = Field(min_length=1, max_length=80)
    unit: str | None = Field(max_length=40)


class ProfilePoint(_Model):
    row_id: Sha256
    actual_coordinates: ActualPoint
    constraints_satisfied: bool
    response_predictions: list[_ResponsePrediction] = Field(min_length=1, max_length=4)
    desirability_moments: DesirabilityMomentResult
    prediction_source: Literal["completed_observations_base_posterior"]


class ProfilePath(_Model):
    policy: Literal["excess_above_lower", "deficit_below_upper", "held_mixture_process_axis_v1"]
    feasible_interval: tuple[FiniteFloat, FiniteFloat] | None
    unavailable_reason: str | None = Field(max_length=120)


class ProfileAxis(_Model):
    factor_id: Identifier
    name: str = Field(min_length=1, max_length=120)
    unit: str | None = Field(max_length=40)
    kind: Literal["continuous", "discrete_numeric", "nominal", "ordinal", "mixture_component"]
    available_level_count: int | None = Field(ge=1, le=10001)
    points: list[ProfilePoint] = Field(max_length=100)
    path: ProfilePath | None = None

    @model_validator(mode="after")
    def explicit_path_state(self) -> "ProfileAxis":
        if self.path is None:
            if len(self.points) < 2 or self.kind == "mixture_component":
                raise ValueError("bayesian_view_payload_invalid")
        elif bool(self.points) == bool(self.path.unavailable_reason):
            raise ValueError("bayesian_view_payload_invalid")
        if self.path and self.path.feasible_interval:
            lo, hi = self.path.feasible_interval
            if lo > hi:
                raise ValueError("bayesian_view_payload_invalid")
        return self


class ProfilerMatrixPayload(_Model):
    schema_version: Literal[1, 2] = 1
    kind: Literal["profiler_matrix"]
    source: ViewSource
    model_refit: Literal[False] = False
    policy: Literal[
        "source_locked_conditional_profiler_matrix_v1", "source_locked_mixture_profiler_matrix_v1"
    ]
    mixture_domain: dict[str, JsonValue] | None = None
    holds: ActualPoint
    axes: list[ProfileAxis] = Field(min_length=1, max_length=10)
    constraints: list[BayesianLinearConstraintRequest] = Field(max_length=16)
    responses: list[ViewResponse] = Field(min_length=1, max_length=4)
    point_count: int = Field(ge=0, le=1000, strict=True)
    warnings: list[str] = Field(max_length=64)

    @model_validator(mode="after")
    def complete_matrix(self) -> "ProfilerMatrixPayload":
        factors = [axis.factor_id for axis in self.axes]
        responses = [row.response_id for row in self.responses]
        mixture = self.policy == "source_locked_mixture_profiler_matrix_v1"
        if (
            (self.schema_version == 2) != mixture
            or (self.mixture_domain is not None) != mixture
            or any((axis.path is not None) != mixture for axis in self.axes)
        ):
            raise ValueError("bayesian_view_payload_invalid")
        if (
            len(set(factors)) != len(factors)
            or set(factors) != set(self.holds)
            or len(set(responses)) != len(responses)
            or self.point_count != sum(len(axis.points) for axis in self.axes)
        ):
            raise ValueError("bayesian_view_payload_invalid")
        for axis in self.axes:
            if len({point.row_id for point in axis.points}) != len(axis.points):
                raise ValueError("bayesian_view_payload_invalid")
            if axis.kind in {"nominal", "ordinal"} and axis.available_level_count != len(
                axis.points
            ):
                raise ValueError("bayesian_view_payload_invalid")
            for point in axis.points:
                if (
                    set(point.actual_coordinates) != set(factors)
                    or [row.response_id for row in point.response_predictions] != responses
                ):
                    raise ValueError("bayesian_view_payload_invalid")
        return self


class ConditionalLooPayload(_Model):
    schema_version: Literal[1] = 1
    kind: Literal["conditional_loo"]
    source: ViewSource
    model_refit: Literal[False] = False
    responses: list[ViewResponse] = Field(min_length=1, max_length=4)
    calculation: LooCalculation
    calculation_sha256: Sha256


ViewPayload = Annotated[ProfilerMatrixPayload | ConditionalLooPayload, Field(discriminator="kind")]


class ViewEvaluationReceipt(_Model):
    receipt_id: UUID
    request_sha256: Sha256
    view_sha256: Sha256
    expires_at: str
    payload: ViewPayload


class SaveViewRequest(_Model):
    request_id: UUID
    receipt_id: UUID
    expected_model_sha256: Sha256
    expected_request_sha256: Sha256
    expected_view_sha256: Sha256


class SavedViewSummary(_Model):
    schema_version: Literal[1] = 1
    view_id: UUID
    source: ViewSource
    kind: Literal["profiler_matrix", "conditional_loo"]
    request_sha256: Sha256
    view_sha256: Sha256
    created_at: str


class SavedView(SavedViewSummary):
    evaluation_request: ViewEvaluationRequest
    payload: ViewPayload


class SavedViewList(_Model):
    items: list[SavedViewSummary] = Field(max_length=32)
