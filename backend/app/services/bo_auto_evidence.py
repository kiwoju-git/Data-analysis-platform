"""Immutable Auto evidence. Restore/export validate bindings, never refit or rerun LOO."""

from __future__ import annotations

from typing import Any

from app.api.v1.schemas.bo_auto_strategy import AutoEvidenceRequest, AutoStrategyEvidence
from app.api.v1.schemas.bo_loo import LooCalculation, LooSnapshot
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_auto_strategy import suggest_augmentation
from app.storage.bo_planning import planning_sha


def build_auto_evidence(
    snapshot: dict[str, Any],
    identity: dict[str, Any],
    reference: dict[str, Any],
    *,
    mixed: bool = False,
) -> dict[str, Any]:
    """Called only inside the augmentation's single owned worker/deadline."""
    from app.statistics.bo_loo import planning_loo

    request = AutoEvidenceRequest.model_validate(reference)
    diagnostic = LooSnapshot(
        **identity,
        calculation=LooCalculation.model_validate(planning_loo(snapshot, mixed=mixed)),
        calculation_sha256="0" * 64,
    )
    diagnostic.calculation_sha256 = planning_sha(diagnostic.calculation.model_dump(mode="json"))
    source = snapshot["calculation_request"]
    decision = suggest_augmentation(
        [
            {"response_id": row.response_id, "r_squared": row.r_squared}
            for row in diagnostic.calculation.responses
        ],
        [factor.get("domain_kind", "continuous") for factor in source["factors"]],
        request.r_squared_threshold,
    )
    payload = {"diagnostic": diagnostic.model_dump(mode="json"), "decision": decision}
    digest = planning_sha(payload)
    if digest != request.expected_decision_sha256 or decision["recommended_policy"] is None:
        raise BayesianOptimizationError("bayesian_auto_evidence_mismatch")
    return AutoStrategyEvidence.model_validate({**payload, "decision_sha256": digest}).model_dump(
        mode="json"
    )


def validate_auto_evidence(
    evidence: AutoStrategyEvidence,
    reference: AutoEvidenceRequest,
    *,
    identity: dict[str, Any],
    snapshot: dict[str, Any],
    policy: str,
) -> None:
    """Bounded structural/digest checks; no posterior calculation on reads."""
    try:
        diagnostic = evidence.diagnostic
        source = snapshot["calculation_request"]
        expected_decision = suggest_augmentation(
            [
                {"response_id": row.response_id, "r_squared": row.r_squared}
                for row in diagnostic.calculation.responses
            ],
            [factor.get("domain_kind", "continuous") for factor in source["factors"]],
            reference.r_squared_threshold,
        )
        payload = evidence.model_dump(mode="json")
        if (
            any(payload["diagnostic"][key] != value for key, value in identity.items())
            or str(diagnostic.model_id) != str(reference.routing_model_id)
            or diagnostic.model_sha256 != reference.expected_model_sha256
            or diagnostic.calculation_sha256
            != planning_sha(diagnostic.calculation.model_dump(mode="json"))
            or evidence.decision.model_dump(mode="json") != expected_decision
            or evidence.decision.recommended_policy != policy
            or evidence.decision_sha256 != reference.expected_decision_sha256
            or evidence.decision_sha256
            != planning_sha({key: payload[key] for key in ("diagnostic", "decision")})
            or [row.response_id for row in diagnostic.calculation.responses]
            != [row["response_id"] for row in source["objective"]["responses"]]
        ):
            raise ValueError
        for response in diagnostic.calculation.responses:
            if [(str(row.trial_id), row.observed) for row in response.points] != [
                (row["trial_id"], row["response_values"][response.response_id])
                for row in source["observations"]
            ]:
                raise ValueError
    except (ValueError, KeyError, TypeError):
        raise BayesianOptimizationError("bayesian_auto_evidence_mismatch") from None


def evidence_identity(study_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "study_id": study_id,
        "model_id": record["model_id"],
        "model_sha256": record["snapshot_sha256"],
        "config_sha256": record["config_sha256"],
        "source_history_revision_id": record["source_history_revision_id"],
        "history_sha256": record["history_sha256"],
    }
