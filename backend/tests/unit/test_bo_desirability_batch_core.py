from __future__ import annotations

import copy
import json

import pytest
from pydantic import ValidationError
from test_bo_desirability_contract import calculation_request

from app.api.v1.schemas.bo_desirability_batch_calculation import (
    DesirabilityBatchCalculationRequest,
    DesirabilityBatchCalculationResult,
)
from app.services.bo_desirability_batch_contract import validate_batch_calculation_result
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability_batch_core import calculate_desirability_batch
from app.statistics.bo_desirability_core import calculate_desirability_recommendation


def batch_request(q=2):
    raw = calculation_request()
    raw.update(
        schema_version=5,
        batch_size=q,
        batch_options={
            "sample_count": 16,
            "max_moment_evaluations": 8192,
            "min_batch_distance_normalized": 0.05,
        },
    )
    raw["search"]["max_evaluations_total"] = 1024
    raw["search"]["time_budget_ms"] = 60000
    return raw


def test_new_contract_rejects_legacy_version_and_strict_batch_options():
    parsed = DesirabilityBatchCalculationRequest.model_validate(batch_request())
    assert parsed.batch_size == 2
    for patch in (
        {"schema_version": 4},
        {"batch_size": True},
        {"batch_size": 9},
        {"batch_options": {"sample_count": 15}},
        {"batch_size": "2"},
    ):
        with pytest.raises(ValidationError):
            DesirabilityBatchCalculationRequest.model_validate({**batch_request(), **patch})


def test_first_candidate_preserves_q1_and_fit_once_per_response(monkeypatch):
    from app.statistics import bo_surrogate

    original = bo_surrogate.fit_bo_surrogate
    calls = []

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(bo_surrogate, "fit_bo_surrogate", counted)
    request = DesirabilityBatchCalculationRequest.model_validate(batch_request())
    before = copy.deepcopy(request.worker_payload())
    result = calculate_desirability_batch(before)
    assert len(calls) == 2
    assert before == request.worker_payload()
    parsed = DesirabilityBatchCalculationResult.model_validate_json(json.dumps(result))
    validate_batch_calculation_result(request, parsed)
    legacy = request.q1_request().worker_payload()
    old = calculate_desirability_recommendation(legacy)
    first = result["items"][0]
    for key in old["items"][0]:
        assert first[key] == old["items"][0][key]
    assert [i["rank"] for i in result["items"]] == [1, 2]
    assert first["planning"]["score"] == first["acquisition"]["value"]
    assert result["items"][1]["planning"]["sampler"]["effective_sample_count"] == 16
    assert result["search_budget"]["response_fit_count"] == 2
    assert result["search_budget"]["final_factorizations"] == 2


def test_batch_moment_preflight_rejects_before_fit(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("preflight must precede fitting")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    raw = batch_request(8)
    raw["batch_options"]["sample_count"] = 256
    with pytest.raises(BayesianOptimizationError, match="batch_budget_exhausted"):
        calculate_desirability_batch(raw)


def test_impossible_distance_never_returns_partial_batch():
    raw = batch_request(2)
    raw["batch_options"]["min_batch_distance_normalized"] = 2.0
    with pytest.raises(BayesianOptimizationError, match="no_feasible_candidate"):
        calculate_desirability_batch(raw)


@pytest.fixture(scope="module")
def complete_batch():
    request = DesirabilityBatchCalculationRequest.model_validate(batch_request(3))
    raw = calculate_desirability_batch(request.worker_payload())
    return request, raw


def test_all_steps_share_model_budget_and_no_refit_validation(complete_batch, monkeypatch):
    request, raw = complete_batch

    def forbidden(*args, **kwargs):
        pytest.fail("validation must not fit or evaluate sample quadrature")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    parsed = DesirabilityBatchCalculationResult.model_validate_json(json.dumps(raw))
    validate_batch_calculation_result(request, parsed)
    consumed = raw["search_budget"]["incumbent_moment_evaluations"]
    for item in raw["items"]:
        sampler = item["planning"]["sampler"]
        assert sampler["max_moment_evaluations"] == 8192 - consumed
        consumed += sampler["moment_evaluations"]
    assert consumed == raw["search_budget"]["moment_evaluations"]
    assert raw["items"][1]["planning"]["score"] != raw["items"][1]["acquisition"]["value"]


@pytest.mark.parametrize(
    "defect",
    [
        "rank",
        "seed",
        "prefix",
        "covariance",
        "cross",
        "conditional",
        "threshold",
        "score",
        "mc_error",
        "moments",
        "budget",
        "response_id",
    ],
)
def test_malformed_batch_proof_is_rejected(complete_batch, defect):
    request, original = complete_batch
    raw = copy.deepcopy(original)
    item = raw["items"][2]
    planning = item["planning"]
    proof = planning["proof"]
    if defect == "rank":
        item["rank"] = 2
    elif defect == "seed":
        planning["sampler"]["response_sample_seeds"]["yield"] = "1"
    elif defect == "prefix":
        planning["sampler"]["conditioned_on_selected_ranks"] = [2, 1]
    elif defect == "covariance":
        cov = proof["response_proofs"]["yield"]["selected_covariance_scaled"]
        cov[0][1] = cov[1][0] = 0.0
    elif defect == "cross":
        proof["response_proofs"]["yield"]["cross_covariance_scaled"][0] += 1
    elif defect == "conditional":
        planning["conditional_variance_raw"]["yield"] *= 2
    elif defect == "threshold":
        proof["thresholds"][0] += 0.01
    elif defect == "score":
        planning["score"] += 0.01
    elif defect == "mc_error":
        planning["mc_standard_error"] += 0.01
    elif defect == "moments":
        proof["sample_moments"][0]["variance"] = 0.25
    elif defect == "budget":
        planning["sampler"]["moment_evaluations"] += 1
    else:
        item["response_predictions"][0]["response_id"] = "cost"
    with pytest.raises((ValidationError, BayesianOptimizationError)):
        parsed = DesirabilityBatchCalculationResult.model_validate_json(json.dumps(raw))
        validate_batch_calculation_result(request, parsed)


def test_fixed_seed_repeats_entire_ordered_batch(complete_batch):
    request, previous = complete_batch
    repeated = calculate_desirability_batch(request.worker_payload())
    assert repeated["items"] == previous["items"]
    assert repeated["incumbent"] == previous["incumbent"]


def test_q8_is_complete_with_explicit_small_sample_budget():
    raw = batch_request(8)
    raw["batch_options"]["min_batch_distance_normalized"] = 0.02
    result = calculate_desirability_batch(raw)
    assert len(result["items"]) == 8
    parsed = DesirabilityBatchCalculationResult.model_validate_json(json.dumps(result))
    validate_batch_calculation_result(
        DesirabilityBatchCalculationRequest.model_validate(raw), parsed
    )
    assert result["search_budget"]["moment_evaluations"] <= 8192


def mixed_request(q=2):
    raw = batch_request(q)
    raw["factors"].append(
        {"factor_id": "d", "low": 0.0, "high": 2.0, "domain_kind": "discrete_numeric", "step": 1.0}
    )
    for i, row in enumerate(raw["observations"]):
        row["actual_coordinates"]["d"] = float(i % 3)
        row["normalized_coordinates"]["d"] = i % 3 / 2
        raw["excluded_normalized"][i].append(i % 3 / 2)
    raw["constraints"] = [
        {
            "constraint_id": "limit",
            "name": "Synthetic limit",
            "terms": [
                {"factor_id": "x", "coefficient": 1.0},
                {"factor_id": "d", "coefficient": 0.1},
            ],
            "relation": "less_than_or_equal",
            "bound": 0.95,
        }
    ]
    return raw


def test_discrete_enumeration_pool_is_not_miscounted_as_random_pool():
    from app.statistics.bo_desirability_batch_core import batch_preflight

    raw = mixed_request()
    request = DesirabilityBatchCalculationRequest.model_validate(raw)
    info = batch_preflight(request)
    assert info["initial_pool_upper_bound_per_step"] == 35
    assert info["preflight_moment_allowance"] == 5 + 37 * 18
    raw["batch_options"]["max_moment_evaluations"] = 5 + 34 * 18
    with pytest.raises(BayesianOptimizationError, match="batch_budget_exhausted"):
        batch_preflight(DesirabilityBatchCalculationRequest.model_validate(raw))


def test_mixed_search_local_refinement_constraints_and_canonical_score():
    raw = mixed_request()
    raw["search"]["local_start_count_per_step"] = 1
    result = calculate_desirability_batch(raw)
    assert all(s["local_starts"] == 1 for s in result["search_budget"]["searches"])
    for item in result["items"]:
        actual = item["actual_coordinates"]
        assert actual["d"] in (0, 1, 2)
        assert actual["x"] + 0.1 * actual["d"] <= 0.95 + 1e-10
        assert item["normalized_coordinates"]["d"] == actual["d"] / 2
        assert all(c["satisfied"] for c in item["constraint_evaluations"])
    validate_batch_calculation_result(
        DesirabilityBatchCalculationRequest.model_validate(raw),
        DesirabilityBatchCalculationResult.model_validate_json(json.dumps(result)),
    )


def test_runtime_moment_exhaustion_after_first_selection_returns_no_partial(monkeypatch):
    import numpy as np

    from app.statistics import bo_desirability_batch_core as core

    original = core.search_mixed_acquisition
    calls = []

    def added_work(**kwargs):
        calls.append(1)
        if len(calls) == 2:
            kwargs["consume"](60)
            kwargs["score"](np.full((60, 1), 0.19))
        return original(**kwargs)

    monkeypatch.setattr(core, "search_mixed_acquisition", added_work)
    raw = batch_request()
    raw["batch_options"]["max_moment_evaluations"] = 700
    with pytest.raises(BayesianOptimizationError, match="batch_budget_exhausted"):
        calculate_desirability_batch(raw)
    assert len(calls) == 2


def test_local_solver_revisiting_selected_point_keeps_actual_budget(monkeypatch):
    import numpy as np

    from app.statistics import bo_desirability_batch_core as core
    from app.statistics import bo_mixed_search as mixed

    original_search, original_minimize = core.search_mixed_acquisition, mixed.minimize
    selected = []

    def search(**kwargs):
        selected[:] = kwargs["selected_normalized"]
        return original_search(**kwargs)

    def minimize(fun, *args, **kwargs):
        if selected:
            fun(np.asarray(selected[0]))
        return original_minimize(fun, *args, **kwargs)

    monkeypatch.setattr(core, "search_mixed_acquisition", search)
    monkeypatch.setattr(mixed, "minimize", minimize)
    raw = batch_request()
    raw["search"]["local_start_count_per_step"] = 1
    result = calculate_desirability_batch(raw)
    assert result["items"][1]["planning"]["sampler"]["exact_selected_evaluations"] >= 1
    validate_batch_calculation_result(
        DesirabilityBatchCalculationRequest.model_validate(raw),
        DesirabilityBatchCalculationResult.model_validate_json(json.dumps(result)),
    )


def test_distinct_actual_identity_with_same_float_encoding_counts_cached_work():
    raw = batch_request(1)
    raw["factors"][0]["low"] = -1.0
    actuals = [-1.0, -0.5, 0.0, 1e-17, 1.0]
    for i, (row, actual) in enumerate(zip(raw["observations"], actuals, strict=True)):
        row["actual_coordinates"]["x"] = actual
        row["normalized_coordinates"]["x"] = (actual + 1) / 2
        raw["excluded_normalized"][i] = [(actual + 1) / 2]
    result = calculate_desirability_batch(raw)
    assert result["observation_view"]["unique_coordinate_count"] == 5
    assert result["observation_view"]["raw_observation_count"] == 5
    assert result["search_budget"]["incumbent_moment_evaluations"] == 4
    validate_batch_calculation_result(
        DesirabilityBatchCalculationRequest.model_validate(raw),
        DesirabilityBatchCalculationResult.model_validate_json(json.dumps(result)),
    )
