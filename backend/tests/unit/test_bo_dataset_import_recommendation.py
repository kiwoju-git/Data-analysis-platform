"""Real next-recommendation workflows from synthetic imported measured rows."""

import math
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.analysis_run_execution import canonical_json_bytes
from app.storage.metadata import metadata_db_path
from tests.unit.test_bayesian_noise_api import _noise_request
from tests.unit.test_bo_dataset_import_api import (
    ROOT,
    commit_request,
    import_request,
    preflight,
)
from tests.unit.test_bo_mixed_batches_api import (
    confirm_payload,
    create_selection,
    selection_body,
)
from tests.unit.test_bo_mixed_planning_api import fit_options, source
from tests.unit.test_bo_mixed_studies import request as mixed_request


def _import_snapshot(workspace_root, study):
    with sqlite3.connect(metadata_db_path(workspace_root)) as db:
        version = db.execute(
            "SELECT * FROM bayesian_study_versions WHERE study_version_id=?",
            (study["study_version_id"],),
        ).fetchone()
        imported = db.execute(
            "SELECT * FROM bayesian_dataset_imports WHERE study_version_id=?",
            (study["study_version_id"],),
        ).fetchone()
        history = db.execute(
            "SELECT * FROM bayesian_observation_history_revisions WHERE history_revision_id=?",
            (study["observation_history"]["history_revision_id"],),
        ).fetchone()
    assert version is not None and imported is not None and history is not None
    return version, imported, history


def _assert_import_preserved(client, workspace_root, study, snapshot):
    response = client.get(f"{ROOT}/{study['study_id']}")
    assert response.status_code == 200, response.text
    current = response.json()
    assert current["study_version_id"] == study["study_version_id"]
    assert current["definition_sha256"] == study["definition_sha256"]
    assert canonical_json_bytes(current["initial_design"]) == canonical_json_bytes(
        study["initial_design"]
    )
    assert current["observation_history"] == study["observation_history"]
    assert current["trials"][: study["trial_count"]] == study["trials"]
    assert current["completed_trial_count"] == study["trial_count"]
    assert current["pending_trial_count"] == 1
    assert current["trial_count"] == study["trial_count"] + 1
    assert _import_snapshot(workspace_root, study) == snapshot


def test_imported_scalar_target_gets_real_q1_recommendation_and_preserves_source(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        body, _ = import_request(client)
        body["objective"] = {
            "name": "Target response",
            "goal_type": "match_target",
            "target_value": 20.0,
            "target_tolerance": 1.0,
        }
        created = client.post(
            f"{ROOT}/from-dataset", json=commit_request(body, preflight(client, body))
        )
        assert created.status_code == 201, created.text
        study = created.json()
        assert study["recommendation_available"] is True
        assert study["initial_design"]["policy"] == "dataset_observations_v1"
        snapshot = _import_snapshot(tmp_path, study)
        endpoint = f"{ROOT}/{study['study_id']}"
        request = _noise_request(study, count=1)
        request["acquisition"]["kind"] = "expected_target_improvement"
        response = client.post(endpoint + "/recommendation-batches", json=request)
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["batch_size"] == 1
        assert (
            batch["source_history_revision_id"]
            == study["observation_history"]["history_revision_id"]
        )
        assert (
            batch["source_observation_history_sha256"]
            == study["observation_history"]["observation_history_sha256"]
        )
        assert batch["observation_view"]["raw_observation_count"] == 4
        item = batch["items"][0]
        assert item["acquisition_kind"] == "expected_target_improvement"
        assert math.isfinite(item["acquisition_value_raw"])
        assert item["acquisition_value_raw"] >= 0
        assert 0 <= item["actual_coordinates"]["x"] <= 10
        assert item["actual_coordinates"] not in [
            trial["actual_coordinates"] for trial in study["trials"]
        ]
        saved_url = endpoint + "/recommendation-batches/" + batch["batch_id"]
        restored = client.get(saved_url)
        assert restored.status_code == 200, restored.text
        assert restored.json() == batch
        assert len(batch["result_sha256"]) == 64
        _assert_import_preserved(client, tmp_path, study, snapshot)
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(saved_url).json() == batch
        _assert_import_preserved(restarted, tmp_path, study, snapshot)


def test_imported_mixed_vector_gets_real_q1_refine_recommendation_and_preserves_source(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        body, version = import_request(
            client, b"x,y,kind\n0,0.1,A\n2,0.7,B\n4,0.4,C\n6,0.8,A\n8,0.3,B\n10,0.9,C\n"
        )
        definition = mixed_request()
        category = definition["factors"][1]
        category["levels"] = ["A", "B", "C"]
        body["factor_mappings"].append(
            {"column_id": version["columns"][2]["column_id"], "factor": category}
        )
        body["objective"] = definition["objective"]
        body["objective"]["responses"][0].update(lower=-1.0, target=2.0)
        body["response_mappings"][0]["response_id"] = "yield"
        preview = preflight(client, body)
        assert preview["n_used"] == preview["unique_coordinate_count"] == 6
        created = client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview))
        assert created.status_code == 201, created.text
        study = created.json()
        assert study["study_schema_version"] == 7
        assert study["recommendation_available"] is True
        assert study["initial_design"]["policy"] == "dataset_observations_v1"
        snapshot = _import_snapshot(tmp_path, study)
        endpoint = f"{ROOT}/{study['study_id']}"
        # Keep the existing mixed reference fixture's declared kernel/noise policy.
        fitted = client.post(
            endpoint + "/mixed-planning-models",
            json=source(study) | {"request_id": str(uuid4()), "fit": fit_options()},
        )
        assert fitted.status_code == 201, fitted.text
        model = fitted.json()
        assert model["observation_view"]["raw_observation_count"] == 6
        candidates = client.post(
            endpoint + "/mixed-candidate-revisions",
            json=source(study)
            | {
                "schema_version": 3,
                "request_id": str(uuid4()),
                "candidate_set_id": str(uuid4()),
                "name": "Imported mixed next candidates",
                "expected_head_revision_id": None,
                "model_id": model["model_id"],
                "expected_model_sha256": model["snapshot_sha256"],
                "duplicate_tolerance": 1e-6,
                "source": {"kind": "seeded_uniform", "seed": 12, "count": 16},
            },
        )
        assert candidates.status_code == 201, candidates.text
        selection = create_selection(
            client,
            endpoint,
            selection_body(
                study,
                model,
                candidates.json(),
                size=1,
                policy="refine_ei_alternating_desirability_response_sd_v2",
            ),
        )
        selected = selection["calculation"]["selected_rows"][0]
        assert selected["acquisition"]["numerical_policy"] == "positive_beta_integral_v2"
        assert math.isfinite(selected["acquisition"]["value"])
        assert selected["acquisition"]["value"] >= 0
        assert selected["actual_coordinates"]["kind"] in ["A", "B", "C"]
        assert 0 <= selected["actual_coordinates"]["x"] <= 10
        assert selected["actual_coordinates"] not in [
            trial["actual_coordinates"] for trial in study["trials"]
        ]
        confirmed = client.post(
            endpoint + "/mixed-selections/" + selection["selection_id"] + "/confirm",
            json=confirm_payload(selection),
        )
        assert confirmed.status_code == 201, confirmed.text
        batch = confirmed.json()
        assert batch["batch_size"] == 1
        assert batch["calculation"] == selection["calculation"]
        saved_url = endpoint + "/mixed-planning-batches/" + batch["batch_id"]
        restored = client.get(saved_url)
        assert restored.status_code == 200, restored.text
        assert restored.json() == batch
        assert len(batch["result_sha256"]) == 64
        _assert_import_preserved(client, tmp_path, study, snapshot)
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(saved_url).json() == batch
        _assert_import_preserved(restarted, tmp_path, study, snapshot)
