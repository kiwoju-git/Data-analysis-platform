import json
from itertools import combinations
from pathlib import Path

import pytest

from app.api.v1.schemas.doe import DoeFactorialAnalysisResult
from app.statistics.factorial_analysis import FactorialAnalysisRun, calculate_factorial_analysis
from app.statistics.term_block_model_selection import DoeSelectionOptions

REFERENCE = json.loads(
    (
        Path(__file__).parents[1] / "reference/fixtures/factorial_selection_statsmodels.json"
    ).read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", REFERENCE["cases"])
def test_final_selected_fit_matches_static_statsmodels_reference(case):
    runs = [
        FactorialAnalysisRun(
            index + 1, index % 8 + 1, False, None, dict(zip("ABC", row, strict=True)), response
        )
        for index, (row, response) in enumerate(zip(case["corners"], case["response"], strict=True))
    ]
    result = calculate_factorial_analysis(
        runs,
        list("ABC"),
        response_name="Yield",
        response_unit=None,
        max_interaction_order=3,
        model_selection=DoeSelectionOptions("backward_elimination"),
    )
    DoeFactorialAnalysisResult.model_validate(result)
    ids = [
        "intercept",
        *[
            ":".join(f"factor_{index + 1}" for index in indices)
            for order in (1, 2, 3)
            for indices in combinations(range(3), order)
        ],
    ]
    assert result["model_selection"]["pooled_term_ids"] == [
        ids[index] for index in case["pooled_columns"]
    ]
    assert result["model_selection"]["removed_term_ids"] == [
        ids[index] for index in case["removed_columns"]
    ]
    assert result["sample"]["df_residual"] == case["residual_df"]
    for field, expected in [
        ("coefficient", "coefficients"),
        ("standard_error", "standard_errors"),
        ("p_value", "p_values"),
    ]:
        assert [term[field] for term in result["terms"]] == pytest.approx(
            case[expected], rel=1e-8, abs=1e-9
        )
    for field in ("r_squared", "adjusted_r_squared"):
        assert result["fit"][field] == pytest.approx(case[field], abs=1e-9)
    assert result["fit"]["residual_standard_error"] == pytest.approx(case["s"], abs=1e-9)
    for field in ("press", "predicted_r_squared"):
        assert result["final_model"][field] == pytest.approx(case[field], abs=1e-9)
    assert [
        term["vif"] for term in result["final_model"]["coded_coefficients"][1:]
    ] == pytest.approx(case["vif"], abs=1e-9)


def test_none_preserves_every_legacy_numerical_payload():
    case = REFERENCE["cases"][1]
    runs = [
        FactorialAnalysisRun(
            index + 1, index % 8 + 1, False, None, dict(zip("ABC", row, strict=True)), response
        )
        for index, (row, response) in enumerate(zip(case["corners"], case["response"], strict=True))
    ]
    kwargs = {"response_name": "Yield", "response_unit": None, "max_interaction_order": 3}
    legacy = calculate_factorial_analysis(runs, list("ABC"), **kwargs)
    current = calculate_factorial_analysis(
        runs, list("ABC"), **kwargs, model_selection=DoeSelectionOptions()
    )
    for field in ("terms", "sample", "fit", "anova", "diagnostics", "plots"):
        assert current[field] == legacy[field]
