"""Owned, bounded spawn execution for the internal desirability calculation.

No study, trial, workspace or artifact is created by this service. The public
q1 review uses schema4; schema5 batch calculation remains an internal boundary.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Any

from pydantic import ValidationError

from app.api.v1.schemas.bo_curve_calculation import (
    DesirabilityCurveCalculationRequest,
    DesirabilityCurveCalculationResult,
)
from app.api.v1.schemas.bo_desirability_batch_calculation import (
    DesirabilityBatchCalculationRequest,
    DesirabilityBatchCalculationResult,
)
from app.api.v1.schemas.bo_fit_quality import (
    DesirabilityFitCalculationRequest,
    DesirabilityFitCalculationResult,
)
from app.services.analysis_run_execution import canonical_json_bytes
from app.services.bo_desirability_batch_contract import validate_batch_calculation_result
from app.services.bo_desirability_contract import (
    DesirabilityCalculationRequest,
    DesirabilityCalculationResult,
    validate_calculation_result,
)
from app.statistics.bayesian_optimization import BayesianOptimizationError

MAX_INPUT_BYTES = 512 * 1024
MAX_RESULT_BYTES = 4 * 1024 * 1024
_ADMISSION = threading.BoundedSemaphore(1)
_ALLOWED_ERRORS = frozenset(
    {
        "bayesian_desirability_input_invalid",
        "bayesian_desirability_batch_input_invalid",
        "bayesian_desirability_batch_budget_exhausted",
        "bayesian_desirability_covariance_precision_unsupported",
        "bayesian_desirability_raw_variance_precision_unsupported",
        "bayesian_desirability_response_mapping_invalid",
        "bayesian_desirability_model_contract_invalid",
        "bayesian_desirability_numeric_invalid",
        "bayesian_desirability_moments_invalid",
        "bayesian_desirability_quadrature_not_converged",
        "bayesian_desirability_integration_budget_exceeded",
        "bayesian_desirability_weight_precision_unsupported",
        "bayesian_desirability_beta_precision_unsupported",
        "bayesian_desirability_result_invalid",
        "bayesian_desirability_result_too_large",
        "bayesian_optimization_budget_exhausted",
        "bayesian_optimization_time_budget_exhausted",
        "bayesian_optimization_no_feasible_candidate",
        "bayesian_optimization_duplicate_candidate",
        "bayesian_optimization_factor_space_invalid",
        "bayesian_optimization_constraint_invalid",
        "bayesian_optimization_invalid_options",
        "bayesian_optimization_search_options_invalid",
        "bayesian_optimization_acquisition_invalid",
        "bayesian_optimization_surrogate_fit_failed",
        "bayesian_optimization_constant_objective",
        "bayesian_optimization_history_incomplete",
        "bayesian_unique_conditions_insufficient",
        "bayesian_observation_limit_reached",
        "bayesian_observation_identity_invalid",
        "bayesian_observation_coordinates_invalid",
        "bayesian_observation_factors_invalid",
        "bayesian_observation_group_invalid",
        "bayesian_observation_mode_invalid",
        "bayesian_observation_value_invalid",
        "bayesian_observations_invalid",
        "bayesian_observation_statistics_nonfinite",
        "bayesian_nearby_options_invalid",
        "bayesian_surrogate_noise_invalid",
        "bayesian_surrogate_policy_invalid",
        "bayesian_surrogate_prediction_invalid",
        "bayesian_surrogate_kernel_invalid",
        "bayesian_surrogate_covariance_invalid",
        "bayesian_fit_policy_invalid",
        "bayesian_target_curve_precision_unsupported",
    }
)


@dataclass(frozen=True)
class DesirabilityWorkerCalculation:
    request_sha256: str
    result_sha256: str
    calculation: DesirabilityCalculationResult


@dataclass(frozen=True)
class DesirabilityBatchWorkerCalculation:
    request_sha256: str
    result_sha256: str
    calculation: (
        DesirabilityBatchCalculationResult
        | DesirabilityFitCalculationResult
        | DesirabilityCurveCalculationResult
    )


def _require_current_numerical_policy(
    rows: Any, *, error_code: str = "bayesian_desirability_result_invalid"
) -> None:
    from app.statistics.bo_beta_policy import BETA_NUMERICAL_POLICY

    if not isinstance(rows, list):
        raise BayesianOptimizationError(error_code)
    for row in rows:
        if not isinstance(row, dict):
            raise BayesianOptimizationError(error_code)
        acquisition = row.get("acquisition")
        if acquisition is not None and (
            not isinstance(acquisition, dict)
            or acquisition.get("numerical_policy") != BETA_NUMERICAL_POLICY
        ):
            raise BayesianOptimizationError(error_code)
        planning = row.get("planning")
        if planning is not None:
            sampler = planning.get("sampler") if isinstance(planning, dict) else None
            if (
                not isinstance(sampler, dict)
                or sampler.get("numerical_policy") != BETA_NUMERICAL_POLICY
            ):
                raise BayesianOptimizationError(error_code)


def _duplicate_free_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("nonfinite JSON number")


def _read_json(data: bytes) -> Any:
    return json.loads(
        data, object_pairs_hook=_duplicate_free_object, parse_constant=_invalid_constant
    )


def _worker_entry(output: Connection, payload_bytes: bytes) -> None:
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    from app.statistics.bo_desirability_batch_core import calculate_desirability_batch
    from app.statistics.bo_desirability_core import calculate_desirability_recommendation

    try:
        payload = _read_json(payload_bytes)
        with threadpool_limits(limits=1):
            result = (
                calculate_desirability_batch(payload)
                if isinstance(payload, dict) and payload.get("schema_version") in {5, 6, 7}
                else calculate_desirability_recommendation(payload)
            )
        message = {
            "status": "ok",
            "request_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "result": result,
        }
    except BayesianOptimizationError as exc:
        message = {
            "status": "error",
            "code": exc.code
            if exc.code in _ALLOWED_ERRORS
            else "bayesian_optimization_surrogate_fit_failed",
        }
    except Exception:
        message = {"status": "error", "code": "bayesian_optimization_surrogate_fit_failed"}
    try:
        data = canonical_json_bytes(message)
        if len(data) > MAX_RESULT_BYTES:
            data = canonical_json_bytes(
                {"status": "error", "code": "bayesian_desirability_result_too_large"}
            )
        output.send_bytes(data)
    finally:
        output.close()


def _run_owned_worker(
    payload_bytes: bytes,
    *,
    timeout_ms: int,
    cancel: threading.Event | None,
    entrypoint: Callable[[Connection, bytes], None] | None = None,
    max_result_bytes: int = MAX_RESULT_BYTES,
) -> bytes:
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=entrypoint or _worker_entry, args=(send, payload_bytes))
    deadline = time.monotonic() + timeout_ms / 1000
    received: list[bytes | Exception] = []
    complete = threading.Event()

    def read_message() -> None:
        try:
            received.append(receive.recv_bytes(max_result_bytes))
        except Exception as exc:
            received.append(exc)
        finally:
            complete.set()

    # A pipe can become readable before an entire frame arrives. Keep the
    # deadline watcher separate from recv_bytes, including partial-frame hangs.
    reader = threading.Thread(target=read_message, name="bo-desirability-receiver", daemon=True)
    reader_started = False
    try:
        process.start()
        send.close()
        reader.start()
        reader_started = True
        while True:
            if cancel is not None and cancel.is_set():
                raise BayesianOptimizationError("bayesian_desirability_cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")
            if complete.wait(min(0.05, remaining)):
                data = received[0]
                if isinstance(data, Exception):
                    raise BayesianOptimizationError(
                        "bayesian_desirability_result_invalid"
                    ) from None
                process.join(timeout=2)
                if process.is_alive() or process.exitcode != 0:
                    raise BayesianOptimizationError("bayesian_desirability_worker_failed")
                return data
    finally:
        send.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
            if not process.is_alive():
                process.close()
        # Windows overlapped reads may still wait after an early child startup
        # termination. Closing our read handle cancels that pending I/O first.
        receive.close()
        if reader_started:
            reader.join(timeout=5)
        if reader_started and reader.is_alive():
            raise BayesianOptimizationError("bayesian_desirability_worker_cleanup_failed")


def run_desirability_calculation(
    request: DesirabilityCalculationRequest, *, cancel: threading.Event | None = None
) -> DesirabilityWorkerCalculation:
    result = _run_calculation(request, cancel=cancel)
    assert isinstance(result, DesirabilityWorkerCalculation)
    return result


def run_desirability_batch_calculation(
    request: DesirabilityBatchCalculationRequest
    | DesirabilityFitCalculationRequest
    | DesirabilityCurveCalculationRequest,
    *,
    cancel: threading.Event | None = None,
) -> DesirabilityBatchWorkerCalculation:
    result = _run_calculation(request, cancel=cancel)
    assert isinstance(result, DesirabilityBatchWorkerCalculation)
    return result


def _run_calculation(
    request: DesirabilityCalculationRequest
    | DesirabilityBatchCalculationRequest
    | DesirabilityFitCalculationRequest
    | DesirabilityCurveCalculationRequest,
    *,
    cancel: threading.Event | None,
) -> DesirabilityWorkerCalculation | DesirabilityBatchWorkerCalculation:
    if not _ADMISSION.acquire(blocking=False):
        raise BayesianOptimizationError("bayesian_desirability_worker_busy")
    try:
        if cancel is not None and cancel.is_set():
            raise BayesianOptimizationError("bayesian_desirability_cancelled")
        # Snapshot mutable caller containers before spawn and validate the snapshot,
        # not whatever the caller happens to hold when the worker finishes.
        payload_bytes = canonical_json_bytes(request.worker_payload())
        if len(payload_bytes) > MAX_INPUT_BYTES:
            raise BayesianOptimizationError("bayesian_desirability_input_too_large")
        try:
            snapshot = type(request).model_validate_json(payload_bytes, strict=True)
        except ValidationError:
            raise BayesianOptimizationError("bayesian_desirability_input_invalid") from None
        request_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        if isinstance(
            snapshot,
            DesirabilityBatchCalculationRequest
            | DesirabilityFitCalculationRequest
            | DesirabilityCurveCalculationRequest,
        ):
            from app.statistics.bo_desirability_batch_core import batch_preflight

            batch_preflight(snapshot)
        data = _run_owned_worker(
            payload_bytes, timeout_ms=snapshot.search.time_budget_ms + 20_000, cancel=cancel
        )
        if cancel is not None and cancel.is_set():
            raise BayesianOptimizationError("bayesian_desirability_cancelled")
        try:
            message = _read_json(data)
            if not isinstance(message, dict):
                raise ValueError
            if message.get("status") == "error":
                code = message.get("code")
                raise BayesianOptimizationError(
                    code
                    if isinstance(code, str) and code in _ALLOWED_ERRORS
                    else "bayesian_optimization_surrogate_fit_failed"
                )
            if (
                set(message) != {"status", "request_sha256", "result"}
                or message["status"] != "ok"
                or message["request_sha256"] != request_sha256
            ):
                raise ValueError
            result_bytes = canonical_json_bytes(message["result"])
            _require_current_numerical_policy(message["result"]["items"])
            returned: DesirabilityWorkerCalculation | DesirabilityBatchWorkerCalculation
            result_sha256 = hashlib.sha256(result_bytes).hexdigest()
            if isinstance(
                snapshot,
                DesirabilityBatchCalculationRequest
                | DesirabilityFitCalculationRequest
                | DesirabilityCurveCalculationRequest,
            ):
                batch = (
                    DesirabilityCurveCalculationResult
                    if snapshot.schema_version == 7
                    else DesirabilityFitCalculationResult
                    if snapshot.schema_version == 6
                    else DesirabilityBatchCalculationResult
                ).model_validate_json(result_bytes, strict=True)
                validate_batch_calculation_result(snapshot, batch)
                returned = DesirabilityBatchWorkerCalculation(request_sha256, result_sha256, batch)
            else:
                result = DesirabilityCalculationResult.model_validate_json(
                    result_bytes, strict=True
                )
                validate_calculation_result(snapshot, result)
                returned = DesirabilityWorkerCalculation(request_sha256, result_sha256, result)
        except BayesianOptimizationError:
            raise
        except (ValueError, TypeError, KeyError, OverflowError):
            raise BayesianOptimizationError("bayesian_desirability_result_invalid") from None
        if cancel is not None and cancel.is_set():
            raise BayesianOptimizationError("bayesian_desirability_cancelled")
        return returned
    finally:
        _ADMISSION.release()
