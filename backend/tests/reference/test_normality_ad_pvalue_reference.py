import json
from pathlib import Path

import pytest

from app.statistics.normality import NormalityColumn, calculate_normality

REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/normality_statsmodels_reference.json",
)


def test_anderson_darling_approximation_matches_statsmodels_reference() -> None:
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    assert reference["statsmodels_version"] == "0.14.6"
    assert reference["p_value_method"] == "stephens_normal_unknown_mean_variance"

    for case in reference["cases"]:
        result = calculate_normality(
            [[str(value)] for value in case["values"]],
            [_column(case["case_id"])],
        )
        column = result["columns"][0]
        anderson = column["anderson_darling"]
        assert anderson["adjusted_statistic"] == pytest.approx(
            case["adjusted_statistic"],
            abs=1e-12,
        )
        assert anderson["p_value"] == pytest.approx(
            case["approximate_p_value"],
            abs=1e-12,
        )
        assert anderson["p_value_is_approximate"] is True
        assert anderson["p_value_method"] == reference["p_value_method"]


def _column(display_name: str) -> NormalityColumn:
    return NormalityColumn(
        column_id=display_name,
        column_index=0,
        display_name=display_name,
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )
