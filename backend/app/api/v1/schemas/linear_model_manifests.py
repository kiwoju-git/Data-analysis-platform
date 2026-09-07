"""Schema-4 linear manifests. Legacy schemas are validated by their existing reader."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, TypeAdapter, model_validator


class _Manifest(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)
    manifest_schema_version: Literal[4]
    method_id: Literal["regression.linear_model"]
    method_version: Literal["0.3.0"]
    linear_model_result_schema_version: Literal[6]
    model_id: str
    analysis_id: str
    dataset_version_id: str
    source_schema_hash: str
    coefficients: list[dict[str, Any]] = Field(min_length=1)
    response: dict[str, Any]
    predictors: list[dict[str, Any]]
    model_specification: dict[str, Any]
    training_domain: dict[str, Any]


class OlsManifest(_Manifest):
    model_kind: Literal["ols"]
    model_family: Literal["linear_regression_ols"]
    prediction_basis: dict[str, Any]
    alpha: FiniteFloat = Field(gt=0, lt=1)
    confidence_level: FiniteFloat = Field(gt=0, lt=1)


class PointPredictionBasis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    basis_schema_version: Literal[2]
    kind: Literal["point_only"]
    coefficient_order: list[str] = Field(min_length=2)


class RegularizationManifest(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)
    selected_alpha: FiniteFloat = Field(gt=0)
    selected_l1_ratio: FiniteFloat | None
    scaler_means: list[FiniteFloat]
    scaler_scales: list[Annotated[FiniteFloat, Field(gt=0)]]
    feature_order: list[str] = Field(min_length=1)


class _PenalizedManifest(_Manifest):
    model_family: Literal["linear_regression_regularized"]
    prediction_basis: PointPredictionBasis
    regularization: RegularizationManifest

    @model_validator(mode="after")
    def feature_alignment(self) -> "_PenalizedManifest":
        size = len(self.coefficients) - 1
        tuning = self.regularization
        if (
            len(self.prediction_basis.coefficient_order) != size + 1
            or len(tuning.scaler_means) != size
            or len(tuning.scaler_scales) != size
            or tuning.feature_order != self.prediction_basis.coefficient_order[1:]
        ):
            raise ValueError("linear_manifest_feature_alignment")
        if any(key in (self.model_extra or {}) for key in ("anova", "alpha", "confidence_level")):
            raise ValueError("linear_manifest_classical_inference_incompatible")
        return self


class RidgeManifest(_PenalizedManifest):
    model_kind: Literal["ridge"]


class LassoManifest(_PenalizedManifest):
    model_kind: Literal["lasso"]


class ElasticNetManifest(_PenalizedManifest):
    model_kind: Literal["elastic_net"]


LinearModelManifest = Annotated[
    OlsManifest | RidgeManifest | LassoManifest | ElasticNetManifest,
    Field(discriminator="model_kind"),
]
LINEAR_MODEL_MANIFEST_ADAPTER: TypeAdapter[LinearModelManifest] = TypeAdapter(LinearModelManifest)
