"""Stored categorical-test tables and plots, without raw-data access or refits."""

from app.services.inference_report_primitives import (
    Field,
    fields_table,
    finite_fields,
    interval_table,
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
    report_horizontal_bars,
    report_number,
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


CATEGORICAL_REPORT_VARIANTS: tuple[ReportVariantDefinition, ...] = (
    _variant(
        "one_proportion",
        ("sample_summary", "test", "estimate_interval"),
        ("levels", "effect_sizes", "count_plot"),
    ),
    _variant(
        "two_proportion",
        ("groups", "test", "estimate_interval"),
        ("contingency_table", "expected_counts", "effect_sizes", "count_plot"),
    ),
    _variant(
        "chi_square",
        ("contingency_table", "test"),
        (
            "levels",
            "expected_counts",
            "cell_diagnostics",
            "effect_sizes",
            "alternatives",
            "count_plot",
        ),
    ),
)
CATEGORICAL_REPORT_VARIANTS_BY_METHOD = {
    method: tuple(item for item in CATEGORICAL_REPORT_VARIANTS if item.variant_id == name)
    for method, name in (
        ("categorical.one_proportion", "one_proportion"),
        ("categorical.two_proportion", "two_proportion"),
        ("categorical.chi_square_association", "chi_square"),
    )
}
TEST_FIELDS: tuple[Field, ...] = (
    ("statistic", "검정통계량", "Statistic"),
    ("statistic_name", "통계량 이름", "Statistic name"),
    ("df", "자유도", "DF"),
    ("p_value", "p값", "P value"),
    ("reject_null", "귀무가설 기각", "Reject null"),
    ("alternative", "대립가설", "Alternative"),
    ("exact", "정확 검정", "Exact test"),
    ("continuity_correction", "연속성 보정", "Continuity correction"),
)
COUNT_FIELDS: tuple[Field, ...] = (
    ("group_label", "그룹", "Group"),
    ("event_count", "사건 수", "Events"),
    ("non_event_count", "비사건 수", "Non-events"),
    ("total", "N", "N"),
    ("sample_proportion", "표본 비율", "Sample proportion"),
    ("difference_from_null", "귀무비율 대비 차이", "Difference from null proportion"),
    ("odds", "오즈", "Odds"),
)


def _interval(result: dict[str, object], locale: str, *, one_sample: bool) -> ReportSection:
    source = stored_object(result.get("sample" if one_sample else "difference"))
    interval = (
        stored_object(result.get("confidence_interval"))
        if one_sample
        else stored_object(source.get("confidence_interval"))
        if source
        else None
    )
    key = "sample_proportion" if one_sample else "estimate"
    valid = source is not None and finite_fields(source, (key,))
    markup = interval_table(interval, locale) if interval and valid else ""
    if markup and source:
        markup = (
            fields_table(
                source,
                (
                    (
                        key,
                        "비율 추정량" if one_sample else "비율 차이 추정량",
                        "Proportion estimate" if one_sample else "Proportion-difference estimate",
                    ),
                    ("definition", "차이 정의", "Difference definition"),
                ),
                locale,
            )
            + markup
        )
        markup += (
            paragraph(
                "구간은 모집단 비율에 대한 구간이며, "
                "귀무비율 대비 차이의 구간으로 바꾸지 않습니다.",
                "This is an interval for the population proportion, "
                "not an interval for its difference from the null proportion.",
                locale,
            )
            if one_sample
            else paragraph(
                "차이 방향은 저장된 그룹 순서와 정의를 따릅니다.",
                "The difference follows the stored group order and definition.",
                locale,
            )
        )
    return section(
        "estimate_interval", "추정량과 신뢰구간", "Estimate and confidence interval", markup, locale
    )


def _count_plot(values: list[tuple[str, float]], locale: str) -> ReportSection:
    return section(
        "count_plot",
        "저장 빈도 그래프",
        "Stored count plot",
        report_horizontal_bars(
            text(locale, "저장 빈도", "Stored counts"),
            text(locale, "빈도", "Count"),
            text(locale, "수준 / 그룹", "Level / group"),
            values,
        ),
        locale,
    )


def _one_proportion(result: dict[str, object], locale: str) -> list[ReportSection]:
    sample = stored_object(result.get("sample"))
    valid = sample is not None and finite_fields(
        sample, ("event_count", "non_event_count", "total", "sample_proportion")
    )
    summary = section(
        "sample_summary",
        "표본 요약",
        "Sample summary",
        fields_table(sample, COUNT_FIELDS, locale) if valid and sample else "",
        locale,
    )
    levels = stored_rows(result.get("levels"))
    valid_levels = levels and all(
        finite_fields(row, ("count",)) and isinstance(row.get("level"), str) for row in levels
    )
    level_section = section(
        "levels",
        "반응 수준",
        "Response levels",
        rows_table(
            levels,
            (
                ("level", "수준", "Level"),
                ("count", "빈도", "Count"),
                ("is_event", "사건 수준", "Event level"),
            ),
            locale,
        )
        if valid_levels and levels
        else "",
        locale,
    )
    effect = stored_object(result.get("effect_size"))
    effect_section = section(
        "effect_sizes",
        "효과크기",
        "Effect size",
        fields_table(
            effect,
            (("cohen_h", "Cohen h", "Cohen h"), ("definition", "정의", "Definition")),
            locale,
        )
        if effect and finite_fields(effect, ("cohen_h",))
        else "",
        locale,
    )
    values = (
        [(str(row["level"]), report_number(row["count"])) for row in levels]
        if valid_levels and levels
        else []
    )
    return [
        summary,
        _interval(result, locale, one_sample=True),
        level_section,
        effect_section,
        _count_plot(values, locale),
    ]


def _two_proportion(result: dict[str, object], locale: str) -> list[ReportSection]:
    groups = stored_rows(result.get("groups"))
    valid = (
        groups
        and len(groups) == 2
        and all(
            finite_fields(row, ("event_count", "non_event_count", "total", "sample_proportion"))
            and isinstance(row.get("group_label"), str)
            for row in groups
        )
    )
    markup = rows_table(groups, COUNT_FIELDS, locale) if valid and groups else ""
    if markup and groups:
        for group in groups:
            levels = stored_rows(group.get("levels"))
            if levels:
                markup += report_table([text(locale, "그룹", "Group")], [(group["group_label"],)])
                markup += rows_table(
                    levels, (("level", "수준", "Level"), ("count", "빈도", "Count")), locale
                )
    group_section = section(
        "groups", "그룹별 사건 수와 비율", "Group event counts and proportions", markup, locale
    )
    contingency = stored_object(result.get("contingency_table"))
    rows = stored_rows(contingency.get("rows")) if contingency else None
    table_valid = (
        rows
        and len(rows) == 2
        and all(
            finite_fields(row, ("event_count", "non_event_count"))
            and isinstance(row.get("group_label"), str)
            for row in rows
        )
    )
    table = section(
        "contingency_table",
        "2 x 2 관측 빈도",
        "2 by 2 observed counts",
        rows_table(rows, COUNT_FIELDS, locale) if table_valid and rows else "",
        locale,
    )
    expected_rows = []
    expected = contingency.get("expected_counts") if contingency else None
    if expected is not None:
        if (
            not isinstance(expected, list)
            or len(expected) != 2
            or any(not isinstance(row, list) or len(row) != 2 for row in expected)
        ):
            raise ValueError("analysis_report_payload_invalid")
        for index, row in enumerate(expected):
            expected_rows.append(
                (
                    rows[index]["group_label"] if table_valid and rows else index + 1,
                    report_number(row[0]),
                    report_number(row[1]),
                )
            )
    expected_markup = (
        report_table(
            [
                text(locale, "그룹", "Group"),
                text(locale, "사건 기대 빈도", "Expected events"),
                text(locale, "비사건 기대 빈도", "Expected non-events"),
            ],
            expected_rows,
        )
        if expected_rows
        else ""
    )
    if expected_markup and contingency:
        expected_markup += fields_table(
            contingency,
            (("min_expected_count", "최소 기대 빈도", "Minimum expected count"),),
            locale,
        )
    effects = stored_object(result.get("effect_sizes"))
    effect_markup = ""
    for key, ko, en in (
        ("risk_ratio", "위험비", "Risk ratio"),
        ("odds_ratio", "오즈비", "Odds ratio"),
    ):
        effect = stored_object(effects.get(key)) if effects else None
        if effect:
            effect_markup += fields_table(
                {"name": text(locale, ko, en), **effect},
                (
                    ("name", "효과", "Effect"),
                    ("estimate", "추정량", "Estimate"),
                    ("definition", "정의", "Definition"),
                ),
                locale,
            )
            ci = stored_object(effect.get("confidence_interval"))
            effect_markup += (
                interval_table(ci, locale)
                if ci
                else paragraph(
                    "해당 효과의 구간은 저장 결과에 없습니다. 영빈도 등에 대한 경고를 확인하세요.",
                    "No interval for this effect is stored. "
                    "Review warnings, including any zero-cell limitations.",
                    locale,
                )
            )
    values = (
        [
            (
                str(row["group_label"]) + " / " + text(locale, "사건", "Events"),
                report_number(row["event_count"]),
            )
            for row in groups
        ]
        if valid and groups
        else []
    )
    values += (
        [
            (
                str(row["group_label"]) + " / " + text(locale, "비사건", "Non-events"),
                report_number(row["non_event_count"]),
            )
            for row in groups
        ]
        if valid and groups
        else []
    )
    return [
        group_section,
        _interval(result, locale, one_sample=False),
        table,
        section("expected_counts", "기대 빈도", "Expected counts", expected_markup, locale),
        section(
            "effect_sizes",
            "위험비와 오즈비",
            "Risk and odds ratios",
            effect_markup
            if effects and all(key in effects for key in ("risk_ratio", "odds_ratio"))
            else "",
            locale,
        ),
        _count_plot(values, locale),
    ]


def _chi_square(result: dict[str, object], locale: str) -> list[ReportSection]:
    table = stored_object(result.get("contingency_table"))
    rows = stored_rows(table.get("rows")) if table else None
    columns = table.get("column_levels") if table else None
    valid = (
        rows
        and isinstance(columns, list)
        and len(columns) >= 2
        and all(isinstance(value, str) for value in columns)
    )
    observed_rows: list[list[object]] = []
    diagnostic_rows: list[dict[str, object]] = []
    expected_rows: list[list[object]] = []
    values: list[tuple[str, float]] = []
    if valid and rows and isinstance(columns, list):
        for row in rows:
            cells = stored_rows(row.get("cells"))
            if (
                not cells
                or len(cells) != len(columns)
                or not isinstance(row.get("row_level"), str)
                or not finite_fields(row, ("row_total",))
            ):
                valid = False
                break
            if any(
                cell.get("column_level") != columns[index] or not finite_fields(cell, ("observed",))
                for index, cell in enumerate(cells)
            ):
                valid = False
                break
            observed_rows.append(
                [row["row_level"], *[cell["observed"] for cell in cells], row["row_total"]]
            )
            if all(finite_fields(cell, ("expected",)) for cell in cells):
                expected_rows.append([row["row_level"], *[cell["expected"] for cell in cells]])
            for cell in cells:
                diagnostic_rows.append({"row_level": row["row_level"], **cell})
                values.append(
                    (
                        str(row["row_level"]) + " / " + str(cell["column_level"]),
                        report_number(cell["observed"]),
                    )
                )
    observed = ""
    if valid and table and isinstance(columns, list):
        totals = table.get("column_totals")
        if (
            isinstance(totals, list)
            and len(totals) == len(columns)
            and finite_fields(table, ("grand_total",))
        ):
            observed_rows.append(
                [
                    text(locale, "전체", "Total"),
                    *[report_number(value) for value in totals],
                    table["grand_total"],
                ]
            )
        else:
            valid = False
        if valid:
            observed = report_table(
                [
                    text(locale, "행 / 열", "Row / column"),
                    *columns,
                    text(locale, "행 합계", "Row total"),
                ],
                observed_rows,
            )
    expected_markup = (
        report_table([text(locale, "행 / 열", "Row / column"), *columns], expected_rows)
        if valid and rows and len(expected_rows) == len(rows) and isinstance(columns, list)
        else ""
    )
    expected_summary = stored_object(result.get("expected_count_summary"))
    if expected_markup and expected_summary:
        expected_markup += fields_table(
            expected_summary,
            (
                ("min_expected", "최소 기대 빈도", "Minimum expected count"),
                ("cells_below_1", "기대 빈도 1 미만 셀", "Cells below 1"),
                ("cells_below_5", "기대 빈도 5 미만 셀", "Cells below 5"),
                ("cell_count", "셀 수", "Cell count"),
                ("share_below_5", "5 미만 비중", "Share below 5"),
                ("rule_of_thumb_passed", "기대 빈도 기준 충족", "Expected-count rule passed"),
            ),
            locale,
        )
    diagnostic_keys = ("row_percent", "column_percent", "total_percent", "standardized_residual")
    diagnostics_valid = (
        valid
        and diagnostic_rows
        and all(all(key in row for key in diagnostic_keys) for row in diagnostic_rows)
    )
    diagnostics = (
        rows_table(
            diagnostic_rows,
            (
                ("row_level", "행 수준", "Row level"),
                ("column_level", "열 수준", "Column level"),
                ("observed", "관측 빈도", "Observed"),
                ("expected", "기대 빈도", "Expected"),
                ("row_percent", "행 백분율", "Row percent"),
                ("column_percent", "열 백분율", "Column percent"),
                ("total_percent", "전체 백분율", "Total percent"),
                ("standardized_residual", "표준화 잔차", "Standardized residual"),
            ),
            locale,
        )
        if diagnostics_valid
        else ""
    )
    level_markup = ""
    for key, ko, en in (
        ("row_levels", "행 수준", "Row levels"),
        ("column_levels", "열 수준", "Column levels"),
    ):
        levels = stored_rows(result.get(key))
        if levels:
            level_markup += paragraph(ko, en, locale) + rows_table(
                levels,
                (
                    ("level", "수준", "Level"),
                    ("index", "번호", "Index"),
                    ("count", "빈도", "Count"),
                ),
                locale,
            )
    effect = stored_object(result.get("effect_size"))
    alternatives = stored_rows(result.get("recommended_alternative_tests"))
    alternative_markup = (
        rows_table(
            alternatives,
            (
                ("method", "권고 방법", "Recommended method"),
                ("reason", "사유", "Reason"),
                ("implemented", "구현 여부", "Implemented"),
            ),
            locale,
        )
        if alternatives
        else paragraph("저장된 대안 권고 없음.", "No alternative recommendation is stored.", locale)
        if alternatives == []
        else ""
    )
    if alternative_markup:
        alternative_markup += paragraph(
            "권고는 별도 검정을 실행했다는 뜻이 아닙니다. 자동으로 방법을 바꾸지 않았습니다.",
            "A recommendation does not mean that another test was executed. "
            "No method was switched automatically.",
            locale,
        )
    return [
        section(
            "contingency_table", "관측 빈도와 합계", "Observed counts and totals", observed, locale
        ),
        section(
            "levels",
            "범주 수준",
            "Category levels",
            level_markup if result.get("row_levels") and result.get("column_levels") else "",
            locale,
        ),
        section(
            "expected_counts",
            "기대 빈도와 적합성",
            "Expected counts and adequacy",
            expected_markup if expected_summary else "",
            locale,
        ),
        section(
            "cell_diagnostics",
            "셀별 비율과 잔차",
            "Cell percentages and residuals",
            diagnostics,
            locale,
        ),
        section(
            "effect_sizes",
            "연관 효과크기",
            "Association effect size",
            fields_table(
                effect,
                (("cramers_v", "Cramer V", "Cramer V"), ("definition", "정의", "Definition")),
                locale,
            )
            if effect and finite_fields(effect, ("cramers_v",))
            else "",
            locale,
        ),
        section(
            "alternatives", "대안 권고", "Alternative recommendations", alternative_markup, locale
        ),
        _count_plot(values if valid else [], locale),
    ]


def render_categorical_report(result: dict[str, object], locale: str = "ko") -> ReportBody:
    variant = {
        "one_proportion_test": "one_proportion",
        "two_proportion_test": "two_proportion",
        "chi_square_association": "chi_square",
    }.get(str(result.get("summary_type")))
    if (
        variant is None
        or type(result.get("schema_version")) is not int
        or result.get("schema_version") != 1
    ):
        return ReportBody("unsupported", (), "unsupported_result_schema")
    test = stored_object(result.get("test")) or {}
    valid = (
        finite_fields(test, ("p_value",))
        and isinstance(test.get("reject_null"), bool)
        and isinstance(test.get("statistic_name"), str)
    )
    if test.get("statistic") is not None:
        finite_fields(test, ("statistic",))
    sections = [
        settings(result, locale),
        section(
            "test",
            "검정 결과",
            "Test result",
            fields_table(test, TEST_FIELDS, locale) if valid else "",
            locale,
        ),
    ]
    if variant == "one_proportion":
        sections.extend(_one_proportion(result, locale))
    elif variant == "two_proportion":
        sections.extend(_two_proportion(result, locale))
    else:
        sections.extend(_chi_square(result, locale))
    sections += [
        warnings_section(result, locale),
        section(
            "interpretation",
            "해석 제한",
            "Interpretation limits",
            paragraph(
                "저장된 빈도와 검정값만 표시합니다. 관측 독립성은 설계 가정이며, "
                "비기각은 비율이 같거나 연관성이 없다는 증명이 아닙니다. "
                "저장되지 않은 구간은 계산하지 않습니다.",
                "Only stored counts and test results are displayed. "
                "Independence is a design assumption; failure to reject does not prove "
                "equal proportions or absence of association. "
                "Unstored intervals are not calculated.",
                locale,
            ),
            locale,
        ),
    ]
    expected = next(item for item in CATEGORICAL_REPORT_VARIANTS if item.variant_id == variant)
    by_id = {item.section_id: item for item in sections}
    return ReportBody(variant, tuple(by_id[item.section_id] for item in expected.sections))
