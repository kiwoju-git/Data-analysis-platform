from math import isclose

from app.statistics.descriptive import DescriptiveColumn, describe_numeric_columns


def test_descriptive_statistics_are_hand_checkable() -> None:
    result = describe_numeric_columns(
        [
            ["1"],
            ["2"],
            [None],
            ["bad"],
            ["3"],
            ["4"],
        ],
        [
            DescriptiveColumn(
                column_id="alpha",
                column_index=0,
                display_name="alpha",
                data_type="decimal",
                measurement_level="continuous",
                role="feature",
                unit=None,
            ),
        ],
    )

    summary = result["columns"][0]  # type: ignore[index]
    assert summary["n_total"] == 6
    assert summary["n_used"] == 4
    assert summary["n_missing"] == 1
    assert summary["n_non_numeric"] == 1
    assert summary["mean"] == 2.5
    assert isclose(summary["std"], 1.2909944487358056, rel_tol=0, abs_tol=1e-12)
    assert summary["min"] == 1.0
    assert summary["q1"] == 1.5
    assert summary["median"] == 2.5
    assert summary["q3"] == 3.5
    assert summary["max"] == 4.0
    assert summary["warnings"] == ["non_numeric_values_excluded"]


def test_descriptive_statistics_report_constant_and_empty_columns() -> None:
    result = describe_numeric_columns(
        [
            ["5", None],
            ["5", "bad"],
        ],
        [
            DescriptiveColumn(
                column_id="constant",
                column_index=0,
                display_name="constant",
                data_type="integer",
                measurement_level="continuous",
                role="feature",
                unit=None,
            ),
            DescriptiveColumn(
                column_id="empty",
                column_index=1,
                display_name="empty",
                data_type="decimal",
                measurement_level="continuous",
                role="feature",
                unit=None,
            ),
        ],
    )

    columns = result["columns"]  # type: ignore[assignment]
    assert columns[0]["warnings"] == ["constant_column"]
    assert columns[1]["n_used"] == 0
    assert columns[1]["mean"] is None
    assert columns[1]["warnings"] == ["non_numeric_values_excluded", "no_numeric_values"]
