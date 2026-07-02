from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import floor, isfinite, sqrt

from scipy import stats  # type: ignore[import-untyped]

from app.statistics.gage_rr_preflight import GageRrColumn


class GageRrError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class _Observation:
    part: str
    operator: str
    replicate: str
    value: float


def calculate_gage_rr_anova(
    rows: Iterable[Sequence[str | None]],
    *,
    measurement_column: GageRrColumn,
    part_column: GageRrColumn,
    operator_column: GageRrColumn,
    replicate_column: GageRrColumn,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
) -> dict[str, object]:
    if missing_policy != "complete_case":
        raise GageRrError("gage_rr_missing_policy_unsupported")

    observations, sample = _collect_observations(
        rows,
        measurement_column=measurement_column,
        part_column=part_column,
        operator_column=operator_column,
        replicate_column=replicate_column,
        decimal=decimal,
        thousands=thousands,
    )
    design = _balanced_design(observations)
    if not design["ready_for_anova"]:
        raise GageRrError(str(design["error_code"]))

    anova = _anova(observations, design)
    components = _variance_components(anova, design)
    total_variation = _component_mapping(components["total_variation"])
    if _component_float(total_variation, "final_variance") <= 0:
        raise GageRrError("gage_rr_zero_total_variation")

    return {
        "schema_version": 1,
        "summary_type": "gage_rr",
        "method": "balanced_crossed_anova",
        "missing_policy": missing_policy,
        "columns": {
            "measurement": _column_payload(measurement_column),
            "part": _column_payload(part_column),
            "operator": _column_payload(operator_column),
            "replicate": _column_payload(replicate_column),
        },
        "sample": sample,
        "design": {
            key: value
            for key, value in design.items()
            if key not in {"error_code", "part_ids", "operator_ids", "replicate_ids"}
        },
        "anova_table": anova["table"],
        "variance_components": components,
        "warnings": _warnings(sample, components),
        "notes": [
            "interaction_not_pooled",
            "negative_variance_components_clamped_to_zero",
            "part_operator_replicate_labels_redacted",
        ],
    }


def _collect_observations(
    rows: Iterable[Sequence[str | None]],
    *,
    measurement_column: GageRrColumn,
    part_column: GageRrColumn,
    operator_column: GageRrColumn,
    replicate_column: GageRrColumn,
    decimal: str,
    thousands: str | None,
) -> tuple[list[_Observation], dict[str, int]]:
    n_total = 0
    n_excluded_missing_measurement = 0
    n_excluded_non_numeric_measurement = 0
    n_excluded_missing_part = 0
    n_excluded_missing_operator = 0
    n_excluded_missing_replicate = 0
    n_excluded_missing_identifier = 0
    observations: list[_Observation] = []

    for row in rows:
        n_total += 1
        raw_measurement = _row_value(row, measurement_column.column_index)
        raw_part = _row_value(row, part_column.column_index)
        raw_operator = _row_value(row, operator_column.column_index)
        raw_replicate = _row_value(row, replicate_column.column_index)

        measurement_missing = _is_missing(raw_measurement)
        part_missing = _is_missing(raw_part)
        operator_missing = _is_missing(raw_operator)
        replicate_missing = _is_missing(raw_replicate)
        if measurement_missing:
            n_excluded_missing_measurement += 1
        if part_missing:
            n_excluded_missing_part += 1
        if operator_missing:
            n_excluded_missing_operator += 1
        if replicate_missing:
            n_excluded_missing_replicate += 1
        if part_missing or operator_missing or replicate_missing:
            n_excluded_missing_identifier += 1
        if measurement_missing or part_missing or operator_missing or replicate_missing:
            continue

        measurement = _parse_number(raw_measurement, decimal=decimal, thousands=thousands)
        if measurement is None:
            n_excluded_non_numeric_measurement += 1
            continue
        observations.append(
            _Observation(
                part=_identifier_value(raw_part),
                operator=_identifier_value(raw_operator),
                replicate=_identifier_value(raw_replicate),
                value=measurement,
            ),
        )

    sample = {
        "n_total": n_total,
        "n_used": len(observations),
        "n_excluded": n_total - len(observations),
        "n_excluded_missing_measurement": n_excluded_missing_measurement,
        "n_excluded_non_numeric_measurement": n_excluded_non_numeric_measurement,
        "n_excluded_missing_part": n_excluded_missing_part,
        "n_excluded_missing_operator": n_excluded_missing_operator,
        "n_excluded_missing_replicate": n_excluded_missing_replicate,
        "n_excluded_missing_identifier": n_excluded_missing_identifier,
    }
    return observations, sample


def _balanced_design(observations: Sequence[_Observation]) -> dict[str, object]:
    parts = sorted({observation.part for observation in observations})
    operators = sorted({observation.operator for observation in observations})
    replicate_sets: dict[tuple[str, str], set[str]] = defaultdict(set)
    duplicate_replicates_per_cell = 0
    for observation in observations:
        cell_key = (observation.part, observation.operator)
        if observation.replicate in replicate_sets[cell_key]:
            duplicate_replicates_per_cell += 1
        replicate_sets[cell_key].add(observation.replicate)

    expected_cell_count = len(parts) * len(operators)
    missing_cell_count = max(0, expected_cell_count - len(replicate_sets))
    replicate_count_values = [len(replicates) for replicates in replicate_sets.values()]
    min_replicates_per_cell = min(replicate_count_values, default=0)
    max_replicates_per_cell = max(replicate_count_values, default=0)
    unique_replicate_sets = {frozenset(replicates) for replicates in replicate_sets.values()}
    replicate_set_consistent = len(unique_replicate_sets) == 1
    replicate_ids = sorted(next(iter(unique_replicate_sets), frozenset()))

    error_code: str | None = None
    if not observations:
        error_code = "gage_rr_no_usable_measurements"
    elif len(parts) < 2:
        error_code = "gage_rr_part_count_too_small"
    elif len(operators) < 2:
        error_code = "gage_rr_operator_count_too_small"
    elif min_replicates_per_cell < 2:
        error_code = "gage_rr_replicate_count_too_small"
    elif missing_cell_count > 0:
        error_code = "gage_rr_crossed_cells_missing"
    elif min_replicates_per_cell != max_replicates_per_cell or not replicate_set_consistent:
        error_code = "gage_rr_unbalanced_crossed_design"
    elif duplicate_replicates_per_cell > 0:
        error_code = "gage_rr_duplicate_replicates_per_cell"

    return {
        "design_type": "crossed",
        "balanced": error_code is None,
        "ready_for_anova": error_code is None,
        "part_count": len(parts),
        "operator_count": len(operators),
        "replicate_count": min_replicates_per_cell if error_code is None else None,
        "expected_cell_count": expected_cell_count,
        "observed_cell_count": len(replicate_sets),
        "missing_cell_count": missing_cell_count,
        "min_replicates_per_cell": min_replicates_per_cell,
        "max_replicates_per_cell": max_replicates_per_cell,
        "replicate_set_consistent": replicate_set_consistent,
        "duplicate_replicates_per_cell": duplicate_replicates_per_cell,
        "error_code": error_code,
        "part_ids": parts,
        "operator_ids": operators,
        "replicate_ids": replicate_ids,
    }


def _anova(
    observations: Sequence[_Observation],
    design: dict[str, object],
) -> dict[str, object]:
    part_ids = _string_list(design["part_ids"])
    operator_ids = _string_list(design["operator_ids"])
    replicate_ids = _string_list(design["replicate_ids"])
    part_count = len(part_ids)
    operator_count = len(operator_ids)
    replicate_count = len(replicate_ids)

    cell_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    part_values: dict[str, list[float]] = defaultdict(list)
    operator_values: dict[str, list[float]] = defaultdict(list)
    all_values = []
    for observation in observations:
        cell_values[(observation.part, observation.operator)].append(observation.value)
        part_values[observation.part].append(observation.value)
        operator_values[observation.operator].append(observation.value)
        all_values.append(observation.value)

    grand_mean = _mean(all_values)
    part_means = {part_id: _mean(part_values[part_id]) for part_id in part_ids}
    operator_means = {
        operator_id: _mean(operator_values[operator_id]) for operator_id in operator_ids
    }
    cell_means = {
        cell_key: _mean(values)
        for cell_key, values in sorted(cell_values.items(), key=lambda item: item[0])
    }

    ss_part = (
        operator_count
        * replicate_count
        * sum((part_means[part_id] - grand_mean) ** 2 for part_id in part_ids)
    )
    ss_operator = (
        part_count
        * replicate_count
        * sum((operator_means[operator_id] - grand_mean) ** 2 for operator_id in operator_ids)
    )
    ss_interaction = replicate_count * sum(
        (
            cell_means[(part_id, operator_id)]
            - part_means[part_id]
            - operator_means[operator_id]
            + grand_mean
        )
        ** 2
        for part_id in part_ids
        for operator_id in operator_ids
    )
    ss_repeatability = sum(
        (value - cell_means[cell_key]) ** 2
        for cell_key, values in cell_values.items()
        for value in values
    )
    ss_total = sum((value - grand_mean) ** 2 for value in all_values)

    df_part = part_count - 1
    df_operator = operator_count - 1
    df_interaction = df_part * df_operator
    df_repeatability = part_count * operator_count * (replicate_count - 1)
    df_total = len(all_values) - 1

    ms_part = ss_part / df_part
    ms_operator = ss_operator / df_operator
    ms_interaction = ss_interaction / df_interaction
    ms_repeatability = ss_repeatability / df_repeatability

    table = [
        _anova_row(
            source="part",
            degrees_of_freedom=df_part,
            sum_of_squares=ss_part,
            mean_square=ms_part,
            denominator="part_operator",
            denominator_mean_square=ms_interaction,
            denominator_degrees_of_freedom=df_interaction,
        ),
        _anova_row(
            source="operator",
            degrees_of_freedom=df_operator,
            sum_of_squares=ss_operator,
            mean_square=ms_operator,
            denominator="part_operator",
            denominator_mean_square=ms_interaction,
            denominator_degrees_of_freedom=df_interaction,
        ),
        _anova_row(
            source="part_operator",
            degrees_of_freedom=df_interaction,
            sum_of_squares=ss_interaction,
            mean_square=ms_interaction,
            denominator="repeatability",
            denominator_mean_square=ms_repeatability,
            denominator_degrees_of_freedom=df_repeatability,
        ),
        {
            "source": "repeatability",
            "degrees_of_freedom": df_repeatability,
            "sum_of_squares": ss_repeatability,
            "mean_square": ms_repeatability,
            "f_statistic": None,
            "p_value": None,
            "denominator": None,
        },
        {
            "source": "total",
            "degrees_of_freedom": df_total,
            "sum_of_squares": ss_total,
            "mean_square": None,
            "f_statistic": None,
            "p_value": None,
            "denominator": None,
        },
    ]
    return {
        "grand_mean": grand_mean,
        "table": table,
        "mean_squares": {
            "part": ms_part,
            "operator": ms_operator,
            "part_operator": ms_interaction,
            "repeatability": ms_repeatability,
        },
        "sums_of_squares": {
            "part": ss_part,
            "operator": ss_operator,
            "part_operator": ss_interaction,
            "repeatability": ss_repeatability,
            "total": ss_total,
        },
    }


def _anova_row(
    *,
    source: str,
    degrees_of_freedom: int,
    sum_of_squares: float,
    mean_square: float,
    denominator: str,
    denominator_mean_square: float,
    denominator_degrees_of_freedom: int,
) -> dict[str, object]:
    if denominator_mean_square <= 0:
        f_statistic = None
        p_value = None
    else:
        f_statistic = mean_square / denominator_mean_square
        p_value = float(stats.f.sf(f_statistic, degrees_of_freedom, denominator_degrees_of_freedom))
    return {
        "source": source,
        "degrees_of_freedom": degrees_of_freedom,
        "sum_of_squares": sum_of_squares,
        "mean_square": mean_square,
        "f_statistic": f_statistic,
        "p_value": p_value,
        "denominator": denominator,
    }


def _variance_components(
    anova: dict[str, object],
    design: dict[str, object],
) -> dict[str, object]:
    mean_squares = _float_dict(anova["mean_squares"])
    part_count = _object_int(design["part_count"])
    operator_count = _object_int(design["operator_count"])
    replicate_count = _object_int(design["replicate_count"])

    raw_repeatability = mean_squares["repeatability"]
    raw_part_operator = (mean_squares["part_operator"] - mean_squares["repeatability"]) / (
        replicate_count
    )
    raw_operator = (mean_squares["operator"] - mean_squares["part_operator"]) / (
        part_count * replicate_count
    )
    raw_part = (mean_squares["part"] - mean_squares["part_operator"]) / (
        operator_count * replicate_count
    )

    repeatability = _component("repeatability", raw_repeatability)
    part_operator = _component("part_operator", raw_part_operator)
    operator = _component("operator", raw_operator)
    reproducibility = _derived_component(
        "reproducibility",
        _component_float(operator, "final_variance")
        + _component_float(part_operator, "final_variance"),
    )
    total_gage_rr = _derived_component(
        "total_gage_rr",
        _component_float(repeatability, "final_variance")
        + _component_float(reproducibility, "final_variance"),
    )
    part_to_part = _component("part_to_part", raw_part)
    total_variation = _derived_component(
        "total_variation",
        _component_float(total_gage_rr, "final_variance")
        + _component_float(part_to_part, "final_variance"),
    )
    components = [
        repeatability,
        operator,
        part_operator,
        reproducibility,
        total_gage_rr,
        part_to_part,
        total_variation,
    ]
    total_variance = _component_float(total_variation, "final_variance")
    total_study_variation = _component_float(total_variation, "study_variation")
    for component in components:
        component["percent_contribution"] = _ratio_percent(
            _component_float(component, "final_variance"),
            total_variance,
        )
        component["percent_study_variation"] = _ratio_percent(
            _component_float(component, "study_variation"),
            total_study_variation,
        )

    gage_std = _component_float(total_gage_rr, "standard_deviation")
    part_std = _component_float(part_to_part, "standard_deviation")
    ndc = None if gage_std <= 0 else floor(1.41 * part_std / gage_std)

    return {
        "repeatability": repeatability,
        "operator": operator,
        "part_operator": part_operator,
        "reproducibility": reproducibility,
        "total_gage_rr": total_gage_rr,
        "part_to_part": part_to_part,
        "total_variation": total_variation,
        "ndc": ndc,
        "ndc_formula": "floor(1.41 * part_to_part_sd / total_gage_rr_sd)",
        "negative_component_policy": "raw_estimate_reported_final_variance_clamped_to_zero",
        "interaction_policy": "preserve_part_operator_interaction_no_pooling",
    }


def _component(name: str, raw_variance: float) -> dict[str, object]:
    final_variance = max(raw_variance, 0.0)
    return {
        "component": name,
        "raw_variance": raw_variance,
        "final_variance": final_variance,
        "standard_deviation": sqrt(final_variance),
        "study_variation": 6 * sqrt(final_variance),
        "clamped_to_zero": raw_variance < 0,
    }


def _derived_component(name: str, final_variance: float) -> dict[str, object]:
    return {
        "component": name,
        "raw_variance": final_variance,
        "final_variance": final_variance,
        "standard_deviation": sqrt(final_variance),
        "study_variation": 6 * sqrt(final_variance),
        "clamped_to_zero": False,
    }


def _warnings(sample: dict[str, int], components: dict[str, object]) -> list[str]:
    warnings = [
        "gage_rr_balanced_crossed_anova_assumed",
        "gage_rr_interaction_not_pooled",
        "gage_rr_independence_not_proven",
        "gage_rr_labels_redacted",
    ]
    for key in ("repeatability", "operator", "part_operator", "part_to_part"):
        component = components[key]
        if isinstance(component, dict) and component.get("clamped_to_zero") is True:
            warnings.append("gage_rr_negative_variance_component_clamped")
            break
    if sample["n_excluded_missing_measurement"] > 0:
        warnings.append("missing_values_excluded")
    if sample["n_excluded_non_numeric_measurement"] > 0:
        warnings.append("non_numeric_values_excluded")
    if sample["n_excluded_missing_identifier"] > 0:
        warnings.append("gage_rr_identifier_missing_excluded")
    return warnings


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip() == ""


def _identifier_value(value: str | None) -> str:
    if value is None:
        raise GageRrError("gage_rr_identifier_missing")
    stripped = value.strip()
    if stripped == "":
        raise GageRrError("gage_rr_identifier_missing")
    return stripped


def _parse_number(value: str | None, *, decimal: str, thousands: str | None) -> float | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
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
    as_float = float(parsed)
    if not isfinite(as_float):
        return None
    return as_float


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _ratio_percent(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return (numerator / denominator) * 100


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise GageRrError("gage_rr_internal_design_invalid")
    return value


def _float_dict(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        raise GageRrError("gage_rr_internal_anova_invalid")
    result = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, int | float):
            raise GageRrError("gage_rr_internal_anova_invalid")
        result[key] = float(item)
    return result


def _object_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GageRrError("gage_rr_internal_design_invalid")
    return value


def _component_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise GageRrError("gage_rr_internal_component_invalid")
    if not all(isinstance(key, str) for key in value):
        raise GageRrError("gage_rr_internal_component_invalid")
    return value


def _component_float(component: dict[str, object], key: str) -> float:
    value = component.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GageRrError("gage_rr_internal_component_invalid")
    return float(value)


def _column_payload(column: GageRrColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }
