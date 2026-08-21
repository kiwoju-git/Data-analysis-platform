import hashlib
import json
import random
from dataclasses import dataclass
from itertools import product
from math import isfinite
from typing import Any

from app.statistics.doe_factor_domain import (
    DoeFactorDomain,
    DoeFactorDomainError,
    factor_domain_payload,
    validate_factor_domain,
)

FACTORIAL_DESIGN_SCHEMA_VERSION = 2
FRACTIONAL_FACTORIAL_DESIGN_SCHEMA_VERSION = 2
FACTORIAL_DESIGN_FAMILY = "two_level_full_factorial"
FRACTIONAL_FACTORIAL_DESIGN_FAMILY = "two_level_regular_fractional_factorial"
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
    low: float | str
    high: float | str
    unit: str | None = None
    factor_kind: str = "numeric"
    domain_kind: str = "continuous"
    step: float | None = None
    display_decimals: int | None = None


@dataclass(frozen=True)
class FactorialDesignOptions:
    replicates: int
    center_points: int
    randomize: bool
    randomization_seed: int
    block_count: int = 1
    design_type: str = "two_level_full"
    fraction_id: str | None = None


@dataclass(frozen=True)
class FractionalFactorialMetadata:
    catalog_entry_id: str
    base_factor_count: int
    fraction_exponent: int
    fraction: str
    resolution: int
    generators: tuple[str, ...]
    defining_relation: tuple[str, ...]
    alias_groups: tuple[tuple[str, ...], ...]
    estimable_terms: tuple[str, ...]
    non_estimable_terms: tuple[str, ...]
    principal_fraction: bool = True


@dataclass(frozen=True)
class FactorialDesignRun:
    standard_order: int
    run_order: int
    replicate_index: int
    center_point: bool
    block_index: int | None
    factor_levels: dict[str, float | str]
    coded_levels: dict[str, int]


@dataclass(frozen=True)
class FactorialDesign:
    schema_version: int
    family: str
    factors: tuple[FactorialFactor, ...]
    options: FactorialDesignOptions
    runs: tuple[FactorialDesignRun, ...]
    design_sha256: str
    fractional: FractionalFactorialMetadata | None = None


@dataclass(frozen=True)
class FractionalCatalogEntry:
    catalog_entry_id: str
    factor_count: int
    base_factor_count: int
    resolution: int
    generated_words: tuple[tuple[int, ...], ...]


FRACTIONAL_CATALOG: tuple[FractionalCatalogEntry, ...] = (
    FractionalCatalogEntry("3-factor-half-r3", 3, 2, 3, ((0, 1),)),
    FractionalCatalogEntry("4-factor-half-r4", 4, 3, 4, ((0, 1, 2),)),
    FractionalCatalogEntry("5-factor-half-r5", 5, 4, 5, ((0, 1, 2, 3),)),
    FractionalCatalogEntry("5-factor-quarter-r3", 5, 3, 3, ((0, 1), (0, 2))),
    FractionalCatalogEntry("6-factor-half-r6", 6, 5, 6, ((0, 1, 2, 3, 4),)),
    FractionalCatalogEntry("6-factor-quarter-r4", 6, 4, 4, ((0, 1, 2), (1, 2, 3))),
    FractionalCatalogEntry("6-factor-eighth-r3", 6, 3, 3, ((0, 1), (0, 2), (1, 2))),
)


def list_fractional_factorial_catalog(factor_count: int) -> tuple[FractionalCatalogEntry, ...]:
    return tuple(entry for entry in FRACTIONAL_CATALOG if entry.factor_count == factor_count)


def fractional_metadata_for(
    factors: list[FactorialFactor],
    fraction_id: str,
) -> FractionalFactorialMetadata:
    entry = next(
        (
            candidate
            for candidate in FRACTIONAL_CATALOG
            if candidate.catalog_entry_id == fraction_id and candidate.factor_count == len(factors)
        ),
        None,
    )
    if entry is None:
        raise FactorialDesignError(
            code="doe_fractional_catalog_entry_invalid",
            message="요인 수에 맞는 검증된 부분요인 설계를 선택하세요.",
        )
    return _fractional_metadata(factors, entry)


def generate_two_level_factorial_design(
    factors: list[FactorialFactor],
    options: FactorialDesignOptions,
) -> FactorialDesign:
    if options.design_type == "two_level_full":
        return generate_two_level_full_factorial_design(factors, options)
    if options.design_type == "two_level_fractional":
        return generate_two_level_fractional_factorial_design(factors, options)
    raise FactorialDesignError(
        code="doe_factorial_design_type_invalid",
        message="지원하지 않는 factorial 설계 종류입니다.",
    )


def generate_two_level_full_factorial_design(
    factors: list[FactorialFactor],
    options: FactorialDesignOptions,
) -> FactorialDesign:
    _validate_factors(factors)
    _validate_options(options)
    if options.center_points > 0:
        _validate_executable_centers(factors)
    base_run_count = 2 ** len(factors)
    center_specs = _center_run_specs(factors, options)
    run_count = base_run_count * options.replicates + len(center_specs)
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

    for center_index, (levels, coded, block_index) in enumerate(center_specs, start=1):
        rows.append(
            FactorialDesignRun(
                standard_order=base_run_count + center_index,
                run_order=0,
                replicate_index=(
                    (center_index - 1) // max(1, _categorical_combination_count(factors))
                )
                + 1,
                center_point=True,
                block_index=block_index,
                factor_levels=levels,
                coded_levels=coded,
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
            block_index=(
                row.block_index
                if row.center_point
                else _block_index(run_order, options.block_count)
            ),
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


def generate_two_level_fractional_factorial_design(
    factors: list[FactorialFactor],
    options: FactorialDesignOptions,
) -> FactorialDesign:
    _validate_factors(factors)
    _validate_options(options)
    if options.center_points > 0:
        _validate_executable_centers(factors)
    entry = next(
        (
            candidate
            for candidate in FRACTIONAL_CATALOG
            if candidate.catalog_entry_id == options.fraction_id
            and candidate.factor_count == len(factors)
        ),
        None,
    )
    if entry is None:
        raise FactorialDesignError(
            code="doe_fractional_catalog_entry_invalid",
            message="요인 수에 맞는 검증된 부분요인 설계를 선택하세요.",
        )
    base_run_count = 2**entry.base_factor_count
    center_specs = _center_run_specs(factors, options)
    run_count = base_run_count * options.replicates + len(center_specs)
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
            coded = _fractional_coded_levels(factors, entry, standard_order)
            rows.append(
                FactorialDesignRun(
                    standard_order=standard_order,
                    run_order=0,
                    replicate_index=replicate_index,
                    center_point=False,
                    block_index=None,
                    factor_levels={
                        factor.name: factor.low if coded[factor.name] == -1 else factor.high
                        for factor in factors
                    },
                    coded_levels=coded,
                )
            )
    for center_index, (levels, coded, block_index) in enumerate(center_specs, start=1):
        rows.append(
            FactorialDesignRun(
                standard_order=base_run_count + center_index,
                run_order=0,
                replicate_index=(
                    (center_index - 1) // max(1, _categorical_combination_count(factors))
                )
                + 1,
                center_point=True,
                block_index=block_index,
                factor_levels=levels,
                coded_levels=coded,
            )
        )
    order = list(range(len(rows)))
    if options.randomize:
        random.Random(options.randomization_seed).shuffle(order)
    runs = tuple(
        FactorialDesignRun(
            standard_order=row.standard_order,
            run_order=run_order,
            replicate_index=row.replicate_index,
            center_point=row.center_point,
            block_index=(
                row.block_index
                if row.center_point
                else _block_index(run_order, options.block_count)
            ),
            factor_levels=row.factor_levels,
            coded_levels=row.coded_levels,
        )
        for run_order, row in enumerate((rows[index] for index in order), start=1)
    )
    fractional = _fractional_metadata(factors, entry)
    payload = canonical_factorial_design_payload(
        family=FRACTIONAL_FACTORIAL_DESIGN_FAMILY,
        factors=factors,
        options=options,
        runs=runs,
        schema_version=FRACTIONAL_FACTORIAL_DESIGN_SCHEMA_VERSION,
    )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return FactorialDesign(
        schema_version=FRACTIONAL_FACTORIAL_DESIGN_SCHEMA_VERSION,
        family=FRACTIONAL_FACTORIAL_DESIGN_FAMILY,
        factors=tuple(factors),
        options=options,
        runs=runs,
        design_sha256=hashlib.sha256(encoded).hexdigest(),
        fractional=fractional,
    )


def canonical_factorial_design_payload(
    *,
    family: str,
    factors: list[FactorialFactor] | tuple[FactorialFactor, ...],
    options: FactorialDesignOptions,
    runs: tuple[FactorialDesignRun, ...],
    schema_version: int = FACTORIAL_DESIGN_SCHEMA_VERSION,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "family": family,
        "factors": [factor_to_payload(factor) for factor in factors],
        "options": options_to_payload(options, schema_version=schema_version),
        "runs": [run_to_payload(run) for run in sorted(runs, key=lambda run: run.run_order)],
    }


def factor_to_payload(factor: FactorialFactor) -> dict[str, Any]:
    if factor.factor_kind == "categorical":
        return {
            "factor_kind": "categorical",
            "name": factor.name,
            "low_label": str(factor.low),
            "high_label": str(factor.high),
            "unit": factor.unit,
        }
    low, high = _numeric_bounds(factor)
    domain = DoeFactorDomain(
        low=low,
        high=high,
        domain_kind=factor.domain_kind,  # type: ignore[arg-type]
        step=factor.step,
        display_decimals=factor.display_decimals,
    )
    payload = {
        "name": factor.name,
        "low": low,
        "high": high,
        "unit": factor.unit,
    }
    if (
        domain.domain_kind != "continuous"
        or domain.step is not None
        or domain.display_decimals is not None
    ):
        payload.update(factor_domain_payload(domain))
    return payload


def options_to_payload(
    options: FactorialDesignOptions,
    *,
    schema_version: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "replicates": options.replicates,
        "center_points": options.center_points,
        "randomize": options.randomize,
        "randomization_seed": options.randomization_seed,
        "block_count": options.block_count,
    }
    resolved_schema_version = (
        FRACTIONAL_FACTORIAL_DESIGN_SCHEMA_VERSION
        if schema_version is None and options.design_type == "two_level_fractional"
        else (1 if schema_version is None else schema_version)
    )
    if (
        options.design_type != "two_level_full"
        or options.fraction_id is not None
        or resolved_schema_version != 1
    ):
        payload.update(
            {
                "design_type": options.design_type,
                "fraction_id": options.fraction_id,
                "design_schema_version": resolved_schema_version,
            }
        )
    return payload


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
        if factor.factor_kind == "categorical":
            low_label = str(factor.low).strip()
            high_label = str(factor.high).strip()
            if (
                not low_label
                or not high_label
                or low_label == high_label
                or any(ord(character) < 32 for character in f"{low_label}{high_label}")
            ):
                raise FactorialDesignError(
                    code="doe_factorial_categorical_levels_invalid",
                    message="범주형 DOE 요인의 두 수준은 비어 있지 않고 서로 달라야 합니다.",
                )
            continue
        if factor.factor_kind != "numeric":
            raise FactorialDesignError(
                code="doe_factorial_factor_kind_invalid",
                message="지원하지 않는 DOE 요인 유형입니다.",
            )
        low, high = _numeric_bounds(factor)
        if not isfinite(low) or not isfinite(high) or low >= high:
            raise FactorialDesignError(
                code="doe_factorial_factor_range_invalid",
                message="DOE 요인의 low/high 수준은 유한한 숫자이며 low < high 여야 합니다.",
            )
        domain = DoeFactorDomain(
            low=low,
            high=high,
            domain_kind=factor.domain_kind,  # type: ignore[arg-type]
            step=factor.step,
            display_decimals=factor.display_decimals,
        )
        try:
            validate_factor_domain(domain)
        except DoeFactorDomainError as exc:
            raise FactorialDesignError(exc.code, "DOE 요인의 실행 가능 간격을 확인하세요.") from exc


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


def _validate_executable_centers(factors: list[FactorialFactor]) -> None:
    numeric_factors = [factor for factor in factors if factor.factor_kind == "numeric"]
    if not numeric_factors:
        raise FactorialDesignError(
            code="doe_factorial_center_requires_numeric_factor",
            message="모든 요인이 범주형이면 센터점으로 곡률을 평가할 수 없습니다.",
        )
    for factor in numeric_factors:
        low, high = _numeric_bounds(factor)
        domain = DoeFactorDomain(
            low=low,
            high=high,
            domain_kind=factor.domain_kind,  # type: ignore[arg-type]
            step=factor.step,
            display_decimals=factor.display_decimals,
        )
        if domain.domain_kind == "discrete_numeric" and not domain.is_executable(
            (low + high) / 2
        ):
            raise FactorialDesignError(
                code="doe_factorial_center_not_executable",
                message=(
                    f"현재 실행 간격에서는 {factor.name} 센터점을 실행할 수 없습니다. "
                    "센터점을 제거하거나 요인 범위와 간격을 조정하세요."
                ),
            )


def _fractional_coded_levels(
    factors: list[FactorialFactor],
    entry: FractionalCatalogEntry,
    standard_order: int,
) -> dict[str, int]:
    offset = standard_order - 1
    base = [1 if (offset >> index) & 1 else -1 for index in range(entry.base_factor_count)]
    levels = list(base)
    for word in entry.generated_words:
        value = 1
        for index in word:
            value *= base[index]
        levels.append(value)
    return {factor.name: levels[index] for index, factor in enumerate(factors)}


def _fractional_metadata(
    factors: list[FactorialFactor],
    entry: FractionalCatalogEntry,
) -> FractionalFactorialMetadata:
    factor_labels = [chr(ord("A") + index) for index in range(entry.factor_count)]
    defining_generators = [
        frozenset((*word, entry.base_factor_count + generated_index))
        for generated_index, word in enumerate(entry.generated_words)
    ]
    defining_words: set[frozenset[int]] = {frozenset()}
    for generator in defining_generators:
        defining_words |= {word.symmetric_difference(generator) for word in tuple(defining_words)}
    defining_relation = tuple(
        "I" if not word else "".join(factor_labels[index] for index in sorted(word))
        for word in sorted(defining_words, key=lambda word: (len(word), tuple(sorted(word))))
    )
    generators = tuple(
        f"{factor_labels[entry.base_factor_count + index]}="
        + "".join(factor_labels[item] for item in word)
        for index, word in enumerate(entry.generated_words)
    )
    candidate_effects = [frozenset((index,)) for index in range(entry.factor_count)] + [
        frozenset((left, right))
        for left in range(entry.factor_count)
        for right in range(left + 1, entry.factor_count)
    ]
    groups: dict[tuple[tuple[int, ...], ...], tuple[str, ...]] = {}
    for effect in candidate_effects:
        aliases = {effect.symmetric_difference(word) for word in defining_words}
        key = tuple(
            sorted(
                (tuple(sorted(alias)) for alias in aliases),
                key=lambda value: (len(value), value),
            )
        )
        labels = tuple(_effect_label(alias, factors) for alias in aliases if alias)
        groups[key] = tuple(sorted(labels, key=lambda label: (label.count(" × "), label)))
    alias_groups = tuple(sorted(set(groups.values()), key=lambda group: group[0]))
    main_terms = tuple(factor.name for factor in factors)
    independently_estimable = main_terms
    aliased_terms = tuple(
        sorted(
            {
                alias
                for group in alias_groups
                if any(term in group for term in main_terms)
                for alias in group
                if alias not in main_terms
            }
        )
    )
    return FractionalFactorialMetadata(
        catalog_entry_id=entry.catalog_entry_id,
        base_factor_count=entry.base_factor_count,
        fraction_exponent=entry.factor_count - entry.base_factor_count,
        fraction=f"1/{2 ** (entry.factor_count - entry.base_factor_count)}",
        resolution=entry.resolution,
        generators=generators,
        defining_relation=defining_relation,
        alias_groups=alias_groups,
        estimable_terms=independently_estimable,
        non_estimable_terms=aliased_terms,
    )


def _effect_label(effect: frozenset[int], factors: list[FactorialFactor]) -> str:
    return " × ".join(factors[index].name for index in sorted(effect)) if effect else "I"


def _factor_levels_for_standard_order(
    factors: list[FactorialFactor],
    standard_order: int,
) -> dict[str, float | str]:
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


def _numeric_bounds(factor: FactorialFactor) -> tuple[float, float]:
    try:
        return float(factor.low), float(factor.high)
    except (TypeError, ValueError) as exc:
        raise FactorialDesignError(
            code="doe_factorial_factor_range_invalid",
            message="숫자형 DOE 요인의 low/high 수준을 확인하세요.",
        ) from exc


def _categorical_combination_count(factors: list[FactorialFactor]) -> int:
    return 2 ** sum(factor.factor_kind == "categorical" for factor in factors)


def _center_run_specs(
    factors: list[FactorialFactor],
    options: FactorialDesignOptions,
) -> list[tuple[dict[str, float | str], dict[str, int], int | None]]:
    if options.center_points == 0:
        return []
    categorical_factors = [factor for factor in factors if factor.factor_kind == "categorical"]
    sign_combinations = list(product((-1, 1), repeat=len(categorical_factors)))
    specs: list[tuple[dict[str, float | str], dict[str, int], int | None]] = []
    for block_index in range(1, options.block_count + 1):
        for _center_index in range(options.center_points):
            for signs in sign_combinations:
                categorical_signs = {
                    factor.name: signs[index] for index, factor in enumerate(categorical_factors)
                }
                levels: dict[str, float | str] = {}
                coded: dict[str, int] = {}
                for factor in factors:
                    if factor.factor_kind == "categorical":
                        sign = categorical_signs[factor.name]
                        levels[factor.name] = factor.low if sign == -1 else factor.high
                        coded[factor.name] = sign
                    else:
                        low, high = _numeric_bounds(factor)
                        levels[factor.name] = (low + high) / 2
                        coded[factor.name] = 0
                specs.append(
                    (
                        levels,
                        coded,
                        None if options.block_count == 1 else block_index,
                    )
                )
    return specs
