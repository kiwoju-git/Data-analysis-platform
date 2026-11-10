import copy
import hashlib
import multiprocessing
import os
import threading
from types import SimpleNamespace

import pytest
from desirability_worker_probe import abruptly_exit, oversized_result, partial_frame, slow_result
from test_bo_desirability_contract import calculation_request

from app.services import bo_desirability_worker as worker
from app.services.analysis_run_execution import canonical_json_bytes
from app.services.bo_desirability_contract import (
    DesirabilityCalculationRequest,
    DesirabilityCalculationResult,
    validate_calculation_result,
)
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability_core import calculate_desirability_recommendation
from app.statistics.bo_desirability_posterior import raw_posterior_standard_deviation


@pytest.fixture(scope="module")
def actual_calculation():
    request = DesirabilityCalculationRequest.model_validate(calculation_request())
    result = calculate_desirability_recommendation(request.worker_payload())
    return request, result


def test_real_calculation_typed_round_trip_and_relationship_validation(actual_calculation):
    request, raw = actual_calculation
    result = DesirabilityCalculationResult.model_validate_json(
        canonical_json_bytes(raw), strict=True
    )
    validate_calculation_result(request, result)
    assert result.model_dump(mode="json") == raw


def test_impossible_training_moments_are_rejected(monkeypatch, actual_calculation):
    request, original = actual_calculation
    result = copy.deepcopy(original)
    result["incumbent"]["training_posterior_desirabilities"][0]["moments"]["variance"] = 0.2
    monkeypatch.setattr(
        worker, "_run_owned_worker", lambda payload, **kwargs: response_bytes(payload, result)
    )
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        worker.run_desirability_calculation(request)


def test_canonical_observation_coordinates_are_used_for_nearest_distance():
    raw = calculation_request()
    for index in (1, 2, 3):
        raw["observations"][index]["normalized_coordinates"]["x"] += 0.9e-12
        raw["excluded_normalized"][index][0] += 0.9e-12
    request = DesirabilityCalculationRequest.model_validate(raw)
    result = calculate_desirability_recommendation(request.worker_payload())
    parsed = DesirabilityCalculationResult.model_validate_json(
        canonical_json_bytes(result), strict=True
    )
    validate_calculation_result(request, parsed)


def test_actual_owned_spawn_uses_complete_snapshot_and_finite_json():
    request = DesirabilityCalculationRequest.model_validate(calculation_request())
    before = request.model_dump(mode="json")
    old_children = {p.pid for p in multiprocessing.active_children()}
    result = worker.run_desirability_calculation(request)
    assert result.request_sha256 == hashlib.sha256(canonical_json_bytes(before)).hexdigest()
    assert (
        result.result_sha256
        == hashlib.sha256(
            canonical_json_bytes(result.calculation.model_dump(mode="json"))
        ).hexdigest()
    )
    assert request.model_dump(mode="json") == before
    assert {p.pid for p in multiprocessing.active_children()} <= old_children


def response_bytes(payload, result):
    return canonical_json_bytes(
        {"status": "ok", "request_sha256": hashlib.sha256(payload).hexdigest(), "result": result}
    )


@pytest.mark.parametrize(
    "defect",
    [
        "response_id",
        "factor_order",
        "noise",
        "goal",
        "observed",
        "incumbent",
        "candidate",
        "score",
        "budget",
        "history",
        "group",
    ],
)
def test_corrupted_result_cannot_be_accepted_without_any_refit(
    monkeypatch, actual_calculation, defect
):
    request, original = actual_calculation
    result = copy.deepcopy(original)
    if defect == "response_id":
        result["items"][0]["response_predictions"][0]["response_id"] = "cost"
    elif defect == "factor_order":
        result["shared_model"]["response_models"][0]["model"]["factor_ids"] = ["wrong"]
    elif defect == "noise":
        result["items"][0]["response_predictions"][0]["predictive_standard_deviation_raw"] *= 2
    elif defect == "goal":
        result["objective"]["responses"][0]["target"] += 1
    elif defect == "observed":
        result["incumbent"]["observed_trial_desirabilities"][0]["value"] = 0.91
    elif defect == "incumbent":
        result["incumbent"]["latent_incumbent_value"] = 0.99
    elif defect == "candidate":
        result["items"][0]["normalized_coordinates"]["x"] = 0
    elif defect == "score":
        result["items"][0]["acquisition"]["value"] += 0.01
    elif defect == "budget":
        result["search_budget"]["evaluations_consumed"] = 129
    elif defect == "history":
        result["incumbent"]["training_posterior_desirabilities"].reverse()
    else:
        result["observation_view"]["groups"][0]["member_indices"] = [2]
    monkeypatch.setattr(
        worker, "_run_owned_worker", lambda payload, **kwargs: response_bytes(payload, result)
    )

    def forbidden(*args, **kwargs):
        pytest.fail("result validation must not refit")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        worker.run_desirability_calculation(request)


@pytest.mark.parametrize(
    "message",
    [
        b'{"status":"ok","status":"error"}',
        b'{"status":"ok","result":NaN}',
        b"[]",
        b'{"status":"ok","request_sha256":"wrong","result":{}}',
        b"invalid",
    ],
)
def test_protocol_rejects_nonfinite_duplicate_keys_and_wrong_snapshot(monkeypatch, message):
    monkeypatch.setattr(worker, "_run_owned_worker", lambda *args, **kwargs: message)
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        worker.run_desirability_calculation(
            DesirabilityCalculationRequest.model_validate(calculation_request())
        )


@pytest.mark.parametrize(
    "code,expected",
    [
        (
            "bayesian_desirability_beta_precision_unsupported",
            "bayesian_desirability_beta_precision_unsupported",
        ),
        ("bayesian_desirability_numeric_invalid", "bayesian_desirability_numeric_invalid"),
        ("secret filename measurement", "bayesian_optimization_surrogate_fit_failed"),
    ],
)
def test_worker_errors_are_stable_codes_without_raw_details(monkeypatch, code, expected):
    monkeypatch.setattr(
        worker,
        "_run_owned_worker",
        lambda *args, **kwargs: canonical_json_bytes({"status": "error", "code": code}),
    )
    with pytest.raises(BayesianOptimizationError) as error:
        worker.run_desirability_calculation(
            DesirabilityCalculationRequest.model_validate(calculation_request())
        )
    assert error.value.code == expected
    assert "secret" not in str(error.value)


def test_raw_sd_underflow_keeps_existing_numeric_error_across_worker_entry(monkeypatch):
    messages, closed = [], []

    def underflow(_payload):
        return raw_posterior_standard_deviation(1e-300, 1e-200)

    monkeypatch.setattr(
        "app.statistics.bo_desirability_core.calculate_desirability_recommendation", underflow
    )
    output = SimpleNamespace(send_bytes=messages.append, close=lambda: closed.append(True))
    worker._worker_entry(output, b"{}")
    assert worker._read_json(messages[0]) == {
        "status": "error",
        "code": "bayesian_desirability_numeric_invalid",
    }
    assert closed == [True]


def test_caller_mutation_after_spawn_cannot_change_worker_snapshot(monkeypatch, actual_calculation):
    original, result = actual_calculation
    request = original.model_copy(deep=True)

    def fake_run(payload, **kwargs):
        request.observations[0].response_values["cost"] = 9999
        return response_bytes(payload, result)

    monkeypatch.setattr(worker, "_run_owned_worker", fake_run)
    returned = worker.run_desirability_calculation(request)
    assert (
        returned.request_sha256
        == hashlib.sha256(canonical_json_bytes(original.worker_payload())).hexdigest()
    )


def test_cancellation_during_validation_does_not_return_success(monkeypatch, actual_calculation):
    request, result = actual_calculation
    cancel = threading.Event()
    monkeypatch.setattr(
        worker, "_run_owned_worker", lambda payload, **kwargs: response_bytes(payload, result)
    )
    monkeypatch.setattr(worker, "validate_calculation_result", lambda *args: cancel.set())
    with pytest.raises(BayesianOptimizationError, match="cancelled"):
        worker.run_desirability_calculation(request, cancel=cancel)


def test_input_size_busy_and_precancelled_do_not_start_worker(monkeypatch):
    request = DesirabilityCalculationRequest.model_validate(calculation_request())

    def forbidden(*args, **kwargs):
        pytest.fail("no process may start")

    monkeypatch.setattr(worker, "_run_owned_worker", forbidden)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(BayesianOptimizationError, match="cancelled"):
        worker.run_desirability_calculation(request, cancel=cancel)
    assert worker._ADMISSION.acquire(blocking=False)
    try:
        with pytest.raises(BayesianOptimizationError, match="worker_busy"):
            worker.run_desirability_calculation(request)
    finally:
        worker._ADMISSION.release()
    monkeypatch.setattr(worker, "MAX_INPUT_BYTES", 1)
    with pytest.raises(BayesianOptimizationError, match="input_too_large"):
        worker.run_desirability_calculation(request)


@pytest.mark.parametrize("case", ["timeout", "cancel", "oversized", "crash"])
def test_owned_process_cleanup_on_failure(monkeypatch, case):
    probe = (
        oversized_result
        if case == "oversized"
        else abruptly_exit
        if case == "crash"
        else slow_result
    )
    monkeypatch.setattr(worker, "_worker_entry", probe)
    before = {p.pid for p in multiprocessing.active_children()}
    cancel = threading.Event()
    timer = threading.Timer(0.25, cancel.set)
    if case == "cancel":
        timer.start()
    try:
        with pytest.raises(BayesianOptimizationError):
            worker._run_owned_worker(
                b"{}", timeout_ms=200 if case == "timeout" else 15_000, cancel=cancel
            )
    finally:
        if case == "cancel":
            timer.join()
    assert {p.pid for p in multiprocessing.active_children()} <= before
    assert not any(t.name == "bo-desirability-receiver" for t in threading.enumerate())


@pytest.mark.skipif(os.name == "nt", reason="POSIX stream frame; Windows uses message-mode pipes")
def test_partial_pipe_frame_cannot_disable_timeout(monkeypatch):
    monkeypatch.setattr(worker, "_worker_entry", partial_frame)
    before = {p.pid for p in multiprocessing.active_children()}
    with pytest.raises(BayesianOptimizationError, match="time_budget_exhausted"):
        worker._run_owned_worker(b"{}", timeout_ms=1500, cancel=None)
    assert {p.pid for p in multiprocessing.active_children()} <= before
    assert not any(t.name == "bo-desirability-receiver" for t in threading.enumerate())
