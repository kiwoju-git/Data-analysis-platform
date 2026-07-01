from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import erf, fsum, isfinite, sqrt

MIN_CAPABILITY_N = 2
DEFAULT_HISTOGRAM_BIN_LIMIT = 30
D2_MOVING_RANGE_2 = 1.128


class CapabilityError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CapabilityColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


def calculate_normal_capability(
    rows: Iterable[Sequence[str | None]],
    value_column: CapabilityColumn,
    *,
    lsl: float | None,
    usl: float | None,
    target: float | None = None,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
    histogram_bin_limit: int = DEFAULT_HISTOGRAM_BIN_LIMIT,
) -> dict[str, object]:
    if missing_policy != "complete_case":
        raise CapabilityError("capability_missing_policy_unsupported")
    if lsl is None and usl is None:
        raise CapabilityError("capability_spec_limit_required")
    if lsl is not None and usl is not None and lsl >= usl:
        raise CapabilityError("capability_spec_limits_invalid")
    if target is not None:
        if lsl is not None and target < lsl:
            raise CapabilityError("capability_target_outside_spec")
        if usl is not None and target > usl:
            raise CapabilityError("capability_target_outside_spec")
    if histogram_bin_limit < 1 or histogram_bin_limit > DEFAULT_HISTOGRAM_BIN_LIMIT:
        raise CapabilityError("invalid_capability_histogram_bin_limit")

    n_total = 0
    n_excluded_missing_value = 0
    n_excluded_non_numeric_value = 0
    values: list[float] = []

    for row in rows:
        n_total += 1
        raw_value = row[value_column.column_index] if value_column.column_index < len(row) else None
        if raw_value is None or raw_value.strip() == "":
            n_excluded_missing_value += 1
            continue
        parsed_value = _parse_number(raw_value, decimal=decimal, thousands=thousands)
        if parsed_value is None:
            n_excluded_non_numeric_value += 1
            continue
        values.append(parsed_value)

    n_used = len(values)
    if n_used < MIN_CAPABILITY_N:
        raise CapabilityError("capability_n_too_small")

    mean = fsum(values) / n_used
    overall_sigma = _sample_std(values)
    if overall_sigma <= 0:
        raise CapabilityError("capability_zero_overall_sigma")
    moving_ranges = [abs(values[index] - values[index - 1]) for index in range(1, n_used)]
    mrbar = fsum(moving_ranges) / len(moving_ranges)
    within_sigma = mrbar / D2_MOVING_RANGE_2
    if within_sigma <= 0:
        raise CapabilityError("capability_zero_within_sigma")

    sorted_values = sorted(values)
    observed = _observed_nonconformance(values, lsl=lsl, usl=usl)
    expected = _expected_normal_nonconformance(
        mean=mean,
        sigma=overall_sigma,
        lsl=lsl,
        usl=usl,
    )

    result = {
        "schema_version": 1,
        "summary_type": "capability_analysis",
        "method": "normal_capability",
        "distribution": "normal",
        "missing_policy": missing_policy,
        "sigma_estimators": {
            "overall": "sample_standard_deviation_ddof_1",
            "within": "average_moving_range_d2",
            "moving_range_length": 2,
            "d2": D2_MOVING_RANGE_2,
            "mrbar": mrbar,
        },
        "warnings": _result_warnings(
            n_excluded_missing_value=n_excluded_missing_value,
            n_excluded_non_numeric_value=n_excluded_non_numeric_value,
            lsl=lsl,
            usl=usl,
            target=target,
        ),
        "value": _column_payload(value_column),
        "spec_limits": {
            "lsl": lsl,
            "usl": usl,
            "target": target,
        },
        "n_total": n_total,
        "n_used": n_used,
        "n_excluded_missing_value": n_excluded_missing_value,
        "n_excluded_non_numeric_value": n_excluded_non_numeric_value,
        "sample": {
            "mean": mean,
            "std_overall": overall_sigma,
            "std_within": within_sigma,
            "min": sorted_values[0],
            "max": sorted_values[-1],
        },
        "capability": {
            "within": _capability_indices(mean=mean, sigma=within_sigma, lsl=lsl, usl=usl),
            "overall": _capability_indices(mean=mean, sigma=overall_sigma, lsl=lsl, usl=usl),
        },
        "observed_nonconformance": observed,
        "expected_nonconformance_normal": expected,
        "histogram": _histogram(
            sorted_values,
            mean=mean,
            sigma=overall_sigma,
            bin_limit=histogram_bin_limit,
        ),
    }
    return result


def _parse_number(value: str, *, decimal: str, thousands: str | None) -> float | None:
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


def _sample_std(values: Sequence[float]) -> float:
    mean = fsum(values) / len(values)
    variance = fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return sqrt(variance)


def _capability_indices(
    *,
    mean: float,
    sigma: float,
    lsl: float | None,
    usl: float | None,
) -> dict[str, float | None]:
    lower = None if lsl is None else (mean - lsl) / (3 * sigma)
    upper = None if usl is None else (usl - mean) / (3 * sigma)
    two_sided = None if lsl is None or usl is None else (usl - lsl) / (6 * sigma)
    available_sides = [value for value in (lower, upper) if value is not None]
    return {
        "two_sided": two_sided,
        "lower": lower,
        "upper": upper,
        "min_side": min(available_sides) if available_sides else None,
    }


def _observed_nonconformance(
    values: Sequence[float],
    *,
    lsl: float | None,
    usl: float | None,
) -> dict[str, object]:
    below = 0 if lsl is None else sum(1 for value in values if value < lsl)
    above = 0 if usl is None else sum(1 for value in values if value > usl)
    total = below + above
    n = len(values)
    return {
        "below_lsl_count": below,
        "above_usl_count": above,
        "total_count": total,
        "below_lsl_proportion": below / n,
        "above_usl_proportion": above / n,
        "total_proportion": total / n,
        "total_ppm": (total / n) * 1_000_000,
    }


def _expected_normal_nonconformance(
    *,
    mean: float,
    sigma: float,
    lsl: float | None,
    usl: float | None,
) -> dict[str, float]:
    below = 0.0 if lsl is None else _normal_cdf((lsl - mean) / sigma)
    above = 0.0 if usl is None else 1 - _normal_cdf((usl - mean) / sigma)
    total = below + above
    return {
        "below_lsl_probability": below,
        "above_usl_probability": above,
        "total_probability": total,
        "total_ppm": total * 1_000_000,
    }


def _normal_cdf(z: float) -> float:
    return 0.5 * (1 + erf(z / sqrt(2)))


def _normal_pdf(x: float, *, mean: float, sigma: float) -> float:
    z = (x - mean) / sigma
    return (1 / (sigma * sqrt(2 * 3.141592653589793))) * (2.718281828459045 ** (-0.5 * z * z))


def _histogram(
    sorted_values: Sequence[float],
    *,
    mean: float,
    sigma: float,
    bin_limit: int,
) -> dict[str, object]:
    n = len(sorted_values)
    minimum = sorted_values[0]
    maximum = sorted_values[-1]
    if minimum == maximum:
        raise CapabilityError("capability_zero_overall_sigma")

    suggested_bins = max(5, min(bin_limit, round(sqrt(n)) + 1))
    width = (maximum - minimum) / suggested_bins
    counts = [0 for _index in range(suggested_bins)]
    for value in sorted_values:
        if value == maximum:
            index = suggested_bins - 1
        else:
            index = int((value - minimum) / width)
        counts[index] += 1

    bins = []
    for index, count in enumerate(counts):
        lower = minimum + (index * width)
        upper = lower + width
        midpoint = (lower + upper) / 2
        bins.append(
            {
                "lower": lower,
                "upper": upper if index < suggested_bins - 1 else maximum,
                "midpoint": midpoint,
                "count": count,
                "proportion": count / n,
                "density": count / (n * width),
                "normal_density": _normal_pdf(midpoint, mean=mean, sigma=sigma),
            },
        )
    return {
        "bin_count": suggested_bins,
        "bins": bins,
    }


def _result_warnings(
    *,
    n_excluded_missing_value: int,
    n_excluded_non_numeric_value: int,
    lsl: float | None,
    usl: float | None,
    target: float | None,
) -> list[str]:
    warnings = [
        "capability_normal_model_assumed",
        "capability_control_limits_not_spec_limits",
        "capability_process_stability_not_proven",
        "capability_measurement_system_not_verified",
        "capability_within_sigma_uses_canonical_moving_range",
        "capability_point_estimates_without_ci",
    ]
    if lsl is None or usl is None:
        warnings.append("capability_one_sided_spec")
    if target is not None:
        warnings.append("capability_target_recorded_cpm_not_computed")
    if n_excluded_missing_value > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_value > 0:
        warnings.append("non_numeric_values_excluded")
    return warnings


def _column_payload(column: CapabilityColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }
