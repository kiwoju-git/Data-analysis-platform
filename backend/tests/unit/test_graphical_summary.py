from math import isclose

from app.statistics.graphical_summary import (
    GraphicalSummaryColumn,
    summarize_numeric_graphics,
)


def test_graphical_summary_is_hand_checkable_with_fixed_histogram_bins() -> None:
    result = summarize_numeric_graphics(
        [["1"], ["2"], ["3"], ["4"], ["5"]],
        [
            GraphicalSummaryColumn(
                column_id="alpha",
                column_index=0,
                display_name="alpha",
                data_type="decimal",
                measurement_level="continuous",
                role="feature",
                unit=None,
            ),
        ],
        histogram_bin_count=2,
    )

    assert result["summary_type"] == "graphical_summary"
    assert result["histogram_method"] == "fixed_count"
    column = result["columns"][0]  # type: ignore[index]
    assert column["n_total"] == 5
    assert column["n_used"] == 5
    assert column["min"] == 1.0
    assert column["q1"] == 1.5
    assert column["median"] == 3.0
    assert column["q3"] == 4.5
    assert column["max"] == 5.0

    assert column["histogram"]["bin_count"] == 2
    assert column["histogram"]["bins"] == [
        {
            "lower": 1.0,
            "upper": 3.0,
            "count": 2,
            "include_lower": True,
            "include_upper": False,
        },
        {
            "lower": 3.0,
            "upper": 5.0,
            "count": 3,
            "include_lower": True,
            "include_upper": True,
        },
    ]
    assert column["boxplot"] == {
        "lower_whisker": 1.0,
        "q1": 1.5,
        "median": 3.0,
        "q3": 4.5,
        "upper_whisker": 5.0,
        "lower_fence": -3.0,
        "upper_fence": 9.0,
        "outlier_count": 0,
    }
    assert column["qq_plot"]["point_count"] == 5
    assert isclose(
        column["qq_plot"]["points"][2]["theoretical"],
        0.0,
        rel_tol=0,
        abs_tol=1e-12,
    )
    assert column["qq_plot"]["points"][2]["sample"] == 3.0
    assert column["ecdf"]["points"][-1] == {"x": 5.0, "probability": 1.0}


def test_graphical_summary_reports_outliers_and_truncated_plot_points() -> None:
    result = summarize_numeric_graphics(
        [[str(value)] for value in [1, 2, 3, 4, 5, 100]],
        [
            GraphicalSummaryColumn(
                column_id="alpha",
                column_index=0,
                display_name="alpha",
                data_type="decimal",
                measurement_level="continuous",
                role="feature",
                unit=None,
            ),
        ],
        point_limit=3,
    )

    column = result["columns"][0]  # type: ignore[index]
    assert column["boxplot"]["upper_whisker"] == 5.0
    assert column["boxplot"]["outlier_count"] == 1
    assert column["qq_plot"]["point_count"] == 3
    assert column["qq_plot"]["points_truncated"] is True
    assert column["ecdf"]["point_count"] == 3
    assert column["ecdf"]["points_truncated"] is True
    assert column["warnings"] == ["graphical_points_truncated"]


def test_graphical_summary_reports_missing_non_numeric_and_constant_columns() -> None:
    result = summarize_numeric_graphics(
        [["5"], [None], ["bad"], ["5"]],
        [
            GraphicalSummaryColumn(
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

    column = result["columns"][0]  # type: ignore[index]
    assert column["n_total"] == 4
    assert column["n_used"] == 2
    assert column["n_missing"] == 1
    assert column["n_non_numeric"] == 1
    assert column["histogram"]["binning"] == "constant"
    assert column["histogram"]["bins"][0]["count"] == 2
    assert column["warnings"] == ["non_numeric_values_excluded", "constant_column"]
