"""Deterministic DOE selection; no dependency on regression result contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from math import floor, isfinite, sqrt
from time import monotonic
from typing import Any, Literal

import numpy as np
from scipy import stats  # type: ignore[import-untyped]
from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

TIE_TOLERANCE = 1e-12
PRESS_LEVERAGE_TOLERANCE = 1e-10


class TermBlockSelectionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DoeSelectionOptions:
    method: Literal["none", "backward_elimination"] = "none"
    alpha_to_remove: float = 0.05
    hierarchy_policy: Literal["strong"] = "strong"
    saturated_start_policy: Literal["pool_smallest_adjusted_ss"] = "pool_smallest_adjusted_ss"
    display_step_details: bool = True


@dataclass(frozen=True)
class ModelSelectionTermBlock:
    block_id: str
    label: str
    factor_ids: tuple[str, ...]
    column_indices: tuple[int, ...]
    fixed: bool = False


@dataclass(frozen=True)
class _Fit:
    columns: tuple[int, ...]
    coefficients: np.ndarray
    sse: float
    residual_df: int
    metrics: dict[str, Any]


def pooling_target(term_count: int) -> int:
    return min(9, max(1, floor(term_count / 4 + 0.5)))


def term_is_removable(
    term: ModelSelectionTermBlock, active: Sequence[ModelSelectionTermBlock]
) -> bool:
    return not term.fixed and not any(
        set(term.factor_ids) < set(other.factor_ids) for other in active if not other.fixed
    )


def select_term_blocks(
    matrix: np.ndarray,
    response: np.ndarray,
    blocks: Sequence[ModelSelectionTermBlock],
    options: DoeSelectionOptions,
    *,
    time_budget_seconds: float = 60.0,
) -> tuple[list[int], dict[str, Any]]:
    _validate(matrix, response, blocks, options)
    deadline = monotonic() + time_budget_seconds
    with threadpool_limits(limits=1):
        return _select(matrix, response, blocks, options, deadline)


def _select(
    matrix: np.ndarray,
    response: np.ndarray,
    blocks: Sequence[ModelSelectionTermBlock],
    options: DoeSelectionOptions,
    deadline: float,
) -> tuple[list[int], dict[str, Any]]:
    active = list(blocks)
    initial_order = {block.block_id: index for index, block in enumerate(blocks)}
    initial_ids = [block.block_id for block in blocks if not block.fixed]
    current = _fit(matrix, response, active, deadline)
    saturated = current.residual_df == 0
    target = pooling_target(len(initial_ids)) if saturated and options.method != "none" else 0
    pooled: list[str] = []
    removed: list[str] = []
    steps = [_step(0, "initial_full_model", active, current)]
    stop_reason = "not_requested"

    if options.method != "none":
        # Pool by SS only. Inferential p-values do not exist at a saturated start.
        while len(pooled) < target or (target > 0 and current.residual_df < 1):
            candidates = _candidates(matrix, response, active, current, deadline)
            if not candidates:
                stop_reason = "insufficient_residual_df"
                break
            smallest = min(item[2] for item in candidates)
            tolerance = TIE_TOLERANCE * max(abs(smallest), float(np.var(response)))
            tied = [item for item in candidates if item[2] <= smallest + tolerance]
            block, reduced, adjusted_ss, removed_df = max(
                tied, key=lambda item: _tie_key(item[0], initial_order)
            )
            active = [item for item in active if item.block_id != block.block_id]
            current = reduced
            pooled.append(block.block_id)
            steps.append(
                _step(
                    len(steps), "initial_pooling", active, current, block, removed_df, adjusted_ss
                )
            )
        stop_reason = "all_terms_below_alpha"
        while True:
            if not any(not block.fixed for block in active):
                stop_reason = "intercept_only_or_structural_terms_only"
                break
            if current.residual_df <= 0:
                stop_reason = "insufficient_residual_df"
                break
            mse = current.sse / current.residual_df
            if mse <= np.finfo(float).eps ** 2 * float(np.mean(response**2)):
                stop_reason = "residual_variance_unavailable"
                break
            candidates = _candidates(matrix, response, active, current, deadline)
            if not candidates:
                stop_reason = "no_removable_terms_due_to_hierarchy"
                break
            evaluated = [
                (*item, float(stats.f.sf((item[2] / item[3]) / mse, item[3], current.residual_df)))
                for item in candidates
            ]
            largest = max(item[4] for item in evaluated)
            tied_p_values = [item for item in evaluated if largest - item[4] <= TIE_TOLERANCE]
            block, reduced, adjusted_ss, removed_df, p_value = max(
                tied_p_values, key=lambda item: _tie_key(item[0], initial_order)
            )
            if p_value <= options.alpha_to_remove:
                break
            active = [item for item in active if item.block_id != block.block_id]
            current = reduced
            removed.append(block.block_id)
            steps.append(
                _step(
                    len(steps),
                    "backward_elimination",
                    active,
                    current,
                    block,
                    removed_df,
                    adjusted_ss,
                    p_value,
                )
            )

    if steps:
        steps[-1]["stop_reason"] = stop_reason
    return list(current.columns), {
        "method": options.method,
        "alpha_to_remove": options.alpha_to_remove,
        "hierarchy_policy": options.hierarchy_policy,
        "saturated_start_policy": options.saturated_start_policy,
        "display_step_details": options.display_step_details,
        "tie_break_policy": "within_1e-12_higher_order_later_initial_order_stable_id",
        "initial_model_saturated": saturated,
        "initial_parameter_count": matrix.shape[1],
        "initial_residual_df": len(response) - matrix.shape[1],
        "target_pool_count": target,
        "initial_term_ids": initial_ids,
        "pooled_term_ids": pooled,
        "removed_term_ids": removed,
        "final_term_ids": [block.block_id for block in active if not block.fixed],
        "fixed_term_ids": [block.block_id for block in active if block.fixed],
        "stop_reason": stop_reason,
        "steps": steps if options.display_step_details and options.method != "none" else [],
        "post_selection_inference": "exploratory" if options.method != "none" else "not_selected",
    }


def _tie_key(block: ModelSelectionTermBlock, order: dict[str, int]) -> tuple[int, int, str]:
    return len(block.factor_ids), order[block.block_id], block.block_id


def _candidates(
    matrix: np.ndarray,
    response: np.ndarray,
    active: Sequence[ModelSelectionTermBlock],
    current: _Fit,
    deadline: float,
) -> list[tuple[ModelSelectionTermBlock, _Fit, float, int]]:
    candidates = []
    for block in active:
        if not term_is_removable(block, active):
            continue
        reduced = _fit(
            matrix, response, [item for item in active if item.block_id != block.block_id], deadline
        )
        removed_df = reduced.residual_df - current.residual_df
        if removed_df <= 0:
            raise TermBlockSelectionError("doe_factorial_selection_rank_failure")
        candidates.append((block, reduced, max(0.0, reduced.sse - current.sse), removed_df))
    return candidates


def _fit(
    matrix: np.ndarray,
    response: np.ndarray,
    blocks: Sequence[ModelSelectionTermBlock],
    deadline: float,
) -> _Fit:
    if monotonic() >= deadline:
        raise TermBlockSelectionError("doe_factorial_selection_time_budget_exceeded")
    columns = tuple(sorted(index for block in blocks for index in block.column_indices))
    selected = matrix[:, columns]
    coefficients, _, rank, _ = np.linalg.lstsq(selected, response, rcond=None)
    if rank != len(columns):
        raise TermBlockSelectionError("doe_factorial_selection_rank_failure")
    residuals = response - selected @ coefficients
    sse = max(0.0, float(residuals @ residuals))
    df = len(response) - int(rank)
    total_ss = float(np.sum((response - np.mean(response)) ** 2))
    q, _ = np.linalg.qr(selected, mode="reduced")
    leverage = np.sum(q * q, axis=1)
    press = (
        float(np.sum((residuals / (1.0 - leverage)) ** 2))
        if bool(np.all(1.0 - leverage > PRESS_LEVERAGE_TOLERANCE))
        else None
    )
    return _Fit(
        columns,
        coefficients,
        sse,
        df,
        {
            "sse": sse,
            "residual_df": df,
            "residual_standard_error": sqrt(sse / df) if df > 0 else None,
            "r_squared": 1.0 - sse / total_ss,
            "adjusted_r_squared": 1.0 - (sse / df) / (total_ss / (len(response) - 1))
            if df > 0
            else None,
            "press": press,
            "predicted_r_squared": 1.0 - press / total_ss if press is not None else None,
        },
    )


def _step(
    number: int,
    phase: str,
    blocks: Sequence[ModelSelectionTermBlock],
    fit: _Fit,
    removed: ModelSelectionTermBlock | None = None,
    removed_df: int | None = None,
    adjusted_ss: float | None = None,
    p_value: float | None = None,
) -> dict[str, Any]:
    return {
        "step": number,
        "phase": phase,
        "active_term_ids": [block.block_id for block in blocks],
        "removed_term_id": removed.block_id if removed else None,
        "removal_df": removed_df,
        "removal_adjusted_ss": adjusted_ss,
        "removal_p_value": p_value,
        "stop_reason": None,
        "coefficients": [
            {"column_index": index, "coefficient": float(value)}
            for index, value in zip(fit.columns, fit.coefficients, strict=True)
        ],
        **fit.metrics,
    }


def _validate(
    matrix: np.ndarray,
    response: np.ndarray,
    blocks: Sequence[ModelSelectionTermBlock],
    options: DoeSelectionOptions,
) -> None:
    if (
        options.method not in {"none", "backward_elimination"}
        or not isfinite(options.alpha_to_remove)
        or not 0 < options.alpha_to_remove < 1
        or options.hierarchy_policy != "strong"
        or options.saturated_start_policy != "pool_smallest_adjusted_ss"
    ):
        raise TermBlockSelectionError("doe_factorial_model_selection_options_invalid")
    if (
        matrix.ndim != 2
        or response.ndim != 1
        or matrix.shape[0] != len(response)
        or not 2 <= len(response) <= 256
        or not 1 <= matrix.shape[1] <= len(response)
        or not bool(np.isfinite(matrix).all())
        or not bool(np.isfinite(response).all())
        or float(np.var(response)) == 0
        or not bool(np.all(matrix[:, 0] == 1))
    ):
        raise TermBlockSelectionError("doe_factorial_selection_matrix_invalid")
    columns = [index for block in blocks for index in block.column_indices]
    if (
        sorted(columns) != list(range(matrix.shape[1]))
        or len({block.block_id for block in blocks}) != len(blocks)
        or not any(block.fixed and 0 in block.column_indices for block in blocks)
        or any(not block.column_indices for block in blocks)
    ):
        raise TermBlockSelectionError("doe_factorial_selection_blocks_invalid")
    factor_sets = {frozenset(block.factor_ids) for block in blocks if not block.fixed}
    for block in blocks:
        if block.fixed:
            continue
        if not block.factor_ids or len(set(block.factor_ids)) != len(block.factor_ids):
            raise TermBlockSelectionError("doe_factorial_selection_blocks_invalid")
        for order in range(1, len(block.factor_ids)):
            if any(
                frozenset(subset) not in factor_sets
                for subset in combinations(block.factor_ids, order)
            ):
                raise TermBlockSelectionError("doe_factorial_selection_hierarchy_invalid")
