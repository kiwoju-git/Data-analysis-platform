"""Explicit fixed-candidate policies, separate from conditional MC acquisition."""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.statistics.bayesian_optimization import BayesianOptimizationError

MAXPRO = "greedy_incremental_maxpro_v1"
MIXED_MAXIMIN = "greedy_mixed_maximin_v1"
REFINE = "refine_ei_then_desirability_sd_v1"
REFINE_V2 = "refine_ei_alternating_desirability_response_sd_v2"
CONFIRM = "confirm_mean_then_competitive_sd_v1"
POLICIES = (MAXPRO, MIXED_MAXIMIN, REFINE, REFINE_V2, CONFIRM)
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_KINDS = {"continuous", "discrete_numeric", "nominal", "ordinal"}


def _error(code: str = "bayesian_augmentation_input_invalid") -> BayesianOptimizationError:
    return BayesianOptimizationError(code)


def _number(value: Any, low: float, high: float) -> float:
    if type(value) not in {int, float}:
        raise _error()
    try:
        number = float(value)
    except OverflowError:
        raise _error() from None
    if not low <= number <= high or not math.isfinite(number):
        raise _error()
    return number


@dataclass
class _Budget:
    maximum: int
    deadline: float
    evaluations: int = 0
    pair_comparisons: int = 0

    def check(self) -> None:
        if time.perf_counter() >= self.deadline:
            raise _error("bayesian_augmentation_time_budget_exhausted")

    def consume(self) -> None:
        self.check()
        if self.evaluations >= self.maximum:
            raise _error("bayesian_augmentation_budget_exhausted")
        self.evaluations += 1


@dataclass(frozen=True)
class _Candidate:
    row_id: str
    coordinates: tuple[Any, ...]
    nearest_existing: float
    mean: float | None
    variance: float | None
    ei: float | None
    response_sd: float | None


def _response_context(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not 1 <= len(value) <= 4:
        raise _error()
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if type(item) is not dict or set(item) != {
            "response_id",
            "normalization_scale",
            "normalized_importance",
        }:
            raise _error()
        key = item["response_id"]
        if not isinstance(key, str) or not key or len(key) > 128 or key in seen:
            raise _error()
        seen.add(key)
        scale = _number(item["normalization_scale"], 0, math.inf)
        weight = _number(item["normalized_importance"], 0, 1)
        if scale == 0 or weight == 0:
            raise _error()
        result.append(
            {"response_id": key, "normalization_scale": scale, "normalized_importance": weight}
        )
    if not math.isclose(
        math.fsum(item["normalized_importance"] for item in result),
        1.0,
        rel_tol=0,
        abs_tol=16 * math.ulp(1.0),
    ):
        raise _error()
    return sorted(result, key=lambda item: item["response_id"])


def _response_sd(row: dict[str, Any], context: list[dict[str, Any]]) -> float:
    predictions = row.get("response_predictions")
    if type(predictions) is not list or len(predictions) != len(context):
        raise _error()
    by_id: dict[str, Any] = {}
    for prediction in predictions:
        if type(prediction) is not dict:
            raise _error()
        key = prediction.get("response_id")
        if not isinstance(key, str) or key in by_id:
            raise _error()
        by_id[key] = prediction
    if set(by_id) != {item["response_id"] for item in context}:
        raise _error()
    terms = []
    for item in context:
        sd = _number(by_id[item["response_id"]].get("latent_standard_deviation_raw"), 0, math.inf)
        ratio = sd / item["normalization_scale"]
        term = math.sqrt(item["normalized_importance"]) * ratio
        if not math.isfinite(term) or (sd > 0 and term == 0):
            raise _error("bayesian_augmentation_score_invalid")
        terms.append(term)
    # hypot avoids squaring overflow/underflow in otherwise representable RMS values.
    result = math.hypot(*terms)
    if not math.isfinite(result):
        raise _error("bayesian_augmentation_score_invalid")
    return result


def _source(value: Any, model_required: bool) -> dict[str, Any]:
    fields = {
        "model_snapshot_id",
        "model_snapshot_sha256",
        "candidate_revision_id",
        "candidate_revision_sha256",
        "history_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error()
    has_model = value["model_snapshot_id"] is not None
    if has_model != (value["model_snapshot_sha256"] is not None) or (
        model_required and not has_model
    ):
        raise _error()
    for key in ("model_snapshot_id", "candidate_revision_id"):
        identifier = value[key]
        if identifier is None and key == "model_snapshot_id":
            continue
        if not isinstance(identifier, str):
            raise _error()
        try:
            if str(UUID(identifier)) != identifier:
                raise _error()
        except ValueError:
            raise _error() from None
    for key in ("model_snapshot_sha256", "candidate_revision_sha256", "history_sha256"):
        digest = value[key]
        if digest is None and key == "model_snapshot_sha256":
            continue
        if not isinstance(digest, str) or _HASH.fullmatch(digest) is None:
            raise _error()
    return dict(value)


def _coordinates(value: Any, factors: dict[str, str]) -> tuple[Any, ...]:
    if type(value) is not dict or set(value) != set(factors):
        raise _error()
    result: list[Any] = []
    for key, kind in factors.items():
        coordinate = value[key]
        if kind == "nominal":
            # Codes/labels are equality tokens, never distances between arbitrary codes.
            if type(coordinate) is str:
                if not coordinate or len(coordinate) > 512:
                    raise _error()
            elif type(coordinate) is int:
                if not 0 <= coordinate <= 31:
                    raise _error()
            else:
                raise _error()
            result.append(coordinate)
        else:
            result.append(_number(coordinate, 0, 1))
    return tuple(result)


def _distance(
    left: tuple[Any, ...], right: tuple[Any, ...], kinds: tuple[str, ...], budget: _Budget
) -> float:
    budget.pair_comparisons += 1
    terms = [
        float(a != b) if kind == "nominal" else a - b
        for a, b, kind in zip(left, right, kinds, strict=True)
    ]
    value = math.hypot(*terms)
    if not math.isfinite(value):
        raise _error("bayesian_augmentation_distance_invalid")
    return value


def _log_projection_cost(left: tuple[Any, ...], right: tuple[Any, ...]) -> float | None:
    differences = [abs(a - b) for a, b in zip(left, right, strict=True)]
    if any(value == 0 for value in differences):
        return None
    return -2 * math.fsum(math.log(value) for value in differences)


def _log_sum(values: list[float]) -> float:
    maximum = max(values)
    return maximum + math.log(math.fsum(math.exp(value - maximum) for value in values))


def _candidates(
    rows: Any,
    factors: dict[str, str],
    reference: list[tuple[Any, ...]],
    tolerance: float,
    model_required: bool,
    budget: _Budget,
    acquisition_required: bool,
    response_context: list[dict[str, Any]] | None,
) -> list[_Candidate]:
    if type(rows) is not list or not 1 <= len(rows) <= 10_000:
        raise _error()
    seen_ids: set[str] = set()
    seen_coordinates: set[tuple[Any, ...]] = set()
    result = []
    kinds = tuple(factors.values())
    for row in rows:
        budget.check()
        if type(row) is not dict:
            raise _error()
        identifier = row.get("row_id")
        if (
            not isinstance(identifier, str)
            or _HASH.fullmatch(identifier) is None
            or identifier in seen_ids
            or any(
                type(row.get(key)) is not bool
                for key in ("eligible", "novel", "constraints_satisfied")
            )
            or row["eligible"] != (row["novel"] and row["constraints_satisfied"])
        ):
            raise _error()
        point = _coordinates(row.get("normalized_coordinates"), factors)
        if point in seen_coordinates:
            raise _error("bayesian_augmentation_duplicate_row")
        seen_ids.add(identifier)
        seen_coordinates.add(point)
        mean = variance = improvement = response_sd = None
        if model_required:
            moments = row.get("desirability_moments")
            if type(moments) is not dict:
                raise _error()
            mean = _number(moments.get("mean"), 0, 1)
            variance = _number(moments.get("variance"), 0, mean * (1 - mean))
        if acquisition_required:
            acquisition = row.get("acquisition")
            if type(acquisition) is not dict:
                raise _error()
            improvement = _number(acquisition.get("value"), 0, 1)
        if response_context is not None:
            response_sd = _response_sd(row, response_context)
        if not row["eligible"]:
            continue
        nearest = min(_distance(point, previous, kinds, budget) for previous in reference)
        if nearest > tolerance:
            result.append(
                _Candidate(identifier, point, nearest, mean, variance, improvement, response_sd)
            )
    return result


def select_augmentation(
    rows: list[dict[str, Any]],
    *,
    factor_kinds: dict[str, str],
    existing_coordinates: list[dict[str, Any]],
    policy: str,
    batch_size: int,
    source: dict[str, Any],
    latent_incumbent: float | None = None,
    duplicate_tolerance: float = 1e-6,
    min_batch_distance_normalized: float = 0.0,
    ordinal_rank_distance: bool = False,
    max_evaluations: int = 100_000,
    time_budget_ms: int = 60_000,
    absolute_deadline: float | None = None,
    response_uncertainty_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Select exact stored rows atomically; this function never fits or writes.

    The service must verify the model/candidate/source hashes before supplying
    rows. Numeric/ordinal coordinates are normalized; nominal entries are tokens.
    """
    if (
        policy not in POLICIES
        or type(batch_size) is not int
        or not 1 <= batch_size <= 8
        or type(factor_kinds) is not dict
        or not 1 <= len(factor_kinds) <= 10
        or any(not isinstance(key, str) or not key or len(key) > 80 for key in factor_kinds)
        or any(type(kind) is not str or kind not in _KINDS for kind in factor_kinds.values())
        or type(ordinal_rank_distance) is not bool
        or type(max_evaluations) is not int
        or not 1 <= max_evaluations <= 100_000
        or type(time_budget_ms) is not int
        or not 1000 <= time_budget_ms <= 60_000
        or type(existing_coordinates) is not list
        or not 1 <= len(existing_coordinates) <= 400
    ):
        raise _error()
    kinds = tuple(factor_kinds.values())
    if policy == MAXPRO and any(kind != "continuous" for kind in kinds):
        raise _error("bayesian_maxpro_continuous_only")
    if "ordinal" in kinds and not ordinal_rank_distance:
        raise _error("bayesian_augmentation_ordinal_distance_required")
    tolerance = _number(duplicate_tolerance, 1e-12, 0.1)
    minimum = _number(min_batch_distance_normalized, 0, math.sqrt(len(kinds)))
    if policy == CONFIRM:
        threshold = _number(latent_incumbent, 0, 1)
    elif latent_incumbent is not None:
        _number(latent_incumbent, 0, 1)
        threshold = None
    else:
        threshold = None
    model_required = policy in {REFINE, REFINE_V2, CONFIRM}
    context = _response_context(response_uncertainty_context) if policy == REFINE_V2 else None
    if policy != REFINE_V2 and response_uncertainty_context is not None:
        raise _error()
    identity = _source(source, model_required)
    deadline = time.perf_counter() + time_budget_ms / 1000
    if absolute_deadline is not None:
        if not math.isfinite(absolute_deadline):
            raise _error()
        deadline = min(deadline, absolute_deadline)
    budget = _Budget(max_evaluations, deadline)
    budget.check()
    reference = list(dict.fromkeys(_coordinates(row, factor_kinds) for row in existing_coordinates))
    candidates = _candidates(
        rows,
        factor_kinds,
        reference,
        tolerance,
        model_required,
        budget,
        policy in {REFINE, REFINE_V2},
        context,
    )
    if len(candidates) < batch_size:
        raise _error("bayesian_augmentation_insufficient_candidates")
    selected: list[_Candidate] = []
    steps: list[dict[str, Any]] = []
    unscorable: dict[str, dict[str, Any]] = {}
    projection_collisions = 0
    for rank in range(1, batch_size + 1):
        comparisons: list[tuple[float, str, _Candidate, float | None, str]] = []
        current_projection_collisions = 0
        for candidate in candidates:
            if any(previous.row_id == candidate.row_id for previous in selected):
                continue
            budget.consume()
            nearest = min(
                (
                    _distance(candidate.coordinates, previous.coordinates, kinds, budget)
                    for previous in selected
                ),
                default=None,
            )
            if nearest is not None and (nearest <= tolerance or nearest < minimum):
                continue
            if policy == MAXPRO:
                cost = [
                    _log_projection_cost(candidate.coordinates, previous)
                    for previous in [*reference, *(item.coordinates for item in selected)]
                ]
                budget.pair_comparisons += len(cost)
                if any(value is None for value in cost):
                    projection_collisions += 1
                    current_projection_collisions += 1
                    unscorable.setdefault(
                        candidate.row_id,
                        {
                            "row_id": candidate.row_id,
                            "first_rank": rank,
                            "score": None,
                            "status": "projection_collision",
                        },
                    )
                    continue
                score = _log_sum([value for value in cost if value is not None])
                criterion = "log_incremental_inverse_projection_distance"
            elif policy == MIXED_MAXIMIN:
                score = -min(
                    candidate.nearest_existing, nearest if nearest is not None else math.inf
                )
                criterion = "minimum_explicit_mixed_distance"
            elif policy in {REFINE, REFINE_V2} and rank == 1:
                assert candidate.ei is not None
                score = -candidate.ei
                criterion = "base_desirability_beta_ei"
            elif policy == CONFIRM and rank == 1:
                assert candidate.mean is not None
                score = -candidate.mean
                criterion = "base_expected_desirability"
            elif policy == REFINE_V2 and rank % 2 == 1:
                assert candidate.response_sd is not None
                score = -candidate.response_sd
                criterion = "base_response_normalized_latent_standard_deviation"
            else:
                assert candidate.mean is not None and candidate.variance is not None
                if policy == CONFIRM and threshold is not None and candidate.mean < threshold:
                    continue
                score = -math.sqrt(candidate.variance)
                criterion = "base_desirability_standard_deviation"
            if not math.isfinite(score):
                raise _error("bayesian_augmentation_score_invalid")
            comparisons.append((score, candidate.row_id, candidate, nearest, criterion))
        if not comparisons:
            code = (
                "bayesian_maxpro_projection_collision"
                if policy == MAXPRO and current_projection_collisions
                else "bayesian_augmentation_insufficient_candidates"
            )
            raise _error(code)
        score, _, chosen, nearest, criterion = min(comparisons, key=lambda entry: entry[:2])
        steps.append(
            {
                "rank": rank,
                "row_id": chosen.row_id,
                "criterion": criterion,
                "score": score if policy == MAXPRO else -score,
                "score_scale": "natural_log" if policy == MAXPRO else "original",
                "optimization_direction": "minimize" if policy == MAXPRO else "maximize",
                "nearest_existing_distance": chosen.nearest_existing,
                "nearest_selected_distance": nearest,
                "compared_candidate_count": len(comparisons),
                "competitive_threshold": threshold if policy == CONFIRM and rank > 1 else None,
            }
        )
        selected.append(chosen)
    budget.check()
    warnings = ["bayesian_augmentation_not_verified_jmp_parity"]
    if model_required:
        warnings.append("bayesian_augmentation_base_posterior_not_conditioned_by_selection")
    if policy == REFINE:
        warnings.append("bayesian_refine_multimodel_sd_not_implemented")
    if policy == REFINE_V2:
        warnings.append("bayesian_refine_weighted_rms_schedule_product_policy")
    if policy == MAXPRO and any(
        len({row[index] for row in reference}) != len(reference) for index in range(len(kinds))
    ):
        warnings.append("bayesian_maxpro_fixed_reference_projection_collisions")
    result: dict[str, Any] = {
        "schema_version": 1,
        "policy": policy,
        "source": identity,
        "selected_row_ids": [item.row_id for item in selected],
        "steps": steps,
        "distance_policy": "normalized_numeric_hamming_nominal_explicit_ordinal_rank_v1",
        "ordinal_rank_distance": ordinal_rank_distance,
        "tie_break": "row_id_ascending",
        "competitive_set_policy": "mean_at_least_observed_location_latent_incumbent"
        if policy == CONFIRM
        else None,
        "reference_count": len(reference),
        "raw_reference_count": len(existing_coordinates),
        "eligible_candidate_count": len(candidates),
        "projection_collisions": projection_collisions,
        "unscorable_candidates": [unscorable[key] for key in sorted(unscorable)],
        "evaluations": budget.evaluations,
        "max_evaluations": max_evaluations,
        "pair_comparisons": budget.pair_comparisons,
        "time_budget_ms": time_budget_ms,
        "model_refit": False,
        "fantasy_observations": False,
        "warnings": warnings,
    }
    if context is not None:
        result["response_uncertainty"] = {
            "policy": "importance_weighted_rms_normalized_latent_sd_v1",
            "variance_kind": "latent",
            "scale": "dimensionless",
            "context": context,
            "schedule": "first_ei_then_alternating_desirability_sd_response_sd",
        }
    return result
