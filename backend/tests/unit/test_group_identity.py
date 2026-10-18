"""F01: a display abbreviation must never become a statistical group key."""

from typing import Any

import pytest

from app.statistics import equal_variances, kruskal_wallis, two_sample_t

PREFIX = "X" * 121
LABELS = [PREFIX + "-A", PREFIX + "-B", "C", "D"]


def _columns(module: Any) -> tuple[Any, Any]:
    prefix = {
        equal_variances: "EqualVariance",
        kruskal_wallis: "KruskalWallis",
        two_sample_t: "TwoSampleT",
    }[module]
    common = {
        "unit": None,
        "role": "response",
        "data_type": "decimal",
        "measurement_level": "continuous",
    }
    response = getattr(module, prefix + "ResponseColumn")(
        column_id="response", column_index=0, display_name="response", **common
    )
    group = getattr(module, prefix + "GroupColumn")(
        column_id="group",
        column_index=1,
        display_name="group",
        unit=None,
        role="group",
        data_type="text",
        measurement_level="nominal",
    )
    return response, group


def _rows(labels: list[str]) -> list[list[str]]:
    return [
        [str(index * 10 + value), label]
        for index, label in enumerate(labels)
        for value in range(1, 6)
    ]


@pytest.mark.parametrize("module", [equal_variances, kruskal_wallis])
def test_four_full_group_values_do_not_merge_at_display_prefix(module: Any) -> None:
    calculate = getattr(module, "calculate_" + module.__name__.split(".")[-1])
    actual = calculate(_rows(LABELS), *_columns(module))
    expected = calculate(_rows(["A", "B", "C", "D"]), *_columns(module))
    assert actual["group_count"] == 4
    assert [group["n"] for group in actual["groups"]] == [5, 5, 5, 5]
    assert [group["group_value"] for group in actual["groups"]] == LABELS
    assert [group["group_index"] for group in actual["groups"]] == [0, 1, 2, 3]
    assert actual["groups"][0]["group_label"] == actual["groups"][1]["group_label"]
    assert actual["groups"][0]["group_label"] == "X" * 117 + "..."
    for left, right in zip(actual["groups"], expected["groups"], strict=True):
        for key in ("n", "mean", "median", "min", "max"):
            assert left[key] == right[key]
    key = "levene" if module is equal_variances else "test"
    assert actual[key] == expected[key]


def test_dunn_pair_identity_preserves_rank_and_p_value_associations() -> None:
    actual = kruskal_wallis.calculate_kruskal_wallis(_rows(LABELS), *_columns(kruskal_wallis))
    expected = kruskal_wallis.calculate_kruskal_wallis(
        _rows(["A", "B", "C", "D"]), *_columns(kruskal_wallis)
    )
    assert len(actual["posthoc"]["comparisons"]) == 6
    for left, right in zip(
        actual["posthoc"]["comparisons"], expected["posthoc"]["comparisons"], strict=True
    ):
        assert left["group_1_index"] == right["group_1_index"]
        assert left["group_2_index"] == right["group_2_index"]
        assert left["group_1_value"] == LABELS[left["group_1_index"]]
        assert left["group_2_value"] == LABELS[left["group_2_index"]]
        for key in (
            "mean_rank_difference",
            "standard_error",
            "z_statistic",
            "raw_p_value",
            "adjusted_p_value",
            "reject_holm",
        ):
            assert left[key] == right[key]


def test_two_sample_t_rejects_three_full_groups_even_if_two_labels_collide() -> None:
    with pytest.raises(
        two_sample_t.TwoSampleTError, match="two_sample_t_requires_exactly_two_groups"
    ):
        two_sample_t.calculate_two_sample_t(_rows(LABELS[:3]), *_columns(two_sample_t))


@pytest.mark.parametrize("alternative", ["two_sided", "less", "greater"])
@pytest.mark.parametrize("variance_assumption", ["welch", "pooled"])
def test_two_full_groups_keep_encounter_contrast_and_each_tail(
    alternative: str, variance_assumption: str
) -> None:
    options = {"alternative": alternative, "variance_assumption": variance_assumption}
    actual = two_sample_t.calculate_two_sample_t(
        _rows(LABELS[:2]), *_columns(two_sample_t), **options
    )
    expected = two_sample_t.calculate_two_sample_t(
        _rows(["A", "B"]), *_columns(two_sample_t), **options
    )
    assert [group["n"] for group in actual["groups"]] == [5, 5]
    assert actual["contrast"]["group_1_index"] == 0
    assert actual["contrast"]["group_2_index"] == 1
    assert actual["contrast"]["group_1_value"] == LABELS[0]
    assert actual["contrast"]["group_2_value"] == LABELS[1]
    for key in (
        "estimate",
        "standard_error",
        "statistic",
        "df",
        "p_value",
        "reject_null",
        "confidence_interval",
        "effect_size",
    ):
        assert actual["contrast"][key] == expected["contrast"][key]
    assert actual["contrast"]["estimate"] == -10.0
    rows = _rows(LABELS[:2])
    reversed_groups = two_sample_t.calculate_two_sample_t(
        rows[5:] + rows[:5], *_columns(two_sample_t), **options
    )
    assert reversed_groups["contrast"]["group_1_value"] == LABELS[1]
    assert reversed_groups["contrast"]["group_2_value"] == LABELS[0]
    assert reversed_groups["contrast"]["estimate"] == 10.0
    opposite = {"less": "greater", "greater": "less", "two_sided": "two_sided"}[alternative]
    reversed_reference = two_sample_t.calculate_two_sample_t(
        rows, *_columns(two_sample_t), alternative=opposite, variance_assumption=variance_assumption
    )
    assert reversed_groups["contrast"]["p_value"] == reversed_reference["contrast"]["p_value"]


@pytest.mark.parametrize("module", [equal_variances, kruskal_wallis])
def test_full_group_identity_uses_existing_strip_only(module: Any) -> None:
    labels = [
        "  " + "가" * 121 + "-A ",
        "가" * 121 + "-B",
        "literal...",
        "Literal...",
        "01",
        "1",
        "é",
        "e\u0301",
    ]
    calculate = getattr(module, "calculate_" + module.__name__.split(".")[-1])
    result = calculate(_rows(labels), *_columns(module))
    assert [group["group_value"] for group in result["groups"]] == [
        label.strip() for label in labels
    ]
    assert result["group_count"] == len(labels)


def test_equal_variance_intervals_join_by_index_not_colliding_label_or_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offsets = [-2, -1, -0.5, 0, 0.5, 1, 2, -1.5, 1.5, 0.25]
    rows = [
        [str(10 * index + scale * offset), label]
        for index, (label, scale) in enumerate(zip(LABELS[:2], [1, 3], strict=True))
        for offset in offsets
    ]
    original = equal_variances._multiple_comparisons

    def reversed_groups(*args: Any, **kwargs: Any) -> dict[str, object]:
        result = original(*args, **kwargs)
        result["groups"] = list(reversed(result["groups"]))
        return result

    monkeypatch.setattr(equal_variances, "_multiple_comparisons", reversed_groups)
    actual = equal_variances.calculate_equal_variances(rows, *_columns(equal_variances))
    assert actual["group_count"] == 2
    comparison = actual["multiple_comparisons"]
    assert comparison["computed"] is True
    by_index = {group["group_index"]: group for group in comparison["groups"]}
    for group in actual["groups"]:
        assert group["comparison_interval"] == by_index[group["group_index"]]["comparison_interval"]
        assert group["group_value"] == by_index[group["group_index"]]["group_value"]
    assert actual["groups"][0]["comparison_interval"] != actual["groups"][1]["comparison_interval"]
    assert comparison["pairwise_p_values"][0]["left_group_index"] == 0
    assert comparison["pairwise_p_values"][0]["right_group_index"] == 1


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "wrong_value", "boolean"])
def test_equal_variance_interval_identity_must_be_valid(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    original = equal_variances._multiple_comparisons

    def invalid_groups(*args: Any, **kwargs: Any) -> dict[str, object]:
        result = original(*args, **kwargs)
        groups = result["groups"]
        assert result["computed"] is True
        if mutation == "missing":
            groups.pop()
        elif mutation == "duplicate":
            groups[1]["group_index"] = groups[0]["group_index"]
        elif mutation == "boolean":
            groups[0]["group_index"] = False
        else:
            groups[0]["group_value"] = "another full value"
        return result

    monkeypatch.setattr(equal_variances, "_multiple_comparisons", invalid_groups)
    rows = [
        [str(value * scale), label]
        for label, scale in zip(LABELS[:2], [1, 3], strict=True)
        for value in range(1, 11)
    ]
    with pytest.raises(ValueError, match="equal_variances_comparison_group_mismatch"):
        equal_variances.calculate_equal_variances(rows, *_columns(equal_variances))


def test_multiple_comparison_pairs_keep_full_identity_and_numeric_bijection() -> None:
    def calculate(labels: list[str]) -> Any:
        return equal_variances.calculate_equal_variances(
            [
                [str((index + 1) * value), label]
                for index, label in enumerate(labels)
                for value in range(1, 11)
            ],
            *_columns(equal_variances),
        )["multiple_comparisons"]

    actual = calculate(LABELS)
    expected = calculate(["A", "B", "C", "D"])
    assert actual["computed"] is True
    assert actual["p_value"] == expected["p_value"]
    assert len(actual["pairwise_p_values"]) == 6
    for left, right in zip(actual["pairwise_p_values"], expected["pairwise_p_values"], strict=True):
        assert left["left_group_value"] == LABELS[left["left_group_index"]]
        assert left["right_group_value"] == LABELS[left["right_group_index"]]
        assert left["p_value"] == right["p_value"]
    for left, right in zip(actual["groups"], expected["groups"], strict=True):
        assert left["comparison_interval"] == right["comparison_interval"]
