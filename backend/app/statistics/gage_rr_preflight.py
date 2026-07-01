from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite


class GageRrPreflightError(ValueError):
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


def calculate_gage_rr_preflight(
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
        raise GageRrPreflightError("gage_rr_missing_policy_unsupported")

    n_total = 0
    n_used = 0
    n_excluded_missing_measurement = 0
    n_excluded_non_numeric_measurement = 0
    n_excluded_missing_part = 0
    n_excluded_missing_operator = 0
    n_excluded_missing_replicate = 0
    n_excluded_missing_identifier = 0
    duplicate_replicates_per_cell = 0

    parts: set[str] = set()
    operators: set[str] = set()
    replicate_levels: set[str] = set()
    cells: dict[tuple[str, str], set[str]] = {}

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

        part = _identifier_value(raw_part)
        operator = _identifier_value(raw_operator)
        replicate = _identifier_value(raw_replicate)
        parts.add(part)
        operators.add(operator)
        replicate_levels.add(replicate)
        cell_key = (part, operator)
        cell_replicates = cells.setdefault(cell_key, set())
        if replicate in cell_replicates:
            duplicate_replicates_per_cell += 1
        else:
            cell_replicates.add(replicate)
        n_used += 1

    part_count = len(parts)
    operator_count = len(operators)
    replicate_level_count = len(replicate_levels)
    expected_cell_count = part_count * operator_count
    observed_cell_count = len(cells)
    missing_cell_count = max(0, expected_cell_count - observed_cell_count)
    replicate_counts = [len(replicates) for replicates in cells.values()]
    min_replicates_per_cell = min(replicate_counts, default=0)
    max_replicates_per_cell = max(replicate_counts, default=0)
    replicate_sets = {frozenset(replicates) for replicates in cells.values()}
    replicate_set_consistent = len(replicate_sets) <= 1
    cell_replicate_distribution = _cell_replicate_distribution(replicate_counts)

    issues = _design_issues(
        n_used=n_used,
        part_count=part_count,
        operator_count=operator_count,
        replicate_level_count=replicate_level_count,
        missing_cell_count=missing_cell_count,
        min_replicates_per_cell=min_replicates_per_cell,
        max_replicates_per_cell=max_replicates_per_cell,
        replicate_set_consistent=replicate_set_consistent,
        duplicate_replicates_per_cell=duplicate_replicates_per_cell,
        n_excluded_missing_measurement=n_excluded_missing_measurement,
        n_excluded_non_numeric_measurement=n_excluded_non_numeric_measurement,
        n_excluded_missing_identifier=n_excluded_missing_identifier,
    )
    ready_for_anova = not any(issue["severity"] == "error" for issue in issues)

    return {
        "schema_version": 1,
        "summary_type": "gage_rr_preflight",
        "method": "balanced_crossed_anova_preflight",
        "missing_policy": missing_policy,
        "columns": {
            "measurement": _column_payload(measurement_column),
            "part": _column_payload(part_column),
            "operator": _column_payload(operator_column),
            "replicate": _column_payload(replicate_column),
        },
        "sample": {
            "n_total": n_total,
            "n_used": n_used,
            "n_excluded": n_total - n_used,
            "n_excluded_missing_measurement": n_excluded_missing_measurement,
            "n_excluded_non_numeric_measurement": n_excluded_non_numeric_measurement,
            "n_excluded_missing_part": n_excluded_missing_part,
            "n_excluded_missing_operator": n_excluded_missing_operator,
            "n_excluded_missing_replicate": n_excluded_missing_replicate,
            "n_excluded_missing_identifier": n_excluded_missing_identifier,
        },
        "design": {
            "design_type": "crossed",
            "balanced": ready_for_anova,
            "ready_for_anova": ready_for_anova,
            "part_count": part_count,
            "operator_count": operator_count,
            "replicate_level_count": replicate_level_count,
            "expected_cell_count": expected_cell_count,
            "observed_cell_count": observed_cell_count,
            "missing_cell_count": missing_cell_count,
            "min_replicates_per_cell": min_replicates_per_cell,
            "max_replicates_per_cell": max_replicates_per_cell,
            "expected_replicates_per_cell": (min_replicates_per_cell if ready_for_anova else None),
            "replicate_set_consistent": replicate_set_consistent,
            "duplicate_replicates_per_cell": duplicate_replicates_per_cell,
            "cell_replicate_count_distribution": cell_replicate_distribution,
        },
        "issues": issues,
        "next_step": (
            "ready_for_balanced_crossed_anova" if ready_for_anova else "fix_design_before_gage_rr"
        ),
    }


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip() == ""


def _identifier_value(value: str | None) -> str:
    if value is None:
        raise GageRrPreflightError("gage_rr_identifier_missing")
    stripped = value.strip()
    if stripped == "":
        raise GageRrPreflightError("gage_rr_identifier_missing")
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


def _cell_replicate_distribution(replicate_counts: Sequence[int]) -> list[dict[str, int]]:
    distribution = Counter(replicate_counts)
    return [
        {"replicate_count": replicate_count, "cell_count": distribution[replicate_count]}
        for replicate_count in sorted(distribution)
    ]


def _design_issues(
    *,
    n_used: int,
    part_count: int,
    operator_count: int,
    replicate_level_count: int,
    missing_cell_count: int,
    min_replicates_per_cell: int,
    max_replicates_per_cell: int,
    replicate_set_consistent: bool,
    duplicate_replicates_per_cell: int,
    n_excluded_missing_measurement: int,
    n_excluded_non_numeric_measurement: int,
    n_excluded_missing_identifier: int,
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = [
        _issue(
            "gage_rr_preflight_only_no_variance_components",
            "info",
            "이번 단계는 Gage R&R 계산 전 설계 사전점검만 수행하며 ANOVA table, "
            "분산성분, %GRR, ndc를 계산하지 않습니다.",
        ),
        _issue(
            "gage_rr_requires_balanced_crossed_design",
            "info",
            "첫 Gage R&R 계산 slice는 balanced crossed ANOVA 설계만 지원할 예정입니다.",
        ),
        _issue(
            "gage_rr_independence_not_proven",
            "info",
            "부품 선정, 측정자 독립성, 반복 측정 순서는 소프트웨어가 증명할 수 없습니다.",
        ),
        _issue(
            "gage_rr_labels_redacted",
            "info",
            "사전점검 응답은 로컬 식별값의 원문을 노출하지 않고 count와 설계 상태만 반환합니다.",
        ),
    ]
    if n_used == 0:
        issues.append(
            _issue(
                "gage_rr_no_usable_measurements",
                "error",
                "Gage R&R 사전점검에 사용할 수 있는 측정 행이 없습니다.",
                n_used,
            ),
        )
    if part_count < 2:
        issues.append(
            _issue(
                "gage_rr_part_count_too_small",
                "error",
                "Gage R&R에는 최소 2개 부품이 필요합니다.",
                part_count,
            ),
        )
    if operator_count < 2:
        issues.append(
            _issue(
                "gage_rr_operator_count_too_small",
                "error",
                "Gage R&R에는 최소 2명 이상의 측정자가 필요합니다.",
                operator_count,
            ),
        )
    if replicate_level_count < 2 or min_replicates_per_cell < 2:
        issues.append(
            _issue(
                "gage_rr_replicate_count_too_small",
                "error",
                "각 부품-측정자 조합에는 최소 2회 반복 측정이 필요합니다.",
                min_replicates_per_cell,
            ),
        )
    if missing_cell_count > 0:
        issues.append(
            _issue(
                "gage_rr_crossed_cells_missing",
                "error",
                "일부 부품-측정자 조합이 없어 crossed 설계가 완전하지 않습니다.",
                missing_cell_count,
            ),
        )
    if min_replicates_per_cell != max_replicates_per_cell or not replicate_set_consistent:
        issues.append(
            _issue(
                "gage_rr_unbalanced_crossed_design",
                "error",
                "부품-측정자 조합별 반복 수 또는 반복 ID 집합이 일치하지 않습니다.",
            ),
        )
    if duplicate_replicates_per_cell > 0:
        issues.append(
            _issue(
                "gage_rr_duplicate_replicates_per_cell",
                "error",
                "같은 부품-측정자 조합 안에 중복 반복 ID가 있습니다.",
                duplicate_replicates_per_cell,
            ),
        )
    if n_excluded_missing_measurement > 0:
        issues.append(
            _issue(
                "missing_values_excluded",
                "warning",
                "측정값 결측 행은 complete-case 정책으로 제외했습니다.",
                n_excluded_missing_measurement,
            ),
        )
    if n_excluded_non_numeric_measurement > 0:
        issues.append(
            _issue(
                "non_numeric_values_excluded",
                "warning",
                "숫자로 해석할 수 없는 측정값은 제외했습니다.",
                n_excluded_non_numeric_measurement,
            ),
        )
    if n_excluded_missing_identifier > 0:
        issues.append(
            _issue(
                "gage_rr_identifier_missing_excluded",
                "warning",
                "부품, 측정자, 반복 ID 결측 행은 complete-case 정책으로 제외했습니다.",
                n_excluded_missing_identifier,
            ),
        )
    return issues


def _issue(
    code: str,
    severity: str,
    message: str,
    count: int | None = None,
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "count": count,
    }


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
