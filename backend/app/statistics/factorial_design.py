import hashlib
import json
import random
from dataclasses import dataclass
from math import isfinite
from typing import Any

FACTORIAL_DESIGN_SCHEMA_VERSION = 1
FACTORIAL_DESIGN_FAMILY = "two_level_full_factorial"
MAX_FACTORIAL_FACTORS = 6
MIN_FACTORIAL_FACTORS = 2
MAX_FACTORIAL_RUNS = 256


class FactorialDesignError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class FactorialFactor:
    name: str
    low: float
    high: float
    unit: str | None = None


@dataclass(frozen=True)
class FactorialDesignOptions:
    replicates: int
    center_points: int
    randomize: bool
    randomization_seed: int
    block_count: int = 1


@dataclass(frozen=True)
class FactorialDesignRun:
    standard_order: int
    run_order: int
    replicate_index: int
    center_point: bool
    block_index: int | None
    factor_levels: dict[str, float]
    coded_levels: dict[str, int]


@dataclass(frozen=True)
class FactorialDesign:
    schema_version: int
    family: str
    factors: tuple[FactorialFactor, ...]
    options: FactorialDesignOptions
    runs: tuple[FactorialDesignRun, ...]
    design_sha256: str


def generate_two_level_full_factorial_design(
    factors: list[FactorialFactor],
    options: FactorialDesignOptions,
) -> FactorialDesign:
    _validate_factors(factors)
    _validate_options(options)
    base_run_count = 2 ** len(factors)
    run_count = base_run_count * options.replicates + options.center_points
    if run_count > MAX_FACTORIAL_RUNS:
        raise FactorialDesignError(
            code="doe_factorial_run_count_exceeds_limit",
            message="생성할 DOE run 수가 현재 제한을 초과합니다.",
        )
    if options.block_count > run_count:
        raise FactorialDesignError(
            code="doe_factorial_block_count_exceeds_run_count",
            message="블록 수는 전체 run 수보다 클 수 없습니다.",
        )

    rows: list[FactorialDesignRun] = []
    for replicate_index in range(1, options.replicates + 1):
        for standard_order in range(1, base_run_count + 1):
            rows.append(
                FactorialDesignRun(
                    standard_order=standard_order,
                    run_order=0,
                    replicate_index=replicate_index,
                    center_point=False,
                    block_index=None,
                    factor_levels=_factor_levels_for_standard_order(factors, standard_order),
                    coded_levels=_coded_levels_for_standard_order(factors, standard_order),
                ),
            )

    for center_index in range(1, options.center_points + 1):
        rows.append(
            FactorialDesignRun(
                standard_order=base_run_count + center_index,
                run_order=0,
                replicate_index=center_index,
                center_point=True,
                block_index=None,
                factor_levels={factor.name: (factor.low + factor.high) / 2 for factor in factors},
                coded_levels={factor.name: 0 for factor in factors},
            ),
        )

    order = list(range(len(rows)))
    if options.randomize:
        random.Random(options.randomization_seed).shuffle(order)

    ordered_rows = [rows[index] for index in order]
    runs = tuple(
        FactorialDesignRun(
            standard_order=row.standard_order,
            run_order=run_order,
            replicate_index=row.replicate_index,
            center_point=row.center_point,
            block_index=_block_index(run_order, options.block_count),
            factor_levels=row.factor_levels,
            coded_levels=row.coded_levels,
        )
        for run_order, row in enumerate(ordered_rows, start=1)
    )
    payload = canonical_factorial_design_payload(
        family=FACTORIAL_DESIGN_FAMILY,
        factors=factors,
        options=options,
        runs=runs,
    )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8",
    )
    return FactorialDesign(
        schema_version=FACTORIAL_DESIGN_SCHEMA_VERSION,
        family=FACTORIAL_DESIGN_FAMILY,
        factors=tuple(factors),
        options=options,
        runs=runs,
        design_sha256=hashlib.sha256(encoded).hexdigest(),
    )


def canonical_factorial_design_payload(
    *,
    family: str,
    factors: list[FactorialFactor] | tuple[FactorialFactor, ...],
    options: FactorialDesignOptions,
    runs: tuple[FactorialDesignRun, ...],
) -> dict[str, Any]:
    return {
        "schema_version": FACTORIAL_DESIGN_SCHEMA_VERSION,
        "family": family,
        "factors": [factor_to_payload(factor) for factor in factors],
        "options": options_to_payload(options),
        "runs": [run_to_payload(run) for run in sorted(runs, key=lambda run: run.run_order)],
    }


def factor_to_payload(factor: FactorialFactor) -> dict[str, Any]:
    return {
        "name": factor.name,
        "low": factor.low,
        "high": factor.high,
        "unit": factor.unit,
    }


def options_to_payload(options: FactorialDesignOptions) -> dict[str, Any]:
    return {
        "replicates": options.replicates,
        "center_points": options.center_points,
        "randomize": options.randomize,
        "randomization_seed": options.randomization_seed,
        "block_count": options.block_count,
    }


def run_to_payload(run: FactorialDesignRun) -> dict[str, Any]:
    return {
        "standard_order": run.standard_order,
        "run_order": run.run_order,
        "replicate_index": run.replicate_index,
        "center_point": run.center_point,
        "block_index": run.block_index,
        "factor_levels": run.factor_levels,
        "coded_levels": run.coded_levels,
    }


def _validate_factors(factors: list[FactorialFactor]) -> None:
    if not MIN_FACTORIAL_FACTORS <= len(factors) <= MAX_FACTORIAL_FACTORS:
        raise FactorialDesignError(
            code="doe_factorial_factor_count_out_of_range",
            message="2-level factorial 설계는 현재 2개 이상 6개 이하의 요인을 지원합니다.",
        )

    seen: set[str] = set()
    for factor in factors:
        name = factor.name.strip()
        if not name:
            raise FactorialDesignError(
                code="doe_factorial_factor_name_required",
                message="DOE 요인 이름은 비어 있을 수 없습니다.",
            )
        normalized = name.casefold()
        if normalized in seen:
            raise FactorialDesignError(
                code="doe_factorial_factor_names_not_unique",
                message="DOE 요인 이름은 중복될 수 없습니다.",
            )
        seen.add(normalized)
        if not isfinite(factor.low) or not isfinite(factor.high) or factor.low >= factor.high:
            raise FactorialDesignError(
                code="doe_factorial_factor_range_invalid",
                message="DOE 요인의 low/high 수준은 유한한 숫자이며 low < high 여야 합니다.",
            )


def _validate_options(options: FactorialDesignOptions) -> None:
    if options.replicates < 1:
        raise FactorialDesignError(
            code="doe_factorial_replicates_invalid",
            message="반복 수는 1 이상이어야 합니다.",
        )
    if options.center_points < 0:
        raise FactorialDesignError(
            code="doe_factorial_center_points_invalid",
            message="센터점 수는 0 이상이어야 합니다.",
        )
    if options.block_count < 1:
        raise FactorialDesignError(
            code="doe_factorial_block_count_invalid",
            message="블록 수는 1 이상이어야 합니다.",
        )
    if options.randomization_seed < 0:
        raise FactorialDesignError(
            code="doe_factorial_seed_invalid",
            message="랜덤 seed는 0 이상의 정수여야 합니다.",
        )


def _factor_levels_for_standard_order(
    factors: list[FactorialFactor],
    standard_order: int,
) -> dict[str, float]:
    coded_levels = _coded_levels_for_standard_order(factors, standard_order)
    return {
        factor.name: factor.low if coded_levels[factor.name] == -1 else factor.high
        for factor in factors
    }


def _coded_levels_for_standard_order(
    factors: list[FactorialFactor],
    standard_order: int,
) -> dict[str, int]:
    offset = standard_order - 1
    return {
        factor.name: 1 if (offset >> factor_index) & 1 else -1
        for factor_index, factor in enumerate(factors)
    }


def _block_index(run_order: int, block_count: int) -> int | None:
    if block_count <= 1:
        return None
    return ((run_order - 1) % block_count) + 1
