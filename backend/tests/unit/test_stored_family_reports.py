"""Actual producer payloads, then rendering with calculation disabled."""

import copy
import hashlib
import json
from typing import Any
from xml.etree import ElementTree as ET

import pytest

from app.services.correlation_report import CORRELATION_REPORT_VARIANTS, correlation_report_body
from app.services.gaussian_process_report import gp_surface_sections
from app.services.normality_report import NORMALITY_REPORT_VARIANTS, normality_report_body
from app.services.principal_components_report import (
    PCA_REPORT_VARIANTS,
    principal_components_report_body,
)
from app.services.quality_report import QUALITY_REPORT_VARIANTS, quality_report_body
from app.services.report_contract import ReportBody, ReportDefinition, assess_report_body
from app.services.stored_report_primitives import report_grid, report_histogram, report_plot
from app.statistics.attribute_control_chart import (
    AttributeControlChartColumn,
    calculate_attribute_control_chart,
)
from app.statistics.capability import CapabilityColumn, calculate_normal_capability
from app.statistics.gage_rr import calculate_gage_rr_anova
from app.statistics.gage_rr_preflight import GageRrColumn
from app.statistics.gage_run_chart import GageRunChartColumn, calculate_gage_run_chart
from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    calculate_gaussian_process_regression,
)
from app.statistics.individuals_chart import IndividualsChartColumn, calculate_individuals_chart
from app.statistics.normality import NormalityColumn, calculate_normality
from app.statistics.pearson import PearsonCorrelationColumn, calculate_pearson_correlation
from app.statistics.principal_components import (
    PrincipalComponentsColumn,
    PrincipalComponentsOptions,
    calculate_principal_components,
)
from app.statistics.run_chart import RunChartColumn, calculate_run_chart
from app.statistics.subgroup_chart import SubgroupChartColumn, calculate_subgroup_chart
from app.statistics.xy_correlation import XyCorrelationColumn, calculate_xy_correlation


def column(
    cls: Any,
    index: int = 0,
    *,
    name: str = "Length <unsafe> & 한글",
    unit: str | None = "mm",
    role: str = "feature",
    data_type: str = "decimal",
) -> Any:
    return cls(
        column_id=f"c{index}",
        column_index=index,
        display_name=name,
        data_type=data_type,
        measurement_level="continuous" if data_type == "decimal" else "nominal",
        role=role,
        unit=unit,
    )


def tree(body: ReportBody) -> ET.Element:
    return ET.fromstring("<body>" + body.render() + "</body>")


def digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def section(body: ReportBody, section_id: str) -> Any:
    return next(item for item in body.sections if item.section_id == section_id)


def test_normality_preserves_qq_values_counts_ad_p_and_escaping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = calculate_normality(
        [[str(i)] for i in range(151)], [column(NormalityColumn)], qq_point_limit=120
    )
    before = digest(result)
    monkeypatch.setattr(
        "app.statistics.normality.calculate_normality",
        lambda *args, **kwargs: pytest.fail("report refit"),
    )
    for locale in ("en", "ko"):
        body = normality_report_body(result, locale)
        root = tree(body)
        circles = root.findall(".//circle")
        assert len(circles) == 120
        assert [float(point.attrib["data-y"]) for point in circles] == [
            point["sample"] for point in result["columns"][0]["qq_plot"]["points"]
        ]
        assert "120 / 151" in body.render()
        assert "Anderson-Darling p" in body.render()
        assert "Length &lt;unsafe&gt; &amp; 한글" in body.render()
        assert "<unsafe>" not in body.render()
        assert all(item.status == "rendered" for item in body.sections)
    assert digest(result) == before
    legacy = copy.deepcopy(result)
    del legacy["columns"][0]["qq_plot"]
    assert section(normality_report_body(legacy), "qq_plots").status == "missing"


@pytest.fixture
def pca_result() -> dict[str, Any]:
    rows = [[str(i), str(i * 2 + i % 3), str(i % 7)] for i in range(1, 151)]
    rows.insert(4, ["", "", ""])
    return calculate_principal_components(
        rows,
        [column(PrincipalComponentsColumn, i, name=f"Variable {i}") for i in range(3)],
        options=PrincipalComponentsOptions(
            component_selection="fixed", component_count=3, plot_point_limit=120
        ),
    )


def test_pca_stored_raw_loading_biplot_scale_and_source_rows(pca_result: dict[str, Any]) -> None:
    before = digest(pca_result)
    body = principal_components_report_body(pca_result)
    root = tree(body)
    assert all(item.status == "rendered" for item in body.sections)
    assert "Mahalanobis distance squared (D²)" in body.render()
    assert "Hotelling" not in body.render()
    score = ET.fromstring("<div>" + section(body, "score_plot").markup + "</div>")
    assert len(score.findall(".//circle")) + len(score.findall(".//rect")) == 120
    biplot = ET.fromstring("<div>" + section(body, "biplot").markup + "</div>")
    scale = float(biplot.find(".//span").attrib["data-loading-display-scale"])
    expected = (
        max(abs(value) for row in pca_result["plot"]["points"] for value in row["scores"][:2])
        * 1.08
    )
    assert scale == pytest.approx(expected, abs=1e-12)
    vectors = [item for item in biplot.findall(".//g") if "data-raw-x" in item.attrib]
    assert [float(item.attrib["data-raw-x"]) for item in vectors] == [
        row["values"][0] for row in pca_result["loadings"]
    ]
    assert len(biplot.findall(".//text")) < 40
    outlier = ET.fromstring("<div>" + section(body, "outlier_plot").markup + "</div>")
    source_rows = [
        float(item.attrib["data-x"]) for item in outlier.iter() if "data-x" in item.attrib
    ]
    assert source_rows == [row["source_row_number"] for row in pca_result["plot"]["points"]]
    assert 5 not in source_rows
    assert root.findall(".//svg")
    assert digest(pca_result) == before


def test_pca_one_component_never_invents_pc2() -> None:
    result = calculate_principal_components(
        [[str(i), str(i * 2 + i % 3)] for i in range(1, 16)],
        [column(PrincipalComponentsColumn, i) for i in range(2)],
        options=PrincipalComponentsOptions(component_selection="fixed", component_count=1),
    )
    # The current producer stores all dimensions, even when one is selected.
    # Exercise an archived payload that actually retained just one dimension.
    for row in result["plot"]["points"]:
        row["scores"] = row["scores"][:1]
    for row in result["loadings"]:
        row["values"] = row["values"][:1]
    body = principal_components_report_body(result)
    assert section(body, "biplot").status == "not_applicable"
    assert "Source row number" in section(body, "score_plot").markup
    assert "PC2" not in section(body, "score_plot").markup
    assert "PC1 loading" in section(body, "loading_plot").markup


def test_pearson_and_xy_actual_payloads_preserve_axes_and_failed_pairs() -> None:
    rows = [[str(i), str(i * 2 + i % 3), "7"] for i in range(1, 31)]
    pearson = calculate_pearson_correlation(
        rows,
        column(PearsonCorrelationColumn),
        column(PearsonCorrelationColumn, 1, name="Response", unit="mg"),
    )
    body = correlation_report_body(pearson)
    assert "Response (mg)" in body.render()
    assert len(tree(body).findall(".//circle")) == 30
    xy = calculate_xy_correlation(
        rows,
        [column(XyCorrelationColumn)],
        [column(XyCorrelationColumn, 1), column(XyCorrelationColumn, 2)],
    )
    body = correlation_report_body(xy)
    assert "failed" in body.render()
    assert len([cell for cell in tree(body).findall(".//rect") if "data-value" in cell.attrib]) == 1
    assert 'data-scale-value="-1.0"' in body.render()
    assert 'data-scale-value="1.0"' in body.render()


def test_quality_i_mr_shapes_zero_limit_and_no_refit() -> None:
    result = calculate_individuals_chart(
        [[str(value)] for value in [10, 10.1, 10.2, 10.1, 10, 14]], column(IndividualsChartColumn)
    )
    before = digest(result)
    body = quality_report_body(result)
    root = tree(body)
    assert len(root.findall(".//svg")) == 2
    assert len(root.findall('.//rect[@data-marker="square"]')) == 2
    assert any(item.attrib.get("data-value") == "0.0" for item in root.findall(".//line"))
    assert "mm" in body.render()
    assert digest(result) == before


@pytest.mark.parametrize("chart_type", ["p", "u"])
def test_attribute_variable_limits_and_run_median_only(chart_type: str) -> None:
    result = calculate_attribute_control_chart(
        [["1", "20"], ["2", "50"], ["3", "100"], ["0", "40"]],
        column(AttributeControlChartColumn),
        column(AttributeControlChartColumn, 1),
        chart_type=chart_type,
        count_definition="defectives" if chart_type == "p" else "defects",
    )
    root = tree(quality_report_body(result))
    assert len(root.findall(".//polyline")) == 3
    values = [float(item.attrib["data-y"]) for item in root.findall(".//circle")]
    assert values[-4:] == [point["ucl"] for point in result["chart"]["points"]]
    run = calculate_run_chart(
        [[str(value)] for value in [1, 4, 2, 5, 3, 6]], column(RunChartColumn)
    )
    body = quality_report_body(run)
    assert "Median" in body.render()
    assert "UCL" not in body.render() and "LCL" not in body.render()
    assert section(body, "randomness_tests").status == "rendered"


@pytest.mark.parametrize("chart_type", ["xbar_r", "xbar_s"])
def test_subgroup_chart_preserves_stored_statistics_and_sizes(chart_type: str) -> None:
    result = calculate_subgroup_chart(
        [["10", "A"], ["12", "A"], ["11", "B"], ["13", "B"], ["9", "C"], ["11", "C"]],
        column(SubgroupChartColumn),
        column(SubgroupChartColumn, 1, data_type="text"),
        chart_type=chart_type,
    )
    body = quality_report_body(result)
    assert len(tree(body).findall(".//svg")) == 2
    assert "subgroup_label=A; n=2" in body.render()
    assert "Subgroup mean (mm)" in body.render()
    assert section(body, "subgroup_charts").status == "rendered"


def test_capability_saved_bins_and_zero_specification() -> None:
    result = calculate_normal_capability(
        [[str(i)] for i in range(1, 31)], column(CapabilityColumn), lsl=0, usl=35
    )
    body = quality_report_body(result)
    root = tree(body)
    bars = [item for item in root.findall(".//rect") if "data-lower" in item.attrib]
    assert [float(item.attrib["data-value"]) for item in bars] == [
        row["count"] for row in result["histogram"]["bins"]
    ]
    assert any(item.attrib.get("data-value") == "0.0" for item in root.findall(".//line"))
    assert "Frequency" in body.render()


def gage_result(cls: Any, calculator: Any) -> dict[str, Any]:
    rows = [
        [
            str(part * 10 + operator * 2 + replicate + (part + operator) * replicate / 5),
            str(part),
            str(operator),
            str(replicate),
        ]
        for part in range(1, 4)
        for operator in range(1, 3)
        for replicate in range(1, 3)
    ]
    return calculator(
        rows,
        measurement_column=column(cls),
        part_column=column(cls, 1, role="part_id", data_type="text"),
        operator_column=column(cls, 2, role="operator_id", data_type="text"),
        replicate_column=column(cls, 3, role="replicate_id", data_type="text"),
    )


def test_gage_preserves_separate_series_and_does_not_invent_interaction() -> None:
    run = gage_result(GageRunChartColumn, calculate_gage_run_chart)
    body = quality_report_body(run)
    assert len(tree(body).findall(".//polyline")) == 6
    assert "replicate_index=" in body.render()
    rr = gage_result(GageRrColumn, calculate_gage_rr_anova)
    body = quality_report_body(rr)
    assert section(body, "gage_interaction").status == "missing"
    assert section(body, "gage_anova").status == "rendered"
    assert section(body, "gage_variance_components").status == "rendered"


def test_gp_surface_both_modes_units_constant_scale_and_no_predictions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = calculate_gaussian_process_regression(
        [[str(i), str(i % 4), str(i / 3 + (i % 4) ** 2)] for i in range(24)],
        column(GaussianProcessColumn, 2, name="Response", unit="mg"),
        [
            column(GaussianProcessColumn),
            column(GaussianProcessColumn, 1, name="Temperature", unit="C"),
        ],
        options=GaussianProcessOptions(
            validation_method="none", optimizer_restarts=0, profile_points=10, surface_grid_size=10
        ),
    )
    result.pop("prediction_basis")  # The runner persists numeric model state separately.
    before = digest(result)
    monkeypatch.setattr(
        "app.statistics.gaussian_process_regression.calculate_gaussian_process_regression",
        lambda *args, **kwargs: pytest.fail("report fit"),
    )
    sections = gp_surface_sections(result)
    assert [item.section_id for item in sections] == ["gp_surface_mean", "gp_surface_sd"]
    root = tree(ReportBody("single", sections))
    assert len(root.findall(".//svg")) == 2
    assert len([item for item in root.findall(".//rect") if "data-value" in item.attrib]) == 200
    assert "Temperature (C)" in sections[0].markup
    assert "New Observation Predictive SD (mg)" in sections[1].markup
    assert digest(result) == before
    assert all(
        item.status == "not_applicable"
        for item in gp_surface_sections({"two_predictor_surface": None})
    )
    constant = report_grid("Constant", "X", "Y", "Value (mg)", [(0.0, 0.0, 3.0, "cell")])
    assert constant.count("data-scale-value") == 1
    assert "nan" not in constant.lower()


def test_plot_rejects_nonfinite_and_keeps_square_unit_length() -> None:
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        report_plot("Bad", "X", "Y", [("S", [(float("nan"), 1.0, "bad")])])
    root = ET.fromstring(
        report_plot(
            "Square", "X", "Y", [("S", [(0.0, 0.0, "zero"), (1.0, 1.0, "one")])], square=True
        )
    )
    first, second = root.findall(".//circle")
    assert float(second.attrib["cx"]) - float(first.attrib["cx"]) == pytest.approx(
        float(first.attrib["cy"]) - float(second.attrib["cy"]), abs=0.001
    )


@pytest.mark.parametrize(
    "renderer",
    [
        normality_report_body,
        principal_components_report_body,
        correlation_report_body,
        quality_report_body,
    ],
)
def test_unknown_payload_never_claims_complete_report(renderer: Any) -> None:
    body = renderer({"summary_type": "unknown", "schema_version": 999})
    assert body.unsupported_reason is not None
    assert body.sections == ()
    assert body.render() == ""


def definition(summary: str, variants: Any) -> ReportDefinition:
    return ReportDefinition("test.method", summary, (1, 2, 3), "test.renderer", "1", variants)


def test_pca_legacy_missing_scores_is_summary_but_keeps_loadings(
    pca_result: dict[str, Any],
) -> None:
    expected = definition("principal_components_analysis", PCA_REPORT_VARIANTS)
    assert assess_report_body(expected, principal_components_report_body(pca_result)) == "full"
    legacy = copy.deepcopy(pca_result)
    del legacy["plot"]
    body = principal_components_report_body(legacy)
    assert assess_report_body(expected, body) == "summary"
    assert section(body, "loading_plot").status == "rendered"
    assert section(body, "score_plot").reason == "pca_points_not_stored"


def test_contract_sections_match_actual_normality_correlation_and_quality() -> None:
    normality = calculate_normality([[str(i)] for i in range(10)], [column(NormalityColumn)])
    assert (
        assess_report_body(
            definition("normality_test", NORMALITY_REPORT_VARIANTS),
            normality_report_body(normality),
        )
        == "full"
    )
    del normality["columns"][0]["qq_plot"]
    assert (
        assess_report_body(
            definition("normality_test", NORMALITY_REPORT_VARIANTS),
            normality_report_body(normality),
        )
        == "summary"
    )
    pearson = calculate_pearson_correlation(
        [[str(i), str(i * 2 + i % 3)] for i in range(10)],
        column(PearsonCorrelationColumn),
        column(PearsonCorrelationColumn, 1),
    )
    assert (
        assess_report_body(
            definition("pearson_correlation", CORRELATION_REPORT_VARIANTS["pearson_correlation"]),
            correlation_report_body(pearson),
        )
        == "full"
    )
    rr = gage_result(GageRrColumn, calculate_gage_rr_anova)
    expected = definition("gage_rr", QUALITY_REPORT_VARIANTS["gage_rr"])
    assert assess_report_body(expected, quality_report_body(rr)) == "summary"
    del rr["anova_table"]
    assert assess_report_body(expected, quality_report_body(rr)) == "unsupported"


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf")])
def test_all_plot_coordinate_boundaries_reject_nonfinite(invalid: float) -> None:
    series = [("S", [(1.0, 2.0, "stored")])]
    calls = [
        lambda: report_plot("P", "X", "Y", series, selected_x=invalid),
        lambda: report_plot("P", "X", "Y", series, x_ticks=[(invalid, "bad")]),
        lambda: report_plot("P", "X", "Y", series, reference_lines=[("y", invalid, "bad")]),
        *[
            lambda index=index: report_plot(
                "P",
                "X",
                "Y",
                series,
                reference_segments=[("saved", *[invalid if i == index else 0.0 for i in range(4)])],
            )
            for index in range(4)
        ],
        lambda: report_grid("P", "X", "Y", "V", [(0.0, 0.0, invalid, "bad")]),
        lambda: report_grid("P", "X", "Y", "V", [(0.0, 0.0, 1.0, "ok")], value_range=(0, invalid)),
        lambda: report_histogram("P", "X", "Count", [(0.0, 1.0, invalid)]),
    ]
    for call in calls:
        with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
            call()


def test_grid_midpoint_geometry_axis_labels_and_reserved_missing_categories() -> None:
    svg = ET.fromstring(
        report_grid(
            "Grid",
            "Distance (m)",
            "Temperature (C)",
            "Mean (mg)",
            [(0.0, 1.0, 2.0, "a"), (2.0, 1.0, 3.0, "b"), (10.0, 1.0, 4.0, "c")],
        )
    )
    cells = [item for item in svg.findall("rect") if "data-value" in item.attrib]
    assert [float(item.attrib["width"]) for item in cells] == pytest.approx(
        [42, 210, 168], abs=0.001
    )
    assert "Distance (m)" in "".join(svg.itertext())
    assert "Temperature (C)" in "".join(svg.itertext())
    assert "Mean (mg)" in "".join(svg.itertext())
    categorical = ET.fromstring(
        report_grid(
            "Matrix",
            "X",
            "Y",
            "r",
            [(0.0, 0.0, 0.5, "ok")],
            categorical=True,
            x_ticks=[(0.0, "X")],
            y_ticks=[(0.0, "valid"), (1.0, "failed")],
            value_range=(-1, 1),
        )
    )
    cell = next(item for item in categorical.findall("rect") if "data-value" in item.attrib)
    assert float(cell.attrib["height"]) == pytest.approx(140, abs=0.001)
    assert "failed" in "".join(categorical.itertext())


def test_stored_reference_segment_domain_geometry_legend_and_no_extra_markers() -> None:
    series = [("Observed", [(0.0, 0.0, "one"), (1.0, 1.0, "two")])]
    original = report_plot("Q-Q", "Quantile", "Residual", series)
    assert report_plot("Q-Q", "Quantile", "Residual", series, reference_segments=()) == original
    label = 'Saved <reference> "line"'
    rendered = report_plot(
        "Q-Q",
        "Quantile",
        "Residual",
        series,
        reference_segments=[(label, -2.0, -3.0, 4.0, 5.0)],
    )
    svg = ET.fromstring(rendered)
    segment = next(item for item in svg.findall("line") if "data-reference-segment" in item.attrib)
    assert segment.attrib["data-reference-segment"] == label
    assert [float(segment.attrib[f"data-{axis}"]) for axis in ("x1", "y1", "x2", "y2")] == [
        -2,
        -3,
        4,
        5,
    ]
    assert [float(segment.attrib[axis]) for axis in ("x1", "y1", "x2", "y2")] == pytest.approx(
        [
            75 + 500 * 0.06 / 1.12,
            230 - 195 * 0.06 / 1.12,
            75 + 500 * 1.06 / 1.12,
            230 - 195 * 1.06 / 1.12,
        ],
        abs=0.001,
    )
    assert len(svg.findall("circle")) == 2
    assert any(label in "".join(item.itertext()) for item in svg.findall("text"))
    assert "<reference>" not in rendered


def test_histogram_boundaries_and_exact_counts_not_rebinned() -> None:
    svg = report_histogram(
        "Saved bins",
        "Length (mm)",
        "Count",
        [(0, 0.25, 1), (0.25, 2, 101)],
        reference_lines=[("x", 0.0, "LSL")],
    )
    root = ET.fromstring("<body>" + svg + "</body>")
    assert [float(item.attrib["data-value"]) for item in root.findall(".//rect")] == [1.0, 101.0]
    assert [float(item.attrib["data-upper"]) for item in root.findall(".//rect")] == [0.25, 2.0]
    assert "101" in "".join(root.find(".//tbody").itertext())
    assert any(item.attrib.get("data-value") == "0.0" for item in root.findall(".//line"))


def test_surface_long_korean_names_xss_and_legacy_missing() -> None:
    name = "긴 변수 이름 " * 15 + '<script>alert("x")</script>'
    payload = {
        "response": {"unit": "mg"},
        "predictors": [{"column_id": "x", "unit": "mm"}],
        "two_predictor_surface": {
            "x_column_id": "x",
            "x_display_name": name,
            "y_column_id": "y",
            "y_display_name": "한글 반응",
            "fixed_values": [1.0],
            "points": [
                {"x": 1.0, "y": 2.0, "predicted_mean": 3.0, "predictive_standard_deviation": 0.5}
            ],
        },
    }
    sections = gp_surface_sections(payload, "ko")
    body = ReportBody("single", sections)
    assert name in "".join(tree(body).itertext())
    assert "<script>" not in body.render()
    assert "새 관측값 예측 표준편차 (mg)" in body.render()
    assert all(item.status == "missing" for item in gp_surface_sections({}))
    payload["two_predictor_surface"]["points"][0]["predictive_standard_deviation"] = -1
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        gp_surface_sections(payload)


def test_large_constant_coordinates_have_finite_padding() -> None:
    plot = report_plot("Constant", "X", "Y", [("S", [(1e308, 1e308, "large")])])
    point = ET.fromstring(plot).find("circle")
    assert float(point.attrib["cx"]) == pytest.approx(325, abs=0.001)
    assert float(point.attrib["cy"]) == pytest.approx(132.5, abs=0.001)
    grid = report_grid("Constant", "X", "Y", "Value", [(1e308, 1e308, 3.0, "large")])
    cell = next(item for item in ET.fromstring(grid).findall("rect") if "data-value" in item.attrib)
    assert float(cell.attrib["width"]) == pytest.approx(420, abs=0.001)
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        report_plot("Overflow", "X", "Y", [("S", [(-1e308, 0.0, "low"), (1e308, 0.0, "high")])])
