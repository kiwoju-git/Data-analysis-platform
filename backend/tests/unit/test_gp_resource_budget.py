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


def test_phase_estimate_keeps_budget_and_exposes_calibrated_process_allowance():
    result = estimate(2000, profile="extended_exact", kernel_parameter_counts=(2,))
    assert result.estimate_version == "exact_gp_peak_v2"
    assert result.process_allowance_bytes == 160 * 1024**2
    assert result.memory_budget_bytes == 512 * 1024**2
    assert result.estimated_peak_bytes == max(result.fit_phase_bytes, result.transfer_phase_bytes)
    assert result.fit_phase_bytes > result.transfer_phase_bytes
    assert result.comparison_allocator_reserve_bytes == 0


@pytest.mark.parametrize("parameters", [(2, 2), (3,)])
def test_two_thousand_complex_requests_are_rejected_without_option_changes(parameters):
    with pytest.raises(GpResourceError, match="gp_memory_budget_exceeded"):
        estimate(2000, profile="extended_exact", kernel_parameter_counts=parameters)


@pytest.mark.parametrize(
    ("n", "parameters", "observed_worker_mib"),
    [(501, (2,), 174.77), (1000, (3,), 248.84), (2000, (2,), 496.59)],
)
def test_estimate_covers_recorded_native_worker_calibration_cases(
    n, parameters, observed_worker_mib
):
    # Linux job 119267054835, source 1c178d3: post-serialization worker high-water RSS.
    result = estimate(
        n,
        profile="extended_exact",
        kernel_parameter_counts=parameters,
        prediction_query_count=n + 10,
    )
    assert result.estimated_peak_bytes >= observed_worker_mib * 1024**2


def test_actual_training_predictions_are_included_in_preflight(monkeypatch):
    from app.statistics import gaussian_process_regression as gp

    captured = []
    original = gp.estimate_gp_resources

    def record(**options):
        captured.append(options)
        return original(**options)

    monkeypatch.setattr(gp, "estimate_gp_resources", record)
    response = gp.GaussianProcessColumn(
        "y", 0, "Response", "decimal", "continuous", "response", None
    )
    predictor = gp.GaussianProcessColumn("x", 1, "Input", "decimal", "continuous", "feature", None)
    rows = [[str(2 * index + 0.1 * index**2), str(index)] for index in range(16)]
    result = gp.calculate_gaussian_process_regression(
        rows,
        response,
        [predictor],
        options=gp.GaussianProcessOptions(
            validation_method="none",
            optimizer_restarts=0,
            noise_mode="fixed",
            fixed_noise_standard_deviation=0.1,
            profile_points=10,
        ),
    )
    assert len(result["diagnostics"]["points"]) == 16
    assert captured[0]["prediction_query_count"] == 16 + 10


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
