import json
import math
from pathlib import Path
from statistics import NormalDist

import pytest

from app.analyses.registry import METHOD_VERSIONS, get_analysis_method
from app.api.v1.schemas.analyses import MethodAvailability
from app.services.analysis_runs import _METHOD_EXECUTION_HANDLERS

FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "reference"
    / "fixtures"
    / "doe_bayesian_optimization_reference_policy.json"
)
CONTRACT_PATH = Path(__file__).parents[3] / "docs" / "bayesian_optimization_contract.md"


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _expected_improvement(mean: float, std: float, incumbent: float, xi: float) -> float:
    if std <= 0.0:
        return 0.0
    improvement = mean - incumbent - xi
    z_value = improvement / std
    standard_normal = NormalDist()
    density = math.exp(-0.5 * z_value * z_value) / math.sqrt(2.0 * math.pi)
    return improvement * standard_normal.cdf(z_value) + std * density


def test_bayesian_optimization_stays_planned_without_runtime_handler() -> None:
    method = get_analysis_method("doe.bayesian_optimization")

    assert method is not None
    assert method.method_version == METHOD_VERSIONS[method.method_id] == "0.1.0"
    assert method.availability == MethodAvailability.PLANNED
    assert method.requires_dataset is False
    assert method.method_id not in _METHOD_EXECUTION_HANDLERS
    assert method.disabled_reason is not None
    assert "실행 API와 추천 결과는 아직 제공하지 않습니다" in method.disabled_reason


def test_expected_improvement_hand_cases_match_policy_fixture() -> None:
    fixture = _load_fixture()
    reference = fixture["expected_improvement_reference"]
    assert isinstance(reference, dict)
    tolerance = float(reference["absolute_tolerance"])
    cases = reference["cases"]
    assert isinstance(cases, list)

    for case in cases:
        assert isinstance(case, dict)
        actual = _expected_improvement(
            float(case["posterior_mean"]),
            float(case["posterior_std"]),
            float(case["incumbent"]),
            float(case["xi"]),
        )
        assert actual == pytest.approx(float(case["expected_improvement"]), abs=tolerance)


def test_reference_benchmarks_reproduce_declared_analytic_optima() -> None:
    fixture = _load_fixture()
    benchmarks = fixture["benchmarks"]
    assert isinstance(benchmarks, list)
    benchmark_by_id = {
        str(benchmark["benchmark_id"]): benchmark
        for benchmark in benchmarks
        if isinstance(benchmark, dict)
    }

    quadratic = benchmark_by_id["hand_quadratic_1d_maximize"]
    quadratic_x = float(quadratic["known_optimizers"][0][0])
    quadratic_value = 1.0 - (quadratic_x - 0.25) ** 2
    assert quadratic_value == pytest.approx(
        float(quadratic["known_optimum"]),
        abs=float(quadratic["absolute_tolerance"]),
    )

    branin = benchmark_by_id["botorch_branin_minimize"]
    constants = branin["constants"]
    assert isinstance(constants, dict)
    for point in branin["known_optimizers"]:
        x1, x2 = (float(value) for value in point)
        value = (
            (
                x2
                - float(constants["b"]) * x1**2
                + float(constants["c"]) * x1
                - float(constants["r"])
            )
            ** 2
            + 10.0 * (1.0 - float(constants["t"])) * math.cos(x1)
            + 10.0
        )
        assert value == pytest.approx(
            float(branin["known_optimum"]),
            abs=float(branin["absolute_tolerance"]),
        )


def test_reference_policy_forbids_objective_execution_and_global_claims() -> None:
    fixture = _load_fixture()
    policy = fixture["policy"]
    assert isinstance(policy, dict)

    assert fixture["status"] == "planning_only"
    assert fixture["runtime_result_expected"] is False
    assert policy["app_executes_objective"] is False
    assert policy["global_optimum_guaranteed"] is False
    assert policy["objective_count"] == 1
    assert policy["factor_type"] == "continuous"


def test_contract_records_required_safety_and_reproducibility_decisions() -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")

    for phrase in (
        "planning-only",
        "GaussianProcessRegressor",
        "Matérn 5/2",
        "Expected Improvement",
        "completed trial",
        "global optimum",
        "arbitrary Python",
        "observation_history_sha256",
        "No executable API",
    ):
        assert phrase in contract
