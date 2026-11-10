"""No-fit space filling and exact saved-model augmentation integration."""

from copy import deepcopy
from uuid import uuid4

import pytest

from app.statistics.bo_augmentation import CONFIRM, MAXPRO, REFINE, REFINE_V2
from app.statistics.bo_augmentation_view import build_augmentation_view


def arguments():
    return {
        "factors": [{"factor_id": "x", "low": 0.0, "high": 1.0}],
        "constraints": [],
        "points": [{"x": x} for x in (0.1, 0.3, 0.7, 0.9)],
        "existing_coordinates": [[0.0], [1.0]],
        "source": {
            "model_snapshot_id": None,
            "model_snapshot_sha256": None,
            "candidate_revision_id": str(uuid4()),
            "candidate_revision_sha256": "a" * 64,
            "history_sha256": "b" * 64,
        },
        "policy": MAXPRO,
        "batch_size": 2,
        "snapshot": None,
        "duplicate_tolerance": 1e-6,
        "min_batch_distance_normalized": 0.0,
        "max_evaluations": 1000,
        "max_moment_evaluations": 4096,
        "time_budget_ms": 60000,
    }


def test_model_free_space_filling_never_loads_or_fits_surrogate(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("model-free policy must not load or fit a surrogate")

    monkeypatch.setattr("app.statistics.bo_planning_model.restore_planning_model", forbidden)
    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    body = arguments()
    original = deepcopy(body)
    result = build_augmentation_view(**body)
    assert result["prediction_evaluations"] == 0
    assert len(result["selected_rows"]) == 2
    assert {row["actual_coordinates"]["x"] for row in result["selected_rows"]} == {0.3, 0.7}
    assert body == original
    assert result["model_refit"] is False


@pytest.mark.parametrize("policy,snapshot", [(REFINE, None), (MAXPRO, {})])
def test_policy_model_presence_is_explicit(policy, snapshot):
    body = arguments() | {"policy": policy, "snapshot": snapshot}
    with pytest.raises(ValueError, match="model_policy_mismatch"):
        build_augmentation_view(**body)


def test_model_based_source_mismatch_rejected_before_prediction(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("mismatched source must not evaluate")

    monkeypatch.setattr("app.statistics.bo_planning_model.evaluate_planning_points", forbidden)
    body = arguments() | {"policy": REFINE, "snapshot": {"calculation_request": {"factors": []}}}
    with pytest.raises(ValueError, match="source_mismatch"):
        build_augmentation_view(**body)


@pytest.mark.parametrize("value", [True, 0, 65537, float("inf")])
def test_invalid_moment_budget_cannot_enter_receipt(value):
    with pytest.raises(ValueError, match="input_invalid"):
        build_augmentation_view(**(arguments() | {"max_moment_evaluations": value}))


def test_minimum_budget_is_not_rejected_for_submillisecond_dispatch(monkeypatch):
    ticks = iter([10.0, *([10.0001] * 1000)])
    monkeypatch.setattr("time.perf_counter", lambda: next(ticks))
    result = build_augmentation_view(**(arguments() | {"time_budget_ms": 1000}))
    assert len(result["selected_rows"]) == 2
    assert result["augmentation"]["time_budget_ms"] == 1000


def test_original_deadline_expires_without_a_fresh_stage_budget(monkeypatch):
    ticks = iter([10.0, *([11.01] * 1000)])
    monkeypatch.setattr("time.perf_counter", lambda: next(ticks))
    with pytest.raises(ValueError, match="time_budget_exhausted"):
        build_augmentation_view(**(arguments() | {"time_budget_ms": 1000}))


def test_candidate_validation_observes_deadline_before_all_rows(monkeypatch):
    import app.statistics.bo_candidate_points as candidates

    seen = []
    original = candidates._evaluations

    def evaluations(*args):
        seen.append(1)
        return original(*args)

    monkeypatch.setattr(candidates, "_evaluations", evaluations)
    monkeypatch.setattr("time.perf_counter", lambda: 10.0 if not seen else 12.0)
    with pytest.raises(ValueError, match="time_budget_exhausted"):
        build_augmentation_view(**(arguments() | {"time_budget_ms": 1000}))
    assert len(seen) == 1


def test_confirm_bypasses_beta_precision_limit_without_fabricating_ei(monkeypatch):
    from types import SimpleNamespace

    import app.statistics.bo_planning_model as planning
    from app.statistics.bo_desirability import DesirabilityMoments
    from app.statistics.bo_desirability_posterior import SurrogateDesirability

    factor = SimpleNamespace(factor_id="x", model_dump=lambda: arguments()["factors"][0])
    model = SimpleNamespace(
        request=SimpleNamespace(
            factors=[factor],
            constraints=[],
            search=SimpleNamespace(duplicate_tolerance=1e-6),
            xi_desirability=0.01,
        ),
        models={},
        goals=[],
        incumbent={"latent_incumbent_value": 0.4},
    )
    monkeypatch.setattr(planning, "restore_planning_model", lambda *args, **kwargs: model)
    monkeypatch.setattr(planning, "_eligibility_coordinates", lambda *args: [[0.0], [1.0]])
    monkeypatch.setattr(
        planning,
        "evaluate_surrogate_desirability",
        lambda *args: SurrogateDesirability(
            DesirabilityMoments(0.5, 0.25 + 1e-12, 1e-12, 0, 0, 0), ()
        ),
    )
    body = arguments()
    body.update(
        policy=CONFIRM,
        snapshot={
            "calculation_request": {
                "factors": body["factors"],
                "constraints": [],
                "search": {"duplicate_tolerance": 1e-6},
            },
            "incumbent": {"latent_incumbent_value": 0.4},
        },
    )
    body["source"].update(model_snapshot_id=str(uuid4()), model_snapshot_sha256="c" * 64)
    result = build_augmentation_view(**body)
    assert all(row["acquisition"] is None for row in result["selected_rows"])
    assert result["augmentation"]["steps"][0]["score"] == 0.5
    assert result["augmentation"]["steps"][1]["score"] == pytest.approx(1e-6)
    with pytest.raises(ValueError, match="beta_precision_unsupported"):
        build_augmentation_view(**(body | {"policy": REFINE}))


@pytest.mark.parametrize("importance_scale", [1.0, 1e-300, 1e300])
def test_refine_v2_adapter_uses_saved_scales_and_goal_importances(monkeypatch, importance_scale):
    from test_bo_augmentation import _multimodel_rows

    captured = []

    def evaluate(snapshot, points, **kwargs):
        captured.append(kwargs)
        return _multimodel_rows()

    monkeypatch.setattr("app.statistics.bo_planning_model.evaluate_planning_points", evaluate)
    body = arguments()
    body.update(
        policy=REFINE_V2,
        batch_size=5,
        snapshot={
            "calculation_request": {
                "factors": body["factors"],
                "constraints": [],
                "search": {"duplicate_tolerance": 1e-6},
                "objective": {
                    "responses": [
                        {"response_id": "a", "importance": importance_scale},
                        {"response_id": "b", "importance": 3 * importance_scale},
                    ]
                },
            },
            "incumbent": {"latent_incumbent_value": 0.4},
            "response_models": [
                {"response_id": "b", "model": {"normalization": {"scale": 10.0}}},
                {"response_id": "a", "model": {"normalization": {"scale": 2.0}}},
            ],
        },
    )
    body["source"].update(model_snapshot_id=str(uuid4()), model_snapshot_sha256="c" * 64)
    result = build_augmentation_view(**body)
    assert captured[0]["compute_acquisition"] is True
    assert result["augmentation"]["steps"][2]["score"] == pytest.approx(7.75**0.5)
    assert result["augmentation"]["response_uncertainty"]["context"] == [
        {"response_id": "a", "normalization_scale": 2.0, "normalized_importance": 0.25},
        {"response_id": "b", "normalization_scale": 10.0, "normalized_importance": 0.75},
    ]
