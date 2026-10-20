"""RSM selection uses explicit strong hierarchy and never factorial start pooling."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from app.statistics.rsm_model_basis import RsmBasisTerm
from app.statistics.term_block_model_selection import (
    DoeSelectionOptions,
    ModelSelectionTermBlock,
    TermBlockSelectionError,
    resolve_term_policies,
    select_term_blocks,
    term_catalog,
)


def rsm_term_blocks(terms: Sequence[RsmBasisTerm]) -> list[ModelSelectionTermBlock]:
    return [
        ModelSelectionTermBlock(
            block_id=term.term_id,
            label=term.label,
            factor_ids=tuple(
                f"factor_{index + 1}" for index, power in enumerate(term.powers) if power
            ),
            column_indices=(column,),
            fixed=term.kind == "intercept",
            hierarchy_role="structural_term" if term.kind == "intercept" else "factorial_term",
            kind=term.kind,
            coefficient_labels=(term.label,),
            depends_on=term.depends_on,
        )
        for column, term in enumerate(terms)
    ]


def rsm_term_catalog(terms: Sequence[RsmBasisTerm]) -> list[dict[str, Any]]:
    return term_catalog(rsm_term_blocks(terms))


def select_rsm_terms(
    matrix: np.ndarray,
    response: np.ndarray,
    terms: Sequence[RsmBasisTerm],
    options: DoeSelectionOptions,
) -> tuple[list[int], dict[str, Any]]:
    blocks = rsm_term_blocks(terms)
    active = resolve_term_policies(blocks, options)
    columns = [index for block in active for index in block.column_indices]
    rank = int(np.linalg.matrix_rank(matrix[:, columns]))
    if rank != len(columns):
        raise TermBlockSelectionError("doe_rsm_model_rank_deficient")
    if options.method != "none" and len(response) - rank <= 0:
        raise TermBlockSelectionError("doe_rsm_selection_requires_residual_df")
    selected, result = select_term_blocks(matrix, response, blocks, options)
    # RSM's positive-DF precondition prevents the shared factorial pooling path.
    result["saturated_start_policy"] = "require_positive_residual_df"
    return selected, result
