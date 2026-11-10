"""Persisted mixed candidate selections, separate from numeric batch readers."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from app.api.v1.schemas.bayesian_desirability_recommendations import DesirabilityProvenance
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_mixed_studies import MixedTrialResponse
from app.api.v1.schemas.bo_mixed_workflow import (
    MixedIncumbent,
    MixedResponseModel,
    MixedSelectionCalculation,
    MixedSelectionRequest,
)
from app.api.v1.schemas.bo_planning import Sha256


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MixedBatchSource(_Model):
    model_id: UUID | None
    model_sha256: Sha256 | None
    candidate_revision_id: UUID
    rows_sha256: Sha256
    selection_id: UUID
    selection_config_sha256: Sha256
    selection_result_sha256: Sha256

    @model_validator(mode="after")
    def optional_model_pair(self) -> "MixedBatchSource":
        if (self.model_id is None) != (self.model_sha256 is None):
            raise ValueError("bayesian_planning_model_mismatch")
        return self


class MixedBatchItem(_Model):
    item_id: UUID
    batch_id: UUID
    rank: int = Field(ge=1, le=8, strict=True)
    trial: MixedTrialResponse
    current_trial: MixedTrialResponse


class MixedBatchResponse(_Model):
    method_id: Literal["doe.bayesian_optimization"] = "doe.bayesian_optimization"
    method_version: Literal["0.15.0"] = "0.15.0"
    config_schema_version: Literal[10] = 10
    result_schema_version: Literal[10] = 10
    model_schema_version: Literal[10] = 10
    item_schema_version: Literal[5] = 5
    batch_size: int = Field(ge=1, le=8, strict=True)
    batch_policy: Literal["source_owned_mixed_planning_v1"] = "source_owned_mixed_planning_v1"
    batch_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: Sha256
    definition_sha256: Sha256
    source: MixedBatchSource
    objective: AnyDesirabilityObjective
    response_models: list[MixedResponseModel] | None = Field(min_length=1, max_length=4)
    incumbent: MixedIncumbent | None
    observation_view: dict[str, JsonValue] | None
    warnings: list[str] = Field(max_length=128)
    selection_request: MixedSelectionRequest
    calculation: MixedSelectionCalculation
    items: list[MixedBatchItem] = Field(min_length=1, max_length=8)
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
    def complete_bundle(self) -> "MixedBatchResponse":
        rows = (
            self.calculation.items
            if self.calculation.schema_version == 2
            else self.calculation.selected_rows
        )
        if (
            len(self.items) != self.batch_size
            or len(rows) != self.batch_size
            or [item.rank for item in self.items] != list(range(1, self.batch_size + 1))
            or len({item.item_id for item in self.items}) != self.batch_size
            or len({item.trial.trial_id for item in self.items}) != self.batch_size
            or any(item.batch_id != self.batch_id for item in self.items)
            or self.batch_id != self.source.selection_id
            or self.selection_request.batch_size != self.batch_size
            or self.selection_request.total_trial_budget != self.requested_total_trial_budget
            or (self.selection_request.kind == "manual_ordered")
            != (self.calculation.schema_version == 2)
            or any(
                item.trial.trial_id != item.current_trial.trial_id
                or item.trial.coordinates_sha256 != item.current_trial.coordinates_sha256
                or item.trial.actual_coordinates != row.actual_coordinates
                or item.trial.encoded_coordinates != row.encoded_coordinates
                for item, row in zip(self.items, rows, strict=True)
            )
        ):
            raise ValueError("bayesian_planning_result_invalid")
        model_free = self.source.model_id is None
        if (
            model_free != (self.response_models is None)
            or model_free != (self.incumbent is None)
            or model_free != (self.observation_view is None)
            or self.source.model_id != self.selection_request.model_id
            or self.source.model_sha256 != self.selection_request.expected_model_sha256
        ):
            raise ValueError("bayesian_planning_model_mismatch")
        return self


class MixedLatestBatchResponse(_Model):
    item: MixedBatchResponse | None
