"""Manual candidate batches are not advertised as automatic acquisition search."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.bayesian_desirability import DesirabilityObjective
from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityOrderedBatchItem,
    DesirabilityProvenance,
)
from app.api.v1.schemas.bo_curve_policy import VersionedCurveObjective
from app.api.v1.schemas.bo_desirability_calculation import (
    _Incumbent,
    _ResponseModelResult,
    _SharedObservationView,
)
from app.api.v1.schemas.bo_fit_quality import _ResponseModel
from app.api.v1.schemas.bo_planning import PlanningSelectionCalculation, Sha256


class PlanningBatchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: UUID
    model_sha256: Sha256
    candidate_revision_id: UUID
    rows_sha256: Sha256
    selection_id: UUID
    selection_config_sha256: Sha256
    selection_result_sha256: Sha256


class PlanningBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method_id: Literal["doe.bayesian_optimization"] = "doe.bayesian_optimization"
    method_version: Literal["0.13.0"] = "0.13.0"
    config_schema_version: Literal[8] = 8
    result_schema_version: Literal[8] = 8
    model_schema_version: Literal[8] = 8
    item_schema_version: Literal[4] = 4
    batch_size: int = Field(ge=1, le=8, strict=True)
    batch_policy: Literal["manual_ordered_fixed_model_v1"] = "manual_ordered_fixed_model_v1"
    batch_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: Sha256
    definition_sha256: Sha256
    source: PlanningBatchSource
    objective: DesirabilityObjective | VersionedCurveObjective
    response_models: list[_ResponseModelResult | _ResponseModel] = Field(min_length=1, max_length=4)
    incumbent: _Incumbent
    observation_view: _SharedObservationView
    warnings: list[str] = Field(max_length=64)
    calculation: PlanningSelectionCalculation
    items: list[DesirabilityOrderedBatchItem] = Field(min_length=1, max_length=8)
    config_sha256: Sha256
    result_sha256: Sha256
    created_at: str
    is_latest: bool = False
    batch_state: Literal[
        "pending",
        "partially_completed",
        "completed",
        "abandoned",
        "closed_mixed",
    ] = "pending"
    requested_total_trial_budget: int = Field(ge=2, le=200)
    provenance: DesirabilityProvenance

    @model_validator(mode="after")
    def validate_bundle(self) -> PlanningBatchResponse:
        if (
            self.batch_size != len(self.items)
            or len(self.calculation.items) != self.batch_size
            or [item.rank for item in self.items] != list(range(1, self.batch_size + 1))
            or len({item.item_id for item in self.items}) != self.batch_size
            or len({item.trial.trial_id for item in self.items}) != self.batch_size
            or any(item.batch_id != self.batch_id for item in self.items)
            or self.batch_id != self.source.selection_id
        ):
            raise ValueError("bayesian_planning_result_invalid")
        return self


class PlanningLatestBatchResponse(BaseModel):
    item: PlanningBatchResponse | None
