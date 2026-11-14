"""Historical mixture reports have an exact immutable source, not a live overlay."""

import json
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services.bo_mixture_report_source import read_mixture_bayesian
from app.services.bo_mixture_studies import load_validated_mixture_study
from app.services.dedicated_report_sources import list_dedicated_report_sources
from app.storage.metadata import metadata_db_path
from tests.unit.test_bo_mixed_planning_api import fit_options, source
from tests.unit.test_bo_mixture_lifecycle_api import observations, request


@pytest.mark.parametrize("fault", ["bytes", "overlay"])
def test_mixture_history_and_batch_report_use_saved_values(tmp_path, monkeypatch, fault):
    settings = Settings(workspace_root=tmp_path / "mixture reports")
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/v1/bayesian-studies/mixture", json=request())
        assert created.status_code == 201, created.text
        study = created.json()
        base = "/api/v1/bayesian-studies/" + study["study_id"]
        completed = client.put(base + "/observations/batch", json=observations(study))
        assert completed.status_code == 200, completed.text
        study = completed.json()["study"]
        fitted = client.post(
            base + "/mixture-planning-models",
            json={
                **source(study),
                "request_id": str(uuid4()),
                "fit": fit_options(),
            },
        )
        assert fitted.status_code == 201, fitted.text
        model = fitted.json()
        candidate = client.post(
            base + "/mixture-candidate-revisions",
            json={
                **source(study),
                "schema_version": 4,
                "request_id": str(uuid4()),
                "candidate_set_id": str(uuid4()),
                "name": "Synthetic report candidates",
                "model_id": model["model_id"],
                "expected_model_sha256": model["snapshot_sha256"],
                "source": {"kind": "seeded_uniform", "seed": 17, "count": 4},
            },
        )
        assert candidate.status_code == 201, candidate.text
        page = candidate.json()
        selected = client.post(
            base + "/mixture-selections",
            json={
                **source(study),
                "schema_version": 6,
                "request_id": str(uuid4()),
                "candidate_revision_id": page["revision"]["revision_id"],
                "expected_rows_sha256": page["revision"]["rows_sha256"],
                "model_id": model["model_id"],
                "expected_model_sha256": model["snapshot_sha256"],
                "policy": "manual_mixture_base_posterior_v1",
                "row_ids": [page["items"][0]["row_id"]],
                "batch_size": 1,
                "total_trial_budget": 20,
            },
        )
        assert selected.status_code == 201, selected.text
        selection = selected.json()
        confirmed = client.post(
            base + "/mixture-selections/" + selection["selection_id"] + "/confirm",
            json={
                "expected_config_sha256": selection["config_sha256"],
                "expected_result_sha256": selection["result_sha256"],
            },
        )
        assert confirmed.status_code == 201, confirmed.text
        current = client.get(base).json()
        assert (
            client.put(base + "/observations/batch", json=observations(current)).status_code == 200
        )

        def forbidden(*args, **kwargs):
            raise AssertionError(
                "Report must not fit, evaluate, or validate unrelated live batches"
            )

        monkeypatch.setattr("app.services.bo_mixture_workflow._run", forbidden)
        monkeypatch.setattr(
            "app.services.bo_mixture_studies.load_validated_mixture_study", forbidden
        )
        catalog = list_dedicated_report_sources(settings, "bayesian_history_revision")
        exact = [
            item
            for item in catalog.items
            if str(item.source.history_revision_id)
            == study["observation_history"]["history_revision_id"]
        ]
        assert {item.source.attachment.kind for item in exact} >= {"none", "batch"}
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            before = db.execute(
                "SELECT config_json,result_json FROM bayesian_recommendation_batches"
            ).fetchall()
        for descriptor in exact:
            if descriptor.source.attachment.kind == "batch":
                assert "mixture_planning_batch_id=" in descriptor.open_target
                resolved = client.get(
                    base
                    + "/mixture-planning-batches/"
                    + selection["selection_id"]
                    + "/report-source"
                )
                assert resolved.status_code == 200, resolved.text
                assert resolved.json()["source_ref_sha256"] == descriptor.source_ref_sha256
            exported = client.post(
                "/api/v1/reports",
                json={
                    "source": descriptor.source.model_dump(mode="json"),
                    "expected_source_ref_sha256": descriptor.source_ref_sha256,
                    "locale": "en",
                },
            )
            assert exported.status_code == 201, exported.text
            artifact = exported.json()
            download = client.post(
                "/api/v1/reports/" + artifact["export_id"] + "/download",
                json={
                    "source": descriptor.source.model_dump(mode="json"),
                    "expected_sha256": artifact["sha256"],
                },
            )
            assert download.status_code == 200, download.text
            assert "mixture_pseudocomponents_process_v1" in download.text
            assert "<svg" in download.text
            assert "default-src 'none'" in download.headers["Content-Security-Policy"]
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            assert (
                db.execute(
                    "SELECT config_json,result_json FROM bayesian_recommendation_batches"
                ).fetchall()
                == before
            )
        batch_descriptor = next(item for item in exact if item.source.attachment.kind == "batch")
        report_request = {
            "source": batch_descriptor.source.model_dump(mode="json"),
            "expected_source_ref_sha256": batch_descriptor.source_ref_sha256,
            "locale": "en",
        }
        # Copied digest columns cannot make altered immutable document bytes valid.
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            original_config, original_result = db.execute(
                "SELECT config_json,result_json FROM bayesian_recommendation_batches "
                "WHERE batch_id=?",
                (selection["selection_id"],),
            ).fetchone()
        changed_config = json.loads(original_config)
        changed_config["total_trial_budget"] += 1
        assert (
            changed_config["expected_trial_count"]
            == json.loads(original_config)["expected_trial_count"]
        )
        mutations = (
            (
                ("result_json", "{}", original_result),
                ("config_json", json.dumps(changed_config), original_config),
            )
            if fault == "bytes"
            else ()
        )
        for column, changed, original in mutations:
            with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                db.execute(
                    f"UPDATE bayesian_recommendation_batches SET {column}=? WHERE batch_id=?",
                    (changed, selection["selection_id"]),
                )
            try:
                rejected = client.post("/api/v1/reports", json=report_request)
                assert rejected.status_code == 409, (column, rejected.text)
                with pytest.raises(ApiError) as invalid_source:
                    read_mixture_bayesian(settings, batch_descriptor.source)
                assert invalid_source.value.status_code == 409
                with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                    assert (
                        db.execute(
                            f"SELECT {column} FROM bayesian_recommendation_batches "
                            "WHERE batch_id=?",
                            (selection["selection_id"],),
                        ).fetchone()[0]
                        == changed
                    )
            finally:
                with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                    db.execute(
                        f"UPDATE bayesian_recommendation_batches SET {column}=? WHERE batch_id=?",
                        (original, selection["selection_id"]),
                    )

        exported = client.post("/api/v1/reports", json=report_request)
        assert exported.status_code == 201, exported.text
        saved_artifact = exported.json()
        download_path = "/api/v1/reports/" + saved_artifact["export_id"] + "/download"
        download_body = {
            "source": report_request["source"],
            "expected_sha256": saved_artifact["sha256"],
        }
        original_download = client.post(download_path, json=download_body)
        assert original_download.status_code == 200
        selected_trial_id = confirmed.json()["items"][0]["trial"]["trial_id"]
        immutable_payload = read_mixture_bayesian(settings, batch_descriptor.source)
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            old_overlay = db.execute(
                "SELECT response_values_json FROM bayesian_trials WHERE trial_id=?",
                (selected_trial_id,),
            ).fetchone()[0]
            db.execute(
                "UPDATE bayesian_trials SET response_values_json='{}' WHERE trial_id=?",
                (selected_trial_id,),
            )
        try:
            monkeypatch.setattr(
                "app.services.bo_mixture_studies.load_validated_mixture_study",
                load_validated_mixture_study,
            )
            assert client.get(base).status_code == 409
            monkeypatch.setattr(
                "app.services.bo_mixture_studies.load_validated_mixture_study", forbidden
            )
            exported_after = client.post("/api/v1/reports", json=report_request)
            assert exported_after.status_code == 201, exported_after.text
            assert read_mixture_bayesian(settings, batch_descriptor.source) == immutable_payload
            historical = client.post(download_path, json=download_body)
            assert historical.status_code == 200, historical.text
            assert historical.content == original_download.content
        finally:
            with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                db.execute(
                    "UPDATE bayesian_trials SET response_values_json=? WHERE trial_id=?",
                    (old_overlay, selected_trial_id),
                )

        # Historical projection excludes only mutable lifecycle/response overlay.
        for column, changed in (
            ("actual_coordinates_json", "{}"),
            ("study_version_id", str(uuid4())),
            ("trial_number", 100),
        ):
            with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                original = db.execute(
                    f"SELECT {column} FROM bayesian_trials WHERE trial_id=?", (selected_trial_id,)
                ).fetchone()[0]
                db.execute(
                    f"UPDATE bayesian_trials SET {column}=? WHERE trial_id=?",
                    (changed, selected_trial_id),
                )
            try:
                rejected = client.post("/api/v1/reports", json=report_request)
                assert rejected.status_code == 409, (column, rejected.text)
            finally:
                with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                    db.execute(
                        f"UPDATE bayesian_trials SET {column}=? WHERE trial_id=?",
                        (original, selected_trial_id),
                    )
