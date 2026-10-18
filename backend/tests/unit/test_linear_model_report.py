import json
from copy import deepcopy
from html import escape
from math import sin
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from app.services.analysis_run_exports import prepare_analysis_report
from app.services.linear_model_report import linear_model_report_body
from app.statistics.linear_model import LinearModelColumn, calculate_linear_model
from app.statistics.regularized_linear_model import (
    RegularizationConfig,
    calculate_regularized_linear_model,
)


def _payload(kind="ols", selection="none", count=130):
    response = LinearModelColumn(
        "y", 0, "Yield <test> 한글", "decimal", "continuous", "response", "mg"
    )
    predictors = [
        LinearModelColumn("x", 1, "Temperature", "decimal", "continuous", "predictor", "C")
    ]
    rows = [[str(2 + 0.7 * i + sin(i * 1.7)), str(i)] for i in range(count)]
    if kind == "ols":
        return calculate_linear_model(rows, response, predictors, model_selection_method=selection)
    return calculate_regularized_linear_model(
        rows,
        response,
        predictors,
        config=RegularizationConfig(
            estimator=kind,
            mode="automatic_cv",
            validation="k_fold",
            outer_folds=3,
            inner_folds=3,
            alpha_candidates=3,
            alpha_min=0.01,
            alpha_max=1.0,
        ),
    )


def _assert_stored_numeric_column(markup, header, stored_values):
    table = ElementTree.fromstring(f"<root>{markup}</root>").find(".//table")
    assert table is not None
    headers = ["".join(cell.itertext()) for cell in table.findall("./thead/tr/th")]
    column_index = headers.index(header)
    rows = table.findall("./tbody/tr")
    assert len(rows) == len(stored_values)
    # Precision is column-wide: distinct stored floats must have distinct visible labels.
    distinct_values = set(stored_values)
    digits = next(
        digits
        for digits in range(10, 18)
        if len({format(value, f".{digits}g") for value in distinct_values}) == len(distinct_values)
    )
    labels = []
    for row, value in zip(rows, stored_values, strict=True):
        cell = row.findall("td")[column_index]
        label = "".join(cell.itertext())
        assert label == format(value, f".{digits}g")
        assert cell.get("title") == repr(value)
        assert cell.get("aria-label") == repr(value)
        labels.append(label)
    assert len(set(labels)) == len(distinct_values)


@pytest.mark.parametrize("locale", ["en", "ko"])
@pytest.mark.parametrize("selection", ["none", "backward_elimination"])
def test_ols_report_uses_saved_coefficients_anova_selection_and_full_diagnostics(
    locale, selection, monkeypatch
):
    payload = _payload(selection=selection)
    before = json.dumps(payload, sort_keys=True)

    def forbidden(*args, **kwargs):
        pytest.fail("stored report attempted numerical fitting or source reads")

    monkeypatch.setattr("numpy.linalg.lstsq", forbidden)
    monkeypatch.setattr("app.services.dataset_rows.iter_dataset_rows", forbidden)
    prepared = prepare_analysis_report(
        SimpleNamespace(method_id="regression.linear_model", result=payload), locale
    )
    assert prepared.level == "full", prepared.body
    html = prepared.render()
    assert html.count("<svg") == 8
    assert escape(payload["response"]["display_name"]) in html
    assert escape(payload["equation"]["display_equation"]) in html
    coefficients = next(s.markup for s in prepared.body.sections if s.section_id == "coefficients")
    _assert_stored_numeric_column(
        coefficients, "T", [row["statistic"] for row in payload["coefficients"]]
    )
    _assert_stored_numeric_column(
        coefficients,
        "CI lower",
        [row["confidence_interval"]["lower"] for row in payload["coefficients"]],
    )
    anova = next(s.markup for s in prepared.body.sections if s.section_id == "anova")
    _assert_stored_numeric_column(
        anova, "Adjusted SS", [row["adjusted_ss"] for row in payload["anova"]["rows"]]
    )
    raw = next(s.markup for s in prepared.body.sections if s.section_id == "residuals_raw")
    assert raw.count("<circle") == 390
    assert ("Residual (mg)" if locale == "en" else "잔차 (mg)") in raw
    assert ("Stored Q-Q reference" if locale == "en" else "저장된 Q-Q 기준선") in raw
    assert "130 / 130" in raw
    selection_section = next(s for s in prepared.body.sections if s.section_id == "selection")
    assert selection_section.status == ("not_applicable" if selection == "none" else "rendered")
    assert json.dumps(payload, sort_keys=True) == before


def test_legacy_ols_is_summary_instead_of_inventing_unstored_plots():
    payload = _payload(count=12)
    for key in ("residual_plots", "model_selection", "anova"):
        payload.pop(key)
    payload["schema_version"] = 1
    prepared = prepare_analysis_report(
        SimpleNamespace(method_id="regression.linear_model", result=payload)
    )
    assert prepared.level == "summary"
    assert {s.section_id for s in prepared.body.sections if s.status == "missing"} == {
        "anova",
        "selection",
        "residuals_raw",
        "residuals_standardized",
    }
    assert "<svg" not in prepared.render()


@pytest.mark.parametrize("kind", ["ridge", "lasso", "elastic_net"])
def test_regularized_report_keeps_cv_path_and_adds_saved_distribution(kind):
    payload = _payload(kind=kind, count=30)
    prepared = prepare_analysis_report(
        SimpleNamespace(method_id="regression.linear_model", result=payload)
    )
    assert prepared.level == "full", prepared.body
    assert prepared.body.variant_id == kind
    html = prepared.render()
    assert "Cross-Validation Error" in html and "Coefficient Path" in html
    assert "Residual Normal Q-Q Plot" in html and "Residual Histogram" in html
    assert "Classical OLS inference" in html
    assert "Adjusted SS" not in html


def test_invalid_stored_plot_value_cannot_be_rendered_as_zero():
    payload = deepcopy(_payload(count=12))
    payload["residual_plots"]["qq_plots"]["raw"]["points"][0]["residual"] = float("nan")
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        linear_model_report_body(payload, "en")
