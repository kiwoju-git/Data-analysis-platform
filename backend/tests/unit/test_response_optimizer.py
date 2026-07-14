import json
from pathlib import Path

import pytest

from app.statistics.response_optimizer import (
    OptimizerFactor,
    OptimizerFactorBound,
    OptimizerLinearConstraint,
    OptimizerModel,
    OptimizerObjective,
    OptimizerSearchOptions,
    OptimizerTerm,
    ResponseOptimizerError,
    calculate_response_optimizer,
    composite_desirability,
    individual_desirability,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "reference"
    / "fixtures"
    / "response_optimizer_nist_reference.json"
)


def _factor(name: str) -> OptimizerFactor:
    return OptimizerFactor(name=name, low=-1.0, high=1.0, alpha=1.0)


def _model(
    analysis_id: str,
    response_name: str,
    terms: list[tuple[str, tuple[str, ...], float]],
    factor_names: tuple[str, ...] = ("x", "y"),
) -> OptimizerModel:
    return OptimizerModel(
        analysis_id=analysis_id,
        response_name=response_name,
        response_unit=None,
        factors=tuple(_factor(name) for name in factor_names),
        terms=tuple(
            OptimizerTerm(kind=kind, factor_names=names, coefficient=coefficient)  # type: ignore[arg-type]
            for kind, names, coefficient in terms
        ),
    )


def _objective(
    model: OptimizerModel,
    goal: str,
    *,
    lower: float | None,
    target: float | None,
    upper: float | None,
    importance: float = 1.0,
) -> OptimizerObjective:
    return OptimizerObjective(
        model=model,
        goal=goal,  # type: ignore[arg-type]
        lower=lower,
        target=target,
        upper=upper,
        lower_weight=1.0,
        upper_weight=1.0,
        importance=importance,
    )


def _options(**overrides: int) -> OptimizerSearchOptions:
    values = {
        "random_seed": 20260714,
        "random_candidate_count": 256,
        "multi_start_count": 8,
        "max_iterations": 120,
        "max_evaluations": 5000,
        "time_budget_ms": 5000,
    }
    values.update(overrides)
    return OptimizerSearchOptions(**values)


def test_desirability_functions_and_importance_weighted_composite_are_hand_checkable() -> None:
    model = _model("model-a", "response", [("intercept", (), 0.0)])
    maximize = _objective(model, "maximize", lower=0.0, target=10.0, upper=None)
    minimize = _objective(model, "minimize", lower=None, target=2.0, upper=6.0)
    target = _objective(model, "target", lower=0.0, target=5.0, upper=9.0)
    in_range = _objective(model, "range", lower=3.0, target=None, upper=7.0)

    assert individual_desirability(5.0, maximize) == pytest.approx(0.5)
    assert individual_desirability(4.0, minimize) == pytest.approx(0.5)
    assert individual_desirability(7.0, target) == pytest.approx(0.5)
    assert individual_desirability(3.0, in_range) == 1.0
    assert individual_desirability(8.0, in_range) == 0.0

    first = _objective(model, "maximize", lower=0.0, target=10.0, upper=None, importance=1)
    second_model = _model("model-b", "second", [("intercept", (), 0.0)])
    second = _objective(
        second_model,
        "maximize",
        lower=0.0,
        target=10.0,
        upper=None,
        importance=3,
    )
    assert composite_desirability((0.25, 1.0), (first, second)) == pytest.approx(0.25**0.25)
    assert composite_desirability((0.0, 1.0), (first, second)) == 0.0


def test_optimizer_finds_known_bounded_quadratic_maximum_and_honors_linear_constraint() -> None:
    model = _model(
        "known-maximum",
        "yield",
        [
            ("intercept", (), 9.4375),
            ("main_effect", ("x",), 0.5),
            ("main_effect", ("y",), -2.0),
            ("quadratic", ("x",), -1.0),
            ("quadratic", ("y",), -2.0),
        ],
    )
    result = calculate_response_optimizer(
        [_objective(model, "maximize", lower=8.0, target=10.0, upper=None)],
        factor_bounds=[],
        linear_constraints=[
            OptimizerLinearConstraint(
                name="combined load",
                coefficients={"x": 1.0, "y": 1.0},
                relation="less_than_or_equal",
                bound=0.0,
            )
        ],
        search_options=_options(),
    )

    recommendation = result["recommendation"]
    assert isinstance(recommendation, dict)
    actual = recommendation["actual_coordinates"]
    assert isinstance(actual, dict)
    assert actual["x"] == pytest.approx(0.25, abs=1e-5)
    assert actual["y"] == pytest.approx(-0.5, abs=1e-5)
    assert recommendation["composite_desirability"] == pytest.approx(1.0)
    assert recommendation["all_constraints_satisfied"] is True
    assert result["model_policy"]["global_optimum_guaranteed"] is False  # type: ignore[index]


def test_nist_multiple_response_desirability_reference_is_reproduced() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    factor_names = tuple(fixture["factor_bounds"])
    factors = tuple(_factor(name) for name in factor_names)
    objectives = []
    for source in fixture["models"]:
        model = OptimizerModel(
            analysis_id=source["analysis_id"],
            response_name=source["response_name"],
            response_unit=None,
            factors=factors,
            terms=tuple(
                OptimizerTerm(kind=term[0], factor_names=tuple(term[1]), coefficient=term[2])
                for term in source["terms"]
            ),
        )
        objectives.append(
            _objective(
                model,
                source["goal"],
                lower=source["lower"],
                target=source["target"],
                upper=source["upper"],
            )
        )

    result = calculate_response_optimizer(
        objectives,
        factor_bounds=[],
        linear_constraints=[],
        search_options=_options(
            random_candidate_count=1024,
            multi_start_count=24,
            max_evaluations=30_000,
        ),
    )

    recommendation = result["recommendation"]
    assert isinstance(recommendation, dict)
    actual = recommendation["actual_coordinates"]
    assert isinstance(actual, dict)
    published = fixture["published_best"]
    for factor_name, expected in published["coded_coordinates"].items():
        assert actual[factor_name] == pytest.approx(expected, abs=0.12)
    assert recommendation["composite_desirability"] == pytest.approx(
        published["composite_desirability"], abs=0.02
    )
    assert "response_optimizer_confirmation_run_required" in result["warnings"]


def test_optimizer_reports_deterministic_evaluation_budget_termination() -> None:
    model = _model(
        "budget-model",
        "yield",
        [("intercept", (), 5.0), ("main_effect", ("x",), 1.0)],
    )
    result = calculate_response_optimizer(
        [_objective(model, "maximize", lower=3.0, target=6.0, upper=None)],
        factor_bounds=[],
        linear_constraints=[],
        search_options=_options(random_candidate_count=100, max_evaluations=32),
    )

    search = result["search"]
    assert isinstance(search, dict)
    assert search["evaluation_count"] == 32
    assert search["termination_reason"] == "evaluation_budget"
    assert "response_optimizer_evaluation_budget_reached" in result["warnings"]


@pytest.mark.parametrize(
    ("objective", "bounds", "constraints", "expected_code"),
    [
        (
            ("maximize", 5.0, 4.0, None),
            [],
            [],
            "response_optimizer_objective_thresholds_invalid",
        ),
        (
            ("maximize", 0.0, 10.0, None),
            [OptimizerFactorBound("x", -2.0, 1.0)],
            [],
            "response_optimizer_factor_bound_invalid",
        ),
        (
            ("maximize", 0.0, 10.0, None),
            [],
            [
                OptimizerLinearConstraint(
                    "impossible",
                    {"x": 1.0},
                    "less_than_or_equal",
                    -2.0,
                )
            ],
            "response_optimizer_no_feasible_point",
        ),
    ],
)
def test_optimizer_rejects_invalid_objectives_bounds_and_infeasible_constraints(
    objective,
    bounds,
    constraints,
    expected_code,
) -> None:
    model = _model("invalid-model", "yield", [("intercept", (), 5.0)])
    goal, lower, target, upper = objective
    with pytest.raises(ResponseOptimizerError, match=expected_code) as exc_info:
        calculate_response_optimizer(
            [_objective(model, goal, lower=lower, target=target, upper=upper)],
            factor_bounds=bounds,
            linear_constraints=constraints,
            search_options=_options(),
        )
    assert exc_info.value.code == expected_code
