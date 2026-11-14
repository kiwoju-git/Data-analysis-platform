"""Explicit review renewal preserves historical numeric artifacts and exact sources."""

import json
import sqlite3
from contextlib import ExitStack
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services import bo_desirability_worker as execution
from app.storage.bo_planning import planning_json, planning_sha
from app.storage.metadata import metadata_db_path
from tests.unit.test_bayesian_multiresponse_lifecycle import url
from tests.unit.test_bo_candidates_v2 import request
from tests.unit.test_bo_desirability_review_api import completed
from tests.unit.test_bo_planning_api import fit_request
from tests.unit.test_bo_planning_worker import _Output


@pytest.fixture
def legacy_selection(tmp_path, monkeypatch):
    def in_process(encoded, *, entrypoint, timeout_ms, cancel, max_result_bytes):
        output = _Output()
        entrypoint(output, encoded)
        assert output.closed and len(output.data) <= max_result_bytes
        return output.data

    monkeypatch.setattr(execution, "_run_owned_worker", in_process)
    settings = Settings(workspace_root=tmp_path / "renewal synthetic")
    with ExitStack() as lifetime:
        client = lifetime.enter_context(TestClient(create_app(settings)))
        study = completed(client)
        fitted = client.post(url(study) + "/planning-models", json=fit_request(study))
        assert fitted.status_code == 201, fitted.text
        model = fitted.json()
        candidate_body = request(study) | {
            "model_id": model["model_id"],
            "expected_model_sha256": model["snapshot_sha256"],
            "duplicate_tolerance": model["fit"]["search"]["duplicate_tolerance"],
            "source": {
                "kind": "explicit_rows",
                "points": [{"x": value} for value in (1.25, 3.25, 4.25, 6.25, 7.25)],
            },
        }
        response = client.post(url(study) + "/candidate-revisions", json=candidate_body)
        assert response.status_code == 201, response.text
        candidate = response.json()["revision"]
        body = {
            key: candidate_body[key]
            for key in (
                "schema_version",
                "expected_study_version_id",
                "expected_definition_sha256",
                "expected_history_revision_id",
                "expected_history_sha256",
                "expected_trial_count",
                "model_id",
                "expected_model_sha256",
                "duplicate_tolerance",
            )
        } | {
            "request_id": str(uuid4()),
            "candidate_revision_id": candidate["revision_id"],
            "expected_rows_sha256": candidate["rows_sha256"],
            "policy": "refine_ei_then_desirability_sd_v1",
            "batch_size": 2,
            "total_trial_budget": 20,
        }
        response = client.post(url(study) + "/augmentations", json=body)
        assert response.status_code == 201, response.text
        selected = response.json()
        result = selected["calculation"]
        for row in result["selected_rows"]:
            if row["acquisition"] is not None:
                row["acquisition"].pop("numerical_policy")
        database = metadata_db_path(settings.workspace_root)
        # A historical fixture: only the explicitly absent policy distinguishes its receipt.
        with sqlite3.connect(database) as db:
            db.execute(
                "UPDATE bayesian_planning_selections SET result_json=?,result_sha256=? "
                "WHERE selection_id=?",
                (planning_json(result), planning_sha(result), selected["selection_id"]),
            )
        endpoint = url(study) + "/augmentations/" + selected["selection_id"]
        response = client.get(endpoint)
        assert response.status_code == 200, response.text
        original = response.json()
        before = _stored_selection(database, selected["selection_id"])
        yield SimpleNamespace(
            client=client,
            settings=settings,
            study=study,
            original=original,
            endpoint=endpoint,
            database=database,
            before=before,
            close=lifetime.close,
            body={
                "request_id": str(uuid4()),
                "expected_config_sha256": original["config_sha256"],
                "expected_result_sha256": original["result_sha256"],
            },
        )


def _stored_selection(database, selection_id):
    with sqlite3.connect(database) as db:
        return db.execute(
            "SELECT config_json,config_sha256,result_json,result_sha256 "
            "FROM bayesian_planning_selections WHERE selection_id=?",
            (selection_id,),
        ).fetchone()


def test_legacy_first_confirmation_requires_explicit_renewal(legacy_selection):
    state = legacy_selection
    response = state.client.post(
        state.endpoint + "/confirm",
        json={key: state.body[key] for key in ("expected_config_sha256", "expected_result_sha256")},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "bayesian_augmentation_renewal_required"
    assert state.client.get(url(state.study)).json()["pending_trial_count"] == 0
    assert _stored_selection(state.database, state.original["selection_id"]) == state.before


def test_already_confirmed_absent_policy_receipt_replays_without_recalculation(
    legacy_selection, monkeypatch
):
    state = legacy_selection
    from app.api.v1.schemas.bo_augmentation import AugmentationSelectionResponse
    from app.services import bo_augmentation_batches as service

    # Build the historical confirmed record at the former commit boundary.
    service._confirm_uncommitted_augmentation(
        state.settings,
        UUID(state.study["study_id"]),
        UUID(state.original["selection_id"]),
        AugmentationSelectionResponse.model_validate(state.original),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("confirmed historical replay must not run a new numerical decision")

    monkeypatch.setattr(service, "_confirm_uncommitted_augmentation", forbidden)
    monkeypatch.setattr(service, "validate_augmentation_for_commit", forbidden)
    body = {key: state.body[key] for key in ("expected_config_sha256", "expected_result_sha256")}
    first = state.client.post(state.endpoint + "/confirm", json=body)
    assert first.status_code == 201, first.text
    assert state.client.post(state.endpoint + "/confirm", json=body).json() == first.json()
    assert _stored_selection(state.database, state.original["selection_id"]) == state.before
    assert state.client.get(url(state.study)).json()["trial_count"] == 5


def test_renewal_preserves_exact_request_and_receipt_without_refit(legacy_selection, monkeypatch):
    state = legacy_selection
    from app.services import bo_planning

    original_run = bo_planning.run_planning_operation

    def no_refit(operation, *args, **kwargs):
        assert operation not in {"fit", "fit_mixed"}
        return original_run(operation, *args, **kwargs)

    monkeypatch.setattr(bo_planning, "run_planning_operation", no_refit)
    response = state.client.post(state.endpoint + "/renew", json=state.body)
    assert response.status_code == 201, response.text
    value = response.json()
    renewed = value["selection"]
    expected = state.original["request"] | {"request_id": state.body["request_id"]}
    assert renewed["request"] == expected
    assert renewed["selection_id"] != state.original["selection_id"]
    assert renewed["confirmed_batch_id"] is None
    assert value["lineage"]["original_selection_id"] == state.original["selection_id"]
    assert value["lineage"]["original_config_sha256"] == state.original["config_sha256"]
    assert value["lineage"]["original_result_sha256"] == state.original["result_sha256"]
    assert value["lineage"]["numerical_policy"] == "positive_beta_integral_v2"
    assert all(
        row["acquisition"] is None
        or row["acquisition"]["numerical_policy"] == "positive_beta_integral_v2"
        for row in renewed["calculation"]["selected_rows"]
    )
    assert _stored_selection(state.database, state.original["selection_id"]) == state.before
    assert state.client.get(state.endpoint).json() == state.original
    assert state.client.get(url(state.study)).json()["pending_trial_count"] == 0
    assert state.client.post(state.endpoint + "/renew", json=state.body).json() == value
    renewed_endpoint = url(state.study) + "/augmentations/" + renewed["selection_id"]
    assert state.client.get(renewed_endpoint + "/renewal").json() == value["lineage"]
    assert state.client.get(state.endpoint + "/renewal").json() is None
    with sqlite3.connect(state.database) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_augmentation_renewals").fetchone()[0] == 1


@pytest.mark.parametrize("field", ["expected_config_sha256", "expected_result_sha256"])
def test_renewal_checks_both_original_hashes(legacy_selection, field):
    state = legacy_selection
    response = state.client.post(state.endpoint + "/renew", json=state.body | {field: "f" * 64})
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "bayesian_planning_selection_mismatch"
    assert _stored_selection(state.database, state.original["selection_id"]) == state.before


def test_renewal_and_lineage_rollback_together(legacy_selection):
    state = legacy_selection
    with sqlite3.connect(state.database) as db:
        count = db.execute("SELECT COUNT(*) FROM bayesian_planning_selections").fetchone()[0]
        db.execute(
            "CREATE TRIGGER synthetic_renewal_failure BEFORE INSERT "
            "ON bayesian_augmentation_renewals BEGIN SELECT RAISE(ABORT,'synthetic'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic"):
        state.client.post(state.endpoint + "/renew", json=state.body)
    with sqlite3.connect(state.database) as db:
        assert (
            db.execute("SELECT COUNT(*) FROM bayesian_planning_selections").fetchone()[0] == count
        )
        assert db.execute("SELECT COUNT(*) FROM bayesian_augmentation_renewals").fetchone()[0] == 0
    assert _stored_selection(state.database, state.original["selection_id"]) == state.before


def test_normal_request_id_cannot_be_reused_as_renewal(legacy_selection):
    state = legacy_selection
    current = state.original["request"] | {"request_id": state.body["request_id"]}
    response = state.client.post(url(state.study) + "/augmentations", json=current)
    assert response.status_code == 201, response.text
    response = state.client.post(state.endpoint + "/renew", json=state.body)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "bayesian_planning_request_conflict"
    with sqlite3.connect(state.database) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_augmentation_renewals").fetchone()[0] == 0


def test_renewal_parent_must_not_change_inside_write_transaction(legacy_selection, monkeypatch):
    state = legacy_selection
    from app.storage import bo_planning

    original_insert = bo_planning.insert_planning_selection

    def changed(root, record, **kwargs):
        with sqlite3.connect(state.database) as db:
            original = json.loads(state.before[0])
            original["time_budget_ms"] -= 1
            db.execute(
                "UPDATE bayesian_planning_selections SET config_json=?,config_sha256=? "
                "WHERE selection_id=?",
                (planning_json(original), planning_sha(original), state.original["selection_id"]),
            )
        return original_insert(root, record, **kwargs)

    monkeypatch.setattr(bo_planning, "insert_planning_selection", changed)
    response = state.client.post(state.endpoint + "/renew", json=state.body)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "bayesian_planning_selection_mismatch"


def test_renewed_confirm_replay_and_original_preserved(legacy_selection):
    state = legacy_selection
    response = state.client.post(state.endpoint + "/renew", json=state.body)
    assert response.status_code == 201, response.text
    renewed = response.json()["selection"]
    endpoint = url(state.study) + "/augmentations/" + renewed["selection_id"] + "/confirm"
    body = {key: renewed[key] for key in ("config_sha256", "result_sha256")}
    body = {"expected_" + key: value for key, value in body.items()}
    confirmed = state.client.post(endpoint, json=body)
    assert confirmed.status_code == 201, confirmed.text
    assert state.client.post(endpoint, json=body).json() == confirmed.json()
    # Lost renewal response can be recovered after confirmation without a new worker/trial.
    replay = state.client.post(state.endpoint + "/renew", json=state.body)
    assert replay.status_code == 201, replay.text
    assert replay.json()["selection"]["confirmed_batch_id"] == confirmed.json()["batch_id"]
    assert state.client.get(url(state.study)).json()["trial_count"] == 5
    assert _stored_selection(state.database, state.original["selection_id"]) == state.before


def test_second_new_renewal_refuses_pending_source(legacy_selection):
    state = legacy_selection
    renewed = state.client.post(state.endpoint + "/renew", json=state.body).json()["selection"]
    confirmed = state.client.post(
        url(state.study) + "/augmentations/" + renewed["selection_id"] + "/confirm",
        json={
            "expected_config_sha256": renewed["config_sha256"],
            "expected_result_sha256": renewed["result_sha256"],
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    response = state.client.post(
        state.endpoint + "/renew", json=state.body | {"request_id": str(uuid4())}
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] in {
        "bayesian_candidate_source_changed",
        "bayesian_optimization_pending_recommendation_exists",
    }


def test_renewal_restart_backup_and_source_deletion_manifest(legacy_selection, tmp_path):
    state = legacy_selection
    from app.storage.bo_planning import planning_owner_manifest
    from app.storage.workspace_backup import backup_workspace, restore_workspace

    saved = state.client.post(state.endpoint + "/renew", json=state.body)
    assert saved.status_code == 201, saved.text
    value = saved.json()
    with sqlite3.connect(state.database) as db:
        manifest = planning_owner_manifest(db, state.study["study_id"])
        assert manifest["augmentation_renewal_count"] == 1
    state.close()
    archive, restored = tmp_path / "renewal.tar.gz", tmp_path / "restored renewal"
    backup_workspace(state.settings.workspace_root, archive)
    restore_workspace(archive, restored)
    with TestClient(create_app(Settings(workspace_root=restored))) as client:
        assert client.get(state.endpoint).json() == state.original
        assert client.post(state.endpoint + "/renew", json=state.body).json() == value
        new_id = value["selection"]["selection_id"]
        assert (
            client.get(url(state.study) + "/augmentations/" + new_id + "/renewal").json()
            == value["lineage"]
        )


@pytest.mark.parametrize("change", ["closed", "history"])
def test_renewal_rejects_closed_or_changed_history_without_new_records(legacy_selection, change):
    state = legacy_selection
    if change == "closed":
        from tests.unit.test_bayesian_study_lifecycle_api import _close_request

        response = state.client.post(
            url(state.study) + "/close",
            json=_close_request(
                state.study, target_status="abandoned", reason_code="study_cancelled"
            ),
        )
    else:
        from tests.unit.test_bayesian_multiresponse_lifecycle import observations
        from tests.unit.test_bayesian_replicates_api import request_for

        replicated = state.client.post(
            url(state.study) + f"/trials/{state.study['trials'][0]['trial_id']}/replicates",
            json=request_for(state.study, count=1),
        )
        assert replicated.status_code == 201, replicated.text
        current = state.client.get(url(state.study)).json()
        response = state.client.put(
            url(state.study) + "/observations/batch", json=observations(current, (3,))
        )
    assert response.status_code == 200, response.text
    if change == "history":
        assert response.json()["study"]["pending_trial_count"] == 0
        assert response.json()["study"]["observation_history"] != state.study["observation_history"]
    with sqlite3.connect(state.database) as db:
        before = db.execute("SELECT COUNT(*) FROM bayesian_planning_selections").fetchone()[0]
    response = state.client.post(state.endpoint + "/renew", json=state.body)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "bayesian_candidate_source_changed"
    with sqlite3.connect(state.database) as db:
        assert (
            db.execute("SELECT COUNT(*) FROM bayesian_planning_selections").fetchone()[0] == before
        )
        assert db.execute("SELECT COUNT(*) FROM bayesian_augmentation_renewals").fetchone()[0] == 0
    assert _stored_selection(state.database, state.original["selection_id"]) == state.before


def test_renewal_lineage_is_owner_scoped_and_deleted_with_study(legacy_selection):
    state = legacy_selection
    from tests.unit.test_bayesian_multiresponse_lifecycle import create_study
    from tests.unit.test_bayesian_study_lifecycle_api import _close_request

    before = state.client.get(url(state.study) + "/deletion-preflight").json()
    renewed = state.client.post(state.endpoint + "/renew", json=state.body)
    assert renewed.status_code == 201, renewed.text
    new_id = renewed.json()["selection"]["selection_id"]
    other = create_study(state.client)
    wrong_original = url(other) + "/augmentations/" + state.original["selection_id"]
    assert state.client.post(wrong_original + "/renew", json=state.body).status_code == 404
    assert state.client.get(url(other) + "/augmentations/" + new_id + "/renewal").status_code == 404
    current = state.client.get(url(state.study) + "/deletion-preflight").json()
    assert current["counts"]["augmentation_renewal_count"] == 1
    assert before["deletion_manifest_sha256"] != current["deletion_manifest_sha256"]
    closed = state.client.post(
        url(state.study) + "/close",
        json=_close_request(state.study, target_status="abandoned", reason_code="study_cancelled"),
    )
    assert closed.status_code == 200, closed.text
    request = {
        "confirmation_study_id": state.study["study_id"],
        "expected_deletion_manifest_sha256": before["deletion_manifest_sha256"],
    }
    stale = state.client.request("DELETE", url(state.study), json=request)
    assert stale.status_code == 409, stale.text
    with sqlite3.connect(state.database) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_augmentation_renewals").fetchone()[0] == 1
    fresh = state.client.get(url(state.study) + "/deletion-preflight").json()
    request["expected_deletion_manifest_sha256"] = fresh["deletion_manifest_sha256"]
    deleted = state.client.request("DELETE", url(state.study), json=request)
    assert deleted.status_code == 200, deleted.text
    assert state.client.get(state.endpoint).status_code == 404
    assert (
        state.client.get(url(state.study) + "/augmentations/" + new_id + "/renewal").status_code
        == 404
    )
    with sqlite3.connect(state.database) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_augmentation_renewals").fetchone()[0] == 0
        assert (
            db.execute(
                "SELECT COUNT(*) FROM bayesian_planning_selections WHERE study_version_id=?",
                (state.study["study_version_id"],),
            ).fetchone()[0]
            == 0
        )
