"""Bounded planning operations using the same owned spawn/admission boundary as BO."""

from __future__ import annotations

import hashlib
import threading
import time
from multiprocessing.connection import Connection
from typing import Any

from app.services import bo_desirability_worker as execution
from app.services.analysis_run_execution import canonical_json_bytes
from app.statistics.bayesian_optimization import BayesianOptimizationError

MAX_PLANNING_BYTES = 16 * 1024 * 1024
PLANNING_ERRORS = frozenset(
    {
        "bayesian_planning_input_invalid",
        "bayesian_planning_snapshot_invalid",
        "bayesian_planning_result_invalid",
        "bayesian_planning_selection_invalid",
        "bayesian_planning_selection_ineligible",
        "bayesian_planning_selection_distance",
        "bayesian_candidate_range_precision_unsupported",
        "bayesian_candidate_input_invalid",
        "bayesian_candidate_coordinates_invalid",
        "bayesian_candidate_duplicate_row",
        "bayesian_candidate_constraint_violation",
        "bayesian_candidate_space_exhausted",
        "bayesian_candidate_generation_budget_exhausted",
        "bayesian_surrogate_snapshot_invalid",
        "bayesian_augmentation_input_invalid",
        "bayesian_augmentation_model_policy_mismatch",
        "bayesian_augmentation_source_mismatch",
        "bayesian_augmentation_result_invalid",
        "bayesian_augmentation_budget_exhausted",
        "bayesian_augmentation_distance_invalid",
        "bayesian_augmentation_duplicate_row",
        "bayesian_augmentation_insufficient_candidates",
        "bayesian_augmentation_ordinal_distance_required",
        "bayesian_augmentation_score_invalid",
        "bayesian_augmentation_time_budget_exhausted",
        "bayesian_maxpro_continuous_only",
        "bayesian_maxpro_projection_collision",
        "bayesian_mixed_planning_input_invalid",
        "bayesian_mixed_planning_snapshot_invalid",
        "bayesian_mixed_candidate_invalid",
        "bayesian_unique_conditions_insufficient",
        "bayesian_mixed_surrogate_input_invalid",
        "bayesian_mixed_surrogate_snapshot_invalid",
        "bayesian_mixed_snapshot_invalid",
        "bayesian_loo_diagnostic_invalid",
        "bayesian_auto_evidence_mismatch",
    }
)


def _calculate(operation: str, payload: dict[str, Any]) -> Any:
    if operation in {"auto_augmentation", "auto_mixed_augmentation"}:
        from app.services.bo_auto_evidence import build_auto_evidence

        evidence = build_auto_evidence(**payload["routing"])
        if evidence["decision"]["recommended_policy"] != payload["policy"]:
            raise BayesianOptimizationError("bayesian_auto_evidence_mismatch")
        result = _calculate(
            "mixed_augmentation" if operation == "auto_mixed_augmentation" else "augmentation",
            {key: value for key, value in payload.items() if key != "routing"},
        )
        return {
            **result,
            "schema_version": 4 if operation == "auto_mixed_augmentation" else 2,
            "auto_evidence": evidence,
        }
    if operation == "loo":
        from app.statistics.bo_loo import planning_loo

        return planning_loo(**payload)
    from app.statistics.bo_candidate_points import (
        generate_candidate_points,
        validated_candidate_rows,
    )
    from app.statistics.bo_planning_model import (
        evaluate_planning_points,
        fit_planning_model,
        score_ordered_selection,
    )

    if operation in {"mixed_fit", "mixed_evaluate"}:
        from app.statistics.bo_mixed_planning import (
            evaluate_mixed_planning_points,
            fit_mixed_planning_model,
        )

        if operation == "mixed_fit":
            return fit_mixed_planning_model(payload)
        return evaluate_mixed_planning_points(**payload)
    if operation == "mixed_candidates":
        from app.services.bo_mixed_workflow_contract import calculate_mixed_candidates

        return calculate_mixed_candidates(payload)
    if operation == "mixed_selection":
        from app.statistics.bo_mixed_planning import score_mixed_ordered_selection

        return score_mixed_ordered_selection(**payload)
    if operation == "mixed_augmentation":
        from app.statistics.bo_mixed_augmentation import build_mixed_augmentation

        return build_mixed_augmentation(**payload)

    if operation == "fit":
        return fit_planning_model(payload)
    if operation == "evaluate":
        return evaluate_planning_points(**payload)
    if operation == "selection":
        return score_ordered_selection(**payload)
    if operation == "augmentation":
        from app.statistics.bo_augmentation_view import build_augmentation_view

        return build_augmentation_view(
            **{key: value for key, value in payload.items() if key != "source_rows"}
        )
    if operation == "candidates":
        source = payload["source"]
        generation = None
        if source["kind"] == "seeded_uniform":
            generation = generate_candidate_points(
                payload["factors"],
                payload["constraints"],
                count=source["count"],
                seed=source["seed"],
                include_constraint_violations=payload["include_violations"],
            )
            points = generation["points"]
        elif source["kind"] == "explicit_rows":
            points = source["points"]
        else:
            raise BayesianOptimizationError("bayesian_candidate_input_invalid")
        rows = validated_candidate_rows(
            points,
            payload["factors"],
            payload["constraints"],
            excluded_normalized=payload["excluded"],
            duplicate_tolerance=payload["tolerance"],
            include_constraint_violations=payload["include_violations"],
        )
        return {
            "rows": rows,
            "generation": None
            if generation is None
            else {key: value for key, value in generation.items() if key != "points"},
        }
    raise BayesianOptimizationError("bayesian_planning_input_invalid")


def _worker_entry(output: Connection, payload_bytes: bytes) -> None:
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    from app.services.bo_planning_contract import (
        validate_candidate_generation,
        validate_planning_evaluation,
        validate_planning_selection,
    )
    from app.statistics.bo_planning_model import PlanningEvaluationBudget, restore_planning_model

    try:
        envelope = execution._read_json(payload_bytes)
        if not isinstance(envelope, dict) or set(envelope) != {
            "operation",
            "payload",
            "time_budget_ms",
        }:
            raise BayesianOptimizationError("bayesian_planning_input_invalid")
        duration = envelope["time_budget_ms"]
        if type(duration) is not int or not 1000 <= duration <= 60_000:
            raise BayesianOptimizationError("bayesian_planning_input_invalid")
        deadline = time.perf_counter() + duration / 1000
        operation, payload = envelope["operation"], envelope["payload"]
        with threadpool_limits(limits=1):
            result = _calculate(operation, payload)
            # Numerical revalidation shares admission, thread limit and the
            # original hard-timeout process, rather than starting a parent fit.
            if operation == "loo":
                from app.api.v1.schemas.bo_loo import LooCalculation

                result = LooCalculation.model_validate(result).model_dump(mode="json")
            elif operation == "mixed_fit":
                from app.statistics.bo_mixed_planning import restore_mixed_planning_model

                if result["calculation_request"] != payload:
                    raise BayesianOptimizationError("bayesian_mixed_planning_snapshot_invalid")
                restore_mixed_planning_model(
                    result,
                    budget=PlanningEvaluationBudget(deadline, payload["max_moment_evaluations"]),
                )
            elif operation == "mixed_evaluate":
                from app.services.bo_mixed_workflow_contract import validate_mixed_evaluation

                validate_mixed_evaluation(payload, result, deadline=deadline)
            elif operation == "mixed_candidates":
                from app.services.bo_mixed_workflow_contract import validate_mixed_candidates

                validate_mixed_candidates(payload, result, deadline=deadline)
            elif operation in {"mixed_selection", "mixed_augmentation", "auto_mixed_augmentation"}:
                from app.services.bo_mixed_workflow_contract import validate_mixed_selection

                if operation == "auto_mixed_augmentation":
                    validate_mixed_selection(
                        "mixed_augmentation",
                        {key: value for key, value in payload.items() if key != "routing"},
                        {
                            **{
                                key: value
                                for key, value in result.items()
                                if key != "auto_evidence"
                            },
                            "schema_version": 3,
                        },
                        deadline=deadline,
                    )
                else:
                    validate_mixed_selection(operation, payload, result, deadline=deadline)
            elif operation == "fit":
                if result["calculation_request"] != payload:
                    raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
                restore_planning_model(result, budget=PlanningEvaluationBudget(deadline, 4096))
            elif operation == "evaluate":
                validate_planning_evaluation(
                    payload["snapshot"],
                    payload["points"],
                    payload["eligibility_excluded_normalized"],
                    result,
                    deadline=deadline,
                )
            elif operation == "selection":
                validate_planning_selection(
                    payload["snapshot"],
                    payload["points"],
                    payload["eligibility_excluded_normalized"],
                    result,
                    deadline=deadline,
                )
            elif operation in {"augmentation", "auto_augmentation"}:
                from app.services.bo_augmentation_contract import validate_augmentation_binding

                validate_augmentation_binding(
                    result,
                    request=payload,
                    snapshot=payload["snapshot"],
                    rows=payload["source_rows"],
                    existing_coordinates=payload["existing_coordinates"],
                )
            else:
                validate_candidate_generation(payload, result)
            if operation in {"auto_augmentation", "auto_mixed_augmentation"}:
                from app.api.v1.schemas.bo_auto_strategy import (
                    AutoEvidenceRequest,
                    AutoStrategyEvidence,
                )
                from app.services.bo_auto_evidence import validate_auto_evidence

                routing = payload["routing"]
                validate_auto_evidence(
                    AutoStrategyEvidence.model_validate(result["auto_evidence"]),
                    AutoEvidenceRequest.model_validate(routing["reference"]),
                    identity=routing["identity"],
                    snapshot=routing["snapshot"],
                    policy=payload["policy"],
                )
            if time.perf_counter() >= deadline:
                raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")
        message = {
            "status": "ok",
            "request_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "result": result,
        }
    except BayesianOptimizationError as exc:
        message = {
            "status": "error",
            "code": exc.code
            if exc.code in execution._ALLOWED_ERRORS | PLANNING_ERRORS
            else "bayesian_planning_input_invalid",
        }
    except Exception:
        message = {"status": "error", "code": "bayesian_planning_input_invalid"}
    try:
        data = canonical_json_bytes(message)
        if len(data) > MAX_PLANNING_BYTES:
            data = canonical_json_bytes(
                {
                    "status": "error",
                    "code": "bayesian_desirability_result_too_large",
                }
            )
        output.send_bytes(data)
    finally:
        output.close()


def run_planning_operation(
    operation: str,
    payload: dict[str, Any],
    *,
    time_budget_ms: int = 60_000,
    cancel: threading.Event | None = None,
) -> Any:
    if operation not in {
        "loo",
        "fit",
        "evaluate",
        "selection",
        "candidates",
        "augmentation",
        "auto_augmentation",
        "auto_mixed_augmentation",
        "mixed_fit",
        "mixed_evaluate",
        "mixed_candidates",
        "mixed_selection",
        "mixed_augmentation",
    } or (type(time_budget_ms) is not int or not 1000 <= time_budget_ms <= 60_000):
        raise BayesianOptimizationError("bayesian_planning_input_invalid")
    if not execution._ADMISSION.acquire(blocking=False):
        raise BayesianOptimizationError("bayesian_desirability_worker_busy")
    try:
        if cancel is not None and cancel.is_set():
            raise BayesianOptimizationError("bayesian_desirability_cancelled")
        encoded = canonical_json_bytes(
            {"operation": operation, "payload": payload, "time_budget_ms": time_budget_ms}
        )
        if len(encoded) > MAX_PLANNING_BYTES:
            raise BayesianOptimizationError("bayesian_desirability_input_too_large")
        raw = execution._run_owned_worker(
            encoded,
            timeout_ms=time_budget_ms + 20_000,
            cancel=cancel,
            entrypoint=_worker_entry,
            max_result_bytes=MAX_PLANNING_BYTES,
        )
        if cancel is not None and cancel.is_set():
            raise BayesianOptimizationError("bayesian_desirability_cancelled")
        try:
            message = execution._read_json(raw)
            if not isinstance(message, dict):
                raise ValueError
            if message.get("status") == "error":
                code = message.get("code")
                raise BayesianOptimizationError(
                    code
                    if isinstance(code, str) and code in execution._ALLOWED_ERRORS | PLANNING_ERRORS
                    else "bayesian_planning_input_invalid"
                )
            if set(message) != {"status", "request_sha256", "result"} or (
                message["status"] != "ok"
                or message["request_sha256"] != hashlib.sha256(encoded).hexdigest()
            ):
                raise ValueError
            return message["result"]
        except BayesianOptimizationError:
            raise
        except (ValueError, TypeError, KeyError):
            raise BayesianOptimizationError("bayesian_planning_snapshot_invalid") from None
    finally:
        execution._ADMISSION.release()
