from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.analyses.registry import METHODS
from app.services import analysis_run_exports as exports
from app.services.report_contract import ReportBody, ReportSection
from app.services.report_coverage import INLINE_REPORT_CONTRACTS, report_definitions


def test_every_inline_method_has_an_explicit_report_contract_and_dispatch():
    expected = {
        m.method_id
        for m in METHODS
        if m.execution_mode == "inline" and m.availability == "available"
    }
    assert set(INLINE_REPORT_CONTRACTS) == expected
    special = {
        "descriptive_statistics": "render_basic_eda_report",
        "graphical_summary": "render_basic_eda_report",
        "normality_test": "normality_report_body",
        "equal_variances_test": "render_basic_eda_report",
        "two_variances_test": "render_two_variances_report",
        "principal_components_analysis": "principal_components_report_body",
        "partial_least_squares_regression": "pls_report_body",
        "gaussian_process_regression": "_gaussian_process_report_section",
        "linear_model": "linear_model_report_body",
        "pearson_correlation": "correlation_report_body",
        "xy_correlation_matrix": "correlation_report_body",
    }
    for method_id, (summary, schemas) in INLINE_REPORT_CONTRACTS.items():
        renderer = special.get(summary)
        if renderer is None:
            groups = [
                (exports.HYPOTHESIS_REPORT_SUMMARY_TYPES, "render_hypothesis_report"),
                (exports.CATEGORICAL_REPORT_SUMMARY_TYPES, "render_categorical_report"),
                (exports.QUALITY_REPORT_SUMMARY_TYPES, "quality_report_body"),
            ]
            renderer = next(name for values, name in groups if summary in values)
        definition = report_definitions()[method_id]
        assert definition.summary_type == summary
        assert set(definition.accepted_schemas) == schemas
        variant = definition.variants[0]
        body = ReportBody(
            variant.variant_id,
            tuple(
                ReportSection(
                    section.section_id,
                    section.section_id,
                    "rendered",
                    "<table><tr><td>dispatch</td></tr></table>",
                )
                for section in variant.sections
            ),
        )
        returns_body = renderer.endswith("_body") or renderer in {
            "render_hypothesis_report",
            "render_categorical_report",
            "render_basic_eda_report",
        }
        with patch.object(
            exports,
            renderer,
            return_value=body if returns_body else "<table><tr><td>dispatch</td></tr></table>",
        ) as render:
            envelope = SimpleNamespace(
                method_id=method_id,
                result={
                    "summary_type": summary,
                    "schema_version": max(schemas),
                    "fixture": True,
                    "model_summary": {"selected_components": 1},
                },
            )
            assert "<table>" in exports._analysis_result_method_specific_report_section(
                envelope, "en"
            )
            render.assert_called_once()


def test_shared_tost_summary_does_not_authorize_other_design_variants():
    expected = {
        "hypothesis.equivalence_tost": "tost_one_sample",
        "hypothesis.two_sample_equivalence_tost": "tost_two_sample",
        "hypothesis.paired_equivalence_tost": "tost_paired",
    }
    for method_id, variant in expected.items():
        assert [v.variant_id for v in report_definitions()[method_id].variants] == [variant]


@pytest.mark.parametrize(
    "method,summary,schema",
    [
        ("future.method", "future", 1),
        ("regression.partial_least_squares", "partial_least_squares_regression", 999),
        ("regression.partial_least_squares", "linear_model", 1),
    ],
)
def test_unknown_or_mismatched_report_cannot_be_labelled_complete(method, summary, schema):
    with pytest.raises(ValueError, match="analysis_report_schema_unsupported"):
        exports._analysis_result_method_specific_report_section(
            SimpleNamespace(
                method_id=method, result={"summary_type": summary, "schema_version": schema}
            )
        )


@pytest.mark.parametrize("method_id", list(INLINE_REPORT_CONTRACTS))
def test_empty_known_core_result_cannot_be_a_success_report(method_id):
    summary, schemas = INLINE_REPORT_CONTRACTS[method_id]
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        exports._analysis_result_method_specific_report_section(
            SimpleNamespace(
                method_id=method_id,
                result={"summary_type": summary, "schema_version": max(schemas), "warnings": []},
            )
        )
