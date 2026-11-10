"""Versioned measured-response definitions, shared with the internal BO worker."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

if TYPE_CHECKING:
    from app.statistics.bo_desirability import DesirabilityGoal

ResponseId = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")]
ResponseNumber = Annotated[FiniteFloat, Field(strict=True)]
ResponseValues = Annotated[dict[ResponseId, ResponseNumber], Field(min_length=1, max_length=4)]


class DesirabilityResponseGoal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    response_id: ResponseId
    name: str = Field(min_length=1, max_length=80)
    unit: str | None = Field(default=None, max_length=40)
    goal: Literal["maximize", "minimize", "match_target"]
    lower: FiniteFloat | None
    target: FiniteFloat
    upper: FiniteFloat | None
    importance: FiniteFloat = Field(default=1, gt=0)

    def calculation_goal(self) -> DesirabilityGoal:
        from app.statistics.bo_desirability import DesirabilityGoal

        return DesirabilityGoal(
            self.response_id, self.goal, self.lower, self.target, self.upper, self.importance
        )

    @model_validator(mode="after")
    def validate_curve(self) -> DesirabilityResponseGoal:
        from app.statistics.bayesian_optimization import BayesianOptimizationError

        if not self.name.strip():
            raise ValueError("bayesian_desirability_input_invalid")
        try:
            self.calculation_goal()
        except BayesianOptimizationError as exc:
            raise ValueError(exc.code) from exc
        return self


class DesirabilityObjective(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    responses: list[DesirabilityResponseGoal] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def validate_weights(self) -> DesirabilityObjective:
        from app.statistics.bayesian_optimization import BayesianOptimizationError
        from app.statistics.bo_desirability import normalized_importance

        try:
            normalized_importance([r.calculation_goal() for r in self.responses])
        except BayesianOptimizationError as exc:
            raise ValueError(exc.code) from exc
        return self


class BayesianDesirabilityObjective(DesirabilityObjective):
    name: str = Field(min_length=1, max_length=80)
    goal_type: Literal["desirability"]
    observation_policy: Literal["complete_response_vector"]
    curve_policy: Literal["derringer_suich_linear_v1"]
    # No scalar unit, target or direction represents a vector of measured responses.
    unit: None = None
    direction: None = None
    target_value: None = None
    target_tolerance: None = None

    @model_validator(mode="after")
    def validate_name(self) -> BayesianDesirabilityObjective:
        if not self.name.strip():
            raise ValueError("bayesian_study_name_invalid")
        return self
