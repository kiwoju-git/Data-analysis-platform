import math

import numpy as np
import pytest

from app.statistics.bo_observation_groups import (
    BoObservationGroupsError,
    prepare_bo_observation_view,
)


def _factors():
    return [{"factor_id": "x", "low": 0.0, "high": 1.0}]


def _observations(xs, ys, *, contexts=None):
    return [
        {
            "trial_id": f"trial-{index}",
            "actual_coordinates": {"x": x},
            "normalized_coordinates": {"x": x},
            "objective_value": y,
            **({"condition_key": contexts[index]} if contexts is not None else {}),
        }
        for index, (x, y) in enumerate(zip(xs, ys, strict=True))
    ]


def test_exact_replicates_preserve_unequal_counts_singletons_and_raw_normalization():
    rows = _observations([0, 0, 0, 0.5, 1, 1], [1, 3, 5, 4, 10, 12])
    view = prepare_bo_observation_view(rows, _factors(), mode="exact_replicates")
    assert view.raw_observation_count == 6
    assert view.unique_condition_count == 3
    assert view.effective_training_count == 3
    assert [group.n for group in view.groups] == [3, 1, 2]
    assert [group.mean for group in view.groups] == [3, 4, 11]
    assert [group.within_ss for group in view.groups] == [8, 0, 2]
    assert [group.sample_variance for group in view.groups] == [4, None, 2]
    assert view.groups[0].member_trial_ids == ("trial-0", "trial-1", "trial-2")
    assert view.groups[2].member_indices == (4, 5)
    assert view.normalization_mean == pytest.approx(35 / 6, abs=1e-14)
    expected_scale = math.sqrt(sum((y - 35 / 6) ** 2 for y in [1, 3, 5, 4, 10, 12]) / 6)
    assert view.normalization_scale == pytest.approx(expected_scale, rel=1e-14)
    assert view.normalization_mean != np.mean([3, 4, 11])
    np.testing.assert_allclose(
        view.training_y_scaled, (np.array([3, 4, 11]) - 35 / 6) / expected_scale, rtol=1e-14
    )
    np.testing.assert_allclose(
        view.training_within_ss_scaled, np.array([8, 0, 2]) / expected_scale**2, rtol=1e-14
    )
    assert rows[0]["objective_value"] == 1
    assert view.provenance()["normalization"]["ddof"] == 0


@pytest.mark.parametrize("mode", ["retain_raw", "nearby_diagnostics"])
def test_noncompressing_modes_retain_every_training_row(mode):
    rows = _observations([0, 0, 0.02, 1], [1, 3, 2, 8])
    kwargs = {"nearby_tolerances": {"x": 0.05}} if mode == "nearby_diagnostics" else {}
    view = prepare_bo_observation_view(rows, _factors(), mode=mode, **kwargs)
    assert view.effective_training_count == 4
    assert view.unique_condition_count == 3
    np.testing.assert_array_equal(view.training_x, view.raw_x)
    np.testing.assert_array_equal(view.training_y_scaled, view.raw_y_scaled)
    np.testing.assert_array_equal(view.training_counts, [1, 1, 1, 1])
    np.testing.assert_array_equal(view.training_within_ss_scaled, [0, 0, 0, 0])


def test_nearby_uses_deterministic_complete_link_not_connected_components():
    rows = _observations([0, 0.09, 0.18, 1], [1, 2, 3, 4])
    view = prepare_bo_observation_view(
        rows, _factors(), mode="nearby_diagnostics", nearby_tolerances={"x": 0.1}
    )
    assert [group.member_trial_ids for group in view.nearby_groups] == [("trial-0", "trial-1")]
    assert view.nearby_groups[0].maximum_normalized_distance == pytest.approx(0.09)
    assert view.nearby_groups[0].response_sample_variance == pytest.approx(0.5)
    reverse = prepare_bo_observation_view(
        list(reversed(rows)), _factors(), mode="nearby_diagnostics", nearby_tolerances={"x": 0.1}
    )
    assert [group.member_trial_ids for group in reverse.nearby_groups] == [("trial-0", "trial-1")]


def test_nearby_units_are_explicit_and_discrete_levels_never_merge():
    factors = [
        {"factor_id": "x", "low": 10, "high": 20},
        {"factor_id": "d", "low": 0, "high": 2, "domain_kind": "discrete_numeric", "step": 1},
    ]
    rows = [
        {
            "trial_id": f"trial-{i}",
            "actual_coordinates": {"x": x, "d": d},
            "normalized_coordinates": {"x": (x - 10) / 10, "d": d / 2},
            "objective_value": i + 1,
        }
        for i, (x, d) in enumerate([(10, 0), (10.5, 0), (10.5, 1), (20, 2)])
    ]
    normalized = prepare_bo_observation_view(
        rows,
        factors,
        mode="nearby_diagnostics",
        nearby_tolerances={"x": 0.1, "d": 1},
        nearby_units="normalized",
    )
    assert normalized.nearby_groups[0].member_trial_ids == ("trial-0", "trial-1")
    actual = prepare_bo_observation_view(
        rows, factors, mode="nearby_diagnostics", nearby_tolerances={"x": 0.1, "d": 2}
    )
    assert actual.nearby_groups == ()


def test_full_actual_identity_does_not_use_novelty_tolerance_or_display_rounding():
    rows = _observations([0, 1e-14, 1, 1], [1, 2, 3, 5])
    view = prepare_bo_observation_view(rows, _factors(), mode="exact_replicates")
    assert view.unique_condition_count == 3
    assert [group.n for group in view.groups] == [1, 1, 2]
    assert view.groups[1].canonical_actual_coordinates == (1e-14,)


def test_explicit_process_context_is_part_of_exact_and_nearby_identity():
    rows = _observations([0, 0, 1], [1, 2, 3], contexts=["X" * 121 + "A", "X" * 121 + "B", None])
    view = prepare_bo_observation_view(rows, _factors(), mode="exact_replicates")
    assert view.unique_condition_count == 3
    nearby = prepare_bo_observation_view(
        rows, _factors(), mode="nearby_diagnostics", nearby_tolerances={"x": 0.1}
    )
    assert nearby.nearby_groups == ()


def test_discrete_identity_uses_canonical_level_index():
    factors = [
        {"factor_id": "x", "low": 0, "high": 1, "domain_kind": "discrete_numeric", "step": 0.1}
    ]
    rows = _observations([0.3, 0.1 + 0.2, 1], [1, 3, 5])
    view = prepare_bo_observation_view(rows, factors, mode="exact_replicates")
    assert [group.n for group in view.groups] == [2, 1]
    assert view.groups[0].canonical_level_indices == (3,)
    assert view.groups[0].canonical_actual_coordinates == (0.3,)
    assert view.raw_actual_coordinates[1] == (0.1 + 0.2,)


@pytest.mark.parametrize("mode", ["retain_raw", "exact_replicates", "nearby_diagnostics"])
def test_raw_budget_cannot_be_bypassed_by_compression(mode):
    rows = _observations([0] * 200 + [1], list(range(201)))
    kwargs = {"nearby_tolerances": {"x": 0.1}} if mode == "nearby_diagnostics" else {}
    with pytest.raises(BoObservationGroupsError, match="observation_limit"):
        prepare_bo_observation_view(rows, _factors(), mode=mode, **kwargs)


def test_repeats_do_not_satisfy_unique_coordinate_minimum():
    with pytest.raises(BoObservationGroupsError, match="unique_conditions_insufficient"):
        prepare_bo_observation_view(_observations([0] * 6, list(range(6))), _factors())


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows[0].update(trial_id=rows[1]["trial_id"]),
        lambda rows: rows[0].update(trial_id=""),
        lambda rows: rows[0].update(objective_value=float("nan")),
        lambda rows: rows[0].update(objective_value=float("inf")),
        lambda rows: rows[0].update(objective_value=True),
        lambda rows: rows[0].update(normalized_coordinates={"x": 0.9}),
        lambda rows: rows[0].update(actual_coordinates={"x": -1}),
        lambda rows: rows[0].update(condition_key={"time": 1}),
    ],
)
def test_invalid_observation_identity_or_value_is_rejected(mutation):
    rows = _observations([0, 1], [1, 2])
    mutation(rows)
    with pytest.raises(BoObservationGroupsError):
        prepare_bo_observation_view(rows, _factors())


@pytest.mark.parametrize(
    "tolerance", [None, {}, {"x": -1}, {"x": float("nan")}, {"x": 1, "other": 1}]
)
def test_nearby_tolerances_are_complete_finite_and_nonnegative(tolerance):
    with pytest.raises(BoObservationGroupsError, match="nearby"):
        prepare_bo_observation_view(
            _observations([0, 1], [1, 2]),
            _factors(),
            mode="nearby_diagnostics",
            nearby_tolerances=tolerance,
        )


def test_constant_response_is_recorded_and_arrays_cannot_mutate_view():
    view = prepare_bo_observation_view(_observations([0, 1], [4, 4]), _factors())
    assert view.normalization_scale == 1
    assert view.constant_response
    assert view.provenance()["raw_observation_count"] == 2
    with pytest.raises(ValueError):
        view.raw_y[0] = 99


def test_sufficient_statistics_match_independent_raw_cholesky_likelihood_and_posterior():
    rows = _observations([0, 0, 0, 0.5, 1, 1], [1, 3, 5, 4, 10, 12])
    view = prepare_bo_observation_view(rows, _factors(), mode="exact_replicates")
    observation_variance, jitter = 0.3, 1e-8
    variance = observation_variance + jitter
    x_raw = np.array([0, 0, 0, 0.5, 1, 1])
    y_raw = (np.array([1, 3, 5, 4, 10, 12]) - 35 / 6) / view.normalization_scale
    unique = view.training_x[:, 0]

    def kernel(left, right):
        return 1.4 * np.exp(-0.5 * ((left[:, None] - right[None, :]) / 0.7) ** 2)

    def log_likelihood(y, covariance):
        lower = np.linalg.cholesky(covariance)
        white = np.linalg.solve(lower, y)
        return (
            -0.5 * white @ white - np.log(np.diag(lower)).sum() - len(y) / 2 * math.log(2 * math.pi)
        )

    raw_covariance = kernel(x_raw, x_raw) + variance * np.eye(6)
    compressed_covariance = kernel(unique, unique) + np.diag(variance / view.training_counts)
    corrected = log_likelihood(view.training_y_scaled, compressed_covariance) - 0.5 * np.sum(
        (view.training_counts - 1) * math.log(2 * math.pi * variance)
        + view.training_within_ss_scaled / variance
        + np.log(view.training_counts)
    )
    assert corrected == pytest.approx(log_likelihood(y_raw, raw_covariance), rel=1e-13, abs=1e-13)
    query = np.array([0.2, 0.8])
    raw_cross, compressed_cross = kernel(query, x_raw), kernel(query, unique)
    np.testing.assert_allclose(
        raw_cross @ np.linalg.solve(raw_covariance, y_raw),
        compressed_cross @ np.linalg.solve(compressed_covariance, view.training_y_scaled),
        rtol=1e-13,
        atol=1e-13,
    )
    np.testing.assert_allclose(
        kernel(query, query) - raw_cross @ np.linalg.solve(raw_covariance, raw_cross.T),
        kernel(query, query)
        - compressed_cross @ np.linalg.solve(compressed_covariance, compressed_cross.T),
        rtol=1e-13,
        atol=1e-13,
    )


def test_process_context_cannot_inflate_explored_coordinate_minimum():
    rows = _observations([0, 0], [1, 2], contexts=["batch A", "batch B"])
    with pytest.raises(BoObservationGroupsError, match="unique_conditions_insufficient"):
        prepare_bo_observation_view(rows, _factors())


@pytest.mark.parametrize("rows", [[], _observations([0], [1])])
def test_empty_or_insufficient_observations_fail(rows):
    with pytest.raises(BoObservationGroupsError):
        prepare_bo_observation_view(rows, _factors())


@pytest.mark.parametrize("minimum", [0, 1, True, 1.5, 201])
def test_explicit_minimum_cannot_weaken_product_unique_policy(minimum):
    with pytest.raises(BoObservationGroupsError, match="unique_condition_policy_invalid"):
        prepare_bo_observation_view(
            _observations([0, 1], [1, 2]), _factors(), minimum_unique_conditions=minimum
        )


def test_large_zero_within_variance_and_raw_boundary():
    view = prepare_bo_observation_view(
        _observations([0] * 100 + [1] * 100, [2] * 100 + [5] * 100),
        _factors(),
        mode="exact_replicates",
    )
    assert view.raw_observation_count == 200
    assert [group.n for group in view.groups] == [100, 100]
    assert [group.within_ss for group in view.groups] == [0, 0]
    np.testing.assert_allclose(view.training_counts, [100, 100])


@pytest.mark.parametrize("values", [[1e308, -1e308], [10**1000, 1]])
def test_statistical_overflow_is_an_explicit_error(values):
    with pytest.raises(BoObservationGroupsError):
        prepare_bo_observation_view(_observations([0, 1], values), _factors())
