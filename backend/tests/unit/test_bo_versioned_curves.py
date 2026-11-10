import math

import pytest
from scipy.integrate import quad
from scipy.stats import norm

from app.statistics.bo_desirability import (
    DesirabilityGoal,
    composite_desirability,
    gaussian_desirability_moments,
    independent_desirability_moments,
)
from app.statistics.bo_target_curve import GaussianTargetGoal


def target(**kwargs):
    return GaussianTargetGoal("size", "match_target", -1.0, 0.0, 2.0, **kwargs)


def test_weight_precedes_tail_underflow():
    goals = [target(importance=1), DesirabilityGoal("yield", "maximize", 0, 1, None, 99)]
    # Lower ordinate exp(-1) and y=-30 imply log(d)=-900, but log(d**.01)=-9.
    goals[0] = target(importance=1, lower_desirability=math.exp(-1))
    assert composite_desirability({"size": -30, "yield": 1}, goals) == pytest.approx(
        math.exp(-9), rel=2e-14
    )
    moments = independent_desirability_moments({"size": (-30, 0), "yield": (1, 0)}, goals)
    assert moments.mean == pytest.approx(math.exp(-9), rel=2e-14)
    assert moments.variance == 0


@pytest.mark.parametrize("power", [0.01, 0.3, 1.0])
def test_asymmetric_moments_independent_reference(power):
    goal = target(lower_desirability=0.04, upper_desirability=0.2)

    def integrand(y, p):
        width, ordinate = (1, 0.04) if y < 0 else (2, 0.2)
        return math.exp(p * math.log(ordinate) * (y / width) ** 2) * norm.pdf(y, 0.4, 0.7)

    expected = [
        sum(quad(integrand, lo, hi, args=(p,), epsabs=1e-13)[0] for lo, hi in [(-10, 0), (0, 10)])
        for p in (power, 2 * power)
    ]
    actual = gaussian_desirability_moments(0.4, 0.7, goal, power=power)
    assert actual.mean == pytest.approx(expected[0], rel=2e-11)
    assert actual.variance == pytest.approx(expected[1] - expected[0] ** 2, rel=2e-10)


def test_legacy_linear_target_still_has_hard_zero():
    goal = DesirabilityGoal("size", "match_target", -1, 0, 2)
    assert composite_desirability({"size": -2}, [goal]) == 0


def test_gaussian_goal_rejects_directional_use():
    with pytest.raises(ValueError):
        GaussianTargetGoal("size", "maximize", -1, 0, None)


def test_unrepresentable_weighted_decay_is_not_perfect_desirability():
    from app.statistics.bo_target_curve import TargetCurve, target_log_desirability, target_moments

    curve = TargetCurve(-1, 0, 1, math.nextafter(1, 0), math.nextafter(1, 0))
    for sd in (0, 1):
        with pytest.raises(ValueError, match="precision_unsupported"):
            target_moments(1e168, sd, curve, power=1e-320)
    with pytest.raises(ValueError, match="precision_unsupported"):
        target_log_desirability(1e168, curve, power=1e-320)


@pytest.mark.parametrize("sd", [0, 0.001])
def test_positive_composite_moment_underflow_is_not_deterministic_zero(sd):
    from dataclasses import replace

    goal = target(lower_desirability=math.exp(-1), upper_desirability=math.exp(-1))
    goals = [replace(goal, response_id=f"r{i}") for i in range(4)]
    with pytest.raises(ValueError, match="precision_unsupported"):
        independent_desirability_moments(
            {g.response_id: (-math.sqrt(800), sd) for g in goals}, goals
        )


def curve_request(q=2):
    from test_bo_desirability_batch_core import batch_request

    raw = batch_request(q)
    raw.update(schema_version=7, fit_policy=None)
    response = raw["objective"]["responses"][1]
    response.update(
        goal="match_target",
        lower=-10.0,
        target=2.0,
        upper=12.0,
        curve={
            "policy": "two_sided_gaussian_target_peak_one_v1",
            "lower_desirability": 0.04,
            "upper_desirability": 0.2,
        },
    )
    return raw


def test_exact_ds_zero_is_absorbing_before_intermediate_gaussian_underflow():
    from dataclasses import replace
    from itertools import permutations

    goal = target(lower_desirability=math.exp(-1), upper_desirability=math.exp(-1))
    goals = [replace(goal, response_id=f"r{i}") for i in range(3)]
    goals.append(DesirabilityGoal("yield", "maximize", 0, 1, None))
    posteriors = {g.response_id: (-math.sqrt(1200), 0) for g in goals[:3]}
    posteriors["yield"] = (0, 0)
    for ordering in permutations(goals):
        result = independent_desirability_moments(posteriors, ordering)
        assert result.mean == result.second_moment == result.variance == 0


@pytest.mark.parametrize("batch_size", [2, 8])
def test_curve_batch_uses_same_first_candidate_and_keeps_definition(batch_size):
    import copy
    import json

    from app.api.v1.schemas.bo_curve_calculation import (
        DesirabilityCurveCalculationRequest,
        DesirabilityCurveCalculationResult,
    )
    from app.services.bo_desirability_batch_contract import validate_batch_calculation_result
    from app.statistics.bo_desirability_batch_core import calculate_desirability_batch

    raw = curve_request(batch_size)
    before = copy.deepcopy(raw)
    result = calculate_desirability_batch(raw)
    parsed = DesirabilityCurveCalculationResult.model_validate_json(json.dumps(result))
    validate_batch_calculation_result(
        DesirabilityCurveCalculationRequest.model_validate(raw), parsed
    )
    assert raw == before
    single = calculate_desirability_batch(curve_request(1))
    assert result["items"][0] == single["items"][0]
    assert result["objective"] == raw["objective"]
    assert result["shared_model"]["schema_version"] == 7
    assert len(result["items"]) == batch_size
    assert result["items"][1]["planning"]["sampler"]["effective_sample_count"] == 16


@pytest.mark.parametrize("value", [True, "0.2", 0, 1, -0.1, float("nan"), float("inf")])
def test_new_curve_controls_never_coerce_or_clip(value):
    from pydantic import ValidationError

    from app.api.v1.schemas.bo_curve_calculation import DesirabilityCurveCalculationRequest

    raw = curve_request()
    raw["objective"]["responses"][1]["curve"]["lower_desirability"] = value
    with pytest.raises(ValidationError):
        DesirabilityCurveCalculationRequest.model_validate(raw)


def test_curve_fitted_exact_replicates_and_corruption_validation():
    import copy
    import json
    from uuid import UUID

    from app.api.v1.schemas.bo_curve_calculation import (
        DesirabilityCurveCalculationRequest,
        DesirabilityCurveCalculationResult,
    )
    from app.services.bo_desirability_batch_contract import validate_batch_calculation_result
    from app.statistics.bo_desirability_batch_core import calculate_desirability_batch

    raw = curve_request(1)
    raw["fit_policy"] = {"kind": "bounded_multiscale_starts_v1", "deterministic_start_count": 1}
    raw["search"]["model_max_evaluations"] = 1800
    raw["observation_policy"] = {"mode": "exact_replicates"}
    replicate = copy.deepcopy(raw["observations"][0])
    replicate["trial_id"] = str(UUID(int=999))
    replicate["response_values"]["yield"] += 0.2
    raw["observations"].append(replicate)
    request = DesirabilityCurveCalculationRequest.model_validate(raw)
    result = calculate_desirability_batch(raw)
    parsed = DesirabilityCurveCalculationResult.model_validate_json(json.dumps(result))
    validate_batch_calculation_result(request, parsed)
    assert all(m["model"]["schema_version"] == 5 for m in result["shared_model"]["response_models"])
    assert result["observation_view"]["raw_observation_count"] == 6
    assert result["observation_view"]["unique_condition_count"] == 5
    parsed.objective.responses[1].curve.lower_desirability = 0.05
    with pytest.raises(ValueError):
        validate_batch_calculation_result(request, parsed)
