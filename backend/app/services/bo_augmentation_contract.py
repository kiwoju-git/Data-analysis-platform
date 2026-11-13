"""Bound an augmentation receipt to its inputs without refitting or reranking."""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

from app.api.v1.schemas.bo_augmentation import AugmentationCalculation
from app.api.v1.schemas.bo_planning import CandidateRow
from app.services.bo_acquisition_receipts import (
    _ValidationBoundary,
    validate_legacy_acquisition_receipt,
)
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_augmentation import CONFIRM, MAXPRO, MIXED_MAXIMIN, REFINE, REFINE_V2
from app.statistics.bo_beta_policy import stored_beta_expected_improvement


def _require(condition: bool) -> None:
    if not condition:
        raise BayesianOptimizationError("bayesian_augmentation_result_invalid")


def _finite(value: Any, *, low: float = 0, high: float = math.inf) -> float:
    _require(type(value) in {int, float})
    result = float(value)
    _require(math.isfinite(result) and low <= result <= high)
    return result


def _same(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    a, b = _finite(left, low=-math.inf), _finite(right, low=-math.inf)
    if a == b:
        return True
    # Regenerated elementary operations may differ by a few ULP across targets.
    # A nonzero value must not be accepted as a rounded zero.
    return a != 0 and b != 0 and abs(a - b) <= 16 * max(math.ulp(a), math.ulp(b))


def _context(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    definitions = snapshot["calculation_request"]["objective"]["responses"]
    models = snapshot["response_models"]
    _require(type(definitions) is list and 1 <= len(definitions) <= 4)
    _require(type(models) is list and len(models) == len(definitions))
    keys = [item["response_id"] for item in definitions]
    model_keys = [item["response_id"] for item in models]
    _require(len(set(keys)) == len(keys) and set(keys) == set(model_keys))
    importance = [_finite(item["importance"]) for item in definitions]
    _require(all(value > 0 for value in importance))
    scaled = [value / max(importance) for value in importance]
    weights = [value / math.fsum(scaled) for value in scaled]
    _require(all(value > 0 for value in weights))
    scales = {
        item["response_id"]: _finite(item["model"]["normalization"]["scale"]) for item in models
    }
    _require(all(value > 0 for value in scales.values()))
    return sorted(
        [
            {
                "response_id": key,
                "normalization_scale": scales[key],
                "normalized_importance": weight,
            }
            for key, weight in zip(keys, weights, strict=True)
        ],
        key=lambda item: item["response_id"],
    )


def _point(value: dict[str, Any], factor_ids: list[str]) -> tuple[float, ...]:
    _require(type(value) is dict and set(value) == set(factor_ids))
    return tuple(_finite(value[key], high=1) for key in factor_ids)


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.hypot(*(a - b for a, b in zip(left, right, strict=True)))


def _projection_score(point: tuple[float, ...], references: list[tuple[float, ...]]) -> float:
    values = []
    for reference in references:
        differences = [abs(a - b) for a, b in zip(point, reference, strict=True)]
        _require(all(value > 0 for value in differences))
        values.append(-2 * math.fsum(math.log(value) for value in differences))
    peak = max(values)
    return peak + math.log(math.fsum(math.exp(value - peak) for value in values))


def _response_rms(row: dict[str, Any], context: list[dict[str, Any]]) -> float:
    predictions = {item["response_id"]: item for item in row["response_predictions"]}
    terms = []
    for item in context:
        sd = predictions[item["response_id"]]["latent_standard_deviation_raw"]
        term = math.sqrt(item["normalized_importance"]) * (sd / item["normalization_scale"])
        _require(math.isfinite(term) and (sd == 0 or term > 0))
        terms.append(term)
    return _finite(math.hypot(*terms))


def _model_row(
    row: dict[str, Any],
    snapshot: dict[str, Any],
    policy: str,
    *,
    boundary: _ValidationBoundary = _ValidationBoundary.CALCULATION,
) -> None:
    predictions = row["response_predictions"]
    models = {item["response_id"]: item["model"] for item in snapshot["response_models"]}
    keys = [item["response_id"] for item in predictions]
    _require(len(keys) == len(models) and len(set(keys)) == len(keys) and set(keys) == set(models))
    for item in predictions:
        noise_sd = _finite(models[item["response_id"]]["observation_noise_sd_raw"])
        _require(
            _same(
                item["predictive_standard_deviation_raw"],
                math.hypot(item["latent_standard_deviation_raw"], noise_sd),
            )
        )
    if policy == CONFIRM:
        _require(row["acquisition"] is None)
        return
    acquisition = row["acquisition"]
    _require(isinstance(acquisition, dict))
    xi = _finite(snapshot["calculation_request"]["xi_desirability"])
    moments = row["desirability_moments"]
    if boundary is _ValidationBoundary.STORED_RECEIPT and "numerical_policy" not in acquisition:
        validate_legacy_acquisition_receipt(
            acquisition,
            moments["mean"],
            moments["variance"],
            snapshot["incumbent"]["latent_incumbent_value"],
            xi=xi,
        )
        return
    expected = asdict(
        stored_beta_expected_improvement(
            moments["mean"],
            moments["variance"],
            snapshot["incumbent"]["latent_incumbent_value"],
            xi=xi,
            numerical_policy=acquisition.get("numerical_policy"),
        )
    )
    _require(acquisition["xi_desirability"] == xi)
    for key, value in expected.items():
        if isinstance(value, str):
            _require(acquisition[key] == value)
        else:
            _require(_same(acquisition[key], value))


def _validate(
    result: dict[str, Any],
    *,
    request: dict[str, Any],
    snapshot: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    existing_coordinates: list[list[float]],
    mixed_domains: Any = None,
    boundary: _ValidationBoundary = _ValidationBoundary.CALCULATION,
) -> None:
    if mixed_domains is None:
        if result.get("schema_version") == 2:
            result = {key: value for key, value in result.items() if key != "auto_evidence"}
            result["schema_version"] = 1
        checked: Any = AugmentationCalculation.model_validate(result)
        candidate_type: Any = CandidateRow
        coordinate_key = "normalized_coordinates"
    else:
        from app.api.v1.schemas.bo_mixed_planning import MixedCandidateRow
        from app.api.v1.schemas.bo_mixed_workflow import MixedAugmentationCalculation

        checked = MixedAugmentationCalculation.model_validate(result)
        candidate_type = MixedCandidateRow
        coordinate_key = "encoded_coordinates"
    data = checked.model_dump(mode="json", exclude_unset=True)
    trace = data["augmentation"]
    policy = request["policy"]
    model_required = policy in {REFINE, REFINE_V2, CONFIRM}
    _require(policy in {MAXPRO, MIXED_MAXIMIN, REFINE, REFINE_V2, CONFIRM})
    _require(model_required == (snapshot is not None))
    _require(model_required == (trace["source"]["model_snapshot_id"] is not None))
    _require(model_required == (trace["source"]["model_snapshot_sha256"] is not None))
    if "source" in request:
        _require(trace["source"] == request["source"])
    _require(trace["policy"] == policy)
    _require(
        type(request["batch_size"]) is int and len(data["selected_rows"]) == request["batch_size"]
    )
    for key in ("time_budget_ms", "max_moment_evaluations"):
        _require(type(request[key]) is int and data[key] == request[key])
    for key in ("time_budget_ms", "max_evaluations"):
        _require(type(request[key]) is int and trace[key] == request[key])
    factors = request["factors"]
    _require(type(factors) is list and 1 <= len(factors) <= 10)
    factor_ids = [factor["factor_id"] for factor in factors]
    _require(len(set(factor_ids)) == len(factor_ids))
    _require(all(isinstance(key, str) and key for key in factor_ids))
    # Category distance needs its own versioned coordinate adapter, not numeric codes.
    if mixed_domains is None:
        _require(
            all(
                factor.get("domain_kind", "continuous") in {"continuous", "discrete_numeric"}
                for factor in factors
            )
        )
    else:
        _require(factor_ids == [domain.factor_id for domain in mixed_domains])
    if policy == MAXPRO:
        _require(all(factor.get("domain_kind", "continuous") == "continuous" for factor in factors))
    tolerance = _finite(request["duplicate_tolerance"], low=1e-12, high=0.1)
    minimum = _finite(
        request["min_batch_distance_normalized" if mixed_domains is None else "min_batch_distance"],
        high=math.sqrt(len(factors)) if mixed_domains is None else math.inf,
    )
    _require(type(existing_coordinates) is list and 1 <= len(existing_coordinates) <= 400)
    references = []
    for values in existing_coordinates:
        _require(type(values) is list and len(values) == len(factor_ids))
        if mixed_domains is None:
            references.append(tuple(_finite(value, high=1) for value in values))
        else:
            for domain, value in zip(mixed_domains, values, strict=True):
                domain.decode(value)
            references.append(tuple(values))
    references = list(dict.fromkeys(references))
    _require(trace["raw_reference_count"] == len(existing_coordinates))
    _require(trace["reference_count"] == len(references))
    ordinal = False if mixed_domains is None else request["ordinal_rank_distance"]
    _require(type(ordinal) is bool and trace["ordinal_rank_distance"] == ordinal)

    def distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if mixed_domains is None:
            return _distance(left, right)
        from app.statistics.bo_mixed_candidate_points import mixed_point_distance

        return mixed_point_distance(left, right, mixed_domains, ordinal_rank_distance=ordinal)

    _require(type(rows) is list and 1 <= len(rows) <= 10000)
    originals = {}
    for row in rows:
        candidate = candidate_type.model_validate(
            {key: row[key] for key in candidate_type.model_fields}
        )
        _require(candidate.row_id not in originals)
        originals[candidate.row_id] = candidate.model_dump(mode="json")
    _require(data["source_row_count"] == len(rows))
    _require(data["prediction_evaluations"] == (len(rows) if model_required else 0))
    count = trace["eligible_candidate_count"]
    # The selector independently rechecks novelty; an ULP-boundary row may be
    # excluded there. Do not repeat every candidate/reference distance on read.
    _require(request["batch_size"] <= count <= sum(row["eligible"] for row in originals.values()))
    q = request["batch_size"]
    _require(trace["evaluations"] == q * count - q * (q - 1) // 2)
    minimum_pairs = count * len(references) + sum((count - rank) * rank for rank in range(q))
    _require(trace["pair_comparisons"] >= minimum_pairs)
    if policy != MAXPRO:
        _require(trace["projection_collisions"] == 0 and trace["unscorable_candidates"] == [])
    else:
        unscorable_ids = [item["row_id"] for item in trace["unscorable_candidates"]]
        _require(unscorable_ids == sorted(set(unscorable_ids)))
        _require(set(unscorable_ids).issubset(originals))
        _require(not set(unscorable_ids).intersection(trace["selected_row_ids"]))
        _require(trace["projection_collisions"] >= len(unscorable_ids))
        _require(all(item["first_rank"] <= q for item in trace["unscorable_candidates"]))
    for index, step in enumerate(trace["steps"]):
        _require(step["compared_candidate_count"] <= count - index)
    context = None
    if snapshot is not None:
        _require(snapshot["calculation_request"]["factors"] == factors)
        _require(snapshot["calculation_request"]["search"]["duplicate_tolerance"] == tolerance)
        context = _context(snapshot)
        if policy == REFINE_V2:
            _require(trace["response_uncertainty"]["context"] == context)
    threshold = None
    if policy == CONFIRM and snapshot is not None:
        threshold = _finite(snapshot["incumbent"]["latent_incumbent_value"], high=1)
    _require(
        trace["competitive_set_policy"]
        == ("mean_at_least_observed_location_latent_incumbent" if policy == CONFIRM else None)
    )
    selected: list[tuple[float, ...]] = []
    for row, step in zip(data["selected_rows"], trace["steps"], strict=True):
        original = originals.get(row["row_id"])
        if original is None:
            raise BayesianOptimizationError("bayesian_augmentation_result_invalid")
        _require(all(row[key] == value for key, value in original.items()))
        if mixed_domains is None:
            point = _point(row[coordinate_key], factor_ids)
        else:
            _require(set(row[coordinate_key]) == set(factor_ids))
            point = tuple(row[coordinate_key][key] for key in factor_ids)
            for domain, value in zip(mixed_domains, point, strict=True):
                domain.decode(value)
        nearest = min(distance(point, old) for old in references)
        selected_distance = min((distance(point, old) for old in selected), default=None)
        _require(nearest > tolerance and _same(step["nearest_existing_distance"], nearest))
        _require(_same(row["nearest_existing_distance"], nearest))
        _require(_same(step["nearest_selected_distance"], selected_distance))
        _require(
            selected_distance is None
            or (selected_distance > tolerance and selected_distance >= minimum)
        )
        if snapshot is not None:
            _model_row(row, snapshot, policy, boundary=boundary)
        rank = step["rank"]
        expected_threshold = threshold if policy == CONFIRM and rank > 1 else None
        _require(step["competitive_threshold"] == expected_threshold)
        if policy == MAXPRO:
            score = _projection_score(point, [*references, *selected])
            criterion = "log_incremental_inverse_projection_distance"
        elif policy == MIXED_MAXIMIN:
            score = min(nearest, selected_distance if selected_distance is not None else math.inf)
            criterion = "minimum_explicit_mixed_distance"
        elif policy in {REFINE, REFINE_V2} and rank == 1:
            score, criterion = row["acquisition"]["value"], "base_desirability_beta_ei"
        elif policy == CONFIRM and rank == 1:
            score, criterion = row["desirability_moments"]["mean"], "base_expected_desirability"
        elif policy == REFINE_V2 and rank % 2 == 1:
            if context is None:
                raise BayesianOptimizationError("bayesian_augmentation_result_invalid")
            score = _response_rms(row, context)
            criterion = "base_response_normalized_latent_standard_deviation"
        else:
            if policy == CONFIRM:
                if threshold is None:
                    raise BayesianOptimizationError("bayesian_augmentation_result_invalid")
                _require(row["desirability_moments"]["mean"] >= threshold)
            score = math.sqrt(row["desirability_moments"]["variance"])
            criterion = "base_desirability_standard_deviation"
        _require(step["criterion"] == criterion and _same(step["score"], score))
        _require(step["score_scale"] == ("natural_log" if policy == MAXPRO else "original"))
        _require(step["optimization_direction"] == ("minimize" if policy == MAXPRO else "maximize"))
        selected.append(point)
    warnings = ["bayesian_augmentation_not_verified_jmp_parity"]
    if model_required:
        warnings.append("bayesian_augmentation_base_posterior_not_conditioned_by_selection")
    if policy == REFINE:
        warnings.append("bayesian_refine_multimodel_sd_not_implemented")
    if policy == REFINE_V2:
        warnings.append("bayesian_refine_weighted_rms_schedule_product_policy")
    if policy == MAXPRO and any(
        len({point[i] for point in references}) != len(references) for i in range(len(factors))
    ):
        warnings.append("bayesian_maxpro_fixed_reference_projection_collisions")
    _require(trace["warnings"] == warnings)


def validate_augmentation_binding(
    result: dict[str, Any],
    *,
    request: dict[str, Any],
    snapshot: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    existing_coordinates: list[list[float]],
) -> None:
    """Verify bounded input/score links; no posterior or global ranking claim.

    ``request.factors`` is internal context in immutable study order. The caller
    still owns owner/hash/CAS checks; candidate points and GP moments are not
    re-generated. At most eight selected rows are numerically checked against at
    most 400 reference points, with one cheap Beta evaluation per selected row.
    """
    try:
        _validate(
            result,
            request=request,
            snapshot=snapshot,
            rows=rows,
            existing_coordinates=existing_coordinates,
        )
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        raise BayesianOptimizationError("bayesian_augmentation_result_invalid") from None


def validate_stored_augmentation_binding(
    result: dict[str, Any],
    *,
    request: dict[str, Any],
    snapshot: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    existing_coordinates: list[list[float]],
) -> None:
    """Read a hash/source-verified receipt; do not replay absent-policy Beta EI."""
    try:
        _validate(
            result,
            request=request,
            snapshot=snapshot,
            rows=rows,
            existing_coordinates=existing_coordinates,
            boundary=_ValidationBoundary.STORED_RECEIPT,
        )
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        raise BayesianOptimizationError("bayesian_augmentation_result_invalid") from None


def validate_mixed_augmentation_binding(
    result: dict[str, Any],
    *,
    request: dict[str, Any],
    snapshot: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    existing_coordinates: list[list[float]],
    domains: Any,
) -> None:
    """Explicit mixed encoding adapter; equality codes never become numeric distances."""
    try:
        _validate(
            result,
            request=request,
            snapshot=snapshot,
            rows=rows,
            existing_coordinates=existing_coordinates,
            mixed_domains=domains,
        )
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        raise BayesianOptimizationError("bayesian_augmentation_result_invalid") from None
