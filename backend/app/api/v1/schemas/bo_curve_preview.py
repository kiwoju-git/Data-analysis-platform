from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

from app.statistics.bo_target_curve import TargetCurve

Number = Annotated[FiniteFloat, Field(strict=True)]


class PreviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TargetCurveControls(PreviewModel):
    lower: Number
    target: Number
    upper: Number
    lower_desirability: Annotated[Number, Field(gt=0, lt=1)]
    upper_desirability: Annotated[Number, Field(gt=0, lt=1)]
    peak: Literal[1] = 1

    @field_validator("peak", mode="before")
    @classmethod
    def numeric_peak(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("bayesian_desirability_input_invalid")
        return value

    def curve(self) -> TargetCurve:
        return TargetCurve(
            self.lower, self.target, self.upper, self.lower_desirability, self.upper_desirability
        )

    @model_validator(mode="after")
    def validate_curve(self) -> "TargetCurveControls":
        self.curve()
        return self


class AssumedGaussian(PreviewModel):
    mean: Number
    standard_deviation: Annotated[Number, Field(ge=0)]
    incumbent: Annotated[Number, Field(ge=0, le=1)]
    xi: Annotated[Number, Field(ge=0, le=1)] = 0.0


class CurvePreviewRequest(PreviewModel):
    schema_version: Literal[1] = 1
    controls: TargetCurveControls
    plot_lower: Number
    plot_upper: Number
    assumed_distribution: AssumedGaussian | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "CurvePreviewRequest":
        import math

        if not (
            self.plot_lower <= self.controls.lower < self.controls.upper <= self.plot_upper
            and math.isfinite(self.plot_upper - self.plot_lower)
        ):
            raise ValueError("bayesian_curve_preview_range_invalid")
        return self


class CurvePreviewPoint(PreviewModel):
    response_value: Number
    gaussian: Number
    linear: Number


class CurvePreviewMetrics(PreviewModel):
    policy: str
    mean: Number | None = None
    variance: Number | None = None
    second_moment: Number | None = None
    beta_ei: Number | None = None
    ei_distribution: str | None = None
    unavailable_code: str | None = None
    ei_unavailable_code: str | None = None
    normal_tail_bound: Number | None = None
    integration_error: Number | None = None


class CurvePreviewResponse(PreviewModel):
    schema_version: Literal[1] = 1
    preview_only: Literal[True] = True
    persisted: Literal[False] = False
    applied_to_recommendations: Literal[False] = False
    request_snapshot: CurvePreviewRequest
    curve_policy: Literal["two_sided_gaussian_target_peak_one_v1"]
    comparison_policy: Literal["derringer_suich_linear_v1"]
    moment_policy: Literal["gaussian_target_closed_form_centered_variance_v1"]
    points: Annotated[list[CurvePreviewPoint], Field(min_length=3, max_length=164)]
    gaussian_underflow_count: Annotated[int, Field(ge=0, le=164)]
    metrics: Annotated[list[CurvePreviewMetrics], Field(max_length=2)]
