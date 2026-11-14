"""Synthetic measured-observation import, without fitting a surrogate."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.storage.metadata import SCHEMA_VERSION, metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bayesian_multiresponse_lifecycle import study_request
from tests.unit.test_dataset_version_retention_api import _confirm

ROOT = "/api/v1/bayesian-studies"


def import_request(
    client, content=b"x,y,cost\n0,10,4\n5,20,3\n5,21,2\n10,30,1\n", *, numeric_y=False
):
    upload = client.post("/api/v1/datasets", files={"file": ("synthetic.csv", content, "text/csv")})
    assert upload.status_code == 201, upload.text
    version = _confirm(
        client,
        upload.json()["dataset_id"],
        columns=[{"column_index": 1, "data_type": "decimal"}] if numeric_y else None,
    )
    return {
        "schema_version": 1,
        "name": "Measured fixture",
        "dataset_version_id": version["version_id"],
        "expected_schema_hash": version["schema_hash"],
        "factor_mappings": [
            {
                "column_id": version["columns"][0]["column_id"],
                "factor": {"factor_id": "x", "name": "X", "low": 0, "high": 10},
            }
        ],
        "objective": {"name": "Y", "goal_type": "maximize"},
        "response_mappings": [{"column_id": version["columns"][1]["column_id"]}],
        "filter_snapshot": {"expression_version": 1, "conditions": []},
        "missing_policy": "reject",
    }, version


def preflight(client, body):
    response = client.post(f"{ROOT}/import-preflight", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def commit_request(body, preview):
    return {
        **body,
        "request_id": str(uuid4()),
        "expected_preflight_sha256": preview["preflight_sha256"],
    }


def test_scalar_exact_repeats_atomic_history_and_idempotency(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client)
        preview = preflight(client, body)
        assert (preview["n_total"], preview["n_used"], preview["n_missing"]) == (4, 4, 0)
        assert preview["unique_coordinate_count"] == 3
        assert preview["repeated_coordinate_count"] == 1
        assert preview["conflicting_coordinate_count"] == 1
        request = commit_request(body, preview)
        response = client.post(f"{ROOT}/from-dataset", json=request)
        assert response.status_code == 201, response.text
        saved = response.json()
        assert saved["completed_trial_count"] == 4
        assert saved["pending_trial_count"] == 0
        assert saved["initial_design"]["policy"] == "dataset_observations_v1"
        assert "seed" not in saved["initial_design"]
        assert [t["actual_coordinates"]["x"] for t in saved["trials"]] == [0, 5, 5, 10]
        assert [t["objective_value"] for t in saved["trials"]] == [10, 20, 21, 30]
        assert saved["observation_history"]["revision_number"] == 1
        assert saved["observation_history"]["completed_trial_count"] == 4
        assert saved["recommendation_available"] is True
        assert client.get(f"{ROOT}/{saved['study_id']}").json() == saved
        assert client.post(f"{ROOT}/from-dataset", json=request).json() == saved
        changed = {**request, "name": "Other"}
        rejected = client.post(f"{ROOT}/from-dataset", json=changed)
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "bayesian_import_request_id_conflict"
        deletion = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/deletion-preflight"
        ).json()
        assert deletion["deletion_ready"] is False
        assert "dataset_version_deletion_bayesian_study_dependency" in deletion["blockers"]
        assert deletion["counts"]["bayesian_study_count"] == 1
        assert deletion["dependency_preview"][0]["asset_type"] == "bayesian_study"
        assert deletion["dependency_preview"][0]["asset_id"] == saved["study_id"]
        assert not any(item["ready"] for item in deletion["available_operations"])
    with sqlite3.connect(metadata_db_path(tmp_path)) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_studies").fetchone()[0] == 1
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_vector_values_and_explicit_complete_case(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client, b"x,y,cost\n0,10,4\n3,,3\n6,21,2\n10,30,1\n")
        body["objective"] = study_request()["objective"]
        body["response_mappings"] = [
            {"column_id": version["columns"][1]["column_id"], "response_id": "yield"},
            {"column_id": version["columns"][2]["column_id"], "response_id": "cost"},
        ]
        rejected = client.post(f"{ROOT}/import-preflight", json=body)
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "bayesian_import_missing_values"
        body["missing_policy"] = "complete_case"
        preview = preflight(client, body)
        assert (preview["n_missing"], preview["n_used"]) == (1, 3)
        saved = client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview)).json()
        assert saved["initial_design"]["source_row_indices"] == [0, 2, 3]
        assert [t["response_values"] for t in saved["trials"]] == [
            {"yield": 10, "cost": 4},
            {"yield": 21, "cost": 2},
            {"yield": 30, "cost": 1},
        ]
        assert client.get(f"{ROOT}/{saved['study_id']}").status_code == 200


def test_numeric_gaussian_target_import_preserves_versioned_curve(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client)
        objective = study_request()["objective"]
        objective["curve_policy"] = "per_response_target_gaussian_or_ds_v1"
        objective["responses"][0].update(
            goal="match_target",
            lower=0,
            target=20,
            upper=40,
            curve={
                "policy": "two_sided_gaussian_target_peak_one_v1",
                "lower_desirability": 0.1,
                "upper_desirability": 0.2,
            },
        )
        body["objective"] = objective
        body["response_mappings"] = [
            {"column_id": version["columns"][1]["column_id"], "response_id": "yield"},
            {"column_id": version["columns"][2]["column_id"], "response_id": "cost"},
        ]
        request = commit_request(body, preflight(client, body))
        response = client.post(f"{ROOT}/from-dataset", json=request)
        assert response.status_code == 201, response.text
        saved = response.json()
        assert saved["study_schema_version"] == 6
        assert saved["objective"]["curve_policy"] == objective["curve_policy"]
        assert saved["objective"]["responses"][0]["curve"] == objective["responses"][0]["curve"]
        assert client.get(f"{ROOT}/{saved['study_id']}").json() == saved
        assert client.post(f"{ROOT}/from-dataset", json=request).json() == saved


def test_mixed_import_combined_category_budget_is_controlled_error(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client, b"x,y,a,b,c\n0,1,L0,L0,L0\n5,2,L1,L1,L1\n")
        body["objective"] = study_request()["objective"]
        body["objective"]["responses"] = body["objective"]["responses"][:1]
        body["response_mappings"][0]["response_id"] = "yield"
        for index in range(2, 5):
            body["factor_mappings"].append(
                {
                    "column_id": version["columns"][index]["column_id"],
                    "factor": {
                        "factor_id": f"category_{index}",
                        "name": f"Category {index}",
                        "domain_kind": "ordinal",
                        "levels": [f"L{i}" for i in range(32)],
                        "correlation_policy": "ordinal_monotone_latent_rbf_v1",
                    },
                }
            )
        response = client.post(f"{ROOT}/import-preflight", json=body)
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "bayesian_import_factor_space_invalid"
        assert client.get(ROOT).json()["total"] == 0


@pytest.mark.parametrize(
    "content,code",
    [
        (b"x,y\n0,1\n11,2\n", "bayesian_import_factor_out_of_domain"),
        (b"x,y\n0,1\n5,inf\n", "bayesian_import_nonfinite_value"),
        (b"x,y\n0,1\n5,invalid\n", "bayesian_import_numeric_column_required"),
        (("x,y\n" + "5,1\n" * 201).encode(), "bayesian_import_trial_limit"),
    ],
)
def test_invalid_rows_never_create_studies(tmp_path, content, code):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, _ = import_request(
            client, content, numeric_y=code == "bayesian_import_nonfinite_value"
        )
        rejected = client.post(f"{ROOT}/import-preflight", json=body)
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["error"]["code"] == code
        assert client.get(ROOT).json()["total"] == 0


def test_commit_rolls_back_rows_and_ownership_after_insert_failure(tmp_path, monkeypatch):
    from app.services import bo_dataset_import as service

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, _ = import_request(client)
        request = commit_request(body, preflight(client, body))
        original = service._insert

        def fail_after_insert(*args, **kwargs):
            original(*args, **kwargs)
            raise ApiError(
                code="synthetic_failure", message="Synthetic rollback test.", status_code=409
            )

        with monkeypatch.context() as patch:
            patch.setattr(service, "_insert", fail_after_insert)
            failed = client.post(f"{ROOT}/from-dataset", json=request)
        assert failed.status_code == 409
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            for table in [
                "bayesian_studies",
                "bayesian_study_versions",
                "bayesian_trials",
                "bayesian_observation_history_revisions",
                "bayesian_dataset_imports",
            ]:
                assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert client.post(f"{ROOT}/from-dataset", json=request).status_code == 201


def test_simultaneous_duplicate_import_has_one_study(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, _ = import_request(client)
        request = commit_request(body, preflight(client, body))
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(
                executor.map(lambda _: client.post(f"{ROOT}/from-dataset", json=request), range(2))
            )
        assert [response.status_code for response in responses] == [201, 201]
        assert responses[0].json() == responses[1].json()
        assert client.get(ROOT).json()["total"] == 1


def test_import_snapshot_survives_schema_edit_and_archive_without_rewriting_legacy(tmp_path):
    root = tmp_path / "source space"
    with TestClient(create_app(Settings(workspace_root=root))) as client:
        legacy = client.post(ROOT, json=study_request()).json()
        body, version = import_request(client)
        saved = client.post(
            f"{ROOT}/from-dataset", json=commit_request(body, preflight(client, body))
        ).json()
        with sqlite3.connect(metadata_db_path(root)) as db:
            before = db.execute(
                "SELECT * FROM bayesian_study_versions ORDER BY study_version_id"
            ).fetchall()
            db.execute(
                "UPDATE dataset_versions SET schema_hash=? WHERE version_id=?",
                ("b" * 64, version["version_id"]),
            )
        assert client.get(f"{ROOT}/{saved['study_id']}").json() == saved
    archive, restored = tmp_path / "snapshot.zip", tmp_path / "restored space"
    assert backup_workspace(root, archive)["metadata_schema_version"] == SCHEMA_VERSION
    restore_workspace(archive, restored)
    with sqlite3.connect(metadata_db_path(restored)) as db:
        assert (
            db.execute("SELECT * FROM bayesian_study_versions ORDER BY study_version_id").fetchall()
            == before
        )
    with TestClient(create_app(Settings(workspace_root=restored))) as client:
        assert client.get(f"{ROOT}/{saved['study_id']}").json() == saved
        assert client.get(f"{ROOT}/{legacy['study_id']}").json() == legacy


def test_mixed_import_reuses_existing_source_and_keeps_literal_levels(tmp_path):
    from tests.unit.test_bo_mixed_studies import request as mixed_request

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client, b"x,y,kind\n0,1,A\n5,2,B\n5,3,B\n10,4,A\n")
        body["factor_mappings"].append(
            {
                "column_id": version["columns"][2]["column_id"],
                "factor": {
                    "factor_id": "kind",
                    "name": "Kind",
                    "domain_kind": "nominal",
                    "levels": ["A", "B"],
                    "correlation_policy": "equal_positive_correlation_v1",
                },
            }
        )
        body["objective"] = mixed_request()["objective"]
        body["response_mappings"][0]["response_id"] = "yield"
        preview = preflight(client, body)
        response = client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview))
        assert response.status_code == 201, response.text
        saved = response.json()
        assert saved["study_schema_version"] == 7
        assert saved["trials"][1]["actual_coordinates"] == {"x": 5, "kind": "B"}
        assert saved["trials"][1]["encoded_coordinates"] == {"x": 0.5, "kind": 1}
        assert saved["recommendation_available"] is True
        assert client.get(f"{ROOT}/{saved['study_id']}").json() == saved


def test_canonical_tamper_and_deletion_race_never_partially_commit(tmp_path):
    from app.storage.metadata import get_dataset_artifact_record

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client)
        preview = preflight(client, body)
        artifact = get_dataset_artifact_record(tmp_path, version["version_id"], "canonical_rows")
        assert artifact is not None
        path = tmp_path / artifact.path
        original = path.read_bytes()
        path.write_bytes(original.replace(b'"10"', b'"11"'))
        rejected = client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview))
        assert rejected.status_code == 409
        assert client.get(ROOT).json()["total"] == 0
        path.write_bytes(original)
        deletion = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/deletion-preflight"
        ).json()
        assert (
            client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview)).status_code
            == 201
        )
        rejected = client.request(
            "DELETE",
            f"/api/v1/dataset-versions/{version['version_id']}/deletion",
            json={
                "confirmation_version_id": version["version_id"],
                "expected_deletion_manifest_sha256": deletion["deletion_manifest_sha256"],
            },
        )
        assert rejected.status_code == 409
        assert path.read_bytes() == original


def test_filter_and_schema_changes_invalidate_preflight(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client)
        preview = preflight(client, body)
        changed = deepcopy(body)
        changed["filter_snapshot"]["conditions"] = [
            {
                "column_id": version["columns"][0]["column_id"],
                "operator": "gte",
                "value": 5,
            }
        ]
        rejected = client.post(f"{ROOT}/from-dataset", json=commit_request(changed, preview))
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "bayesian_import_preflight_stale"
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            db.execute(
                "UPDATE dataset_versions SET schema_hash=? WHERE version_id=?",
                ("f" * 64, version["version_id"]),
            )
        rejected = client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview))
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "bayesian_import_source_stale"
        assert client.get(ROOT).json()["total"] == 0


def test_commit_revalidates_source_inside_ownership_transaction(tmp_path, monkeypatch):
    from app.services import bo_dataset_import as service

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client)
        request = commit_request(body, preflight(client, body))
        original = service.commit_dataset_import

        def race(root, request_id, request_sha256, create):
            with sqlite3.connect(metadata_db_path(root)) as db:
                db.execute(
                    "UPDATE dataset_versions SET schema_hash=? WHERE version_id=?",
                    ("c" * 64, version["version_id"]),
                )
            return original(root, request_id, request_sha256, create)

        monkeypatch.setattr(service, "commit_dataset_import", race)
        response = client.post(f"{ROOT}/from-dataset", json=request)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "bayesian_import_source_stale"
        assert client.get(ROOT).json()["total"] == 0


def test_source_fk_blocks_sql_deletion_and_releases_only_after_study_delete(tmp_path):
    from tests.unit.test_bayesian_study_lifecycle_api import _close_request

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client)
        saved = client.post(
            f"{ROOT}/from-dataset", json=commit_request(body, preflight(client, body))
        ).json()
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            db.execute("PRAGMA foreign_keys=ON")
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "DELETE FROM dataset_versions WHERE version_id=?", (version["version_id"],)
                )
        closed = client.post(
            f"{ROOT}/{saved['study_id']}/close",
            json=_close_request(saved, target_status="abandoned", reason_code="study_cancelled"),
        )
        assert closed.status_code == 200, closed.text
        deletion = client.get(f"{ROOT}/{saved['study_id']}/deletion-preflight").json()
        deleted = client.request(
            "DELETE",
            f"{ROOT}/{saved['study_id']}",
            json={
                "confirmation_study_id": saved["study_id"],
                "expected_deletion_manifest_sha256": deletion["deletion_manifest_sha256"],
            },
        )
        assert deleted.status_code == 200, deleted.text
        dataset_deletion = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/deletion-preflight"
        ).json()
        assert dataset_deletion["deletion_ready"] is True


def test_explicit_filter_reduces_raw_budget_without_truncation(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client, ("x,y\n" + "1,2\n" * 200 + "9,3\n").encode())
        body["filter_snapshot"]["conditions"] = [
            {"column_id": version["columns"][0]["column_id"], "operator": "lt", "value": 5}
        ]
        preview = preflight(client, body)
        assert (preview["n_total"], preview["n_filtered"], preview["n_used"]) == (201, 1, 200)
        response = client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview))
        assert response.status_code == 201, response.text
        assert response.json()["completed_trial_count"] == 200
        assert response.json()["recommendation_available"] is False


def test_source_file_disappearing_during_commit_is_a_redacted_conflict(tmp_path, monkeypatch):
    from app.services import bo_dataset_import as service

    with TestClient(
        create_app(Settings(workspace_root=tmp_path)), raise_server_exceptions=False
    ) as client:
        body, _ = import_request(client)
        request = commit_request(body, preflight(client, body))

        def disappear(_context):
            raise FileNotFoundError("synthetic private path")

        monkeypatch.setattr(service, "iter_dataset_rows", disappear)
        rejected = client.post(f"{ROOT}/from-dataset", json=request)
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "bayesian_import_source_stale"
        assert "synthetic private path" not in rejected.text
        assert client.get(ROOT).json()["total"] == 0
