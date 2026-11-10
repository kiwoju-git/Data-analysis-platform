"""Augmentation is a saved selection policy, not conditional MC or a measured outcome."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityOrderedBatchItem,
    DesirabilityProvenance,
)
from app.api.v1.schemas.bo_augmentation import AugmentationCalculation, AugmentationSelectionRequest
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_planning import PlanningModelDetail, Sha256


class AugmentationBatchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: UUID | None
    model_sha256: Sha256 | None
    candidate_revision_id: UUID
    rows_sha256: Sha256
    selection_id: UUID
    selection_config_sha256: Sha256
    selection_result_sha256: Sha256


class AugmentationBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method_id: Literal["doe.bayesian_optimization"] = "doe.bayesian_optimization"
    method_version: Literal["0.14.0"] = "0.14.0"
    config_schema_version: Literal[9] = 9
    result_schema_version: Literal[9] = 9
    model_schema_version: Literal[9] = 9
    item_schema_version: Literal[4] = 4
    batch_size: int = Field(ge=1, le=8, strict=True)
    batch_policy: Literal["source_owned_augmentation_v1"] = "source_owned_augmentation_v1"
    batch_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: Sha256
    definition_sha256: Sha256
    source: AugmentationBatchSource
    objective: AnyDesirabilityObjective
    model: PlanningModelDetail | None
    calculation: AugmentationCalculation
    selection_request: AugmentationSelectionRequest
    items: list[DesirabilityOrderedBatchItem] = Field(min_length=1, max_length=8)
    config_sha256: Sha256
    result_sha256: Sha256
    created_at: str
    is_latest: bool = False
    batch_state: Literal[
        "pending", "partially_completed", "completed", "abandoned", "closed_mixed"
    ] = "pending"
    requested_total_trial_budget: int = Field(ge=2, le=200)
    provenance: DesirabilityProvenance

    @model_validator(mode="after")
    def exact_bundle(self) -> "AugmentationBatchResponse":
        if (
            self.batch_size != len(self.items)
            or self.batch_size != len(self.calculation.selected_rows)
            or [item.rank for item in self.items] != list(range(1, self.batch_size + 1))
            or len({item.item_id for item in self.items}) != self.batch_size
            or len({item.trial.trial_id for item in self.items}) != self.batch_size
            or any(item.batch_id != self.batch_id for item in self.items)
            or self.batch_id != self.source.selection_id
            or (self.model is None) != (self.source.model_id is None)
            or self.selection_request.policy != self.calculation.augmentation.policy
        ):
            raise ValueError("bayesian_augmentation_result_invalid")
        return self
