"""Transient review contracts, separate from committed experiment artifacts."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.bayesian_noise import BayesianNoiseCalculation


class BayesianRecommendationReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    review_id: UUID
    study_id: UUID
    study_version_id: UUID
    source_history_revision_id: UUID
    source_observation_history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_at: str
    calculation: BayesianNoiseCalculation


class BayesianRecommendationReviewConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
