"""Explicit renewal identity, separate from historical selection hash payloads."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.v1.schemas.bo_augmentation import AugmentationSelectionResponse
from app.api.v1.schemas.bo_planning import Sha256


class AugmentationRenewalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_config_sha256: Sha256
    expected_result_sha256: Sha256


class AugmentationRenewalLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    study_version_id: UUID
    renewed_selection_id: UUID
    original_selection_id: UUID
    original_config_sha256: Sha256
    original_result_sha256: Sha256
    numerical_policy: Literal["positive_beta_integral_v2"]
    created_at: str


class AugmentationRenewalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selection: AugmentationSelectionResponse
    lineage: AugmentationRenewalLineage
