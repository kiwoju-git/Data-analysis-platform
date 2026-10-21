"""Independent joint-payoff reference and bounded, actual V2 sequential runs."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from statistics import median
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import ndtr

from app.statistics.bo_acquisition import BoAcquisitionContext
from app.statistics.bo_batch_acquisition import BoBatchAcquisition
from app.statistics.bo_recommendation_core import calculate_noise_aware_batch

POLICY = "greedy_mc_joint_latent_improvement_v2"
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "bo_noise_policy_reference.json").read_text(
        encoding="utf-8"
    )
)


class _DeclaredPosterior:
    def __init__(self, spec: dict) -> None:
        self.x_train = np.array([[0.0], [1.0]])
        self.means = np.asarray(spec["means"], dtype=float)
        self.covariance = np.asarray(spec["covariance"], dtype=float)

    def predict(self, x, *, joint=False):
        indices = np.asarray(x)[:, 0].astype(int)
        cov = self.covariance[np.ix_(indices, indices)]
        return SimpleNamespace(
            mean_scaled=self.means[indices],
            latent_variance_scaled=np.diag(cov),
            predictive_variance_scaled=np.diag(cov) + 0.3,
            latent_covariance_scaled=cov if joint else None,
        )

    def latent_cross_covariance(self, x, z):
        a, b = np.asarray(x)[:, 0].astype(int), np.asarray(z)[:, 0].astype(int)
        return self.covariance[np.ix_(a, b)]


def _joint_payoff(samples: np.ndarray, goal: str, spec: dict) -> np.ndarray:
    selected, candidate = samples.T
    if goal == "maximize":
        threshold = spec["directional_incumbent"] + spec["xi"]
        return np.maximum(candidate - np.maximum(threshold, selected), 0)
    radius = np.minimum(spec["target_distance"] - spec["xi"], abs(selected - spec["target"]))
    return np.maximum(radius - abs(candidate - spec["target"]), 0)


def _independent_joint_mc(goal: str, spec: dict) -> tuple[float, float]:
    rng = np.random.default_rng(spec["reference_seed"])
    lower = np.linalg.cholesky(np.asarray(spec["covariance"]))
    total = total_squared = 0.0
    count = spec["reference_sample_count"]
    for start in range(0, count, 16384):
        samples = (
            np.asarray(spec["means"])
            + rng.standard_normal((min(16384, count - start), 2)) @ lower.T
        )
        values = _joint_payoff(samples, goal, spec)
        total += float(values.sum())
        total_squared += float(values @ values)
    mean = total / count
    variance = (total_squared - count * mean**2) / (count - 1)
    return mean, math.sqrt(variance / count)


def _quadrature_reference(goal: str, spec: dict) -> float:
    mu_s, mu_x = spec["means"]
    v_s, cross = spec["covariance"][0]
    conditional_sd = math.sqrt(spec["covariance"][1][1] - cross**2 / v_s)

    def integrand(z: float) -> float:
        selected = mu_s + math.sqrt(v_s) * z
        mean = mu_x + cross / v_s * (selected - mu_s)
        if goal == "maximize":
            threshold = max(spec["directional_incumbent"] + spec["xi"], selected)
            standardized = (mean - threshold) / conditional_sd
            gain = (mean - threshold) * ndtr(standardized) + conditional_sd * math.exp(
                -0.5 * standardized**2
            ) / math.sqrt(2 * math.pi)
        else:
            radius = min(spec["target_distance"] - spec["xi"], abs(selected - spec["target"]))
            target = spec["target"]

            def payoff_density(value: float) -> float:
                return (
                    (radius - abs(value - target))
                    * math.exp(-0.5 * ((value - mean) / conditional_sd) ** 2)
                    / (conditional_sd * math.sqrt(2 * math.pi))
                )

            gain = (
                quad(payoff_density, target - radius, target, epsabs=1e-12)[0]
                + quad(payoff_density, target, target + radius, epsabs=1e-12)[0]
            )
        return gain * math.exp(-0.5 * z**2) / math.sqrt(2 * math.pi)

    # Normal mass outside +/-10 is below 2e-23; no production acquisition is used.
    return quad(integrand, -10, 10, epsabs=1e-11, limit=200)[0]


@pytest.mark.parametrize("goal", ["maximize", "match_target"])
def test_mc_sample_stability_against_independent_joint_reference(goal: str) -> None:
    spec = FIXTURE["mc"]
    reference, reference_se = _independent_joint_mc(goal, spec)
    exact = _quadrature_reference(goal, spec)
    assert abs(reference - exact) <= spec["maximum_reference_standard_errors"] * reference_se
    model = _DeclaredPosterior(spec)
    context = BoAcquisitionContext(
        goal,
        spec["xi"],
        spec["target_distance"] if goal == "match_target" else spec["directional_incumbent"],
        spec["target"] if goal == "match_target" else None,
    )
    evidence = []
    errors_by_count = []
    for count in spec["sample_counts"]:
        estimates = np.asarray(
            [
                BoBatchAcquisition(
                    model, context, [[0.0]], sample_count=count, root_seed=seed, step=1
                )
                .score([[1.0]])
                .scores_scaled[0]
                for seed in spec["root_seeds"]
            ]
        )
        errors = estimates - reference
        errors_by_count.append(errors)
        evidence.append(
            {
                "samples": count,
                "rmse": float(np.sqrt(np.mean(errors**2))),
                "bias": float(errors.mean()),
                "maximum_absolute_error": float(abs(errors).max()),
            }
        )
    assert evidence[-1]["rmse"] <= spec["maximum_rms_ratio_256_to_16"] * evidence[0]["rmse"]
    assert abs(evidence[-1]["bias"]) <= 3 * evidence[-1]["rmse"] / math.sqrt(
        len(spec["root_seeds"])
    )
    print(
        json.dumps(
            {
                "stage": "joint_mc_stability",
                "goal": goal,
                "reference": reference,
                "reference_standard_error": reference_se,
                "independent_quadrature": exact,
                "counts": evidence,
                "nonmonotone_seed_transitions": int(
                    np.sum(np.diff(np.abs(errors_by_count), axis=0) > 0)
                ),
            },
            sort_keys=True,
        )
    )


def _truth(d: float, x: float) -> float:
    return 2 - 4 * (x - 0.68) ** 2 - 0.2 * (d - 1) ** 2


def _oracle_regret(truths: list[float], goal: str, spec: dict) -> float:
    if goal == "match_target":
        return min(abs(value - spec["target"]) for value in truths)
    return spec["known_maximum"] - max(truths)


def test_declared_oracle_optimum_and_target_are_feasible() -> None:
    spec = FIXTURE["sequential"]
    assert _truth(1, 0.68) == spec["known_maximum"]
    assert 0.68 + 0.1 <= 0.95
    target_x = 0.68 - math.sqrt((spec["known_maximum"] - spec["target"]) / 4)
    assert 0 <= target_x <= 1 and target_x + 0.1 <= 0.95
    assert _truth(1, target_x) == pytest.approx(spec["target"], abs=1e-14)


def _request(points: list[list[float]], values: list[float], seed: int, goal: str) -> dict:
    spec = FIXTURE["sequential"]
    return {
        "schema_version": 2,
        "factors": [
            {
                "factor_id": "d",
                "low": 0.0,
                "high": 2.0,
                "domain_kind": "discrete_numeric",
                "step": 1.0,
            },
            {"factor_id": "x", "low": 0.0, "high": 1.0},
        ],
        "constraints": [
            {
                "constraint_id": "limit",
                "name": "Synthetic limit",
                "terms": [
                    {"factor_id": "d", "coefficient": 0.1},
                    {"factor_id": "x", "coefficient": 1.0},
                ],
                "relation": "less_than_or_equal",
                "bound": 0.95,
            }
        ],
        "observations": [
            {
                "trial_id": f"synthetic-{i}",
                "actual_coordinates": {"d": d, "x": x},
                "normalized_coordinates": {"d": d / 2, "x": x},
                "objective_value": value,
            }
            for i, ((d, x), value) in enumerate(zip(points, values, strict=True))
        ],
        "excluded_normalized": [[d / 2, x] for d, x in points],
        "objective": {
            "goal_type": goal,
            "target_value": spec["target"] if goal == "match_target" else None,
        },
        "batch_size": spec["batch_size"],
        "acquisition": {
            "kind": "expected_target_improvement"
            if goal == "match_target"
            else "expected_improvement",
            "exploration_profile": "balanced",
            "xi_standardized": 0.01,
        },
        "surrogate": {"noise_mode": "estimate"},
        "observation_policy": {"mode": "retain_raw"},
        "batch_options": {
            "posterior_sample_count": spec["posterior_sample_count"],
            "min_batch_distance_normalized": 0.0,
        },
        "search": {**spec["search"], "random_seed": seed, "batch_policy": POLICY},
    }


@pytest.mark.parametrize("goal", ["maximize", "match_target"])
def test_v2_noisy_multistep_regret_constraints_and_reproducibility(goal: str) -> None:
    spec = FIXTURE["sequential"]
    evidence = []
    for seed in spec["root_seeds"]:
        points = copy.deepcopy(spec["initial_points"])
        rng = np.random.default_rng(seed + 91817)
        truths = [_truth(*point) for point in points]
        values = [value + spec["noise_sd"] * rng.standard_normal() for value in truths]

        initial = _oracle_regret(truths, goal, spec)
        initial_observed = (
            max(values)
            if goal == "maximize"
            else min(abs(value - spec["target"]) for value in values)
        )
        trace = []
        for step in range(spec["batch_count"]):
            request = _request(points, values, seed + 1009 * step, goal)
            before = copy.deepcopy(request)
            result = calculate_noise_aware_batch(request)
            replay = calculate_noise_aware_batch(copy.deepcopy(request))
            assert request == before
            assert result["items"] == replay["items"]
            assert result["schema_version"] == 2 and result["batch_policy"] == POLICY
            assert result["shared_model"]["noise"]["mode"] == "estimate"
            assert result["shared_model"]["raw_observation_count"] == len(points)
            for rank, item in enumerate(result["items"]):
                d, x = item["actual_coordinates"]["d"], item["actual_coordinates"]["x"]
                assert d in {0, 1, 2} and 0 <= x <= 1 and x + 0.1 * d <= 0.95 + 1e-10
                assert item["normalized_coordinates"] == {"d": d / 2, "x": x}
                assert all(
                    math.dist([d / 2, x], [old_d / 2, old_x]) > 1e-6 for old_d, old_x in points
                )
                assert item["planning"]["effective_sample_count"] == (64 if rank else 0)
                assert (
                    item["planning"]["representative_prediction_source"]
                    == "completed_observations_base_posterior"
                )
                assert (
                    item["predictive_standard_deviation"] >= item["latent_standard_deviation"] >= 0
                )
                truth = _truth(d, x)
                measured = truth + spec["noise_sd"] * rng.standard_normal()
                points.append([d, x])
                truths.append(truth)
                values.append(measured)
            trace.append(
                {
                    "step": step + 1,
                    "oracle_regret": _oracle_regret(truths, goal, spec),
                    "observations": len(points),
                    "acquisition_evaluations": result["search_budget"]["evaluations_consumed"],
                }
            )
        assert len(points) == spec["total_trial_budget"]
        assert any(value != truth for value, truth in zip(values, truths, strict=True))
        assert all(
            math.isfinite(row["oracle_regret"]) and row["oracle_regret"] >= 0 for row in trace
        )
        assert all(
            later <= earlier
            for earlier, later in zip(
                [initial, *[row["oracle_regret"] for row in trace[:-1]]],
                [row["oracle_regret"] for row in trace],
                strict=True,
            )
        )
        evidence.append(
            {
                "seed": seed,
                "initial_oracle_regret": initial,
                "final_oracle_regret": _oracle_regret(truths, goal, spec),
                "initial_observed_best_or_target_distance": initial_observed,
                "final_observed_best_or_target_distance": max(values)
                if goal == "maximize"
                else min(abs(value - spec["target"]) for value in values),
                "trace": trace,
            }
        )
    print(
        json.dumps(
            {
                "stage": "v2_noisy_multistep",
                "goal": goal,
                "runs": evidence,
                "replayed_every_batch": True,
                "constraint_violations": 0,
                "median_final_to_initial_oracle_regret_ratio": median(
                    row["final_oracle_regret"] for row in evidence
                )
                / median(row["initial_oracle_regret"] for row in evidence),
                "exploratory_half_regret_criterion_met": median(
                    row["final_oracle_regret"] for row in evidence
                )
                <= spec["exploratory_median_regret_ratio_threshold_not_a_release_gate"]
                * median(row["initial_oracle_regret"] for row in evidence),
            },
            sort_keys=True,
        )
    )
