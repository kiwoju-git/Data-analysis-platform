from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, cast

from app.api.v1.schemas.bayesian import MAX_COMPLETED_OBSERVATIONS
from app.core.doe_capabilities import BAYESIAN_STUDY_FACTOR_LIMIT
from app.statistics.doe_factor_domain import (
    DoeFactorDomain,
    DoeFactorDomainError,
    validate_factor_domain,
)

ObservationMode = Literal["retain_raw", "exact_replicates", "nearby_diagnostics"]


class BoObservationGroupsError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class BoObservationGroup:
    member_indices: tuple[int, ...]
    member_trial_ids: tuple[str, ...]
    canonical_actual_coordinates: tuple[float, ...]
    normalized_coordinates: tuple[float, ...]
    canonical_level_indices: tuple[int | None, ...]
    condition_key: str | None
    n: int
    mean: float
    within_ss: float
    sample_variance: float | None
    mean_scaled: float
    within_ss_scaled: float


@dataclass(frozen=True)
class BoNearbyGroup:
    member_indices: tuple[int, ...]
    member_trial_ids: tuple[str, ...]
    maximum_normalized_distance: float
    maximum_axis_distances: tuple[float, ...]
    response_range: tuple[float, float]
    response_sample_variance: float


@dataclass(frozen=True)
class BoObservationView:
    mode: ObservationMode
    factor_ids: tuple[str, ...]
    trial_ids: tuple[str, ...]
    raw_actual_coordinates: tuple[tuple[float, ...], ...]
    raw_x: Any
    raw_y: Any
    raw_y_scaled: Any
    normalization_mean: float
    normalization_scale: float
    constant_response: bool
    groups: tuple[BoObservationGroup, ...]
    nearby_groups: tuple[BoNearbyGroup, ...]
    nearby_units: Literal["actual", "normalized"]
    nearby_tolerances: tuple[float, ...] | None
    training_x: Any
    training_y_scaled: Any
    training_counts: Any
    training_within_ss_scaled: Any
    unique_coordinate_count: int

    @property
    def raw_observation_count(self) -> int:
        return len(self.trial_ids)

    @property
    def unique_condition_count(self) -> int:
        return len(self.groups)

    @property
    def effective_training_count(self) -> int:
        return len(self.training_counts)

    def provenance(self) -> dict[str, Any]:
        return {
            "policy_version": 1,
            "mode": self.mode,
            "raw_observation_count": self.raw_observation_count,
            "unique_condition_count": self.unique_condition_count,
            "unique_coordinate_count": self.unique_coordinate_count,
            "effective_training_count": self.effective_training_count,
            "normalization": {
                "source": "raw_observations",
                "mean": self.normalization_mean,
                "scale": self.normalization_scale,
                "ddof": 0,
                "constant_response_scale_fallback": self.constant_response,
            },
            "groups": [
                {
                    "member_trial_ids": list(group.member_trial_ids),
                    "member_indices": list(group.member_indices),
                    "canonical_actual_coordinates": dict(
                        zip(self.factor_ids, group.canonical_actual_coordinates, strict=True)
                    ),
                    "canonical_level_indices": dict(
                        zip(self.factor_ids, group.canonical_level_indices, strict=True)
                    ),
                    "condition_key": group.condition_key,
                    "n": group.n,
                    "mean": group.mean,
                    "within_ss": group.within_ss,
                    "sample_variance": group.sample_variance,
                }
                for group in self.groups
            ],
            "nearby_diagnostics": {
                "changes_training_data": False,
                "grouping_policy": "deterministic_complete_link_v1",
                "units": self.nearby_units,
                "tolerances": (
                    None
                    if self.nearby_tolerances is None
                    else dict(zip(self.factor_ids, self.nearby_tolerances, strict=True))
                ),
                "groups": [
                    {
                        "member_trial_ids": list(group.member_trial_ids),
                        "maximum_normalized_distance": group.maximum_normalized_distance,
                        "maximum_axis_distances": dict(
                            zip(self.factor_ids, group.maximum_axis_distances, strict=True)
                        ),
                        "response_range": list(group.response_range),
                        "response_sample_variance": group.response_sample_variance,
                    }
                    for group in self.nearby_groups
                ],
            },
        }


def prepare_bo_observation_view(
    observations: list[dict[str, Any]],
    factors: list[dict[str, Any]],
    *,
    mode: ObservationMode = "retain_raw",
    nearby_tolerances: dict[str, float] | None = None,
    nearby_units: Literal["actual", "normalized"] = "actual",
    minimum_unique_conditions: int | None = None,
) -> BoObservationView:
    """Prepare a read-only view of one validated study's response and unit.

    Continuous coordinate identity is exact; discrete identity uses the existing
    executable-level policy. Nearby diagnostics never change training observations.
    """
    import numpy as np

    if not isinstance(mode, str) or mode not in {
        "retain_raw",
        "exact_replicates",
        "nearby_diagnostics",
    }:
        raise BoObservationGroupsError("bayesian_observation_mode_invalid")
    if not isinstance(observations, list) or not observations:
        raise BoObservationGroupsError("bayesian_observations_invalid")
    if len(observations) > MAX_COMPLETED_OBSERVATIONS:
        raise BoObservationGroupsError("bayesian_observation_limit_reached")
    factor_ids, domains = _factor_domains(factors)
    tolerances = _nearby_options(mode, factor_ids, nearby_tolerances, nearby_units)
    minimum = max(2, len(factor_ids) + 1)
    if minimum_unique_conditions is not None:
        if (
            not isinstance(minimum_unique_conditions, int)
            or isinstance(minimum_unique_conditions, bool)
            or not minimum <= minimum_unique_conditions <= MAX_COMPLETED_OBSERVATIONS
        ):
            raise BoObservationGroupsError("bayesian_unique_condition_policy_invalid")
        minimum = minimum_unique_conditions

    ids: list[str] = []
    source_actual: list[tuple[float, ...]] = []
    canonical_actual: list[tuple[float, ...]] = []
    normalized_rows: list[tuple[float, ...]] = []
    level_rows: list[tuple[int | None, ...]] = []
    contexts: list[str | None] = []
    responses: list[float] = []
    grouped: dict[tuple[tuple[float | int, ...], str | None], list[int]] = {}
    for row_index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise BoObservationGroupsError("bayesian_observations_invalid")
        trial_id = observation.get("trial_id")
        context = observation.get("condition_key")
        if (
            not isinstance(trial_id, str)
            or not trial_id
            or trial_id in ids
            or (context is not None and (not isinstance(context, str) or not context))
        ):
            raise BoObservationGroupsError("bayesian_observation_identity_invalid")
        actual = observation.get("actual_coordinates")
        normalized = observation.get("normalized_coordinates")
        if (
            not isinstance(actual, dict)
            or not isinstance(normalized, dict)
            or set(actual) != set(factor_ids)
            or set(normalized) != set(factor_ids)
        ):
            raise BoObservationGroupsError("bayesian_observation_coordinates_invalid")
        source = tuple(_finite_number(actual[factor_id]) for factor_id in factor_ids)
        canonical: list[float] = []
        encoded: list[float] = []
        levels: list[int | None] = []
        identity: list[float | int] = []
        for factor_id, domain, value in zip(factor_ids, domains, source, strict=True):
            if not domain.is_executable(value):
                raise BoObservationGroupsError("bayesian_observation_coordinates_invalid")
            supplied = _finite_number(normalized[factor_id])
            expected = domain.normalized(value)
            if not 0 <= supplied <= 1 or not math.isclose(
                supplied, expected, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise BoObservationGroupsError("bayesian_observation_coordinates_invalid")
            level: int | None = None
            if domain.domain_kind == "discrete_numeric":
                low = Decimal(str(domain.low))
                step = Decimal(str(domain.step))
                level = int(((Decimal(str(value)) - low) / step).to_integral_value())
                value = float(low + step * level)
            canonical.append(value)
            encoded.append(domain.normalized(value))
            levels.append(level)
            identity.append(value if level is None else level)
        ids.append(trial_id)
        contexts.append(context)
        source_actual.append(source)
        canonical_actual.append(tuple(canonical))
        normalized_rows.append(tuple(encoded))
        level_rows.append(tuple(levels))
        responses.append(_finite_number(observation.get("objective_value")))
        grouped.setdefault((tuple(identity), context), []).append(row_index)

    unique_coordinates = len(set(canonical_actual))
    if unique_coordinates < minimum:
        raise BoObservationGroupsError("bayesian_unique_conditions_insufficient")
    raw_x = np.asarray(normalized_rows, dtype=float)
    raw_y = np.asarray(responses, dtype=float)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            mean = float(np.mean(raw_y))
            scale = float(np.std(raw_y, ddof=0))
            constant = scale <= max(1e-12, abs(mean) * 1e-12)
            if constant:
                scale = 1.0
            scaled = (raw_y - mean) / scale
            groups = tuple(
                _summarize_group(
                    indices,
                    ids,
                    canonical_actual,
                    normalized_rows,
                    level_rows,
                    contexts,
                    raw_y,
                    scaled,
                )
                for indices in grouped.values()
            )
            nearby = _nearby_groups(
                ids,
                canonical_actual,
                normalized_rows,
                level_rows,
                contexts,
                raw_y,
                tolerances,
                nearby_units,
            )
    except (ArithmeticError, ValueError) as exc:
        raise BoObservationGroupsError("bayesian_observation_statistics_nonfinite") from exc
    if mode == "exact_replicates":
        training_x = np.asarray([group.normalized_coordinates for group in groups], dtype=float)
        training_y = np.asarray([group.mean_scaled for group in groups], dtype=float)
        counts = np.asarray([group.n for group in groups], dtype=float)
        within_ss = np.asarray([group.within_ss_scaled for group in groups], dtype=float)
    else:
        training_x, training_y = raw_x.copy(), scaled.copy()
        counts = np.ones(len(raw_y), dtype=float)
        within_ss = np.zeros(len(raw_y), dtype=float)
    for array in (raw_x, raw_y, scaled, training_x, training_y, counts, within_ss):
        if not np.all(np.isfinite(array)):
            raise BoObservationGroupsError("bayesian_observation_statistics_nonfinite")
        array.setflags(write=False)
    return BoObservationView(
        mode,
        factor_ids,
        tuple(ids),
        tuple(source_actual),
        raw_x,
        raw_y,
        scaled,
        mean,
        scale,
        constant,
        groups,
        nearby,
        nearby_units,
        tolerances,
        training_x,
        training_y,
        counts,
        within_ss,
        unique_coordinates,
    )


def _summarize_group(
    indices: list[int],
    ids: list[str],
    actual: list[tuple[float, ...]],
    normalized: list[tuple[float, ...]],
    levels: list[tuple[int | None, ...]],
    contexts: list[str | None],
    raw_y: Any,
    scaled_y: Any,
) -> BoObservationGroup:
    import numpy as np

    values, scaled_values = raw_y[indices], scaled_y[indices]
    mean, scaled_mean = float(np.mean(values)), float(np.mean(scaled_values))
    within_ss = float(np.sum((values - mean) ** 2))
    scaled_ss = float(np.sum((scaled_values - scaled_mean) ** 2))
    if not all(math.isfinite(value) for value in (mean, scaled_mean, within_ss, scaled_ss)):
        raise BoObservationGroupsError("bayesian_observation_statistics_nonfinite")
    first, n = indices[0], len(indices)
    return BoObservationGroup(
        tuple(indices),
        tuple(ids[i] for i in indices),
        actual[first],
        normalized[first],
        levels[first],
        contexts[first],
        n,
        mean,
        within_ss,
        within_ss / (n - 1) if n > 1 else None,
        scaled_mean,
        scaled_ss,
    )


def _nearby_groups(
    ids: list[str],
    actual: list[tuple[float, ...]],
    normalized: list[tuple[float, ...]],
    levels: list[tuple[int | None, ...]],
    contexts: list[str | None],
    raw_y: Any,
    tolerances: tuple[float, ...] | None,
    units: str,
) -> tuple[BoNearbyGroup, ...]:
    import numpy as np

    if tolerances is None:
        return ()
    coordinates = actual if units == "actual" else normalized
    clusters: list[list[int]] = []
    ordered = sorted(
        range(len(ids)),
        key=lambda i: (actual[i], contexts[i] is not None, contexts[i] or "", ids[i]),
    )

    def compatible(left: int, right: int) -> bool:
        return (
            contexts[left] == contexts[right]
            and levels[left] == levels[right]
            and all(
                abs(a - b) <= tolerance
                for a, b, tolerance in zip(
                    coordinates[left], coordinates[right], tolerances, strict=True
                )
            )
        )

    # Every new member must be close to every member, not only the nearest neighbor.
    for index in ordered:
        for cluster in clusters:
            if all(compatible(index, member) for member in cluster):
                cluster.append(index)
                break
        else:
            clusters.append([index])
    result: list[BoNearbyGroup] = []
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        distances = [
            math.dist(normalized[left], normalized[right])
            for position, left in enumerate(cluster)
            for right in cluster[position + 1 :]
        ]
        axis_distances = tuple(
            max(coordinates[i][axis] for i in cluster) - min(coordinates[i][axis] for i in cluster)
            for axis in range(len(tolerances))
        )
        values = raw_y[cluster]
        result.append(
            BoNearbyGroup(
                tuple(cluster),
                tuple(ids[i] for i in cluster),
                max(distances),
                axis_distances,
                (float(np.min(values)), float(np.max(values))),
                float(np.var(values, ddof=1)),
            )
        )
    return tuple(result)


def _factor_domains(
    factors: list[dict[str, Any]],
) -> tuple[tuple[str, ...], tuple[DoeFactorDomain, ...]]:
    if not isinstance(factors, list) or not 1 <= len(factors) <= BAYESIAN_STUDY_FACTOR_LIMIT:
        raise BoObservationGroupsError("bayesian_observation_factors_invalid")
    ids: list[str] = []
    domains: list[DoeFactorDomain] = []
    for factor in factors:
        if not isinstance(factor, dict):
            raise BoObservationGroupsError("bayesian_observation_factors_invalid")
        factor_id = factor.get("factor_id")
        if not isinstance(factor_id, str) or not factor_id or factor_id in ids:
            raise BoObservationGroupsError("bayesian_observation_factors_invalid")
        kind = factor.get("domain_kind", "continuous")
        if not isinstance(kind, str) or kind not in {"continuous", "discrete_numeric"}:
            raise BoObservationGroupsError("bayesian_observation_factors_invalid")
        step = factor.get("step")
        domain = DoeFactorDomain(
            low=_finite_number(factor.get("low")),
            high=_finite_number(factor.get("high")),
            domain_kind=cast(Literal["continuous", "discrete_numeric"], kind),
            step=None if step is None else _finite_number(step),
        )
        try:
            validate_factor_domain(domain)
        except DoeFactorDomainError as exc:
            raise BoObservationGroupsError("bayesian_observation_factors_invalid") from exc
        if not math.isfinite(domain.high - domain.low):
            raise BoObservationGroupsError("bayesian_observation_factors_invalid")
        ids.append(factor_id)
        domains.append(domain)
    return tuple(ids), tuple(domains)


def _nearby_options(
    mode: ObservationMode,
    factor_ids: tuple[str, ...],
    tolerances: dict[str, float] | None,
    units: str,
) -> tuple[float, ...] | None:
    if not isinstance(units, str) or units not in {"actual", "normalized"}:
        raise BoObservationGroupsError("bayesian_nearby_options_invalid")
    if mode != "nearby_diagnostics":
        if tolerances is not None:
            raise BoObservationGroupsError("bayesian_nearby_options_invalid")
        return None
    if not isinstance(tolerances, dict) or set(tolerances) != set(factor_ids):
        raise BoObservationGroupsError("bayesian_nearby_options_invalid")
    try:
        values = tuple(_finite_number(tolerances[key]) for key in factor_ids)
    except BoObservationGroupsError as exc:
        raise BoObservationGroupsError("bayesian_nearby_options_invalid") from exc
    if any(value < 0 for value in values):
        raise BoObservationGroupsError("bayesian_nearby_options_invalid")
    return values


def _finite_number(value: object) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise BoObservationGroupsError("bayesian_observation_value_invalid")
    try:
        numeric = float(value)
    except OverflowError as exc:
        raise BoObservationGroupsError("bayesian_observation_value_invalid") from exc
    if not math.isfinite(numeric):
        raise BoObservationGroupsError("bayesian_observation_value_invalid")
    return numeric
