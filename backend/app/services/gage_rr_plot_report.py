"""Static Gage charts from validated saved summaries, never from source measurements."""

from collections.abc import Mapping, Sequence
from hashlib import sha256
from html import escape
from typing import Any

from app.api.v1.schemas.gage_rr_plots import (
    GageComponentPlotItem,
    GageRrPlotBundle,
    validate_gage_rr_plot_result,
)
from app.i18n.report_text import ReportLocale, report_text
from app.services.report_contract import ReportSection
from app.services.report_numeric_axis import (
    numeric_axis_plan,
    numeric_axis_ticks,
    numeric_fraction,
    padded_range,
)
from app.services.stored_report_primitives import (
    report_column_label,
    report_number,
    report_table,
    short_label,
)

GAGE_PLOT_SECTION_IDS = (
    "gage_components_plot",
    "gage_response_by_part",
    "gage_dispersion",
    "gage_response_by_operator",
    "gage_xbar",
    "gage_interaction",
)
_COLORS = ("#225aa7", "#26775a", "#a9442f")
_COMPONENTS = ("total_gage_rr", "repeatability", "reproducibility", "part_to_part")


def _text(locale: ReportLocale, en: str, ko: str) -> str:
    return report_text(locale, en=en, ko=ko)


def _paragraph(value: str) -> str:
    return f"<p>{escape(value)}</p>"


def _pages(count: int, size: int) -> list[range]:
    return [range(start, min(start + size, count)) for start in range(0, count, size)]


def _attrs(values: dict[str, object]) -> str:
    return " ".join(f'{key}="{escape(str(value), quote=True)}"' for key, value in values.items())


class _Plot:
    """Small SVG surface using the same numeric-axis policy as other stored reports."""

    def __init__(
        self,
        title: str,
        x_label: str,
        y_label: str,
        x_ticks: Sequence[tuple[float, str]],
        y_values: Sequence[float],
        legend: Sequence[str] = (),
        *,
        part_tick_ids: Mapping[float, str] | None = None,
    ) -> None:
        if not x_ticks or not y_values:
            raise ValueError("analysis_report_payload_invalid")
        values = [report_number(value) for value in y_values]
        self.xmin, self.xmax = x_ticks[0][0] - 0.5, x_ticks[-1][0] + 0.5
        self.ymin, self.ymax = padded_range(min(values), max(values))
        if self.ymax <= self.ymin:
            raise ValueError("analysis_report_payload_invalid")
        self.clip = (
            "gage-"
            + sha256(repr((title, x_ticks, self.ymin, self.ymax)).encode("utf-8")).hexdigest()[:16]
        )
        self.axis_description = f"{x_label} / {y_label}"
        height = 305 + 18 * len(legend)
        self.parts = [
            f'<svg role="img" aria-label="{escape(title, quote=True)}" viewBox="0 0 560 {height}" '
            f'data-x-min="{self.xmin!r}" data-x-max="{self.xmax!r}" '
            f'data-y-min="{self.ymin!r}" data-y-max="{self.ymax!r}">'
            f"<title>{escape(title)}</title><desc>{escape(x_label)} / {escape(y_label)}</desc>",
            f'<defs><clipPath id="{self.clip}"><rect x="80" y="32" width="455" height="208"/>'
            "</clipPath></defs>",
            '<path d="M80 32V240H535" fill="none" stroke="#637083"/>',
        ]
        for x, label in x_ticks:
            lines = label.split("\n")
            part_id = None if part_tick_ids is None else part_tick_ids.get(x)
            identity = _attrs({"data-gage-part-id": part_id}) if part_id is not None else ""
            self.parts.append(
                f'<text x="{self.sx(x):.6f}" y="257" text-anchor="middle" '
                f'font-size="11" {identity}>'
            )
            if part_id is not None:
                self.parts.append(f"<title>{escape(part_id)}</title>")
            for index, line in enumerate(lines):
                self.parts.append(
                    f'<tspan x="{self.sx(x):.6f}" dy="{0 if index == 0 else 13}">'
                    f"{escape(line)}</tspan>"
                )
            self.parts.append("</text>")
        plan = numeric_axis_plan(self.ymin, self.ymax, 4)
        if plan.offset:
            self.parts.append(
                f'<text x="80" y="17" font-size="11" data-axis-offset="{plan.offset!r}">'
                f"<title>{escape(y_label)}</title>y: {plan.offset:+.17g}</text>"
            )
        for value, label in numeric_axis_ticks(plan):
            self.parts.append(
                f'<text x="73" y="{self.sy(value)+4:.6f}" text-anchor="end" font-size="11">'
                f"{escape(label)}</text>"
            )
        self.parts.extend(
            (
                '<text x="307" y="291" text-anchor="middle" font-size="12">'
                f"<title>{escape(x_label)}</title>{escape(short_label(x_label, 48))}</text>",
                '<text transform="translate(15 136) rotate(-90)" '
                'text-anchor="middle" font-size="12">'
                f"<title>{escape(y_label)}</title>{escape(short_label(y_label, 25))}</text>",
            )
        )
        for index, label in enumerate(legend):
            color = _COLORS[index % len(_COLORS)]
            self.parts.append(
                f'<line x1="80" x2="97" y1="{305 + index*18}" y2="{305 + index*18}" '
                f'stroke="{color}"/>'
                f'<text x="104" y="{309 + index*18}" font-size="11">{escape(label)}</text>'
            )

    def sx(self, value: float) -> float:
        return 80 + numeric_fraction(value, self.xmin, self.xmax) * 455

    def sy(self, value: float) -> float:
        return 240 - numeric_fraction(report_number(value), self.ymin, self.ymax) * 208

    def point(
        self,
        x: float,
        y: float,
        title: str,
        *,
        color: str = _COLORS[0],
        shape: str = "circle",
        attrs: dict[str, object] | None = None,
    ) -> None:
        geometry = (
            f'<rect x="{self.sx(x)-3:.6f}" y="{self.sy(y)-3:.6f}" width="6" height="6"'
            if shape == "square"
            else f'<circle cx="{self.sx(x):.6f}" cy="{self.sy(y):.6f}" r="2.5"'
        )
        tag = "rect" if shape == "square" else "circle"
        self.parts.append(
            f'{geometry} fill="{color}" clip-path="url(#{self.clip})" '
            f'data-x="{x!r}" data-y="{y!r}" {_attrs(attrs or {})}>'
            f"<title>{escape(title)}: {y!r}</title></{tag}>"
        )

    def line(self, points: Sequence[tuple[float, float]], color: str) -> None:
        path = " ".join(f"{self.sx(x):.6f},{self.sy(y):.6f}" for x, y in points)
        self.parts.append(
            f'<polyline points="{path}" fill="none" stroke="{color}" '
            f'clip-path="url(#{self.clip})"/>'
        )

    def reference(self, key: str, value: float, label: str) -> None:
        self.parts.append(
            f'<line x1="80" x2="535" y1="{self.sy(value):.6f}" y2="{self.sy(value):.6f}" '
            f'stroke="#637083" stroke-dasharray="5 3" data-reference="{key}" '
            f'data-value="{value!r}">'
            f"<title>{escape(label)}: {value!r}</title></line>"
        )

    def finish(self) -> str:
        return "".join(self.parts) + "</svg>" + _paragraph(self.axis_description)


def _component_chart(items: Sequence[GageComponentPlotItem], locale: ReportLocale) -> str:
    labels = (
        _text(locale, "Total Gage\nR&R", "총 Gage\nR&R"),
        _text(locale, "Repeatability", "반복성"),
        _text(locale, "Reproducibility", "재현성"),
        _text(locale, "Part-to-part", "부품 간"),
    )
    metrics = (
        ("percent_contribution", _text(locale, "% Contribution", "% 기여율")),
        ("percent_study_variation", _text(locale, "% Study Variation", "% 연구 변동")),
    )
    plot = _Plot(
        _text(locale, "Components of Variation", "변동 성분"),
        _text(locale, "Component", "성분"),
        "%",
        list(enumerate(labels)),
        [0.0, *[report_number(getattr(item, metric)) for item in items for metric, _ in metrics]],
        [label for _, label in metrics],
    )
    for index, item in enumerate(items):
        for metric_index, (metric, label) in enumerate(metrics):
            value = report_number(getattr(item, metric))
            lower = index - 0.35 + metric_index * 0.35
            plot.parts.append(
                f'<rect x="{plot.sx(lower):.6f}" y="{plot.sy(value):.6f}" '
                f'width="{plot.sx(lower+0.3)-plot.sx(lower):.6f}" '
                f'height="{plot.sy(0)-plot.sy(value):.6f}" '
                f'fill="{_COLORS[metric_index]}" data-component="{item.component}" '
                f'data-metric="{metric}" data-value="{value!r}"><title>'
                f'{escape(labels[index].replace(chr(10), " "))} / '
                f"{escape(label)}: {value!r}%</title></rect>"
            )
    return (
        plot.finish()
        + report_table(
            [
                _text(locale, "Component", "성분"),
                _text(locale, "Variance", "분산"),
                "SD",
                *[label for _, label in metrics],
            ],
            [
                [
                    labels[index].replace("\n", " "),
                    item.final_variance,
                    item.standard_deviation,
                    item.percent_contribution,
                    item.percent_study_variation,
                ]
                for index, item in enumerate(items)
            ],
        )
        + _paragraph(
            _text(
                locale,
                "Saved final components are shown without renormalizing either percentage series. "
                "% Study Variation is a ratio of SDs; these overlapping components "
                "are not additive.",
                "저장된 최종 성분을 두 백분율의 재정규화 없이 표시합니다. "
                "% 연구 변동은 표준편차의 비율이며 겹치는 성분을 더하는 비율이 아닙니다.",
            )
        )
    )


def _part_label(bundle: GageRrPlotBundle, index: int, locale: ReportLocale) -> str:
    if bundle.schema_version == 2:
        part_id = bundle.parts[index].part_id
        if part_id is None:
            raise ValueError("analysis_report_payload_invalid")
        return part_id
    return f'{_text(locale, "Display", "표시 번호")} {index+1}'


def _part_tick_label(bundle: GageRrPlotBundle, index: int, limit: int) -> str:
    return (
        short_label(_part_label(bundle, index, "en"), limit)
        if bundle.schema_version == 2
        else str(index + 1)
    )


def _part_axis(bundle: GageRrPlotBundle, locale: ReportLocale) -> str:
    return (
        _text(locale, "Part ID", "부품 ID")
        if bundle.schema_version == 2
        else _text(locale, "Part display number", "부품 표시 번호")
    )


def _part_identity_attrs(bundle: GageRrPlotBundle, index: int) -> dict[str, object]:
    return (
        {"data-gage-part-id": _part_label(bundle, index, "en")}
        if bundle.schema_version == 2
        else {}
    )


def _identity_note(bundle: GageRrPlotBundle, locale: ReportLocale) -> str:
    return _paragraph(
        _text(
            locale,
            "Part IDs are the original saved identities. Axis labels may be shortened; "
            "the complete IDs appear in point descriptions and the tables below. "
            "O1/O2 are display numbers; original operator and replicate IDs remain redacted.",
            "부품 ID는 저장된 원래 식별자입니다. 축 이름은 짧게 표시할 수 있으며 "
            "점 설명과 아래 표에서 전체 ID를 확인할 수 있습니다. "
            "O1/O2는 표시 번호이고 원래 작업자와 반복 ID는 비식별화 상태를 유지합니다.",
        )
        if bundle.schema_version == 2
        else _text(
            locale,
            "Display 1 / Display 2 are part display numbers, not original IDs. "
            "Original part IDs were not stored "
            "in this historical result. Reanalysis is required to display original part IDs; "
            "the stored index/value mapping is unchanged. O1/O2 are redacted operator numbers.",
            "표시 번호 1 / 표시 번호 2는 원래 ID가 아닌 부품 표시 번호입니다. "
            "이 과거 결과에는 원래 부품 ID가 저장되지 "
            "않았습니다. 원래 부품 ID를 표시하려면 재분석이 필요하며 저장된 번호와 값의 연결은 "
            "그대로 유지됩니다. O1/O2는 비식별 작업자 번호입니다.",
        )
    )


def _page_heading(
    bundle: GageRrPlotBundle, parts: range, operators: range, locale: ReportLocale
) -> str:
    part_range = (
        f'{_text(locale, "Part positions", "부품 표시 위치")} {parts.start+1}-{parts.stop}'
        if bundle.schema_version == 2
        else f"{_part_axis(bundle, locale)} {parts.start+1}-{parts.stop}"
    )
    return (
        f"<h4>{escape(part_range)}; "
        f'{escape(_text(locale, "Operators", "작업자"))} '
        f"O{operators.start+1}-O{operators.stop}</h4>"
    )


def _measurement_bounds(bundle: GageRrPlotBundle) -> list[float]:
    return [bundle.measurement_range.minimum, bundle.measurement_range.maximum]


def _cell_charts(
    bundle: GageRrPlotBundle, key: str, locale: ReportLocale, title: str, ylabel: str
) -> str:
    plot_data = bundle.dispersion if key == "dispersion" else bundle.xbar
    limits = [
        (name, report_number(getattr(plot_data, name)))
        for name in ("center", "lower_limit", "upper_limit")
    ]
    y_values = [report_number(point.value) for point in plot_data.points] + [
        value for _, value in limits
    ]
    result: list[str] = [_identity_note(bundle, locale)]
    for parts in _pages(bundle.counts.part_count, 5):
        for operators in _pages(bundle.counts.operator_count, 3):
            x_ticks = [
                (float(j * (len(parts) + 1) + i), _part_tick_label(bundle, p, 4))
                for j, _ in enumerate(operators)
                for i, p in enumerate(parts)
            ]
            plot = _Plot(
                title + f" {parts.start}/{operators.start}",
                _part_axis(bundle, locale) + " / " + _text(locale, "Operator", "작업자"),
                ylabel,
                x_ticks,
                y_values,
                [f"O{o+1}" for o in operators],
                part_tick_ids={
                    float(j * (len(parts) + 1) + i): _part_label(bundle, p, locale)
                    for j, _ in enumerate(operators)
                    for i, p in enumerate(parts)
                }
                if bundle.schema_version == 2
                else None,
            )
            for name, value in limits:
                plot.reference(
                    name, value, {"center": "CL", "lower_limit": "LCL", "upper_limit": "UCL"}[name]
                )
            for j, operator in enumerate(operators):
                points = {
                    point.part_index: point
                    for point in plot_data.points
                    if point.operator_index == operator
                }
                series = []
                plot.parts.append(
                    f'<text x="{plot.sx(j*(len(parts)+1)+(len(parts)-1)/2):.6f}" y="27" '
                    f'text-anchor="middle" font-size="11">O{operator+1}</text>'
                )
                for i, part in enumerate(parts):
                    point = points[part]
                    x, y = float(j * (len(parts) + 1) + i), report_number(point.value)
                    series.append((x, y))
                    outside = getattr(
                        point,
                        "outside_limits",
                        getattr(point, "outside_repeatability_limits", False),
                    )
                    plot.point(
                        x,
                        y,
                        f"{_part_label(bundle, part, locale)} / O{operator+1}; n={point.n}",
                        color=_COLORS[j],
                        shape="square" if outside else "circle",
                        attrs={
                            **_part_identity_attrs(bundle, part),
                            "data-part-index": part,
                            "data-operator-index": operator,
                            "data-role": key,
                        },
                    )
                plot.line(series, _COLORS[j])
            result.extend((_page_heading(bundle, parts, operators, locale), plot.finish()))
    result.append(
        report_table(
            [_text(locale, "Limit", "한계"), _text(locale, "Stored value", "저장된 값")],
            [
                [{"center": "CL", "lower_limit": "LCL", "upper_limit": "UCL"}[key], value]
                for key, value in limits
            ],
        )
    )
    result.append(
        report_table(
            [_part_axis(bundle, locale), _text(locale, "Operator", "작업자"), "n", ylabel],
            [
                [
                    _part_label(bundle, point.part_index, locale),
                    f"O{point.operator_index+1}",
                    point.n,
                    point.value,
                ]
                for point in plot_data.points
            ],
        )
    )
    if key == "dispersion":
        result.append(
            _paragraph(
                _text(
                    locale,
                    "R uses saved within-cell ranges and three-decimal D3/D4 constants "
                    "for 2-8 repeats. "
                    "At 9+ repeats, S uses saved sample SDs and full-precision log-gamma c4/B3/B4. "
                    "Squares mark points outside the stored diagnostic limits; "
                    "limits are not specifications.",
                    "반복 2~8회는 셀 내 범위와 소수 셋째 자리 D3/D4 상수의 R을 사용합니다. "
                    "9회 이상은 표본 표준편차와 log-gamma c4/B3/B4의 S를 사용합니다. "
                    "사각형은 저장 진단한계 밖의 점이며 한계는 규격이 아닙니다.",
                )
            )
        )
        result.append(
            report_table(
                [_text(locale, "Constant", "상수"), _text(locale, "Stored value", "저장된 값")],
                [
                    [name, value]
                    for name, value in bundle.dispersion.constants.model_dump().items()
                    if value is not None
                ],
            )
        )
        if "within_cell_variation_zero" in bundle.dispersion.warning_codes:
            result.append(
                _paragraph(
                    _text(
                        locale,
                        "Within-cell variation is zero; "
                        "no positive repeatability dispersion is evidenced.",
                        "셀 내 변동이 0이며 양의 반복성 산포가 확인되지 않았습니다.",
                    )
                )
            )
    else:
        result.append(
            _paragraph(
                _text(
                    locale,
                    "Xbar limits use repeatability variance from the selected ANOVA, "
                    "not an Rbar estimate. This is a part-discrimination diagnostic: "
                    "a point outside these limits is not by itself a process-fault signal.",
                    "Xbar 한계는 Rbar 추정치가 아닌 선택된 ANOVA 반복성 분산을 사용합니다. "
                    "이는 부품 구별력 진단이며 한계 밖의 점만으로 공정 이상을 판정하지 않습니다.",
                )
            )
        )
    return "".join(result)


def _part_charts(
    bundle: GageRrPlotBundle, locale: ReportLocale, title: str, ylabel: str, *, interaction: bool
) -> str:
    result: list[str] = [_identity_note(bundle, locale)]
    means = {part.part_index: part for part in bundle.parts}
    for parts in _pages(bundle.counts.part_count, 10):
        for operators in _pages(bundle.counts.operator_count, 3):
            legend = [f"O{operator+1}" for operator in operators]
            if not interaction:
                legend += [
                    _text(
                        locale, "Squares: all-operator part means", "사각형: 전체 작업자 부품 평균"
                    )
                ]
            plot = _Plot(
                title + f" {parts.start}/{operators.start}",
                _part_axis(bundle, locale),
                ylabel,
                [(float(part), _part_tick_label(bundle, part, 6)) for part in parts],
                _measurement_bounds(bundle),
                legend,
                part_tick_ids={float(part): _part_label(bundle, part, locale) for part in parts}
                if bundle.schema_version == 2
                else None,
            )
            source = bundle.interaction.points if interaction else bundle.response_by_part.points
            for j, operator in enumerate(operators):
                series = []
                for point in source:
                    if point.part_index not in parts or point.operator_index != operator:
                        continue
                    y = report_number(getattr(point, "mean" if interaction else "value"))
                    x = float(point.part_index)
                    series.append((x, y))
                    plot.point(
                        x,
                        y,
                        f"{_part_label(bundle, point.part_index, locale)} / O{operator+1}",
                        color=_COLORS[j],
                        attrs={
                            **_part_identity_attrs(bundle, point.part_index),
                            "data-part-index": point.part_index,
                            "data-operator-index": operator,
                            "data-role": "cell_mean" if interaction else "measurement",
                        },
                    )
                if interaction:
                    plot.line(sorted(series), _COLORS[j])
            if not interaction:
                for part in parts:
                    plot.point(
                        float(part),
                        report_number(means[part].mean),
                        f"{_part_label(bundle, part, locale)}; n={means[part].n}",
                        color="#172033",
                        shape="square",
                        attrs={
                            "data-role": "part_mean",
                            "data-part-index": part,
                            **_part_identity_attrs(bundle, part),
                        },
                    )
            result.extend((_page_heading(bundle, parts, operators, locale), plot.finish()))
    if interaction:
        result.append(
            _paragraph(
                _text(
                    locale,
                    "Lines connect actual stored cell means, "
                    "including when the interaction was pooled. "
                    "They are not fitted additive means; "
                    "visible nonparallelism alone is not a significance test.",
                    "선은 교호작용을 풀링한 경우에도 실제 저장 셀 평균을 연결합니다. "
                    "가법모형 적합 평균이 아니며 비평행 모양만으로 유의성을 판단하지 않습니다.",
                )
            )
        )
        result.append(
            report_table(
                [
                    _part_axis(bundle, locale),
                    _text(locale, "Operator", "작업자"),
                    "n",
                    _text(locale, "Cell mean", "셀 평균"),
                ],
                [
                    [
                        _part_label(bundle, point.part_index, locale),
                        f"O{point.operator_index+1}",
                        point.n,
                        point.mean,
                    ]
                    for point in bundle.interaction.points
                ],
            )
        )
    else:
        counts = bundle.counts
        result.append(
            _paragraph(
                _text(
                    locale,
                    f"Displayed raw observations: {counts.displayed_raw_point_count} / "
                    f"{counts.raw_point_count}. "
                    "The saved deterministic cell-stratified display cap "
                    "does not change any full-data mean or summary. All part/operator pages "
                    "are included; source row order is not a measurement-time axis.",
                    f"표시 원관측점: {counts.displayed_raw_point_count} / "
                    f"{counts.raw_point_count}. "
                    "저장된 결정적 셀별 표시 제한은 전체 자료 평균과 요약을 바꾸지 않습니다. "
                    "모든 부품/작업자 페이지를 포함하며 원본 행 순서는 측정 시간축이 아닙니다.",
                )
            )
        )
        result.append(
            '<div data-gage-part-summary="true">'
            + report_table(
                [_part_axis(bundle, locale), "n", _text(locale, "Part mean", "부품 평균")],
                [
                    [_part_label(bundle, part.part_index, locale), part.n, part.mean]
                    for part in bundle.parts
                ],
            )
            + "</div>"
        )
    return "".join(result)


def _operator_charts(
    bundle: GageRrPlotBundle, locale: ReportLocale, title: str, ylabel: str
) -> str:
    result = []
    for operators in _pages(bundle.counts.operator_count, 6):
        plot = _Plot(
            title + f" {operators.start}",
            _text(locale, "Operator", "작업자"),
            ylabel,
            [(float(operator), f"O{operator+1}") for operator in operators],
            _measurement_bounds(bundle),
        )
        for operator in operators:
            box = bundle.response_by_operator.boxes[operator]
            q1, q3 = report_number(box.q1), report_number(box.q3)
            low, high = report_number(box.lower_whisker), report_number(box.upper_whisker)
            x = float(operator)
            plot.parts.append(
                f'<line x1="{plot.sx(x):.6f}" x2="{plot.sx(x):.6f}" '
                f'y1="{plot.sy(low):.6f}" y2="{plot.sy(high):.6f}" stroke="{_COLORS[0]}" '
                f'data-box-whisker="{operator}" data-lower="{low!r}" data-upper="{high!r}">'
                f"<title>O{operator+1}: {low!r}, {high!r}</title></line>"
                f'<rect x="{plot.sx(x-0.22):.6f}" y="{plot.sy(q3):.6f}" '
                f'width="{plot.sx(x+0.22)-plot.sx(x-0.22):.6f}" '
                f'height="{plot.sy(q1)-plot.sy(q3):.6f}" fill="#d9e7f6" stroke="{_COLORS[0]}" '
                f'data-box-operator="{operator}" data-q1="{q1!r}" data-q3="{q3!r}">'
                f"<title>O{operator+1}: Q1={q1!r}, Q3={q3!r}</title></rect>"
            )
            for key, value in (
                ("lower_whisker", low),
                ("upper_whisker", high),
                ("median", report_number(box.median)),
            ):
                plot.parts.append(
                    f'<line x1="{plot.sx(x-0.22):.6f}" x2="{plot.sx(x+0.22):.6f}" '
                    f'y1="{plot.sy(value):.6f}" y2="{plot.sy(value):.6f}" stroke="#172033" '
                    f'data-box-statistic="{key}" data-value="{value!r}"/>'
                )
            plot.point(
                x,
                report_number(box.mean),
                _text(locale, "Mean", "평균"),
                shape="square",
                color="#26775a",
            )
            for point in box.outliers:
                plot.point(
                    x,
                    point.value,
                    f"O{operator+1}; " + _text(locale, "Stored outlier", "저장 이상치"),
                    color="#a9442f",
                    attrs={"data-role": "outlier"},
                )
        result.append(plot.finish())
    result.append(
        _paragraph(
            _text(
                locale,
                "Boxes use all individual observations: type-7 quartiles, "
                "observed whiskers within 1.5 IQR fences, median line and square mean. "
                "Circles show saved displayed outliers; total outlier counts below may exceed "
                "displayed counts. All pages share bounds from the full measurement range, "
                "including undisplayed outliers.",
                "상자는 모든 개별 관측으로 계산한 type-7 사분위수, "
                "1.5 IQR 울타리 안의 실제 관측 수염, 중앙값 선과 사각형 평균입니다. "
                "원은 저장된 표시 이상치이며 전체 이상치 수가 표시 수보다 클 수 있습니다. "
                "모든 페이지의 범위는 미표시 이상치를 포함한 전체 측정 범위를 공유합니다.",
            )
        )
    )
    result.append(
        report_table(
            [
                _text(locale, "Operator", "작업자"),
                "n",
                _text(locale, "Mean", "평균"),
                "Q1",
                _text(locale, "Median", "중앙값"),
                "Q3",
                _text(locale, "Lower whisker", "아래 수염"),
                _text(locale, "Upper whisker", "위 수염"),
                _text(locale, "Total outliers", "전체 이상치"),
                _text(locale, "Displayed outliers", "표시 이상치"),
            ],
            [
                [
                    f"O{box.operator_index+1}",
                    box.n,
                    box.mean,
                    box.q1,
                    box.median,
                    box.q3,
                    box.lower_whisker,
                    box.upper_whisker,
                    box.outlier_count,
                    box.displayed_outlier_count,
                ]
                for box in bundle.response_by_operator.boxes
            ],
        )
    )
    return "".join(result)


def gage_rr_plot_sections(
    payload: dict[str, Any], locale: ReportLocale = "en"
) -> tuple[ReportSection, ...]:
    titles = (
        _text(locale, "Components of Variation", "변동 성분"),
        _text(locale, "Response by Part", "부품별 반응"),
        _text(locale, "Within-cell Dispersion by Operator", "작업자별 셀 내 산포"),
        _text(locale, "Response by Operator", "작업자별 반응"),
        _text(locale, "Xbar Chart by Operator", "작업자별 Xbar 관리도"),
        _text(locale, "Part by Operator Interaction", "부품과 작업자 교호작용"),
    )
    if payload.get("schema_version") in (1, 2):
        components = payload.get("variance_components", {})
        try:
            items = [
                GageComponentPlotItem.model_validate(
                    {
                        "component": key,
                        **{
                            name: components[key][name]
                            for name in (
                                "final_variance",
                                "standard_deviation",
                                "percent_contribution",
                                "percent_study_variation",
                            )
                        },
                    },
                    strict=True,
                )
                for key in _COMPONENTS
            ]
            markup = _component_chart(items, locale)
        except (KeyError, TypeError, ValueError):
            markup = None
        if markup:
            markup += _paragraph(
                _text(
                    locale,
                    "Reanalysis is required for the other five charts: "
                    "this historical result stores variance components but not the raw-display "
                    "or cell/box summaries. No source rows were read and no result was rewritten.",
                    "다른 다섯 그래프는 재분석이 필요합니다. 이 과거 결과에는 분산 성분만 있고 "
                    "원관측 표시점 및 셀/상자 요약이 없습니다. "
                    "원자료를 읽거나 기존 결과를 다시 쓰지 않았습니다.",
                )
            )
        reason = "gage_plot_bundle_not_stored_reanalysis_required"
        return tuple(
            ReportSection(
                key,
                title,
                "rendered" if index == 0 and markup else "missing",
                markup if index == 0 else None,
                None if index == 0 and markup else reason,
            )
            for index, (key, title) in enumerate(zip(GAGE_PLOT_SECTION_IDS, titles, strict=True))
        )
    validate_gage_rr_plot_result(payload)
    bundle = GageRrPlotBundle.model_validate(payload["plot_bundle"], strict=True)
    ylabel = report_column_label(
        bundle.measurement.model_dump(), _text(locale, "Measurement", "측정값")
    )
    range_title = (
        _text(locale, "R Chart by Operator", "작업자별 R 관리도")
        if bundle.dispersion.statistic == "range"
        else _text(locale, "S Chart by Operator", "작업자별 S 관리도")
    )
    titles = (*titles[:2], range_title, *titles[3:])
    plots = (
        bundle.components,
        bundle.response_by_part,
        bundle.dispersion,
        bundle.response_by_operator,
        bundle.xbar,
        bundle.interaction,
    )
    renderers = (
        lambda: _component_chart(bundle.components.items, locale) + _identity_note(bundle, locale),
        lambda: _part_charts(bundle, locale, titles[1], ylabel, interaction=False),
        lambda: _cell_charts(
            bundle,
            "dispersion",
            locale,
            titles[2],
            (
                _text(locale, "Range", "범위")
                if bundle.dispersion.statistic == "range"
                else _text(locale, "Sample SD", "표본 표준편차")
            )
            + (f" ({bundle.measurement.unit})" if bundle.measurement.unit else ""),
        ),
        lambda: _operator_charts(bundle, locale, titles[3], ylabel),
        lambda: _cell_charts(bundle, "xbar", locale, titles[4], ylabel),
        lambda: _part_charts(bundle, locale, titles[5], ylabel, interaction=True),
    )
    return tuple(
        ReportSection(key, title, "rendered", render())
        if plot.status == "available"
        else ReportSection(key, title, "missing", reason="gage_saved_plot_summary_unavailable")
        for key, title, plot, render in zip(
            GAGE_PLOT_SECTION_IDS, titles, plots, renderers, strict=True
        )
    )
