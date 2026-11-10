import json
import threading

import pytest

from app.services import bo_desirability_worker as execution
from app.services import bo_planning_worker as worker
from app.statistics.bayesian_optimization import BayesianOptimizationError


class _Output:
    def __init__(self):
        self.data = None
        self.closed = False

    def send_bytes(self, data):
        self.data = data

    def close(self):
        self.closed = True


def _in_process(encoded, *, entrypoint, timeout_ms, cancel, max_result_bytes):
    output = _Output()
    entrypoint(output, encoded)
    assert output.closed and len(output.data) <= max_result_bytes
    assert timeout_ms == 21_000 and cancel is None
    return output.data


@pytest.mark.parametrize("operation", ["evaluate", "selection", "candidates", "fit"])
def test_validation_is_inside_admission_and_original_worker_deadline(monkeypatch, operation):
    from app.services import bo_planning_contract as contract
    from app.statistics import bo_planning_model as model

    payload = {"snapshot": {}, "points": [], "eligibility_excluded_normalized": []}
    result = {"calculation_request": payload}
    events = []

    def calculate(kind, received):
        assert kind == operation and received == payload
        events.append("calculate")
        return result

    def validate(*args, **kwargs):
        assert not execution._ADMISSION.acquire(blocking=False)
        if operation == "fit":
            deadline = kwargs["budget"].deadline
        elif operation == "candidates":
            deadline = None
        else:
            deadline = kwargs["deadline"]
        if deadline is not None:
            assert deadline == 101.0
        events.append("validate")

    monkeypatch.setattr(worker, "_calculate", calculate)
    monkeypatch.setattr(worker.time, "perf_counter", lambda: 100.0)
    monkeypatch.setattr(execution, "_run_owned_worker", _in_process)
    monkeypatch.setattr(model, "restore_planning_model", validate)
    monkeypatch.setattr(contract, "validate_planning_evaluation", validate)
    monkeypatch.setattr(contract, "validate_planning_selection", validate)
    monkeypatch.setattr(contract, "validate_candidate_generation", validate)
    assert worker.run_planning_operation(operation, payload, time_budget_ms=1000) == result
    assert events == ["calculate", "validate"]
    assert execution._ADMISSION.acquire(blocking=False)
    execution._ADMISSION.release()


def test_worker_does_not_reset_expired_budget_before_validation(monkeypatch):
    from app.services import bo_planning_contract as contract

    clock = [100.0]

    def calculate(*args):
        clock[0] = 102.0
        return []

    def validate(*args, deadline):
        assert deadline == 101.0
        raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")

    monkeypatch.setattr(worker.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(worker, "_calculate", calculate)
    monkeypatch.setattr(contract, "validate_planning_evaluation", validate)
    monkeypatch.setattr(execution, "_run_owned_worker", _in_process)
    with pytest.raises(BayesianOptimizationError) as error:
        worker.run_planning_operation(
            "evaluate",
            {"snapshot": {}, "points": [], "eligibility_excluded_normalized": []},
            time_budget_ms=1000,
        )
    assert error.value.code == "bayesian_optimization_time_budget_exhausted"
    assert execution._ADMISSION.acquire(blocking=False)
    execution._ADMISSION.release()


def test_invalid_return_envelope_never_reaches_caller(monkeypatch):
    monkeypatch.setattr(
        execution,
        "_run_owned_worker",
        lambda *args, **kwargs: json.dumps(
            {"status": "ok", "request_sha256": "0" * 64, "result": {}}
        ).encode(),
    )
    with pytest.raises(BayesianOptimizationError) as error:
        worker.run_planning_operation("fit", {}, time_budget_ms=1000)
    assert error.value.code == "bayesian_planning_snapshot_invalid"


def test_cancelled_request_does_not_start_process(monkeypatch):
    cancel = threading.Event()
    cancel.set()
    monkeypatch.setattr(execution, "_run_owned_worker", lambda *args, **kwargs: pytest.fail())
    with pytest.raises(BayesianOptimizationError) as error:
        worker.run_planning_operation("fit", {}, time_budget_ms=1000, cancel=cancel)
    assert error.value.code == "bayesian_desirability_cancelled"
