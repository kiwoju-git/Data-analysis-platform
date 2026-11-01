from collections import defaultdict
from collections.abc import Iterable, Sequence
from math import floor, fsum, isfinite, sqrt

from scipy import stats  # type: ignore[import-untyped]

from app.statistics.gage_rr_data import (
    GageObservation as _Observation,
)
from app.statistics.gage_rr_data import (
    GageRrColumn,
    GageRrDataError,
    prepare_gage_data,
    public_design,
)
from app.statistics.gage_rr_data import (
    column_payload as _column_payload,
)


class GageRrError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def calculate_gage_rr_anova(
    rows: Iterable[Sequence[str | None]],
    *,
    measurement_column: GageRrColumn,
    part_column: GageRrColumn,
    operator_column: GageRrColumn,
    replicate_column: GageRrColumn | None = None,
    replicate_mode: str | None = None,
    interaction_policy: str = "retain",
    alpha_to_remove_interaction: float = 0.05,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
    source_row_numbers: Sequence[int] | None = None,
) -> dict[str, object]:
    if interaction_policy not in {"retain", "auto_pool"}:
        raise GageRrError("gage_rr_interaction_policy_invalid")
    if not isfinite(alpha_to_remove_interaction) or not 0 < alpha_to_remove_interaction < 1:
        raise GageRrError("gage_rr_interaction_alpha_invalid")
    try:
        prepared = prepare_gage_data(
            rows,
            measurement_column=measurement_column,
            part_column=part_column,
            operator_column=operator_column,
            replicate_column=replicate_column,
            replicate_mode=replicate_mode,
            decimal=decimal,
            thousands=thousands,
            missing_policy=missing_policy,
            source_row_numbers=source_row_numbers,
        )
    except GageRrDataError as exc:
        raise GageRrError(exc.code) from exc
    observations, sample, design = prepared.observations, prepared.sample, prepared.design
    if not design["ready_for_anova"]:
        errors = _string_list(design["error_codes"])
        raise GageRrError(errors[0])
    full = _anova(observations, design)
    full_table = full["table"]
    assert isinstance(full_table, list)
    p_value = full_table[2]["p_value"]
    pooled = (
        interaction_policy == "auto_pool"
        and p_value is not None
        and isfinite(p_value)
        and p_value >= alpha_to_remove_interaction
    )
    reduced = _pooled_anova(full) if pooled else None
    anova = reduced if reduced is not None else full
    components = _variance_components(anova, design, pooled=pooled)
    total_variation = _component_mapping(components["total_variation"])
    if _component_float(total_variation, "final_variance") <= 0:
        raise GageRrError("gage_rr_zero_total_variation")
    reason = (
        "interaction_not_significant"
        if pooled
        else "retained_by_request"
        if interaction_policy == "retain"
        else "interaction_test_unavailable"
        if p_value is None or not isfinite(p_value)
        else "interaction_significant"
    )
    selection = {
        "requested_policy": interaction_policy,
        "effective_policy": "pooled" if pooled else "retain",
        "alpha_to_remove_interaction": alpha_to_remove_interaction,
        "interaction_p_value": p_value,
        "pooled": pooled,
        "reason": reason,
    }
    return {
        "schema_version": 2,
        "summary_type": "gage_rr",
        "method": "balanced_crossed_anova",
        "missing_policy": missing_policy,
        "replicate_mode": prepared.replicate_mode,
        "columns": {
            "measurement": _column_payload(measurement_column),
            "part": _column_payload(part_column),
            "operator": _column_payload(operator_column),
            "replicate": _column_payload(replicate_column),
        },
        "sample": sample,
        "design": public_design(design),
        "anova_table": anova["table"],
        "full_anova_table": full_table,
        "reduced_anova_table": None if reduced is None else reduced["table"],
        "interaction_selection": selection,
        "variance_components": components,
        "warnings": _warnings(sample, components, pooled=pooled),
        "notes": [
            "interaction_pooled" if pooled else "interaction_not_pooled",
            "negative_variance_components_clamped_to_zero",
            "part_operator_replicate_labels_redacted",
            "automatic_replicate_ordinal_is_not_time_or_round"
            if prepared.replicate_mode == "infer_from_rows"
            else "explicit_replicate_identity_is_cell_local",
        ],
    }


def _pooled_anova(full: dict[str, object]) -> dict[str, object]:
    table = full["table"]
    assert isinstance(table, list)
    interaction, error = table[2], table[3]
    df = interaction["degrees_of_freedom"] + error["degrees_of_freedom"]
    ss = interaction["sum_of_squares"] + error["sum_of_squares"]
    mse = ss / df
    rows = [
        _anova_row(
            source=row["source"],
            degrees_of_freedom=row["degrees_of_freedom"],
            sum_of_squares=row["sum_of_squares"],
            mean_square=row["mean_square"],
            denominator="repeatability",
            denominator_mean_square=mse,
            denominator_degrees_of_freedom=df,
        )
        for row in table[:2]
    ]
    rows.extend(
        [
            {**error, "degrees_of_freedom": df, "sum_of_squares": ss, "mean_square": mse},
            table[4],
        ]
    )
    means = _float_dict(full["mean_squares"])
    return {**full, "table": rows, "mean_squares": {**means, "repeatability": mse}}


def _anova(
    observations: Sequence[_Observation],
    design: dict[str, object],
) -> dict[str, object]:
    part_ids = _string_list(design["part_ids"])
    operator_ids = _string_list(design["operator_ids"])
    part_count = len(part_ids)
    operator_count = len(operator_ids)
    replicate_count = _object_int(design["replicate_count"])

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
    *,
    pooled: bool = False,
) -> dict[str, object]:
    mean_squares = _float_dict(anova["mean_squares"])
    part_count = _object_int(design["part_count"])
    operator_count = _object_int(design["operator_count"])
    replicate_count = _object_int(design["replicate_count"])

    raw_repeatability = mean_squares["repeatability"]
    comparison_ms = raw_repeatability if pooled else mean_squares["part_operator"]
    raw_part_operator = (mean_squares["part_operator"] - mean_squares["repeatability"]) / (
        replicate_count
    )
    if pooled:
        raw_part_operator = 0.0
    raw_operator = (mean_squares["operator"] - comparison_ms) / (part_count * replicate_count)
    raw_part = (mean_squares["part"] - comparison_ms) / (operator_count * replicate_count)

    repeatability = _component("repeatability", raw_repeatability)
    part_operator = _component("part_operator", raw_part_operator)
    part_operator["status"] = "removed_from_model" if pooled else "retained"
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
        "interaction_policy": "interaction_pooled_into_repeatability"
        if pooled
        else "preserve_part_operator_interaction_no_pooling",
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


def _warnings(
    sample: dict[str, int], components: dict[str, object], *, pooled: bool = False
) -> list[str]:
    warnings = [
        "gage_rr_balanced_crossed_anova_assumed",
        "gage_rr_interaction_pooled" if pooled else "gage_rr_interaction_not_pooled",
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


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


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
