"""Small, escaped projections of stored inference results; no calculations or I/O."""

from collections.abc import Sequence
from html import escape
from math import isfinite

from app.services.report_contract import ReportSection
from app.services.report_warnings import report_warning_text
from app.services.stored_report_primitives import report_column_label, report_table

Field = tuple[str, str, str]
INVALID = "analysis_report_payload_invalid"


def text(locale: str, ko: str, en: str) -> str:
    return ko if locale == "ko" else en


def stored_object(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(INVALID)
    return value


def stored_rows(value: object) -> list[dict[str, object]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(INVALID)
    rows = []
    for item in value:
        row = stored_object(item)
        if row is None:
            raise ValueError(INVALID)
        rows.append(row)
    return rows


def finite_fields(value: dict[str, object], keys: Sequence[str]) -> bool:
    for key in keys:
        if key not in value or value[key] is None:
            return False
        item = value[key]
        if isinstance(item, bool) or not isinstance(item, float | int) or not isfinite(item):
            raise ValueError(INVALID)
    return True


def scalar(value: object, locale: str) -> object:
    if isinstance(value, bool):
        return text(locale, "예", "Yes") if value else text(locale, "아니요", "No")
    if isinstance(value, list | dict):
        raise ValueError(INVALID)
    if isinstance(value, int | float) and not isfinite(value):
        raise ValueError(INVALID)
    return value


def fields_table(value: dict[str, object], fields: Sequence[Field], locale: str) -> str:
    rows = [
        (text(locale, ko, en), scalar(value[key], locale)) for key, ko, en in fields if key in value
    ]
    return (
        report_table([text(locale, "항목", "Item"), text(locale, "저장값", "Stored value")], rows)
        if rows
        else ""
    )


def rows_table(rows: Sequence[dict[str, object]], fields: Sequence[Field], locale: str) -> str:
    selected = [(key, ko, en) for key, ko, en in fields if any(key in row for row in rows)]
    return (
        report_table(
            [text(locale, ko, en) for _, ko, en in selected],
            [[scalar(row.get(key), locale) for key, _, _ in selected] for row in rows],
        )
        if rows and selected
        else ""
    )


def section(section_id: str, ko: str, en: str, markup: str, locale: str) -> ReportSection:
    return (
        ReportSection(section_id, text(locale, ko, en), "rendered", markup=markup)
        if markup
        else missing(section_id, ko, en, locale)
    )


def missing(
    section_id: str,
    ko: str,
    en: str,
    locale: str,
    *,
    reason: str = "not_stored",
    applicable: bool = True,
) -> ReportSection:
    return ReportSection(
        section_id,
        text(locale, ko, en),
        "missing" if applicable else "not_applicable",
        reason=reason,
    )


def paragraph(ko: str, en: str, locale: str) -> str:
    return f"<p>{escape(text(locale, ko, en))}</p>"


SETTINGS_FIELDS: tuple[Field, ...] = (
    ("method", "방법", "Method"),
    ("design", "연구 설계", "Design"),
    ("input_mode", "입력 방식", "Input mode"),
    ("input_layout", "입력 배치", "Input layout"),
    ("missing_policy", "결측 처리", "Missing-data policy"),
    ("n_total", "전체 행 수", "Total rows"),
    ("n_used", "사용 행 수", "Used rows"),
    ("n_missing", "결측 제외 행 수", "Missing rows"),
    ("n_non_numeric", "비수치 제외 행 수", "Non-numeric rows"),
    ("n_incomplete_pairs", "불완전 쌍 수", "Incomplete pairs"),
    ("n_complete_pairs", "완전 쌍 수", "Complete pairs"),
    ("n_missing_before", "이전 측정 결측", "Missing before"),
    ("n_missing_after", "이후 측정 결측", "Missing after"),
    ("n_non_numeric_before", "이전 측정 비수치", "Non-numeric before"),
    ("n_non_numeric_after", "이후 측정 비수치", "Non-numeric after"),
    ("n_non_numeric_pairs", "비수치 쌍 수", "Non-numeric pairs"),
    ("n_missing_test", "검정 측정 결측", "Missing test measurement"),
    ("n_missing_reference", "기준 측정 결측", "Missing reference measurement"),
    ("n_missing_response", "반응 결측", "Missing response"),
    ("n_missing_group", "그룹 결측", "Missing group"),
    ("n_excluded_missing_response", "반응 결측 제외", "Excluded: missing response"),
    ("n_excluded_non_numeric_response", "반응 비수치 제외", "Excluded: non-numeric response"),
    ("n_excluded_missing_group", "그룹 결측 제외", "Excluded: missing group"),
    ("n_excluded_unselected_groups", "미선택 그룹 제외", "Excluded: unselected groups"),
    ("n_excluded_missing_row", "행 변수 결측 제외", "Excluded: missing row variable"),
    ("n_excluded_missing_column", "열 변수 결측 제외", "Excluded: missing column variable"),
    ("alpha", "유의수준", "Alpha"),
    ("confidence_level", "신뢰수준", "Confidence level"),
    ("alternative", "대립가설", "Alternative"),
    ("null_mean", "귀무 평균", "Null mean"),
    ("null_difference", "귀무 차이", "Null difference"),
    ("null_location", "귀무 위치", "Null location"),
    ("null_proportion", "귀무 비율", "Null proportion"),
    ("event_level", "사건 수준", "Event level"),
    ("reference_mean", "기준 평균", "Reference mean"),
    ("estimate_definition", "추정량 정의", "Estimate definition"),
    ("difference_definition", "차이 방향", "Difference definition"),
    ("variance_assumption", "분산 가정", "Variance assumption"),
    ("variance_model", "분산 모형", "Variance model"),
    ("anova_type", "ANOVA 유형", "ANOVA type"),
    ("posthoc_method", "사후검정 방법", "Post-hoc method"),
    ("posthoc_policy", "사후검정 실행 정책", "Post-hoc policy"),
    ("control_group_label", "대조군", "Control group"),
    ("dunnett_rng_seed", "Dunnett 난수 시드", "Dunnett random seed"),
    ("requested_method", "요청 계산 방법", "Requested calculation method"),
    ("resolved_method", "적용 계산 방법", "Resolved calculation method"),
    ("zero_method", "영차이 처리", "Zero-difference policy"),
    ("use_continuity", "연속성 보정", "Continuity correction"),
    ("correction", "연속성 보정", "Continuity correction"),
    ("ci_method", "구간 방법", "Interval method"),
    ("group_count", "그룹 수", "Group count"),
)


def settings(result: dict[str, object], locale: str) -> ReportSection:
    valid = finite_fields(result, ("n_total", "n_used", "alpha")) and isinstance(
        result.get("method"), str
    )
    markup = fields_table(result, SETTINGS_FIELDS, locale) if valid else ""
    if markup:
        columns = []
        for key, ko, en in (
            ("response", "반응", "Response"),
            ("group", "그룹", "Group"),
            ("before", "이전 측정", "Before"),
            ("after", "이후 측정", "After"),
            ("test_column", "검정 측정", "Test measurement"),
            ("reference_column", "기준 측정", "Reference measurement"),
            ("row_variable", "행 변수", "Row variable"),
            ("column_variable", "열 변수", "Column variable"),
        ):
            column = stored_object(result.get(key))
            if column:
                columns.append(
                    (
                        text(locale, ko, en),
                        report_column_label(column, key),
                        column.get("column_id"),
                    )
                )
        if columns:
            markup += report_table(
                [
                    text(locale, "역할", "Role"),
                    text(locale, "변수 (단위)", "Variable (unit)"),
                    "column_id",
                ],
                columns,
            )
        versions = stored_object(result.get("package_versions"))
        if versions:
            markup += report_table(
                [text(locale, "패키지", "Package"), text(locale, "버전", "Version")],
                [(key, scalar(value, locale)) for key, value in versions.items()],
            )
    return section("settings", "입력 및 설정", "Inputs and settings", markup, locale)


def warnings_section(result: dict[str, object], locale: str) -> ReportSection:
    if "warnings" not in result:
        return missing("warnings", "경고", "Warnings", locale)
    warnings = result["warnings"]
    if not isinstance(warnings, list):
        raise ValueError(INVALID)
    sources: list[tuple[str, list[object]]] = [("result", warnings)]
    for key in ("sample", "paired_sample"):
        sample = stored_object(result.get(key))
        if sample and "warnings" in sample:
            value = sample["warnings"]
            if not isinstance(value, list):
                raise ValueError(INVALID)
            sources.append((key, value))
    for group in stored_rows(result.get("groups")) or []:
        if "warnings" in group:
            value = group["warnings"]
            if not isinstance(value, list):
                raise ValueError(INVALID)
            sources.append((str(group.get("group_label", "group")), value))
    samples = result.get("samples")
    if isinstance(samples, dict):
        for key, value in samples.items():
            sample = stored_object(value)
            if sample and "warnings" in sample:
                value = sample["warnings"]
                if not isinstance(value, list):
                    raise ValueError(INVALID)
                sources.append((str(key), value))
    rows: list[tuple[str, str, object]] = []
    for context, source in sources:
        for warning in source:
            if isinstance(warning, str):
                rows.append((context, warning, report_warning_text(warning, "", locale)))
            elif isinstance(warning, dict) and isinstance(warning.get("code"), str):
                message = warning.get("message", "")
                if not isinstance(message, str):
                    raise ValueError(INVALID)
                rows.append(
                    (
                        context,
                        warning["code"],
                        report_warning_text(warning["code"], message, locale),
                    )
                )
            else:
                raise ValueError(INVALID)
    markup = (
        report_table(
            [
                text(locale, "대상", "Context"),
                text(locale, "경고 코드", "Warning code"),
                text(locale, "경고 내용", "Warning message"),
            ],
            rows,
        )
        if rows
        else paragraph("저장된 경고 없음.", "No stored warnings.", locale)
    )
    return section("warnings", "경고", "Warnings", markup, locale)


def interval_table(interval: dict[str, object], locale: str) -> str:
    if not finite_fields(interval, ("level",)) or not all(
        key in interval for key in ("lower", "upper")
    ):
        return ""
    lower, upper = interval["lower"], interval["upper"]
    if lower is None and upper is None:
        raise ValueError(INVALID)
    for value in (lower, upper):
        if value is not None:
            scalar(value, locale)
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError(INVALID)
    rows = [
        [
            interval.get("method", "-"),
            interval["level"],
            lower if lower is not None else text(locale, "하한 없음", "Unbounded below"),
            upper if upper is not None else text(locale, "상한 없음", "Unbounded above"),
        ]
    ]
    return report_table(
        [
            text(locale, "구간 방법", "Interval method"),
            text(locale, "신뢰수준", "Confidence level"),
            text(locale, "하한", "Lower"),
            text(locale, "상한", "Upper"),
        ],
        rows,
    )
