"""Escaped tables and static SVG projections of already stored result values."""

from collections.abc import Sequence
from html import escape
from math import isfinite


def report_number(value: object) -> float:
    """Reject absent or invalid stored coordinates instead of drawing a false zero."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not isfinite(value):
        raise ValueError("analysis_report_payload_invalid")
    return float(value)


def report_column_label(column: dict[str, object], fallback: str) -> str:
    name = str(column.get("display_name") or fallback)
    return name + (f" ({column['unit']})" if column.get("unit") else "")


def report_value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("analysis_report_payload_invalid")
        return format(value, ".10g")
    return str(value)


def report_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(report_value(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return (
        f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def report_plot(
    title: str,
    x_label: str,
    y_label: str,
    series: Sequence[tuple[str, Sequence[tuple[float, float, str]]]],
    *,
    lines: bool = False,
    identity: bool = False,
    zero: bool = False,
    selected_x: float | None = None,
    x_ticks: Sequence[tuple[float, str]] | None = None,
    y_ticks: Sequence[tuple[float, str]] | None = None,
    square: bool = False,
    reference_lines: Sequence[tuple[str, float, str]] = (),
    reference_segments: Sequence[tuple[str, float, float, float, float]] = (),
    marker_shapes: Sequence[Sequence[str]] | None = None,
    vectors: Sequence[tuple[float, float, str, float, float]] = (),
    histogram_bins: Sequence[tuple[float, float, float, str]] = (),
) -> str:
    values = [(x, y) for _, points in series for x, y, _ in points]
    values += [(x, y) for x, y, _, _, _ in vectors]
    values += [
        (x, y)
        for lower, upper, value, _ in histogram_bins
        for x, y in ((lower, 0.0), (upper, value))
    ]
    point_count = len(values)
    values += [(x, y) for _, x1, y1, x2, y2 in reference_segments for x, y in ((x1, y1), (x2, y2))]
    if not values:
        return ""
    for x, y in values:
        report_number(x)
        report_number(y)
    if selected_x is not None:
        report_number(selected_x)
    if marker_shapes is not None and (
        len(marker_shapes) != len(series)
        or any(
            len(shapes) != len(points)
            for shapes, (_, points) in zip(marker_shapes, series, strict=True)
        )
    ):
        raise ValueError("analysis_report_payload_invalid")
    xmin, xmax = min(x for x, _ in values), max(x for x, _ in values)
    ymin, ymax = min(y for _, y in values), max(y for _, y in values)
    for axis, value, _ in reference_lines:
        report_number(value)
        if axis == "x":
            xmin, xmax = min(xmin, value), max(xmax, value)
        elif axis == "y":
            ymin, ymax = min(ymin, value), max(ymax, value)
        else:
            raise ValueError("analysis_report_payload_invalid")
    if zero:
        ymin, ymax = min(0, ymin), max(0, ymax)
    if identity:
        xmin = ymin = min(xmin, ymin)
        xmax = ymax = max(xmax, ymax)
    if square:
        bound = max(abs(xmin), abs(xmax), abs(ymin), abs(ymax)) or 1
        xmin = ymin = -bound
        xmax = ymax = bound
    bottom = 535 if square else 230
    height = bottom - 35
    xpad = (xmax - xmin or max(abs(xmin), 1)) * 0.06
    ypad = (ymax - ymin or max(abs(ymin), 1)) * 0.06
    xmin, xmax, ymin, ymax = xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad
    report_number(xmax - xmin)
    report_number(ymax - ymin)
    if xmax <= xmin or ymax <= ymin:
        raise ValueError("analysis_report_payload_invalid")

    def sx(x: float) -> float:
        return 75 + (x - xmin) / (xmax - xmin) * 500

    def sy(y: float) -> float:
        return bottom - (y - ymin) / (ymax - ymin) * height

    legend_count = len(series) + len(reference_lines) + len(reference_segments)
    parts = [
        f'<svg role="img" aria-label="{escape(title, quote=True)}" '
        f'viewBox="0 0 640 {bottom + 60 + legend_count * 17}">'
        f"<title>{escape(title)}</title>",
        f"<desc>{escape(x_label)} / {escape(y_label)}; {point_count} points</desc>",
        f'<g fill="none" stroke="#637083"><path d="M75 35V{bottom}H575"/></g>',
    ]
    for axis, specified, low, high in (("x", x_ticks, xmin, xmax), ("y", y_ticks, ymin, ymax)):
        ticks = (
            specified
            if specified is not None
            else [
                (low + (high - low) * (index / 4), f"{low + (high - low) * (index / 4):.4g}")
                for index in range(5)
            ]
        )
        for value, label in ticks:
            report_number(value)
            if axis == "x":
                parts.append(
                    f'<text x="{sx(value):.3f}" y="{bottom+19}" text-anchor="middle" '
                    f'font-size="10">{escape(label)}</text>'
                )
            else:
                parts.append(
                    f'<text x="68" y="{sy(value)+3:.3f}" text-anchor="end" '
                    f'font-size="10">{escape(label)}</text>'
                )
    parts += [
        f'<text x="325" y="{bottom+39}" text-anchor="middle" font-size="12">'
        f"<title>{escape(x_label)}</title>{escape(short_label(x_label, 44))}</text>",
        f'<text transform="translate(14 {(bottom+35)/2}) rotate(-90)" text-anchor="middle" '
        f'font-size="12"><title>{escape(y_label)}</title>'
        f"{escape(short_label(y_label, 24))}</text>",
    ]
    if zero:
        parts.append(
            f'<line x1="75" x2="575" y1="{sy(0):.3f}" y2="{sy(0):.3f}" '
            'stroke="#777" stroke-dasharray="4 3"/>',
        )
    if identity:
        parts.append(
            f'<line x1="75" x2="575" y1="{bottom}" y2="35" stroke="#777" stroke-dasharray="4 3"/>'
        )
    if selected_x is not None:
        parts.append(
            f'<line x1="{sx(selected_x):.3f}" x2="{sx(selected_x):.3f}" y1="35" '
            f'y2="{bottom}" stroke="#9e3e25" stroke-dasharray="3 3"/>'
        )
    for index, (axis, value, label) in enumerate(reference_lines):
        coordinates = (
            f'x1="{sx(value):.3f}" x2="{sx(value):.3f}" y1="35" y2="{bottom}"'
            if axis == "x"
            else f'x1="75" x2="575" y1="{sy(value):.3f}" y2="{sy(value):.3f}"'
        )
        parts.append(
            f'<line {coordinates} stroke="#777" stroke-dasharray="4 3" '
            f'data-reference-axis="{axis}" data-value="{value!r}">'
            f"<title>{escape(label)}: {value:.10g}</title></line>"
            f'<text x="75" y="{bottom+62+(len(series)+index)*17}" font-size="11">'
            f"{escape(label)}: {value:.10g}</text>"
        )
    for index, (label, x1, y1, x2, y2) in enumerate(reference_segments):
        legend_y = bottom + 62 + (len(series) + len(reference_lines) + index) * 17
        parts.append(
            f'<line x1="{sx(x1):.3f}" y1="{sy(y1):.3f}" '
            f'x2="{sx(x2):.3f}" y2="{sy(y2):.3f}" '
            f'stroke="#777" stroke-dasharray="4 3" '
            f'data-reference-segment="{escape(label, quote=True)}" '
            f'data-x1="{x1!r}" data-y1="{y1!r}" data-x2="{x2!r}" data-y2="{y2!r}">'
            f"<title>{escape(label)}: ({x1:.10g}, {y1:.10g}), "
            f"({x2:.10g}, {y2:.10g})</title></line>"
            f'<line x1="75" x2="95" y1="{legend_y-4}" y2="{legend_y-4}" '
            f'stroke="#777" stroke-dasharray="4 3"/>'
            f'<text x="102" y="{legend_y}" font-size="11">'
            f"<title>{escape(label)}</title>{escape(short_label(label, 60))}</text>"
        )
    for index, (label, points) in enumerate(series):
        color = ("#225aa7", "#26775a", "#a9442f", "#6d507e")[index % 4]
        if lines:
            coordinates = " ".join(f"{sx(x):.3f},{sy(y):.3f}" for x, y, _ in points)
            parts.append(f'<polyline points="{coordinates}" fill="none" stroke="{color}"/>')
        for point_index, (x, y, point_label) in enumerate(points):
            shape = marker_shapes[index][point_index] if marker_shapes is not None else "circle"
            if shape not in {"circle", "square", "diamond"}:
                raise ValueError("analysis_report_payload_invalid")
            geometry = (
                f'<rect x="{sx(x)-3:.3f}" y="{sy(y)-3:.3f}" width="6" height="6"'
                if shape == "square"
                else f'<polygon points="{sx(x):.3f},{sy(y)-4:.3f} {sx(x)+4:.3f},{sy(y):.3f} '
                f'{sx(x):.3f},{sy(y)+4:.3f} {sx(x)-4:.3f},{sy(y):.3f}"'
                if shape == "diamond"
                else f'<circle cx="{sx(x):.3f}" cy="{sy(y):.3f}" r="2.5"'
            )
            tag = {"circle": "circle", "square": "rect", "diamond": "polygon"}[shape]
            parts.append(
                f'{geometry} fill="{color}" data-marker="{shape}" '
                f'data-x="{x!r}" data-y="{y!r}"><title>{escape(point_label)}: '
                f"{x:.10g}, {y:.10g}</title></{tag}>"
            )
        parts.append(
            f'<text x="75" y="{bottom+62+index*17}" fill="{color}" font-size="11">'
            f"<title>{escape(label)}</title>{escape(short_label(label, 64))}</text>"
        )
    for lower, upper, value, label in histogram_bins:
        if upper <= lower or value < 0:
            raise ValueError("analysis_report_payload_invalid")
        parts.append(
            f'<rect x="{sx(lower):.3f}" y="{sy(value):.3f}" '
            f'width="{sx(upper)-sx(lower):.3f}" height="{sy(0)-sy(value):.3f}" '
            f'fill="#225aa7" fill-opacity="0.7" stroke="#fff" '
            f'data-lower="{lower!r}" data-upper="{upper!r}" data-value="{value!r}">'
            f"<title>{escape(label)}: [{lower:.10g}, {upper:.10g}], {value:.10g}</title></rect>"
        )
    for x, y, label, raw_x, raw_y in vectors:
        report_number(raw_x)
        report_number(raw_y)
        dx, dy = sx(x) - sx(0), sy(y) - sy(0)
        length = (dx * dx + dy * dy) ** 0.5
        ux, uy = (dx / length, dy / length) if length else (0.0, 0.0)
        arrow = (
            f"{sx(x):.3f},{sy(y):.3f} "
            f"{sx(x)-8*ux+3*uy:.3f},{sy(y)-8*uy-3*ux:.3f} "
            f"{sx(x)-8*ux-3*uy:.3f},{sy(y)-8*uy+3*ux:.3f}"
        )
        parts.append(
            f'<g data-raw-x="{raw_x!r}" data-raw-y="{raw_y!r}">'
            f"<title>{escape(label)}: {raw_x:.10g}, {raw_y:.10g}</title>"
            f'<line x1="{sx(0):.3f}" y1="{sy(0):.3f}" x2="{sx(x):.3f}" '
            f'y2="{sy(y):.3f}" stroke="#26775a"/>'
            f'<polygon points="{arrow}" fill="#26775a"/></g>'
        )
        if len(vectors) <= 12:
            parts.append(
                f'<text x="{sx(x):.3f}" y="{sy(y)-5:.3f}" font-size="10">'
                f"<title>{escape(label)}</title>{escape(short_label(label, 18))}</text>"
            )
    return "".join(parts) + "</svg>"


def report_grid(
    title: str,
    x_label: str,
    y_label: str,
    value_label: str,
    cells: Sequence[tuple[float, float, float, str]],
    *,
    value_range: tuple[float, float] | None = None,
    x_ticks: Sequence[tuple[float, str]] | None = None,
    y_ticks: Sequence[tuple[float, str]] | None = None,
    categorical: bool = False,
) -> str:
    """Render stored node coordinates; gaps are never filled with invented values."""
    if not cells:
        return ""
    for x, y, value, _ in cells:
        report_number(x)
        report_number(y)
        report_number(value)
    if len({(x, y) for x, y, _, _ in cells}) != len(cells):
        raise ValueError("analysis_report_payload_invalid")
    xs = sorted(
        {x for x, _, _, _ in cells}
        | ({value for value, _ in x_ticks} if categorical and x_ticks else set())
    )
    ys = sorted(
        {y for _, y, _, _ in cells}
        | ({value for value, _ in y_ticks} if categorical and y_ticks else set())
    )
    for value in [*xs, *ys]:
        report_number(value)

    def edges(values: list[float]) -> list[float]:
        if len(values) == 1:
            padding = max(abs(values[0]) * 0.06, 0.5)
            return [values[0] - padding, values[0] + padding]
        return [
            values[0] - (values[1] - values[0]) / 2 if categorical else values[0],
            *[a + (b - a) / 2 for a, b in zip(values, values[1:], strict=False)],
            values[-1] + (values[-1] - values[-2]) / 2 if categorical else values[-1],
        ]

    xe, ye = edges(xs), edges(ys)
    report_number(xe[-1] - xe[0])
    report_number(ye[-1] - ye[0])
    if xe[-1] <= xe[0] or ye[-1] <= ye[0]:
        raise ValueError("analysis_report_payload_invalid")
    low, high = value_range or (min(v for _, _, v, _ in cells), max(v for _, _, v, _ in cells))
    report_number(low)
    report_number(high)
    report_number(high - low)
    if high < low or any(value < low or value > high for _, _, value, _ in cells):
        raise ValueError("analysis_report_payload_invalid")

    def sx(value: float) -> float:
        return 85 + (value - xe[0]) / (xe[-1] - xe[0]) * 420

    def sy(value: float) -> float:
        return 320 - (value - ye[0]) / (ye[-1] - ye[0]) * 280

    def color(value: float) -> str:
        fraction = (value - low) / (high - low) if high != low else 0.5
        return f"rgb({round(230-195*fraction)},{round(240-150*fraction)},{round(248-85*fraction)})"

    parts = [
        f'<svg viewBox="0 0 680 425" role="img" aria-label="{escape(title, quote=True)}">',
        f"<title>{escape(title)}</title><desc>{escape(x_label)} / {escape(y_label)}; "
        f"{escape(value_label)}</desc>",
    ]
    for x, y, value, label in cells:
        ix, iy = xs.index(x), ys.index(y)
        parts.append(
            f'<rect x="{sx(xe[ix]):.3f}" y="{sy(ye[iy+1]):.3f}" '
            f'width="{sx(xe[ix+1])-sx(xe[ix]):.3f}" height="{sy(ye[iy])-sy(ye[iy+1]):.3f}" '
            f'fill="{color(value)}" data-x="{x!r}" data-y="{y!r}" data-value="{value!r}">'
            f"<title>{escape(label)}: {value:.10g}</title></rect>"
        )
    for axis, supplied, values in (("x", x_ticks, xs), ("y", y_ticks, ys)):
        ticks = (
            supplied
            if supplied is not None
            else [
                (
                    values[0] + (values[-1] - values[0]) * (i / 4),
                    f"{values[0] + (values[-1]-values[0])*(i/4):.4g}",
                )
                for i in range(5 if len(values) > 1 else 1)
            ]
        )
        for value, label in ticks:
            report_number(value)
            coordinates = (
                f'x="{sx(value):.3f}" y="342" text-anchor="middle"'
                if axis == "x"
                else f'x="78" y="{sy(value)+3:.3f}" text-anchor="end"'
            )
            parts.append(
                f'<text {coordinates} font-size="10"><title>{escape(label)}</title>'
                f"{escape(short_label(label, 18))}</text>"
            )
    parts += [
        f'<text x="295" y="375" text-anchor="middle" font-size="12">'
        f"<title>{escape(x_label)}</title>{escape(short_label(x_label, 48))}</text>",
        '<text transform="translate(15 180) rotate(-90)" text-anchor="middle" font-size="12">'
        f"<title>{escape(y_label)}</title>{escape(short_label(y_label, 35))}</text>",
        f'<text x="85" y="410" font-size="11"><title>{escape(value_label)}</title>'
        f"{escape(short_label(value_label, 78))}</text>",
    ]
    for index in range(10):
        value = low + (high - low) * (index / 9)
        parts.append(
            f'<rect x="535" y="{40+28*(9-index)}" width="16" height="28" fill="{color(value)}"/>'
        )
    for value, y in ((high, 45), (low, 320)) if high != low else ((low, 180),):
        parts.append(
            f'<text x="558" y="{y}" font-size="11" data-scale-value="{value!r}">{value:.5g}</text>'
        )
    return "".join(parts) + "</svg>"


def short_label(label: str, limit: int) -> str:
    return label if len(label) <= limit else label[: limit - 3] + "..."


def report_histogram(
    title: str,
    x_label: str,
    y_label: str,
    bins: Sequence[tuple[float, float, float]],
    *,
    reference_lines: Sequence[tuple[str, float, str]] = (),
) -> str:
    """No rebinning: the producer's boundaries and frequencies are the sole input."""
    if not bins:
        return ""
    values = [
        (report_number(lower), report_number(upper), report_number(count))
        for lower, upper, count in bins
    ]
    return report_plot(
        title,
        x_label,
        y_label,
        [],
        reference_lines=reference_lines,
        histogram_bins=[(lower, upper, count, y_label) for lower, upper, count in values],
    ) + report_table([f"{x_label} lower", f"{x_label} upper", y_label], values)


def report_horizontal_bars(
    title: str, x_label: str, y_label: str, values: Sequence[tuple[str, float]]
) -> str:
    if not values:
        return ""
    if not all(isfinite(value) for _, value in values):
        raise ValueError("analysis_report_payload_invalid")
    low, high = min(0, min(value for _, value in values)), max(0, max(value for _, value in values))
    padding = (high - low or 1) * 0.06
    low, high = low - padding, high + padding
    report_number(high - low)

    def x(value: float) -> float:
        return 190 + (value - low) / (high - low) * 400

    pages = []
    for offset in range(0, len(values), 12):
        page = values[offset : offset + 12]
        bottom = 40 + 24 * len(page)
        parts = [
            f'<svg viewBox="0 0 640 {bottom+60}" role="img" '
            f'aria-label="{escape(title, quote=True)}">',
            f"<title>{escape(title)}</title><desc>{escape(y_label)} / {escape(x_label)}</desc>",
            f'<text x="12" y="20">{escape(y_label)}</text>',
            f'<line x1="{x(0):.3f}" x2="{x(0):.3f}" y1="30" y2="{bottom}" stroke="#777"/>',
        ]
        for index, (label, value) in enumerate(page):
            y = 40 + index * 24
            parts += [
                f'<text x="175" y="{y+4}" text-anchor="end" font-size="11">'
                f"<title>{escape(label)}</title>{escape(short_label(label, 22))}</text>",
                f'<rect x="{min(x(0),x(value)):.3f}" y="{y-7}" '
                f'width="{abs(x(value)-x(0)):.3f}" height="14" fill="#225aa7" '
                f'data-value="{value!r}"><title>{escape(label)}: {value:.10g}</title></rect>',
            ]
        for index in range(5):
            value = low + (high - low) * (index / 4)
            parts.append(
                f'<text x="{x(value):.3f}" y="{bottom+15}" text-anchor="middle" '
                f'font-size="10">{value:.4g}</text>'
            )
        parts.append(
            f'<text x="390" y="{bottom+40}" text-anchor="middle" font-size="12">'
            f"{escape(x_label)}</text></svg>"
        )
        pages.append("".join(parts))
    return "".join(pages)
