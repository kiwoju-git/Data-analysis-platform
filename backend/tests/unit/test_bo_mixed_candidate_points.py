"""Mixed candidate identity and distance are independent from learned kernels."""

from copy import deepcopy

import pytest

from app.api.v1.schemas.bo_mixed_planning import MixedCandidateRow
from app.statistics.bo_factor_domains import BoCategoricalFactorDomain, BoNumericFactorDomain
from app.statistics.bo_mixed_candidate_points import (
    generate_mixed_candidate_points,
    validated_mixed_candidate_rows,
)
from app.statistics.bo_mixed_initial_design import MixedLinearConstraint
from app.statistics.doe_factor_domain import DoeFactorDomain


def domains(kind="nominal"):
    return (
        BoNumericFactorDomain("x", DoeFactorDomain(1000.0, 1001.0, "discrete_numeric", 0.1)),
        BoCategoricalFactorDomain(
            "group",
            kind,
            ("  A  ", "B", "C"),
            "ordinal_monotone_latent_rbf_v1"
            if kind == "ordinal"
            else "equal_positive_correlation_v1",
        ),
    )


def validate(points, *, prior=None, kind="nominal", ordinal=False, **kwargs):
    return validated_mixed_candidate_rows(
        points,
        domains(kind),
        [],
        excluded_encoded=prior or [],
        duplicate_tolerance=1e-6,
        ordinal_rank_distance=ordinal,
        **kwargs,
    )


def test_canonical_decimal_levels_and_whole_category_identity():
    points = [{"x": 1000.1, "group": "  A  "}, {"x": 1000.1, "group": "B"}]
    original = deepcopy(points)
    rows = validate(points, prior=[[0.1, 0.0]])
    assert points == original
    assert rows[0]["actual_coordinates"] == points[0]
    assert rows[0]["canonical_level_indices"] == {"x": 1, "group": 0}
    assert rows[0]["novel"] is False and rows[1]["novel"] is True
    assert rows[1]["nearest_existing_distance"] == pytest.approx(1.0)
    assert rows[0]["row_id"] != rows[1]["row_id"]
    for row in rows:
        assert MixedCandidateRow.model_validate(row).model_dump(mode="json") == row
        assert "normalized_coordinates" not in row


@pytest.mark.parametrize("level", ["A", 0, "unknown"])
def test_no_category_trim_numeric_coercion_or_unknown_level(level):
    with pytest.raises(ValueError):
        validate([{"x": 1000.1, "group": level}])


def test_declared_ordinal_rank_distance_requires_explicit_selection():
    points = [{"x": 1000.0, "group": "B"}]
    default = validate(points, prior=[[0.0, 0.0]], kind="ordinal")[0]
    ranked = validate(points, prior=[[0.0, 0.0]], kind="ordinal", ordinal=True)[0]
    assert default["nearest_existing_distance"] == 1.0
    assert ranked["nearest_existing_distance"] == 0.5
    assert default["distance_policy"] != ranked["distance_policy"]


def test_constraints_keep_invalid_rows_only_on_explicit_request():
    constraint = MixedLinearConstraint("limit", (("x", 1.0),), "less_than_or_equal", 1000.5)
    points = [{"x": 1000.8, "group": "B"}]
    with pytest.raises(ValueError, match="constraint_violation"):
        validated_mixed_candidate_rows(
            points, domains(), [constraint], excluded_encoded=[], duplicate_tolerance=1e-6
        )
    row = validated_mixed_candidate_rows(
        points,
        domains(),
        [constraint],
        excluded_encoded=[],
        duplicate_tolerance=1e-6,
        include_constraint_violations=True,
    )[0]
    assert row["eligible"] is False and row["constraints_satisfied"] is False
    assert row["constraint_evaluations"][0]["slack"] == pytest.approx(-0.3)


def test_generation_is_deterministic_feasible_and_bounded():
    constraint = MixedLinearConstraint("limit", (("x", 1.0),), "less_than_or_equal", 1000.5)
    first = generate_mixed_candidate_points(domains(), [constraint], seed=42, count=8)
    assert first == generate_mixed_candidate_points(domains(), [constraint], seed=42, count=8)
    assert len(first["points"]) == 8
    assert all(point["x"] <= 1000.5 for point in first["points"])
    assert len({tuple(point.values()) for point in first["points"]}) == 8
    with pytest.raises(ValueError, match="space_exhausted"):
        generate_mixed_candidate_points(domains(), [], seed=42, count=34)
    with pytest.raises(ValueError, match="generation_budget_exhausted"):
        generate_mixed_candidate_points(domains(), [constraint], seed=42, count=18, max_attempts=18)


def test_deadline_callback_prevents_candidate_work():
    def expired():
        raise ValueError("synthetic_deadline_expired")

    with pytest.raises(ValueError, match="synthetic_deadline_expired"):
        validate([{"x": 1000.1, "group": "B"}], check_budget=expired)
    with pytest.raises(ValueError, match="synthetic_deadline_expired"):
        generate_mixed_candidate_points(domains(), [], seed=42, count=2, check_budget=expired)
