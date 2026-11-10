"""Read union for all immutable recommendation generations."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.bayesian_desirability_recommendations import DesirabilityAnyBatchResponse
from app.api.v1.schemas.bayesian_noise import BayesianAnyBatchResponse as ScalarBatchResponse
from app.api.v1.schemas.bo_augmentation_batch import AugmentationBatchResponse
from app.api.v1.schemas.bo_mixed_batch import MixedBatchResponse
from app.api.v1.schemas.bo_planning_batch import PlanningBatchResponse

BayesianAnyBatchResponse = (
    ScalarBatchResponse
    | DesirabilityAnyBatchResponse
    | PlanningBatchResponse
    | MixedBatchResponse
    | AugmentationBatchResponse
)


class BayesianAnyBatchListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study_id: UUID
    study_version_id: UUID
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[BayesianAnyBatchResponse]


class BayesianAnyLatestBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study_id: UUID
    study_version_id: UUID
    item: BayesianAnyBatchResponse | None
