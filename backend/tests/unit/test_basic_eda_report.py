"""Section coverage from actual EDA producer payloads, without refitting at export."""

import copy
import json
import sys
from html import escape
from typing import Any

import pytest

from app.services.analysis_run_exports import (
    _report_boxplot_svg,
    _report_confidence_interval_svg,
    _report_histogram_svg,
    _variance_comparison_report_svg,
)
from app.services.basic_eda_report import (
    BASIC_EDA_REPORT_VARIANTS_BY_METHOD,
    BasicEdaPlotRenderers,
    render_basic_eda_report,
)
from app.services.report_contract import ReportDefinition, assess_report_body
from app.services.stored_report_primitives import report_value
from app.statistics.descriptive import DescriptiveColumn, describe_numeric_columns
from app.statistics.equal_variances import (
    EqualVarianceGroupColumn,
    EqualVarianceResponseColumn,
    calculate_equal_variances,
)
from app.statistics.graphical_summary import GraphicalSummaryColumn, summarize_numeric_graphics

NAME = '<script>not executable</script> 측정 "\\\ue000fixture.key\ue001'
COLUMN_ARGS = ("response-id", 0, NAME, "number", "continuous", "response", "mg/L")
GROUP = EqualVarianceGroupColumn("group-id", 1, "그룹<&>", "string", "nominal", "group", None)
PLOTS = BasicEdaPlotRenderers(
    histogram=_report_histogram_svg,
    boxplot=_report_boxplot_svg,
    confidence_intervals=_report_confidence_interval_svg,
    variance_intervals=_variance_comparison_report_svg,
)
METHODS = tuple(BASIC_EDA_REPORT_VARIANTS_BY_METHOD)


def payload(method: str) -> dict[str, Any]:
    rows = [[str(value)] for value in (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 35)]
    rows += [[None], ["not numeric"]]
    if method == "eda.descriptive":
        return describe_numeric_columns(rows, [DescriptiveColumn(*COLUMN_ARGS)])
    if method == "eda.graphical_summary":
        return summarize_numeric_graphics(rows, [GraphicalSummaryColumn(*COLUMN_ARGS)])
    return calculate_equal_variances(
        [
            [str((index + 1) * value), group]
            for index, group in enumerate(("A<&>", "B", "C"))
            for value in (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 35)
        ]
        + [[None, "A<&>"], ["bad", "B"], ["10", None]],
        EqualVarianceResponseColumn(*COLUMN_ARGS),
        GROUP,
    )


def definition(method: str, result: dict[str, Any]) -> ReportDefinition:
    return ReportDefinition(
        method,
        result["summary_type"],
        (1, 2),
        "basic_eda",
        "1",
        BASIC_EDA_REPORT_VARIANTS_BY_METHOD[method],
    )


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("locale", ["ko", "en"])
def test_current_producer_payload_has_visible_sections_and_unchanged_source(
    method: str, locale: str
) -> None:
    result = payload(method)
    before = json.dumps(result, sort_keys=True, ensure_ascii=False)
    body = render_basic_eda_report(result, locale, plots=PLOTS)
    markup = body.render()
    assert assess_report_body(definition(method, result), body) == "full"
    assert '<div data-report-section="settings"' in markup
    assert "<table>" in markup
    assert escape(NAME) in markup and "<script>" not in markup
    assert "mg/L" in markup and "\ue000fixture.key\ue001" in markup
    assert (
        "입력 및 계산 정의" if locale == "ko" else "Inputs and calculation definitions"
    ) in markup
    assert json.dumps(result, sort_keys=True, ensure_ascii=False) == before
    assert "<svg" in markup if method != "eda.descriptive" else "<svg" not in markup
    assert "<script" not in markup and "<iframe" not in markup


@pytest.mark.parametrize("locale", ["ko", "en"])
def test_equal_variances_preserves_every_group_pair_and_additional_test(locale: str) -> None:
    result = payload("eda.equal_variances")
    body = render_basic_eda_report(result, locale, plots=PLOTS)
    sections = {section.section_id: section.markup or "" for section in body.sections}
    for group in result["groups"]:
        for field in ("group_label", "n", "mean", "median", "variance", "std", "min", "max"):
            assert f"<td>{escape(report_value(group[field]))}</td>" in sections["groups"]
    multiple = result["multiple_comparisons"]
    assert len(multiple["pairwise_p_values"]) == 3
    for pair in multiple["pairwise_p_values"]:
        for field in ("left_group", "right_group", "p_value"):
            assert f"<td>{escape(report_value(pair[field]))}</td>" in sections["pairwise"]
    for group in multiple["groups"]:
        assert f"<td>{report_value(group['allocation'])}</td>" in sections["comparison_intervals"]
        for bound in ("lower", "upper"):
            assert (
                f"<td>{report_value(group['comparison_interval'][bound])}</td>"
                in sections["comparison_intervals"]
            )
    assert "classical_levene_mean_centered" in sections["additional_tests"]
    assert "levene_brown_forsythe" in sections["tests"]
    assert (
        "not ordinary confidence intervals" in sections["interpretation"]
        if locale == "en"
        else "일반 신뢰구간이 아닙니다" in sections["interpretation"]
    )


@pytest.mark.parametrize("method", METHODS)
def test_missing_core_is_not_successful_full_report(method: str) -> None:
    result = payload(method)
    result.pop("groups" if method == "eda.equal_variances" else "columns")
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition(method, result), body) == "unsupported"


@pytest.mark.parametrize("method", METHODS)
def test_legacy_payload_missing_supported_sections_is_honest_summary(method: str) -> None:
    result = payload(method)
    result["schema_version"] = 1
    if method == "eda.equal_variances":
        result.pop("multiple_comparisons")
        result.pop("additional_tests")
        result.pop("levene")
        missing_sections = {
            "multiple_summary",
            "comparison_intervals",
            "pairwise",
            "non_overlap",
            "additional_tests",
        }
    elif method == "eda.graphical_summary":
        for column in result["columns"]:
            for key in (
                "normal_fit_curve",
                "anderson_darling",
                "confidence_intervals",
                "variance",
                "skewness",
                "kurtosis_excess",
            ):
                column.pop(key)
        missing_sections = {"normal_fit", "normality", "confidence_intervals", "moments"}
    else:
        # Descriptive is a table-only method; never invent a chart requirement.
        result["columns"][0].pop("q1")
        missing_sections = {"distribution_summary"}
    before = copy.deepcopy(result)
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition(method, result), body) == "summary"
    assert missing_sections <= {
        section.section_id for section in body.sections if section.status == "missing"
    }
    assert result == before


def test_table_only_legacy_graphical_result_does_not_claim_plots() -> None:
    result = payload("eda.graphical_summary")
    result["schema_version"] = 1
    for column in result["columns"]:
        for field in (
            "histogram",
            "boxplot",
            "qq_plot",
            "ecdf",
            "normal_fit_curve",
            "anderson_darling",
            "confidence_intervals",
        ):
            column.pop(field)
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition("eda.graphical_summary", result), body) == "summary"
    assert "<svg" not in body.render()


@pytest.mark.parametrize(
    "field,section_id",
    [
        ("histogram", "histogram"),
        ("boxplot", "boxplot"),
        ("qq_plot", "qq_plot"),
        ("ecdf", "ecdf"),
        ("confidence_intervals", "confidence_intervals"),
    ],
)
def test_missing_current_graphic_is_summary_not_false_full(field: str, section_id: str) -> None:
    result = payload("eda.graphical_summary")
    result["columns"][0].pop(field)
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition("eda.graphical_summary", result), body) == "summary"
    assert next(item for item in body.sections if item.section_id == section_id).status == "missing"


def test_absent_callbacks_do_not_claim_rendered_graphics() -> None:
    result = payload("eda.graphical_summary")
    body = render_basic_eda_report(result, "en")
    assert assess_report_body(definition("eda.graphical_summary", result), body) == "summary"
    for section_id in ("histogram", "boxplot", "confidence_intervals"):
        assert (
            next(item for item in body.sections if item.section_id == section_id).status
            == "missing"
        )


def test_all_saved_qq_ecdf_points_and_limits_are_preserved() -> None:
    result = summarize_numeric_graphics(
        [[str(index + (index % 5) * 0.01)] for index in range(240)],
        [GraphicalSummaryColumn(*COLUMN_ARGS)],
        point_limit=151,
    )
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    sections = {section.section_id: section.markup or "" for section in body.sections}
    for key in ("qq_plot", "ecdf"):
        assert result["columns"][0][key]["point_count"] == 151
        assert sections[key].count("<circle ") == 151
        assert "<td>240</td>" in sections[key] and "<td>151</td>" in sections[key]
        assert "Display limited" in sections[key]
    assert "Theoretical standard-normal quantile" in sections["qq_plot"]
    assert "Cumulative probability" in sections["ecdf"]


@pytest.mark.parametrize("rows", [[["1"]], [["1"], ["1"], ["1"]], [[None], ["bad"]]])
def test_graphical_not_computed_sections_preserve_saved_unavailability(
    rows: list[list[str | None]],
) -> None:
    result = summarize_numeric_graphics(rows, [GraphicalSummaryColumn(*COLUMN_ARGS)])
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition("eda.graphical_summary", result), body) == "full"
    assert "<td>No</td>" in body.render()
    assert "No usable stored points" in body.render() or "<svg" in body.render()


def test_multiple_intervals_not_computed_does_not_invent_an_interval() -> None:
    result = calculate_equal_variances(
        [[str(value), group] for group in ("A", "B") for value in (1, 2, 3)],
        EqualVarianceResponseColumn(*COLUMN_ARGS),
        GROUP,
    )
    assert result["multiple_comparisons"]["computed"] is False
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition("eda.equal_variances", result), body) == "full"
    section = next(item for item in body.sections if item.section_id == "comparison_intervals")
    assert "were not computed" in (section.markup or "") and "<svg" not in (section.markup or "")


@pytest.mark.parametrize("method", METHODS)
def test_unknown_warning_and_private_use_characters_are_preserved(method: str) -> None:
    result = payload(method)
    warning = "future_warning_<script>\ue000fixture.key\ue001"
    target = result if method == "eda.equal_variances" else result["columns"][0]
    target["warnings"].append(warning)
    for locale in ("ko", "en"):
        markup = render_basic_eda_report(result, locale, plots=PLOTS).render()
        assert escape(warning) in markup
        assert "<script>" not in markup


@pytest.mark.parametrize("schema", [True, "2", 0, 3])
def test_unsupported_schema_is_not_rendered(schema: object) -> None:
    result = payload("eda.descriptive")
    result["schema_version"] = schema
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert body.unsupported_reason == "unsupported_result_schema"
    assert not body.sections


@pytest.mark.parametrize("field", ["histogram", "qq_plot", "ecdf"])
def test_non_finite_graphics_are_rejected(field: str) -> None:
    result = payload("eda.graphical_summary")
    if field == "histogram":
        result["columns"][0][field]["bins"][0]["count"] = float("nan")
    else:
        result["columns"][0][field]["points"][0][
            "sample" if field == "qq_plot" else "probability"
        ] = float("inf")
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        render_basic_eda_report(result, "en", plots=PLOTS)


def test_mismatched_stored_point_count_is_rejected() -> None:
    result = payload("eda.graphical_summary")
    result["columns"][0]["qq_plot"]["point_count"] += 1
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        render_basic_eda_report(result, "en", plots=PLOTS)


@pytest.mark.parametrize(
    "source,field,section_id",
    [
        ("anderson_darling", "p_value", "normality"),
        ("anderson_darling", "critical_values", "normality"),
        ("normal_fit_curve", "standard_deviation", "normal_fit"),
        ("normal_fit_curve", "points", "normal_fit"),
    ],
)
def test_incomplete_computed_optional_results_do_not_claim_full(
    source: str, field: str, section_id: str
) -> None:
    result = payload("eda.graphical_summary")
    result["columns"][0][source].pop(field)
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition("eda.graphical_summary", result), body) == "summary"
    assert next(item for item in body.sections if item.section_id == section_id).status == "missing"


def test_ad_critical_levels_remain_proportions_not_false_percentages() -> None:
    result = payload("eda.graphical_summary")
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    markup = next(item for item in body.sections if item.section_id == "normality").markup or ""
    assert "Significance level (proportion)" in markup
    assert "Significance level (%)" not in markup
    for item in result["columns"][0]["anderson_darling"]["critical_values"]:
        assert f"<td>{report_value(item['significance_level'])}</td>" in markup


@pytest.mark.parametrize(
    "field,section_id", [("pairwise_p_values", "pairwise"), ("groups", "comparison_intervals")]
)
def test_incomplete_multiple_comparison_details_are_summary(field: str, section_id: str) -> None:
    result = payload("eda.equal_variances")
    if field == "groups":
        result["multiple_comparisons"][field].pop()
    else:
        result["multiple_comparisons"][field][0].pop("p_value")
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition("eda.equal_variances", result), body) == "summary"
    assert next(item for item in body.sections if item.section_id == section_id).status == "missing"


@pytest.mark.parametrize("method", METHODS)
def test_render_uses_only_supplied_stored_payload(
    method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = payload(method)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("report must not read raw rows or rerun statistics")

    for module, name in (
        ("app.statistics.descriptive", "describe_numeric_columns"),
        ("app.statistics.graphical_summary", "summarize_numeric_graphics"),
        ("app.statistics.equal_variances", "calculate_equal_variances"),
        ("app.services.dataset_rows", "get_dataset_rows_context"),
    ):
        if module in sys.modules:
            monkeypatch.setattr(sys.modules[module], name, forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    body = render_basic_eda_report(result, "en", plots=PLOTS)
    assert assess_report_body(definition(method, result), body) == "full"
