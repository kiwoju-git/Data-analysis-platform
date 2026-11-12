"""Selected immutable dataset to completed BO observations; no generated points."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.analyses import AnalysisFilterSnapshot
from app.api.v1.schemas.bayesian import (
    BayesianFactorRequest,
    BayesianLinearConstraintRequest,
    BayesianObjectiveRequest,
)
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_dataset_source import ImportHash
from app.api.v1.schemas.bo_mixed_studies import MixedCategoricalFactorRequest


class DatasetFactorMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column_id: str = Field(min_length=1, max_length=128)
    factor: BayesianFactorRequest | MixedCategoricalFactorRequest


class DatasetResponseMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column_id: str = Field(min_length=1, max_length=128)
    response_id: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


class DatasetImportPreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=120)
    dataset_version_id: UUID
    expected_schema_hash: ImportHash
    factor_mappings: list[DatasetFactorMapping] = Field(min_length=1, max_length=10)
    objective: BayesianObjectiveRequest | AnyDesirabilityObjective
    response_mappings: list[DatasetResponseMapping] = Field(min_length=1, max_length=10)
    constraints: list[BayesianLinearConstraintRequest] = Field(default_factory=list, max_length=16)
    filter_snapshot: AnalysisFilterSnapshot
    missing_policy: Literal["reject", "complete_case"]

    @model_validator(mode="after")
    def validate_mapping(self) -> "DatasetImportPreflightRequest":
        factors = [item.factor.factor_id for item in self.factor_mappings]
        columns = [item.column_id for item in self.factor_mappings] + [
            item.column_id for item in self.response_mappings
        ]
        responses = [item.response_id for item in self.response_mappings]
        if (
            not self.name.strip()
            or len(factors) != len(set(factors))
            or len(columns) != len(set(columns))
        ):
            raise ValueError("bayesian_import_mapping_invalid")
        if isinstance(self.objective, BayesianObjectiveRequest):
            if responses != [None]:
                raise ValueError("bayesian_import_scalar_mapping_invalid")
            if any(
                isinstance(item.factor, MixedCategoricalFactorRequest)
                for item in self.factor_mappings
            ):
                raise ValueError("bayesian_mixed_requires_response_vector")
        elif len(responses) != len(set(responses)) or set(responses) != {
            item.response_id for item in self.objective.responses
        }:
            raise ValueError("bayesian_import_response_mapping_invalid")
        return self


class DatasetImportCreateRequest(DatasetImportPreflightRequest):
    request_id: UUID
    expected_preflight_sha256: ImportHash
