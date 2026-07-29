import hashlib
import json
from dataclasses import dataclass
from typing import Literal

import numpy as np
import scipy  # type: ignore[import-untyped]
from scipy.spatial.distance import pdist  # type: ignore[import-untyped]
from scipy.stats import qmc  # type: ignore[import-untyped]

LATIN_HYPERCUBE_FAMILY = "latin_hypercube_space_filling"
LATIN_HYPERCUBE_POLICY = "scipy_latin_hypercube_random_cd_v1"


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
    optimizer = "random-cd" if options.optimization == "random_cd" else None
    engine = qmc.LatinHypercube(
        d=len(factors),
        scramble=True,
        strength=1,
        optimization=optimizer,
        rng=np.random.default_rng(options.seed),
    )
    normalized = np.asarray(engine.random(options.run_count), dtype=float)
    lows = np.asarray([factor.low for factor in factors], dtype=float)
    highs = np.asarray([factor.high for factor in factors], dtype=float)
    actual = np.asarray(qmc.scale(normalized, lows, highs), dtype=float)
    if not np.isfinite(normalized).all() or not np.isfinite(actual).all():
        raise LatinHypercubeError("lhs_generation_non_finite")

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
    quality = calculate_latin_hypercube_quality(normalized)
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


def calculate_latin_hypercube_quality(points: np.ndarray) -> LatinHypercubeQuality:
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
    )


def canonical_latin_hypercube_payload(
    *,
    factors: list[LatinHypercubeFactor] | tuple[LatinHypercubeFactor, ...],
    options: LatinHypercubeOptions,
    quality: LatinHypercubeQuality,
    runs: tuple[LatinHypercubeRun, ...],
) -> dict[str, object]:
    return {
        "design_schema_version": 1,
        "method_id": "doe.latin_hypercube",
        "method_version": "0.1.0",
        "family": LATIN_HYPERCUBE_FAMILY,
        "factors": [
            {"name": item.name, "low": item.low, "high": item.high, "unit": item.unit}
            for item in factors
        ],
        "options": {
            "policy": LATIN_HYPERCUBE_POLICY,
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
