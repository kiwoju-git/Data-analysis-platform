"""Independent positive-density reference; no surrogate fitting or GP workers."""

import json
import math
from decimal import Decimal
from pathlib import Path

import pytest

from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from tests.reference.bo_beta_reference import (
    decimal_beta_stop_loss,
    moment_matched_reference,
)


def test_decimal_reference_matches_exact_symmetric_integer_shape():
    result = decimal_beta_stop_loss(100.0, 100.0, 0.5)
    exact = math.comb(200, 100) / 4**101
    assert result.value == pytest.approx(exact, rel=2e-12, abs=0)
    assert result.quadrature_relative_error <= 2e-11
    assert result.tail_relative_bound <= 2e-12
    assert Decimal(result.log_gamma_remainder_bound) < Decimal("1e-30")


def test_decimal_reference_rejects_unvalidated_scope():
    with pytest.raises(ValueError, match="shape"):
        decimal_beta_stop_loss(2.0, 2.0, 0.5)
    with pytest.raises(ValueError, match="threshold"):
        decimal_beta_stop_loss(100.0, 100.0, 0.0)


def test_frozen_decimal_references_recompute_and_match_production():
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "bo_beta_decimal_reference.json").read_text(
            encoding="utf-8"
        )
    )
    for case in fixture["cases"]:
        mean, variance, threshold = case["mean"], case["variance"], case["threshold"]
        reference = moment_matched_reference(mean, variance, threshold)
        assert reference.value == pytest.approx(case["expected_ei"], rel=2e-12, abs=0)
        assert reference.quadrature_relative_error <= fixture["quadrature_error_limit"]
        assert reference.tail_relative_bound <= fixture["tail_relative_bound_limit"]
        result = beta_expected_improvement(mean, variance, threshold)
        assert result.distribution == "beta_moment_match"
        assert result.value == pytest.approx(
            reference.value, rel=fixture["production_relative_tolerance"], abs=0
        )
        if "expected_log_ei" in case:
            assert float(reference.log_value) == pytest.approx(
                case["expected_log_ei"], rel=0, abs=1e-10
            )
            assert reference.log_tangent_upper_bound is not None
            assert float(reference.log_tangent_upper_bound) == pytest.approx(
                case["expected_log_tangent_upper_bound"], rel=0, abs=1e-10
            )
            assert Decimal(reference.log_tangent_upper_bound) < -Decimal(1075) * Decimal(2).ln()
