"""Typed distance projection for augmentation; the GP keeps its category encoding."""

from __future__ import annotations

import math
import time
from typing import Any

from pydantic import TypeAdapter

from app.api.v1.schemas.bayesian import BayesianLinearConstraintRequest
from app.api.v1.schemas.bo_mixed_studies import (
    MixedFactorRequest,
    mixed_constraint_definitions,
    mixed_factor_domains,
)
from app.api.v1.schemas.bo_mixed_workflow import MixedAugmentationCalculation
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_augmentation import CONFIRM, REFINE_V2, select_augmentation
from app.statistics.bo_factor_domains import BoCategoricalFactorDomain
from app.statistics.bo_mixed_candidate_points import validated_mixed_candidate_rows


def build_mixed_augmentation(
    *,
    factors: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    points: list[dict[str, Any]],
    existing_coordinates: list[list[float]],
    source: dict[str, Any],
    policy: str,
    batch_size: int,
    snapshot: dict[str, Any] | None,
    duplicate_tolerance: float,
    ordinal_rank_distance: bool,
    min_batch_distance: float,
    max_evaluations: int,
    max_moment_evaluations: int,
    time_budget_ms: int,
) -> dict[str, Any]:
    deadline = time.perf_counter() + time_budget_ms / 1000
    domains = mixed_factor_domains(TypeAdapter(list[MixedFactorRequest]).validate_python(factors))
    checks = mixed_constraint_definitions(
        TypeAdapter(list[BayesianLinearConstraintRequest]).validate_python(constraints)
    )

    def budget() -> None:
        if time.perf_counter() >= deadline:
            raise BayesianOptimizationError("bayesian_augmentation_time_budget_exhausted")

    if snapshot is None:
        rows = validated_mixed_candidate_rows(
            points,
            domains,
            checks,
            excluded_encoded=existing_coordinates,
            duplicate_tolerance=duplicate_tolerance,
            ordinal_rank_distance=ordinal_rank_distance,
            include_constraint_violations=True,
            check_budget=budget,
        )
        incumbent, context = None, None
    else:
        from app.statistics.bo_mixed_planning import evaluate_mixed_planning_points

        raw = snapshot["calculation_request"]
        if (
            raw["factors"] != factors
            or raw["constraints"] != constraints
            or raw["search"]["duplicate_tolerance"] != duplicate_tolerance
        ):
            raise BayesianOptimizationError("bayesian_augmentation_source_mismatch")
        rows = evaluate_mixed_planning_points(
            snapshot,
            points,
            time_budget_ms=time_budget_ms,
            absolute_deadline=deadline,
            max_moment_evaluations=max_moment_evaluations,
            eligibility_excluded_encoded=existing_coordinates,
            compute_acquisition=policy != CONFIRM,
            ordinal_rank_distance=ordinal_rank_distance,
        )
        incumbent, context = snapshot["incumbent"]["latent_incumbent_value"], None
        if policy == REFINE_V2:
            goals = raw["objective"]["responses"]
            weights = [goal["importance"] / max(g["importance"] for g in goals) for goal in goals]
            scales = {
                m["response_id"]: m["model"]["normalization"]["scale"]
                for m in snapshot["response_models"]
            }
            context = [
                {
                    "response_id": goal["response_id"],
                    "normalization_scale": scales[goal["response_id"]],
                    "normalized_importance": weight / math.fsum(weights),
                }
                for goal, weight in zip(goals, weights, strict=True)
            ]

    # The augmentation helper's metric coordinates are separate from GP inputs:
    # nominal (and non-rank ordinal) entries remain equality tokens.
    kinds = {
        d.factor_id: ("ordinal" if d.kind == "ordinal" and ordinal_rank_distance else "nominal")
        if isinstance(d, BoCategoricalFactorDomain)
        else d.domain.domain_kind
        for d in domains
    }

    def metric(values: dict[str, float]) -> dict[str, Any]:
        return {
            d.factor_id: (
                values[d.factor_id] / (len(d.levels) - 1)
                if d.kind == "ordinal" and ordinal_rank_distance
                else d.decode(values[d.factor_id])
            )
            if isinstance(d, BoCategoricalFactorDomain)
            else values[d.factor_id]
            for d in domains
        }

    trace = select_augmentation(
        [{**row, "normalized_coordinates": metric(row["encoded_coordinates"])} for row in rows],
        factor_kinds=kinds,
        existing_coordinates=[
            metric(dict(zip(kinds, point, strict=True))) for point in existing_coordinates
        ],
        policy=policy,
        batch_size=batch_size,
        source=source,
        latent_incumbent=incumbent,
        duplicate_tolerance=duplicate_tolerance,
        min_batch_distance_normalized=min_batch_distance,
        ordinal_rank_distance=ordinal_rank_distance,
        max_evaluations=max_evaluations,
        time_budget_ms=time_budget_ms,
        absolute_deadline=deadline,
        response_uncertainty_context=context,
    )
    by_id = {row["row_id"]: row for row in rows}
    return MixedAugmentationCalculation.model_validate(
        {
            "schema_version": 3,
            "augmentation": trace,
            "selected_rows": [by_id[key] for key in trace["selected_row_ids"]],
            "source_row_count": len(rows),
            "prediction_evaluations": len(rows) if snapshot else 0,
            "max_moment_evaluations": max_moment_evaluations,
            "time_budget_ms": time_budget_ms,
            "model_refit": False,
        }
    ).model_dump(mode="json")
