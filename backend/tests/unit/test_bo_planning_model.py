from copy import deepcopy

import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_planning_model import (
    evaluate_planning_points,
    fit_planning_model,
    restore_planning_model,
    score_ordered_selection,
)


@pytest.fixture(scope="module")
def snapshot():
    from test_bo_versioned_curves import curve_request

    return fit_planning_model(curve_request(2))


def _points(snapshot):
    factors = snapshot["calculation_request"]["factors"]
    return [
        {
            factor["factor_id"]: factor["low"] + position * (factor["high"] - factor["low"])
            for factor in factors
        }
        for position in (0.173, 0.633)
    ]


def test_saved_model_evaluation_and_ordered_selection_never_fit(snapshot, monkeypatch):
    import app.statistics.bo_desirability_core as core
    import app.statistics.bo_surrogate as surrogate

    def forbidden(*args, **kwargs):
        pytest.fail("no fit is allowed after storing a planning model")

    monkeypatch.setattr(surrogate, "fit_bo_surrogate", forbidden)
    monkeypatch.setattr(core, "_fit_response_models", forbidden)
    before = deepcopy(snapshot)
    points = _points(snapshot)
    evaluated = evaluate_planning_points(snapshot, points)
    selected = score_ordered_selection(snapshot, points)
    from app.api.v1.schemas.bo_planning import EvaluatedCandidateRow, PlanningSelectionCalculation

    for row in evaluated:
        assert EvaluatedCandidateRow.model_validate(row).model_dump(mode="json") == row
    assert PlanningSelectionCalculation.model_validate(selected).model_dump(mode="json") == selected
    from app.services.bo_planning_contract import (
        validate_planning_evaluation,
        validate_planning_selection,
    )

    validate_planning_evaluation(snapshot, points, [], evaluated)
    validate_planning_selection(snapshot, points, [], selected)
    assert selected["model_refit"] is False
    assert selected["selection_policy"] == "manual_ordered_fixed_model_v1"
    assert [item["actual_coordinates"] for item in selected["items"]] == points
    assert selected["items"][0]["planning"]["score"] == pytest.approx(
        evaluated[0]["acquisition"]["value"], rel=1e-13
    )
    for base, item in zip(evaluated, selected["items"], strict=True):
        assert base["response_predictions"] == item["response_predictions"]
    reordered = score_ordered_selection(snapshot, points[::-1])
    assert reordered["items"][0]["planning"]["sampler"]["conditioned_on_selected_ranks"] == []
    assert reordered["items"][1]["planning"]["sampler"]["conditioned_on_selected_ranks"] == [1]
    assert reordered["items"][0]["planning"]["score"] == pytest.approx(
        evaluated[1]["acquisition"]["value"], rel=1e-13
    )
    assert snapshot == before


def test_report_keeps_fit_warning_and_exact_order_without_refitting(snapshot, monkeypatch):
    from app.services.bo_planning_report import planning_report_section

    def forbidden(*args, **kwargs):
        pytest.fail("stored report must not fit or evaluate model")

    selected = score_ordered_selection(snapshot, _points(snapshot))
    before = deepcopy(snapshot)
    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    monkeypatch.setattr("app.statistics.bo_planning_model.restore_planning_model", forbidden)
    source = {
        "model_id": "synthetic-model",
        "model_sha256": "a" * 64,
        "candidate_revision_id": "synthetic-candidates",
        "rows_sha256": "b" * 64,
        "selection_id": "synthetic-selection",
        "selection_result_sha256": "c" * 64,
    }
    attachment = {
        "source": source,
        "calculation": selected,
        "objective": snapshot["calculation_request"]["objective"],
        "response_models": snapshot["response_models"],
        "incumbent": snapshot["incumbent"],
        "observation_view": snapshot["observation_view"],
        "warnings": ["synthetic_bound_warning", "<script>synthetic</script>"],
        "items": [{"trial": {"trial_id": f"synthetic-{i}"}} for i in (1, 2)],
    }
    definition = {
        "factors": [
            {**factor, "name": f"Synthetic {factor['factor_id']}"}
            for factor in snapshot["calculation_request"]["factors"]
        ]
    }
    for locale in ("en", "ko"):
        section = planning_report_section(attachment, definition, locale)
        assert section.status == "rendered"
        assert "synthetic_bound_warning" in section.markup
        assert "&lt;script&gt;synthetic&lt;/script&gt;" in section.markup
        assert '<section data-batch-rank="1">' in section.markup
        assert "a" * 64 in section.markup
    assert snapshot == before


def test_incumbent_tampering_is_not_a_new_valid_threshold(snapshot):
    changed = deepcopy(snapshot)
    changed["incumbent"]["latent_incumbent_value"] = 1.0
    with pytest.raises(BayesianOptimizationError, match="planning_snapshot_invalid"):
        restore_planning_model(changed)


@pytest.mark.parametrize("field", ["kernel", "noise", "jitter", "fit_policy"])
def test_request_and_saved_model_policy_must_match(snapshot, field):
    changed = deepcopy(snapshot)
    request = changed["calculation_request"]
    if field == "kernel":
        kernel = request["response_models"][0]["kernel"]
        kernel["kind"] = "gaussian" if kernel["kind"] != "gaussian" else "matern_3_2"
    elif field == "noise":
        request["response_models"][0]["surrogate"]["noise_mode"] = "near_noiseless"
        request["response_models"][0]["surrogate"]["fixed_noise_sd"] = None
    elif field == "jitter":
        request["search"]["jitter"] *= 2
    else:
        request["fit_policy"] = {
            "kind": "bounded_multiscale_starts_v1",
            "deterministic_start_count": 2,
        }
    with pytest.raises(BayesianOptimizationError):
        restore_planning_model(changed)


def test_view_budget_includes_model_validation_and_every_point(snapshot):
    with pytest.raises(BayesianOptimizationError, match="budget_exhausted"):
        evaluate_planning_points(snapshot, _points(snapshot), max_moment_evaluations=1)


def test_fit_rejects_insufficient_incumbent_budget_before_fitting(monkeypatch):
    from test_bo_versioned_curves import curve_request

    import app.statistics.bo_planning_model as planning

    def forbidden(*args, **kwargs):
        pytest.fail("preflight should reject before fit")

    monkeypatch.setattr(planning, "_fit_response_models", forbidden)
    request = curve_request(2)
    request["batch_options"]["max_moment_evaluations"] = 1
    with pytest.raises(BayesianOptimizationError, match="budget_exhausted"):
        fit_planning_model(request)


def test_incomplete_exclusion_source_is_rejected_before_evaluation(snapshot):
    changed = deepcopy(snapshot)
    request = changed["calculation_request"]
    request["excluded_normalized"] = [[0.12345] * len(request["factors"])]
    actual = request["observations"][0]["actual_coordinates"]
    with pytest.raises(BayesianOptimizationError, match="planning_input_invalid"):
        evaluate_planning_points(changed, [actual])
    with pytest.raises(BayesianOptimizationError, match="planning_input_invalid"):
        score_ordered_selection(changed, [actual])
