"""Synthetic response-vector lifecycle, independent of GP calculation."""

import hashlib
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace


def study_request() -> dict:
    return {
        "name": "Vector lifecycle fixture",
        "factors": [{"factor_id": "x", "name": "X", "low": 0, "high": 10}],
        "objective": {
            "goal_type": "desirability",
            "name": "Joint goals",
            "observation_policy": "complete_response_vector",
            "curve_policy": "derringer_suich_linear_v1",
            "responses": [
                {
                    "response_id": "yield",
                    "name": "Yield",
                    "unit": "%",
                    "goal": "maximize",
                    "lower": 0,
                    "target": 100,
                    "upper": None,
                    "importance": 2,
                },
                {
                    "response_id": "cost",
                    "name": "Cost",
                    "unit": "USD",
                    "goal": "minimize",
                    "lower": None,
                    "target": 1,
                    "upper": 10,
                    "importance": 1,
                },
            ],
        },
        "initial_design_seed": 42,
        "initial_design_size": 3,
    }


def create_study(client: TestClient) -> dict:
    response = client.post("/api/v1/bayesian-studies", json=study_request())
    assert response.status_code == 201, response.text
    return response.json()


def observations(study: dict, indices: tuple[int, ...] = (0, 1, 2)) -> dict:
    return {
        "request_id": str(uuid4()),
        "expected_study_version_id": study["study_version_id"],
        "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_observation_history_sha256": study["observation_history"][
            "observation_history_sha256"
        ],
        "observations": [
            {
                "trial_id": study["trials"][index]["trial_id"],
                "response_values": {"yield": 40.0 + index, "cost": 3.0 + index},
            }
            for index in indices
        ],
    }


def test_vector_create_complete_restart_and_replay(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = create_study(client)
        assert study["study_schema_version"] == 5
        assert study["observation_history"]["schema_version"] == 2
        body = observations(study)
        url = f"/api/v1/bayesian-studies/{study['study_id']}/observations/batch"
        response = client.put(url, json=body)
        assert response.status_code == 200, response.text
        saved = response.json()
        assert saved["study"]["completed_trial_count"] == 3
        assert saved["observation_history"]["revision_number"] == 2
        for trial, requested in zip(saved["study"]["trials"], body["observations"], strict=True):
            assert trial["objective_value"] is None
            assert trial["response_values"] == requested["response_values"]
    with TestClient(create_app(settings)) as client:
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert restored.status_code == 200, restored.text
        assert restored.json() == saved["study"]
        replay = client.put(url, json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json() == saved
        changed = deepcopy(body)
        changed["observations"][0]["response_values"]["cost"] += 0.1
        rejected = client.put(url, json=changed)
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "bayesian_observation_request_id_conflict"


def url(study: dict) -> str:
    return f"/api/v1/bayesian-studies/{study['study_id']}"


def stored_rows(root) -> dict:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        return {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in (
                "bayesian_studies",
                "bayesian_study_versions",
                "bayesian_trials",
                "bayesian_observation_history_revisions",
                "bayesian_observation_history_heads",
            )
        }


@pytest.mark.parametrize(
    "values",
    [
        {"yield": 5.0},
        {"yield": 5.0, "cost": 2.0, "extra": 3.0},
        {"yield": True, "cost": 2.0},
        {"yield": "5", "cost": 2.0},
        {"yield": None, "cost": 2.0},
        {},
    ],
)
def test_partial_or_invalid_vector_never_commits_any_trial(tmp_path, values) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = create_study(client)
        before = stored_rows(tmp_path)
        body = observations(study)
        body["observations"][1]["response_values"] = values
        response = client.put(url(study) + "/observations/batch", json=body)
        assert response.status_code in {409, 422}, response.text
        assert stored_rows(tmp_path) == before
        assert client.get(url(study)).json() == study


@pytest.mark.parametrize(
    "mutation", ["duplicate_id", "missing_limit", "zero_weight", "wrong_curve", "scalar_unit"]
)
def test_invalid_response_definition_is_not_persisted(tmp_path, mutation) -> None:
    body = study_request()
    objective = body["objective"]
    if mutation == "duplicate_id":
        objective["responses"][1]["response_id"] = "yield"
    elif mutation == "missing_limit":
        objective["responses"][0]["lower"] = None
    elif mutation == "zero_weight":
        objective["responses"][1]["importance"] = 0
    elif mutation == "wrong_curve":
        objective["curve_policy"] = "jmp_exact"
    else:
        objective["unit"] = "fake joint unit"
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        before = stored_rows(tmp_path)
        response = client.post("/api/v1/bayesian-studies", json=body)
        assert response.status_code == 422, response.text
        assert stored_rows(tmp_path) == before


def test_vector_and_scalar_modes_cannot_be_cross_written(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        vector = create_study(client)
        scalar_body = study_request()
        scalar_body["objective"] = {"name": "Scalar", "direction": "maximize"}
        scalar = client.post("/api/v1/bayesian-studies", json=scalar_body).json()
        before = stored_rows(tmp_path)
        vector_body = observations(vector, (0,))
        vector_body["observations"] = [
            {"trial_id": vector["trials"][0]["trial_id"], "objective_value": 0.5}
        ]
        for study, body in ((vector, vector_body), (scalar, observations(scalar, (0,)))):
            response = client.put(url(study) + "/observations/batch", json=body)
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "bayesian_observation_mode_invalid"
        single = client.put(
            url(vector) + f"/trials/{vector['trials'][0]['trial_id']}/observation",
            json={
                "objective_value": 0.5,
                "expected_history_revision_id": vector["observation_history"][
                    "history_revision_id"
                ],
            },
        )
        assert single.status_code == 409
        assert stored_rows(tmp_path) == before


def test_early_history_hash_replay_and_csv_do_not_use_latest_values(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = create_study(client)
        first_body = observations(study, (0,))
        first = client.put(url(study) + "/observations/batch", json=first_body).json()
        later_body = observations(first["study"], (1, 2))
        later = client.put(url(study) + "/observations/batch", json=later_body).json()
        replay = client.put(url(study) + "/observations/batch", json=first_body)
        assert replay.status_code == 200
        assert replay.json()["observation_history"] == first["observation_history"]
        assert replay.json()["study"] == later["study"]
        old = client.get(
            url(study) + f"/history/{first['observation_history']['history_revision_id']}"
        )
        assert old.status_code == 200, old.text
        assert old.json() == first["observation_history"]
        csv = client.get(url(study) + "/initial-design.csv")
        assert csv.status_code == 200
        assert "Yield [%],Cost [USD]" in csv.text
        assert "40.0,3.0,recorded" in csv.text
        assert "pending" not in csv.text


@pytest.mark.parametrize("same_request", [True, False])
def test_concurrent_vector_save_replay_or_cas(tmp_path, monkeypatch, same_request) -> None:
    from app.services import bayesian_studies as service

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = create_study(client)
        body = observations(study)
        other = deepcopy(body)
        if not same_request:
            other["request_id"] = str(uuid4())
        gate = threading.Barrier(2)
        original = service.complete_bayesian_trial_batch_records

        def synchronized(*args, **kwargs):
            gate.wait(timeout=15)
            return original(*args, **kwargs)

        monkeypatch.setattr(service, "complete_bayesian_trial_batch_records", synchronized)
        with ThreadPoolExecutor(max_workers=2) as pool:
            calls = [
                pool.submit(client.put, url(study) + "/observations/batch", json=b)
                for b in (body, other)
            ]
            responses = [call.result(timeout=30) for call in calls]
        assert sorted(r.status_code for r in responses) == (
            [200, 200] if same_request else [200, 409]
        )
        if same_request:
            assert responses[0].json() == responses[1].json()
        current = client.get(url(study)).json()
        assert current["completed_trial_count"] == 3
        assert current["observation_history"]["revision_number"] == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("response_values_json", '{"yield":41,"cost":3}'),
        ("response_values_json", '{"yield":40,"yield":40,"cost":3}'),
        ("response_values_json", '{"yield":NaN,"cost":3}'),
        ("objective_value", 0.5),
    ],
)
def test_corrupt_vector_restore_fails_closed_without_rewrite(tmp_path, field, value) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = create_study(client)
        assert (
            client.put(url(study) + "/observations/batch", json=observations(study)).status_code
            == 200
        )
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                f"UPDATE bayesian_trials SET {field}=? WHERE trial_id=?",
                (value, study["trials"][0]["trial_id"]),
            )
        before = stored_rows(tmp_path)
        response = client.get(url(study))
        assert response.status_code == 409, response.text
        assert "yield" not in response.text and "41" not in response.json()["error"]["message"]
        assert stored_rows(tmp_path) == before


def test_replicate_vector_backup_restore_and_closed_delete(tmp_path) -> None:
    from test_bayesian_replicates_api import request_for
    from test_bayesian_study_lifecycle_api import _close_request

    root = tmp_path / "synthetic source"
    with TestClient(create_app(Settings(workspace_root=root))) as client:
        study = create_study(client)
        saved = client.put(url(study) + "/observations/batch", json=observations(study)).json()[
            "study"
        ]
        request = request_for(saved, count=2)
        endpoint = url(study) + f"/trials/{study['trials'][0]['trial_id']}/replicates"
        replicated = client.post(endpoint, json=request)
        assert replicated.status_code == 201, replicated.text
        current = client.get(url(study)).json()
        assert current["trials"][3]["objective_value"] is None
        before_parent = current["trials"][0]
        completed = client.put(
            url(study) + "/observations/batch", json=observations(current, (3, 4))
        )
        assert completed.status_code == 200, completed.text
        current = completed.json()["study"]
        assert current["trials"][0] == before_parent
        close = client.post(
            url(study) + "/close",
            json=_close_request(current, target_status="abandoned", reason_code="study_cancelled"),
        )
        assert close.status_code == 200, close.text
        current = close.json()["study"]
    archive = tmp_path / "vector.zip"
    manifest = backup_workspace(root, archive)
    assert manifest["metadata_schema_version"] == 32
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    restored_root = tmp_path / "restored spaced path"
    restore_workspace(archive, restored_root)
    with TestClient(create_app(Settings(workspace_root=restored_root))) as client:
        restored = client.get(url(study))
        assert restored.status_code == 200, restored.text
        assert restored.json() == current
        preflight = client.get(url(study) + "/deletion-preflight").json()
        response = client.request(
            "DELETE",
            url(study),
            json={
                "confirmation_study_id": study["study_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        assert response.status_code == 200, response.text
        assert client.get(url(study)).status_code == 404
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == sha
    with TestClient(create_app(Settings(workspace_root=root))) as client:
        assert client.get(url(study)).json() == current


def test_vector_history_managed_report_exact_revision_no_fit_and_escaping(
    tmp_path, monkeypatch
) -> None:
    from test_dedicated_report_sources import no_recompute
    from test_managed_report_api import VisibleReport

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body = study_request()
        body["objective"]["responses"][0]["name"] = '<img src=x onerror="alert(1)">수율'
        study = client.post("/api/v1/bayesian-studies", json=body).json()
        first = client.put(
            url(study) + "/observations/batch", json=observations(study, (0,))
        ).json()
        history = first["observation_history"]
        source = {
            "kind": "bayesian_history_revision",
            "study_id": study["study_id"],
            "study_version_id": study["study_version_id"],
            "definition_sha256": study["definition_sha256"],
            "history_revision_id": history["history_revision_id"],
            "expected_source_sha256": history["observation_history_sha256"],
            "attachment": {"kind": "none"},
        }
        assert (
            client.put(
                url(study) + "/observations/batch", json=observations(first["study"], (1, 2))
            ).status_code
            == 200
        )
        before = stored_rows(tmp_path)
        no_recompute(monkeypatch)
        for locale in ("ko", "en"):
            request = {"source": source, "locale": locale}
            capability = client.post("/api/v1/reports/capability", json=request)
            assert capability.status_code == 200, capability.text
            snapshot = client.post("/api/v1/reports/source-snapshot", json=request)
            assert snapshot.status_code == 200, snapshot.text
            assert len(snapshot.json()["payload"]["observations"]) == 1
            assert snapshot.json()["payload"]["observations"][0]["response_values"] == {
                "yield": 40,
                "cost": 3,
            }
            report = client.post(
                "/api/v1/reports",
                json={
                    **request,
                    "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
                },
            )
            assert report.status_code == 201, report.text
            report = report.json()
            downloaded = client.post(
                f"/api/v1/reports/{report['export_id']}/download",
                json={"source": source, "expected_sha256": report["sha256"]},
            )
            assert downloaded.status_code == 200, downloaded.text
            assert hashlib.sha256(downloaded.content).hexdigest() == report["sha256"]
            assert "<img src=x" not in downloaded.text
            assert "&lt;img" in downloaded.text
            assert f'<html lang="{locale}">' in downloaded.text
            visible = VisibleReport()
            visible.feed(downloaded.text)
            assert visible.svgs == 2
            assert "40" in "".join(visible.text) and "3" in "".join(visible.text)
            assert client.get(f"/api/v1/reports/{report['export_id']}").json() == report
        assert stored_rows(tmp_path) == before


@pytest.mark.parametrize(
    "route", ["recommendations", "recommendation-batches", "recommendation-reviews"]
)
def test_scalar_recommendation_routes_never_fit_vectors(tmp_path, monkeypatch, route) -> None:
    from test_bayesian_noise_api import _request

    from app.services import bayesian_noise_recommendations

    def forbidden(*args, **kwargs):
        pytest.fail("Vector observations reached the scalar GP worker")

    monkeypatch.setattr(bayesian_noise_recommendations, "calculate_noise_recommendation", forbidden)
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = create_study(client)
        saved = client.put(url(study) + "/observations/batch", json=observations(study)).json()[
            "study"
        ]
        assert saved["recommendation_available"] is True
        assert saved["surrogate_available"] is True
        assert saved["recommendation_blockers"] == []
        request = _request()
        request.update(
            expected_history_revision_id=saved["observation_history"]["history_revision_id"],
            expected_history_sha256=saved["observation_history"]["observation_history_sha256"],
        )
        if route == "recommendations":
            request.pop("acquisition")
        before = stored_rows(tmp_path)
        response = client.post(url(study) + "/" + route, json=request)
        assert response.status_code == 409, response.text
        assert (
            response.json()["error"]["code"] == "bayesian_multiresponse_recommendation_not_enabled"
        )
        assert stored_rows(tmp_path) == before
