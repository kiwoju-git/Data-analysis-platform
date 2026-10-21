import hashlib
import json
import sqlite3
from uuid import uuid4

import pytest
from bo_worker_probe import large_result, slow_result
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_bayesian_batches_api import _batch_request, _completed_study, _study_request

from app.api.v1.schemas.bayesian_noise import (
    BayesianNoiseBatchCreateRequest,
    BayesianNoiseSingleCreateRequest,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services.analysis_run_execution import canonical_json_bytes
from app.services.dedicated_report_sources import (
    list_dedicated_report_sources,
    prepare_dedicated_report_source,
)
from app.storage.metadata import metadata_db_path


def _request():
    return {
        "schema_version": 2,
        "expected_history_revision_id": str(uuid4()),
        "expected_history_sha256": "a" * 64,
        "acquisition": {"kind": "expected_improvement"},
    }


def test_noise_request_defaults_are_explicit_and_separate_from_legacy():
    request = BayesianNoiseBatchCreateRequest.model_validate(_request())
    assert request.surrogate.noise_mode == "estimate"
    assert request.surrogate.initial_noise_variance_scaled == 1e-2
    assert request.surrogate.lower_noise_variance_scaled == 1e-6
    assert request.observation_policy.mode == "retain_raw"
    assert request.batch_options.posterior_sample_count == 64
    assert request.batch_options.min_batch_distance_normalized == 0
    assert request.search.batch_policy == "greedy_mc_joint_latent_improvement_v2"


@pytest.mark.parametrize(
    "policy",
    [
        {"lower_noise_variance_scaled": 2, "upper_noise_variance_scaled": 1},
        {"initial_noise_variance_scaled": 2},
        {"initial_noise_variance_scaled": 0},
        {"lower_noise_variance_scaled": float("nan")},
        {"noise_mode": "fixed"},
        {"noise_mode": "fixed", "fixed_noise_sd": 0},
        {"noise_mode": "near_noiseless", "fixed_noise_sd": 1},
    ],
)
def test_invalid_noise_request_is_rejected_without_reordering_or_fallback(policy):
    with pytest.raises(ValidationError):
        BayesianNoiseBatchCreateRequest.model_validate({**_request(), "surrogate": policy})


def test_nearby_requires_explicit_factor_tolerances():
    with pytest.raises(ValidationError):
        BayesianNoiseBatchCreateRequest.model_validate(
            {**_request(), "observation_policy": {"mode": "nearby_diagnostics"}}
        )


def test_new_single_request_cannot_accept_legacy_policy_fields():
    payload = _request()
    payload.pop("acquisition")
    request = BayesianNoiseSingleCreateRequest.model_validate(payload)
    assert request.search.xi == 0.01
    with pytest.raises(ValidationError):
        BayesianNoiseSingleCreateRequest.model_validate({**payload, "batch_size": 2})


def test_noise_target_batch_roundtrip_and_pending_guard(tmp_path, monkeypatch):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = _completed_study(client, goal_type="match_target")
        body = _batch_request(
            study["observation_history"]["history_revision_id"],
            batch_size=2,
            kind="expected_target_improvement",
        )
        body.update(
            schema_version=2,
            expected_history_sha256=study["observation_history"]["observation_history_sha256"],
        )
        body["search"]["batch_policy"] = "greedy_mc_joint_latent_improvement_v2"
        path = f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches"
        created = client.post(path, json=body)
        assert created.status_code == 201, created.json()
        result = created.json()
        assert result["result_schema_version"] == 2
        assert result["shared_model"]["noise"]["mode"] == "estimate"
        assert result["items"][1]["planning"]["conditioned_on_selected_ranks"] == [1]
        assert result["shared_model"]["raw_observation_count"] == 2
        restored = client.get(f"{path}/{result['batch_id']}")
        assert restored.status_code == 200, restored.json()
        assert restored.json() == result
        assert client.get(f"/api/v1/bayesian-studies/{study['study_id']}").status_code == 200
        blocked = client.post(path, json=body)
        assert blocked.status_code == 409, blocked.json()
        assert (
            blocked.json()["error"]["code"] == "bayesian_optimization_pending_recommendation_exists"
        )
        assert client.get(f"{path}/latest").json()["item"] == result
        assert client.get(path).json()["items"] == [result]
        history_id = body["expected_history_revision_id"]
        for item in result["items"]:
            completed = client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}/trials/{item['trial']['trial_id']}/observation",
                json={"objective_value": 0.5, "expected_history_revision_id": history_id},
            )
            assert completed.status_code == 200, completed.json()
            history_id = completed.json()["observation_history"]["history_revision_id"]
        restored = client.get(f"{path}/{result['batch_id']}")
        assert restored.status_code == 200, restored.json()
        assert restored.json()["batch_state"] == "completed"
        assert restored.json()["items"][0]["trial"]["state"] == "pending"
        source = next(
            item.source
            for item in list_dedicated_report_sources(
                Settings(workspace_root=tmp_path), "bayesian_history_revision"
            ).items
            if item.source.attachment.kind == "batch"
        )

        def forbidden(*args, **kwargs):
            raise AssertionError("report must not recompute")

        monkeypatch.setattr(
            "app.statistics.bo_recommendation_core.calculate_noise_aware_batch", forbidden
        )
        report = prepare_dedicated_report_source(Settings(workspace_root=tmp_path), source, "en")
        assert report.payload["attachment"]["shared_model"]["noise"]["mode"] == "estimate"
        assert "latent_standard_deviation" in report.body.render()
        summary = next(
            section for section in report.body.sections if section.section_id == "noise_summary"
        )
        assert summary.status == "rendered"
        for label in (
            "Base posterior mean",
            "Latent SD",
            "New-observation predictive SD",
            "Jitter",
            "not exact qNEI",
        ):
            assert label in summary.markup
        assert result["items"][1]["planning"]["sample_seed"] in summary.markup
        korean = prepare_dedicated_report_source(Settings(workspace_root=tmp_path), source, "ko")
        assert "실제 관측 기반 예측 평균" in korean.body.render()


def _noise_request(study, *, count=1):
    body = _batch_request(
        study["observation_history"]["history_revision_id"],
        batch_size=count,
        kind="expected_improvement",
    )
    body.update(
        schema_version=2,
        expected_history_sha256=study["observation_history"]["observation_history_sha256"],
    )
    body["search"]["batch_policy"] = "greedy_mc_joint_latent_improvement_v2"
    return body


@pytest.mark.parametrize("goal", ["maximize", "minimize"])
@pytest.mark.parametrize("response_scale", [1.0, 1000.0])
def test_direction_normalization_nonzero_mean_roundtrips_without_history_mutation(
    tmp_path, goal, response_scale
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        created = client.post("/api/v1/bayesian-studies", json=_study_request(goal_type=goal))
        assert created.status_code == 201, created.json()
        study = created.json()
        history_id = study["observation_history"]["history_revision_id"]
        for trial, raw_value in zip(study["trials"], [10.0, 14.0], strict=True):
            completed = client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
                json={
                    "objective_value": raw_value * response_scale,
                    "expected_history_revision_id": history_id,
                },
            )
            assert completed.status_code == 200, completed.json()
            history_id = completed.json()["observation_history"]["history_revision_id"]
        study = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
        before_history = canonical_json_bytes(study["observation_history"])
        path = f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches"
        response = client.post(path, json=_noise_request(study))
        assert response.status_code == 201, response.json()
        result = response.json()
        direction = -1 if goal == "minimize" else 1
        assert result["shared_model"]["normalization"]["mean"] == direction * 12 * response_scale
        assert result["shared_model"]["normalization"]["scale"] == 2 * response_scale
        assert (
            result["incumbent"]["best_observed_objective"]
            == (10 if goal == "minimize" else 14) * response_scale
        )
        assert result["items"][0]["predicted_objective_mean"] > 0
        restored = client.get(f"{path}/{result['batch_id']}")
        assert restored.status_code == 200, restored.json()
        assert restored.json() == result
        current = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert current.status_code == 200, current.json()
        assert canonical_json_bytes(current.json()["observation_history"]) == before_history
        assert current.json()["trials"][:2] == study["trials"]


def test_legacy_single_target_adapter_uses_batch_core(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = _completed_study(client, goal_type="match_target")
        response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json={
                "schema_version": 2,
                "expected_history_revision_id": study["observation_history"]["history_revision_id"],
                "expected_history_sha256": study["observation_history"][
                    "observation_history_sha256"
                ],
                "search": {
                    "candidate_count": 32,
                    "local_start_count": 0,
                    "model_max_iterations": 20,
                },
            },
        )
        assert response.status_code == 201, response.json()
        data = response.json()
        assert data["batch_size"] == 1 and data["result_schema_version"] == 2
        assert data["items"][0]["planning"]["effective_sample_count"] == 0
        assert data["acquisition"]["kind"] == "expected_target_improvement"
        restored = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches/{data['batch_id']}"
        )
        assert restored.status_code == 200, restored.json()


def test_stale_hash_budget_and_worker_failure_leave_no_trials(tmp_path, monkeypatch):
    from app.services import bayesian_noise_recommendations as service

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = _completed_study(client)
        path = f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches"
        body = _noise_request(study)
        bad = {**body, "expected_history_sha256": "0" * 64}
        assert (
            client.post(path, json=bad).json()["error"]["code"]
            == "bayesian_optimization_history_stale"
        )
        budget = {**body, "search": {**body["search"], "total_trial_budget": 2}}
        assert (
            client.post(path, json=budget).json()["error"]["code"]
            == "bayesian_optimization_batch_budget_exceeded"
        )

        def fail(*args, **kwargs):
            raise ApiError(
                code="bayesian_optimization_batch_incomplete", message="Incomplete", status_code=409
            )

        monkeypatch.setattr(service, "_run_worker", fail)
        assert client.post(path, json=body).status_code == 409
        current = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
        assert current["trials"] == study["trials"]
        assert current["observation_history"] == study["observation_history"]
        assert client.get(path).json()["total"] == 0


def test_new_batch_does_not_rewrite_legacy_snapshot(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = _completed_study(client)
        path = f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches"
        legacy = client.post(
            path,
            json=_batch_request(
                study["observation_history"]["history_revision_id"],
                batch_size=1,
                kind="expected_improvement",
            ),
        )
        assert legacy.status_code == 201, legacy.json()
        identifier = legacy.json()["batch_id"]
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            before = connection.execute(
                "SELECT config_json,result_json,config_sha256,result_sha256 "
                "FROM bayesian_recommendation_batches WHERE batch_id=?",
                (identifier,),
            ).fetchone()
        trial = legacy.json()["items"][0]["trial"]
        assert (
            client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
                json={
                    "objective_value": 0.5,
                    "expected_history_revision_id": study["observation_history"][
                        "history_revision_id"
                    ],
                },
            ).status_code
            == 200
        )
        study = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
        created = client.post(path, json=_noise_request(study))
        assert created.status_code == 201, created.json()
        assert client.get(f"{path}/{identifier}").status_code == 200
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            after = connection.execute(
                "SELECT config_json,result_json,config_sha256,result_sha256 "
                "FROM bayesian_recommendation_batches WHERE batch_id=?",
                (identifier,),
            ).fetchone()
        assert before == after
        assert '"schema_version":2' not in before[0]


@pytest.mark.parametrize("study_version", ["0.6.0", "0.7.0"])
def test_current_and_legacy_study_use_versioned_recommendations_and_close(
    tmp_path, monkeypatch, study_version
):
    from test_bayesian_study_lifecycle_api import _close_request

    from app.analyses import registry

    method_id = "doe.bayesian_optimization"
    assert registry.METHOD_VERSIONS[method_id] == "0.7.0"
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        with monkeypatch.context() as legacy:
            if study_version == "0.6.0":
                legacy.setitem(registry.METHOD_VERSIONS, method_id, "0.6.0")
                legacy.setitem(
                    registry.METHOD_BY_ID,
                    method_id,
                    registry.METHOD_BY_ID[method_id].model_copy(update={"method_version": "0.6.0"}),
                )
            study = _completed_study(client)
        assert study["method_version"] == study_version
        definition_hash = study["definition_sha256"]
        path = f"/api/v1/bayesian-studies/{study['study_id']}"
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            original_definition = connection.execute(
                "SELECT * FROM bayesian_study_versions WHERE study_version_id=?",
                (study["study_version_id"],),
            ).fetchone()
        for request_version, expected_method in [(1, "0.6.0"), (2, "0.7.0")]:
            request = (
                _noise_request(study)
                if request_version == 2
                else _batch_request(
                    study["observation_history"]["history_revision_id"],
                    batch_size=1,
                    kind="expected_improvement",
                )
            )
            created = client.post(f"{path}/recommendation-batches", json=request)
            assert created.status_code == 201, created.json()
            result = created.json()
            assert result["method_version"] == expected_method
            assert result["result_schema_version"] == request_version
            item = result["items"][0]
            completed = client.put(
                f"{path}/trials/{item['trial']['trial_id']}/observation",
                json={
                    "objective_value": 0.5,
                    "expected_history_revision_id": study["observation_history"][
                        "history_revision_id"
                    ],
                },
            )
            assert completed.status_code == 200, completed.json()
            restored = client.get(f"{path}/recommendation-batches/{result['batch_id']}")
            assert restored.status_code == 200, restored.json()
            assert restored.json()["method_version"] == expected_method
            study_response = client.get(path)
            assert study_response.status_code == 200, study_response.json()
            study = study_response.json()
            assert study["method_version"] == study_version
            assert study["definition_sha256"] == definition_hash
        closed = client.post(
            f"{path}/close",
            json=_close_request(
                study, target_status="completed", reason_code="objective_satisfied"
            ),
        )
        assert closed.status_code == 200, closed.json()
        restored_study = client.get(path)
        assert restored_study.status_code == 200, restored_study.json()
        assert restored_study.json()["status"] == "completed"
        assert restored_study.json()["method_version"] == study_version
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            after = connection.execute(
                "SELECT * FROM bayesian_study_versions WHERE study_version_id=?",
                (study["study_version_id"],),
            ).fetchone()
        assert after == original_definition


def test_tampered_noise_source_rejected_even_when_outer_hash_recomputed(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = _completed_study(client)
        path = f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches"
        result = client.post(path, json=_noise_request(study))
        assert result.status_code == 201, result.json()
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            raw = connection.execute(
                "SELECT result_json FROM bayesian_recommendation_batches WHERE batch_id=?",
                (result.json()["batch_id"],),
            ).fetchone()[0]
            data = json.loads(raw)
            data["shared_model"]["normalization"]["mean"] += 1
            data["result_sha256"] = "0" * 64
            data["result_sha256"] = hashlib.sha256(canonical_json_bytes(data)).hexdigest()
            updated = canonical_json_bytes(data)
            connection.execute(
                "UPDATE bayesian_recommendation_batches SET result_json=?,result_sha256=? "
                "WHERE batch_id=?",
                (updated.decode(), hashlib.sha256(updated).hexdigest(), result.json()["batch_id"]),
            )
        restored = client.get(f"{path}/{result.json()['batch_id']}")
        assert restored.status_code == 409, restored.json()


def test_worker_drains_pipe_before_join_and_terminates_only_own_child(monkeypatch):
    import multiprocessing

    from app.services import bayesian_noise_recommendations as service

    before = {process.pid for process in multiprocessing.active_children()}
    monkeypatch.setattr(service, "_worker_entry", large_result)
    assert len(service._run_worker({}, timeout_ms=20_000)["fixture"]) == 500_000
    monkeypatch.setattr(service, "_worker_entry", slow_result)
    with pytest.raises(ApiError) as exc:
        service._run_worker({}, timeout_ms=100)
    assert exc.value.code == "bayesian_optimization_batch_incomplete"
    assert {process.pid for process in multiprocessing.active_children()} == before


@pytest.mark.parametrize("mode", ["estimate", "fixed", "near_noiseless"])
def test_explicit_replicates_feed_sufficient_statistics_without_history_mutation(tmp_path, mode):
    from test_bayesian_replicates_api import completed_study, request_for, url

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed_study(client)
        created = client.post(url(study), json=request_for(study))
        assert created.status_code == 201, created.json()
        history_id = study["observation_history"]["history_revision_id"]
        for index, trial in enumerate(created.json()["trials"]):
            completed = client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
                json={"objective_value": 2 + index, "expected_history_revision_id": history_id},
            )
            assert completed.status_code == 200, completed.json()
            history_id = completed.json()["observation_history"]["history_revision_id"]
        study = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
        body = _noise_request(study)
        body["observation_policy"] = {"mode": "exact_replicates"}
        body["surrogate"] = {"noise_mode": mode}
        if mode == "fixed":
            body["surrogate"]["fixed_noise_sd"] = 0.1
        response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches", json=body
        )
        assert response.status_code == 201, response.json()
        result = response.json()
        assert result["shared_model"]["raw_observation_count"] == 4
        assert result["shared_model"]["effective_training_count"] == 2
        assert sorted(result["shared_model"]["training_group_counts"]) == [1, 3]
        assert sum(group["n"] for group in result["observation_view"]["groups"]) == 4
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert restored.status_code == 200, restored.json()
        assert restored.json()["observation_history"] == study["observation_history"]
        assert restored.json()["trials"][:4] == study["trials"]
        source = next(
            item.source
            for item in list_dedicated_report_sources(
                Settings(workspace_root=tmp_path), "bayesian_history_revision"
            ).items
            if item.source.attachment.kind == "batch"
        )
        report = prepare_dedicated_report_source(Settings(workspace_root=tmp_path), source, "en")
        assert len(report.payload["observations"]) == 4
        assert sum(item["origin"] == "replicate" for item in report.payload["observations"]) == 2
