from __future__ import annotations

import hashlib
import math
import time
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import beta, norm

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import DesirabilityGoal
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_desirability_batch_acquisition import (
    POLICY_VERSION,
    DesirabilityBatchAcquisition,
    batch_response_seed,
)
from app.statistics.bo_desirability_posterior import evaluate_surrogate_desirability
from app.statistics.bo_surrogate import BoSurrogatePolicy, fit_bo_surrogate


@pytest.fixture
def fitted():
    x = np.array([[0], [0.2], [0.4], [0.8], [1.0]])
    values = {"yield": np.array([10, 15, 16, 12, 9.0]), "cost": np.array([5, 4, 3, 2, 4.0])}
    settings = {
        "random_seed": 13,
        "jitter": 1e-8,
        "hyperparameter_restart_count": 0,
        "model_max_iterations": 50,
        "model_max_evaluations": 200,
    }
    models = {
        key: fit_bo_surrogate(
            x,
            y,
            BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.2),
            settings,
            deadline=time.perf_counter() + 30,
            optimize=False,
        )
        for key, y in values.items()
    }
    goals = (
        DesirabilityGoal("yield", "maximize", 8, 18, None, 1),
        DesirabilityGoal("cost", "minimize", None, 1, 6, 2),
    )
    return models, goals, x, values


def _plan(fitted, selected=None, **kwargs):
    models, goals, _, _ = fitted
    return DesirabilityBatchAcquisition(
        models, goals, 0.45, selected, xi=0.01, root_seed=73, sample_count=16, **kwargs
    )


def test_empty_selection_is_exact_existing_q1_and_does_not_sample(fitted, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("q1 must not draw MC samples")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    plan = _plan(fitted)
    result = plan.score([[0.3], [0.6]])
    for i, coordinate in enumerate((0.3, 0.6)):
        old = evaluate_surrogate_desirability(fitted[0], fitted[1], [coordinate])
        assert result.base_posteriors[i] == old
        assert (
            result.scores[i]
            == beta_expected_improvement(
                old.moments.mean, old.moments.variance, 0.45, xi=0.01
            ).value
        )
    np.testing.assert_array_equal(result.mc_standard_error, [0, 0])
    assert plan.metadata()["effective_sample_count"] == 0


def test_exact_selected_revisit_counts_only_real_moments_and_copies_proof(fitted):
    consumed = []
    plan = _plan(
        fitted, [[0.35]], max_moment_evaluations=35, consume_moments=lambda n: consumed.append(n)
    )
    first = plan.score([[0.6]], include_details=True)
    assert first.details is not None
    first.details["response_proofs"]["yield"]["selected_mean_scaled"][0] = 999
    again = plan.score([[0.6]], include_details=True)
    assert again.details["response_proofs"]["yield"]["selected_mean_scaled"][0] != 999
    result = plan.score([[0.35]])
    assert result.scores[0] == 0
    meta = plan.metadata()
    assert meta["candidate_evaluations"] == 3
    assert meta["exact_selected_evaluations"] == 1
    assert meta["moment_evaluations"] == sum(consumed) == 35


def _kernel(left, right):
    radius = np.sqrt(5) * np.abs(left[:, None, 0] - right[None, :, 0])
    return (1 + radius + radius**2 / 3) * np.exp(-radius)


def _posterior(x, y, q):
    scale, center = float(y.std(ddof=0)), float(y.mean())
    ky = _kernel(x, x) + np.eye(len(x)) * ((0.2 / scale) ** 2 + 1e-8)
    cross = _kernel(x, q)
    mean = cross.T @ np.linalg.solve(ky, (y - center) / scale) * scale + center
    covariance = (_kernel(q, q) - cross.T @ np.linalg.solve(ky, cross)) * scale**2
    return mean, covariance


def _payoff(values):
    yield_d = np.clip((values["yield"] - 8) / 10, 0, 1)
    cost_d = np.clip((6 - values["cost"]) / 5, 0, 1)
    return yield_d ** (1 / 3) * cost_d ** (2 / 3)


def _reference_moments(posteriors):
    first, second = 1.0, 1.0
    for key, power, low, high in (("yield", 1 / 3, 8, 18), ("cost", 2 / 3, 1, 6)):
        mean, sd = posteriors[key]

        def moment(exponent, mean=mean, sd=sd, low=low, high=high, key=key):
            def integrand(z):
                y = mean + sd * z
                d = (y - low) / (high - low) if key == "yield" else (high - y) / (high - low)
                return max(0, min(1, d)) ** exponent * norm.pdf(z)

            lo, hi = (low - mean) / sd, (high - mean) / sd
            tail = norm.sf(hi) if key == "yield" else norm.cdf(lo)
            return (
                quad(
                    integrand,
                    max(-12, lo),
                    min(12, hi),
                    epsabs=2e-12,
                    epsrel=2e-11,
                    points=[0] if lo < 0 < hi else None,
                )[0]
                + tail
            )

        first *= moment(power)
        second *= moment(2 * power)
    return first, second - first * first


def _reference_beta_ei(mean, variance, threshold):
    if threshold >= 1:
        return 0.0
    concentration = mean * (1 - mean) / variance - 1
    a, b = mean * concentration, (1 - mean) * concentration
    return quad(
        lambda d: (d - threshold) * beta.pdf(d, a, b),
        threshold,
        1,
        epsabs=1e-11,
        epsrel=1e-9,
        points=[mean] if threshold < mean else None,
    )[0]


def test_joint_conditioning_matches_independent_raw_cholesky_and_beta_integral(fitted):
    selected = np.array([[0.25], [0.85]])
    candidate = np.array([[0.6]])
    plan = _plan(fitted, selected)
    result = plan.score(candidate)
    _, _, x, observations = fitted
    raw_samples, conditional = {}, {}
    for key, y in observations.items():
        mean, covariance = _posterior(x, y, np.concatenate((selected, candidate)))
        seed = int.from_bytes(
            hashlib.sha256(
                f"{POLICY_VERSION}\0{73}\0latent_selected_responses\0{2}\0{key}".encode()
            ).digest()[:8],
            "big",
        )
        draws = np.random.default_rng(seed).standard_normal((16, 2))
        samples = mean[:2] + draws @ np.linalg.cholesky(covariance[:2, :2]).T
        raw_samples[key] = samples
        np.testing.assert_allclose(plan.selected_samples_raw[key], samples, atol=3e-12, rtol=0)
        cross = covariance[2, :2]
        cond_mean = mean[2] + cross @ np.linalg.solve(covariance[:2, :2], (samples - mean[:2]).T)
        cond_var = covariance[2, 2] - cross @ np.linalg.solve(covariance[:2, :2], cross)
        conditional[key] = (cond_mean, math.sqrt(cond_var))
        assert result.conditional_variance_raw[key][0] == pytest.approx(cond_var, abs=3e-12)
    thresholds = np.maximum(0.46, _payoff(raw_samples).max(axis=1))
    np.testing.assert_allclose(plan.thresholds, thresholds, atol=3e-13, rtol=0)
    scores = []
    for i, threshold in enumerate(thresholds):
        mu, var = _reference_moments(
            {key: (value[0][i], value[1]) for key, value in conditional.items()}
        )
        scores.append(_reference_beta_ei(mu, var, threshold))
    assert result.scores[0] == pytest.approx(np.mean(scores), abs=3e-10)
    assert result.mc_standard_error[0] == pytest.approx(np.std(scores, ddof=1) / 4, abs=3e-10)
    meta = plan.metadata()
    assert meta["representative_prediction_source"] == "completed_observations_base_posterior"
    assert meta["conditioned_on_selected_ranks"] == [1, 2]
    assert meta["moment_evaluations"] == 17


def test_common_draws_are_order_chunk_and_repeat_stable_and_do_not_refit(fitted, monkeypatch):
    models, goals, _, _ = fitted
    before = {
        key: (m.x_train.copy(), m.alpha.copy(), m.lower.copy(), m.kernel.theta.copy())
        for key, m in models.items()
    }

    def forbidden(*args, **kwargs):
        pytest.fail("planning cannot fit or update raw-data models")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    one = _plan(fitted, [[0.35]], chunk_size=1)
    many = DesirabilityBatchAcquisition(
        dict(reversed(list(models.items()))),
        goals[::-1],
        0.45,
        [[0.35]],
        xi=0.01,
        root_seed=73,
        sample_count=16,
        chunk_size=8,
    )
    points = [[0.1], [0.6], [0.9]]
    expected = one.score(points)
    np.testing.assert_allclose(many.score(points).scores, expected.scores, atol=1e-13, rtol=0)
    np.testing.assert_array_equal(one.score(points[::-1]).scores, expected.scores[::-1])
    for key, model in models.items():
        for actual, original in zip(
            (model.x_train, model.alpha, model.lower, model.kernel.theta), before[key], strict=True
        ):
            np.testing.assert_array_equal(actual, original)


def test_selected_location_has_zero_marginal_score_but_nonzero_base_uncertainty(fitted):
    result = _plan(fitted, [[0.35]]).score([[0.35]])
    assert result.scores[0] == 0
    assert result.base_posteriors[0].moments.variance > 0
    assert all(value[0] == 0 for value in result.conditional_variance_raw.values())


@pytest.mark.parametrize("baseline,xi", [(0.8, 0.3), (1.0, 0.0), (0.45, 1e100)])
def test_threshold_above_support_is_zero_without_double_xi(fitted, baseline, xi):
    plan = DesirabilityBatchAcquisition(
        fitted[0], fitted[1], baseline, [[0.35]], xi=xi, root_seed=73, sample_count=16
    )
    assert plan.score([[0.6]]).scores[0] == 0
    np.testing.assert_array_equal(plan.thresholds, np.full(16, baseline + xi))


def test_seed_uses_full_response_identity_not_python_hash_or_array_position():
    assert batch_response_seed(73, 2, "yield") == batch_response_seed(73, 2, "yield")
    assert (
        len(
            {
                batch_response_seed(73, step, response)
                for step in (1, 2)
                for response in ("X" * 121 + "A", "X" * 121 + "B")
            }
        )
        == 4
    )


def test_budget_and_deadline_callback_reject_without_partial_result(fitted):
    plan = _plan(fitted, [[0.35]], max_moment_evaluations=16)
    with pytest.raises(BayesianOptimizationError, match="budget"):
        plan.score([[0.6]])
    assert plan.metadata()["moment_evaluations"] == 0

    def timeout():
        raise TimeoutError("synthetic deadline")

    with pytest.raises(TimeoutError, match="synthetic deadline"):
        _plan(fitted, [[0.35]], check_budget=timeout)


@pytest.mark.parametrize(
    "patch",
    [
        {"sample_count": True},
        {"sample_count": 15},
        {"sample_count": 257},
        {"root_seed": -1},
        {"root_seed": "1"},
        {"chunk_size": 0},
        {"max_moment_evaluations": 0},
        {"incumbent": math.nan},
        {"xi": -1},
    ],
)
def test_invalid_options_rejected(fitted, patch):
    options = dict(root_seed=73, sample_count=16, incumbent=0.45, xi=0.01)
    options.update(patch)
    with pytest.raises(BayesianOptimizationError):
        DesirabilityBatchAcquisition(fitted[0], fitted[1], selected_x=[[0.35]], **options)


@pytest.mark.parametrize(
    "points",
    [[[True]], [[".3"]], [[math.inf]], [[-0.1]], [[1.1]], [[0.3, 0.4]], [], [[0.2], [True]]],
)
def test_bad_candidates_rejected(fitted, points):
    with pytest.raises(BayesianOptimizationError):
        _plan(fitted).score(points)


def test_direction_transformed_models_and_duplicate_selected_points_rejected(fitted):
    models = {**fitted[0], "cost": replace(fitted[0]["cost"], direction_multiplier=-1)}
    with pytest.raises(BayesianOptimizationError):
        DesirabilityBatchAcquisition(models, fitted[1], 0.45, root_seed=73)
    with pytest.raises(BayesianOptimizationError):
        _plan(fitted, [[0.3], [0.3]])


class _KnownPosterior:
    """Hand-specified latent Gaussian, independent of production GP solvers."""

    def __init__(self, mean, covariance, *, scale=1.0, center=0.0, noise=0.04):
        self.mean = np.array(mean, dtype=float)
        self.covariance = np.array(covariance, dtype=float)
        self.normalization_scale = scale
        self.normalization_mean = center
        self.direction_multiplier = 1
        self.covariance_roundoff_scale = 1.0
        self.x_train = np.zeros((1, 1))
        self.noise = noise
        self.calls = []

    def predict(self, x, *, joint=False):
        self.calls.append((len(x), joint))
        indices = (x[:, 0] * 2).astype(int)
        covariance = self.covariance[np.ix_(indices, indices)]
        return SimpleNamespace(
            mean_scaled=self.mean[indices],
            latent_variance_scaled=np.diag(covariance),
            predictive_variance_scaled=np.diag(covariance) + self.noise,
            latent_covariance_scaled=covariance if joint else None,
        )

    def latent_cross_covariance(self, left, right):
        return self.covariance[np.ix_((left[:, 0] * 2).astype(int), (right[:, 0] * 2).astype(int))]


def _known_plan(model, selected=((0.0,),), **kwargs):
    return DesirabilityBatchAcquisition(
        {"y": model},
        [DesirabilityGoal("y", "maximize", 0, 1, None)],
        kwargs.pop("incumbent", 0.2),
        selected,
        root_seed=19,
        sample_count=16,
        xi=kwargs.pop("xi", 0.3),
        **kwargs,
    )


def test_deterministic_hand_check_xi_once_and_noise_not_sampled():
    model = _KnownPosterior([0.4, 0.7, 0.8], np.zeros((3, 3)), noise=100.0)
    plan = _known_plan(model)
    result = plan.score([[0.5]])
    assert result.scores[0] == pytest.approx(0.2, abs=1e-16)
    assert result.mc_standard_error[0] == 0
    np.testing.assert_array_equal(plan.selected_samples_raw["y"], np.full((16, 1), 0.4))
    assert result.base_posteriors[0].responses[0].predictive_standard_deviation_raw == 10
    assert result.conditional_variance_raw["y"][0] == 0
    assert plan.metadata()["selected_covariance"]["y"]["rank"] == 0


def test_exact_rank_deficient_joint_keeps_correlated_draws_without_noise():
    # Two selected coordinates are different but the latent variables coincide.
    model = _KnownPosterior(
        [0.4, 0.5, 0.6], [[0.04, 0.04, 0.01], [0.04, 0.04, 0.01], [0.01, 0.01, 0.09]]
    )
    plan = _known_plan(model, [[0], [0.5]], xi=0.0)
    samples = plan.selected_samples_raw["y"]
    np.testing.assert_allclose(samples[:, 1] - samples[:, 0], 0.1, atol=1e-16, rtol=0)
    result = plan.score([[1]])
    assert result.conditional_variance_raw["y"][0] == pytest.approx(0.0875, abs=1e-15)
    assert plan.metadata()["selected_covariance"]["y"]["rank"] == 1
    assert plan.metadata()["selected_covariance"]["y"]["negative_eigenvalue_adjustment_scaled"] == 0


@pytest.mark.parametrize(
    "covariance,code",
    [
        ([[1e-16, 0, 0], [0, 0.1, 0], [0, 0, 0.1]], "precision_unsupported"),
        ([[-1e-5, 0, 0], [0, 0.1, 0], [0, 0, 0.1]], "covariance_invalid"),
        ([[0.1, 0.2, 0], [0.1, 0.1, 0], [0, 0, 0.1]], "covariance_invalid"),
        ([[0.1, 0.2, 0], [0.2, 0.1, 0], [0, 0, 0.1]], "covariance_invalid"),
    ],
)
def test_material_or_ambiguous_selected_covariance_is_not_hidden(covariance, code):
    with pytest.raises(BayesianOptimizationError, match=code):
        _known_plan(_KnownPosterior([0.4, 0.5, 0.6], covariance), [[0], [0.5]])


def test_tiny_negative_selected_eigenvalue_adjustment_is_explicit_and_not_noise():
    # Predictor variances are valid; a roundoff-size negative selected direction
    # is supplied only in the joint covariance by this deliberately corrupt probe.
    model = _KnownPosterior([0.4, 0.5, 0.6], [[-1e-16, 0, 0], [0, 0.1, 0], [0, 0, 0.1]], scale=3.0)
    plan = _known_plan(model)
    meta = plan.metadata()
    assert meta["selected_covariance"]["y"]["negative_eigenvalue_adjustment_scaled"] == 1e-16
    assert meta["selected_covariance"]["y"]["negative_eigenvalue_adjustment_raw"] == 9e-16
    assert meta["covariance_adjustment_is_measurement_noise"] is False
    assert plan.score([[0.5]]).scores[0] >= 0


@pytest.mark.parametrize("cross", [1e-3, 0.5])
def test_inconsistent_cross_covariance_rejected(cross):
    model = _KnownPosterior([0.4, 0.5, 0.6], [[0, cross, 0], [cross, 0.1, 0], [0, 0, 0.1]])
    with pytest.raises(BayesianOptimizationError, match="covariance_invalid"):
        _known_plan(model).score([[0.5]])


def test_material_negative_schur_variance_rejected():
    model = _KnownPosterior([0.4, 0.5, 0.6], [[0.1, 0.2, 0], [0.2, 0.1, 0], [0, 0, 0.1]])
    with pytest.raises(BayesianOptimizationError, match="covariance_invalid"):
        _known_plan(model).score([[0.5]])


def test_quadrature_precision_failure_is_not_replaced_by_zero_or_other_acquisition(monkeypatch):
    def unsupported(*args, **kwargs):
        raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")

    monkeypatch.setattr(
        "app.statistics.bo_desirability_batch_acquisition.beta_expected_improvement", unsupported
    )
    model = _KnownPosterior([0.4, 0.5, 0.6], np.eye(3) * 0.1)
    with pytest.raises(BayesianOptimizationError, match="beta_precision_unsupported"):
        _known_plan(model).score([[0.5]])


def test_later_deadline_failure_does_not_return_partial_scores_and_samples_are_copies():
    checks = 0

    def deadline():
        nonlocal checks
        checks += 1
        if checks > 15:
            raise TimeoutError("synthetic ongoing deadline")

    model = _KnownPosterior([0.4, 0.5, 0.6], np.eye(3) * 0.1)
    plan = _known_plan(model, check_budget=deadline)
    samples, thresholds = plan.selected_samples_raw, plan.thresholds
    samples["y"][:] = 100
    thresholds[:] = 100
    assert np.max(plan.selected_samples_raw["y"]) < 100
    assert np.max(plan.thresholds) <= 1
    with pytest.raises(TimeoutError):
        plan.score([[0.5], [1.0]])


def test_seven_selected_directions_and_hard_input_limits(fitted):
    plan = _plan(fitted, [[0.1], [0.2], [0.3], [0.4], [0.5], [0.6], [0.7]])
    assert plan.metadata()["conditioned_on_selected_ranks"] == list(range(1, 8))
    with pytest.raises(BayesianOptimizationError):
        _plan(fitted, [[i / 10] for i in range(8)])
    with pytest.raises(BayesianOptimizationError):
        plan.score(np.ones((4097, 1)))


@pytest.mark.parametrize("scale", [1e200, 1e-200])
@pytest.mark.parametrize("selected", [None, [[0.0]]])
def test_unrepresentable_raw_variance_is_explicit_not_inf_or_zero(scale, selected):
    model = _KnownPosterior([0.4, 0.5, 0.6], np.eye(3) * 0.1, scale=scale)
    goals = [DesirabilityGoal("y", "maximize", 0.0, scale, None)]
    plan = DesirabilityBatchAcquisition(
        {"y": model}, goals, 0.2, selected, root_seed=19, sample_count=16
    )
    with pytest.raises(BayesianOptimizationError, match="raw_variance_precision_unsupported"):
        plan.score([[0.5]])


def test_zero_adjustment_metadata_does_not_square_large_normalization_scale():
    model = _KnownPosterior([0.4, 0.5, 0.6], np.eye(3) * 0.1, scale=1e200)
    assert (
        _known_plan(model).metadata()["selected_covariance"]["y"][
            "negative_eigenvalue_adjustment_raw"
        ]
        == 0
    )


def test_complex_joint_covariance_rejected_before_cast(monkeypatch):
    model = _KnownPosterior([0.4, 0.5, 0.6], np.eye(3) * 0.1)
    original = model.predict

    def complex_predict(x, *, joint=False):
        result = original(x, joint=joint)
        if joint:
            result.latent_covariance_scaled = result.latent_covariance_scaled.astype(complex) + 1j
        return result

    monkeypatch.setattr(model, "predict", complex_predict)
    with pytest.raises(BayesianOptimizationError, match="covariance_invalid"):
        _known_plan(model)


@pytest.mark.parametrize("selected", [None, [[0.0]]])
def test_positive_scaled_variance_cannot_underflow_to_raw_zero_sd(selected):
    model = _KnownPosterior([0.4, 0.5, 0.6], np.diag([0.1, 1e-300, 0.1]), scale=1e-200)
    plan = DesirabilityBatchAcquisition(
        {"y": model},
        [DesirabilityGoal("y", "maximize", 0, 1e-200, None)],
        0.2,
        selected,
        root_seed=19,
        sample_count=16,
    )
    with pytest.raises(BayesianOptimizationError, match="numeric_invalid"):
        plan.score([[0.5]])


@pytest.mark.parametrize("sample_count", [16, 64, 256])
def test_sample_budget_counts_all_conditional_integrals_and_reuses_draws(sample_count):
    model = _KnownPosterior([0.45, 0.65, 0.6], [[0.09, 0.045, 0], [0.045, 0.16, 0], [0, 0, 0.1]])
    plan = DesirabilityBatchAcquisition(
        {"y": model},
        [DesirabilityGoal("y", "maximize", 0, 1, None)],
        0.2,
        [[0]],
        root_seed=19,
        sample_count=sample_count,
        max_moment_evaluations=2 * (sample_count + 1),
    )
    first = plan.score([[0.5]])
    again = plan.score([[0.5]])
    np.testing.assert_array_equal(first.scores, again.scores)
    np.testing.assert_array_equal(first.mc_standard_error, again.mc_standard_error)
    meta = plan.metadata()
    assert meta["moment_evaluations"] == 2 * (sample_count + 1)
    assert meta["response_moment_evaluations"] == meta["moment_evaluations"]
    assert meta["integration_evaluations"] > meta["moment_evaluations"]
    assert meta["candidate_evaluations"] == 2
    assert model.calls == [(1, True), (1, False), (1, False)]
    with pytest.raises(BayesianOptimizationError, match="budget_exhausted"):
        plan.score([[1]])


def test_beta_policy_differs_from_exact_clipped_joint_gaussian_payoff():
    # This independently integrated fixture measures approximation error. It is
    # deliberately not a claim that matching moments gives exact joint EI.
    model = _KnownPosterior([0.45, 0.65, 0.6], [[0.09, 0.045, 0], [0.045, 0.16, 0], [0, 0, 0.1]])
    plan = _known_plan(model, xi=0.0)
    result = plan.score([[0.5]])
    conditional_sd = math.sqrt(0.16 - 0.045**2 / 0.09)

    def clipped_ei(mean, threshold):
        if threshold == 1:
            return 0.0
        low, high = (threshold - mean) / conditional_sd, (1 - mean) / conditional_sd
        return (
            (mean - threshold) * (norm.cdf(high) - norm.cdf(low))
            + conditional_sd * (norm.pdf(low) - norm.pdf(high))
            + (1 - threshold) * norm.sf(high)
        )

    sampled = plan.selected_samples_raw["y"][:, 0]
    exact_conditional = np.array(
        [
            clipped_ei(0.65 + 0.5 * (value - 0.45), max(0.2, min(1, max(0, value))))
            for value in sampled
        ]
    )
    # Same latent draws, so this difference is Beta approximation, not MC error.
    assert abs(result.scores[0] - float(exact_conditional.mean())) > 1e-5

    def integrand(z):
        selected = 0.45 + 0.3 * z
        return norm.pdf(z) * clipped_ei(
            0.65 + 0.5 * (selected - 0.45), max(0.2, min(1, max(0, selected)))
        )

    exact_joint = quad(
        integrand,
        -10,
        10,
        points=[(0.2 - 0.45) / 0.3, (1 - 0.45) / 0.3],
        epsabs=1e-11,
        epsrel=1e-11,
    )[0]

    # Independent survival-integral identity for nonnegative bounded improvement:
    # integral_b^1 P(f_selected < threshold, f_candidate > threshold) dthreshold.
    def survival(threshold):
        return quad(
            lambda z: norm.pdf(z) * norm.sf((threshold - 0.65 - 0.15 * z) / conditional_sd),
            -12,
            (threshold - 0.45) / 0.3,
            epsabs=1e-11,
            epsrel=1e-11,
        )[0]

    survival_reference = quad(survival, 0.2, 1, epsabs=1e-11, epsrel=1e-11)[0]
    assert exact_joint == pytest.approx(survival_reference, abs=1e-10)
    assert plan.metadata()["score_is_exact_joint_ei"] is False
