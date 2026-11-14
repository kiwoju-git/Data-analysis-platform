"""Explicit measured-dataset mixture opt-in; schema-1 import bytes stay intact."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.analyses import AnalysisFilterSnapshot
from app.api.v1.schemas.bayesian import BayesianFactorRequest, BayesianLinearConstraintRequest
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_dataset_import import DatasetResponseMapping
from app.api.v1.schemas.bo_dataset_source import (
    DatasetImportedInitialDesign,
    DatasetImportPreflightResponse,
    ImportHash,
)
from app.api.v1.schemas.bo_mixed_studies import MixedCategoricalFactorRequest
from app.api.v1.schemas.bo_mixture import (
    MixtureComponentRequest,
    MixtureGroupRequest,
    MixtureStudyDefinition,
)


class MixtureImportComponent(MixtureComponentRequest):
    domain_kind: Literal["mixture_component"]


class MixtureDatasetFactorMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column_id: str = Field(min_length=1, max_length=128)
    factor: MixtureImportComponent | BayesianFactorRequest | MixedCategoricalFactorRequest


class MixtureDatasetImportPreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[2]
    name: str = Field(min_length=1, max_length=120)
    dataset_version_id: UUID
    expected_schema_hash: ImportHash
    mixture: MixtureGroupRequest
    factor_mappings: list[MixtureDatasetFactorMapping] = Field(min_length=2, max_length=10)
    objective: AnyDesirabilityObjective
    response_mappings: list[DatasetResponseMapping] = Field(min_length=1, max_length=4)
    constraints: list[BayesianLinearConstraintRequest] = Field(default_factory=list, max_length=16)
    filter_snapshot: AnalysisFilterSnapshot
    missing_policy: Literal["reject", "complete_case"]

    @model_validator(mode="before")
    @classmethod
    def integer_version(cls, value: Any) -> Any:
        if isinstance(value, dict) and type(value.get("schema_version")) is not int:
            raise ValueError("bayesian_mixture_import_version_invalid")
        return value

    def definition(self) -> MixtureStudyDefinition:
        return MixtureStudyDefinition(
            schema_version=8,
            name=self.name,
            mixture=self.mixture,
            process_factors=[
                m.factor
                for m in self.factor_mappings
                if not isinstance(m.factor, MixtureImportComponent)
            ],
            objective=self.objective,
            constraints=self.constraints,
        )

    @model_validator(mode="after")
    def validate_mapping(self) -> "MixtureDatasetImportPreflightRequest":
        self.definition()
        components = [
            MixtureComponentRequest.model_validate(m.factor.model_dump(exclude={"domain_kind"}))
            for m in self.factor_mappings
            if isinstance(m.factor, MixtureImportComponent)
        ]
        columns = [m.column_id for m in self.factor_mappings] + [
            m.column_id for m in self.response_mappings
        ]
        factors = [m.factor.factor_id for m in self.factor_mappings]
        responses = [m.response_id for m in self.response_mappings]
        if (
            components != self.mixture.components
            or len(set(columns)) != len(columns)
            or len(set(factors)) != len(factors)
            or len(set(responses)) != len(responses)
            or set(responses) != {r.response_id for r in self.objective.responses}
        ):
            raise ValueError("bayesian_import_mapping_invalid")
        return self


class MixtureDatasetImportCreateRequest(MixtureDatasetImportPreflightRequest):
    request_id: UUID
    expected_preflight_sha256: ImportHash


class MixtureDatasetImportPreflightResponse(DatasetImportPreflightResponse):
    schema_version: Literal[2] = 2  # type: ignore[assignment]


class MixtureDatasetImportedInitialDesign(DatasetImportedInitialDesign):
    import_schema_version: Literal[2] = 2  # type: ignore[assignment]
