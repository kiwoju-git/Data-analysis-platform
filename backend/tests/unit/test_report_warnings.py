from html import escape

import pytest

from app.services.report_warnings import REPORT_WARNING_TRANSLATIONS, report_warning_text
from app.services.stored_report_primitives import report_table


@pytest.mark.parametrize("code", sorted(REPORT_WARNING_TRANSLATIONS))
def test_known_warning_codes_use_bilingual_explicit_meaning(code: str) -> None:
    ko, en = REPORT_WARNING_TRANSLATIONS[code]
    assert report_warning_text(code, ko, "en") == en
    assert report_warning_text(code, en, "ko") == ko
    assert report_warning_text(code, code, "en") == en
    assert ko != en


@pytest.mark.parametrize("locale", ["ko", "en"])
def test_unknown_warning_keeps_original_text_and_code_at_display_boundary(locale: str) -> None:
    code = "future_warning<&>"
    message = '<script>alert(1)</script> "\\\n\ue000fixture.key\ue001'
    assert report_warning_text(code, message, locale) == message
    table = report_table(["code", "message"], [(code, report_warning_text(code, message, locale))])
    assert escape(code) in table and escape(message) in table
    assert "<script>" not in table
    assert "\ue000fixture.key\ue001" in table
    assert report_warning_text(code, "", locale) == code


@pytest.mark.parametrize("locale", ["ko", "en"])
def test_known_code_does_not_erase_contextual_or_user_containing_source_message(
    locale: str,
) -> None:
    message = 'Column "사용자 이름" <&> \ue000ui.home\ue001 has exclusions: 17 rows.'
    value = report_warning_text("missing_values_excluded", message, locale)
    assert message in value
    assert (
        REPORT_WARNING_TRANSLATIONS["missing_values_excluded"][0 if locale == "ko" else 1] in value
    )
    assert ("원문:" if locale == "ko" else "Original message:") in value


def test_scientific_warning_meanings_are_not_replaced_by_generic_advice() -> None:
    assert "not evidence of equivalence" in report_warning_text(
        "non_significance_is_not_equivalence", "", "en"
    )
    assert "not generally a test of median differences" in report_warning_text(
        "mann_whitney_not_median_test", "", "en"
    )
    assert "zero cells" in report_warning_text("zero_cell_effect_ci_unavailable", "", "en")
    assert "recommendation, not an executed test" in report_warning_text(
        "fisher_exact_recommended_for_sparse_2x2", "", "en"
    )
    assert "not independent external validation" in report_warning_text(
        "gp_kernel_selection_not_external_validation", "", "en"
    )
    assert "every usable row" in report_warning_text("pca_chart_points_limited", "", "en")
