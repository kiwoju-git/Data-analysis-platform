from __future__ import annotations

import pytest

from app.statistics.gp_resource_budget import GpResourceError, estimate_gp_resources


def estimate(n: int = 500, **changes: object):
    options = {
        "profile": "standard_exact",
        "n_rows": n,
        "fold_training_sizes": (int(n * 0.8),) * 5,
        "kernel_parameter_counts": (4,),
        "optimizer_restarts": 1,
        "cv_optimizer_restarts": 0,
        "retained_candidate_count": 0,
        "prediction_query_count": 1000,
    }
    options.update(changes)
    return estimate_gp_resources(**options)


def test_standard_limit_is_not_silently_raised():
    assert estimate().row_limit == 500
    with pytest.raises(GpResourceError, match="gp_usable_rows_limit"):
        estimate(501)


@pytest.mark.parametrize("n", [501, 1000, 2000])
def test_explicit_extended_small_parameter_model_has_bounded_estimate(n):
    result = estimate(n, profile="extended_exact", kernel_parameter_counts=(2,))
    assert result.row_limit == 2000
    assert 0 < result.estimated_peak_bytes <= 512 * 1024**2
    assert result.final_refit_count == 1
    assert result.optimizer_start_count == 7
    assert result.total_training_cubic_units == n**3 * 2 + int(n * 0.8) ** 3 * 5
    assert result.to_payload()["memory_enforcement"] == "admission_estimate_not_os_limit"


def test_two_thousand_rows_is_not_permission_for_every_parameter_count():
    with pytest.raises(GpResourceError, match="gp_memory_budget_exceeded"):
        estimate(2000, profile="extended_exact", kernel_parameter_counts=(18,))


def test_cost_includes_fold_sizes_candidates_restarts_and_retained_refits():
    base = estimate(1000, profile="extended_exact", kernel_parameter_counts=(4,))
    detailed = estimate(
        1000,
        profile="extended_exact",
        kernel_parameter_counts=(4, 5),
        retained_candidate_count=1,
        optimizer_restarts=2,
        cv_optimizer_restarts=1,
    )
    assert detailed.final_refit_count == 2
    assert detailed.optimizer_start_count == 26
    assert detailed.total_training_cubic_units > base.total_training_cubic_units
    assert detailed.estimated_peak_bytes > base.estimated_peak_bytes


def test_prediction_is_chunked_not_full_query_covariance():
    small = estimate(prediction_query_count=256)
    large = estimate(prediction_query_count=10000)
    assert large.prediction_chunk_size == 256
    assert large.prediction_peak_bytes == small.prediction_peak_bytes
    assert large.prediction_chunk_count > small.prediction_chunk_count


@pytest.mark.parametrize(
    "changes",
    [
        {"profile": "approximate"},
        {"n_rows": 2001, "profile": "extended_exact"},
        {"fold_training_sizes": (500, 501)},
        {"kernel_parameter_counts": ()},
        {"kernel_parameter_counts": (float("nan"),)},
        {"optimizer_restarts": -1},
        {"retained_candidate_count": 4},
        {"n_rows": True},
    ],
)
def test_invalid_resource_contract_rejected(changes):
    with pytest.raises(GpResourceError):
        estimate(**changes)
