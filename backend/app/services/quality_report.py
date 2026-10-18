"""Static quality charts from stored limits, counts, bins, and group identities."""

from collections import defaultdict
from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
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

_SECTIONS = {
    "individuals_chart": ("individuals_charts", "signals"),
    "subgroup_chart": ("subgroup_charts", "signals"),
    "attribute_control_chart": ("attribute_chart", "signals"),
    "run_chart": ("run_chart", "randomness_tests", "signals"),
    "capability_analysis": ("capability_indices", "capability_histogram"),
    "gage_rr": ("gage_anova", "gage_variance_components", "gage_interaction"),
    "gage_run_chart": ("gage_run_plot", "gage_group_summaries"),
}
QUALITY_REPORT_VARIANTS = {
    summary: (
        ReportVariantDefinition(
            "default",
            (
                ReportSectionDefinition("quality_summary", core=True),
                *tuple(
                    ReportSectionDefinition(
                        key,
                        core=key
                        in {"gage_anova", "gage_variance_components", "capability_indices"},
                    )
                    for key in keys
                ),
            ),
        ),
    )
    for summary, keys in _SECTIONS.items()
}


def _scalar_rows(values: dict[str, Any], prefix: str = "") -> list[list[object]]:
    rows: list[list[object]] = []
    for key, value in values.items():
        label = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            rows.extend(_scalar_rows(value, label))
        elif isinstance(value, list):
            if all(isinstance(item, str | int | float | bool) for item in value):
                rows.append([label, ", ".join(str(item) for item in value)])
        else:
            rows.append([label, value])
    return rows


def quality_report_body(payload: dict[str, Any], locale: ReportLocale = "en") -> ReportBody:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    kind = payload.get("summary_type")
    if kind not in _SECTIONS or not (
        "n_used" in payload or isinstance(payload.get("sample"), dict)
    ):
        return ReportBody("default", (), "quality_core_not_stored")
    scalar_headers = [
        text("Statistic / setting", "통계량 / 설정"),
        text("Stored value", "저장된 값"),
    ]
    summary = {
        key: value
        for key, value in payload.items()
        if key
        in {
            "method",
            "missing_policy",
            "sample",
            "design",
            "order_source",
            "sigma_estimator",
            "sigma_estimators",
            "control_limit_method",
            "phase",
            "chart_type",
            "count_definition",
            "baseline",
            "limit_set_dependency",
            "target_dependency",
            "dispersion",
            "spec_limits",
            "notes",
            "summary",
            "subgroup_size",
            "subgroup_count",
            "constants",
            "center_method",
            "center_line",
            "order_tie_breaker",
            "order_timezone",
        }
        or key.startswith("n_")
    }
    column_rows: list[list[object]] = []
    for key in ("value", "count", "denominator", "order"):
        if isinstance(payload.get(key), dict):
            column_rows.append([key, report_column_label(payload[key], key)])
    for key, column in payload.get("columns", {}).items():
        if isinstance(column, dict):
            column_rows.append([key, report_column_label(column, key)])
    rule_rows = [
        [f"control_rules.{index + 1}.{key}", value]
        for index, rule in enumerate(payload.get("control_rules", []))
        for key, value in _scalar_rows(rule)
    ]
    sections: list[ReportSection] = [
        ReportSection(
            "quality_summary",
            text("Quality Analysis Summary", "품질 분석 요약"),
            "rendered",
            report_table(scalar_headers, column_rows + _scalar_rows(summary) + rule_rows),
        )
    ]

    def add(
        section_id: str,
        en: str,
        ko: str,
        markup: str | None,
        *,
        reason: str = "section_not_stored",
        not_applicable: bool = False,
    ) -> None:
        sections.append(
            ReportSection(
                section_id,
                text(en, ko),
                "rendered" if markup else "not_applicable" if not_applicable else "missing",
                markup or None,
                None if markup else reason,
            )
        )

    value_label = report_column_label(payload.get("value", {}), text("Measurement", "측정값"))
    value_unit = payload.get("value", {}).get("unit")
    unit_suffix = f" ({value_unit})" if value_unit else ""

    def chart_markup(
        chart: object, title: str, y_label: str, *, point_limits: bool = False, run: bool = False
    ) -> str | None:
        if (
            not isinstance(chart, dict)
            or not isinstance(chart.get("points"), list)
            or not chart["points"]
        ):
            return None
        points = chart["points"]
        data = []
        shapes = []
        for point in points:
            codes = point.get("signal_codes", [])
            label = "; ".join(
                f"{key}={point[key]}"
                for key in (
                    "position",
                    "canonical_position",
                    "subgroup_label",
                    "n",
                    "count",
                    "denominator",
                    "relative_to_center",
                    "previous_canonical_position",
                    "lcl",
                    "ucl",
                    "signal_codes",
                )
                if key in point
            )
            data.append((report_number(point["position"]), report_number(point["value"]), label))
            shapes.append(
                "square"
                if any(
                    "beyond_3_sigma" in code
                    or "beyond_ucl" in code
                    or "beyond_control_limits" in code
                    for code in codes
                )
                else "diamond"
                if codes
                else "circle"
            )
        series = [(title, data)]
        marker_shapes = [shapes]
        references: list[tuple[str, float, str]] = []
        center = chart.get("center_line", payload.get("center_line"))
        if center is not None:
            references.append(
                (
                    "y",
                    report_number(center),
                    text("Median", "중앙값") if run else text("Center line", "중심선"),
                )
            )
        if point_limits:
            for key in ("lcl", "ucl"):
                if any(point.get(key) is None for point in points):
                    raise ValueError("analysis_report_payload_invalid")
                series.append(
                    (
                        key.upper(),
                        [
                            (
                                report_number(point["position"]),
                                report_number(point[key]),
                                key.upper(),
                            )
                            for point in points
                        ],
                    )
                )
                marker_shapes.append(["circle"] * len(points))
        elif not run:
            references.extend(
                ("y", report_number(chart[key]), key.upper())
                for key in ("lcl", "ucl")
                if chart.get(key) is not None
            )
        x_label = (
            text("Sorted order", "정렬 순서")
            if chart.get("x_axis") == "order_rank"
            else text("Analysis row order", "분석 행 순서")
        )
        markup = report_plot(
            title,
            x_label,
            y_label,
            series,
            lines=True,
            reference_lines=references,
            marker_shapes=marker_shapes,
        )
        markup += (
            "<p>"
            + escape(text("Stored / calculated points", "저장 / 계산 점 수"))
            + f": {len(points)} / {chart.get('point_count')}; "
            + escape(text("Truncated", "표시 제한"))
            + f": {chart.get('points_truncated')}</p>"
        )
        markup += (
            "<p>"
            + escape(
                text(
                    "Square: point beyond limits; diamond: other stored signal; "
                    "circle: no stored signal. Control limits are not specification limits.",
                    "사각형: 한계 초과 점, 마름모: 기타 저장 신호, 원: 저장 신호 없음. "
                    "관리한계는 규격한계가 아닙니다.",
                )
            )
            + "</p>"
            if not run
            else ""
        )
        return markup

    if kind == "individuals_chart":
        charts = [
            chart_markup(
                payload.get("individuals_chart"),
                text("Individuals Chart", "개별값 관리도"),
                value_label,
            ),
            chart_markup(
                payload.get("moving_range_chart"),
                text("Moving Range Chart", "이동범위 관리도"),
                text("Moving range", "이동범위") + unit_suffix,
            ),
        ]
        add(
            "individuals_charts",
            "I / MR Charts",
            "I / MR 관리도",
            "".join(chart for chart in charts if chart is not None) if all(charts) else None,
        )
    elif kind == "subgroup_chart":
        spread_key = "r_chart" if payload.get("chart_type") == "xbar_r" else "s_chart"
        charts = [
            chart_markup(
                payload.get("xbar_chart"),
                "Xbar",
                text("Subgroup mean", "부분군 평균") + unit_suffix,
            ),
            chart_markup(
                payload.get(spread_key),
                "R" if spread_key == "r_chart" else "S",
                (
                    text("Subgroup range", "부분군 범위")
                    if spread_key == "r_chart"
                    else text("Subgroup SD", "부분군 표준편차")
                )
                + unit_suffix,
            ),
        ]
        add(
            "subgroup_charts",
            "Subgroup Charts",
            "부분군 관리도",
            "".join(chart for chart in charts if chart is not None) if all(charts) else None,
        )
    elif kind == "attribute_control_chart":
        kind_label = {
            "p": text("Nonconforming proportion", "부적합 비율"),
            "np": text("Nonconforming count", "부적합 개수"),
            "c": text("Nonconformity count", "결점 수"),
            "u": text("Nonconformities per unit", "단위당 결점 수"),
        }.get(str(payload.get("chart_type", "")), text("Stored statistic", "저장 통계량"))
        add(
            "attribute_chart",
            "Attribute Control Chart",
            "계수형 관리도",
            chart_markup(
                payload.get("chart"),
                str(payload.get("chart_type", "")),
                kind_label,
                point_limits=True,
            ),
        )
    elif kind == "run_chart":
        add(
            "run_chart",
            "Run Chart",
            "런 차트",
            chart_markup(payload.get("chart"), text("Run Chart", "런 차트"), value_label, run=True),
        )
        randomness = {
            key: payload[key]
            for key in ("runs", "runs_test", "approximate_randomness_tests")
            if isinstance(payload.get(key), dict)
        }
        add(
            "randomness_tests",
            "Randomness Tests",
            "무작위성 검정",
            report_table(scalar_headers, _scalar_rows(randomness)) if randomness else None,
        )
    elif kind == "capability_analysis":
        capability = payload.get("capability")
        add(
            "capability_indices",
            "Capability Indices",
            "공정능력 지수",
            report_table(
                scalar_headers,
                _scalar_rows(
                    {
                        key: payload[key]
                        for key in (
                            "capability",
                            "observed_nonconformance",
                            "expected_nonconformance_normal",
                        )
                        if isinstance(payload.get(key), dict)
                    }
                ),
            )
            if isinstance(capability, dict) and capability
            else None,
        )
        bins = payload.get("histogram", {}).get("bins")
        histogram = None
        if isinstance(bins, list) and bins:
            references = [
                ("x", report_number(value), key.upper())
                for key, value in payload.get("spec_limits", {}).items()
                if value is not None
            ]
            histogram = report_plot(
                text("Capability Histogram", "공정능력 히스토그램"),
                value_label,
                text("Frequency", "빈도"),
                [],
                reference_lines=references,
                histogram_bins=[
                    (
                        report_number(row["lower"]),
                        report_number(row["upper"]),
                        report_number(row["count"]),
                        text("Stored bin count", "저장 구간 빈도"),
                    )
                    for row in bins
                ],
            )
            histogram += report_table(
                [
                    text("Lower", "하한"),
                    text("Upper", "상한"),
                    text("Count", "빈도"),
                    text("Density", "밀도"),
                    text("Stored normal density", "저장 정규 밀도"),
                ],
                [
                    [
                        row["lower"],
                        row["upper"],
                        row["count"],
                        row.get("density"),
                        row.get("normal_density"),
                    ]
                    for row in bins
                ],
            )
        add("capability_histogram", "Capability Histogram", "공정능력 히스토그램", histogram)
    elif kind == "gage_rr":
        anova = payload.get("anova_table")
        add(
            "gage_anova",
            "Gage R&R ANOVA",
            "Gage R&R 분산분석",
            report_table(
                [text("Source", "원인"), "DF", "SS", "MS", "F", "p", text("Denominator", "분모")],
                [
                    [
                        row.get(key)
                        for key in (
                            "source",
                            "degrees_of_freedom",
                            "sum_of_squares",
                            "mean_square",
                            "f_statistic",
                            "p_value",
                            "denominator",
                        )
                    ]
                    for row in anova
                ],
            )
            if isinstance(anova, list) and anova
            else None,
        )
        components = payload.get("variance_components")
        add(
            "gage_variance_components",
            "Variance Components",
            "분산 성분",
            report_table(scalar_headers, _scalar_rows(components))
            if isinstance(components, dict) and components
            else None,
        )
        add(
            "gage_interaction",
            "Part by Operator Interaction",
            "부품과 작업자 교호작용",
            None,
            reason="interaction_means_not_stored",
        )
    elif kind == "gage_run_chart":
        chart = payload.get("chart") or {}
        points = chart.get("points")
        plot = None
        if isinstance(points, list) and points:
            grouped: dict[tuple[int, int], list[tuple[float, float, str]]] = defaultdict(list)
            for point in points:
                part, operator = point["part_index"], point["operator_index"]
                label = (
                    f"part_index={part}; operator_index={operator}; "
                    f"replicate_index={point['replicate_index']}; "
                    f"canonical_position={point['canonical_position']}"
                )
                grouped[part, operator].append(
                    (report_number(point["position"]), report_number(point["value"]), label)
                )
            # Separate part/operator series never introduce a cross-operator connecting line.
            plot = report_plot(
                text("Gage Run Chart", "측정시스템 런 차트"),
                text("Stored run order", "저장된 실행 순서"),
                report_column_label(
                    payload.get("columns", {}).get("measurement", {}), text("Measurement", "측정값")
                ),
                [
                    (
                        f"{text('Part', '부품')} {part} / {text('Operator', '작업자')} {operator}",
                        values,
                    )
                    for (part, operator), values in grouped.items()
                ],
                lines=True,
            )
            plot += (
                "<p>"
                + escape(
                    text(
                        "Stored identifiers are indices; original group labels were not saved. "
                        "Stored / calculated points",
                        "저장된 식별자는 인덱스이며 원래 그룹 이름은 저장되지 않았습니다. "
                        "저장 / 계산 점 수",
                    )
                )
                + f": {len(points)} / {chart.get('point_count')}</p>"
            )
        add("gage_run_plot", "Gage Run Chart", "측정시스템 런 차트", plot)
        summaries = []
        for name in ("part_summaries", "operator_summaries"):
            values = payload.get(name)
            if isinstance(values, list):
                summaries.extend(
                    [[name, key, value] for row in values for key, value in _scalar_rows(row)]
                )
        add(
            "gage_group_summaries",
            "Group Summaries",
            "그룹 요약",
            report_table([text("Group", "그룹"), *scalar_headers], summaries)
            if summaries
            else None,
        )
    if "signals" in _SECTIONS[kind]:
        signals = payload.get("signals")
        if isinstance(signals, list):
            rows = [
                [index + 1, key, value]
                for index, signal in enumerate(signals)
                for key, value in _scalar_rows(signal)
            ]
            markup = report_table([text("Signal", "신호"), *scalar_headers], rows)
            if not signals:
                markup += (
                    "<p>" + escape(text("No stored signals.", "저장된 신호가 없습니다.")) + "</p>"
                )
            add("signals", "Stored Signals", "저장된 신호", markup)
        else:
            add("signals", "Stored Signals", "저장된 신호", None)
    return ReportBody("default", tuple(sections))
