"""Section-aware EDA reports; chart callbacks only project already stored values."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html import escape

from app.i18n.report_text import ReportLocale
from app.services.inference_report_primitives import (
    Field,
    fields_table,
    finite_fields,
    missing,
    paragraph,
    rows_table,
    scalar,
    section,
    stored_object,
    stored_rows,
    text,
)
from app.services.report_contract import (
    ReportBody,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
)
from app.services.report_warnings import report_warning_text
from app.services.stored_report_primitives import (
    report_column_label,
    report_number,
    report_plot,
    report_table,
)

PlotRenderer = Callable[[dict[object, object], ReportLocale], str]


@dataclass(frozen=True)
class BasicEdaPlotRenderers:
    histogram: PlotRenderer | None = None
    boxplot: PlotRenderer | None = None
    confidence_intervals: PlotRenderer | None = None
    variance_intervals: PlotRenderer | None = None


_NO_PLOTS = BasicEdaPlotRenderers()


def _variant(
    name: str, core: tuple[str, ...], optional: tuple[str, ...]
) -> ReportVariantDefinition:
    return ReportVariantDefinition(
        name,
        tuple(ReportSectionDefinition(key, True) for key in ("settings", *core))
        + tuple(ReportSectionDefinition(key) for key in (*optional, "warnings", "interpretation")),
    )


BASIC_EDA_REPORT_VARIANTS_BY_METHOD: dict[str, tuple[ReportVariantDefinition, ...]] = {
    "eda.descriptive": tuple(
        _variant(f"descriptive_v{schema}", ("summary",), ("distribution_summary",))
        for schema in (1, 2)
    ),
    "eda.graphical_summary": tuple(
        _variant(
            f"graphical_v{schema}",
            ("summary",),
            (
                "moments",
                "histogram",
                "normal_fit",
                "boxplot",
                "qq_plot",
                "ecdf",
                "normality",
                "confidence_intervals",
            ),
        )
        for schema in (1, 2)
    ),
    "eda.equal_variances": tuple(
        _variant(
            f"equal_variances_v{schema}",
            ("groups", "tests"),
            (
                "multiple_summary",
                "comparison_intervals",
                "pairwise",
                "non_overlap",
                "additional_tests",
            ),
        )
        for schema in (1, 2)
    ),
}
_SETTINGS: tuple[Field, ...] = (
    ("schema_version", "저장 스키마", "Stored schema"),
    ("missing_policy", "결측 정책", "Missing-data policy"),
    ("quartile_method", "사분위수 방법", "Quartile method"),
    ("quantile_position", "분위수 위치", "Quantile position"),
    ("std_definition", "표준편차 정의", "SD definition"),
    ("histogram_method", "히스토그램 방법", "Histogram method"),
    ("boxplot_method", "박스플롯 방법", "Boxplot method"),
    ("qq_plot_distribution", "Q-Q 기준 분포", "Q-Q reference distribution"),
    ("qq_plotting_position", "Q-Q 위치", "Q-Q plotting position"),
    ("ecdf_method", "ECDF 방법", "ECDF method"),
    ("point_limit", "저장 점 한도", "Stored point limit"),
    ("confidence_level", "신뢰수준", "Confidence level"),
    ("alpha", "유의수준", "Alpha"),
    ("n_total", "전체 N", "Total N"),
    ("n_used", "사용 N", "Used N"),
    ("n_excluded_missing_response", "반응 결측 제외", "Excluded: missing response"),
    ("n_excluded_missing_group", "그룹 결측 제외", "Excluded: missing group"),
    ("n_excluded_non_numeric_response", "비수치 반응 제외", "Excluded: non-numeric response"),
    ("group_count", "그룹 수", "Group count"),
)
_SUMMARY: tuple[Field, ...] = (
    ("label", "변수 (단위)", "Variable (unit)"),
    ("column_id", "열 ID", "Column ID"),
    ("n_total", "전체 N", "Total N"),
    ("n_used", "사용 N", "Used N"),
    ("n_missing", "결측 N", "Missing N"),
    ("n_non_numeric", "비수치 N", "Non-numeric N"),
    ("mean", "평균", "Mean"),
    ("std", "표본 표준편차", "Sample SD"),
    ("standard_deviation", "표본 표준편차", "Sample SD"),
    ("min", "최솟값", "Minimum"),
    ("q1", "제1사분위수", "Q1"),
    ("median", "중앙값", "Median"),
    ("q3", "제3사분위수", "Q3"),
    ("max", "최댓값", "Maximum"),
)


def _complete(rows: Sequence[dict[str, object]], keys: Sequence[str]) -> bool:
    return bool(rows) and all(all(key in row for key in keys) for row in rows)


def _heading(column: dict[str, object], locale: str) -> str:
    return f"<h4>{escape(report_column_label(column, text(locale, '변수', 'Variable')))}</h4>"


def _warnings(
    result: dict[str, object], columns: Sequence[dict[str, object]], locale: str
) -> ReportSection:
    sources = [("result", result)] if "warnings" in result else []
    sources += [
        (str(row.get("display_name", row.get("group_label", "group"))), row) for row in columns
    ]
    for key in ("tests", "additional_tests"):
        sources += [
            (str(row.get("method", key)), row) for row in stored_rows(result.get(key)) or []
        ]
    multiple = stored_object(result.get("multiple_comparisons"))
    if multiple:
        sources.append(("multiple_comparisons", multiple))
    rows = []
    for context, source in sources:
        values = source.get("warnings")
        if not isinstance(values, list):
            return missing("warnings", "경고", "Warnings", locale)
        for code in values:
            if not isinstance(code, str):
                raise ValueError("analysis_report_payload_invalid")
            rows.append((context, code, report_warning_text(code, "", locale)))
    markup = (
        report_table(
            [
                text(locale, "대상", "Context"),
                text(locale, "코드", "Code"),
                text(locale, "내용", "Message"),
            ],
            rows,
        )
        if rows
        else paragraph("저장된 경고 없음.", "No stored warnings.", locale)
        if sources
        else ""
    )
    return section("warnings", "경고", "Warnings", markup, locale)


def _settings(result: dict[str, object], summary: str, locale: str) -> ReportSection:
    required = (
        ("missing_policy", "quartile_method", "std_definition")
        if summary == "descriptive_statistics"
        else (
            "histogram_method",
            "boxplot_method",
            "qq_plot_distribution",
            "ecdf_method",
            "point_limit",
        )
        if summary == "graphical_summary"
        else ("missing_policy", "alpha", "n_total", "n_used")
    )
    markup = (
        fields_table(result, _SETTINGS, locale) if all(key in result for key in required) else ""
    )
    for key in ("response", "group"):
        column = stored_object(result.get(key))
        if markup and column:
            markup += report_table(
                [
                    text(locale, "역할", "Role"),
                    text(locale, "변수 (단위)", "Variable (unit)"),
                    "column_id",
                ],
                [(key, report_column_label(column, key), column.get("column_id"))],
            )
    versions = stored_object(result.get("package_versions"))
    if markup and versions:
        markup += report_table(
            [text(locale, "패키지", "Package"), text(locale, "버전", "Version")],
            [(key, scalar(value, locale)) for key, value in versions.items()],
        )
    return section(
        "settings", "입력 및 계산 정의", "Inputs and calculation definitions", markup, locale
    )


def _column_objects(result: dict[str, object]) -> list[dict[str, object]]:
    return [
        {**row, "label": report_column_label(row, "column")}
        for row in stored_rows(result.get("columns")) or []
    ]


def _graphical_plots(
    columns: list[dict[str, object]], locale: ReportLocale, plots: BasicEdaPlotRenderers
) -> list[ReportSection]:
    sections: list[ReportSection] = []
    for key, ko, en, callback in (
        (
            "histogram",
            "히스토그램과 저장 정규 적합",
            "Histogram and stored normal fit",
            plots.histogram,
        ),
        ("boxplot", "박스플롯", "Boxplot", plots.boxplot),
        (
            "confidence_intervals",
            "저장 신뢰구간",
            "Stored confidence intervals",
            plots.confidence_intervals,
        ),
    ):
        parts = []
        complete = bool(columns)
        for column in columns:
            source = stored_object(column.get(key))
            if source is None:
                complete = False
                continue
            if key == "histogram":
                bins = stored_rows(source.get("bins"))
                valid = (
                    bins is not None
                    and _complete([source], ("binning", "bin_count"))
                    and all(
                        finite_fields(item, ("lower", "upper", "count"))
                        and _complete([item], ("include_lower", "include_upper"))
                        for item in bins
                    )
                )
                if valid and source["bin_count"] != len(bins or []):
                    raise ValueError("analysis_report_payload_invalid")
                values = bins or []
                rows = rows_table(
                    values,
                    (
                        ("lower", "하한", "Lower"),
                        ("upper", "상한", "Upper"),
                        ("count", "빈도", "Count"),
                        ("include_lower", "하한 포함", "Includes lower"),
                        ("include_upper", "상한 포함", "Includes upper"),
                    ),
                    locale,
                )
            elif key == "boxplot":
                valid = all(
                    field in source
                    for field in (
                        "lower_whisker",
                        "q1",
                        "median",
                        "q3",
                        "upper_whisker",
                        "lower_fence",
                        "upper_fence",
                        "outlier_count",
                    )
                )
                rows = fields_table(
                    source,
                    tuple(
                        (field, ko_label, en_label)
                        for field, ko_label, en_label in (
                            ("lower_whisker", "하단 수염", "Lower whisker"),
                            ("q1", "제1사분위수", "Q1"),
                            ("median", "중앙값", "Median"),
                            ("q3", "제3사분위수", "Q3"),
                            ("upper_whisker", "상단 수염", "Upper whisker"),
                            ("lower_fence", "하단 울타리", "Lower fence"),
                            ("upper_fence", "상단 울타리", "Upper fence"),
                            ("outlier_count", "이상치 수", "Outlier count"),
                        )
                    ),
                    locale,
                )
            else:
                intervals = []
                valid = True
                for field in ("mean", "median", "standard_deviation"):
                    interval = stored_object(source.get(field))
                    if not interval or not all(
                        name in interval
                        for name in (
                            "computed",
                            "method",
                            "confidence_level",
                            "estimate",
                            "lower",
                            "upper",
                        )
                    ):
                        valid = False
                    else:
                        if type(interval["computed"]) is not bool:
                            raise ValueError("analysis_report_payload_invalid")
                        if interval["computed"] and not finite_fields(
                            interval, ("confidence_level", "estimate", "lower", "upper")
                        ):
                            valid = False
                        intervals.append({"quantity": field, **interval})
                rows = rows_table(
                    intervals,
                    (
                        ("quantity", "추정 대상", "Quantity"),
                        ("computed", "계산 여부", "Computed"),
                        ("method", "방법", "Method"),
                        ("confidence_level", "신뢰수준", "Confidence level"),
                        ("estimate", "추정량", "Estimate"),
                        ("lower", "하한", "Lower"),
                        ("upper", "상한", "Upper"),
                    ),
                    locale,
                )
            if not valid:
                complete = False
                continue
            callback_column: dict[object, object] = {key: value for key, value in column.items()}
            rendered = callback(callback_column, locale) if callback else ""
            if not rendered:
                complete = False
            axes = (
                report_table(
                    [text(locale, "축", "Axis"), text(locale, "저장값 의미", "Stored quantity")],
                    [
                        ("X", report_column_label(column, "column")),
                        ("Y", text(locale, "빈도", "Frequency")),
                    ],
                )
                if key == "histogram"
                else ""
            )
            parts.append(_heading(column, locale) + rows + axes + rendered)
        sections.append(section(key, ko, en, "".join(parts) if complete else "", locale))
    for key, ko, en, x_key, y_key in (
        ("qq_plot", "Q-Q 그래프", "Q-Q plot", "theoretical", "sample"),
        ("ecdf", "경험적 누적분포", "Empirical cumulative distribution", "x", "probability"),
    ):
        parts = []
        complete = bool(columns)
        for column in columns:
            source = stored_object(column.get(key))
            points = stored_rows(source.get("points")) if source else None
            if (
                source is None
                or points is None
                or not all(field in source for field in ("point_count", "points_truncated"))
            ):
                complete = False
                continue
            plot_values = [
                (report_number(point.get(x_key)), report_number(point.get(y_key)), str(index + 1))
                for index, point in enumerate(points)
            ]
            if source["point_count"] != len(points):
                raise ValueError("analysis_report_payload_invalid")
            label = report_column_label(column, "column")
            parts.append(
                _heading(column, locale)
                + fields_table(
                    {"n_used": column.get("n_used"), **source},
                    (
                        ("n_used", "계산 N", "Calculation N"),
                        ("point_count", "저장 표시 점 수", "Stored displayed points"),
                        ("points_truncated", "표시 제한", "Display limited"),
                    ),
                    locale,
                )
            )
            parts.append(
                report_plot(
                    text(locale, ko, en),
                    text(locale, "표준정규 이론 분위수", "Theoretical standard-normal quantile")
                    if key == "qq_plot"
                    else label,
                    label
                    if key == "qq_plot"
                    else text(locale, "누적확률", "Cumulative probability"),
                    [(label, plot_values)],
                )
                if plot_values
                else paragraph(
                    "사용 가능한 저장 점이 없습니다.",
                    "No usable stored points are available.",
                    locale,
                )
            )
        sections.append(section(key, ko, en, "".join(parts) if complete else "", locale))
    return sections


def _graphical_extra(columns: list[dict[str, object]], locale: str) -> list[ReportSection]:
    moments = ("mean", "standard_deviation", "variance", "skewness", "kurtosis_excess")
    sections = [
        section(
            "moments",
            "추가 기술통계",
            "Additional descriptive statistics",
            rows_table(
                columns,
                (
                    ("label", "변수", "Variable"),
                    ("mean", "평균", "Mean"),
                    ("standard_deviation", "표준편차", "Standard deviation"),
                    ("variance", "분산", "Variance"),
                    ("skewness", "왜도", "Skewness"),
                    ("kurtosis_excess", "초과 첨도", "Excess kurtosis"),
                ),
                locale,
            )
            if _complete(columns, moments)
            else "",
            locale,
        )
    ]
    for key, ko, en, fields in (
        (
            "normal_fit_curve",
            "저장 정규 적합",
            "Stored normal fit",
            (
                ("computed", "계산 여부", "Computed"),
                ("scale", "척도", "Scale"),
                ("mean", "평균", "Mean"),
                ("standard_deviation", "표준편차", "Standard deviation"),
                ("bin_width", "구간 너비", "Bin width"),
            ),
        ),
        (
            "anderson_darling",
            "Anderson-Darling 검정",
            "Anderson-Darling test",
            (
                ("computed", "계산 여부", "Computed"),
                ("statistic", "A²", "A-squared"),
                ("adjusted_statistic", "수정 A²", "Adjusted A-squared"),
                ("p_value", "p값", "P value"),
                ("p_value_is_approximate", "근사 p값", "Approximate P value"),
                ("p_value_method", "p값 방법", "P-value method"),
            ),
        ),
    ):
        parts = []
        complete = bool(columns)
        for column in columns:
            source = stored_object(column.get(key))
            if not source or not isinstance(source.get("computed"), bool):
                complete = False
                continue
            required = (
                ("scale", "points")
                if key == "normal_fit_curve"
                else (
                    "statistic",
                    "adjusted_statistic",
                    "p_value",
                    "p_value_method",
                    "p_value_is_approximate",
                    "critical_values",
                    "decision_at_alpha",
                )
            )
            if not _complete([source], required):
                complete = False
                continue
            if source["computed"] and not finite_fields(
                source,
                ("mean", "standard_deviation", "bin_width")
                if key == "normal_fit_curve"
                else ("statistic", "adjusted_statistic", "p_value"),
            ):
                complete = False
                continue
            parts.append(_heading(column, locale) + fields_table(source, fields, locale))
            if key == "normal_fit_curve":
                points = stored_rows(source.get("points"))
                if points is None or not all(
                    finite_fields(point, ("x", "expected_count")) for point in points
                ):
                    complete = False
                else:
                    parts.append(
                        rows_table(
                            points,
                            (
                                ("x", "측정값", "Measurement"),
                                ("expected_count", "적합 기대 빈도", "Fitted expected count"),
                            ),
                            locale,
                        )
                    )
            else:
                critical = stored_rows(source.get("critical_values"))
                if critical is not None and any(
                    not finite_fields(item, ("significance_level", "critical_value"))
                    or "reject_normality" not in item
                    for item in critical
                ):
                    complete = False
                if critical:
                    parts.append(
                        rows_table(
                            critical,
                            (
                                (
                                    "significance_level",
                                    "유의수준 (비율)",
                                    "Significance level (proportion)",
                                ),
                                ("critical_value", "임계값", "Critical value"),
                                ("reject_normality", "정규성 기각", "Reject normality"),
                            ),
                            locale,
                        )
                    )
                decision = stored_object(source.get("decision_at_alpha"))
                if decision:
                    parts.append(
                        fields_table(
                            decision,
                            (
                                ("alpha", "유의수준", "Alpha"),
                                ("critical_value", "임계값", "Critical value"),
                                ("reject_normality", "정규성 기각", "Reject normality"),
                                ("method", "방법", "Method"),
                            ),
                            locale,
                        )
                    )
        sections.append(
            section(
                "normal_fit" if key == "normal_fit_curve" else "normality",
                ko,
                en,
                "".join(parts) if complete else "",
                locale,
            )
        )
    return sections


_TESTS: tuple[Field, ...] = (
    ("method", "방법", "Method"),
    ("center", "중심", "Center"),
    ("computed", "계산 여부", "Computed"),
    ("statistic", "통계량", "Statistic"),
    ("p_value", "p값", "P value"),
    ("alpha", "유의수준", "Alpha"),
    ("reject_equal_variances", "등분산 기각", "Reject equal variances"),
    ("valid_group_n_min", "그룹 최소 N", "Minimum group N"),
)


def _equal_variances(
    result: dict[str, object], locale: ReportLocale, plots: BasicEdaPlotRenderers
) -> tuple[list[ReportSection], list[dict[str, object]]]:
    groups = stored_rows(result.get("groups")) or []
    group_keys = ("group_label", "n", "mean", "median", "variance", "std", "min", "max")
    group_fields: tuple[Field, ...] = (
        ("group_label", "그룹", "Group"),
        ("n", "N", "N"),
        ("mean", "평균", "Mean"),
        ("median", "중앙값", "Median"),
        ("variance", "분산", "Variance"),
        ("std", "표준편차", "Standard deviation"),
        ("min", "최솟값", "Minimum"),
        ("max", "최댓값", "Maximum"),
    )
    sections = [
        section(
            "groups",
            "그룹 요약",
            "Group summaries",
            rows_table(groups, group_fields, locale) if _complete(groups, group_keys) else "",
            locale,
        )
    ]
    tests = stored_rows(result.get("tests")) or []
    sections.append(
        section(
            "tests",
            "등분산 검정",
            "Equal-variance tests",
            rows_table(tests, _TESTS, locale)
            if _complete(
                tests,
                ("method", "computed", "statistic", "p_value", "alpha", "reject_equal_variances"),
            )
            else "",
            locale,
        )
    )
    additional = stored_rows(result.get("additional_tests"))
    sections.append(
        section(
            "additional_tests",
            "추가 검정",
            "Additional tests",
            rows_table(additional, _TESTS, locale)
            if additional and _complete(additional, ("method", "computed", "statistic", "p_value"))
            else paragraph("저장된 추가 검정 없음.", "No additional test is stored.", locale)
            if additional == []
            else "",
            locale,
        )
    )
    multiple = stored_object(result.get("multiple_comparisons"))
    sections.append(
        section(
            "multiple_summary",
            "다중 비교 설정과 결과",
            "Multiple-comparison settings and result",
            fields_table(
                multiple,
                (
                    ("computed", "계산 여부", "Computed"),
                    ("method", "방법", "Method"),
                    ("alpha", "유의수준", "Alpha"),
                    ("p_value", "p값", "P value"),
                    ("reject_equal_variances", "등분산 기각", "Reject equal variances"),
                ),
                locale,
            )
            if multiple
            and _complete(
                [multiple], ("computed", "method", "alpha", "p_value", "reject_equal_variances")
            )
            else "",
            locale,
        )
    )
    intervals = []
    comparison_groups = stored_rows(multiple.get("groups")) if multiple else None
    complete = comparison_groups is not None and len(comparison_groups) == len(groups)
    for group in comparison_groups or []:
        ci = stored_object(group.get("comparison_interval"))
        if (
            not ci
            or not finite_fields(ci, ("lower", "upper"))
            or not finite_fields(group, ("sample_standard_deviation", "allocation", "n"))
        ):
            complete = False
        else:
            intervals.append({**group, **ci})
    markup = ""
    if multiple and multiple.get("computed") is False:
        markup = paragraph(
            "다중 비교구간을 계산하지 못했습니다. 저장된 경고를 확인하세요.",
            "Multiple-comparison intervals were not computed. Review the stored warnings.",
            locale,
        )
    elif complete and intervals:
        markup = rows_table(
            intervals,
            (
                ("group_label", "그룹", "Group"),
                ("n", "N", "N"),
                ("sample_standard_deviation", "표본 표준편차", "Sample SD"),
                ("lower", "비교구간 하한", "Comparison lower"),
                ("upper", "비교구간 상한", "Comparison upper"),
                ("allocation", "할당", "Allocation"),
            ),
            locale,
        )
        callback_multiple: dict[object, object] = {
            key: value for key, value in (multiple or {}).items()
        }
        markup += (
            plots.variance_intervals(callback_multiple, locale)
            if plots.variance_intervals and multiple
            else ""
        )
        if not plots.variance_intervals:
            markup = ""
    sections.append(
        section(
            "comparison_intervals",
            "표준편차 다중 비교구간",
            "Standard-deviation multiple-comparison intervals",
            markup,
            locale,
        )
    )
    for key, section_id, ko, en, fields in (
        (
            "pairwise_p_values",
            "pairwise",
            "쌍별 보정 p값",
            "Pairwise adjusted P values",
            (
                ("left_group", "그룹 1", "Group 1"),
                ("right_group", "그룹 2", "Group 2"),
                ("p_value", "보정 p값", "Adjusted P value"),
            ),
        ),
        (
            "non_overlapping_pairs",
            "non_overlap",
            "비중첩 비교구간 쌍",
            "Non-overlapping comparison intervals",
            (("left_group", "그룹 1", "Group 1"), ("right_group", "그룹 2", "Group 2")),
        ),
    ):
        pairs = stored_rows(multiple.get(key)) if multiple else None
        markup = (
            rows_table(pairs, fields, locale)
            if pairs and _complete(pairs, tuple(field[0] for field in fields))
            else paragraph("저장된 해당 쌍 없음.", "No such pairs are stored.", locale)
            if pairs == []
            else ""
        )
        sections.append(section(section_id, ko, en, markup, locale))
    return sections, groups


def render_basic_eda_report(
    result: dict[str, object],
    locale: ReportLocale = "ko",
    *,
    plots: BasicEdaPlotRenderers = _NO_PLOTS,
) -> ReportBody:
    summary, schema = result.get("summary_type"), result.get("schema_version")
    method = {
        "descriptive_statistics": "eda.descriptive",
        "graphical_summary": "eda.graphical_summary",
        "equal_variances_test": "eda.equal_variances",
    }.get(str(summary))
    if method is None or type(schema) is not int or schema not in (1, 2):
        return ReportBody("unsupported", (), "unsupported_result_schema")
    variant = BASIC_EDA_REPORT_VARIANTS_BY_METHOD[method][schema - 1]
    sections = [_settings(result, str(summary), locale)]
    if summary == "equal_variances_test":
        extra, columns = _equal_variances(result, locale, plots)
        sections.extend(extra)
        note = paragraph(
            "다중 비교구간은 그룹 표준편차 비교용이며 모집단 표준편차의 일반 신뢰구간이 아닙니다. "
            "Levene의 중심 선택과 추가 검정을 구분하세요. 비기각은 등분산의 증명이 아닙니다.",
            "Multiple-comparison intervals compare group standard deviations; they are not "
            "ordinary confidence intervals for population SDs. Keep Levene centering and "
            "additional tests distinct. Non-rejection does not prove equal variances.",
            locale,
        )
    else:
        columns = _column_objects(result)
        core_keys = ("column_id", "display_name", "n_total", "n_used", "n_missing", "n_non_numeric")
        sections.append(
            section(
                "summary",
                "변수별 요약",
                "Column summaries",
                rows_table(columns, _SUMMARY, locale) if _complete(columns, core_keys) else "",
                locale,
            )
        )
        if summary == "descriptive_statistics":
            keys = ("mean", "std", "min", "q1", "median", "q3", "max")
            sections.append(
                section(
                    "distribution_summary",
                    "분포 요약",
                    "Distribution summary",
                    rows_table(columns, _SUMMARY, locale) if _complete(columns, keys) else "",
                    locale,
                )
            )
        else:
            sections += _graphical_plots(columns, locale, plots) + _graphical_extra(columns, locale)
        note = paragraph(
            "저장된 요약값과 표시용 점만 사용합니다. 원자료를 다시 읽거나 통계량을 재계산하지 "
            "않습니다. 점 수 제한은 저장된 표시 범위이며 계산 N과 구분합니다.",
            "Only stored summary values and display points are used. Raw data are not reread "
            "and statistics are not recalculated. Stored display-point limits are distinct "
            "from calculation N.",
            locale,
        )
    sections += [
        _warnings(result, columns, locale),
        section(
            "interpretation", "해석 및 저장 범위", "Interpretation and stored scope", note, locale
        ),
    ]
    by_id = {item.section_id: item for item in sections}
    return ReportBody(
        variant.variant_id, tuple(by_id[item.section_id] for item in variant.sections)
    )
