import hashlib
import json
import random
from dataclasses import dataclass
from itertools import product
from math import isfinite
from typing import Any

GENERAL_FACTORIAL_DESIGN_SCHEMA_VERSION = 1
GENERAL_FACTORIAL_DESIGN_FAMILY = "general_full_factorial"
MIN_GENERAL_FACTORS = 2
MAX_GENERAL_FACTORS = 6
MAX_GENERAL_FACTOR_LEVELS = 10
MAX_GENERAL_FACTORIAL_RUNS = 256


class GeneralFactorialDesignError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class GeneralFactorialFactor:
    name: str
    levels: tuple[float | str, ...]
    unit: str | None = None


@dataclass(frozen=True)
class GeneralFactorialOptions:
    replicates: int
    randomize: bool
    randomization_seed: int
    max_interaction_order: int = 2


@dataclass(frozen=True)
class GeneralFactorialRun:
    standard_order: int
    run_order: int
    replicate_index: int
    factor_levels: dict[str, float | str]
    level_indices: dict[str, int]


@dataclass(frozen=True)
class GeneralFactorialDesign:
    schema_version: int
    family: str
    factors: tuple[GeneralFactorialFactor, ...]
    options: GeneralFactorialOptions
    runs: tuple[GeneralFactorialRun, ...]
    design_sha256: str


def generate_general_full_factorial_design(
    factors: list[GeneralFactorialFactor],
    options: GeneralFactorialOptions,
) -> GeneralFactorialDesign:
    _validate(factors, options)
    combinations = list(product(*(range(len(factor.levels)) for factor in factors)))
    rows: list[GeneralFactorialRun] = []
    for replicate_index in range(1, options.replicates + 1):
        for standard_order, indexes in enumerate(combinations, start=1):
            rows.append(
                GeneralFactorialRun(
                    standard_order=standard_order,
                    run_order=0,
                    replicate_index=replicate_index,
                    factor_levels={
                        factor.name: factor.levels[index]
                        for factor, index in zip(factors, indexes, strict=True)
                    },
                    level_indices={
                        factor.name: index for factor, index in zip(factors, indexes, strict=True)
                    },
                )
            )
    order = list(range(len(rows)))
    if options.randomize:
        random.Random(options.randomization_seed).shuffle(order)
    runs = tuple(
        GeneralFactorialRun(
            standard_order=row.standard_order,
            run_order=run_order,
            replicate_index=row.replicate_index,
            factor_levels=row.factor_levels,
            level_indices=row.level_indices,
        )
        for run_order, row in enumerate((rows[index] for index in order), start=1)
    )
    payload = canonical_general_factorial_payload(factors=factors, options=options, runs=runs)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return GeneralFactorialDesign(
        schema_version=GENERAL_FACTORIAL_DESIGN_SCHEMA_VERSION,
        family=GENERAL_FACTORIAL_DESIGN_FAMILY,
        factors=tuple(factors),
        options=options,
        runs=runs,
        design_sha256=hashlib.sha256(encoded).hexdigest(),
    )


def canonical_general_factorial_payload(
    *,
    factors: list[GeneralFactorialFactor] | tuple[GeneralFactorialFactor, ...],
    options: GeneralFactorialOptions,
    runs: tuple[GeneralFactorialRun, ...],
) -> dict[str, Any]:
    return {
        "schema_version": GENERAL_FACTORIAL_DESIGN_SCHEMA_VERSION,
        "family": GENERAL_FACTORIAL_DESIGN_FAMILY,
        "factors": [factor_to_payload(factor) for factor in factors],
        "options": options_to_payload(options),
        "runs": [run_to_payload(run) for run in sorted(runs, key=lambda item: item.run_order)],
    }


def factor_to_payload(factor: GeneralFactorialFactor) -> dict[str, Any]:
    return {"name": factor.name, "levels": list(factor.levels), "unit": factor.unit}


def options_to_payload(options: GeneralFactorialOptions) -> dict[str, Any]:
    return {
        "replicates": options.replicates,
        "randomize": options.randomize,
        "randomization_seed": options.randomization_seed,
        "max_interaction_order": options.max_interaction_order,
    }


def run_to_payload(run: GeneralFactorialRun) -> dict[str, Any]:
    return {
        "standard_order": run.standard_order,
        "run_order": run.run_order,
        "replicate_index": run.replicate_index,
        "factor_levels": run.factor_levels,
        "level_indices": run.level_indices,
    }


def _validate(factors: list[GeneralFactorialFactor], options: GeneralFactorialOptions) -> None:
    if not MIN_GENERAL_FACTORS <= len(factors) <= MAX_GENERAL_FACTORS:
        raise GeneralFactorialDesignError(
            "doe_general_factorial_factor_count_out_of_range",
            "General full-factorial designs support between 2 and 6 factors.",
        )
    names: set[str] = set()
    for factor in factors:
        name = factor.name.strip()
        if not name or name.casefold() in names:
            raise GeneralFactorialDesignError(
                "doe_general_factorial_factor_names_invalid",
                "Factor names must be non-empty and unique.",
            )
        names.add(name.casefold())
        if not 2 <= len(factor.levels) <= MAX_GENERAL_FACTOR_LEVELS:
            raise GeneralFactorialDesignError(
                "doe_general_factorial_levels_out_of_range",
                "Each factor must define between 2 and 10 levels.",
            )
        canonical_levels: set[tuple[str, str]] = set()
        for level in factor.levels:
            if isinstance(level, bool):
                canonical = ("text", str(level))
            elif isinstance(level, int | float):
                if not isfinite(float(level)):
                    raise GeneralFactorialDesignError(
                        "doe_general_factorial_level_invalid",
                        "Numeric levels must be finite.",
                    )
                canonical = ("number", format(float(level), ".17g"))
            else:
                value = str(level).strip()
                if not value or len(value) > 80:
                    raise GeneralFactorialDesignError(
                        "doe_general_factorial_level_invalid",
                        "Text levels must contain between 1 and 80 characters.",
                    )
                canonical = ("text", value.casefold())
            if canonical in canonical_levels:
                raise GeneralFactorialDesignError(
                    "doe_general_factorial_levels_not_unique",
                    "Levels must be unique within each factor.",
                )
            canonical_levels.add(canonical)
    if options.replicates < 1 or options.randomization_seed < 0:
        raise GeneralFactorialDesignError(
            "doe_general_factorial_options_invalid",
            "Replicates and the randomization seed are invalid.",
        )
    if not 1 <= options.max_interaction_order <= min(3, len(factors)):
        raise GeneralFactorialDesignError(
            "doe_general_factorial_interaction_order_invalid",
            "Interaction order must be between 1 and 3.",
        )
    run_count = options.replicates
    for factor in factors:
        run_count *= len(factor.levels)
    if run_count > MAX_GENERAL_FACTORIAL_RUNS:
        raise GeneralFactorialDesignError(
            "doe_general_factorial_run_count_exceeds_limit",
            f"General full-factorial designs are limited to {MAX_GENERAL_FACTORIAL_RUNS} runs.",
        )
