from __future__ import annotations

import json
import multiprocessing
from multiprocessing.connection import Connection
from threading import BoundedSemaphore
from typing import Any

from app.services.analysis_run_execution import RowSnapshotArtifact, iter_rows_for_snapshot
from app.services.dataset_rows import DatasetRowsContext
from app.statistics.linear_model import LinearModelColumn, LinearModelError

_WORKER_SLOT = BoundedSemaphore(1)


def _worker_entry(
    output: Connection,
    context: DatasetRowsContext,
    snapshot: RowSnapshotArtifact,
    response: LinearModelColumn,
    predictors: list[LinearModelColumn],
    options: dict[str, Any],
    quadratic_terms: list[str],
    interaction_terms: list[tuple[str, str]],
) -> None:
    try:
        from app.statistics.regularized_linear_model import (
            RegularizationConfig,
            calculate_regularized_linear_model,
        )

        config = RegularizationConfig(
            estimator=options["estimator"],
            **options["regularization"],
            fixed_alpha=options.get("fixed_alpha"),
            l1_ratio_selection=options.get("l1_ratio_selection", "automatic_cv"),
            fixed_l1_ratio=options.get("fixed_l1_ratio"),
            l1_ratio_candidates=tuple(options.get("l1_ratio_candidates", (0.5,))),
        )
        result = calculate_regularized_linear_model(
            iter_rows_for_snapshot(context, snapshot),
            response,
            predictors,
            config=config,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            quadratic_terms=quadratic_terms,
            interaction_terms=interaction_terms,
        )
        payload: dict[str, Any] = {"result": result}
    except LinearModelError as exc:
        payload = {"error": exc.code}
    except Exception:
        # The process boundary must never expose raw rows or solver exceptions.
        payload = {"error": "regularized_model_fit_failed"}
    try:
        output.send_bytes(json.dumps(payload, allow_nan=False).encode("utf-8"))
    finally:
        output.close()


def run_regularized_worker(
    context: DatasetRowsContext,
    snapshot: RowSnapshotArtifact,
    response: LinearModelColumn,
    predictors: list[LinearModelColumn],
    options: dict[str, Any],
    quadratic_terms: list[str],
    interaction_terms: list[tuple[str, str]],
) -> dict[str, Any]:
    if not _WORKER_SLOT.acquire(blocking=False):
        raise LinearModelError("regularized_model_worker_busy")
    runtime = multiprocessing.get_context("spawn")
    incoming, outgoing = runtime.Pipe(duplex=False)
    process = runtime.Process(
        target=_worker_entry,
        args=(
            outgoing,
            context,
            snapshot,
            response,
            predictors,
            options,
            quadratic_terms,
            interaction_terms,
        ),
    )
    try:
        process.start()
        outgoing.close()
        timeout = float(options["regularization"]["time_budget_seconds"]) + 20
        if not incoming.poll(timeout):
            raise LinearModelError("regularized_model_time_budget_exhausted")
        try:
            payload = json.loads(incoming.recv_bytes(maxlength=64 * 1024 * 1024))
        except (EOFError, OSError, ValueError) as exc:
            raise LinearModelError("regularized_model_fit_failed") from exc
        if "error" in payload:
            raise LinearModelError(payload["error"])
        result = payload.get("result")
        if not isinstance(result, dict):
            raise LinearModelError("regularized_model_fit_failed")
        return result
    finally:
        incoming.close()
        outgoing.close()
        if process.pid is not None:
            process.join(timeout=1)
            if process.is_alive():
                process.terminate()
                process.join()
            process.close()
        _WORKER_SLOT.release()
