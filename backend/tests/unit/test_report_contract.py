from dataclasses import replace

import pytest

from app.services.report_contract import (
    ReportBody,
    ReportDefinition,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
    assess_report_body,
)


def contract():
    return ReportDefinition(
        "fixture.method",
        "fixture",
        (1,),
        "fixture",
        "1.0.0",
        (
            ReportVariantDefinition(
                "default",
                (
                    ReportSectionDefinition("summary", core=True),
                    ReportSectionDefinition("diagnostics"),
                ),
            ),
        ),
    )


def body():
    return ReportBody(
        "default",
        (
            ReportSection(
                "summary", "Stored <values>", "rendered", "<table><tr><td>2</td></tr></table>"
            ),
            ReportSection(
                "diagnostics", "Stored diagnostics", "rendered", '<svg role="img"></svg>'
            ),
        ),
    )


def test_level_is_derived_from_actual_sections_and_applicability():
    original = body()
    assert assess_report_body(contract(), original) == "full"
    for status, expected in (("missing", "summary"), ("not_applicable", "full")):
        changed = replace(
            original,
            sections=(
                original.sections[0],
                ReportSection("diagnostics", "Stored diagnostics", status, reason="not_requested"),
            ),
        )
        assert assess_report_body(contract(), changed) == expected
        assert changed.rendered_count == 1
        assert "<values>" not in changed.render()
        assert "Stored &lt;values&gt;" in changed.render()
        assert 'data-report-section="summary"' in changed.render()
        assert 'data-report-section="diagnostics"' not in changed.render()


def test_missing_core_and_unknown_schema_are_unsupported_not_success_reports():
    original = body()
    changed = replace(
        original,
        sections=(
            ReportSection("summary", "Summary", "missing", reason="not_stored_in_result"),
            original.sections[1],
        ),
    )
    assert assess_report_body(contract(), changed) == "unsupported"
    assert (
        assess_report_body(
            contract(), ReportBody("unknown", (), "analysis_report_schema_unsupported")
        )
        == "unsupported"
    )


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate",
        "missing",
        "extra",
        "unknown_variant",
        "empty",
        "heading",
        "reason",
        "markup",
        "unsafe_id",
    ],
)
def test_contract_drift_and_empty_core_cannot_be_advertised_as_full(kind):
    original = body()
    section = original.sections[0]
    candidates = {
        "duplicate": replace(original, sections=(section, section)),
        "missing": replace(original, sections=(section,)),
        "extra": replace(
            original, sections=(*original.sections, replace(section, section_id="other"))
        ),
        "unknown_variant": replace(original, variant_id="unknown"),
        "empty": replace(original, sections=(replace(section, markup=" "), original.sections[1])),
        "heading": replace(
            original,
            sections=(replace(section, markup="<h3>Title only</h3>"), original.sections[1]),
        ),
        "reason": replace(
            original, sections=(replace(section, reason="none"), original.sections[1])
        ),
        "markup": replace(
            original,
            sections=(replace(section, status="missing", reason="missing"), original.sections[1]),
        ),
        "unsafe_id": replace(
            original, sections=(replace(section, section_id='x" bad'), original.sections[1])
        ),
    }
    with pytest.raises(ValueError, match="analysis_report_(contract|payload)_invalid"):
        assess_report_body(contract(), candidates[kind])
