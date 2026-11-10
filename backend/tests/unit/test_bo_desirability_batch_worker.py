import copy
import hashlib
import multiprocessing
import threading

import pytest
from test_bo_desirability_batch_core import batch_request
from test_bo_desirability_worker import response_bytes

from app.api.v1.schemas.bo_desirability_batch_calculation import DesirabilityBatchCalculationRequest
from app.services import bo_desirability_worker as worker
from app.services.analysis_run_execution import canonical_json_bytes
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability_batch_core import calculate_desirability_batch


@pytest.fixture(scope="module")
def calculation():
    request = DesirabilityBatchCalculationRequest.model_validate(batch_request())
    return request, calculate_desirability_batch(request.worker_payload())


def test_actual_spawn_batch_snapshot_hashes_and_no_surviving_child():
    request = DesirabilityBatchCalculationRequest.model_validate(batch_request())
    before = request.worker_payload()
    children = {p.pid for p in multiprocessing.active_children()}
    result = worker.run_desirability_batch_calculation(request)
    assert result.calculation.batch_size == len(result.calculation.items) == 2
    assert result.request_sha256 == hashlib.sha256(canonical_json_bytes(before)).hexdigest()
    assert (
        result.result_sha256
        == hashlib.sha256(
            canonical_json_bytes(result.calculation.model_dump(mode="json"))
        ).hexdigest()
    )
    assert before == request.worker_payload()
    assert {p.pid for p in multiprocessing.active_children()} <= children


def test_snapshot_mutation_and_shared_admission(calculation, monkeypatch):
    original, raw = calculation
    request = original.model_copy(deep=True)

    def fake(payload, **kwargs):
        request.batch_options.sample_count = 256
        return response_bytes(payload, raw)

    monkeypatch.setattr(worker, "_run_owned_worker", fake)
    returned = worker.run_desirability_batch_calculation(request)
    assert returned.calculation.batch_options.sample_count == 16
    assert worker._ADMISSION.acquire(blocking=False)
    try:
        with pytest.raises(BayesianOptimizationError, match="worker_busy"):
            worker.run_desirability_batch_calculation(original)
        with pytest.raises(BayesianOptimizationError, match="worker_busy"):
            worker.run_desirability_calculation(original.q1_request())
    finally:
        worker._ADMISSION.release()


@pytest.mark.parametrize("defect", ["partial", "version", "hash", "proof"])
def test_partial_or_mixed_worker_output_not_accepted(calculation, monkeypatch, defect):
    request, original = calculation
    raw = copy.deepcopy(original)
    if defect == "partial":
        raw["items"].pop()
    elif defect == "version":
        raw["schema_version"] = 4
    elif defect == "proof":
        raw["items"][1]["planning"]["proof"]["thresholds"][0] += 0.01
    monkeypatch.setattr(
        worker,
        "_run_owned_worker",
        lambda payload, **kwargs: response_bytes(
            b"different" if defect == "hash" else payload, raw
        ),
    )
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        worker.run_desirability_batch_calculation(request)


def test_preflight_and_precancel_never_spawn(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("must not spawn")

    monkeypatch.setattr(worker, "_run_owned_worker", forbidden)
    raw = batch_request(8)
    raw["batch_options"]["sample_count"] = 256
    with pytest.raises(BayesianOptimizationError, match="batch_budget_exhausted"):
        worker.run_desirability_batch_calculation(
            DesirabilityBatchCalculationRequest.model_validate(raw)
        )
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(BayesianOptimizationError, match="cancelled"):
        worker.run_desirability_batch_calculation(
            DesirabilityBatchCalculationRequest.model_validate(batch_request()), cancel=cancel
        )


@pytest.mark.parametrize(
    "code",
    [
        "bayesian_desirability_batch_budget_exhausted",
        "bayesian_desirability_covariance_precision_unsupported",
        "bayesian_desirability_raw_variance_precision_unsupported",
    ],
)
def test_worker_keeps_new_stable_failure_codes(monkeypatch, code):
    monkeypatch.setattr(
        worker,
        "_run_owned_worker",
        lambda *args, **kwargs: canonical_json_bytes({"status": "error", "code": code}),
    )
    with pytest.raises(BayesianOptimizationError) as error:
        worker.run_desirability_batch_calculation(
            DesirabilityBatchCalculationRequest.model_validate(batch_request())
        )
    assert error.value.code == code
