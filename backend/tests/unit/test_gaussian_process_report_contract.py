"""Saved-payload display parity, not an independent GP numerical reference."""

import copy
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest

from app.services.analysis_run_exports import prepare_analysis_report
from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    calculate_gaussian_process_regression,
)


@pytest.fixture(scope="module")
def stored():
    def column(name, index, role):
        return GaussianProcessColumn(name, index, name, "decimal", "continuous", role, "mg")

    result = calculate_gaussian_process_regression(
        [[str(i), str(i * i / 10 + i % 3)] for i in range(12)],
        column("y", 1, "response"),
        [column("x", 0, "predictor")],
        options=GaussianProcessOptions(
            optimizer_restarts=0,
            cv_optimizer_restarts=0,
            validation_method="k_fold",
            cv_folds=3,
            profile_points=10,
        ),
    )
    # The runner persists the numeric prediction basis separately from the result.
    result.pop("prediction_basis", None)
    return result


def prepare(payload, locale="en"):
    return prepare_analysis_report(
        SimpleNamespace(method_id="regression.gaussian_process", result=payload), locale
    )


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_saved_gp_sections_match_visible_values_without_refit(stored, monkeypatch, locale):
    import app.statistics.gaussian_process_regression as gp

    def forbidden(*args, **kwargs):
        pytest.fail("Report must not fit or predict")

    monkeypatch.setattr(gp, "calculate_gaussian_process_regression", forbidden)
    monkeypatch.setattr(gp, "predict_from_gaussian_process_state", forbidden)
    original = copy.deepcopy(stored)
    report = prepare(stored, locale)
    assert report.level == "full"
    sections = {s.section_id: s for s in report.body.sections}
    assert sections["gp_surface_mean"].status == "not_applicable"
    for key in ("gp_training_plot", "gp_cv_plot", "gp_residual_plot", "gp_uncertainty_plot"):
        assert sections[key].status == "rendered"
        root = ET.fromstring("<body>" + sections[key].markup + "</body>")
        assert len(root.findall(".//circle")) == len(stored["diagnostics"]["points"])
    residual = sections["gp_residual_plot"].markup
    assert ("Residual (mg)" if locale == "en" else "잔차 (mg)") in residual
    assert str(stored["conditional_profiles"][0]["fixed_values"]) in sections["gp_profiles"].markup
    assert stored == original


def test_missing_gp_plots_and_legacy_settings_are_summary(stored):
    legacy = copy.deepcopy(stored)
    legacy["schema_version"] = 1
    del legacy["method"]["length_scale"]
    del legacy["diagnostics"]
    report = prepare(legacy)
    assert report.level == "summary"
    statuses = {section.section_id: section.status for section in report.body.sections}
    assert statuses["gp_results"] == "rendered"
    assert statuses["gp_training_plot"] == "missing"
    assert statuses["gp_reproducibility"] == "missing"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(model_summary={}),
        lambda p: p["model_summary"].update(training_rmse=float("nan")),
        lambda p: p["kernel"].update(parameters=[]),
        lambda p: p["kernel"].update(fitted_kernel=""),
        lambda p: p.update(kernel_selection={"mode": "compare"}, kernel_candidates=[]),
        lambda p: p.update(kernel_selection={"mode": "invalid"}),
        lambda p: p.update(kernel_selection=["malformed"]),
        lambda p: p.update(method=[]),
        lambda p: p.update(diagnostics=[]),
        lambda p: p.update(response=[]),
        lambda p: p.update(optimization={"final_runs": ["invalid"]}),
        lambda p: p["method"].update(length_scale=[1]),
    ],
)
def test_invalid_gp_core_or_comparison_not_a_success_report(stored, mutate):
    payload = copy.deepcopy(stored)
    mutate(payload)
    assert prepare(payload).level == "unsupported"


def test_no_cv_is_not_an_unavailable_requested_plot(stored):
    payload = copy.deepcopy(stored)
    payload["method"]["validation_method"] = "none"
    for point in payload["diagnostics"]["points"]:
        point["cross_validated_fitted"] = None
    report = prepare(payload)
    assert report.level == "full"
    section = next(s for s in report.body.sections if s.section_id == "gp_cv_plot")
    assert section.status == "not_applicable"
    assert section.reason == "validation_not_requested"
