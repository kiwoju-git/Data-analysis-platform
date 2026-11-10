"""Schema7 curve-aware calculation, independent of raw GP fit policy."""

from typing import Literal

from pydantic import Field

from app.api.v1.schemas.bo_curve_policy import VersionedCurveObjective
from app.api.v1.schemas.bo_desirability_batch_calculation import (
    _BatchCalculationRequestFields,
    _BatchCalculationResultFields,
)
from app.api.v1.schemas.bo_desirability_calculation import (
    Identifier,
    _CalculationRequestFields,
    _ResponseModelResult,
    _StrictModel,
    _Weight,
)
from app.api.v1.schemas.bo_fit_quality import BayesianFitPolicy, _ResponseModel


class CurveCalculationProjection(_CalculationRequestFields):
    schema_version: Literal[7]
    objective: VersionedCurveObjective


class DesirabilityCurveCalculationRequest(_BatchCalculationRequestFields):
    schema_version: Literal[7]
    objective: VersionedCurveObjective
    fit_policy: BayesianFitPolicy | None

    def q1_request(self) -> CurveCalculationProjection:
        raw = self.model_dump(mode="python", exclude={"batch_options", "fit_policy"})
        raw["batch_size"] = 1
        return CurveCalculationProjection.model_validate(raw)


class CurveSharedModel(_StrictModel):
    schema_version: Literal[7]
    policy_version: Literal[1]
    factor_ids: list[Identifier] = Field(min_length=1, max_length=10)
    response_ids: list[Identifier] = Field(min_length=1, max_length=4)
    normalized_importance: list[_Weight] = Field(min_length=1, max_length=4)
    curve_policy: Literal["per_response_target_gaussian_or_ds_v1"]
    moment_policy: Literal["independent_latent_versioned_curve_moments_v1"]
    independence_assumption: Literal[True]
    response_models: list[_ResponseModel | _ResponseModelResult] = Field(min_length=1, max_length=4)


class DesirabilityCurveCalculationResult(_BatchCalculationResultFields):
    schema_version: Literal[7]
    objective: VersionedCurveObjective
    shared_model: CurveSharedModel
