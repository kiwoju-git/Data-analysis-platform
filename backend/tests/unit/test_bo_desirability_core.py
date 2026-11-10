from __future__ import annotations

import copy
import json
import math
from dataclasses import replace
from uuid import UUID

import numpy as np
import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability_core import calculate_desirability_recommendation


def payload():
    points = [0.0, 0.25, 0.5, 0.75, 1.0]
    yields = [10.0, 15.0, 17.0, 14.0, 9.0]
    costs = [5.0, 4.0, 3.0, 2.0, 4.0]
    return {
        "schema_version": 4,
        "factors": [{"factor_id": "x", "low": 0.0, "high": 1.0}],
        "constraints": [],
        "observations": [
            {
                "trial_id": str(UUID(int=i + 1)),
                "actual_coordinates": {"x": x},
                "normalized_coordinates": {"x": x},
                "response_values": {"yield": yields[i], "cost": costs[i]},
            }
            for i, x in enumerate(points)
        ],
        "excluded_normalized": [[x] for x in points],
        "objective": {
            "responses": [
                {
                    "response_id": "yield",
                    "name": "Yield",
                    "unit": "g",
                    "goal": "maximize",
                    "lower": 8.0,
                    "target": 18.0,
                    "upper": None,
                    "importance": 1.0,
                },
                {
                    "response_id": "cost",
                    "name": "Cost",
                    "unit": None,
                    "goal": "minimize",
                    "lower": None,
                    "target": 1.0,
                    "upper": 6.0,
                    "importance": 2.0,
                },
            ]
        },
        "response_models": [
            {
                "response_id": key,
                "kernel": {"kind": "matern_5_2"},
                "surrogate": {"noise_mode": "fixed", "fixed_noise_sd": 0.2},
            }
            for key in ("yield", "cost")
        ],
        "observation_policy": {"mode": "retain_raw"},
        "xi_desirability": 0.01,
        "search": {
            "random_seed": 13,
            "candidate_count_per_step": 32,
            "local_start_count_per_step": 0,
            "max_iterations_per_step": 15,
            "max_evaluations_total": 128,
            "model_max_iterations": 50,
            "model_max_evaluations": 200,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 30000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
        },
    }


def test_real_models_q1_preserve_raw_vectors_and_noise_separation():
    request = payload()
    before = copy.deepcopy(request)
    result = calculate_desirability_recommendation(request)
    assert request == before
    assert result["schema_version"] == 4
    assert result["shared_model"]["schema_version"] == 5
    assert result["batch_size"] == 1
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["actual_coordinates"] == item["normalized_coordinates"]
    assert item["nearest_existing_distance"] >= request["search"]["duplicate_tolerance"]
    assert {r["response_id"] for r in item["response_predictions"]} == {"yield", "cost"}
    for response in item["response_predictions"]:
        assert (
            response["predictive_standard_deviation_raw"] ** 2
            - response["latent_standard_deviation_raw"] ** 2
        ) == pytest.approx(0.04, abs=1e-12)
    for response in result["shared_model"]["response_models"]:
        assert response["model"]["normalization"]["direction_multiplier"] == 1
        assert response["model"]["schema_version"] == 4
    incumbent = result["incumbent"]
    assert incumbent["latent_incumbent_value"] == max(
        row["moments"]["mean"] for row in incumbent["training_posterior_desirabilities"]
    )
    assert incumbent["best_observed_desirability"] == max(
        row["value"] for row in incumbent["observed_trial_desirabilities"]
    )
    assert result["search_budget"]["response_fit_count"] == 2
    assert result["search_budget"]["integrand_evaluations"] > 0
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "extra",
        "nan",
        "bool",
        "duplicate_trial",
        "duplicate_response",
        "model_mismatch",
        "q2",
    ],
)
def test_invalid_complete_vector_contract_rejected_before_any_fit(monkeypatch, defect):
    request = payload()
    if defect == "missing":
        del request["observations"][0]["response_values"]["cost"]
    elif defect == "extra":
        request["observations"][0]["response_values"]["extra"] = 1.0
    elif defect in {"nan", "bool"}:
        request["observations"][0]["response_values"]["cost"] = np.nan if defect == "nan" else True
    elif defect == "duplicate_trial":
        request["observations"][0]["trial_id"] = request["observations"][1]["trial_id"]
    elif defect == "duplicate_response":
        request["objective"]["responses"][1]["response_id"] = "yield"
    elif defect == "model_mismatch":
        request["response_models"][1]["response_id"] = "unknown"
    else:
        request["batch_size"] = 2

    def forbidden(*args, **kwargs):
        pytest.fail("invalid request must not fit a response model")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    with pytest.raises(BayesianOptimizationError):
        calculate_desirability_recommendation(request)


def test_exact_replicates_share_members_but_not_response_statistics():
    request = payload()
    repeated = copy.deepcopy(request["observations"][1])
    repeated.update(trial_id=str(UUID(int=99)), response_values={"yield": 13.0, "cost": 8.0})
    request["observations"].append(repeated)
    request["observation_policy"]["mode"] = "exact_replicates"
    result = calculate_desirability_recommendation(request)
    view = result["observation_view"]
    assert (view["raw_observation_count"], view["effective_training_count"]) == (6, 5)
    assert view["groups"][1]["member_trial_ids"] == [str(UUID(int=2)), str(UUID(int=99))]
    responses = {r["response_id"]: r for r in result["shared_model"]["response_models"]}
    yield_group = responses["yield"]["observation_view"]["groups"][1]
    cost_group = responses["cost"]["observation_view"]["groups"][1]
    assert (yield_group["mean"], yield_group["within_ss"]) == (14.0, 2.0)
    assert (cost_group["mean"], cost_group["within_ss"]) == (6.0, 8.0)
    assert yield_group["member_indices"] == cost_group["member_indices"]
    assert len(request["observations"]) == 6


def test_reproducible_recommendation_ignores_mapping_insertion_order():
    first_request = payload()
    second_request = copy.deepcopy(first_request)
    second_request["response_models"].reverse()
    for row in second_request["observations"]:
        row["response_values"] = dict(reversed(list(row["response_values"].items())))
    first = calculate_desirability_recommendation(first_request)
    second = calculate_desirability_recommendation(second_request)
    assert first["items"] == second["items"]
    assert first["incumbent"] == second["incumbent"]


def test_concentrated_beta_is_an_explicit_error_not_a_deterministic_fallback(monkeypatch):
    def unsupported(*args, **kwargs):
        raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")

    monkeypatch.setattr(
        "app.statistics.bo_desirability_acquisition.beta_expected_improvement", unsupported
    )
    request = payload()
    before = copy.deepcopy(request)
    with pytest.raises(BayesianOptimizationError, match="precision_unsupported"):
        calculate_desirability_recommendation(request)
    assert request == before


def test_discrete_selected_score_matches_independent_cholesky_payoff_and_beta_integrals():
    from scipy.integrate import quad
    from scipy.stats import beta, norm

    request = payload()
    request["factors"][0].update(high=8.0, domain_kind="discrete_numeric", step=1.0)
    for row in request["observations"]:
        row["actual_coordinates"]["x"] *= 8
    result = calculate_desirability_recommendation(request)
    models = result["shared_model"]["response_models"]
    training_x = np.array([r["normalized_coordinates"]["x"] for r in request["observations"]])
    prepared = []
    for i, response in enumerate(models):
        model = response["model"]
        y = np.array(
            [r["response_values"][response["response_id"]] for r in request["observations"]]
        )
        average, scale = float(y.mean()), float(y.std(ddof=0))
        amplitude = model["signal_kernel"]["amplitude"]
        length = model["signal_kernel"]["length_scales"][0]

        def covariance(left, right, a=amplitude, length_scale=length):
            radius = math.sqrt(5) * np.abs(left[:, None] - right[None, :]) / length_scale
            return a * (1 + radius + radius**2 / 3) * np.exp(-radius)

        matrix = covariance(training_x, training_x) + np.eye(len(y)) * (
            (0.2 / scale) ** 2 + request["search"]["jitter"]
        )
        prepared.append((i, average, scale, amplitude, covariance, matrix, (y - average) / scale))

    def independent_moments(x):
        first = second = 1.0
        for i, average, scale, amplitude, covariance, matrix, scaled_y in prepared:
            cross = covariance(training_x, np.array([x]))
            mean = float((cross.T @ np.linalg.solve(matrix, scaled_y)).item()) * scale + average
            variance = (
                float((amplitude - cross.T @ np.linalg.solve(matrix, cross)).item()) * scale**2
            )
            sd = math.sqrt(variance)
            low, high, weight = (8.0, 18.0, 1 / 3) if i == 0 else (1.0, 6.0, 2 / 3)

            def moment(power, low=low, high=high, i=i, mean=mean, sd=sd):
                def integral(y):
                    payoff = (y - low) / (high - low) if i == 0 else (high - y) / (high - low)
                    return payoff**power * norm.pdf((y - mean) / sd) / sd

                tail = norm.sf((high - mean) / sd) if i == 0 else norm.cdf((low - mean) / sd)
                return quad(integral, low, high, epsabs=1e-12, epsrel=2e-10)[0] + tail

            first *= moment(weight)
            second *= moment(2 * weight)
        return first, second - first * first

    incumbent = max(independent_moments(x)[0] for x in training_x)
    threshold = incumbent + request["xi_desirability"]
    candidates = [1.0, 3.0, 5.0, 7.0]
    scores = {}
    for actual in candidates:
        mean, variance = independent_moments(actual / 8)
        concentration = mean * (1 - mean) / variance - 1
        a, b = mean * concentration, (1 - mean) * concentration
        scores[actual] = quad(
            lambda d, a=a, b=b: (d - threshold) * beta.pdf(d, a, b),
            threshold,
            1,
            epsabs=1e-13,
            epsrel=1e-10,
        )[0]
    expected = max(candidates, key=lambda x: scores[x])
    selected = result["items"][0]
    assert selected["actual_coordinates"]["x"] == expected
    assert selected["acquisition"]["value"] == pytest.approx(scores[expected], abs=3e-11)
    assert result["incumbent"]["latent_incumbent_value"] == pytest.approx(incumbent, abs=3e-11)
    assert result["search_budget"]["searches"][0]["enumerated_all_discrete_assignments"] is True


def test_raw_response_fits_are_once_each_and_share_global_evaluation_allowance(monkeypatch):
    from app.statistics.bo_surrogate import fit_bo_surrogate

    request = payload()
    request["search"]["model_max_evaluations"] = 6
    calls = []

    def fixed_fit(x, y, policy, search, **kwargs):
        calls.append(
            (np.array(y), search["model_max_evaluations"], kwargs["deadline"], kwargs["goal_type"])
        )
        fitted = fit_bo_surrogate(x, y, policy, search, optimize=False, **kwargs)
        return replace(fitted, optimizer={**fitted.optimizer, "evaluations": 3})

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", fixed_fit)
    result = calculate_desirability_recommendation(request)
    assert len(calls) == 2
    np.testing.assert_array_equal(calls[0][0], [10.0, 15.0, 17.0, 14.0, 9.0])
    np.testing.assert_array_equal(calls[1][0], [5.0, 4.0, 3.0, 2.0, 4.0])
    assert [call[1] for call in calls] == [6, 3]
    assert calls[0][2] == calls[1][2]
    assert all(call[3] == "maximize" for call in calls)
    assert result["search_budget"]["model_evaluations_consumed"] == 6


def test_shared_fit_budget_does_not_restart_for_the_next_response(monkeypatch):
    from app.statistics.bo_surrogate import fit_bo_surrogate

    request = payload()
    request["search"]["model_max_evaluations"] = 4
    calls = []

    def full_budget_fit(x, y, policy, search, **kwargs):
        calls.append(search["model_max_evaluations"])
        fitted = fit_bo_surrogate(x, y, policy, search, optimize=False, **kwargs)
        return replace(fitted, optimizer={**fitted.optimizer, "evaluations": 4})

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", full_budget_fit)
    with pytest.raises(BayesianOptimizationError, match="budget_exhausted"):
        calculate_desirability_recommendation(request)
    assert calls == [4]


def test_search_budget_exhaustion_does_not_return_a_partial_candidate(monkeypatch):
    request = payload()

    def exceed(**kwargs):
        kwargs["consume"](request["search"]["max_evaluations_total"] + 1)
        pytest.fail("exhausted search must not continue")

    monkeypatch.setattr("app.statistics.bo_mixed_search.search_mixed_acquisition", exceed)
    with pytest.raises(BayesianOptimizationError, match="budget_exhausted"):
        calculate_desirability_recommendation(request)


def test_global_deadline_applies_before_the_first_fit(monkeypatch):
    import app.statistics.bo_desirability_core as core

    times = iter([0.0, 31.0])
    monkeypatch.setattr(core.time, "perf_counter", lambda: next(times))

    def forbidden(*args, **kwargs):
        pytest.fail("expired request must not fit a model")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    with pytest.raises(BayesianOptimizationError, match="time_budget_exhausted"):
        calculate_desirability_recommendation(payload())


def test_nearby_diagnostics_do_not_merge_raw_response_training():
    request = payload()
    first = calculate_desirability_recommendation(request)
    request["observation_policy"] = {
        "mode": "nearby_diagnostics",
        "nearby_units": "normalized",
        "nearby_tolerances": {"x": 0.3},
    }
    second = calculate_desirability_recommendation(request)
    assert first["items"] == second["items"]
    assert second["observation_view"]["effective_training_count"] == 5
    for record in second["shared_model"]["response_models"]:
        assert record["observation_view"]["nearby_diagnostics"]["changes_training_data"] is False
        assert record["observation_view"]["nearby_diagnostics"]["groups"]


def test_unlisted_observed_points_are_still_excluded_from_recommendation():
    request = payload()
    request["excluded_normalized"] = []
    result = calculate_desirability_recommendation(request)
    selected = result["items"][0]
    assert selected["nearest_existing_distance"] >= request["search"]["duplicate_tolerance"]
    assert selected["actual_coordinates"] not in [
        r["actual_coordinates"] for r in request["observations"]
    ]


def test_four_responses_keep_distinct_kernels_and_mixed_goal_policies():
    request = payload()
    request["search"]["model_max_evaluations"] = 1000
    request["objective"]["responses"].extend(
        [
            {
                "response_id": "strength",
                "name": "Strength",
                "unit": "MPa",
                "goal": "maximize",
                "lower": 0.0,
                "target": 10.0,
                "upper": None,
                "importance": 3.0,
            },
            {
                "response_id": "quality",
                "name": "Quality",
                "unit": None,
                "goal": "match_target",
                "lower": 0.0,
                "target": 5.0,
                "upper": 10.0,
                "importance": 4.0,
            },
        ]
    )
    for i, row in enumerate(request["observations"]):
        row["response_values"].update(
            strength=[3.0, 4.0, 6.0, 8.0, 5.0][i], quality=[7.0, 6.0, 5.0, 4.0, 6.0][i]
        )
    kernels = dict(
        zip(
            ("yield", "cost", "strength", "quality"),
            ("matern_5_2", "matern_3_2", "gaussian", "exponential"),
            strict=True,
        )
    )
    request["response_models"] = [
        {
            "response_id": response_id,
            "kernel": {"kind": kernel},
            "surrogate": {"noise_mode": "fixed", "fixed_noise_sd": 0.2},
        }
        for response_id, kernel in kernels.items()
    ]
    before = copy.deepcopy(request)
    result = calculate_desirability_recommendation(request)
    assert request == before
    assert result["objective"] == request["objective"]
    assert result["search_budget"]["response_fit_count"] == 4
    assert result["search_budget"]["model_evaluations_consumed"] <= 1000
    assert result["shared_model"]["normalized_importance"] == [
        {"response_id": response_id, "weight": weight}
        for response_id, weight in zip(kernels, (0.1, 0.2, 0.3, 0.4), strict=True)
    ]
    for record in result["shared_model"]["response_models"]:
        assert record["model"]["signal_kernel"]["family"] == kernels[record["response_id"]]
        assert record["model"]["normalization"]["direction_multiplier"] == 1
        assert record["model"]["raw_observation_count"] == 5
    item = result["items"][0]
    assert [r["response_id"] for r in item["response_predictions"]] == list(kernels)
    for prediction in item["response_predictions"]:
        assert (
            prediction["predictive_standard_deviation_raw"] ** 2
            - prediction["latent_standard_deviation_raw"] ** 2
        ) == pytest.approx(0.04, abs=2e-12)
    assert item["acquisition"]["kind"] == "desirability_beta_expected_improvement"
    json.dumps(result, allow_nan=False)


def test_raw_unit_transform_of_response_noise_and_preferences_preserves_q1_result():
    original = payload()
    transformed = copy.deepcopy(original)
    transforms = {"yield": (4.0, 64.0), "cost": (0.25, -16.0)}
    for row in transformed["observations"]:
        for response_id, (scale, offset) in transforms.items():
            row["response_values"][response_id] = (
                scale * row["response_values"][response_id] + offset
            )
    for goal in transformed["objective"]["responses"]:
        scale, offset = transforms[goal["response_id"]]
        goal["unit"] = "transformed synthetic unit"
        for field in ("lower", "target", "upper"):
            if goal[field] is not None:
                goal[field] = scale * goal[field] + offset
    for model in transformed["response_models"]:
        scale, _ = transforms[model["response_id"]]
        model["surrogate"]["fixed_noise_sd"] *= scale
    first = calculate_desirability_recommendation(original)
    second = calculate_desirability_recommendation(transformed)
    a, b = first["items"][0], second["items"][0]
    assert a["actual_coordinates"] == b["actual_coordinates"]
    assert a["normalized_coordinates"] == b["normalized_coordinates"]
    assert a["acquisition"]["xi_desirability"] == b["acquisition"]["xi_desirability"] == 0.01
    for name in ("mean", "second_moment", "variance"):
        assert a["desirability_moments"][name] == pytest.approx(
            b["desirability_moments"][name], rel=2e-8, abs=2e-11
        )
    assert a["acquisition"]["value"] == pytest.approx(
        b["acquisition"]["value"], rel=2e-8, abs=2e-11
    )
    for name in ("best_observed_desirability", "latent_incumbent_value"):
        assert first["incumbent"][name] == pytest.approx(second["incumbent"][name], abs=2e-10)
    for raw, changed in zip(a["response_predictions"], b["response_predictions"], strict=True):
        scale, offset = transforms[raw["response_id"]]
        assert changed["mean_raw"] == pytest.approx(scale * raw["mean_raw"] + offset, abs=2e-8)
        for name in ("latent_standard_deviation_raw", "predictive_standard_deviation_raw"):
            assert changed[name] == pytest.approx(scale * raw[name], rel=2e-8, abs=2e-10)
