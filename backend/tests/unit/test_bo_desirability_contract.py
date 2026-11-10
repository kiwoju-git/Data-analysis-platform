import copy
import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.services.bo_desirability_contract import DesirabilityCalculationRequest


def calculation_request():
    return {
        "schema_version": 4,
        "factors": [{"factor_id": "x", "low": 0.0, "high": 1.0}],
        "constraints": [],
        "observations": [
            {
                "trial_id": str(UUID(int=i + 1)),
                "actual_coordinates": {"x": x},
                "normalized_coordinates": {"x": x},
                "response_values": {"yield": y, "cost": cost},
            }
            for i, (x, y, cost) in enumerate(
                [(0, 10, 5), (0.25, 15, 4), (0.5, 17, 3), (0.75, 14, 2), (1, 9, 4)]
            )
        ],
        "excluded_normalized": [[x] for x in (0, 0.25, 0.5, 0.75, 1)],
        "objective": {
            "responses": [
                {
                    "response_id": "yield",
                    "name": "Yield",
                    "unit": "g",
                    "goal": "maximize",
                    "lower": 8,
                    "target": 18,
                    "upper": None,
                    "importance": 1,
                },
                {
                    "response_id": "cost",
                    "name": "Cost",
                    "unit": None,
                    "goal": "minimize",
                    "lower": None,
                    "target": 1,
                    "upper": 6,
                    "importance": 2,
                },
            ]
        },
        "response_models": [
            {
                "response_id": key,
                "kernel": {"kind": "matern_5_2"},
                "surrogate": {"noise_mode": "fixed", "fixed_noise_sd": 0.2},
            }
            for key in ("yield", "cost")
        ],
        "observation_policy": {"mode": "retain_raw"},
        "xi_desirability": 0.01,
        "search": {
            "random_seed": 13,
            "candidate_count_per_step": 32,
            "local_start_count_per_step": 0,
            "max_iterations_per_step": 15,
            "max_evaluations_total": 128,
            "model_max_iterations": 50,
            "model_max_evaluations": 200,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 30000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
        },
    }


def test_complete_vector_contract_json_round_trip_and_user_text():
    raw = calculation_request()
    raw["objective"]["responses"][0]["name"] = '수율 "원값"\n\ue000keep\ue001'
    before = copy.deepcopy(raw)
    parsed = DesirabilityCalculationRequest.model_validate(raw)
    restored = DesirabilityCalculationRequest.model_validate_json(parsed.model_dump_json())
    assert parsed == restored
    assert raw == before
    assert parsed.objective.responses[0].name == raw["objective"]["responses"][0]["name"]
    assert parsed.batch_size == 1
    assert parsed.observations[0].response_values == {"yield": 10, "cost": 5}
    assert "objective_value" not in parsed.model_dump_json()


@pytest.mark.parametrize("value", [True, "2", "2e-1", float("nan"), float("inf")])
@pytest.mark.parametrize("where", ["response", "threshold", "xi", "factor", "noise", "budget"])
def test_numeric_contract_never_coerces_bool_string_or_nonfinite(value, where):
    raw = calculation_request()
    if where == "response":
        raw["observations"][0]["response_values"]["cost"] = value
    elif where == "threshold":
        raw["objective"]["responses"][0]["lower"] = value
    elif where == "xi":
        raw["xi_desirability"] = value
    elif where == "factor":
        raw["factors"][0]["low"] = value
    elif where == "noise":
        raw["response_models"][0]["surrogate"]["fixed_noise_sd"] = value
    else:
        raw["search"]["max_evaluations_total"] = value
    with pytest.raises(ValidationError):
        DesirabilityCalculationRequest.model_validate(raw)


@pytest.mark.parametrize(
    "defect",
    [
        "missing_response",
        "extra_response",
        "duplicate_model",
        "duplicate_goal",
        "duplicate_trial",
        "unknown_factor",
        "wrong_normalized",
        "missing_exclusion",
        "q2",
        "legacy_scalar",
        "constraint_factor",
        "unknown_option",
    ],
)
def test_mapping_and_ownership_shape_is_explicit(defect):
    raw = calculation_request()
    if defect == "missing_response":
        del raw["observations"][0]["response_values"]["cost"]
    elif defect == "extra_response":
        raw["observations"][0]["response_values"]["secret"] = 1
    elif defect == "duplicate_model":
        raw["response_models"][1]["response_id"] = "yield"
    elif defect == "duplicate_goal":
        raw["objective"]["responses"][1]["response_id"] = "yield"
    elif defect == "duplicate_trial":
        raw["observations"][1]["trial_id"] = raw["observations"][0]["trial_id"]
    elif defect == "unknown_factor":
        raw["observations"][0]["actual_coordinates"]["z"] = 1
    elif defect == "wrong_normalized":
        raw["observations"][0]["normalized_coordinates"]["x"] = 0.1
    elif defect == "missing_exclusion":
        raw["excluded_normalized"] = raw["excluded_normalized"][1:]
    elif defect == "q2":
        raw["batch_size"] = 2
    elif defect == "legacy_scalar":
        raw["observations"][0]["objective_value"] = 99
    elif defect == "constraint_factor":
        raw["constraints"] = [
            {
                "constraint_id": "c",
                "name": "Limit",
                "terms": [{"factor_id": "other", "coefficient": 1}],
                "relation": "less_than_or_equal",
                "bound": 1,
            }
        ]
    else:
        raw["search"]["silently_sample"] = True
    with pytest.raises(ValidationError):
        DesirabilityCalculationRequest.model_validate(raw)


def test_existing_study_api_does_not_advertise_unconnected_multiresponse_mode():
    from app.api.v1.schemas.bayesian import BayesianObjectiveRequest
    from app.api.v1.schemas.bayesian_noise import parse_current_batch_request

    with pytest.raises(ValidationError):
        BayesianObjectiveRequest.model_validate({"name": "Goal", "goal_type": "desirability"})
    with pytest.raises(ValidationError):
        parse_current_batch_request(calculation_request())
    assert "desirability" not in json.dumps(BayesianObjectiveRequest.model_json_schema())


def test_discrete_off_grid_observation_is_rejected_before_spawn():
    raw = calculation_request()
    raw["factors"][0].update(domain_kind="discrete_numeric", step=0.5)
    with pytest.raises(ValidationError, match="observation_coordinates_invalid"):
        DesirabilityCalculationRequest.model_validate(raw)


@pytest.mark.parametrize("field", ["schema_version", "batch_size"])
def test_boolean_is_not_a_schema_or_batch_count(field):
    raw = calculation_request()
    raw[field] = True
    with pytest.raises(ValidationError):
        DesirabilityCalculationRequest.model_validate(raw)
