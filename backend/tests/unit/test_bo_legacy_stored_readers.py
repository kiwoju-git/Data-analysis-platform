"""Historical receipt reads must not become fresh legacy Beta calculations.

The synthetic other-platform value is simulated, not a native Linux result.
Only storage/source lookup seams are replaced; the saved augmentation reader,
typed JSON, SHA checks and selected-row contract remain real. Augmentation cases
fit no models; the two persisted desirability cases use bounded fixture fits.
"""

import copy
import hashlib
import json
import math
import sqlite3
from collections import Counter
from dataclasses import asdict, replace
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from threadpoolctl import threadpool_limits

from app.api.v1.schemas.bo_augmentation import AUGMENTATION_REQUEST, AUGMENTATION_RESULT
from app.api.v1.schemas.bo_planning import CandidateRow
from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services import bo_augmentation as service
from app.services.bo_augmentation_contract import validate_augmentation_binding
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_augmentation import REFINE
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.storage import bo_planning as storage
from app.storage.metadata import metadata_db_path
from tests.unit.test_bo_augmentation_contract import receipt

MEAN, VARIANCE, THRESHOLD = 0.9, 1e-9, 0.9000316227766018
OTHER_PLATFORM_LEGACY_EI = 2.633949561237081e-6
POLICY = "positive_beta_integral_v2"


def _forbidden(*args, **kwargs):
    pytest.fail("a historical receipt read must not fit or recalculate legacy Beta EI")


def _encode_record(state):
    record = state.record
    record["config_json"] = storage.planning_json(state.request)
    record["config_sha256"] = hashlib.sha256(record["config_json"].encode()).hexdigest()
    record["result_json"] = storage.planning_json(state.result)
    record["result_sha256"] = hashlib.sha256(record["result_json"].encode()).hexdigest()


@pytest.fixture
def saved_augmentation(tmp_path, monkeypatch):
    result, arguments = receipt(REFINE, batch_size=2)
    snapshot = arguments["snapshot"]
    snapshot["calculation_request"]["xi_desirability"] = 0.0
    snapshot["incumbent"]["latent_incumbent_value"] = THRESHOLD
    concentration = MEAN * (1 - MEAN) / VARIANCE - 1
    for index, row in enumerate(result["selected_rows"]):
        row["desirability_moments"].update(
            mean=MEAN, second_moment=MEAN**2 + VARIANCE, variance=VARIANCE
        )
        row["acquisition"] = {
            "kind": "desirability_beta_expected_improvement",
            "value": OTHER_PLATFORM_LEGACY_EI,
            "threshold": THRESHOLD,
            "distribution": "beta_moment_match",
            "alpha": MEAN * concentration,
            "beta": (1 - MEAN) * concentration,
            "xi_desirability": 0.0,
        }
        result["augmentation"]["steps"][index]["score"] = (
            OTHER_PLATFORM_LEGACY_EI if index == 0 else math.sqrt(VARIANCE)
        )
    study_id, study_version_id, history_id = (UUID(int=index) for index in (3, 4, 5))
    source = {
        "definition_sha256": "d" * 64,
        "source_history_revision_id": str(history_id),
        "history_sha256": "b" * 64,
    }
    candidate = {**source, "rows_sha256": "a" * 64, "source_trial_count": 3}
    model = {**source, "snapshot_sha256": "c" * 64}
    request = AUGMENTATION_REQUEST.validate_python(
        {
            "schema_version": 2,
            "request_id": str(UUID(int=6)),
            "expected_study_version_id": str(study_version_id),
            "expected_definition_sha256": source["definition_sha256"],
            "expected_history_revision_id": str(history_id),
            "expected_history_sha256": source["history_sha256"],
            "expected_trial_count": 3,
            "candidate_revision_id": str(UUID(int=2)),
            "expected_rows_sha256": candidate["rows_sha256"],
            "model_id": str(UUID(int=1)),
            "expected_model_sha256": model["snapshot_sha256"],
            "policy": REFINE,
            "batch_size": 2,
            "total_trial_budget": 20,
            **{
                key: arguments["request"][key]
                for key in (
                    "duplicate_tolerance",
                    "min_batch_distance_normalized",
                    "time_budget_ms",
                    "max_evaluations",
                    "max_moment_evaluations",
                )
            },
        }
    ).model_dump(mode="json")
    result = AUGMENTATION_RESULT.validate_python(result).model_dump(mode="json", exclude_unset=True)
    study = SimpleNamespace(
        study_id=study_id,
        study_version_id=study_version_id,
        definition_sha256=source["definition_sha256"],
        status="active",
        observation_history=SimpleNamespace(
            history_revision_id=history_id,
            observation_history_sha256=source["history_sha256"],
        ),
        factors=[
            SimpleNamespace(factor_id=item["factor_id"]) for item in arguments["request"]["factors"]
        ],
        trials=[
            SimpleNamespace(
                trial_number=index + 1,
                normalized_coordinates=dict(zip(("z", "a"), point, strict=True)),
            )
            for index, point in enumerate(arguments["existing_coordinates"])
        ],
    )
    state = SimpleNamespace(
        settings=Settings(workspace_root=tmp_path),
        study=study,
        selection_id=UUID(int=7),
        request=request,
        result=result,
        arguments=arguments,
        source=source,
        candidate=candidate,
        model=model,
        record={
            "schema_version": 2,
            "request_id": request["request_id"],
            "candidate_revision_id": request["candidate_revision_id"],
            "model_id": request["model_id"],
            "created_at": "2026-11-13T00:00:00Z",
            "confirmed_batch_id": None,
        },
    )
    _encode_record(state)

    def read_record(root, selection_id, study_version):
        assert root == state.settings.workspace_root
        assert selection_id == str(state.selection_id)
        assert study_version == str(state.study.study_version_id)
        storage._documents(
            state.record,
            (("config_json", "config_sha256"), ("result_json", "result_sha256")),
        )
        return state.record

    monkeypatch.setattr(service, "get_bayesian_study", lambda *args: state.study)
    monkeypatch.setattr(storage, "get_planning_selection", read_record)

    def no_renewal(root, selection_id, study_version):
        assert root == state.settings.workspace_root
        assert selection_id == str(state.selection_id)
        assert study_version == str(state.study.study_version_id)
        return None  # This historical fixture has no renewal sidecar or real database.

    monkeypatch.setattr(storage, "get_augmentation_renewal", no_renewal)
    monkeypatch.setattr(
        service,
        "_source_candidate",
        lambda *args: (
            state.candidate,
            [CandidateRow.model_validate(row) for row in state.arguments["rows"]],
            state.source,
            state.arguments["request"]["duplicate_tolerance"],
        ),
    )
    monkeypatch.setattr(service, "_read_model", lambda *args: (state.model, snapshot, None))
    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", _forbidden)
    monkeypatch.setattr(service, "_run", _forbidden)
    return state


def _read(state):
    return service.get_augmentation_selection(
        state.settings, state.study.study_id, state.selection_id
    )


def _assert_rejected(state):
    with pytest.raises(ApiError) as raised:
        _read(state)
    assert raised.value.code in {
        "bayesian_planning_artifact_invalid",
        "bayesian_candidate_source_changed",
    }


def test_actual_saved_legacy_reader_preserves_other_platform_receipt_bytes_and_hash(
    saved_augmentation, monkeypatch
):
    state = saved_augmentation
    original = copy.deepcopy(state.record)
    monkeypatch.setattr("app.statistics.bo_beta_legacy.beta_expected_improvement", _forbidden)
    restored = _read(state)
    assert restored.calculation.selected_rows[0].acquisition.value == OTHER_PLATFORM_LEGACY_EI
    assert restored.result_sha256 == original["result_sha256"]
    assert restored.config_sha256 == original["config_sha256"]
    assert (
        storage.planning_json(restored.calculation.model_dump(mode="json", exclude_unset=True))
        == original["result_json"]
    )
    assert (
        "numerical_policy"
        not in json.loads(original["result_json"])["selected_rows"][0]["acquisition"]
    )
    assert state.record == original


def _legacy_replay_platform(monkeypatch, replay_platform):
    if replay_platform == "simulated_linux_matching_receipt":
        from app.statistics import bo_beta_legacy

        native = bo_beta_legacy.beta_expected_improvement

        def matching_replay(*args, **kwargs):
            return replace(native(*args, **kwargs), value=OTHER_PLATFORM_LEGACY_EI)

        monkeypatch.setattr(bo_beta_legacy, "beta_expected_improvement", matching_replay)


def _alter_ei_from_local_legacy_replay(state):
    from app.statistics.bo_beta_policy import stored_beta_expected_improvement

    snapshot = state.arguments["snapshot"]
    for row in state.result["selected_rows"]:
        moments = row["desirability_moments"]
        row["acquisition"].update(
            asdict(
                stored_beta_expected_improvement(
                    moments["mean"],
                    moments["variance"],
                    snapshot["incumbent"]["latent_incumbent_value"],
                    xi=snapshot["calculation_request"]["xi_desirability"],
                    numerical_policy=None,
                )
            )
        )
    acquisition = state.result["selected_rows"][0]["acquisition"]
    step = state.result["augmentation"]["steps"][0]
    step["score"] = acquisition["value"]
    # A valid local baseline rules out unrelated source/options/shape failures.
    validate_augmentation_binding(state.result, **state.arguments)
    acquisition["value"] *= 1.01
    step["score"] = acquisition["value"]
    _encode_record(state)


@pytest.mark.parametrize("replay_platform", ["native", "simulated_linux_matching_receipt"])
def test_same_legacy_result_still_fails_strict_new_calculation_binding(
    saved_augmentation, monkeypatch, replay_platform
):
    _legacy_replay_platform(monkeypatch, replay_platform)
    state = saved_augmentation
    _alter_ei_from_local_legacy_replay(state)
    with pytest.raises(BayesianOptimizationError, match="augmentation_result_invalid"):
        validate_augmentation_binding(state.result, **state.arguments)


@pytest.mark.parametrize("replay_platform", ["native", "simulated_linux_matching_receipt"])
def test_commit_boundary_still_rejects_a_legacy_receipt_that_reads(
    saved_augmentation, monkeypatch, replay_platform
):
    _legacy_replay_platform(monkeypatch, replay_platform)
    state = saved_augmentation
    _alter_ei_from_local_legacy_replay(state)
    restored = _read(state)
    assert restored.calculation.model_dump(mode="json", exclude_unset=True) == state.result
    rows = [CandidateRow.model_validate(row) for row in state.arguments["rows"]]
    with pytest.raises(BayesianOptimizationError, match="augmentation_result_invalid"):
        service.validate_augmentation_for_commit(
            state.study, restored.request, restored.calculation, rows, state.arguments["snapshot"]
        )


def test_current_policy_saved_reader_still_recalculates_and_rejects_altered_ei(
    saved_augmentation,
):
    state = saved_augmentation
    for row in state.result["selected_rows"]:
        row["acquisition"] = {
            "kind": "desirability_beta_expected_improvement",
            **asdict(beta_expected_improvement(MEAN, VARIANCE, THRESHOLD)),
            "xi_desirability": 0.0,
        }
    state.result["selected_rows"][0]["acquisition"]["value"] *= 1.01
    state.result["augmentation"]["steps"][0]["score"] = state.result["selected_rows"][0][
        "acquisition"
    ]["value"]
    _encode_record(state)
    _assert_rejected(state)


@pytest.mark.parametrize("field", ["config_sha256", "result_sha256"])
def test_saved_legacy_reader_rejects_original_checksum_mismatch(saved_augmentation, field):
    state = saved_augmentation
    state.record[field] = "f" * 64
    _assert_rejected(state)


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("source", "definition_sha256", "e" * 64),
        ("source", "source_history_revision_id", str(UUID(int=99))),
        ("source", "history_sha256", "e" * 64),
        ("candidate", "source_trial_count", 4),
        ("candidate", "rows_sha256", "e" * 64),
        ("model", "snapshot_sha256", "e" * 64),
        ("model", "definition_sha256", "e" * 64),
        ("model", "source_history_revision_id", str(UUID(int=99))),
        ("model", "history_sha256", "e" * 64),
    ],
)
def test_saved_legacy_reader_keeps_source_and_model_binding(
    saved_augmentation, target, field, value
):
    state = saved_augmentation
    getattr(state, target)[field] = value
    _assert_rejected(state)


@pytest.mark.parametrize(
    "field,value",
    [
        ("batch_size", 1),
        ("duplicate_tolerance", 1e-5),
        ("time_budget_ms", 59000),
        ("max_evaluations", 999),
        ("max_moment_evaluations", 4095),
        ("min_batch_distance_normalized", 1.0),
    ],
)
def test_saved_legacy_reader_keeps_options_binding(saved_augmentation, field, value):
    state = saved_augmentation
    state.request[field] = value
    _encode_record(state)
    _assert_rejected(state)


@pytest.mark.parametrize(
    "field,value",
    [
        ("value", "0.000002633949561237081"),
        ("value", True),
        ("value", -1e-9),
        ("value", 1.00001),
        ("threshold", THRESHOLD + 0.01),
        ("distribution", "point_mass"),
        ("alpha", 1.0),
        ("alpha", None),
        ("beta", 1.0),
        ("beta", None),
        ("xi_desirability", 0.01),
        ("numerical_policy", None),
        ("numerical_policy", "unknown"),
    ],
)
def test_saved_legacy_reader_keeps_acquisition_structure_and_moment_links(
    saved_augmentation, field, value
):
    state = saved_augmentation
    state.result["selected_rows"][0]["acquisition"][field] = value
    _encode_record(state)
    _assert_rejected(state)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_saved_legacy_reader_does_not_accept_nonfinite_json(saved_augmentation, value):
    state = saved_augmentation
    state.result["selected_rows"][0]["acquisition"]["value"] = value
    # Deliberately bypass the canonical writer to simulate a malformed stored file.
    encoded = json.dumps(state.result, sort_keys=True, separators=(",", ":"), allow_nan=True)
    state.record["result_json"] = encoded
    state.record["result_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    _assert_rejected(state)


@pytest.mark.parametrize("defect", ["response_id", "duplicate_response", "score", "row_order"])
def test_saved_legacy_reader_keeps_response_and_saved_cross_field_consistency(
    saved_augmentation, defect
):
    state = saved_augmentation
    predictions = state.result["selected_rows"][0]["response_predictions"]
    if defect == "response_id":
        predictions[0]["response_id"] = "unknown"
    elif defect == "duplicate_response":
        predictions[0]["response_id"] = predictions[1]["response_id"]
    elif defect == "score":
        state.result["augmentation"]["steps"][0]["score"] *= 1.01
    else:
        state.result["selected_rows"].reverse()
    _encode_record(state)
    _assert_rejected(state)


def test_saved_legacy_reader_rejects_mathematically_impossible_payoff(saved_augmentation):
    state = saved_augmentation
    state.result["selected_rows"][0]["acquisition"]["value"] = 0.2
    state.result["augmentation"]["steps"][0]["score"] = 0.2
    _encode_record(state)
    _assert_rejected(state)


@pytest.mark.parametrize("field,value", [("score", 0.2), ("mc_standard_error", 0.03)])
def test_stored_conditional_receipt_rejects_mathematically_impossible_summary(
    monkeypatch, field, value
):
    from app.services import bo_desirability_batch_contract as contract
    from app.services.bo_acquisition_receipts import _ValidationBoundary

    monkeypatch.setattr(contract, "composite_desirability", lambda values, goals: 0.5)
    count = 16
    planning = SimpleNamespace(
        sampler=SimpleNamespace(
            numerical_policy=None,
            selected_covariance={},
            effective_sample_count=count,
            baseline_threshold=THRESHOLD,
        ),
        proof=SimpleNamespace(
            response_proofs={},
            thresholds=[THRESHOLD] * count,
            sample_moments=[SimpleNamespace(mean=MEAN, variance=VARIANCE)] * count,
        ),
        score=OTHER_PLATFORM_LEGACY_EI,
        mc_standard_error=0.0,
    )
    item = SimpleNamespace(
        acquisition=SimpleNamespace(numerical_policy=None),
        response_predictions=[],
        planning=planning,
    )
    items = [SimpleNamespace(acquisition=SimpleNamespace(numerical_policy=None)), item]
    setattr(planning, field, value)
    with pytest.raises(BayesianOptimizationError, match="result_invalid"):
        contract._validate_planning_proof(
            items, [], 1, [], boundary=_ValidationBoundary.STORED_RECEIPT
        )


def test_frozen_legacy_compatibility_grid_is_not_a_new_accuracy_reference():
    from app.services.bo_acquisition_receipts import validate_legacy_acquisition_receipt
    from app.statistics.bo_beta_legacy import beta_expected_improvement as legacy

    errors = Counter()
    returned = 0
    for mean in (0.01, 0.1, 0.5, 0.9, 0.99, 1 - 1e-10):
        for fraction in (0.0, 1e-10, 1e-8, 1e-6, 1e-3, 0.01, 0.25, 0.9, 1.0):
            variance = mean * (1 - mean) * fraction
            for threshold in (
                0.0,
                max(0.0, mean - 1e-8),
                mean,
                min(1.0, mean + 1e-8),
                0.9,
                0.99,
                math.nextafter(1.0, 0.0),
                1.0,
            ):
                try:
                    old = legacy(mean, variance, threshold)
                except BayesianOptimizationError as exc:
                    errors[str(exc)] += 1
                    continue
                returned += 1
                acquisition = {
                    "kind": "desirability_beta_expected_improvement",
                    **asdict(old),
                    "xi_desirability": 0.0,
                }
                validate_legacy_acquisition_receipt(acquisition, mean, variance, threshold, xi=0.0)
    assert returned + sum(errors.values()) == 432
    assert returned >= 300
    assert set(errors) == {"bayesian_desirability_beta_precision_unsupported"}
    assert errors["bayesian_desirability_beta_precision_unsupported"] >= 48


@pytest.mark.parametrize("ordered", [False, True])
def test_actual_persisted_desirability_reader_preserves_historical_q1_and_batch(
    tmp_path, monkeypatch, ordered
):
    """Two bounded fixture calculations, then real immutable database reads.

    This constructs simulated historical receipts, not native Linux artifacts.
    Fixture generation uses the real small synthetic calculation once per case;
    no computation result is fabricated for a new review or confirmation.
    """
    from app.api.v1.schemas.bo_desirability_batch_calculation import (
        DesirabilityBatchCalculationResult,
    )
    from app.api.v1.schemas.bo_desirability_calculation import DesirabilityCalculationResult
    from app.services import bo_desirability_worker
    from app.services.bayesian_noise_recommendations import _json, _sha
    from app.statistics.bo_beta_policy import stored_beta_expected_improvement
    from app.statistics.bo_desirability_batch_core import calculate_desirability_batch
    from app.statistics.bo_desirability_core import calculate_desirability_recommendation
    from tests.unit.test_bayesian_multiresponse_lifecycle import url
    from tests.unit.test_bo_desirability_public_batch import batch_request
    from tests.unit.test_bo_desirability_review_api import completed, review_request

    def worker(request):
        with threadpool_limits(limits=1):
            calculated = (
                calculate_desirability_batch(request.worker_payload())
                if ordered
                else calculate_desirability_recommendation(request.worker_payload())
            )
        result_type = (
            DesirabilityBatchCalculationResult if ordered else DesirabilityCalculationResult
        )
        return SimpleNamespace(calculation=result_type.model_validate_json(_json(calculated)))

    monkeypatch.setattr(
        bo_desirability_worker,
        "run_desirability_batch_calculation" if ordered else "run_desirability_calculation",
        worker,
    )
    settings = Settings(workspace_root=tmp_path / "historical saved reader")
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        request = batch_request(study) if ordered else review_request(study)
        response = client.post(url(study) + "/desirability-reviews", json=request)
        assert response.status_code == 200, response.text
        review = response.json()
        confirmed = client.post(
            url(study) + f"/desirability-reviews/{review['review_id']}/confirm",
            json={"expected_config_sha256": review["config_sha256"]},
        )
        assert confirmed.status_code == 201, confirmed.text
        batch_id = confirmed.json()["batch_id"]
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            encoded = db.execute(
                "SELECT result_json FROM bayesian_recommendation_batches WHERE batch_id=?",
                (batch_id,),
            ).fetchone()[0]
            historical = json.loads(encoded)
            calculation = historical["calculation"]
            for item in calculation["items"]:
                moments = item["desirability_moments"]
                old = stored_beta_expected_improvement(
                    moments["mean"],
                    moments["variance"],
                    calculation["incumbent"]["latent_incumbent_value"],
                    xi=request["xi_desirability"],
                    numerical_policy=None,
                )
                assert old.distribution == "beta_moment_match"
                item["acquisition"] = {
                    "kind": "desirability_beta_expected_improvement",
                    **asdict(old),
                    "value": old.value * (1 + 1e-6),
                    "xi_desirability": request["xi_desirability"],
                }
                if ordered:
                    item["planning"]["sampler"].pop("numerical_policy")
                    if item["rank"] == 1:
                        item["planning"]["score"] = item["acquisition"]["value"]
                    else:
                        item["planning"]["score"] *= 1 + 1e-6
                        item["planning"]["mc_standard_error"] *= 1 + 1e-6
            historical["result_sha256"] = "0" * 64
            historical["result_sha256"] = _sha(historical)
            historical_json = _json(historical)
            historical_hash = hashlib.sha256(historical_json.encode()).hexdigest()
            db.execute(
                "UPDATE bayesian_recommendation_batches SET result_json=?,result_sha256=? "
                "WHERE batch_id=?",
                (historical_json, historical_hash, batch_id),
            )
        monkeypatch.setattr("app.statistics.bo_beta_legacy.beta_expected_improvement", _forbidden)
        monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", _forbidden)
        saved_url = url(study) + f"/desirability-recommendations/{batch_id}"
        restored = client.get(saved_url)
        assert restored.status_code == 200, restored.text
        assert restored.json()["calculation"] == historical["calculation"]
        assert restored.json()["result_sha256"] == historical["result_sha256"]
        replayed = client.post(
            url(study) + f"/desirability-reviews/{review['review_id']}/confirm",
            json={"expected_config_sha256": review["config_sha256"]},
        )
        assert replayed.status_code == 201, replayed.text
        assert replayed.json() == restored.json()
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            assert db.execute(
                "SELECT result_json,result_sha256 FROM bayesian_recommendation_batches "
                "WHERE batch_id=?",
                (batch_id,),
            ).fetchone() == (historical_json, historical_hash)
