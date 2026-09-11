from itertools import combinations, product

import numpy as np
import pytest

from app.statistics.term_block_model_selection import (
    DoeSelectionOptions,
    ModelSelectionTermBlock,
    TermBlockSelectionError,
    pooling_target,
    select_term_blocks,
    term_is_removable,
)


def _design(replicates=1):
    corners = np.asarray(list(product((-1.0, 1.0), repeat=3)))
    x = np.tile(corners, (replicates, 1))
    blocks = [ModelSelectionTermBlock("intercept", "Intercept", (), (0,), True)]
    columns = [np.ones(len(x))]
    for order in (1, 2, 3):
        for indexes in combinations(range(3), order):
            names = tuple("ABC"[index] for index in indexes)
            blocks.append(
                ModelSelectionTermBlock(":".join(names), "*".join(names), names, (len(columns),))
            )
            columns.append(np.prod(x[:, indexes], axis=1))
    return np.column_stack(columns), blocks


def test_saturated_start_pools_ss_without_p_values_then_selects_final_model():
    matrix, blocks = _design()
    y = matrix @ np.array([10, 3, 2, 1, 0.02, 0.03, 0.04, 0.01])
    indexes, result = select_term_blocks(
        matrix, y, blocks, DoeSelectionOptions("backward_elimination")
    )
    assert result["initial_model_saturated"]
    assert result["target_pool_count"] == 2
    assert result["pooled_term_ids"] == ["A:B:C", "A:B"]
    assert all(
        step["removal_p_value"] is None
        for step in result["steps"]
        if step["phase"] == "initial_pooling"
    )
    assert result["steps"][1]["removal_adjusted_ss"] == pytest.approx(8 * 0.01**2, abs=1e-12)
    assert result["steps"][2]["removal_adjusted_ss"] == pytest.approx(8 * 0.02**2, abs=1e-12)
    assert result["final_term_ids"] == ["A", "B", "C"]
    assert indexes == [0, 1, 2, 3]
    assert result["post_selection_inference"] == "exploratory"
    for step in result["steps"]:
        retained = [block for block in blocks if block.block_id in step["active_term_ids"]]
        for block in retained:
            for order in range(1, len(block.factor_ids)):
                assert all(
                    ":".join(part) in step["active_term_ids"]
                    for part in combinations(block.factor_ids, order)
                )


def test_replicated_selection_and_none_preserve_original_matrix():
    matrix, blocks = _design(2)
    y = matrix @ np.array([10, 3, 2, 1, 0.02, 0.03, 0.04, 0.01]) + np.repeat([-0.5, 0.5], 8)
    original, none = select_term_blocks(matrix, y, blocks, DoeSelectionOptions())
    assert original == list(range(8))
    assert none["stop_reason"] == "not_requested"
    selected, result = select_term_blocks(
        matrix, y, blocks, DoeSelectionOptions("backward_elimination")
    )
    assert not result["initial_model_saturated"]
    assert result["pooled_term_ids"] == []
    assert selected == [0, 1, 2, 3]
    assert result["removed_term_ids"][0] == "A:B:C"
    assert all(step["removal_p_value"] > 0.05 for step in result["steps"][1:])
    # Direct deleted-observation fits independently check the final trace PRESS.
    final = matrix[:, selected]
    press = 0.0
    for index in range(len(y)):
        keep = np.arange(len(y)) != index
        coefficients, *_ = np.linalg.lstsq(final[keep], y[keep], rcond=None)
        press += (y[index] - final[index] @ coefficients) ** 2
    assert result["steps"][-1]["press"] == pytest.approx(press, abs=1e-10)


def test_strong_three_way_hierarchy_and_fixed_terms():
    _, blocks = _design()
    assert [item.block_id for item in blocks if term_is_removable(item, blocks)] == ["A:B:C"]
    assert not term_is_removable(ModelSelectionTermBlock("block", "Block", (), (8,), True), blocks)
    assert not term_is_removable(
        ModelSelectionTermBlock("curvature", "Curvature", (), (9,), True), blocks
    )


@pytest.mark.parametrize(("count", "expected"), [(1, 1), (2, 1), (6, 2), (7, 2), (10, 3), (40, 9)])
def test_pooling_count_uses_half_up_and_cap(count, expected):
    assert pooling_target(count) == expected


def test_tie_prefers_later_initial_order_and_never_reenters():
    matrix, blocks = _design()
    y = matrix @ np.array([10, 3, 2, 1, 0.02, 0.02, 0.02, 0.01])
    _, result = select_term_blocks(matrix, y, blocks, DoeSelectionOptions("backward_elimination"))
    assert result["pooled_term_ids"] == ["A:B:C", "B:C"]
    for removed in result["pooled_term_ids"]:
        assert removed not in result["final_term_ids"]


def test_multi_df_block_removes_all_dummy_columns():
    levels = np.asarray(list(product(range(3), range(2))) * 2)
    a = np.column_stack([levels[:, 0] == 1, levels[:, 0] == 2]).astype(float)
    b = (levels[:, 1] == 1).astype(float)
    matrix = np.column_stack([np.ones(12), a, b, a * b[:, None]])
    blocks = [
        ModelSelectionTermBlock("I", "Intercept", (), (0,), True),
        ModelSelectionTermBlock("A", "A", ("A",), (1, 2)),
        ModelSelectionTermBlock("B", "B", ("B",), (3,)),
        ModelSelectionTermBlock("AB", "AB", ("A", "B"), (4, 5)),
    ]
    y = matrix @ np.array([10, 2, 4, 3, 0.001, 0.001]) + np.repeat([-0.1, 0.1], 6)
    columns, result = select_term_blocks(
        matrix, y, blocks, DoeSelectionOptions("backward_elimination")
    )
    assert columns == [0, 1, 2, 3]
    assert result["steps"][1]["removal_df"] == 2
    assert result["removed_term_ids"] == ["AB"]


def test_detail_suppression_keeps_decision_and_timeout_is_explicit():
    matrix, blocks = _design()
    y = matrix @ np.arange(1, 9)
    _, result = select_term_blocks(
        matrix, y, blocks, DoeSelectionOptions("backward_elimination", display_step_details=False)
    )
    assert result["steps"] == []
    assert len(result["pooled_term_ids"]) == 2
    with pytest.raises(TermBlockSelectionError, match="time_budget"):
        select_term_blocks(matrix, y, blocks, DoeSelectionOptions(), time_budget_seconds=-1)


@pytest.mark.parametrize("alpha", [0, 1, float("nan"), float("inf")])
def test_invalid_alpha(alpha):
    matrix, blocks = _design()
    with pytest.raises(TermBlockSelectionError, match="options_invalid"):
        select_term_blocks(
            matrix, matrix @ np.arange(1, 9), blocks, DoeSelectionOptions(alpha_to_remove=alpha)
        )


def test_invalid_hierarchy_and_rank_are_not_repaired():
    matrix, blocks = _design()
    y = matrix @ np.arange(1, 9)
    bad_blocks = [
        *blocks[:4],
        ModelSelectionTermBlock("rest", "rest", ("A", "B", "C"), (4, 5, 6, 7)),
    ]
    with pytest.raises(TermBlockSelectionError, match="hierarchy_invalid"):
        select_term_blocks(matrix, y, bad_blocks, DoeSelectionOptions())
    matrix[:, 7] = matrix[:, 6]
    with pytest.raises(TermBlockSelectionError, match="rank_failure"):
        select_term_blocks(matrix, y, blocks, DoeSelectionOptions("backward_elimination"))


@pytest.mark.parametrize("scale", [1e-8, 1.0, 1e8])
def test_response_units_do_not_change_pooling_or_selection(scale):
    matrix, blocks = _design()
    y = scale * (matrix @ np.array([10, 3, 2, 1, 0.02, 0.03, 0.04, 0.01]))
    columns, result = select_term_blocks(
        matrix, y, blocks, DoeSelectionOptions("backward_elimination")
    )
    assert columns == [0, 1, 2, 3]
    assert result["pooled_term_ids"] == ["A:B:C", "A:B"]
