import json
from pathlib import Path

import pytest

from app.statistics.kruskal_wallis import (
    KruskalWallisError,
    KruskalWallisGroupColumn,
    KruskalWallisResponseColumn,
    calculate_kruskal_wallis,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/kruskal_wallis_input.json")
REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/kruskal_wallis_scipy_reference.json",
)


def test_kruskal_wallis_is_hand_checkable_for_rank_sums_and_h() -> None:
    result = calculate_kruskal_wallis(
        [
            ["1", "A"],
            ["2", "A"],
            ["3", "A"],
            ["4", "B"],
            ["5", "B"],
            ["6", "B"],
            ["7", "C"],
            ["8", "C"],
            ["9", "C"],
        ],
        _response_column(),
        _group_column(),
    )

    assert result["summary_type"] == "kruskal_wallis_test"
    assert result["method"] == "kruskal_wallis"
    assert result["missing_policy"] == "complete_case"
    assert result["alpha"] == 0.05
    assert result["has_ties"] is False
    assert result["tie_correction"] == 1.0
    assert result["warnings"] == [
        "kruskal_wallis_independence_assumption",
        "kruskal_wallis_not_median_test",
        "dunn_holm_after_significant",
        "small_group_size",
    ]
    assert result["n_total"] == 9
    assert result["n_used"] == 9
    assert result["group_count"] == 3

    groups = result["groups"]
    assert [group["group_label"] for group in groups] == ["A", "B", "C"]
    assert [group["rank_sum"] for group in groups] == [6.0, 15.0, 24.0]
    assert [group["mean_rank"] for group in groups] == [2.0, 5.0, 8.0]

    test = result["test"]
    assert test["h_statistic"] == pytest.approx(7.2, abs=1e-12)
    assert test["df"] == 2
    assert test["p_value"] == pytest.approx(0.02732372244729256, abs=1e-12)
    assert test["effect_size"]["epsilon_squared"] == pytest.approx(
        0.8666666666666667,
        abs=1e-12,
    )

    posthoc = result["posthoc"]
    assert posthoc["performed"] is True
    assert posthoc["method"] == "dunn"
    assert posthoc["multiplicity_method"] == "holm"
    assert len(posthoc["comparisons"]) == 3
    assert posthoc["comparisons"][1]["group_1_label"] == "A"
    assert posthoc["comparisons"][1]["group_2_label"] == "C"
    assert posthoc["comparisons"][1]["reject_holm"] is True


def test_kruskal_wallis_matches_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        rows = _rows_from_case(case)
        expected = cases_by_id[case["case_id"]]
        result = calculate_kruskal_wallis(
            rows,
            _response_column(),
            _group_column(),
            alpha=case["alpha"],
            posthoc_method=case["posthoc_method"],
            posthoc_policy=case["posthoc_policy"],
        )

        assert [group["group_label"] for group in result["groups"]] == expected["group_order"]
        assert [group["n"] for group in result["groups"]] == expected["group_sizes"]
        assert [group["median"] for group in result["groups"]] == expected["group_medians"]
        assert [group["rank_sum"] for group in result["groups"]] == pytest.approx(
            expected["rank_sums"],
            abs=1e-12,
        )
        assert [group["mean_rank"] for group in result["groups"]] == pytest.approx(
            expected["mean_ranks"],
            abs=1e-12,
        )
        assert result["tie_correction"] == pytest.approx(
            expected["tie_correction"],
            abs=1e-12,
        )
        test = result["test"]
        assert test["h_statistic"] == pytest.approx(
            expected["h_statistic"],
            abs=1e-12,
        )
        assert test["df"] == expected["df"]
        assert test["p_value"] == pytest.approx(expected["pvalue"], abs=1e-12)
        assert test["effect_size"]["epsilon_squared"] == pytest.approx(
            expected["epsilon_squared"],
            abs=1e-12,
        )
        assert result["posthoc"]["performed"] is True
        for actual, comparison in zip(
            result["posthoc"]["comparisons"],
            expected["posthoc"],
            strict=True,
        ):
            assert actual["group_1_label"] == comparison["group_1_label"]
            assert actual["group_2_label"] == comparison["group_2_label"]
            assert actual["mean_rank_difference"] == pytest.approx(
                comparison["mean_rank_difference"],
                abs=1e-12,
            )
            assert actual["standard_error"] == pytest.approx(
                comparison["standard_error"],
                abs=1e-12,
            )
            assert actual["z_statistic"] == pytest.approx(
                comparison["z_statistic"],
                abs=1e-12,
            )
            assert actual["raw_p_value"] == pytest.approx(
                comparison["raw_p_value"],
                abs=1e-12,
            )
            assert actual["adjusted_p_value"] == pytest.approx(
                comparison["adjusted_p_value"],
                abs=1e-12,
            )


def test_kruskal_wallis_reports_exclusions_and_skips_posthoc_when_not_significant() -> None:
    result = calculate_kruskal_wallis(
        [
            ["1", "A"],
            ["2", "A"],
            ["2", "B"],
            ["3", "B"],
            ["3", "C"],
            ["4", "C"],
            ["", "A"],
            ["bad", "B"],
            ["5", ""],
        ],
        _response_column(),
        _group_column(),
    )

    assert result["n_total"] == 9
    assert result["n_used"] == 6
    assert result["n_excluded_missing_response"] == 1
    assert result["n_excluded_missing_group"] == 1
    assert result["n_excluded_non_numeric_response"] == 1
    assert result["has_ties"] is True
    assert result["posthoc"]["performed"] is False
    assert result["posthoc"]["reason"] == "overall_not_significant"
    assert result["warnings"] == [
        "kruskal_wallis_independence_assumption",
        "kruskal_wallis_not_median_test",
        "posthoc_skipped_overall_not_significant",
        "kruskal_wallis_ties_detected",
        "small_group_size",
        "missing_values_excluded",
        "non_numeric_values_excluded",
    ]


def test_kruskal_wallis_rejects_invalid_design_without_fake_statistic() -> None:
    with pytest.raises(
        KruskalWallisError,
        match="kruskal_wallis_requires_at_least_three_groups",
    ):
        calculate_kruskal_wallis(
            [["1", "A"], ["2", "B"]],
            _response_column(),
            _group_column(),
        )

    with pytest.raises(
        KruskalWallisError,
        match="kruskal_wallis_all_values_identical",
    ):
        calculate_kruskal_wallis(
            [["1", "A"], ["1", "B"], ["1", "C"]],
            _response_column(),
            _group_column(),
        )

    with pytest.raises(
        KruskalWallisError,
        match="invalid_kruskal_wallis_posthoc_method",
    ):
        calculate_kruskal_wallis(
            [["1", "A"], ["2", "B"], ["3", "C"]],
            _response_column(),
            _group_column(),
            posthoc_method="fake",
        )


def _rows_from_case(case: dict[str, object]) -> list[list[str]]:
    groups = case["groups"]
    assert isinstance(groups, dict)
    rows: list[list[str]] = []
    for group_label, values in groups.items():
        assert isinstance(group_label, str)
        assert isinstance(values, list)
        rows.extend([[str(value), group_label] for value in values])
    return rows


def _response_column() -> KruskalWallisResponseColumn:
    return KruskalWallisResponseColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _group_column() -> KruskalWallisGroupColumn:
    return KruskalWallisGroupColumn(
        column_id="group",
        column_index=1,
        display_name="group",
        data_type="text",
        measurement_level="nominal",
        role="group",
        unit=None,
    )
