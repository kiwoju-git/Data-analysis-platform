"""Response-independent representative basis for bounded regular fractions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

from app.statistics.doe_matrix_rank import column_scaled_matrix
from app.statistics.term_block_model_selection import (
    DoeSelectionOptions,
    ModelSelectionTermBlock,
    TermBlockSelectionError,
    resolve_term_policies,
)


@dataclass(frozen=True)
class FractionalEstimability:
    columns: tuple[int, ...]
    retained_term_ids: tuple[str, ...]
    initially_excluded_term_ids: tuple[str, ...]
    exclusions: tuple[dict[str, Any], ...]
    requested_parameter_count: int
    rank: int
    residual_df: int
    rank_tolerance: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "policy": "response_independent_structural_forced_main_canonical_interaction",
            "requested_parameter_count": self.requested_parameter_count,
            "estimable_parameter_count": len(self.columns),
            "rank": self.rank,
            "expected_residual_df": self.residual_df,
            "saturated": self.residual_df == 0,
            "representative_term_ids": list(self.retained_term_ids),
            "initially_excluded_term_ids": list(self.initially_excluded_term_ids),
            "exclusions": list(self.exclusions),
            "rank_tolerance": self.rank_tolerance,
            "rank_scaling": "unit_column_norm_fixed_full_matrix_tolerance",
        }


def fractional_estimability(
    matrix: np.ndarray,
    blocks: Sequence[ModelSelectionTermBlock],
    options: DoeSelectionOptions,
) -> FractionalEstimability:
    """Never inspect y or rank candidates by an observed effect/p-value."""
    if (
        matrix.ndim != 2
        or not 1 <= matrix.shape[0] <= 256
        or not 1 <= matrix.shape[1] <= 128
        or not np.isfinite(matrix).all()
        or sorted(index for block in blocks for index in block.column_indices)
        != list(range(matrix.shape[1]))
    ):
        raise TermBlockSelectionError("doe_fractional_estimability_matrix_invalid")
    active = resolve_term_policies(blocks, options)
    active_ids = {block.block_id for block in active}
    excluded = tuple(block.block_id for block in blocks if block.block_id not in active_ids)
    order = {block.block_id: index for index, block in enumerate(blocks)}
    required = {block.block_id for block in active if block.fixed}
    for block in active:
        if block.fixed and block.hierarchy_role == "factorial_term":
            required.update(
                parent.block_id
                for parent in active
                if parent.hierarchy_role == "factorial_term"
                and set(parent.factor_ids) < set(block.factor_ids)
            )
    prioritized = sorted(
        active,
        key=lambda block: (
            0
            if block.hierarchy_role == "structural_term"
            else 1
            if block.block_id in required
            else 2
            if block.kind == "main_effect"
            else 3,
            len(block.factor_ids),
            order[block.block_id],
        ),
    )
    normalized, _ = column_scaled_matrix(matrix)
    with threadpool_limits(limits=1):
        singular = np.linalg.svd(normalized, compute_uv=False)
        tolerance = float(max(matrix.shape) * np.finfo(float).eps * singular[0])

        def rank(columns: Sequence[int]) -> int:
            if not columns:
                return 0
            return int(np.sum(np.linalg.svd(normalized[:, columns], compute_uv=False) > tolerance))

        columns: list[int] = []
        retained: list[ModelSelectionTermBlock] = []
        exclusions: list[dict[str, Any]] = []
        for block in prioritized:
            proposed = [*columns, *block.column_indices]
            if rank(proposed) == len(proposed):
                parents = {
                    parent.block_id
                    for parent in active
                    if parent.hierarchy_role == block.hierarchy_role == "factorial_term"
                    and set(parent.factor_ids) < set(block.factor_ids)
                }
                if parents.issubset({item.block_id for item in retained}):
                    columns = proposed
                    retained.append(block)
                    continue
                reason = "hierarchy_dependency_unavailable"
                representative = None
                sign = None
            else:
                representative, sign = _signed_duplicate(matrix, block, retained)
                structural_columns = [
                    index
                    for item in retained
                    if item.hierarchy_role == "structural_term"
                    for index in item.column_indices
                ]
                structurally_confounded = bool(structural_columns) and rank(
                    [*structural_columns, *block.column_indices]
                ) == len(structural_columns)
                reason = (
                    "structural_confounding"
                    if structurally_confounded
                    else "complete_alias"
                    if representative is not None
                    else "rank_dependency"
                )
            if block.block_id in required:
                raise TermBlockSelectionError(
                    "doe_fractional_forced_terms_conflict",
                    (block.block_id, representative.block_id)
                    if representative
                    else (block.block_id, *(item.block_id for item in retained)),
                )
            exclusions.append(
                {
                    "term_id": block.block_id,
                    "reason": reason,
                    "representative_term_id": representative.block_id if representative else None,
                    "sign": sign,
                }
            )
        # Keep original model-column order for coefficient/selection compatibility.
        columns.sort()
        retained.sort(key=lambda block: order[block.block_id])
        return FractionalEstimability(
            tuple(columns),
            tuple(block.block_id for block in retained),
            excluded,
            tuple(exclusions),
            sum(len(block.column_indices) for block in active),
            rank(columns),
            matrix.shape[0] - len(columns),
            tolerance,
        )


def _signed_duplicate(
    matrix: np.ndarray,
    block: ModelSelectionTermBlock,
    retained: Sequence[ModelSelectionTermBlock],
) -> tuple[ModelSelectionTermBlock | None, int | None]:
    if len(block.column_indices) != 1:
        return None, None
    column = matrix[:, block.column_indices[0]]
    for other in retained:
        if len(other.column_indices) != 1:
            continue
        previous = matrix[:, other.column_indices[0]]
        if np.array_equal(column, previous):
            return other, 1
        if np.array_equal(column, -previous):
            return other, -1
    return None, None
