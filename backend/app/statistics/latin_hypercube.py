import hashlib
import json
from dataclasses import dataclass
from typing import Literal

import numpy as np
import scipy  # type: ignore[import-untyped]
from scipy.spatial.distance import pdist  # type: ignore[import-untyped]
from scipy.stats import qmc  # type: ignore[import-untyped]

from app.statistics.doe_factor_domain import (
    DoeFactorDomain,
    DoeFactorDomainError,
    factor_domain_payload,
    validate_factor_domain,
)

LATIN_HYPERCUBE_FAMILY = "latin_hypercube_space_filling"
LATIN_HYPERCUBE_POLICY = "scipy_latin_hypercube_random_cd_v1"
MIXED_LATIN_HYPERCUBE_POLICY = "mixed_lhs_balanced_discrete_v1"


class LatinHypercubeError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class LatinHypercubeFactor:
    name: str
    low: float
    high: float
    unit: str | None = None
    domain_kind: Literal["continuous", "discrete_numeric"] = "continuous"
    step: float | None = None
    display_decimals: int | None = None


@dataclass(frozen=True)
class LatinHypercubeOptions:
    run_count: int
    seed: int
    randomize_run_order: bool
    run_order_seed: int
    optimization: Literal["random_cd", "none"] = "random_cd"


@dataclass(frozen=True)
class LatinHypercubeQuality:
    centered_discrepancy: float
    minimum_pairwise_distance: float
    maximum_absolute_factor_correlation: float
    per_factor_strata_occupancy: tuple[tuple[int, ...], ...]
    strata_valid: bool
    continuous_strata_valid: bool | None = None
    discrete_level_balance: dict[str, tuple[int, ...]] | None = None
    duplicate_count: int = 0
    executable_point_count: int | None = None


@dataclass(frozen=True)
class LatinHypercubeRun:
    standard_order: int
    run_order: int
    factor_levels: dict[str, float]
    normalized_levels: dict[str, float]


@dataclass(frozen=True)
class LatinHypercubeDesign:
    factors: tuple[LatinHypercubeFactor, ...]
    options: LatinHypercubeOptions
    quality: LatinHypercubeQuality
    runs: tuple[LatinHypercubeRun, ...]
    design_sha256: str
    numpy_version: str
    scipy_version: str


def generate_latin_hypercube_design(
    factors: list[LatinHypercubeFactor],
    options: LatinHypercubeOptions,
) -> LatinHypercubeDesign:
    _validate(factors, options)
    mixed = any(factor.domain_kind == "discrete_numeric" for factor in factors)
    if mixed:
        unique_capacity = 1
        all_discrete = True
        for factor in factors:
            if factor.domain_kind == "discrete_numeric":
                unique_capacity *= (
                    DoeFactorDomain(
                        factor.low, factor.high, factor.domain_kind, factor.step
                    ).level_count
                    or 1
                )
            else:
                all_discrete = False
        if all_discrete and unique_capacity < options.run_count:
            raise LatinHypercubeError("lhs_executable_unique_design_impossible")

    normalized: np.ndarray | None = None
    actual: np.ndarray | None = None
    duplicate_count = 0
    attempt_limit = 32 if mixed else 1
    for attempt in range(attempt_limit):
        optimizer = "random-cd" if options.optimization == "random_cd" else None
        engine = qmc.LatinHypercube(
            d=len(factors),
            scramble=True,
            strength=1,
            optimization=optimizer,
            rng=np.random.default_rng(options.seed + attempt),
        )
        candidate_normalized = np.asarray(engine.random(options.run_count), dtype=float)
        lows = np.asarray([factor.low for factor in factors], dtype=float)
        highs = np.asarray([factor.high for factor in factors], dtype=float)
        candidate_actual = np.asarray(qmc.scale(candidate_normalized, lows, highs), dtype=float)
        if mixed:
            for factor_index, factor in enumerate(factors):
                if factor.domain_kind != "discrete_numeric":
                    continue
                domain = DoeFactorDomain(
                    factor.low,
                    factor.high,
                    factor.domain_kind,
                    factor.step,
                    factor.display_decimals,
                )
                levels = np.asarray(domain.levels(), dtype=float)
                order = np.argsort(candidate_normalized[:, factor_index], kind="stable")
                assignments = np.floor(
                    np.arange(options.run_count) * len(levels) / options.run_count
                ).astype(int)
                candidate_actual[order, factor_index] = levels[assignments]
                candidate_normalized[:, factor_index] = (
                    candidate_actual[:, factor_index] - factor.low
                ) / (factor.high - factor.low)
        if not np.isfinite(candidate_normalized).all() or not np.isfinite(candidate_actual).all():
            raise LatinHypercubeError("lhs_generation_non_finite")
        duplicate_count = options.run_count - len(
            {tuple(float(value) for value in row) for row in candidate_actual}
        )
        if duplicate_count == 0:
            normalized = candidate_normalized
            actual = candidate_actual
            break
    if normalized is None or actual is None:
        raise LatinHypercubeError("lhs_executable_unique_design_impossible")

    standard_order = np.arange(options.run_count)
    if options.randomize_run_order:
        execution_order = np.random.default_rng(options.run_order_seed).permutation(
            options.run_count
        )
    else:
        execution_order = standard_order
    run_order_by_standard = np.empty(options.run_count, dtype=int)
    for run_order, standard_index in enumerate(execution_order, start=1):
        run_order_by_standard[int(standard_index)] = run_order

    runs = tuple(
        LatinHypercubeRun(
            standard_order=index + 1,
            run_order=int(run_order_by_standard[index]),
            factor_levels={
                factor.name: float(actual[index, factor_index])
                for factor_index, factor in enumerate(factors)
            },
            normalized_levels={
                factor.name: float(normalized[index, factor_index])
                for factor_index, factor in enumerate(factors)
            },
        )
        for index in range(options.run_count)
    )
    quality = calculate_latin_hypercube_quality(normalized, factors=factors)
    payload = canonical_latin_hypercube_payload(
        factors=factors,
        options=options,
        quality=quality,
        runs=runs,
    )
    return LatinHypercubeDesign(
        factors=tuple(factors),
        options=options,
        quality=quality,
        runs=runs,
        design_sha256=hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
        numpy_version=np.__version__,
        scipy_version=scipy.__version__,
    )


def calculate_latin_hypercube_quality(
    points: np.ndarray,
    *,
    factors: list[LatinHypercubeFactor] | None = None,
) -> LatinHypercubeQuality:
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 1:
        raise LatinHypercubeError("lhs_quality_shape_invalid")
    run_count, factor_count = points.shape
    occupancy = tuple(
        tuple(
            sorted(
                int(value) for value in np.floor(points[:, factor_index] * run_count).astype(int)
            )
        )
        for factor_index in range(factor_count)
    )
    expected = tuple(range(run_count))
    strata_valid = all(item == expected for item in occupancy)
    continuous_indices = (
        list(range(factor_count))
        if factors is None
        else [index for index, factor in enumerate(factors) if factor.domain_kind == "continuous"]
    )
    continuous_strata_valid = all(occupancy[index] == expected for index in continuous_indices)
    discrete_balance: dict[str, tuple[int, ...]] = {}
    if factors is not None:
        for factor_index, factor in enumerate(factors):
            if factor.domain_kind != "discrete_numeric":
                continue
            levels = DoeFactorDomain(
                factor.low, factor.high, factor.domain_kind, factor.step
            ).levels()
            discrete_balance[factor.name] = tuple(
                int(
                    np.count_nonzero(
                        np.isclose(
                            points[:, factor_index],
                            (level - factor.low) / (factor.high - factor.low),
                            rtol=0.0,
                            atol=1e-12,
                        )
                    )
                )
                for level in levels
            )
    duplicate_count = run_count - len({tuple(float(value) for value in row) for row in points})
    distances = pdist(points, metric="euclidean")
    minimum_distance = float(np.min(distances))
    if factor_count == 1:
        maximum_correlation = 0.0
    else:
        correlations = np.corrcoef(points, rowvar=False)
        mask = ~np.eye(factor_count, dtype=bool)
        maximum_correlation = float(np.max(np.abs(correlations[mask])))
    return LatinHypercubeQuality(
        centered_discrepancy=float(qmc.discrepancy(points, method="CD")),
        minimum_pairwise_distance=minimum_distance,
        maximum_absolute_factor_correlation=maximum_correlation,
        per_factor_strata_occupancy=occupancy,
        strata_valid=strata_valid,
        continuous_strata_valid=continuous_strata_valid,
        discrete_level_balance=discrete_balance,
        duplicate_count=duplicate_count,
        executable_point_count=run_count - duplicate_count,
    )


def canonical_latin_hypercube_payload(
    *,
    factors: list[LatinHypercubeFactor] | tuple[LatinHypercubeFactor, ...],
    options: LatinHypercubeOptions,
    quality: LatinHypercubeQuality,
    runs: tuple[LatinHypercubeRun, ...],
) -> dict[str, object]:
    mixed = any(item.domain_kind == "discrete_numeric" for item in factors)
    return {
        "design_schema_version": 2 if mixed else 1,
        "method_id": "doe.latin_hypercube",
        "method_version": "0.2.0" if mixed else "0.1.0",
        "family": LATIN_HYPERCUBE_FAMILY,
        "factors": [_factor_payload(item) for item in factors],
        "options": {
            "policy": MIXED_LATIN_HYPERCUBE_POLICY if mixed else LATIN_HYPERCUBE_POLICY,
            "run_count": options.run_count,
            "seed": options.seed,
            "scramble": True,
            "strength": 1,
            "optimization": options.optimization,
            "randomize_run_order": options.randomize_run_order,
            "run_order_seed": options.run_order_seed,
        },
        "runs": [
            {
                "standard_order": item.standard_order,
                "run_order": item.run_order,
                "factor_levels": item.factor_levels,
                "normalized_levels": item.normalized_levels,
            }
            for item in runs
        ],
        "quality": {
            "centered_discrepancy": quality.centered_discrepancy,
            "minimum_pairwise_distance": quality.minimum_pairwise_distance,
            "maximum_absolute_factor_correlation": (quality.maximum_absolute_factor_correlation),
            "per_factor_strata_occupancy": quality.per_factor_strata_occupancy,
            "strata_valid": quality.strata_valid,
            **(
                {
                    "continuous_strata_valid": quality.continuous_strata_valid,
                    "discrete_level_balance": quality.discrete_level_balance,
                    "duplicate_count": quality.duplicate_count,
                    "executable_point_count": quality.executable_point_count,
                }
                if mixed
                else {}
            ),
        },
        "package_versions": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }


def _validate(
    factors: list[LatinHypercubeFactor],
    options: LatinHypercubeOptions,
) -> None:
    if not 1 <= len(factors) <= 6:
        raise LatinHypercubeError("lhs_factor_count_invalid")
    names = [factor.name for factor in factors]
    if len(set(names)) != len(names) or any(not name.strip() for name in names):
        raise LatinHypercubeError("lhs_factor_name_invalid")
    if any(
        not np.isfinite(factor.low) or not np.isfinite(factor.high) or factor.low >= factor.high
        for factor in factors
    ):
        raise LatinHypercubeError("lhs_factor_bounds_invalid")
    for factor in factors:
        try:
            validate_factor_domain(
                DoeFactorDomain(
                    factor.low,
                    factor.high,
                    factor.domain_kind,
                    factor.step,
                    factor.display_decimals,
                )
            )
        except DoeFactorDomainError as exc:
            raise LatinHypercubeError(exc.code) from exc
    if not 2 <= options.run_count <= 200:
        raise LatinHypercubeError("lhs_run_count_invalid")
    if options.seed < 0 or options.run_order_seed < 0:
        raise LatinHypercubeError("lhs_seed_invalid")
    if options.optimization not in {"random_cd", "none"}:
        raise LatinHypercubeError("lhs_optimization_invalid")


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _factor_payload(factor: LatinHypercubeFactor) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": factor.name,
        "low": factor.low,
        "high": factor.high,
        "unit": factor.unit,
    }
    if (
        factor.domain_kind != "continuous"
        or factor.step is not None
        or factor.display_decimals is not None
    ):
        payload.update(
            factor_domain_payload(
                DoeFactorDomain(
                    factor.low,
                    factor.high,
                    factor.domain_kind,
                    factor.step,
                    factor.display_decimals,
                )
            )
        )
    return payload
