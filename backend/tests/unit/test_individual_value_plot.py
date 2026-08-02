import pytest

from app.statistics.individual_value_plot import (
    GraphPointColumn,
    GraphPointError,
    calculate_individual_value_points,
)


def test_individual_value_points_are_deterministic_and_not_sampled() -> None:
    column = GraphPointColumn("value", 0, "Value", "kg")
    result = calculate_individual_value_points(
        [["1"], ["1"], ["2"]],
        [column],
        decimal=".",
        thousands=None,
        point_limit=10,
    )

    assert result["sampled"] is False
    assert result["point_count"] == 3
    assert result["points"] == [
        {
            "series_id": "value",
            "series_label": "Value",
            "source_column_label": "Value",
            "group": None,
            "point_index": 1,
            "canonical_position": 1,
            "value": 1.0,
        },
        {
            "series_id": "value",
            "series_label": "Value",
            "source_column_label": "Value",
            "group": None,
            "point_index": 2,
            "canonical_position": 2,
            "value": 1.0,
        },
        {
            "series_id": "value",
            "series_label": "Value",
            "source_column_label": "Value",
            "group": None,
            "point_index": 3,
            "canonical_position": 3,
            "value": 2.0,
        },
    ]


def test_individual_value_points_fail_instead_of_sampling() -> None:
    column = GraphPointColumn("value", 0, "Value", None)
    with pytest.raises(GraphPointError, match="individual_value_point_limit_exceeded"):
        calculate_individual_value_points(
            [[str(index)] for index in range(4)],
            [column],
            decimal=".",
            thousands=None,
            point_limit=3,
        )
