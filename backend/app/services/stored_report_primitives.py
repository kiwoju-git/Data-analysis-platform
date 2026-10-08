"""Escaped tables and static SVG projections of already stored result values."""

from collections.abc import Sequence
from html import escape
from math import isfinite


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
) -> str:
    values = [(x, y) for _, points in series for x, y, _ in points]
    if not values:
        return ""
    if not all(isfinite(x) and isfinite(y) for x, y in values):
        raise ValueError("analysis_report_payload_invalid")
    xmin, xmax = min(x for x, _ in values), max(x for x, _ in values)
    ymin, ymax = min(y for _, y in values), max(y for _, y in values)
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
    xpad, ypad = (xmax - xmin or 1) * 0.06, (ymax - ymin or 1) * 0.06
    xmin, xmax, ymin, ymax = xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad

    def sx(x: float) -> float:
        return 75 + (x - xmin) / (xmax - xmin) * 500

    def sy(y: float) -> float:
        return bottom - (y - ymin) / (ymax - ymin) * height

    parts = [
        f'<svg role="img" aria-label="{escape(title, quote=True)}" '
        f'viewBox="0 0 640 {bottom + 60 + len(series)*17}"><title>{escape(title)}</title>',
        f"<desc>{escape(x_label)} / {escape(y_label)}; {len(values)} points</desc>",
        f'<g fill="none" stroke="#637083"><path d="M75 35V{bottom}H575"/></g>',
    ]
    for axis, specified, low, high in (("x", x_ticks, xmin, xmax), ("y", y_ticks, ymin, ymax)):
        ticks = (
            specified
            if specified is not None
            else [
                (low + (high - low) * index / 4, f"{low + (high - low) * index / 4:.4g}")
                for index in range(5)
            ]
        )
        for value, label in ticks:
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
    for index, (label, points) in enumerate(series):
        color = ("#225aa7", "#26775a", "#a9442f", "#6d507e")[index % 4]
        if lines:
            coordinates = " ".join(f"{sx(x):.3f},{sy(y):.3f}" for x, y, _ in points)
            parts.append(f'<polyline points="{coordinates}" fill="none" stroke="{color}"/>')
        for x, y, point_label in points:
            parts.append(
                f'<circle cx="{sx(x):.3f}" cy="{sy(y):.3f}" r="2.5" fill="{color}" '
                f'data-x="{x!r}" data-y="{y!r}"><title>{escape(point_label)}: '
                f"{x:.10g}, {y:.10g}</title></circle>"
            )
        parts.append(
            f'<text x="75" y="{bottom+62+index*17}" fill="{color}" font-size="11">'
            f"<title>{escape(label)}</title>{escape(short_label(label, 64))}</text>"
        )
    return "".join(parts) + "</svg>"


def short_label(label: str, limit: int) -> str:
    return label if len(label) <= limit else label[: limit - 3] + "..."


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
            value = low + (high - low) * index / 4
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
