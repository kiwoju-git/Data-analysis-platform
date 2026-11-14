"""The same actual setting survives safe numeric and mixed mixture GP states."""

from copy import deepcopy

import pytest
from test_bo_mixed_planning import payload as mixed_payload
from test_bo_mixture_design import design

from app.statistics.bo_mixture_planning import (
    evaluate_mixture_planning_points,
    fit_mixture_planning_model,
    mixture_profile_path,
    restore_mixture_planning_model,
)


def payload(mixed=False):
    from dataclasses import replace

    d = design()
    if not mixed:
        d = replace(d, process_factors=())
    base = mixed_payload()
    points = d.sample(seed=8, count=8, max_attempts=100)["points"]
    return {
        "design_domain": d.payload(),
        "objective": base["objective"],
        "fit": {
            k: base[k]
            for k in (
                "response_models",
                "observation_policy",
                "xi_desirability",
                "search",
                "fit_policy",
                "max_moment_evaluations",
            )
        },
        "observations": [
            {
                "trial_id": str(i),
                "actual_coordinates": p,
                "response_values": {"yield": 3 * p["a"] - p["b"] + i * 0.001},
            }
            for i, p in enumerate(points)
        ],
    }


@pytest.mark.parametrize("mixed", [False, True])
def test_fit_restore_profile_and_explicit_evaluation_agree(mixed):
    body = payload(mixed)
    snapshot = fit_mixture_planning_model(body)
    assert snapshot["schema_version"] == 3
    assert snapshot["inner_model_kind"] == ("mixed" if mixed else "numeric")
    model = restore_mixture_planning_model(deepcopy(snapshot))
    holds = body["observations"][3]["actual_coordinates"]
    trace = mixture_profile_path(snapshot, holds, "a", count=5)
    point = trace["points"][2]
    before = evaluate_mixture_planning_points(snapshot, [point])[0]
    after = evaluate_mixture_planning_points(deepcopy(snapshot), [point])[0]
    assert before == after
    endpoint = {**holds, "a": 0.1, "b": 0.8, "fixed": 0.1}
    boundary = evaluate_mixture_planning_points(snapshot, [endpoint])[0]
    assert boundary["actual_coordinates"] == endpoint
    assert boundary["encoded_coordinates"]["b"] == (0.8 - 0.1) / model.design.mixture.denominator
    assert before["encoded_coordinates"] == dict(
        zip(model.design.keys, model.design.canonical(point)[1], strict=True)
    )
    assert before["distance_policy"] == "mixture_actual_bound_width_process_v1"
    assert (
        before["response_predictions"][0]["predictive_standard_deviation_raw"]
        >= before["response_predictions"][0]["latent_standard_deviation_raw"]
    )
    with pytest.raises(ValueError):
        evaluate_mixture_planning_points(snapshot, [{**point, "b": point["b"] + 0.01}])
    bad = deepcopy(snapshot)
    bad["design_domain"]["mixture"]["effective_coding"] = "upper"
    with pytest.raises(Exception, match="bayesian_mixture_planning_snapshot_invalid"):
        restore_mixture_planning_model(bad)


def test_numeric_affine_boundary_is_a_real_training_observation_not_only_a_query():
    from app.statistics.bo_surrogate_snapshot import load_bo_surrogate

    body = payload(False)
    boundary = {"a": 0.1, "b": 0.8, "fixed": 0.1}
    body["observations"][0]["actual_coordinates"] = boundary
    snapshot = fit_mixture_planning_model(body)
    state = snapshot["response_states"]["yield"]
    assert state["schema_version"] == 2
    assert state["training"]["x_normalized"][0][1] == 1.0000000000000002
    restored = restore_mixture_planning_model(deepcopy(snapshot))
    assert restored.models["yield"].x_train[0][1] == 1.0000000000000002
    before = evaluate_mixture_planning_points(snapshot, [boundary])[0]
    assert before == evaluate_mixture_planning_points(deepcopy(snapshot), [boundary])[0]
    assert before["actual_coordinates"] == boundary
    with pytest.raises(Exception, match="bayesian_surrogate_snapshot_invalid"):
        load_bo_surrogate(state)
    old = deepcopy(state)
    old.update(schema_version=1, policy="bo_numeric_surrogate_state_v1")
    del old["factor_domains"]
    with pytest.raises(Exception, match="bayesian_surrogate_snapshot_invalid"):
        load_bo_surrogate(old)
