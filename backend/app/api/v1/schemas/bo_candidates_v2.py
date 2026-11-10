"""Model-independent candidate table contract; no fabricated fitted model."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.bo_planning import (
    CandidateAppend,
    CandidateGeneration,
    CandidateImport,
    CandidateRemove,
    CandidateRevisionSummary,
    CandidateRow,
    Sha256,
)


class CandidateRevisionCreateRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2]
    request_id: UUID
    candidate_set_id: UUID
    name: str = Field(min_length=1, max_length=120)
    expected_head_revision_id: UUID | None
    expected_study_version_id: UUID
    expected_definition_sha256: Sha256
    expected_history_revision_id: UUID
    expected_history_sha256: Sha256
    expected_trial_count: int = Field(ge=1, le=200, strict=True)
    model_id: UUID | None = None
    expected_model_sha256: Sha256 | None = None
    duplicate_tolerance: float = Field(default=1e-6, ge=1e-12, le=0.1, allow_inf_nan=False)
    source: Annotated[
        CandidateGeneration | CandidateImport | CandidateAppend | CandidateRemove,
        Field(discriminator="kind"),
    ]
    include_constraint_violations: bool = False

    @model_validator(mode="after")
    def source_contract(self) -> CandidateRevisionCreateRequestV2:
        if (self.model_id is None) != (self.expected_model_sha256 is None):
            raise ValueError("bayesian_planning_model_mismatch")
        if self.source.kind in {"append_rows", "remove_rows"} and (
            self.expected_head_revision_id is None
        ):
            raise ValueError("bayesian_candidate_revision_conflict")
        return self


class CandidateRevisionSummaryV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2] = 2
    candidate_set_id: UUID
    name: str
    revision_id: UUID
    revision_number: int = Field(ge=1, le=64)
    parent_revision_id: UUID | None
    model_id: UUID | None
    model_sha256: Sha256 | None
    study_version_id: UUID
    source_history_revision_id: UUID
    definition_sha256: Sha256
    history_sha256: Sha256
    rows_sha256: Sha256
    config_sha256: Sha256
    excluded_coordinates_sha256: Sha256
    source_trial_count: int = Field(ge=1, le=200)
    duplicate_tolerance: float = Field(ge=1e-12, le=0.1, allow_inf_nan=False)
    row_count: int = Field(ge=1, le=10000)
    eligible_count: int = Field(ge=0, le=10000)
    created_at: str
    source_is_current: bool


class CandidatePageV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: CandidateRevisionSummaryV2
    offset: int = Field(ge=0, le=10000)
    limit: int = Field(ge=1, le=100)
    items: list[CandidateRow] = Field(max_length=100)


class CandidateSetListV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CandidateRevisionSummary | CandidateRevisionSummaryV2] = Field(max_length=32)
