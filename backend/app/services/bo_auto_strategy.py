"""Reuse verified saved-model LOO; never fit, write selections, or confirm trials."""

from typing import Any
from uuid import UUID

from app.api.v1.schemas.bo_auto_strategy import (
    AutoStrategyDecision,
    AutoStrategyRequest,
    AutoStrategyView,
)
from app.core.config import Settings
from app.services.bo_loo import get_loo_view
from app.statistics.bo_auto_strategy import suggest_augmentation
from app.storage.bo_planning import planning_sha


def get_auto_strategy(
    settings: Settings,
    study_id: UUID,
    model_id: UUID,
    body: AutoStrategyRequest,
    *,
    mixed: bool = False,
) -> AutoStrategyView:
    diagnostic = get_loo_view(settings, study_id, model_id, body, mixed=mixed)
    if mixed:
        from app.services.bo_mixed_studies import get_mixed_study

        study: Any = get_mixed_study(settings, study_id)
    else:
        from app.services.bayesian_studies import get_bayesian_study

        study = get_bayesian_study(settings, study_id)
    current = (
        diagnostic.source_is_current
        and str(study.observation_history.history_revision_id)
        == str(diagnostic.source_history_revision_id)
        and study.observation_history.observation_history_sha256 == diagnostic.history_sha256
    )
    diagnostic = diagnostic.model_copy(update={"source_is_current": current})
    decision = AutoStrategyDecision.model_validate(
        suggest_augmentation(
            [
                {"response_id": item.response_id, "r_squared": item.r_squared}
                for item in diagnostic.calculation.responses
            ],
            [factor.domain_kind for factor in study.factors],
            body.r_squared_threshold,
        )
    )
    # Include diagnostic source hashes and the decision in the receipt digest.
    digest = planning_sha(
        {
            "diagnostic": diagnostic.model_dump(mode="json", exclude={"source_is_current"}),
            "decision": decision.model_dump(mode="json"),
        }
    )
    return AutoStrategyView(
        diagnostic=diagnostic,
        decision=decision,
        decision_sha256=digest,
        apply_allowed=current
        and study.status == "active"
        and study.pending_trial_count == 0
        and decision.recommended_policy is not None,
    )
