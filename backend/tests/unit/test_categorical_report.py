import json
from html import escape
from typing import Any

import pytest

from app.services.categorical_report import CATEGORICAL_REPORT_VARIANTS, render_categorical_report
from app.services.report_contract import ReportDefinition, assess_report_body
from app.statistics.chi_square_association import calculate_chi_square_association
from app.statistics.one_proportion import OneProportionColumn, calculate_one_proportion
from app.statistics.two_proportion import calculate_two_proportion

NAME = '<svg onload="bad"> 원본 \ue000fixture.key\ue001'
COLUMN = OneProportionColumn("event-id", 0, NAME, "string", "nominal", "response", None)
GROUP = OneProportionColumn("group-id", 1, "그룹 <&>", "string", "nominal", "group", None)
ROWS = [
    [event, group]
    for group, events in (("A<&>", ["yes"] * 8 + ["no"] * 4), ("B", ["yes"] * 4 + ["no"] * 10))
    for event in events
] + [[None, "A<&>"], ["yes", None]]


def payload(variant: str) -> dict[str, Any]:
    if variant == "one_proportion":
        return calculate_one_proportion(ROWS, COLUMN, event_level="yes")
    if variant == "two_proportion":
        return calculate_two_proportion(ROWS, COLUMN, GROUP, event_level="yes")
    if variant == "chi_square":
        return calculate_chi_square_association(ROWS, COLUMN, GROUP)
    raise AssertionError(variant)


def definition(result: dict[str, Any]) -> ReportDefinition:
    return ReportDefinition(
        "test", result["summary_type"], (1,), "categorical", "1", CATEGORICAL_REPORT_VARIANTS
    )


@pytest.mark.parametrize("locale", ["ko", "en"])
@pytest.mark.parametrize("variant", [item.variant_id for item in CATEGORICAL_REPORT_VARIANTS])
def test_actual_categorical_payloads_render_visible_results_without_mutation(
    variant: str, locale: str
) -> None:
    result = payload(variant)
    before = json.dumps(result, sort_keys=True, ensure_ascii=False)
    body = render_categorical_report(result, locale)
    markup = body.render()
    assert body.variant_id == variant
    assert assess_report_body(definition(result), body) == "full"
    assert '<div data-report-section="test"' in markup
    assert '<div data-report-section="settings"' in markup
    assert "<table>" in markup and "<svg" in markup
    assert escape(NAME) in markup and '<svg onload="bad">' not in markup
    assert "\ue000fixture.key\ue001" in markup
    assert f"{result['test']['p_value']:.10g}" in markup
    assert ("입력 및 설정" if locale == "ko" else "Inputs and settings") in markup
    assert json.dumps(result, sort_keys=True, ensure_ascii=False) == before


@pytest.mark.parametrize("variant", [item.variant_id for item in CATEGORICAL_REPORT_VARIANTS])
def test_core_missing_is_unsupported_optional_missing_is_summary(variant: str) -> None:
    result = payload(variant)
    result.pop("test")
    assert (
        assess_report_body(definition(result), render_categorical_report(result)) == "unsupported"
    )
    result = payload(variant)
    result.pop("warnings")
    assert assess_report_body(definition(result), render_categorical_report(result)) == "summary"


def test_two_proportions_uses_real_count_rows_not_nonexistent_cells() -> None:
    result = payload("two_proportion")
    section = next(
        item
        for item in render_categorical_report(result, "en").sections
        if item.section_id == "contingency_table"
    )
    assert section.markup and "Events" in section.markup and "Non-events" in section.markup
    assert "<td>8</td><td>4</td>" in section.markup
    assert "<td>4</td><td>10</td>" in section.markup
    assert "A&lt;&amp;&gt;" in section.markup


def test_zero_cell_ratios_do_not_invent_intervals() -> None:
    rows = [["yes", "A"]] * 5 + [["yes", "B"]] * 3 + [["no", "B"]] * 2
    result = calculate_two_proportion(rows, COLUMN, GROUP, event_level="yes")
    body = render_categorical_report(result, "en")
    effects = next(item for item in body.sections if item.section_id == "effect_sizes")
    assert effects.markup and "No interval for this effect is stored" in effects.markup
    assert "Risk ratio" in effects.markup and "Odds ratio" in effects.markup
    assert assess_report_body(definition(result), body) == "full"
    assert result["effect_sizes"]["odds_ratio"]["confidence_interval"] is None


def test_chi_square_preserves_expected_counts_percentages_residuals_and_recommendations() -> None:
    result = payload("chi_square")
    body = render_categorical_report(result, "en")
    diagnostics = next(item for item in body.sections if item.section_id == "cell_diagnostics")
    expected = next(item for item in body.sections if item.section_id == "expected_counts")
    assert diagnostics.markup and expected.markup
    for row in result["contingency_table"]["rows"]:
        for cell in row["cells"]:
            for key in (
                "observed",
                "expected",
                "row_percent",
                "column_percent",
                "total_percent",
                "standardized_residual",
            ):
                assert f"{cell[key]:.10g}" in diagnostics.markup
    assert "Cells below 5" in expected.markup
    assert "does not mean that another test was executed" in body.render()
    assert "Cramer V" in body.render()


def test_large_stored_chi_square_table_preserves_more_than_100_cells() -> None:
    rows = [
        [f"row {row_index}", f"column {col_index}"]
        for row_index in range(12)
        for col_index in range(12)
        for _ in range(2)
    ]
    result = calculate_chi_square_association(rows, COLUMN, GROUP)
    body = render_categorical_report(result, "en")
    diagnostics = next(item for item in body.sections if item.section_id == "cell_diagnostics")
    assert diagnostics.markup and diagnostics.markup.count("<tr>") == 145
    assert "row 11" in body.render() and "column 11" in body.render()
    assert body.render().count('data-value="2.0"') == 144


def test_unknown_warning_code_and_original_message_are_escaped_and_retained() -> None:
    result = payload("one_proportion")
    result["warnings"] = [
        "future_warning",
        {"code": "future_warning_with_context", "message": NAME},
    ]
    markup = render_categorical_report(result, "en").render()
    assert "future_warning" in markup and "future_warning_with_context" in markup
    assert escape(NAME) in markup


def test_malformed_values_unknown_schema_and_missing_cell_details_are_honest() -> None:
    result = payload("chi_square")
    result["contingency_table"]["rows"][0]["cells"][0]["observed"] = float("inf")
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        render_categorical_report(result)
    result = payload("chi_square")
    result["contingency_table"]["rows"][0]["cells"][0].pop("standardized_residual")
    assert assess_report_body(definition(result), render_categorical_report(result)) == "summary"
    result["schema_version"] = 99
    assert (
        assess_report_body(definition(result), render_categorical_report(result)) == "unsupported"
    )
    result["schema_version"] = True
    assert render_categorical_report(result).unsupported_reason


def test_categorical_renderer_performs_no_calculation_or_file_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [payload(item.variant_id) for item in CATEGORICAL_REPORT_VARIANTS]

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Report rendering must not recalculate or read raw files")

    with monkeypatch.context() as context:
        context.setattr("builtins.open", forbidden)
        context.setattr("app.statistics.one_proportion.calculate_one_proportion", forbidden)
        context.setattr("app.statistics.two_proportion.calculate_two_proportion", forbidden)
        context.setattr(
            "app.statistics.chi_square_association.calculate_chi_square_association", forbidden
        )
        for result in results:
            assert render_categorical_report(result, "en").render()
