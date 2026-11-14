"""Typed study-8 projections for the existing immutable trial lifecycle."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.bayesian import (
    BayesianHistoryRevisionResponse,
    BayesianStudyLifecycleEventResponse,
)
from app.api.v1.schemas.bo_mixture import MixtureStudyResponse, MixtureTrialResponse


class MixtureObservationBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_schema_version: Literal[3] = 3
    study: MixtureStudyResponse
    completed_trial_ids: list[UUID]
    completed_trial_count: int = Field(ge=1, le=200)
    observation_history: BayesianHistoryRevisionResponse
    request_id: UUID
    created_at: str


class MixtureTrialListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study_id: UUID
    study_version_id: UUID
    total: int = Field(ge=0, le=200)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[MixtureTrialResponse]


class MixtureTrialTransitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study_id: UUID
    trial: MixtureTrialResponse
    observation_history: BayesianHistoryRevisionResponse


class MixtureStudyCloseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    study: MixtureStudyResponse
    lifecycle_event: BayesianStudyLifecycleEventResponse


class MixtureReplicateCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[3] = 3
    study_id: UUID
    study_version_id: UUID
    request_id: UUID
    parent_trial_id: UUID
    source_history_revision_id: UUID
    source_history_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    trials: list[MixtureTrialResponse] = Field(min_length=1, max_length=8)
    replayed: bool
