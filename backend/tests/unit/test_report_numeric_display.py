import json
import math
import re
from pathlib import Path
from sys import float_info
from xml.etree import ElementTree

import pytest

from app.services.report_numeric_axis import numeric_axis_plan, numeric_axis_ticks
from app.services.stored_report_primitives import report_grid, report_plot, report_table
from app.services.two_variances_report import ratio_interval_svg

CASES = json.loads(
    (Path(__file__).resolve().parents[3] / "tests/fixtures/numeric_display_cases.json").read_text(
        encoding="utf-8"
    )
)


def test_report_numeric_table_preserves_distinct_large_values() -> None:
    html = report_table(["Stored value"], [[1e12 + index] for index in range(6)])
    cells = re.findall(r"<td[^>]*>(.*?)</td>", html)
    assert len(set(cells)) == 6


def test_report_numeric_axis_labels_preserve_narrow_range() -> None:
    html = report_plot("Stored", "X", "Y", [("Series", [(1000.0, 0.0, "a"), (1000.01, 1.0, "b")])])
    labels = re.findall(r'<text x="[^"]+" y="249"[^>]*>([^<]*)</text>', html)
    assert len(labels) > 1
    assert len(set(labels)) == len(labels)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_shared_numeric_axis_cases(case: dict[str, object]) -> None:
    low, high = float(case["min"]), float(case["max"])
    plan = numeric_axis_plan(low, high)
    assert 2 <= len(plan.values) <= 32
    assert all(math.isfinite(value) and low <= value <= high for value in plan.values)
    assert all(second > first for first, second in zip(plan.values, plan.values[1:], strict=False))
    assert bool(plan.offset) == case["offset"]
    if "expected_values" in case:
        assert list(plan.values) == case["expected_values"]
    ticks = numeric_axis_ticks(plan)
    assert len({label for _, label in ticks}) == len(ticks)


@pytest.mark.parametrize("low,high", [(math.nan, 1), (0, math.inf), (2, 1), (1, 1)])
def test_invalid_numeric_axis_has_no_ticks(low: float, high: float) -> None:
    assert numeric_axis_plan(low, high).values == ()


@pytest.mark.parametrize(
    "low,high",
    [
        (-1.7e308, 1.7e308),
        (1.7976931348623157e308, 1.7976931348623157e308),
        (1.0, math.nextafter(1.0, 2.0)),
        (5e-324, 2e-323),
    ],
)
def test_report_projection_remains_finite(low: float, high: float) -> None:
    points = [(low, low, "first"), (high, high, "last")]
    html = report_plot("Stored", "X", "Y", [("Stored", points)])
    root = ElementTree.fromstring(html)
    for node in root.iter():
        for key in ("cx", "cy", "x", "y", "x1", "y1", "x2", "y2"):
            if key in node.attrib:
                assert math.isfinite(float(node.attrib[key]))
    assert f'data-x="{low!r}"' in html
    assert f'data-x="{high!r}"' in html


def test_report_offset_and_explicit_categories() -> None:
    series = [("Stored", [(1e12, 0.0, "a"), (1e12 + 5, 1.0, "b")])]
    html = report_plot("Stored", "X (mg/L)", "Y", series)
    assert 'data-axis-offset="' in html
    assert "X (mg/L):" in html
    assert 'data-x="1000000000005.0"' in html
    html = report_plot(
        "Stored", "X", "Y", series, x_ticks=[(1e12, "PC1"), (1e12 + 5, "PC2 <user>")]
    )
    assert "data-axis-offset=" not in html
    assert "PC2 &lt;user&gt;" in html


def test_numeric_columns_preserve_strings_integers_and_custom_formatter() -> None:
    html = report_table(
        ["id", "value", "name"],
        [
            [9007199254740993, 1e12 + 1, "1000000000001 <user>"],
            [9007199254740995, 1e12 + 2, "1000000000002"],
        ],
    )
    assert "<td>9007199254740993</td>" in html
    assert "<td>1000000000001 &lt;user&gt;</td>" in html
    assert 'title="1000000000001.0"' in html
    assert ">1000000000001</td>" in html
    calls = []

    def formatter(value, context):
        calls.append((value, context))
        return f"custom<{value!r}>"

    custom = report_table(["value"], [[1e12 + 1], [1e12 + 2]], numeric_columns={0: formatter})
    assert "custom&lt;1000000000001.0&gt;" in custom
    assert calls[0][1].significant_digits >= 13
    assert calls[0][1].values == (1e12 + 1, 1e12 + 2)


def test_interval_precision_context_includes_exact_integers_without_coercion() -> None:
    huge = 10**400
    upper = math.nextafter(1.0, 2.0)
    html = report_table(
        ["lower", "upper", "identifier", "user text"],
        [[1, upper, huge, "1.0000000000000002"]],
        numeric_column_groups=((0, 1),),
    )
    cells = [node.text for node in ElementTree.fromstring(html).findall(".//tbody/tr/td")]
    assert cells == ["1", repr(upper), str(huge), "1.0000000000000002"]
    mixed = report_table(["value"], [[huge], [1], [upper], [True], ["1.0000000000000002"]])
    cells = [node.text for node in ElementTree.fromstring(mixed).findall(".//tbody/tr/td")]
    assert cells == [str(huge), "1", repr(upper), "True", "1.0000000000000002"]


def test_report_grid_uses_distinct_numeric_labels_and_preserves_categories() -> None:
    cells = [(1000.0, 0.0, 1.0, "a"), (1000.01, 0.0, 2.0, "b")]
    html = report_grid("Stored", "X", "Y", "Value", cells)
    root = ElementTree.fromstring(html)
    labels = [
        "".join(node.itertext()) for node in root.findall("text") if node.attrib.get("y") == "342"
    ]
    assert len(labels) > 1 and len(labels) == len(set(labels))
    categorical = report_grid(
        "Stored",
        "X",
        "Y",
        "Value",
        cells,
        x_ticks=[(1000.0, "One"), (1000.01, "Two")],
        categorical=True,
    )
    assert "One" in categorical and "Two" in categorical


@pytest.mark.parametrize(
    "x,y",
    [(float_info.max, 0.0), (-float_info.max, 0.0), (0.0, float_info.max), (0.0, -float_info.max)],
)
def test_report_grid_rejects_nonfinite_expanded_edges(x: float, y: float) -> None:
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        report_grid("Stored", "X", "Y", "Value", [(x, y, 1.0, "row")])


@pytest.mark.parametrize("base,step", [(1000.0, 0.002), (1e12, 1.0)])
@pytest.mark.parametrize("locale", ["ko", "en"])
def test_two_variances_ratio_axis_keeps_stored_spacing(base, step, locale) -> None:
    payload = {
        "ratio_interval": {
            "lower": {"value": base},
            "upper": {"value": base + 5 * step},
            "confidence_level": 0.95,
        },
        "ratio_estimate": {"value": base + 2 * step},
        "hypothesis": {"ratio": base + step},
    }
    html = ratio_interval_svg(payload, locale, "Variance ratio")
    root = ElementTree.fromstring(html)
    labels = [
        "".join(node.itertext()) for node in root.findall("text") if node.attrib.get("y") == "170"
    ]
    assert 2 <= len(labels) <= 32
    assert len(labels) == len(set(labels))
    for node in root.iter():
        for key in ("cx", "cy", "x", "y", "x1", "x2"):
            if key in node.attrib:
                assert math.isfinite(float(node.attrib[key]))
    assert f'data-value="{base + 2 * step!r}"' in html
    assert root.find("circle/title").text == repr(base + 2 * step)
    if base == 1e12:
        assert 'data-axis-offset="' in html
        assert "Variance ratio:" in html


def test_report_point_and_reference_details_keep_exact_saved_values() -> None:
    stored = 1e12 + 1
    html = report_plot(
        "Stored",
        "X",
        "Y",
        [("Stored", [(stored, stored, "row")])],
        reference_lines=[("x", stored, "Reference")],
    )
    root = ElementTree.fromstring(html)
    point = root.find(".//circle/title")
    assert point is not None and repr(stored) in point.text
    assert f"Reference: {stored!r}" in html
