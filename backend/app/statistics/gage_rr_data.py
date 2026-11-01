"""Shared, label-preserving preparation for crossed Gage R&R."""

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite


class GageRrDataError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class GageRrColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class GageObservation:
    part: str
    operator: str
    replicate: str
    value: float
    source_row_number: int


@dataclass(frozen=True)
class PreparedGageData:
    observations: list[GageObservation]
    sample: dict[str, int]
    design: dict[str, object]
    replicate_mode: str


def resolve_replicate_mode(mode: str | None, has_column: bool) -> str:
    resolved = mode or ("explicit_column" if has_column else "infer_from_rows")
    if resolved not in {"explicit_column", "infer_from_rows"} or (
        (resolved == "explicit_column") != has_column
    ):
        raise GageRrDataError("gage_rr_replicate_mode_invalid")
    return resolved


def prepare_gage_data(
    rows: Iterable[Sequence[str | None]],
    *,
    measurement_column: GageRrColumn,
    part_column: GageRrColumn,
    operator_column: GageRrColumn,
    replicate_column: GageRrColumn | None = None,
    replicate_mode: str | None = None,
    missing_policy: str = "complete_case",
    decimal: str = ".",
    thousands: str | None = None,
    source_row_numbers: Sequence[int] | None = None,
) -> PreparedGageData:
    if missing_policy != "complete_case":
        raise GageRrDataError("gage_rr_missing_policy_unsupported")
    mode = resolve_replicate_mode(replicate_mode, replicate_column is not None)
    sample = dict.fromkeys(
        [
            "n_total",
            "n_used",
            "n_excluded",
            "n_excluded_missing_measurement",
            "n_excluded_non_numeric_measurement",
            "n_excluded_missing_part",
            "n_excluded_missing_operator",
            "n_excluded_missing_replicate",
            "n_excluded_missing_identifier",
        ],
        0,
    )
    observations: list[GageObservation] = []
    cell_counts: Counter[tuple[str, str]] = Counter()
    replicate_sets: dict[tuple[str, str], set[str]] = defaultdict(set)
    duplicates = 0
    for position, row in enumerate(rows):
        source_row_number = (
            position + 1 if source_row_numbers is None else source_row_numbers[position]
        )
        sample["n_total"] += 1
        measurement = row_value(row, measurement_column.column_index)
        part = row_value(row, part_column.column_index)
        operator = row_value(row, operator_column.column_index)
        replicate = (
            None if replicate_column is None else row_value(row, replicate_column.column_index)
        )
        missing = {
            "measurement": measurement is None or measurement.strip() == "",
            "part": part is None or part.strip() == "",
            "operator": operator is None or operator.strip() == "",
            "replicate": replicate_column is not None
            and (replicate is None or replicate.strip() == ""),
        }
        for key, absent in missing.items():
            sample[f"n_excluded_missing_{key}"] += int(absent)
        sample["n_excluded_missing_identifier"] += int(
            any(missing[key] for key in ("part", "operator", "replicate"))
        )
        if any(missing.values()):
            continue
        value = parse_number(measurement, decimal=decimal, thousands=thousands)
        if value is None:
            sample["n_excluded_non_numeric_measurement"] += 1
            continue
        assert part is not None and operator is not None
        cell = (part.strip(), operator.strip())
        cell_counts[cell] += 1
        identity = str(cell_counts[cell]) if replicate_column is None else str(replicate).strip()
        duplicates += int(identity in replicate_sets[cell])
        replicate_sets[cell].add(identity)
        observations.append(GageObservation(*cell, identity, value, source_row_number))
    sample["n_used"] = len(observations)
    sample["n_excluded"] = sample["n_total"] - len(observations)
    parts = sorted({item.part for item in observations})
    operators = sorted({item.operator for item in observations})
    counts = list(cell_counts.values())
    minimum, maximum = min(counts, default=0), max(counts, default=0)
    expected = len(parts) * len(operators)
    missing_cells = expected - len(cell_counts)
    balanced = bool(counts) and missing_cells == 0 and minimum == maximum
    errors = []
    if not observations:
        errors.append("gage_rr_no_usable_measurements")
    if len(parts) < 2:
        errors.append("gage_rr_part_count_too_small")
    if len(operators) < 2:
        errors.append("gage_rr_operator_count_too_small")
    if minimum < 2:
        errors.append("gage_rr_replicate_count_too_small")
    if missing_cells:
        errors.append("gage_rr_crossed_cells_missing")
    if minimum != maximum:
        errors.append("gage_rr_unbalanced_crossed_design")
    if duplicates:
        errors.append("gage_rr_duplicate_replicates_per_cell")
    if observations and all(item.value == observations[0].value for item in observations):
        errors.append("gage_rr_zero_total_variation")
    distribution = Counter(counts)
    design: dict[str, object] = {
        "design_type": "crossed",
        "balanced": balanced,
        "ready_for_anova": not errors,
        "part_count": len(parts),
        "operator_count": len(operators),
        "replicate_count": minimum if balanced else None,
        "replicate_level_count": len(set().union(*replicate_sets.values()))
        if replicate_sets
        else 0,
        "expected_cell_count": expected,
        "observed_cell_count": len(cell_counts),
        "missing_cell_count": missing_cells,
        "min_replicates_per_cell": minimum,
        "max_replicates_per_cell": maximum,
        "replicate_set_consistent": len({frozenset(values) for values in replicate_sets.values()})
        <= 1,
        "duplicate_replicates_per_cell": duplicates,
        "cell_replicate_count_distribution": [
            {"replicate_count": count, "cell_count": distribution[count]}
            for count in sorted(distribution)
        ],
        "part_ids": parts,
        "operator_ids": operators,
        "error_codes": errors,
    }
    return PreparedGageData(observations, sample, design, mode)


def public_design(design: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in design.items()
        if key not in {"part_ids", "operator_ids", "error_codes"}
    }


def column_payload(column: GageRrColumn | None) -> dict[str, object] | None:
    return None if column is None else vars(column)


def row_value(row: Sequence[str | None], index: int) -> str | None:
    return row[index] if index < len(row) else None


def parse_number(value: str | None, *, decimal: str, thousands: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    normalized = value.strip()
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    number = float(parsed)
    return number if isfinite(number) else None
