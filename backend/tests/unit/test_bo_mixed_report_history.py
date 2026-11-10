"""An exact mixed report must not depend on unrelated later batch artifacts."""

import hashlib
import sqlite3
from dataclasses import asdict
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.bayesian_studies import get_bayesian_recommendation_batch_record
from app.storage.metadata import metadata_db_path
from tests.unit.test_bo_mixed_batches_api import (
    confirm_payload,
    create_selection,
    prepare,
    selection_body,
)


def test_exact_mixed_report_ignores_later_corrupt_batch_and_current_loader(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "historical mixed report")
    with TestClient(create_app(settings)) as client:
        study, endpoint, model, page = prepare(client, fit=False)
        selection = create_selection(
            client,
            endpoint,
            selection_body(study, model, page, policy="greedy_mixed_maximin_v1"),
        )
        response = client.post(
            endpoint + "/mixed-selections/" + selection["selection_id"] + "/confirm",
            json=confirm_payload(selection),
        )
        assert response.status_code == 201, response.text
        batch = response.json()
        record = get_bayesian_recommendation_batch_record(
            settings.workspace_root, batch["batch_id"]
        )
        assert record is not None
        source = {
            "kind": "bayesian_history_revision",
            "study_id": study["study_id"],
            "study_version_id": study["study_version_id"],
            "definition_sha256": study["definition_sha256"],
            "history_revision_id": batch["source_history_revision_id"],
            "expected_source_sha256": batch["source_observation_history_sha256"],
            "attachment": {
                "kind": "batch",
                "batch_id": batch["batch_id"],
                "result_json_sha256": record.result_sha256,
                "result_payload_sha256": batch["result_sha256"],
            },
        }
        before = client.post("/api/v1/reports/capability", json={"source": source, "locale": "en"})
        assert before.status_code == 200, before.text
        unrelated = asdict(record)
        unrelated.update(
            batch_id=str(uuid4()),
            config_json="{}",
            result_json="{}",
            config_sha256=hashlib.sha256(b"{}").hexdigest(),
            result_sha256=hashlib.sha256(b"{}").hexdigest(),
        )
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            columns = tuple(unrelated)
            db.execute(
                f"INSERT INTO bayesian_recommendation_batches({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                tuple(unrelated[column] for column in columns),
            )

        def no_current(*args, **kwargs):
            raise AssertionError("exact historical report must not load current study")

        monkeypatch.setattr("app.services.bo_mixed_studies.load_validated_mixed_study", no_current)
        monkeypatch.setattr("app.services.bo_mixed_studies.get_mixed_study", no_current)
        monkeypatch.setattr(
            "app.services.bo_mixed_report_source.load_validated_mixed_study",
            no_current,
            raising=False,
        )
        monkeypatch.setattr("app.services.bo_planning.run_planning_operation", no_current)
        after = client.post("/api/v1/reports/capability", json={"source": source, "locale": "en"})
        assert after.status_code == 200, after.text
        assert after.json() == before.json()
        report = client.post(
            "/api/v1/reports",
            json={
                "source": source,
                "locale": "en",
                "expected_source_ref_sha256": after.json()["source_ref_sha256"],
            },
        )
        assert report.status_code == 201, report.text
        exported = report.json()
        downloaded = client.post(
            "/api/v1/reports/" + exported["export_id"] + "/download",
            json={
                "source": source,
                "expected_sha256": exported["sha256"],
            },
        )
        assert downloaded.status_code == 200, downloaded.text
        assert hashlib.sha256(downloaded.content).hexdigest() == exported["sha256"]
        assert batch["source"]["selection_result_sha256"] in downloaded.text
        assert unrelated["batch_id"] not in downloaded.text
