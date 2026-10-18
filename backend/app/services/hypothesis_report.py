"""Method-aware reports from immutable, stored hypothesis-test payloads."""

from app.services.inference_report_primitives import (
    Field,
    fields_table,
    finite_fields,
    interval_table,
    missing,
    paragraph,
    rows_table,
    section,
    settings,
    stored_object,
    stored_rows,
    text,
    warnings_section,
)
from app.services.report_contract import (
    ReportBody,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
)
from app.services.stored_report_primitives import (
    report_column_label,
    report_number,
    report_plot,
    report_table,
)


def _variant(
    name: str, core: tuple[str, ...], optional: tuple[str, ...]
) -> ReportVariantDefinition:
    return ReportVariantDefinition(
        name,
        tuple(ReportSectionDefinition(key, True) for key in ("settings", *core))
        + tuple(ReportSectionDefinition(key) for key in (*optional, "warnings", "interpretation")),
    )


HYPOTHESIS_REPORT_VARIANTS: tuple[ReportVariantDefinition, ...] = (
    *(
        _variant(
            name, ("sample_summary", "test", "estimate_interval"), ("effect_sizes", "interval_plot")
        )
        for name in ("one_sample_t", "paired_t")
    ),
    _variant(
        "two_sample_t", ("groups", "test", "estimate_interval"), ("effect_sizes", "interval_plot")
    ),
    _variant(
        "wilcoxon",
        ("sample_summary", "test"),
        ("rank_details", "effect_sizes", "estimate_interval"),
    ),
    _variant(
        "mann_whitney",
        ("groups", "test"),
        ("sample_inputs", "rank_details", "effect_sizes", "estimate_interval"),
    ),
    _variant(
        "kruskal_wallis",
        ("groups", "test"),
        ("rank_details", "effect_sizes", "posthoc", "estimate_interval"),
    ),
    *(
        _variant(
            name,
            ("groups", "test"),
            ("anova_table", "group_intervals", "effect_sizes", "posthoc", "residual_diagnostics"),
        )
        for name in ("anova_standard", "anova_welch")
    ),
    *(
        _variant(
            name, ("sample_summary", "test", "estimate_interval"), ("effect_sizes", "interval_plot")
        )
        for name in ("tost_one_sample", "tost_two_sample", "tost_paired")
    ),
)

_METHOD_VARIANTS = {
    "hypothesis.one_sample_t": ("one_sample_t",),
    "hypothesis.paired_t": ("paired_t",),
    "hypothesis.two_sample_t": ("two_sample_t",),
    "hypothesis.one_sample_wilcoxon": ("wilcoxon",),
    "hypothesis.mann_whitney": ("mann_whitney",),
    "hypothesis.kruskal_wallis": ("kruskal_wallis",),
    "hypothesis.one_way_anova": ("anova_standard", "anova_welch"),
    "hypothesis.equivalence_tost": ("tost_one_sample",),
    "hypothesis.two_sample_equivalence_tost": ("tost_two_sample",),
    "hypothesis.paired_equivalence_tost": ("tost_paired",),
}
HYPOTHESIS_REPORT_VARIANTS_BY_METHOD = {
    method: tuple(item for item in HYPOTHESIS_REPORT_VARIANTS if item.variant_id in names)
    for method, names in _METHOD_VARIANTS.items()
}

SAMPLE_FIELDS: tuple[Field, ...] = (
    ("group_label", "그룹", "Group"),
    ("sample_label", "표본", "Sample"),
    ("n", "N", "N"),
    ("mean", "평균", "Mean"),
    ("median", "중앙값", "Median"),
    ("variance", "표본 분산", "Sample variance"),
    ("std", "표본 표준편차", "Sample SD"),
    ("sem", "평균 표준오차", "SEM"),
    ("q1", "제1사분위수", "Q1"),
    ("q3", "제3사분위수", "Q3"),
    ("iqr", "사분위범위", "IQR"),
    ("min", "최솟값", "Minimum"),
    ("max", "최댓값", "Maximum"),
    ("before_mean", "이전 측정 평균", "Before mean"),
    ("after_mean", "이후 측정 평균", "After mean"),
    ("mean_difference", "평균 차이", "Mean difference"),
    ("median_difference", "차이의 중앙값", "Median of differences"),
    ("difference_variance", "차이의 표본 분산", "Difference sample variance"),
    ("difference_std", "차이의 표준편차", "Difference SD"),
    ("min_difference", "차이 최솟값", "Minimum difference"),
    ("max_difference", "차이 최댓값", "Maximum difference"),
    ("positive_difference_count", "양의 차이 수", "Positive differences"),
    ("negative_difference_count", "음의 차이 수", "Negative differences"),
    ("zero_difference_count", "영차이 수", "Zero differences"),
    ("rank_sum", "순위합", "Rank sum"),
    ("mean_rank", "평균 순위", "Mean rank"),
)
TEST_FIELDS: tuple[Field, ...] = (
    ("method", "검정 방법", "Test method"),
    ("group_1_label", "그룹 1", "Group 1"),
    ("group_2_label", "그룹 2", "Group 2"),
    ("statistic", "검정통계량", "Statistic"),
    ("w_statistic", "W 통계량", "W statistic"),
    ("u_statistic", "U 통계량", "U statistic"),
    ("u_statistic_group", "U 기준 그룹", "U statistic group"),
    ("h_statistic", "H 통계량", "H statistic"),
    ("f_statistic", "F 통계량", "F statistic"),
    ("df", "자유도", "DF"),
    ("df_numerator", "분자 자유도", "Numerator DF"),
    ("df_denominator", "분모 자유도", "Denominator DF"),
    ("df_between", "집단 간 자유도", "Between-group DF"),
    ("df_within", "집단 내 자유도", "Within-group DF"),
    ("p_value", "p값", "P value"),
    ("reject_null", "귀무가설 기각", "Reject null"),
    ("alternative", "대립가설", "Alternative"),
    ("requested_method", "요청 방법", "Requested method"),
    ("resolved_method", "적용 방법", "Resolved method"),
    ("has_ties", "동점 존재", "Ties present"),
)
EFFECT_FIELDS: tuple[Field, ...] = (
    ("standardizer", "표준화 기준", "Standardizer"),
    ("cohen_dz", "Cohen dz", "Cohen dz"),
    ("cohen_d", "Cohen d", "Cohen d"),
    ("hedges_g", "Hedges g", "Hedges g"),
    ("hedges_correction", "Hedges 보정", "Hedges correction"),
    ("rank_biserial", "순위 양분 상관", "Rank-biserial correlation"),
    ("common_language_probability", "공통 언어 확률", "Common-language probability"),
    ("epsilon_squared", "Epsilon squared", "Epsilon squared"),
    ("eta_squared", "Eta squared", "Eta squared"),
    ("omega_squared", "Omega squared", "Omega squared"),
    ("definition", "정의", "Definition"),
    ("tie_correction", "동점 보정", "Tie correction"),
)


def _samples(result: dict[str, object], variant: str, locale: str) -> ReportSection:
    rows: list[dict[str, object]] = []
    if variant.startswith("tost_"):
        samples = stored_object(result.get("samples"))
        if samples:
            for key, ko, en in (
                ("one_sample", "단일 표본", "One sample"),
                ("test", "검정 표본", "Test sample"),
                ("reference", "기준 표본", "Reference sample"),
                ("paired_differences", "짝 차이", "Paired differences"),
            ):
                sample = stored_object(samples.get(key))
                if sample:
                    rows.append({**sample, "sample_label": text(locale, ko, en)})
        elif variant != "tost_two_sample":
            sample = stored_object(result.get("sample"))
            rows = [sample] if sample else []
    else:
        sample = stored_object(result.get("paired_sample" if variant == "paired_t" else "sample"))
        rows = [sample] if sample else []
    valid = bool(rows) and all(
        finite_fields(row, ("n", "mean_difference" if variant == "paired_t" else "mean"))
        for row in rows
    )
    if variant == "tost_two_sample":
        valid = valid and len(rows) == 2
    return section(
        "sample_summary",
        "표본 요약",
        "Sample summary",
        rows_table(rows, SAMPLE_FIELDS, locale) if valid else "",
        locale,
    )


def _groups(result: dict[str, object], locale: str) -> ReportSection:
    rows = stored_rows(result.get("groups"))
    valid = (
        rows
        and len(rows) >= 2
        and all(
            finite_fields(row, ("n", "mean")) and isinstance(row.get("group_label"), str)
            for row in rows
        )
    )
    return section(
        "groups",
        "그룹별 요약",
        "Group summaries",
        rows_table(rows, SAMPLE_FIELDS, locale) if valid and rows else "",
        locale,
    )


def _effect(value: object, locale: str, *, unavailable: bool = False) -> ReportSection:
    effect = stored_object(value)
    if effect is None and unavailable:
        return missing(
            "effect_sizes",
            "효과크기",
            "Effect sizes",
            locale,
            reason="not_provided_by_selected_method",
            applicable=False,
        )
    return section(
        "effect_sizes",
        "효과크기",
        "Effect sizes",
        fields_table(effect, EFFECT_FIELDS, locale) if effect else "",
        locale,
    )


def _difference_axis(result: dict[str, object], locale: str) -> str:
    column = next(
        (
            stored_object(result.get(key))
            for key in ("response", "after", "test_column")
            if result.get(key)
        ),
        None,
    )
    label = report_column_label(column, "response") if column else text(locale, "반응", "Response")
    return text(locale, "차이: ", "Difference: ") + label


def _estimate_interval(
    estimate: dict[str, object] | None,
    interval: dict[str, object] | None,
    locale: str,
    bounds: dict[str, object] | None = None,
    axis_label: str | None = None,
) -> tuple[ReportSection, ReportSection]:
    fields: tuple[Field, ...] = (
        ("estimate", "추정 차이", "Estimated difference"),
        ("value", "추정 차이", "Estimated difference"),
        ("estimate_definition", "추정량 정의", "Estimate definition"),
        ("definition", "추정량 정의", "Estimate definition"),
        ("standard_error", "표준오차", "Standard error"),
        ("df", "자유도", "DF"),
        ("null_mean", "귀무 평균", "Null mean"),
        ("null_difference", "귀무 차이", "Null difference"),
    )
    value_key = "value" if estimate and "value" in estimate else "estimate"
    valid = estimate is not None and finite_fields(estimate, (value_key, "standard_error", "df"))
    ci_markup = interval_table(interval, locale) if interval else ""
    markup = (
        fields_table(estimate, fields, locale) + ci_markup
        if valid and estimate and ci_markup
        else ""
    )
    if markup and bounds:
        markup += fields_table(
            bounds,
            (
                ("lower", "동등성 하한", "Equivalence lower bound"),
                ("upper", "동등성 상한", "Equivalence upper bound"),
                ("scale", "척도", "Scale"),
                ("estimate_definition", "정의", "Definition"),
            ),
            locale,
        )
    interval_section = section(
        "estimate_interval", "추정량과 신뢰구간", "Estimate and confidence interval", markup, locale
    )
    plot = ""
    if markup and estimate and interval:
        low, high = interval.get("lower"), interval.get("upper")
        if low is None or high is None:
            plot = paragraph(
                "단측 구간의 무한 경계는 위 표에 명시했습니다. 유한 구간처럼 그리지 않습니다.",
                "The table identifies the unbounded end of this one-sided interval; "
                "it is not drawn as a finite interval.",
                locale,
            )
        else:
            estimate_value = report_number(estimate[value_key])
            references = [("x", 0.0, text(locale, "차이 0", "Zero difference"))]
            if bounds and finite_fields(bounds, ("lower", "upper")):
                references = [
                    ("x", report_number(bounds[key]), text(locale, ko, en))
                    for key, ko, en in (
                        ("lower", "동등성 하한", "Equivalence lower bound"),
                        ("upper", "동등성 상한", "Equivalence upper bound"),
                    )
                ]
            plot = report_plot(
                text(locale, "저장된 차이 신뢰구간", "Stored difference confidence interval"),
                axis_label or text(locale, "차이 (반응 단위)", "Difference (response units)"),
                text(locale, "비교", "Comparison"),
                [
                    (
                        text(locale, "신뢰구간", "Confidence interval"),
                        [(report_number(low), 1.0, "lower"), (report_number(high), 1.0, "upper")],
                    ),
                    (
                        text(locale, "추정 차이", "Estimated difference"),
                        [(estimate_value, 1.0, text(locale, "추정량", "Estimate"))],
                    ),
                ],
                lines=True,
                reference_lines=references,
                y_ticks=[(1.0, text(locale, "차이", "Difference"))],
            )
            plot += report_table(
                [text(locale, "추정량", "Estimate"), text(locale, "신뢰수준", "Confidence level")],
                [(estimate_value, interval["level"])],
            )
    return interval_section, section("interval_plot", "구간 그래프", "Interval plot", plot, locale)


def _posthoc(result: dict[str, object], locale: str) -> ReportSection:
    posthoc = stored_object(result.get("posthoc"))
    if not posthoc:
        return missing("posthoc", "사후검정", "Post-hoc comparisons", locale)
    markup = fields_table(
        posthoc,
        (
            ("method", "방법", "Method"),
            ("multiplicity_method", "다중성 보정", "Multiplicity correction"),
            ("policy", "실행 정책", "Policy"),
            ("performed", "실행 여부", "Performed"),
            ("reason", "사유", "Reason"),
            ("confidence_level", "신뢰수준", "Confidence level"),
            ("control_group_label", "대조군", "Control group"),
            ("rng_seed", "난수 시드", "Random seed"),
            ("q_critical", "임계 q", "Critical q"),
        ),
        locale,
    )
    comparisons = stored_rows(posthoc.get("comparisons"))
    if posthoc.get("performed") is True and not comparisons:
        return missing("posthoc", "사후검정", "Post-hoc comparisons", locale)
    fields: tuple[Field, ...] = (
        ("comparison_id", "비교 ID", "Comparison ID"),
        ("method", "방법", "Method"),
        ("group_1_label", "그룹 1", "Group 1"),
        ("group_2_label", "그룹 2", "Group 2"),
        ("control_group_label", "대조군", "Control group"),
        ("mean_1", "평균 1", "Mean 1"),
        ("mean_2", "평균 2", "Mean 2"),
        ("mean_difference", "평균 차이", "Mean difference"),
        ("mean_rank_difference", "평균 순위 차이", "Mean rank difference"),
        ("standard_error", "표준오차", "Standard error"),
        ("mean_difference_standard_error", "평균 차이 표준오차", "Mean-difference standard error"),
        ("statistic", "통계량", "Statistic"),
        ("statistic_kind", "통계량 종류", "Statistic kind"),
        ("z_statistic", "z 통계량", "Z statistic"),
        ("q_statistic", "q 통계량", "Q statistic"),
        ("df", "자유도", "DF"),
        ("raw_p_value", "원시 p값", "Raw P value"),
        ("adjusted_p_value", "보정 p값", "Adjusted P value"),
        ("reject_holm", "Holm 기각", "Reject after Holm"),
        ("reject_adjusted", "보정 후 기각", "Reject after adjustment"),
    )
    if comparisons:
        if not all(finite_fields(row, ("adjusted_p_value",)) for row in comparisons):
            return missing("posthoc", "사후검정", "Post-hoc comparisons", locale)
        markup += rows_table(comparisons, fields, locale)
        for row in comparisons:
            ci = stored_object(row.get("confidence_interval"))
            if ci:
                markup += report_table(
                    [text(locale, "그룹 1", "Group 1"), text(locale, "그룹 2", "Group 2")],
                    [(row.get("group_1_label"), row.get("group_2_label"))],
                ) + interval_table(ci, locale)
    return section("posthoc", "사후검정", "Post-hoc comparisons", markup, locale)


def _anova(result: dict[str, object], variant: str, locale: str) -> list[ReportSection]:
    table = stored_object(result.get("anova_table"))
    if variant == "anova_welch":
        anova = missing(
            "anova_table",
            "분산분석표",
            "ANOVA table",
            locale,
            reason="not_defined_for_welch",
            applicable=False,
        )
    else:
        rows = stored_rows(table.get("rows")) if table else None
        anova = section(
            "anova_table",
            "분산분석표",
            "ANOVA table",
            rows_table(
                rows,
                (
                    ("source", "변동원", "Source"),
                    ("sum_squares", "제곱합", "Sum of squares"),
                    ("df", "자유도", "DF"),
                    ("mean_square", "평균제곱", "Mean square"),
                ),
                locale,
            )
            if rows
            else "",
            locale,
        )
    groups = stored_rows(result.get("groups")) or []
    intervals = []
    for group in groups:
        ci = stored_object(group.get("mean_confidence_interval"))
        if ci and interval_table(ci, locale):
            intervals.append({"group_label": group.get("group_label"), **ci})
    group_intervals = section(
        "group_intervals",
        "그룹 평균 구간",
        "Group mean intervals",
        rows_table(
            intervals,
            (
                ("group_label", "그룹", "Group"),
                ("method", "방법", "Method"),
                ("level", "신뢰수준", "Confidence level"),
                ("lower", "하한", "Lower"),
                ("upper", "상한", "Upper"),
            ),
            locale,
        )
        if groups and len(intervals) == len(groups)
        else "",
        locale,
    )
    test = stored_object(result.get("test")) or {}
    effect = _effect(
        test.get("effect_size", table.get("effect_size") if table else None),
        locale,
        unavailable=variant == "anova_welch",
    )
    return [
        anova,
        group_intervals,
        effect,
        _posthoc(result, locale),
        missing(
            "residual_diagnostics",
            "잔차 진단",
            "Residual diagnostics",
            locale,
            reason="residuals_not_stored",
        ),
    ]


def _rank_sections(
    result: dict[str, object], test: dict[str, object], variant: str, locale: str
) -> list[ReportSection]:
    rank_fields: tuple[Field, ...] = (
        ("n_nonzero", "0이 아닌 차이 수", "Nonzero differences"),
        ("zero_method", "영차이 처리", "Zero-difference policy"),
        ("zero_difference_count", "영차이 수", "Zero differences"),
        ("tie_count", "동점 수", "Tie count"),
        ("tie_correction", "동점 보정", "Tie correction"),
        ("has_ties", "동점 존재", "Ties present"),
        ("positive_rank_sum", "양의 순위합", "Positive rank sum"),
        ("negative_rank_sum", "음의 순위합", "Negative rank sum"),
        ("zero_rank_sum", "영차이 순위합", "Zero rank sum"),
        ("rank_sum_total", "전체 순위합", "Total rank sum"),
    )
    sections = [
        section(
            "rank_details",
            "순위 및 동점",
            "Ranks and ties",
            fields_table({**result, **test}, rank_fields, locale),
            locale,
        ),
        _effect(test.get("effect_size"), locale),
        missing(
            "estimate_interval",
            "위치 차이 구간",
            "Location-difference interval",
            locale,
            reason="not_provided_by_selected_method",
            applicable=False,
        ),
    ]
    if variant == "mann_whitney":
        samples = stored_rows(result.get("samples"))
        rows = []
        for sample in samples or []:
            source = stored_object(sample.get("source_column"))
            rows.append(
                {
                    **sample,
                    "source_column_id": source.get("column_id") if source else None,
                    "source_column_name": source.get("display_name") if source else None,
                }
            )
        sections.append(
            section(
                "sample_inputs",
                "표본별 입력 및 제외",
                "Sample inputs and exclusions",
                rows_table(
                    rows,
                    (
                        ("sample_index", "표본 번호", "Sample index"),
                        ("label", "표본", "Sample"),
                        ("source_column_id", "열 ID", "Column ID"),
                        ("source_column_name", "원본 열", "Source column"),
                        ("source_group_value", "원본 그룹", "Source group value"),
                        ("n_total", "전체 N", "Total N"),
                        ("n_used", "사용 N", "Used N"),
                        ("n_excluded_missing", "결측 제외", "Missing excluded"),
                        ("n_excluded_non_numeric", "비수치 제외", "Non-numeric excluded"),
                    ),
                    locale,
                ),
                locale,
            )
        )
    if variant == "kruskal_wallis":
        sections.append(_posthoc(result, locale))
    return sections


def _tost_sections(result: dict[str, object], locale: str) -> list[ReportSection]:
    tests = stored_object(result.get("tests")) or {}
    lower, upper = stored_object(tests.get("lower")), stored_object(tests.get("upper"))
    tost = stored_object(result.get("tost"))
    valid = (
        lower
        and upper
        and tost
        and finite_fields(lower, ("statistic", "df", "p_value", "bound"))
        and finite_fields(upper, ("statistic", "df", "p_value", "bound"))
        and finite_fields(tost, ("p_value",))
        and isinstance(tost.get("equivalent"), bool)
    )
    markup = ""
    if valid and lower and upper and tost:
        markup = rows_table(
            [{"test": "lower", **lower}, {"test": "upper", **upper}],
            (
                ("test", "검정", "Test"),
                ("bound", "경계", "Bound"),
                ("null_hypothesis", "귀무가설", "Null hypothesis"),
                ("alternative", "대립가설", "Alternative"),
                ("statistic", "t 통계량", "T statistic"),
                ("df", "자유도", "DF"),
                ("p_value", "p값", "P value"),
                ("reject_null", "귀무가설 기각", "Reject null"),
            ),
            locale,
        )
        markup += fields_table(
            tost,
            (
                ("p_value", "TOST p값", "TOST P value"),
                ("equivalent", "동등성 판정", "Equivalent within bounds"),
                ("decision_rule", "판정 규칙", "Decision rule"),
                (
                    "ci_inside_equivalence_bounds",
                    "구간이 동등성 경계 내부",
                    "CI within equivalence bounds",
                ),
            ),
            locale,
        )
    estimate, ci, bounds = (
        stored_object(result.get("estimate")),
        stored_object(result.get("confidence_interval")),
        stored_object(result.get("equivalence_bounds")),
    )
    intervals = _estimate_interval(estimate, ci, locale, bounds, _difference_axis(result, locale))
    if not bounds or not finite_fields(bounds, ("lower", "upper")):
        intervals = (
            missing(
                "estimate_interval", "추정량과 신뢰구간", "Estimate and confidence interval", locale
            ),
            intervals[1],
        )
    return [
        section("test", "두 단측 검정", "Two one-sided tests", markup, locale),
        *intervals,
        _effect(
            result.get("effect_size"),
            locale,
            unavailable=result.get("design") == "two_sample_independent_mean_difference",
        ),
    ]


def render_hypothesis_report(result: dict[str, object], locale: str = "ko") -> ReportBody:
    summary = result.get("summary_type")
    variant = {
        "one_sample_t_test": "one_sample_t",
        "paired_t_test": "paired_t",
        "two_sample_t_test": "two_sample_t",
        "one_sample_wilcoxon_signed_rank_test": "wilcoxon",
        "mann_whitney_u_test": "mann_whitney",
        "kruskal_wallis_test": "kruskal_wallis",
    }.get(str(summary))
    if summary == "one_way_anova":
        anova_type, variance_model = result.get("anova_type"), result.get("variance_model")
        if (
            anova_type not in (None, "standard", "welch")
            or variance_model not in (None, "equal", "unequal")
            or (anova_type == "standard" and variance_model == "unequal")
            or (anova_type == "welch" and variance_model == "equal")
        ):
            return ReportBody("unsupported", (), "unsupported_result_variant")
        variant = (
            "anova_welch"
            if anova_type == "welch" or variance_model == "unequal"
            else "anova_standard"
        )
    elif summary == "equivalence_tost":
        variant = {
            "one_sample_mean": "tost_one_sample",
            "two_sample_independent_mean_difference": "tost_two_sample",
            "paired_mean_difference": "tost_paired",
        }.get(str(result.get("design")))
    schema = result.get("schema_version")
    allowed = (
        (1, 2) if summary in {"one_way_anova", "equivalence_tost", "mann_whitney_u_test"} else (1,)
    )
    if variant is None or type(schema) is not int or schema not in allowed:
        return ReportBody("unsupported", (), "unsupported_result_schema")
    sections = [settings(result, locale)]
    sections.append(
        _samples(result, variant, locale)
        if variant in {"one_sample_t", "paired_t", "wilcoxon"} or variant.startswith("tost_")
        else _groups(result, locale)
    )
    if variant.startswith("tost_"):
        sections.extend(_tost_sections(result, locale))
    else:
        test = (
            stored_object(
                result.get(
                    "contrast"
                    if variant in {"one_sample_t", "paired_t", "two_sample_t"}
                    else "test"
                )
            )
            or {}
        )
        statistic_key = {
            "wilcoxon": "w_statistic",
            "mann_whitney": "u_statistic",
            "kruskal_wallis": "h_statistic",
            "anova_standard": "f_statistic",
            "anova_welch": "f_statistic",
        }.get(variant, "statistic")
        valid = finite_fields(test, (statistic_key, "p_value")) and isinstance(
            test.get("reject_null"), bool
        )
        sections.append(
            section(
                "test",
                "검정 결과",
                "Test result",
                fields_table(test, TEST_FIELDS, locale) if valid else "",
                locale,
            )
        )
        if variant in {"one_sample_t", "paired_t", "two_sample_t"}:
            sections.extend(
                _estimate_interval(
                    test,
                    stored_object(test.get("confidence_interval")),
                    locale,
                    axis_label=_difference_axis(result, locale),
                )
            )
            sections.append(_effect(test.get("effect_size"), locale))
        elif variant.startswith("anova_"):
            sections.extend(_anova(result, variant, locale))
        else:
            sections.extend(_rank_sections(result, test, variant, locale))
    interpretation = paragraph(
        "저장된 결과만 표시하며 재분석하지 않습니다. 독립성은 연구 설계 가정입니다. "
        "비기각은 동일함이나 동등성의 증명이 아닙니다.",
        "Only stored results are displayed; no analysis is rerun. "
        "Independence is a study-design assumption. "
        "Failure to reject does not prove equality or equivalence.",
        locale,
    )
    if variant.startswith("tost_"):
        interpretation += paragraph(
            "동등성은 사전에 지정한 경계와 두 단측 검정에 대한 판정입니다. "
            "표시 구간의 신뢰수준은 저장된 1 - 2 alpha입니다.",
            "Equivalence is assessed against the specified bounds using both one-sided tests. "
            "The displayed interval uses the stored 1 - 2 alpha confidence level.",
            locale,
        )
    elif variant in {"wilcoxon", "mann_whitney", "kruskal_wallis"}:
        interpretation += paragraph(
            "순위 검정을 일반적인 중앙값 차이 검정으로 해석하지 않습니다. "
            "저장되지 않은 위치 차이 추정량이나 신뢰구간은 제공하지 않습니다.",
            "A rank test is not a general test of median differences. "
            "No unstored location-difference estimate or confidence interval is supplied.",
            locale,
        )
    sections += [
        warnings_section(result, locale),
        section("interpretation", "해석 제한", "Interpretation limits", interpretation, locale),
    ]
    expected = next(item for item in HYPOTHESIS_REPORT_VARIANTS if item.variant_id == variant)
    by_id = {item.section_id: item for item in sections}
    return ReportBody(variant, tuple(by_id[item.section_id] for item in expected.sections))
