"""Budgeted exact-candidate augmentation; stored fits are never re-optimized."""

from __future__ import annotations

import math
import time
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_augmentation import CONFIRM, REFINE, REFINE_V2, select_augmentation
from app.statistics.bo_candidate_points import validated_candidate_rows
from app.statistics.bo_desirability import finite_number


def build_augmentation_view(
    *,
    factors: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    points: list[dict[str, float]],
    existing_coordinates: list[list[float]],
    source: dict[str, Any],
    policy: str,
    batch_size: int,
    snapshot: dict[str, Any] | None,
    duplicate_tolerance: float,
    min_batch_distance_normalized: float,
    max_evaluations: int,
    max_moment_evaluations: int,
    time_budget_ms: int,
) -> dict[str, Any]:
    if (
        type(time_budget_ms) is not int
        or not 1000 <= time_budget_ms <= 60000
        or type(max_moment_evaluations) is not int
        or not 1 <= max_moment_evaluations <= 65536
    ):
        raise BayesianOptimizationError("bayesian_augmentation_input_invalid")
    deadline = time.perf_counter() + time_budget_ms / 1000
    keys = [factor["factor_id"] for factor in factors]
    model_required = policy in {REFINE, REFINE_V2, CONFIRM}
    if model_required != (snapshot is not None):
        raise BayesianOptimizationError("bayesian_augmentation_model_policy_mismatch")
    if not model_required and (
        source.get("model_snapshot_id") is not None
        or source.get("model_snapshot_sha256") is not None
    ):
        raise BayesianOptimizationError("bayesian_augmentation_model_policy_mismatch")

    def check_budget() -> None:
        if time.perf_counter() >= deadline:
            raise BayesianOptimizationError("bayesian_augmentation_time_budget_exhausted")

    incumbent = None
    response_context = None
    if snapshot is None:
        rows = validated_candidate_rows(
            points,
            factors,
            constraints,
            excluded_normalized=existing_coordinates,
            duplicate_tolerance=duplicate_tolerance,
            include_constraint_violations=True,
            check_budget=check_budget,
        )
        prediction_evaluations = 0
    else:
        # Importing/restoring the statistical model is unnecessary for MaxPro or
        # explicit maximin. Model-based selection restores once for the full set.
        from app.statistics.bo_planning_model import evaluate_planning_points

        raw = snapshot.get("calculation_request", {})
        if raw.get("factors") != factors or raw.get("constraints") != constraints:
            raise BayesianOptimizationError("bayesian_augmentation_source_mismatch")
        if raw.get("search", {}).get("duplicate_tolerance") != duplicate_tolerance:
            raise BayesianOptimizationError("bayesian_augmentation_source_mismatch")
        rows = evaluate_planning_points(
            snapshot,
            points,
            time_budget_ms=time_budget_ms,
            absolute_deadline=deadline,
            max_moment_evaluations=max_moment_evaluations,
            eligibility_excluded_normalized=existing_coordinates,
            compute_acquisition=policy != CONFIRM,
        )
        incumbent = snapshot["incumbent"]["latent_incumbent_value"]
        prediction_evaluations = len(rows)
        if policy == REFINE_V2:
            definitions = raw["objective"]["responses"]
            importance = [finite_number(item["importance"]) for item in definitions]
            if not 1 <= len(importance) <= 4 or any(value <= 0 for value in importance):
                raise BayesianOptimizationError("bayesian_augmentation_input_invalid")
            # Same max-scaled normalization as desirability importance, without
            # constructing surrogate goals or changing the saved curve policy.
            scaled = [value / max(importance) for value in importance]
            weights = [value / math.fsum(scaled) for value in scaled]
            scales = {
                item["response_id"]: item["model"]["normalization"]["scale"]
                for item in snapshot["response_models"]
            }
            response_context = [
                {
                    "response_id": item["response_id"],
                    "normalization_scale": scales[item["response_id"]],
                    "normalized_importance": weight,
                }
                for item, weight in zip(definitions, weights, strict=True)
            ]
    result = select_augmentation(
        rows,
        factor_kinds={
            factor["factor_id"]: factor.get("domain_kind", "continuous") for factor in factors
        },
        existing_coordinates=[
            dict(zip(keys, values, strict=True)) for values in existing_coordinates
        ],
        policy=policy,
        batch_size=batch_size,
        source=source,
        latent_incumbent=incumbent,
        duplicate_tolerance=duplicate_tolerance,
        min_batch_distance_normalized=min_batch_distance_normalized,
        max_evaluations=max_evaluations,
        time_budget_ms=time_budget_ms,
        absolute_deadline=deadline,
        response_uncertainty_context=response_context,
    )
    by_id = {row["row_id"]: row for row in rows}
    if time.perf_counter() >= deadline:
        raise BayesianOptimizationError("bayesian_augmentation_time_budget_exhausted")
    return {
        "schema_version": 1,
        "augmentation": result,
        "selected_rows": [by_id[key] for key in result["selected_row_ids"]],
        "source_row_count": len(rows),
        "prediction_evaluations": prediction_evaluations,
        "max_moment_evaluations": max_moment_evaluations,
        "time_budget_ms": time_budget_ms,
        "model_refit": False,
    }
