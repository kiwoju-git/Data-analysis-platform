from copy import deepcopy

import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_candidate_points import (
    generate_candidate_points,
    validated_candidate_rows,
)


def _factors():
    return [
        {"factor_id": "d", "low": 0.0, "high": 2.0, "domain_kind": "discrete_numeric", "step": 1.0},
        {"factor_id": "x", "low": -2.0, "high": 4.0},
    ]


def _constraints():
    return [
        {
            "constraint_id": "limit",
            "name": "Limit",
            "terms": [{"factor_id": "x", "coefficient": 1.0}],
            "relation": "less_than_or_equal",
            "bound": 1.0,
        }
    ]


def test_candidate_generation_is_seeded_executable_complete_and_immutable():
    factors, constraints = _factors(), _constraints()
    original = deepcopy((factors, constraints))
    result = generate_candidate_points(factors, constraints, count=100, seed=17)
    assert result == generate_candidate_points(factors, constraints, count=100, seed=17)
    assert len(result["points"]) == 100
    assert all(p["d"] in {0, 1, 2} and -2 <= p["x"] <= 1 for p in result["points"])
    assert len({tuple(point.items()) for point in result["points"]}) == 100
    assert (factors, constraints) == original


def test_import_preserves_order_values_and_marks_old_coordinates_without_dropping():
    points = [{"d": 2.0, "x": 1.0}, {"d": 0.0, "x": -2.0}]
    rows = validated_candidate_rows(
        points,
        _factors(),
        _constraints(),
        excluded_normalized=[[1.0, 0.5]],
        duplicate_tolerance=1e-8,
    )
    assert [r["actual_coordinates"] for r in rows] == points
    assert [r["source_row_number"] for r in rows] == [1, 2]
    assert [r["eligible"] for r in rows] == [False, True]
    reverse = validated_candidate_rows(
        points[::-1], _factors(), _constraints(), excluded_normalized=[], duplicate_tolerance=1e-8
    )
    assert [r["row_id"] for r in rows] == [r["row_id"] for r in reverse][::-1]


@pytest.mark.parametrize("value", ["1", True, float("nan"), float("inf"), 0.5, 3.0])
def test_import_does_not_coerce_or_snap_discrete_values(value):
    with pytest.raises(BayesianOptimizationError, match="bayesian_candidate_coordinates_invalid"):
        validated_candidate_rows(
            [{"d": value, "x": 0.0}],
            _factors(),
            [],
            excluded_normalized=[],
            duplicate_tolerance=1e-8,
        )


def test_import_violations_remain_ineligible_only_with_explicit_permission():
    args = ([{"d": 1.0, "x": 2.0}], _factors(), _constraints())
    with pytest.raises(BayesianOptimizationError, match="bayesian_candidate_constraint_violation"):
        validated_candidate_rows(*args, excluded_normalized=[], duplicate_tolerance=1e-8)
    rows = validated_candidate_rows(
        *args, excluded_normalized=[], duplicate_tolerance=1e-8, include_constraint_violations=True
    )
    assert rows[0]["novel"] and not rows[0]["eligible"]
    assert not rows[0]["constraint_evaluations"][0]["satisfied"]


def test_duplicate_rows_and_exhausted_discrete_space_are_explicit_errors():
    with pytest.raises(BayesianOptimizationError, match="bayesian_candidate_duplicate_row"):
        validated_candidate_rows(
            [{"d": 1.0, "x": 0.0}] * 2,
            _factors(),
            [],
            excluded_normalized=[],
            duplicate_tolerance=1e-8,
        )
    with pytest.raises(BayesianOptimizationError, match="bayesian_candidate_space_exhausted"):
        generate_candidate_points(_factors()[:1], [], count=4, seed=0)


def test_candidate_generation_never_returns_a_partial_success():
    with pytest.raises(
        BayesianOptimizationError, match="bayesian_candidate_generation_budget_exhausted"
    ):
        generate_candidate_points(_factors(), _constraints(), count=100, seed=0, max_attempts=100)


def test_discrete_representations_share_identity_and_original_input_is_preserved():
    factors = [
        {"factor_id": "x", "low": 0.0, "high": 1.0, "domain_kind": "discrete_numeric", "step": 0.1}
    ]

    def rows(value):
        return validated_candidate_rows(
            [{"x": value}], factors, [], excluded_normalized=[], duplicate_tolerance=1e-8
        )

    first, second = rows(0.3)[0], rows(0.30000000000000004)[0]
    assert first["row_id"] == second["row_id"]
    assert second["actual_coordinates"]["x"] == 0.3
    assert second["input_coordinates"]["x"] == 0.30000000000000004
    assert second["canonical_level_indices"] == {"x": 3}
    assert rows(-0.0)[0]["row_id"] == rows(0.0)[0]["row_id"]


def test_unrepresentable_range_is_not_an_infinite_candidate_or_false_normalization():
    factors = [{"factor_id": "x", "low": -1e308, "high": 1e308}]
    with pytest.raises(BayesianOptimizationError, match="range_precision_unsupported"):
        generate_candidate_points(factors, [], count=1, seed=0)
    with pytest.raises(BayesianOptimizationError, match="range_precision_unsupported"):
        validated_candidate_rows(
            [{"x": 0.0}], factors, [], excluded_normalized=[], duplicate_tolerance=1e-8
        )
