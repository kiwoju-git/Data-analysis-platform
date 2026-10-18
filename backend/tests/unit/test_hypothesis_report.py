"""Visible report assertions over actual calculator payloads, not embedded JSON."""

import copy
import json
import re
import sys
from html import escape
from typing import Any

import pytest

from app.services.hypothesis_report import HYPOTHESIS_REPORT_VARIANTS, render_hypothesis_report
from app.services.report_contract import ReportDefinition, assess_report_body
from app.statistics.equivalence_tost import (
    EquivalenceTostColumn,
    calculate_equivalence_tost,
    calculate_paired_equivalence_tost,
    calculate_two_sample_equivalence_tost,
)
from app.statistics.kruskal_wallis import calculate_kruskal_wallis
from app.statistics.mann_whitney import calculate_mann_whitney, calculate_mann_whitney_unstacked
from app.statistics.one_sample_t import calculate_one_sample_t
from app.statistics.one_sample_wilcoxon import calculate_one_sample_wilcoxon
from app.statistics.one_way_anova import calculate_one_way_anova
from app.statistics.paired_t import calculate_paired_t
from app.statistics.two_sample_t import calculate_two_sample_t

NAME = '<script>not executable</script> 변수 "\\\ue000fixture.key\ue001'
COLUMN = EquivalenceTostColumn("response-id", 0, NAME, "number", "continuous", "response", "mg/L")
GROUP = EquivalenceTostColumn("group-id", 1, "그룹<&>", "string", "nominal", "group", None)
SECOND = EquivalenceTostColumn("second-id", 1, "측정 B", "number", "continuous", "response", "mg/L")
ROWS = [[str(value)] for value in (1, 2, 4, 5, 7, 8, 9)] + [[None], ["bad"]]
GROUP_ROWS = [
    [str(value), group]
    for group, values in (
        ("A<&>", (1, 2, 3, 4, 5)),
        ("B", (2, 4, 5, 6, 8)),
        ("C", (3, 6, 7, 9, 12)),
    )
    for value in values
]
PAIR_ROWS = [["1", "2"], ["2", "4"], ["4", "5"], ["5", "9"], ["7", None], ["bad", "5"]]


def payload(variant: str) -> dict[str, Any]:
    if variant == "one_sample_t":
        return calculate_one_sample_t(ROWS, COLUMN, null_mean=2)
    if variant == "paired_t":
        return calculate_paired_t(PAIR_ROWS, COLUMN, SECOND)
    if variant == "two_sample_t":
        return calculate_two_sample_t(GROUP_ROWS[:10], COLUMN, GROUP)
    if variant == "wilcoxon":
        return calculate_one_sample_wilcoxon(ROWS, COLUMN, null_location=3)
    if variant == "mann_whitney":
        return calculate_mann_whitney(GROUP_ROWS[:10], COLUMN, GROUP)
    if variant == "kruskal_wallis":
        return calculate_kruskal_wallis(
            [
                [str(index * 20 + value), group]
                for index, group in enumerate(("A<&>", "B", "C"))
                for value in (1, 2, 3, 4, 5)
            ],
            COLUMN,
            GROUP,
            posthoc_method="dunn_holm",
            posthoc_policy="after_significant",
        )
    if variant == "anova_standard":
        return calculate_one_way_anova(GROUP_ROWS, COLUMN, GROUP)
    if variant == "anova_welch":
        return calculate_one_way_anova(
            GROUP_ROWS, COLUMN, GROUP, anova_type="welch", posthoc_method="games_howell"
        )
    if variant == "tost_one_sample":
        return calculate_equivalence_tost(
            ROWS, COLUMN, reference_mean=3, lower_bound=-4, upper_bound=4
        )
    if variant == "tost_two_sample":
        return calculate_two_sample_equivalence_tost(
            GROUP_ROWS[:10],
            COLUMN,
            GROUP,
            test_group_label="B",
            reference_group_label="A<&>",
            lower_bound=-4,
            upper_bound=4,
        )
    if variant == "tost_paired":
        return calculate_paired_equivalence_tost(
            PAIR_ROWS, COLUMN, SECOND, lower_bound=-4, upper_bound=4
        )
    raise AssertionError(variant)


def definition(result: dict[str, Any]) -> ReportDefinition:
    return ReportDefinition(
        "test", result["summary_type"], (1, 2), "hypothesis", "1", HYPOTHESIS_REPORT_VARIANTS
    )


@pytest.mark.parametrize("locale", ["ko", "en"])
@pytest.mark.parametrize("variant", [item.variant_id for item in HYPOTHESIS_REPORT_VARIANTS])
def test_actual_hypothesis_payloads_have_visible_complete_sections(
    variant: str, locale: str
) -> None:
    result = payload(variant)
    before = json.dumps(result, sort_keys=True, ensure_ascii=False)
    body = render_hypothesis_report(result, locale)
    markup = body.render()
    assert body.variant_id == variant
    assert assess_report_body(definition(result), body) == (
        "summary" if variant.startswith("anova_") else "full"
    )
    assert '<div data-report-section="test"' in markup
    assert '<div data-report-section="settings"' in markup
    assert "<table>" in markup
    assert escape(NAME) in markup
    assert "<script>" not in markup
    assert "mg/L" in markup
    assert ("입력 및 설정" if locale == "ko" else "Inputs and settings") in markup
    test = result.get("contrast", result.get("test", result.get("tost")))
    assert f"{test['p_value']:.10g}" in markup
    assert json.dumps(result, sort_keys=True, ensure_ascii=False) == before
    if variant.startswith("tost_") or variant in {"one_sample_t", "two_sample_t", "paired_t"}:
        assert "<svg" in markup
    if variant.startswith("anova_"):
        assert (
            next(item for item in body.sections if item.section_id == "residual_diagnostics").reason
            == "residuals_not_stored"
        )


@pytest.mark.parametrize("variant", [item.variant_id for item in HYPOTHESIS_REPORT_VARIANTS])
def test_missing_core_or_optional_payload_is_not_claimed_full(variant: str) -> None:
    result = payload(variant)
    result.pop("n_used")
    assert assess_report_body(definition(result), render_hypothesis_report(result)) == "unsupported"
    result = payload(variant)
    result.pop("warnings")
    assert assess_report_body(definition(result), render_hypothesis_report(result)) == "summary"


def test_anova_posthoc_preserves_raw_adjusted_p_df_and_intervals() -> None:
    result = payload("anova_welch")
    body = render_hypothesis_report(result, "en")
    section = next(item for item in body.sections if item.section_id == "posthoc")
    assert section.markup
    assert "games_howell" in section.markup
    assert "Raw P value" in section.markup
    assert "Adjusted P value" in section.markup
    for pair in result["posthoc"]["comparisons"]:
        assert f"{pair['adjusted_p_value']:.10g}" in section.markup
        assert f"{pair['confidence_interval']['lower']:.10g}" in section.markup
    test_section = next(item for item in body.sections if item.section_id == "test")
    assert (
        test_section.markup
        and "Numerator DF" in test_section.markup
        and "Denominator DF" in test_section.markup
    )
    assert (
        next(item for item in body.sections if item.section_id == "anova_table").status
        == "not_applicable"
    )


def test_kruskal_wallis_preserves_rank_not_mean_difference_and_no_fake_ci() -> None:
    result = payload("kruskal_wallis")
    body = render_hypothesis_report(result, "en")
    section = next(item for item in body.sections if item.section_id == "posthoc")
    assert (
        section.markup
        and "Mean rank difference" in section.markup
        and "Raw P value" in section.markup
    )
    for pair in result["posthoc"]["comparisons"]:
        assert f"{pair['mean_rank_difference']:.10g}" in section.markup
    assert (
        next(item for item in body.sections if item.section_id == "estimate_interval").status
        == "not_applicable"
    )
    assert "<svg" not in body.render()


def test_skipped_posthoc_preserves_reason_and_policy() -> None:
    result = calculate_one_way_anova(GROUP_ROWS, COLUMN, GROUP, posthoc_method="none")
    body = render_hypothesis_report(result, "en")
    section = next(item for item in body.sections if item.section_id == "posthoc")
    assert section.status == "rendered" and section.markup
    assert result["posthoc"]["reason"] in section.markup


def test_tost_independent_reports_both_actual_samples_and_difference_direction() -> None:
    result = payload("tost_two_sample")
    body = render_hypothesis_report(result, "en")
    samples = next(item for item in body.sections if item.section_id == "sample_summary")
    assert (
        samples.markup and "Test sample" in samples.markup and "Reference sample" in samples.markup
    )
    assert re.search(
        r"<td(?:\s[^>]*)?>"
        + re.escape(f"{result['samples']['reference']['mean']:.10g}")
        + r"</td>",
        samples.markup,
    )
    assert result["estimate_definition"] in body.render()
    assert "0.9" in body.render()
    assert (
        next(item for item in body.sections if item.section_id == "effect_sizes").status
        == "not_applicable"
    )
    result.pop("samples")
    assert assess_report_body(definition(result), render_hypothesis_report(result)) == "unsupported"


def test_one_sided_t_interval_remains_unbounded_and_has_no_fake_endpoint() -> None:
    result = calculate_one_sample_t(ROWS, COLUMN, alternative="greater")
    body = render_hypothesis_report(result, "en")
    assert "Unbounded above" in body.render()
    assert "<svg" not in body.render()
    assert assess_report_body(definition(result), body) == "full"


def test_unstacked_mann_whitney_retains_sample_specific_exclusions() -> None:
    result = calculate_mann_whitney_unstacked(PAIR_ROWS, COLUMN, SECOND)
    body = render_hypothesis_report(result, "en")
    assert assess_report_body(definition(result), body) == "full"
    inputs = next(item for item in body.sections if item.section_id == "sample_inputs")
    assert (
        inputs.markup
        and "Missing excluded" in inputs.markup
        and "Non-numeric excluded" in inputs.markup
    )
    assert "response-id" in inputs.markup and "second-id" in inputs.markup


def test_large_posthoc_payload_is_not_truncated_at_screen_row_limit() -> None:
    result = payload("kruskal_wallis")
    pair = result["posthoc"]["comparisons"][0]
    result["posthoc"]["comparisons"] = [
        {
            **pair,
            "group_1_label": f"synthetic stored group {index}",
            "group_1_value": f"synthetic stored group {index}",
        }
        for index in range(121)
    ]
    body = render_hypothesis_report(result, "en")
    section = next(item for item in body.sections if item.section_id == "posthoc")
    assert section.markup and section.markup.count("synthetic stored group ") == 121


def test_unknown_warnings_preserve_codes_messages_and_private_use_text() -> None:
    result = payload("one_sample_t")
    result["warnings"] = ["future_warning_code", {"code": "future_detail", "message": NAME}]
    markup = render_hypothesis_report(result, "en").render()
    assert "future_warning_code" in markup and "future_detail" in markup and escape(NAME) in markup
    assert "\ue000fixture.key\ue001" in markup


def test_malformed_stored_numbers_fail_and_unknown_schema_is_unsupported() -> None:
    result = payload("one_sample_t")
    result["contrast"]["p_value"] = float("nan")
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        render_hypothesis_report(result)
    result = payload("one_sample_t")
    result["schema_version"] = 99
    assert assess_report_body(definition(result), render_hypothesis_report(result)) == "unsupported"
    result["schema_version"] = True
    assert render_hypothesis_report(result).unsupported_reason


def test_legacy_mann_whitney_missing_per_sample_exclusions_is_honest_summary() -> None:
    result = copy.deepcopy(payload("mann_whitney"))
    result["schema_version"] = 1
    result.pop("samples")
    body = render_hypothesis_report(result, "en")
    assert assess_report_body(definition(result), body) == "summary"
    assert (
        next(item for item in body.sections if item.section_id == "sample_inputs").status
        == "missing"
    )


def test_renderer_never_reexecutes_calculations_or_reads_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [payload(item.variant_id) for item in HYPOTHESIS_REPORT_VARIANTS]

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Report rendering must not recalculate or read raw files")

    with monkeypatch.context() as context:
        context.setattr("builtins.open", forbidden)
        for name, module in list(sys.modules.items()):
            if name.startswith("app.statistics.") and module is not None:
                for key in vars(module):
                    if key.startswith("calculate_"):
                        context.setattr(module, key, forbidden)
        for result in results:
            assert render_hypothesis_report(result, "en").render()


def test_per_method_variant_declarations_do_not_mix_tost_designs() -> None:
    from app.services.hypothesis_report import HYPOTHESIS_REPORT_VARIANTS_BY_METHOD

    expected = {
        "hypothesis.equivalence_tost": "tost_one_sample",
        "hypothesis.two_sample_equivalence_tost": "tost_two_sample",
        "hypothesis.paired_equivalence_tost": "tost_paired",
    }
    for method, variant in expected.items():
        assert [item.variant_id for item in HYPOTHESIS_REPORT_VARIANTS_BY_METHOD[method]] == [
            variant
        ]


@pytest.mark.parametrize(
    "changes",
    [
        {"anova_type": "future_method"},
        {"variance_model": "future_variance_model"},
        {"anova_type": "standard", "variance_model": "unequal"},
    ],
)
def test_unknown_or_contradictory_anova_variant_is_not_defaulted_to_standard(
    changes: dict[str, str],
) -> None:
    result = {**payload("anova_standard"), **changes}
    body = render_hypothesis_report(result)
    assert body.unsupported_reason == "unsupported_result_variant"
    assert assess_report_body(definition(result), body) == "unsupported"
