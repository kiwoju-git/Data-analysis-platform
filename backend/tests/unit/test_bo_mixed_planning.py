"""Synthetic mixed-domain fit/view/source contracts; no HTTP/storage claims."""

import json
import math
import time
from copy import deepcopy
from uuid import UUID

import numpy as np
import pytest

from app.api.v1.schemas.bo_mixed_planning import MixedPlanningCalculationRequest
from app.api.v1.schemas.bo_mixed_studies import mixed_factor_domains
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_mixed_planning import (
    _training_views,
    evaluate_mixed_planning_points,
    fit_mixed_planning_model,
    restore_mixed_planning_model,
    score_mixed_ordered_selection,
)
from app.statistics.bo_mixed_snapshot import dump_bo_mixed_surrogate, load_bo_mixed_surrogate
from app.statistics.bo_mixed_surrogate import fit_bo_mixed_surrogate
from app.statistics.bo_surrogate import BoSurrogatePolicy


def payload():
    category = {
        "factor_id": "material",
        "name": "Material",
        "unit": None,
        "domain_kind": "nominal",
        "levels": ["A", "B", "C"],
        "correlation_policy": "equal_positive_correlation_v1",
    }
    points = [
        (0.0, "A", 0.1),
        (0.2, "B", 0.7),
        (0.4, "C", 0.4),
        (0.6, "A", 0.8),
        (0.8, "B", 0.3),
        (1.0, "C", 0.9),
    ]
    return {
        "schema_version": 8,
        "factors": [
            {
                "factor_id": "x",
                "name": "Setting",
                "unit": None,
                "low": 0.0,
                "high": 1.0,
                "domain_kind": "continuous",
                "step": None,
                "display_decimals": None,
            },
            category,
        ],
        "constraints": [],
        "observations": [
            {
                "trial_id": str(UUID(int=index + 1)),
                "actual_coordinates": {"x": x, "material": level},
                "encoded_coordinates": {"x": x, "material": float(category["levels"].index(level))},
                "response_values": {"yield": y},
                "condition_key": None,
            }
            for index, (x, level, y) in enumerate(points)
        ],
        "excluded_encoded": [[x, float(category["levels"].index(level))] for x, level, _ in points],
        "objective": {
            "name": "Yield",
            "goal_type": "desirability",
            "observation_policy": "complete_response_vector",
            "curve_policy": "derringer_suich_linear_v1",
            "unit": None,
            "direction": None,
            "target_value": None,
            "target_tolerance": None,
            "responses": [
                {
                    "response_id": "yield",
                    "name": "Yield",
                    "unit": None,
                    "goal": "maximize",
                    "lower": -1.0,
                    "target": 2.0,
                    "upper": None,
                    "importance": 1.0,
                }
            ],
        },
        "response_models": [
            {
                "response_id": "yield",
                "kernel": {"kind": "exponential"},
                "surrogate": {
                    "noise_mode": "fixed",
                    "initial_noise_variance_scaled": 0.01,
                    "lower_noise_variance_scaled": 1e-6,
                    "upper_noise_variance_scaled": 1.0,
                    "fixed_noise_sd": 0.2,
                },
            }
        ],
        "observation_policy": {
            "mode": "retain_raw",
            "nearby_tolerances": None,
            "nearby_units": "normalized",
        },
        "xi_desirability": 0.01,
        "search": {
            "random_seed": 42,
            "candidate_count_per_step": 32,
            "local_start_count_per_step": 0,
            "max_iterations_per_step": 20,
            "max_evaluations_total": 256,
            "model_max_iterations": 60,
            "model_max_evaluations": 1000,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 60000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
        },
        "fit_policy": {"policy": "bounded_typed_factor_starts_v1", "deterministic_start_count": 1},
        "max_moment_evaluations": 4096,
    }


@pytest.fixture(scope="module")
def fitted():
    body = payload()
    return body, fit_mixed_planning_model(body)


def test_fit_save_restore_view_preserves_category_identity_and_source(fitted, monkeypatch):
    body, snapshot = fitted
    original = deepcopy((body, snapshot))
    assert snapshot["schema_version"] == 2
    assert snapshot["response_models"][0]["model"]["schema_version"] == 6
    assert snapshot["fit_evaluations"] <= body["search"]["model_max_evaluations"]
    assert snapshot["calculation_request"]["schema_version"] == 8
    points = [{"x": 0.35, "material": level} for level in ("A", "B", "C")]
    before = evaluate_mixed_planning_points(snapshot, points)

    def no_fit(*args, **kwargs):
        pytest.fail("restore and view must not refit")

    monkeypatch.setattr("app.statistics.bo_mixed_planning.fit_bo_mixed_surrogate", no_fit)
    restored = json.loads(json.dumps(snapshot, allow_nan=False))
    after = evaluate_mixed_planning_points(restored, points)
    assert after == before
    assert [row["actual_coordinates"]["material"] for row in after] == ["A", "B", "C"]
    assert [row["encoded_coordinates"]["material"] for row in after] == [0, 1, 2]
    assert all("normalized_coordinates" not in row for row in after)
    assert all(
        row["acquisition"]["kind"] == "desirability_beta_expected_improvement" for row in after
    )
    assert (body, snapshot) == original
    model = restore_mixed_planning_model(restored)
    for row in after:
        point = np.asarray(
            [[row["encoded_coordinates"]["x"], row["encoded_coordinates"]["material"]]]
        )
        prediction = model.models["yield"].predict(point)
        metadata = snapshot["response_models"][0]["model"]
        response = row["response_predictions"][0]
        assert response["mean_raw"] == pytest.approx(
            prediction.mean_scaled[0] * metadata["normalization"]["scale"]
            + metadata["normalization"]["mean"],
            rel=1e-13,
        )
        assert response["predictive_standard_deviation_raw"] ** 2 - response[
            "latent_standard_deviation_raw"
        ] ** 2 == pytest.approx(0.2**2, rel=1e-12)


def test_incumbent_only_compares_completed_positions(fitted):
    body, snapshot = fitted
    incumbent = snapshot["incumbent"]
    source = {row["trial_id"]: row for row in body["observations"]}
    assert incumbent["latent_incumbent_trial_id"] in source
    assert (
        incumbent["latent_incumbent_encoded_coordinates"]
        == source[incumbent["latent_incumbent_trial_id"]]["encoded_coordinates"]
    )
    assert incumbent["latent_incumbent_value"] == max(
        row["moments"]["mean"] for row in incumbent["training_posterior_desirabilities"]
    )
    assert snapshot["observation_view"]["raw_observation_count"] == 6


@pytest.mark.parametrize(
    "mutation",
    ["response", "condition", "encoding", "levels", "policy", "metadata", "incumbent", "budget"],
)
def test_restore_rejects_broken_source_or_receipt(fitted, mutation):
    _, saved = fitted
    snapshot = deepcopy(saved)
    if mutation == "response":
        snapshot["calculation_request"]["observations"][0]["response_values"]["yield"] += 0.1
    elif mutation == "condition":
        snapshot["calculation_request"]["observations"][0]["condition_key"] = "other"
    elif mutation == "encoding":
        snapshot["calculation_request"]["observations"][0]["encoded_coordinates"]["material"] = 1.0
    elif mutation == "levels":
        snapshot["calculation_request"]["factors"][1]["levels"] = ["B", "A", "C"]
    elif mutation == "policy":
        snapshot["calculation_request"]["response_models"][0]["surrogate"]["fixed_noise_sd"] = 0.3
    elif mutation == "metadata":
        snapshot["response_models"][0]["model"]["normalization"]["mean"] += 0.1
    elif mutation == "incumbent":
        snapshot["incumbent"]["latent_incumbent_value"] *= 0.9
    else:
        snapshot["fit_evaluations"] += 1
    with pytest.raises(ValueError, match="mixed_planning_snapshot_invalid"):
        restore_mixed_planning_model(snapshot)


def test_observed_and_current_excluded_points_remain_ineligible(fitted):
    body, snapshot = fitted
    point = body["observations"][0]["actual_coordinates"]
    rows = evaluate_mixed_planning_points(
        snapshot,
        [point, {"x": 0.35, "material": "C"}],
        eligibility_excluded_encoded=[[0.35, 2.0]],
        compute_acquisition=False,
    )
    assert all(row["eligible"] is False and row["novel"] is False for row in rows)
    assert all(row["acquisition"] is None for row in rows)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown",
        "numeric_category",
        "missing_response",
        "duplicate_trial",
        "nearby",
        "few_unique",
        "bad_encoded",
    ],
)
def test_strict_request_boundaries(mutation):
    body = payload()
    if mutation == "unknown":
        body["observations"][0]["actual_coordinates"]["material"] = "unknown"
    elif mutation == "numeric_category":
        body["observations"][0]["actual_coordinates"]["material"] = 0.0
    elif mutation == "missing_response":
        body["observations"][0]["response_values"] = {}
    elif mutation == "duplicate_trial":
        body["observations"][1]["trial_id"] = body["observations"][0]["trial_id"]
    elif mutation == "nearby":
        body["observation_policy"]["mode"] = "nearby_diagnostics"
    elif mutation == "bad_encoded":
        body["observations"][2]["encoded_coordinates"]["material"] = math.nextafter(2.0, math.inf)
    else:
        body["observations"] = body["observations"][:2]
    with pytest.raises(ValueError):
        MixedPlanningCalculationRequest.model_validate(body)


def test_budget_fails_before_fitting_and_view_never_returns_partial(fitted, monkeypatch):
    body = payload()
    body["max_moment_evaluations"] = 1
    monkeypatch.setattr(
        "app.statistics.bo_mixed_planning.fit_bo_mixed_surrogate",
        lambda *args, **kwargs: pytest.fail("known insufficient budget must fail before fit"),
    )
    with pytest.raises(ValueError, match="budget_exhausted"):
        fit_mixed_planning_model(body)
    with pytest.raises(ValueError, match="budget_exhausted"):
        evaluate_mixed_planning_points(
            fitted[1], [{"x": 0.3, "material": "A"}], max_moment_evaluations=6
        )
    with pytest.raises(ValueError, match="time_budget_exhausted"):
        evaluate_mixed_planning_points(
            fitted[1], [{"x": 0.3, "material": "A"}], absolute_deadline=time.perf_counter() - 1
        )


def repeat_payload(mode):
    body = payload()
    body["factors"] = [body["factors"][1]]
    rows = [
        ("A", "batch-one", 0.1),
        ("A", "batch-one", 0.3),
        ("A", "batch-two", 0.4),
        ("A", "batch-two", 0.5),
        ("A", "batch-two", 0.9),
        ("B", None, 0.7),
        ("C", None, 0.2),
    ]
    body["observations"] = [
        {
            "trial_id": str(UUID(int=i + 1)),
            "actual_coordinates": {"material": level},
            "encoded_coordinates": {"material": float("ABC".index(level))},
            "response_values": {"yield": value},
            "condition_key": condition,
        }
        for i, (level, condition, value) in enumerate(rows)
    ]
    body["excluded_encoded"] = [[float("ABC".index(level))] for level, _, _ in rows]
    body["observation_policy"]["mode"] = mode
    return body


def test_raw_and_compressed_condition_groups_match_independent_cholesky():
    models = []
    requests = []
    for mode in ("retain_raw", "exact_replicates"):
        request = MixedPlanningCalculationRequest.model_validate(repeat_payload(mode))
        requests.append(request)
        views, shared = _training_views(request)
        view = views["yield"]
        assert shared["unique_condition_count"] == 4 and shared["unique_coordinate_count"] == 3
        assert [row["n"] for row in shared["groups"]] == [2, 3, 1, 1]
        model = fit_bo_mixed_surrogate(
            view.training_x,
            view.targets_scaled,
            mixed_factor_domains(request.factors),
            BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.2),
            request.search.model_dump(),
            deadline=time.perf_counter() + 60,
            normalization_mean=view.mean,
            normalization_scale=view.scale,
            group_counts=view.counts,
            within_ss_scaled=view.within_ss_scaled,
            raw_observation_count=7,
            kernel_spec=BoKernelSpec("exponential"),
            optimize=False,
        )
        restored = load_bo_mixed_surrogate(
            dump_bo_mixed_surrogate(model),
            expected_factor_domains=mixed_factor_domains(request.factors),
            expected_training_targets_scaled=view.targets_scaled,
            expected_within_ss_scaled=view.within_ss_scaled,
        )
        models.append(restored)
    query = np.array([[0.0], [1.0], [2.0]])
    raw, compressed = (model.predict(query, joint=True) for model in models)
    np.testing.assert_allclose(raw.mean_scaled, compressed.mean_scaled, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(
        raw.latent_covariance_scaled,
        compressed.latent_covariance_scaled,
        rtol=1e-12,
        atol=1e-12,
    )
    assert models[0].log_marginal_likelihood == pytest.approx(
        models[1].log_marginal_likelihood, rel=1e-12
    )
    x = models[0].x_train[:, 0]
    y = models[0].training_targets_scaled
    noise = (0.2 / models[0].normalization_scale) ** 2
    # Independent equal-correlation kernel, amplitude=1 and mismatch theta=1.
    covariance = np.exp(-(x[:, None] != x[None, :]).astype(float)) + np.eye(len(x)) * (noise + 1e-8)
    cross = np.exp(-(query[:, 0, None] != x[None, :]).astype(float))
    lower = np.linalg.cholesky(covariance)
    alpha = np.linalg.solve(lower.T, np.linalg.solve(lower, y))
    expected_mean = cross @ alpha
    solved = np.linalg.solve(lower, cross.T)
    expected_covariance = (
        np.exp(-(query[:, 0, None] != query[:, 0][None, :]).astype(float)) - solved.T @ solved
    )
    np.testing.assert_allclose(compressed.mean_scaled, expected_mean, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(
        compressed.latent_covariance_scaled, expected_covariance, rtol=1e-12, atol=1e-12
    )


def test_exact_repeat_snapshot_keeps_condition_membership_and_rejects_regrouping():
    body = repeat_payload("exact_replicates")
    snapshot = fit_mixed_planning_model(body)
    restored = restore_mixed_planning_model(snapshot)
    assert restored.models["yield"].group_counts == (2, 3, 1, 1)
    assert [row[0] for row in restored.models["yield"].x_train.tolist()] == [0, 0, 1, 2]
    changed = deepcopy(snapshot)
    changed["calculation_request"]["observations"][2]["condition_key"] = "batch-one"
    with pytest.raises(ValueError, match="mixed_planning_snapshot_invalid"):
        restore_mixed_planning_model(changed)


def test_mixed_q1_is_exact_analytic_view_without_refit(fitted, monkeypatch):
    snapshot = fitted[1]
    points = [{"x": 0.35, "material": "C"}]
    view = evaluate_mixed_planning_points(snapshot, points)[0]
    monkeypatch.setattr(
        "app.statistics.bo_mixed_planning.fit_bo_mixed_surrogate",
        lambda *args, **kwargs: pytest.fail("selection must not refit"),
    )
    selected = score_mixed_ordered_selection(snapshot, points, sample_count=16)
    item = selected["items"][0]
    assert selected["schema_version"] == 2 and selected["model_refit"] is False
    assert selected["moment_evaluations"] == 7
    assert item["encoded_coordinates"]["material"] == 2
    assert item["planning"]["score"] == view["acquisition"]["value"]
    assert item["acquisition"] == view["acquisition"]
    assert item["response_predictions"] == view["response_predictions"]
    assert item["planning"]["sampler"]["effective_sample_count"] == 0
    assert item["planning"]["sampler"]["coordinate_encoding"] == (
        "numeric_normalized_category_index_v1"
    )
    assert "normalized_coordinates" not in item


def test_mixed_q2_conditional_covariance_and_mc_against_independent_reference(fitted):
    from scipy.integrate import quad
    from scipy.special import betainc
    from scipy.stats import norm

    body, snapshot = fitted
    points = [{"x": 0.35, "material": "C"}, {"x": 0.45, "material": "C"}]
    selected = score_mixed_ordered_selection(snapshot, points, sample_count=16)
    assert selected == score_mixed_ordered_selection(snapshot, points, sample_count=16)
    assert selected["moment_evaluations"] == 24  # Six incumbent nodes + 1 + 1 + 16.
    base = evaluate_mixed_planning_points(snapshot, points)
    for item, view in zip(selected["items"], base, strict=True):
        assert item["response_predictions"] == view["response_predictions"]
        assert item["acquisition"] == view["acquisition"]
    plan = selected["items"][1]["planning"]
    assert selected["items"][1]["nearest_selected_distance"] == pytest.approx(0.1)
    model = snapshot["response_models"][0]["model"]
    signal = model["signal_kernel"]
    amplitude = signal["numeric_signal"]["amplitude"]
    length = signal["numeric_signal"]["length_scales"][0]
    theta = signal["parameters"][0]
    x = np.array(
        [[r["encoded_coordinates"][k] for k in ("x", "material")] for r in body["observations"]]
    )
    query = np.array([[0.35, 2.0], [0.45, 2.0]])
    mean, scale = model["normalization"]["mean"], model["normalization"]["scale"]
    y = (np.array([r["response_values"]["yield"] for r in body["observations"]]) - mean) / scale

    def kernel(left, right):
        return amplitude * np.exp(
            -np.abs(left[:, None, 0] - right[None, :, 0]) / length
            - theta * (left[:, None, 1] != right[None, :, 1])
        )

    lower = np.linalg.cholesky(kernel(x, x) + np.eye(len(x)) * ((0.2 / scale) ** 2 + 1e-8))
    cross = kernel(query, x)
    solved = np.linalg.solve(lower, cross.T)
    covariance = kernel(query, query) - solved.T @ solved
    mu = cross @ np.linalg.solve(lower.T, np.linalg.solve(lower, y))
    conditional_variance = covariance[1, 1] - covariance[1, 0] ** 2 / covariance[0, 0]
    assert plan["conditional_variance_raw"]["yield"] == pytest.approx(
        conditional_variance * scale**2, rel=1e-11, abs=1e-13
    )
    proof = plan["proof"]["response_proofs"]["yield"]
    np.testing.assert_allclose(proof["cross_covariance_scaled"], [covariance[1, 0]], rtol=1e-11)
    seed = int(plan["sampler"]["response_sample_seeds"]["yield"])
    sampled = mu[0] + np.sqrt(covariance[0, 0]) * np.random.default_rng(seed).standard_normal(16)
    thresholds = np.maximum(
        snapshot["incumbent"]["latent_incumbent_value"] + body["xi_desirability"],
        np.clip((sampled * scale + mean + 1) / 3, 0, 1),
    )
    np.testing.assert_allclose(plan["proof"]["thresholds"], thresholds, rtol=1e-12, atol=1e-14)
    expected_scores = []
    for index, draw in enumerate(sampled):
        conditional_mean = (
            mu[1] + covariance[1, 0] / covariance[0, 0] * (draw - mu[0])
        ) * scale + mean
        sd = np.sqrt(conditional_variance) * scale
        moments = [
            quad(
                lambda z, mu=conditional_mean, sigma=sd, p=power: float(
                    np.clip((mu + sigma * z + 1) / 3, 0, 1)
                )
                ** p
                * norm.pdf(z),
                -12,
                12,
                points=[
                    z
                    for z in ((-1 - conditional_mean) / sd, (2 - conditional_mean) / sd)
                    if -12 < z < 12
                ],
                epsabs=1e-12,
                epsrel=1e-12,
            )[0]
            for power in (1, 2)
        ]
        mean_d, second = moments
        variance_d = second - mean_d**2
        concentration = mean_d * (1 - mean_d) / variance_d - 1
        a, b = mean_d * concentration, (1 - mean_d) * concentration
        threshold = thresholds[index]
        expected_scores.append(
            0.0
            if threshold >= 1
            else mean_d * (1 - betainc(a + 1, b, threshold))
            - threshold * (1 - betainc(a, b, threshold))
        )
        saved = plan["proof"]["sample_moments"][index]
        assert saved["mean"] == pytest.approx(mean_d, abs=2e-12)
        assert saved["variance"] == pytest.approx(variance_d, abs=2e-12)
    assert plan["score"] == pytest.approx(np.mean(expected_scores), rel=1e-8, abs=2e-11)


@pytest.mark.parametrize(
    "options",
    [
        {"max_moment_evaluations": 23},
        {"min_batch_distance": 0.11},
        {"sample_count": 15},
        {"absolute_deadline": 0.0},
    ],
)
def test_mixed_manual_selection_rejects_incomplete_or_invalid_work(fitted, options):
    points = [{"x": 0.35, "material": "C"}, {"x": 0.45, "material": "C"}]
    with pytest.raises(ValueError):
        score_mixed_ordered_selection(fitted[1], points, **{"sample_count": 16, **options})


def test_mixed_manual_selection_uses_current_novelty_and_original_order(fitted):
    points = [{"x": 0.35, "material": "C"}, {"x": 0.45, "material": "A"}]
    first = score_mixed_ordered_selection(fitted[1], points, sample_count=16)
    reverse = score_mixed_ordered_selection(fitted[1], points[::-1], sample_count=16)
    assert first["items"][0]["row_id"] == reverse["items"][1]["row_id"]
    assert first["items"][1]["planning"]["sampler"]["conditioned_on_selected_ranks"] == [1]
    assert first["items"][1]["nearest_selected_distance"] == pytest.approx(math.hypot(0.1, 1))
    with pytest.raises(ValueError, match="selection_ineligible"):
        score_mixed_ordered_selection(
            fitted[1], points, sample_count=16, eligibility_excluded_encoded=[[0.35, 2.0]]
        )
