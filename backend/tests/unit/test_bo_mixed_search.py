from __future__ import annotations

import time

import numpy as np
import pytest
from scipy.optimize import OptimizeResult

from app.statistics import bo_mixed_search
from app.statistics.bayesian_optimization import BayesianOptimizationError, _SearchBudget
from app.statistics.bo_mixed_search import search_mixed_acquisition


def _factors(*, discrete: bool = True) -> list[dict]:
    factors = [{"factor_id": "x", "low": 10.0, "high": 20.0}]
    if discrete:
        factors.insert(
            0,
            {
                "factor_id": "d",
                "low": 0.0,
                "high": 2.0,
                "domain_kind": "discrete_numeric",
                "step": 1.0,
            },
        )
    return factors


def _toy(points: np.ndarray) -> np.ndarray:
    d = points[:, 0] * 2
    x = points[:, 1]
    optima = np.asarray([0.19, 0.37, 0.83])
    assert np.all(d == np.floor(d)), "SLSQP must not move discrete coordinates"
    return 4 + d - (x - optima[d.astype(int)]) ** 2


def test_mixed_search_refines_continuous_coordinates_at_exact_levels() -> None:
    calls: list[np.ndarray] = []

    def score(points: np.ndarray) -> np.ndarray:
        calls.extend(points.copy())
        return _toy(points)

    result = search_mixed_acquisition(
        factors=_factors(),
        constraints=[],
        score=score,
        seed=31,
        pool_size=32,
        local_start_count=3,
    )
    assert result.actual_coordinates["d"] == 2.0
    assert result.actual_coordinates["x"] == pytest.approx(18.3, abs=1e-5)
    assert result.acquisition == pytest.approx(6.0, abs=1e-10)
    assert result.metadata["local_starts"] == 3
    assert result.metadata["enumerated_all_discrete_assignments"] is True
    assert len(result.metadata["visited_discrete_assignments"]) == 3
    np.testing.assert_array_equal(calls[-1], result.normalized_coordinates)


def test_actual_linear_constraints_move_fixed_discrete_contribution() -> None:
    # 2*d + x <= 20 means d=2 requires normalized x <= .6, not .2 or 1.
    constraints = [
        {
            "constraint_id": "budget",
            "name": "Synthetic limit",
            "coefficients": {"d": 2.0, "x": 1.0},
            "relation": "less_than_or_equal",
            "bound": 20.0,
        }
    ]
    result = search_mixed_acquisition(
        factors=_factors(),
        constraints=constraints,
        score=_toy,
        seed=31,
        pool_size=64,
        local_start_count=3,
    )
    assert result.actual_coordinates["d"] == 2
    assert result.actual_coordinates["x"] == pytest.approx(16.0, abs=1e-6)
    assert result.acquisition == pytest.approx(6 - 0.23**2, abs=1e-8)
    assert 2 * result.actual_coordinates["d"] + result.actual_coordinates["x"] <= 20 + 1e-8


def test_all_discrete_small_space_is_exhaustive_without_slsqp() -> None:
    factors = [_factors()[0]]
    result = search_mixed_acquisition(
        factors=factors,
        constraints=[],
        score=lambda x: 2 - (2 * x[:, 0] - 1) ** 2,
        seed=7,
        pool_size=32,
        local_start_count=16,
    )
    assert result.actual_coordinates == {"d": 1.0}
    assert result.acquisition == 2
    assert result.metadata["local_starts"] == 0
    assert result.metadata["feasible_pool_size"] == 3
    assert result.metadata["termination_reason"] == "exhaustive_discrete_search"


def test_all_continuous_refines_and_reproduces_without_discrete_rounding() -> None:
    kwargs = dict(
        factors=_factors(discrete=False),
        constraints=[],
        score=lambda x: 1 - (x[:, 0] - 0.37123) ** 2,
        seed=47,
        pool_size=32,
        local_start_count=2,
    )
    first, second = search_mixed_acquisition(**kwargs), search_mixed_acquisition(**kwargs)
    assert first == second
    assert first.normalized_coordinates == pytest.approx([0.37123], abs=1e-6)
    assert first.actual_coordinates["x"] == pytest.approx(13.7123, abs=1e-5)
    assert first.metadata["space_kind"] == "continuous"


def test_large_discrete_space_uses_seeded_assignments_and_level_neighbors() -> None:
    factors = [dict(_factors()[0], high=1000.0), _factors()[1]]
    seen: list[np.ndarray] = []

    def score(x: np.ndarray) -> np.ndarray:
        seen.extend(x.copy())
        np.testing.assert_allclose(x[:, 0] * 1000, np.round(x[:, 0] * 1000), atol=1e-10)
        return 2 - (x[:, 0] - 0.371) ** 2 - (x[:, 1] - 0.283) ** 2

    result = search_mixed_acquisition(
        factors=factors,
        constraints=[],
        score=score,
        seed=89,
        pool_size=32,
        local_start_count=4,
    )
    assert result.metadata["enumerated_all_discrete_assignments"] is False
    assert result.metadata["neighbor_assignments_evaluated"] > 0
    assert result.metadata["local_starts"] <= 4
    assert result.actual_coordinates["d"] == int(result.actual_coordinates["d"])
    assert result.acquisition == pytest.approx(score(np.array([result.normalized_coordinates]))[0])


def test_novelty_and_selected_distance_are_separate_final_constraints() -> None:
    result = search_mixed_acquisition(
        factors=_factors(discrete=False),
        constraints=[],
        score=lambda x: 1 - (x[:, 0] - 0.5) ** 2,
        seed=3,
        pool_size=64,
        local_start_count=3,
        excluded_normalized=[[0.5]],
        selected_normalized=[[0.6]],
        duplicate_tolerance=0.001,
        min_batch_distance_normalized=0.2,
    )
    x = result.normalized_coordinates[0]
    assert abs(x - 0.5) > 0.001
    assert abs(x - 0.6) >= 0.2 - 1e-12
    assert result.metadata["nearest_selected_distance"] == pytest.approx(abs(x - 0.6))


def test_all_zero_scores_are_explicit_and_deterministic() -> None:
    kwargs = dict(
        factors=_factors(),
        constraints=[],
        score=lambda x: np.zeros(x.shape[0]),
        seed=13,
        pool_size=32,
        local_start_count=2,
    )
    first = search_mixed_acquisition(**kwargs)
    assert first == search_mixed_acquisition(**kwargs)
    assert first.acquisition == 0
    assert first.metadata["all_acquisitions_zero"] is True
    assert first.metadata["termination_reason"] == "acquisition_numerically_zero"


def test_global_budget_is_charged_and_exhaustion_not_partial_success() -> None:
    started = time.perf_counter()
    budget = _SearchBudget(started, started + 60, 5)

    def consume(count: int) -> None:
        nonlocal budget
        budget = budget.consume(count)

    with pytest.raises(BayesianOptimizationError, match="budget_exhausted"):
        search_mixed_acquisition(
            factors=_factors(),
            constraints=[],
            score=_toy,
            seed=31,
            pool_size=32,
            local_start_count=3,
            consume=consume,
        )


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_invalid_acquisition_is_not_silently_replaced(bad: float) -> None:
    with pytest.raises(BayesianOptimizationError, match="acquisition_invalid"):
        search_mixed_acquisition(
            factors=_factors(),
            constraints=[],
            score=lambda x: np.full(x.shape[0], bad),
            seed=31,
            pool_size=32,
            local_start_count=0,
        )


def test_no_feasible_candidate_has_stable_failure() -> None:
    with pytest.raises(BayesianOptimizationError, match="no_feasible_candidate"):
        search_mixed_acquisition(
            factors=_factors(discrete=False),
            constraints=[
                {
                    "constraint_id": "impossible",
                    "name": "Impossible",
                    "coefficients": {"x": 1.0},
                    "relation": "less_than_or_equal",
                    "bound": 0.0,
                }
            ],
            score=lambda x: np.ones(x.shape[0]),
            seed=1,
            pool_size=32,
            local_start_count=1,
        )


def test_local_solver_failure_retains_seed_and_does_not_trust_solver_fun(monkeypatch) -> None:
    monkeypatch.setattr(
        bo_mixed_search,
        "minimize",
        lambda *args, **kwargs: OptimizeResult(
            x=np.array([float("nan")]),
            fun=-1e12,
            success=False,
            status=9,
            nit=1,
        ),
    )
    result = search_mixed_acquisition(
        factors=_factors(discrete=False),
        constraints=[],
        score=lambda x: 1 - (x[:, 0] - 0.37) ** 2,
        seed=31,
        pool_size=32,
        local_start_count=2,
    )
    assert result.metadata["local_starts"] == 2
    assert result.metadata["local_successes"] == 0
    assert result.metadata["selected_from"] == "feasible_pool"
    assert result.metadata["termination_reason"] == "local_solver_incomplete_best_feasible_retained"
    assert result.acquisition == pytest.approx(1 - (result.normalized_coordinates[0] - 0.37) ** 2)


def test_local_point_score_is_recomputed_even_after_solver_success(monkeypatch) -> None:
    monkeypatch.setattr(
        bo_mixed_search,
        "minimize",
        lambda *args, **kwargs: OptimizeResult(
            x=np.array([0.37123]),
            fun=-1e12,
            success=True,
            status=0,
            nit=1,
        ),
    )
    result = search_mixed_acquisition(
        factors=_factors(discrete=False),
        constraints=[],
        score=lambda x: 1 - (x[:, 0] - 0.37123) ** 2,
        seed=31,
        pool_size=32,
        local_start_count=1,
    )
    assert result.acquisition == pytest.approx(1.0, abs=1e-14)
    assert result.actual_coordinates["x"] == pytest.approx(13.7123, abs=1e-12)
    assert result.metadata["selected_from"] == "local_refinement"


def test_charge_counts_all_scored_rows_with_bounded_chunks() -> None:
    charged = 0
    chunk_sizes: list[int] = []

    def consume(n: int) -> None:
        nonlocal charged
        charged += n

    def score(x: np.ndarray) -> np.ndarray:
        chunk_sizes.append(len(x))
        return _toy(x)

    result = search_mixed_acquisition(
        factors=_factors(),
        constraints=[],
        score=score,
        seed=31,
        pool_size=600,
        local_start_count=1,
        consume=consume,
    )
    assert max(chunk_sizes) <= 256
    assert sum(chunk_sizes) == charged == result.metadata["evaluations"]
    assert result.metadata["local_starts"] == 1


def test_time_budget_error_propagates_before_score() -> None:
    started = time.perf_counter()
    budget = _SearchBudget(started, started - 1, 1000)
    calls = 0

    def score(x: np.ndarray) -> np.ndarray:
        nonlocal calls
        calls += 1
        return np.ones(len(x))

    with pytest.raises(BayesianOptimizationError, match="time_budget_exhausted"):
        search_mixed_acquisition(
            factors=_factors(),
            constraints=[],
            score=score,
            seed=31,
            pool_size=32,
            local_start_count=1,
            consume=budget.consume,
        )
    assert calls == 0


def test_discrete_decimal_levels_and_greater_than_constraint_are_preserved() -> None:
    factors = [dict(_factors()[0], low=0.1, high=0.3, step=0.1), _factors()[1]]
    result = search_mixed_acquisition(
        factors=factors,
        constraints=[
            {
                "constraint_id": "floor",
                "name": "Floor",
                "coefficients": {"d": -10.0, "x": 1.0},
                "relation": "greater_than_or_equal",
                "bound": 15.0,
            }
        ],
        score=lambda x: 3 + x[:, 0] - x[:, 1] ** 2,
        seed=17,
        pool_size=64,
        local_start_count=3,
    )
    assert result.actual_coordinates["d"] == 0.3
    assert result.actual_coordinates["x"] == pytest.approx(18.0, abs=1e-6)
    assert result.acquisition == pytest.approx(4 - 0.8**2, abs=1e-8)


def test_all_discrete_enumeration_is_charged_even_when_larger_than_requested_pool() -> None:
    factors = [dict(_factors()[0], high=255)]
    result = search_mixed_acquisition(
        factors=factors,
        constraints=[],
        score=lambda x: x[:, 0],
        seed=1,
        pool_size=32,
        local_start_count=16,
    )
    assert result.actual_coordinates == {"d": 255.0}
    assert result.metadata["discrete_assignment_count"] == 256
    assert result.metadata["feasible_pool_size"] == 256
    assert result.metadata["evaluations"] == 257
    assert result.metadata["local_starts"] == 0
