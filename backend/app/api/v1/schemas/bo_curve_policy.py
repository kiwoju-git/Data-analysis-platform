"""Explicit new curve definitions; legacy DS objects receive no new defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.api.v1.schemas.bayesian_desirability import (
    BayesianDesirabilityObjective,
    DesirabilityResponseGoal,
)

if TYPE_CHECKING:
    from app.statistics.bo_target_curve import GaussianTargetGoal


class GaussianTargetControls(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    policy: Literal["two_sided_gaussian_target_peak_one_v1"]
    lower_desirability: FiniteFloat = Field(gt=0, lt=1)
    upper_desirability: FiniteFloat = Field(gt=0, lt=1)


class GaussianTargetResponseGoal(DesirabilityResponseGoal):
    curve: GaussianTargetControls

    def calculation_goal(self) -> GaussianTargetGoal:
        from app.statistics.bo_target_curve import GaussianTargetGoal

        return GaussianTargetGoal(
            self.response_id,
            self.goal,
            self.lower,
            self.target,
            self.upper,
            self.importance,
            self.curve.lower_desirability,
            self.curve.upper_desirability,
        )


class VersionedCurveObjective(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    responses: list[GaussianTargetResponseGoal | DesirabilityResponseGoal] = Field(
        min_length=1, max_length=4
    )

    @model_validator(mode="after")
    def validate_curves(self) -> VersionedCurveObjective:
        from app.statistics.bo_desirability import normalized_importance

        normalized_importance([r.calculation_goal() for r in self.responses])
        if not any(isinstance(r, GaussianTargetResponseGoal) for r in self.responses):
            raise ValueError("bayesian_curve_policy_invalid")
        return self


class BayesianVersionedCurveObjective(VersionedCurveObjective):
    name: str = Field(min_length=1, max_length=80)
    goal_type: Literal["desirability"]
    observation_policy: Literal["complete_response_vector"]
    curve_policy: Literal["per_response_target_gaussian_or_ds_v1"]
    unit: None = None
    direction: None = None
    target_value: None = None
    target_tolerance: None = None

    @model_validator(mode="after")
    def validate_name(self) -> BayesianVersionedCurveObjective:
        if not self.name.strip():
            raise ValueError("bayesian_study_name_invalid")
        return self


AnyDesirabilityObjective: TypeAlias = (
    BayesianDesirabilityObjective | BayesianVersionedCurveObjective
)


def study_objective_type(schema_version: int):
    return BayesianVersionedCurveObjective if schema_version == 6 else BayesianDesirabilityObjective
