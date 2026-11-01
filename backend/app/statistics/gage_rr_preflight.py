from collections.abc import Iterable, Sequence

from app.statistics.gage_rr_data import (
    GageRrColumn as GageRrColumn,
)
from app.statistics.gage_rr_data import (
    GageRrDataError,
    column_payload,
    prepare_gage_data,
    public_design,
)


class GageRrPreflightError(GageRrDataError):
    pass


def calculate_gage_rr_preflight(
    rows: Iterable[Sequence[str | None]],
    *,
    measurement_column: GageRrColumn,
    part_column: GageRrColumn,
    operator_column: GageRrColumn,
    replicate_column: GageRrColumn | None = None,
    replicate_mode: str | None = None,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
    source_row_numbers: Sequence[int] | None = None,
) -> dict[str, object]:
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
        raise GageRrPreflightError(exc.code) from exc
    design = public_design(prepared.design)
    design["expected_replicates_per_cell"] = design.pop("replicate_count")
    sample = prepared.sample
    issues = _design_issues(
        n_used=sample["n_used"],
        part_count=int(str(design["part_count"])),
        operator_count=int(str(design["operator_count"])),
        min_replicates_per_cell=int(str(design["min_replicates_per_cell"])),
        max_replicates_per_cell=int(str(design["max_replicates_per_cell"])),
        missing_cell_count=int(str(design["missing_cell_count"])),
        duplicate_replicates_per_cell=int(str(design["duplicate_replicates_per_cell"])),
        n_excluded_missing_measurement=sample["n_excluded_missing_measurement"],
        n_excluded_non_numeric_measurement=sample["n_excluded_non_numeric_measurement"],
        n_excluded_missing_identifier=sample["n_excluded_missing_identifier"],
    )
    error_codes = prepared.design["error_codes"]
    assert isinstance(error_codes, list)
    if "gage_rr_zero_total_variation" in error_codes:
        issues.append(
            _issue("gage_rr_zero_total_variation", "error", "측정값의 총 변동이 0입니다.")
        )
    return {
        "schema_version": 2,
        "summary_type": "gage_rr_preflight",
        "method": "balanced_crossed_anova_preflight",
        "missing_policy": missing_policy,
        "replicate_mode": prepared.replicate_mode,
        "columns": {
            "measurement": column_payload(measurement_column),
            "part": column_payload(part_column),
            "operator": column_payload(operator_column),
            "replicate": column_payload(replicate_column),
        },
        "sample": sample,
        "design": design,
        "issues": issues,
        "next_step": "ready_for_balanced_crossed_anova"
        if design["ready_for_anova"]
        else "fix_design_before_gage_rr",
    }


def _design_issues(
    *,
    n_used: int,
    part_count: int,
    operator_count: int,
    missing_cell_count: int,
    min_replicates_per_cell: int,
    max_replicates_per_cell: int,
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
            "Gage R&R은 balanced crossed ANOVA 설계를 지원합니다. "
            "반복측정은 필요하며 별도 반복번호 열은 선택사항입니다.",
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
    if min_replicates_per_cell < 2:
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
    if min_replicates_per_cell != max_replicates_per_cell:
        issues.append(
            _issue(
                "gage_rr_unbalanced_crossed_design",
                "error",
                "부품-측정자 조합별 유효 측정 행 수가 일치하지 않습니다.",
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
