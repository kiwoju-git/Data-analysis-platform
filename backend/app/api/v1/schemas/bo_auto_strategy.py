"""A read-only suggestion receipt, deliberately not a saved selection contract."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from app.api.v1.schemas.bo_loo import LooRequest, LooSnapshot, LooView
from app.api.v1.schemas.bo_planning import Sha256


class AutoStrategyRequest(LooRequest):
    r_squared_threshold: FiniteFloat = Field(default=0.25, ge=0, le=1, strict=True)


class AutoStrategyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    policy: Literal["conditional_loo_any_low_explore_else_refine_v1"]
    threshold: FiniteFloat = Field(ge=0, le=1)
    comparison: Literal["strictly_less_than"]
    recommended_policy: (
        Literal[
            "greedy_incremental_maxpro_v1",
            "greedy_mixed_maximin_v1",
            "refine_ei_alternating_desirability_response_sd_v2",
        ]
        | None
    )
    reason: Literal[
        "r_squared_unavailable",
        "any_response_below_threshold",
        "all_responses_meet_threshold",
    ]
    response_ids: list[str] = Field(min_length=1, max_length=4)
    below_threshold_response_ids: list[str] = Field(max_length=4)
    unavailable_response_ids: list[str] = Field(max_length=4)
    ordinal_rank_distance_requires_consent: bool
    warnings: list[str] = Field(min_length=2, max_length=3)


class AutoStrategyView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    decision_only: Literal[True] = True
    selection_created: Literal[False] = False
    diagnostic: LooView
    decision: AutoStrategyDecision
    decision_sha256: Sha256
    apply_allowed: bool


class AutoEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    routing_model_id: UUID
    expected_model_sha256: Sha256
    r_squared_threshold: FiniteFloat = Field(ge=0, le=1, strict=True)
    expected_decision_sha256: Sha256


class AutoStrategyEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    diagnostic: LooSnapshot
    decision: AutoStrategyDecision
    decision_sha256: Sha256
