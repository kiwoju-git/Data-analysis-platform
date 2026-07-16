import json
import math
from pathlib import Path
from statistics import median

from app.statistics.bayesian_optimization import calculate_bayesian_recommendation

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "doe_bayesian_optimization_reference_policy.json"
)


def test_seeded_sequential_branin_regret_stays_within_declared_budget() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    characterization = fixture["sequential_characterization"]
    benchmark = next(
        item
        for item in fixture["benchmarks"]
        if item["benchmark_id"] == characterization["benchmark_id"]
    )
    factors = [
        {"factor_id": "x1", "low": benchmark["bounds"][0][0], "high": benchmark["bounds"][0][1]},
        {"factor_id": "x2", "low": benchmark["bounds"][1][0], "high": benchmark["bounds"][1][1]},
    ]
    initial_points = characterization["initial_normalized_points"]
    regrets: list[float] = []

    for base_seed in characterization["random_seeds"]:
        points = [list(point) for point in initial_points]
        values = [_branin_from_normalized(point, benchmark) for point in points]
        initial_best = min(values)
        for step in range(characterization["recommendation_steps"]):
            search = dict(characterization["search_budget"])
            search["random_seed"] = base_seed + step
            result = calculate_bayesian_recommendation(
                {
                    "factors": factors,
                    "constraints": [],
                    "observations": [
                        {
                            "normalized": {"x1": point[0], "x2": point[1]},
                            "objective_value": value,
                        }
                        for point, value in zip(points, values, strict=True)
                    ],
                    "excluded_normalized": points,
                    "objective_direction": "minimize",
                    "search": search,
                }
            )
            point = [
                result["recommended_normalized_coordinates"]["x1"],
                result["recommended_normalized_coordinates"]["x2"],
            ]
            points.append(point)
            values.append(_branin_from_normalized(point, benchmark))

        assert len(points) == characterization["total_trial_budget"]
        assert min(values) < initial_best
        regrets.append(min(values) - benchmark["known_optimum"])

    assert len(regrets) >= 5
    assert max(regrets) <= characterization["maximum_simple_regret"]
    assert median(regrets) <= characterization["median_simple_regret"]


def _branin_from_normalized(point: list[float], benchmark: dict) -> float:
    x1 = benchmark["bounds"][0][0] + point[0] * (
        benchmark["bounds"][0][1] - benchmark["bounds"][0][0]
    )
    x2 = benchmark["bounds"][1][0] + point[1] * (
        benchmark["bounds"][1][1] - benchmark["bounds"][1][0]
    )
    constants = benchmark["constants"]
    return (
        (x2 - constants["b"] * x1**2 + constants["c"] * x1 - constants["r"]) ** 2
        + 10.0 * (1.0 - constants["t"]) * math.cos(x1)
        + 10.0
    )
