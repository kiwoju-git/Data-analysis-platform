"""Stored EI numerical-policy compatibility without any surrogate fits."""

import hashlib
import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest
from pydantic import ValidationError, create_model

from app.api.v1.schemas.bo_desirability_calculation import _Acquisition
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability_acquisition import beta_expected_improvement

POLICY = "positive_beta_integral_v2"
MEAN, VARIANCE, THRESHOLD = 0.9, 1e-9, 0.9000316227766018
LEGACY_VALUE = 2.6340823912618383e-6


def _legacy_payload():
    concentration = MEAN * (1 - MEAN) / VARIANCE - 1
    return {
        "kind": "desirability_beta_expected_improvement",
        "value": LEGACY_VALUE,
        "threshold": THRESHOLD,
        "distribution": "beta_moment_match",
        "alpha": MEAN * concentration,
        "beta": (1 - MEAN) * concentration,
        "xi_desirability": 0.0,
    }


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def test_new_result_records_numerical_policy_and_keeps_statistical_distribution():
    result = beta_expected_improvement(MEAN, VARIANCE, THRESHOLD)
    assert asdict(result)["numerical_policy"] == POLICY
    assert result.distribution == "beta_moment_match"
    assert result.value != LEGACY_VALUE


def test_legacy_nested_acquisition_serialization_and_hash_are_unchanged():
    envelope = create_model("Envelope", acquisition=(_Acquisition, ...))
    old = {"acquisition": _legacy_payload()}
    parsed = envelope.model_validate(old)
    assert parsed.acquisition.numerical_policy is None
    assert parsed.model_dump(mode="json") == old
    assert _canonical(parsed.model_dump(mode="json")) == _canonical(old)
    assert (
        hashlib.sha256(_canonical(parsed.model_dump())).digest()
        == hashlib.sha256(_canonical(old)).digest()
    )
    assert json.loads(parsed.model_dump_json()) == old


def test_new_policy_round_trips_but_unknown_or_explicit_null_policy_is_rejected():
    payload = {
        "kind": "desirability_beta_expected_improvement",
        **asdict(beta_expected_improvement(MEAN, VARIANCE, THRESHOLD)),
        "xi_desirability": 0.0,
    }
    assert _Acquisition.model_validate(payload).model_dump(mode="json") == payload
    for unsupported in ("survival_v999", None, 2, True):
        with pytest.raises(ValidationError):
            _Acquisition.model_validate({**payload, "numerical_policy": unsupported})


def test_stored_dispatch_replays_frozen_legacy_value_without_upgrading_its_payload():
    from app.statistics.bo_beta_policy import stored_beta_expected_improvement

    legacy = stored_beta_expected_improvement(MEAN, VARIANCE, THRESHOLD, numerical_policy=None)
    assert legacy.value == LEGACY_VALUE
    assert "numerical_policy" not in asdict(legacy)
    new = stored_beta_expected_improvement(MEAN, VARIANCE, THRESHOLD, numerical_policy=POLICY)
    assert asdict(new) == asdict(beta_expected_improvement(MEAN, VARIANCE, THRESHOLD))
    with pytest.raises(BayesianOptimizationError, match="numerical_policy_unsupported"):
        stored_beta_expected_improvement(MEAN, VARIANCE, THRESHOLD, numerical_policy="unknown")
    with pytest.raises(BayesianOptimizationError, match="precision_unsupported"):
        stored_beta_expected_improvement(0.5, 1e-12, 0.5, numerical_policy=None)


@pytest.mark.parametrize("mixed", [False, True])
def test_sampler_policy_is_emitted_and_legacy_nested_hash_is_unchanged(mixed):
    from app.api.v1.schemas.bo_desirability_batch_calculation import _Sampler
    from app.api.v1.schemas.bo_mixed_planning import MixedPlanningSampler
    from app.statistics.bo_desirability_batch_acquisition import DesirabilityBatchAcquisition

    state = SimpleNamespace(
        root_seed=1,
        _seeds={"response": 2},
        selected_count=0,
        sample_count=16,
        incumbent=0.5,
        xi=0.0,
        _conditions={},
        max_moment_evaluations=64,
        moment_evaluations=1,
        goals=[object()],
        integration_evaluations=10,
        candidate_evaluations=1,
        exact_selected_evaluations=0,
        factor_domains=() if mixed else None,
    )
    payload = DesirabilityBatchAcquisition.metadata(state)
    assert payload["numerical_policy"] == POLICY
    sampler_type = MixedPlanningSampler if mixed else _Sampler
    envelope = create_model("SamplerEnvelope", sampler=(sampler_type, ...))
    assert envelope.model_validate({"sampler": payload}).model_dump(mode="json") == {
        "sampler": payload
    }
    legacy = {
        "sampler": {key: value for key, value in payload.items() if key != "numerical_policy"}
    }
    restored = envelope.model_validate(legacy)
    assert restored.sampler.numerical_policy is None
    assert _canonical(restored.model_dump(mode="json")) == _canonical(legacy)
    assert json.loads(restored.model_dump_json()) == legacy
    with pytest.raises(ValidationError):
        sampler_type.model_validate({**payload, "numerical_policy": "unknown"})


@pytest.mark.parametrize("policy", [None, POLICY])
def test_conditional_score_proof_uses_stored_policy_and_rejects_mixed_policy(monkeypatch, policy):
    from app.services import bo_desirability_batch_contract as contract
    from app.statistics.bo_beta_policy import stored_beta_expected_improvement

    # Isolate score reduction from posterior validation. There are no models or fits.
    monkeypatch.setattr(contract, "composite_desirability", lambda values, goals: 0.5)
    value = stored_beta_expected_improvement(
        MEAN, VARIANCE, THRESHOLD, numerical_policy=policy
    ).value
    sampler = SimpleNamespace(
        numerical_policy=policy,
        selected_covariance={},
        effective_sample_count=2,
        baseline_threshold=THRESHOLD,
    )
    proof = SimpleNamespace(
        response_proofs={},
        thresholds=[THRESHOLD, THRESHOLD],
        sample_moments=[SimpleNamespace(mean=MEAN, variance=VARIANCE)] * 2,
    )
    item = SimpleNamespace(
        acquisition=SimpleNamespace(numerical_policy=policy),
        response_predictions=[],
        planning=SimpleNamespace(sampler=sampler, proof=proof, score=value, mc_standard_error=0.0),
    )
    items = [SimpleNamespace(acquisition=SimpleNamespace(numerical_policy=policy)), item]
    contract._validate_planning_proof(items, [], 1, [])
    item.planning.score = (
        LEGACY_VALUE if policy else beta_expected_improvement(MEAN, VARIANCE, THRESHOLD).value
    )
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        contract._validate_planning_proof(items, [], 1, [])
    item.planning.score = value
    sampler.numerical_policy = policy
    items[0].acquisition.numerical_policy = POLICY if policy is None else None
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        contract._validate_planning_proof(items, [], 1, [])
    items[0].acquisition.numerical_policy = policy
    sampler.numerical_policy = POLICY if policy is None else None
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        contract._validate_planning_proof(items, [], 1, [])


@pytest.mark.parametrize("policy", [None, POLICY])
def test_augmentation_replays_stored_base_ei_without_refitting(policy):
    from app.services.bo_augmentation_contract import _model_row
    from app.statistics.bo_beta_policy import stored_beta_expected_improvement

    acquisition = {
        "kind": "desirability_beta_expected_improvement",
        **asdict(
            stored_beta_expected_improvement(MEAN, VARIANCE, THRESHOLD, numerical_policy=policy)
        ),
        "xi_desirability": 0.0,
    }
    row = {
        "response_predictions": [],
        "desirability_moments": {"mean": MEAN, "variance": VARIANCE},
        "acquisition": acquisition,
    }
    snapshot = {
        "response_models": [],
        "calculation_request": {"xi_desirability": 0.0},
        "incumbent": {"latent_incumbent_value": THRESHOLD},
    }
    _model_row(row, snapshot, "refine")
    acquisition["value"] *= 1.01
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        _model_row(row, snapshot, "refine")


@pytest.mark.parametrize("policy", [None, POLICY])
def test_new_q1_worker_response_requires_explicit_current_policy(monkeypatch, policy):
    from test_bo_desirability_contract import calculation_request

    from app.services import bo_desirability_worker as worker
    from app.services.analysis_run_execution import canonical_json_bytes

    request = worker.DesirabilityCalculationRequest.model_validate(calculation_request())
    acquisition = _legacy_payload()
    if policy is not None:
        acquisition["numerical_policy"] = policy
    raw = {"items": [{"acquisition": acquisition}]}
    parsed = SimpleNamespace()
    monkeypatch.setattr(
        worker.DesirabilityCalculationResult, "model_validate_json", lambda *args, **kwargs: parsed
    )
    monkeypatch.setattr(worker, "validate_calculation_result", lambda *args: None)
    monkeypatch.setattr(
        worker,
        "_run_owned_worker",
        lambda encoded, **kwargs: canonical_json_bytes(
            {
                "status": "ok",
                "request_sha256": hashlib.sha256(encoded).hexdigest(),
                "result": raw,
            }
        ),
    )
    if policy is None:
        with pytest.raises(BayesianOptimizationError, match="result_invalid"):
            worker.run_desirability_calculation(request)
    else:
        assert worker.run_desirability_calculation(request).calculation is parsed


@pytest.mark.parametrize("policy", [None, POLICY])
def test_new_planning_worker_response_requires_explicit_current_policy(monkeypatch, policy):
    from test_bo_planning_worker import _Output

    from app.services import bo_planning_contract as contract
    from app.services import bo_planning_worker as worker
    from app.services.analysis_run_execution import canonical_json_bytes

    acquisition = _legacy_payload()
    if policy is not None:
        acquisition["numerical_policy"] = policy
    raw = [{"acquisition": acquisition}]
    monkeypatch.setattr(worker, "_calculate", lambda *args: raw)
    monkeypatch.setattr(contract, "validate_planning_evaluation", lambda *args, **kwargs: None)
    output = _Output()
    worker._worker_entry(
        output,
        canonical_json_bytes(
            {
                "operation": "evaluate",
                "payload": {
                    "snapshot": {},
                    "points": [],
                    "eligibility_excluded_normalized": [],
                },
                "time_budget_ms": 1000,
            }
        ),
    )
    message = json.loads(output.data)
    assert output.closed
    if policy is None:
        assert message == {"status": "error", "code": "bayesian_planning_result_invalid"}
    else:
        assert message["status"] == "ok"
        assert message["result"] == raw
