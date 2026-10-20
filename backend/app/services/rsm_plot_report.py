"""Render stored contour geometry; export never evaluates a model."""

from __future__ import annotations

from html import escape
from uuid import uuid4

from app.api.v1.schemas.rsm_plots import RsmPlotBundle
from app.i18n.report_text import ReportLocale
from app.services.report_numeric_axis import numeric_axis_plan, numeric_axis_ticks, numeric_fraction
from app.services.stored_report_primitives import report_plot, report_table

CONTOUR_COLORS = (
    "#eef5fa",
    "#d6e9f2",
    "#afd5e4",
    "#80bacf",
    "#519cb6",
    "#2d7c99",
    "#225d79",
    "#1a455f",
    "#16354b",
    "#112a3e",
    "#0d2031",
    "#091723",
)


def rsm_plot_report(bundle: RsmPlotBundle, locale: ReportLocale) -> str:
    def text(ko: str, en: str) -> str:
        return ko if locale == "ko" else en

    def axis(name: str, unit: str | None) -> str:
        suffix = unit if bundle.settings.axis_scale == "actual" else text("코딩값", "Coded")
        return name + (f" ({suffix})" if suffix else "")

    x_label = axis(bundle.x_axis.name, bundle.x_axis.unit)
    response_label = bundle.response_name + (
        f" ({bundle.response_unit})" if bundle.response_unit else ""
    )
    held = report_table(
        [text("고정 요인", "Held factor"), text("실제값", "Actual value")],
        list(bundle.held_actual_values.items()),
    )
    note = (
        "<p>"
        + escape(
            text(
                "최종 저장 모형의 조건부 적합값입니다. 빗금 영역은 전체 설계 convex hull 밖입니다. "
                "실험점은 현재 고정 조건의 점과 다른 조건의 2D 투영을 구분합니다.",
                "Conditional fitted values from the stored final model. Hatching marks areas "
                "outside the full design convex hull. Slice observations and other-condition "
                "2D projections are distinguished.",
            )
        )
        + "</p>"
    )
    if bundle.geometry is None:
        note = (
            "<p>"
            + escape(
                text(
                    "최종 저장 모형의 조건부 적합값입니다. 표에서 전체 설계 convex hull 밖의 "
                    "값을 구분합니다. 관측한 자료평균이 아닙니다.",
                    "Conditional fitted values from the stored final model, not observed "
                    "data means. The table identifies values outside the full design convex hull.",
                )
            )
            + "</p>"
        )
        series = [
            (
                response_label
                if curve.trace_actual_value is None
                else (
                    f"{bundle.y_axis.name if bundle.y_axis else ''} "
                    f"= {curve.trace_actual_value!r}"
                ),
                [(point.x, point.predicted, point.point_id) for point in curve.points],
            )
            for curve in bundle.curves
        ]
        return (
            held
            + note
            + report_plot(
                text("조건부 적합 곡선", "Conditional fitted curves"),
                x_label,
                response_label,
                series,
                lines=True,
            )
            + report_table(
                [
                    text("계열", "Series"),
                    x_label,
                    response_label,
                    text("설계 hull 밖", "Outside design hull"),
                ],
                [
                    (series[index][0], point.x, point.predicted, point.outside_design_hull)
                    for index, curve in enumerate(bundle.curves)
                    for point in curve.points
                ],
            )
        )
    assert bundle.y_axis is not None
    y_label = axis(bundle.y_axis.name, bundle.y_axis.unit)
    xmin, xmax = bundle.x_axis.minimum, bundle.x_axis.maximum
    ymin, ymax = bundle.y_axis.minimum, bundle.y_axis.maximum
    geometry = bundle.geometry
    level_labels = [f"{level:.7g}" for level in geometry.levels]
    precise_levels = len(set(level_labels)) != len(level_labels)

    def level_label(value: float) -> str:
        return repr(value) if precise_levels else f"{value:.7g}"

    identity = uuid4().hex

    def sx(value: float) -> float:
        return 75 + 450 * numeric_fraction(value, xmin, xmax)

    def sy(value: float) -> float:
        return 325 - 290 * numeric_fraction(value, ymin, ymax)

    def path(vertices: list[tuple[float, float]], close: bool = False) -> str:
        if not vertices:
            return ""
        return (
            "M" + "L".join(f"{sx(x):.5f},{sy(y):.5f}" for x, y in vertices) + ("Z" if close else "")
        )

    parts = [
        f'<svg role="img" aria-label="{escape(response_label, quote=True)}" '
        'viewBox="0 0 640 410" data-rsm-contour="stored-geometry">'
        f"<title>{escape(response_label)}</title><desc>{escape(x_label)}; {escape(y_label)}</desc>",
        f'<defs><clipPath id="clip-{identity}"><rect x="75" y="35" width="450" height="290"/>'
        f'</clipPath><pattern id="hatch-{identity}" width="8" height="8" '
        'patternUnits="userSpaceOnUse">'
        '<path d="M0 8L8 0" stroke="#454f5e" stroke-opacity=".5" stroke-width="1"/>'
        "</pattern></defs>",
        f'<g clip-path="url(#clip-{identity})">',
    ]
    if bundle.settings.filled:
        for index, band in enumerate(geometry.bands):
            color = CONTOUR_COLORS[
                round(index * (len(CONTOUR_COLORS) - 1) / max(1, len(geometry.bands) - 1))
            ]
            for polygon in band.polygons:
                parts.append(
                    f'<path d="{"".join(path(ring, True) for ring in polygon.rings)}" '
                    f'fill="{color}" fill-rule="evenodd" data-band="{index}"/>'
                )
    if bundle.settings.lines:
        for line in geometry.lines:
            for vertices in line.paths:
                parts.append(
                    f'<path d="{path(vertices)}" fill="none" stroke="#273340" '
                    f'stroke-width="1" data-level="{line.level!r}">'
                    f"<title>{line.level!r}</title></path>"
                )
                if vertices:
                    x, y = vertices[len(vertices) // 2]
                    parts.append(
                        f'<text x="{sx(x):.3f}" y="{sy(y):.3f}" font-size="10" '
                        f'fill="#111" stroke="#fff" stroke-width="2" paint-order="stroke">'
                        f"{level_label(line.level)}</text>"
                    )
    outer = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
    parts.append(
        f'<path d="{path(outer, True)}{path(bundle.hull_slice_polygon, True)}" '
        f'fill="url(#hatch-{identity})" fill-rule="evenodd"/>'
    )
    if bundle.settings.design_points:
        for point in bundle.design_points:
            point_kind = (
                text("현재 단면", "On slice") if point.on_slice else text("투영", "Projection")
            )
            parts.append(
                f'<circle cx="{sx(point.x):.3f}" cy="{sy(point.y):.3f}" r="3" '
                f'fill="{"#111" if point.on_slice else "#fff"}" stroke="#111" '
                f'data-on-slice="{str(point.on_slice).lower()}">'
                f"<title>{point.run_order}: {point_kind}"
                "</title></circle>"
            )
    parts.append('</g><path d="M75 35V325H525" fill="none" stroke="#637083"/>')
    for name, low, high in (("x", xmin, xmax), ("y", ymin, ymax)):
        plan = numeric_axis_plan(low, high)
        for value, label in numeric_axis_ticks(plan):
            parts.append(
                f'<text x="{sx(value) if name == "x" else 68:.3f}" '
                f'y="{345 if name == "x" else sy(value)+3:.3f}" '
                f'text-anchor="{"middle" if name == "x" else "end"}" font-size="10">'
                f"{escape(label)}</text>"
            )
        if plan.offset:
            parts.append(
                f'<text x="75" y="{15 if name == "x" else 28}" font-size="10" '
                f'data-axis-offset="{plan.offset!r}">{name}: {plan.offset:+.17g}</text>'
            )
    parts += [
        f'<text x="300" y="373" text-anchor="middle" font-size="12">{escape(x_label)}</text>',
        '<text transform="translate(16 180) rotate(-90)" text-anchor="middle" font-size="12">'
        f"{escape(y_label)}</text>",
    ]
    for index, band in enumerate(geometry.bands):
        color = CONTOUR_COLORS[round(index * 11 / max(1, len(geometry.bands) - 1))]
        lower_label = "-inf" if band.lower is None else level_label(band.lower)
        upper_label = "+inf" if band.upper is None else level_label(band.upper)
        label = (
            f"{geometry.minimum:.7g}" if geometry.constant else f"{lower_label} .. {upper_label}"
        )
        parts.append(
            f'<rect x="537" y="{35+index*22}" width="12" height="14" fill="{color}"/>'
            f'<text x="553" y="{46+index*22}" font-size="9">{escape(label)}</text>'
        )
    parts.append(f'<text x="75" y="399" font-size="11">{escape(response_label)}</text></svg>')
    return (
        held
        + note
        + "".join(parts)
        + report_table(
            [x_label, y_label, response_label, text("설계 hull 밖", "Outside design hull")],
            [
                (point.x, point.y, point.predicted, point.outside_design_hull)
                for point in bundle.points
            ],
        )
    )
