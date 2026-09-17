from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.analyses.registry import METHODS
from app.services import analysis_run_exports as exports
from app.services.report_coverage import INLINE_REPORT_CONTRACTS


def test_every_inline_method_has_an_explicit_report_contract_and_dispatch():
    expected = {
        m.method_id
        for m in METHODS
        if m.execution_mode == "inline" and m.availability == "available"
    }
    assert set(INLINE_REPORT_CONTRACTS) == expected
    special = {
        "descriptive_statistics": "_descriptive_statistics_report_section",
        "graphical_summary": "_graphical_summary_report_section_v2",
        "normality_test": "_normality_report_section",
        "equal_variances_test": "_equal_variances_report_section_v2",
        "principal_components_analysis": "_principal_components_report_section",
        "partial_least_squares_regression": "render_pls_report",
        "gaussian_process_regression": "_gaussian_process_report_section",
    }
    for method_id, (summary, schemas) in INLINE_REPORT_CONTRACTS.items():
        renderer = special.get(summary)
        if renderer is None:
            groups = [
                (exports.HYPOTHESIS_REPORT_SUMMARY_TYPES, "_hypothesis_report_section"),
                (exports.CATEGORICAL_REPORT_SUMMARY_TYPES, "_categorical_report_section"),
                (exports.REGRESSION_REPORT_SUMMARY_TYPES, "_regression_report_section"),
                (exports.QUALITY_REPORT_SUMMARY_TYPES, "_quality_report_section"),
            ]
            renderer = next(name for values, name in groups if summary in values)
        with patch.object(
            exports, renderer, return_value="<table><tr><td>dispatch</td></tr></table>"
        ) as render:
            envelope = SimpleNamespace(
                method_id=method_id,
                result={"summary_type": summary, "schema_version": max(schemas), "fixture": True},
            )
            assert "<table>" in exports._analysis_result_method_specific_report_section(
                envelope, "en"
            )
            render.assert_called_once()


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
