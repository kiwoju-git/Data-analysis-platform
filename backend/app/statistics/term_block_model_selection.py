"""Deterministic DOE selection; no dependency on regression result contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
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
class DoeTermPolicy:
    term_id: str
    disposition: Literal["candidate", "forced", "excluded"]


@dataclass(frozen=True)
class DoeSelectionOptions:
    method: Literal["none", "backward_elimination"] = "none"
    alpha_to_remove: float = 0.05
    hierarchy_policy: Literal["strong"] = "strong"
    saturated_start_policy: Literal["pool_smallest_adjusted_ss"] = "pool_smallest_adjusted_ss"
    display_step_details: bool = True
    term_policies: tuple[DoeTermPolicy, ...] = ()


def selection_options_from_payload(value: dict[str, Any]) -> DoeSelectionOptions:
    return DoeSelectionOptions(
        **{
            **value,
            "term_policies": tuple(
                DoeTermPolicy(**policy) for policy in value.get("term_policies", [])
            ),
        }
    )


@dataclass(frozen=True)
class ModelSelectionTermBlock:
    block_id: str
    label: str
    factor_ids: tuple[str, ...]
    column_indices: tuple[int, ...]
    fixed: bool = False
    hierarchy_role: Literal["factorial_term", "independent_term", "structural_term"] = (
        "factorial_term"
    )
    kind: str = "main_effect"
    coefficient_labels: tuple[str, ...] = ()
    default_disposition: Literal["candidate", "forced", "excluded"] = "candidate"


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
    if term.fixed or term.hierarchy_role == "structural_term":
        return False
    if term.hierarchy_role == "independent_term":
        return True
    return not any(
        set(term.factor_ids) < set(other.factor_ids)
        for other in active
        if other.hierarchy_role == "factorial_term"
    )


def term_catalog(
    blocks: Sequence[ModelSelectionTermBlock], matrix: np.ndarray | None = None
) -> list[dict[str, Any]]:
    nonestimable: set[int] = set()
    if matrix is not None:
        with threadpool_limits(limits=1):
            _, singular, right = np.linalg.svd(matrix, full_matrices=True)
        tolerance = singular[0] * max(matrix.shape) * np.finfo(float).eps
        rank = int(np.sum(singular > tolerance))
        if rank < matrix.shape[1]:
            nonestimable = set(np.flatnonzero(np.any(np.abs(right[rank:]) > 1e-8, axis=0)))
    return [
        {
            "term_id": block.block_id,
            "label": block.label,
            "kind": block.kind,
            "hierarchy_role": block.hierarchy_role,
            "order": len(block.factor_ids) if block.hierarchy_role == "factorial_term" else 0,
            "factor_ids": list(block.factor_ids),
            "hierarchy_dependencies": [
                parent.block_id
                for parent in blocks
                if block.hierarchy_role == parent.hierarchy_role == "factorial_term"
                and set(parent.factor_ids) < set(block.factor_ids)
            ],
            "default_disposition": "forced" if block.fixed else block.default_disposition,
            "df": len(block.column_indices),
            "estimable": not nonestimable.intersection(block.column_indices),
        }
        for block in blocks
    ]


def _resolve_policies(
    blocks: Sequence[ModelSelectionTermBlock], options: DoeSelectionOptions
) -> list[ModelSelectionTermBlock]:
    policies = {policy.term_id: policy.disposition for policy in options.term_policies}
    if (
        len(policies) != len(options.term_policies)
        or not set(policies).issubset({block.block_id for block in blocks})
        or not set(policies.values()).issubset({"candidate", "forced", "excluded"})
    ):
        raise TermBlockSelectionError("doe_factorial_term_policy_invalid")
    active = []
    for block in blocks:
        disposition = policies.get(
            block.block_id, "forced" if block.fixed else block.default_disposition
        )
        if block.fixed and disposition != "forced":
            raise TermBlockSelectionError("doe_factorial_structural_term_policy_invalid")
        if disposition != "excluded":
            active.append(replace(block, fixed=disposition == "forced"))
    factor_sets = {
        frozenset(block.factor_ids)
        for block in active
        if block.hierarchy_role == "factorial_term" and block.factor_ids
    }
    for block in active:
        if block.hierarchy_role != "factorial_term":
            continue
        for order in range(1, len(block.factor_ids)):
            if any(
                frozenset(subset) not in factor_sets
                for subset in combinations(block.factor_ids, order)
            ):
                raise TermBlockSelectionError("doe_factorial_selection_hierarchy_invalid")
    return active


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
    active = _resolve_policies(blocks, options)
    initial_order = {block.block_id: index for index, block in enumerate(blocks)}
    initial_ids = [block.block_id for block in active if _nonstructural(block)]
    candidate_ids = [block.block_id for block in active if not block.fixed]
    included_ids = {block.block_id for block in active}
    excluded_ids = [block.block_id for block in blocks if block.block_id not in included_ids]
    current = _fit(matrix, response, active, deadline)
    initial_fit = current
    saturated = current.residual_df == 0
    target = pooling_target(len(candidate_ids)) if saturated and options.method != "none" else 0
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
    reference_mse = (
        initial_fit.sse / initial_fit.residual_df
        if initial_fit.residual_df > 0
        and initial_fit.sse > np.finfo(float).eps * float(response @ response)
        else None
    )
    for step in steps:
        if options.display_step_details and options.method != "none":
            step_blocks = [block for block in blocks if block.block_id in step["active_term_ids"]]
            forced = {block.block_id for block in active if block.fixed}
            step_blocks = [replace(block, fixed=block.block_id in forced) for block in step_blocks]
            detailed_fit = _fit(matrix, response, step_blocks, deadline, term_details=True)
            step["term_statistics"] = detailed_fit.metrics["term_statistics"]
            if step["removed_term_id"] is not None:
                removed_block = next(
                    block for block in blocks if block.block_id == step["removed_term_id"]
                )
                step["term_statistics"].append(
                    {
                        "term_id": removed_block.block_id,
                        "label": removed_block.label,
                        "status": "removed_this_step",
                        "coefficient": None,
                        "df": len(removed_block.column_indices),
                        "p_value": None,
                        "coefficients": [],
                    }
                )
        step["mallows_cp"] = (
            step["sse"] / reference_mse - (len(response) - 2 * len(step["coefficients"]))
            if reference_mse is not None
            else None
        )
        step["mallows_cp_unavailable_reason"] = (
            None if reference_mse is not None else "reference_full_model_mse_unavailable"
        )
    return list(current.columns), {
        "method": options.method,
        "alpha_to_remove": options.alpha_to_remove,
        "hierarchy_policy": options.hierarchy_policy,
        "saturated_start_policy": options.saturated_start_policy,
        "display_step_details": options.display_step_details,
        "term_policies": [asdict(policy) for policy in options.term_policies],
        "term_catalog": term_catalog(blocks),
        "candidate_term_ids": candidate_ids,
        "initially_excluded_term_ids": excluded_ids,
        "tie_break_policy": "within_1e-12_interaction_independent_main_later_order_stable_id",
        "initial_model_saturated": saturated,
        "initial_parameter_count": len(initial_fit.columns),
        "initial_residual_df": initial_fit.residual_df,
        "target_pool_count": target,
        "initial_term_ids": initial_ids,
        "pooled_term_ids": pooled,
        "removed_term_ids": removed,
        "final_term_ids": [block.block_id for block in active if _nonstructural(block)],
        "fixed_term_ids": [block.block_id for block in active if block.fixed],
        "stop_reason": stop_reason,
        "steps": steps if options.display_step_details and options.method != "none" else [],
        "post_selection_inference": "exploratory" if options.method != "none" else "not_selected",
    }


def _nonstructural(block: ModelSelectionTermBlock) -> bool:
    return block.hierarchy_role == "independent_term" or bool(block.factor_ids)


def _tie_key(block: ModelSelectionTermBlock, order: dict[str, int]) -> tuple[int, int, int, str]:
    priority = (
        2 if len(block.factor_ids) > 1 else (1 if block.hierarchy_role == "independent_term" else 0)
    )
    return priority, len(block.factor_ids), order[block.block_id], block.block_id


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
    *,
    term_details: bool = False,
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
    term_statistics = []
    if term_details and df > 0 and sse > 0:
        covariance = np.linalg.inv(selected.T @ selected) * (sse / df)
    else:
        covariance = None
    positions = {column: index for index, column in enumerate(columns)}
    for block in blocks if term_details else []:
        indexes = [positions[column] for column in block.column_indices]
        beta = coefficients[indexes]
        p_value = None
        if covariance is not None and 0 not in block.column_indices:
            variance = covariance[np.ix_(indexes, indexes)]
            statistic = float(beta @ np.linalg.solve(variance, beta)) / len(indexes)
            p_value = float(stats.f.sf(statistic, len(indexes), df))
        term_statistics.append(
            {
                "term_id": block.block_id,
                "label": block.label,
                "status": "forced"
                if block.fixed
                else (
                    "retained_for_hierarchy" if not term_is_removable(block, blocks) else "active"
                ),
                "coefficient": float(beta[0]) if len(indexes) == 1 else None,
                "df": len(indexes),
                "p_value": p_value,
                "coefficients": [
                    {
                        "column_index": columns[index],
                        "coefficient": float(coefficients[index]),
                        "label": block.coefficient_labels[offset]
                        if block.coefficient_labels
                        else block.label,
                        "p_value": float(
                            2
                            * stats.t.sf(
                                abs(coefficients[index] / sqrt(covariance[index, index])), df
                            )
                        )
                        if covariance is not None and covariance[index, index] > 0
                        else None,
                    }
                    for offset, index in enumerate(indexes)
                ],
            }
        )
    return _Fit(
        columns,
        coefficients,
        sse,
        df,
        {
            "term_statistics": term_statistics,
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
        "removed_term_label": removed.label if removed else None,
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
        or not 1 <= matrix.shape[1] <= 512
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
    for block in blocks:
        if block.fixed or block.hierarchy_role != "factorial_term":
            continue
        if not block.factor_ids or len(set(block.factor_ids)) != len(block.factor_ids):
            raise TermBlockSelectionError("doe_factorial_selection_blocks_invalid")
