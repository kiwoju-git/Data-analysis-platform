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
    xpad, ypad = (xmax - xmin or 1) * 0.06, (ymax - ymin or 1) * 0.06
    xmin, xmax, ymin, ymax = xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad

    def sx(x: float) -> float:
        return 75 + (x - xmin) / (xmax - xmin) * 500

    def sy(y: float) -> float:
        return 230 - (y - ymin) / (ymax - ymin) * 195

    parts = [
        f'<svg role="img" aria-label="{escape(title, quote=True)}" '
        f'viewBox="0 0 640 {290 + len(series)*17}"><title>{escape(title)}</title>',
        f"<desc>{escape(x_label)} / {escape(y_label)}; {len(values)} points</desc>",
        '<g fill="none" stroke="#637083"><path d="M75 35V230H575"/></g>',
    ]
    for index in range(5):
        x, y = xmin + (xmax - xmin) * index / 4, ymin + (ymax - ymin) * index / 4
        parts.append(
            f'<text x="{sx(x):.3f}" y="249" text-anchor="middle" '
            f'font-size="10">{x:.4g}</text><text x="68" y="{sy(y)+3:.3f}" '
            f'text-anchor="end" font-size="10">{y:.4g}</text>'
        )
    parts += [
        '<text x="325" y="269" text-anchor="middle" font-size="12">'
        f"<title>{escape(x_label)}</title>{escape(short_label(x_label, 44))}</text>",
        '<text transform="translate(14 133) rotate(-90)" text-anchor="middle" '
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
            '<line x1="75" x2="575" y1="230" y2="35" stroke="#777" stroke-dasharray="4 3"/>'
        )
    if selected_x is not None:
        parts.append(
            f'<line x1="{sx(selected_x):.3f}" x2="{sx(selected_x):.3f}" y1="35" '
            'y2="230" stroke="#9e3e25" stroke-dasharray="3 3"/>'
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
            f'<text x="75" y="{292+index*17}" fill="{color}" font-size="11">'
            f"<title>{escape(label)}</title>{escape(short_label(label, 64))}</text>"
        )
    return "".join(parts) + "</svg>"


def short_label(label: str, limit: int) -> str:
    return label if len(label) <= limit else label[: limit - 3] + "..."
