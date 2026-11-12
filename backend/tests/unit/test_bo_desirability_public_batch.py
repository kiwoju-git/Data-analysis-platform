"""Synthetic public ordered-batch lifecycle, including actual owned worker."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bayesian_multiresponse_lifecycle import observations, url
from tests.unit.test_bo_desirability_review_api import completed, review_request


def batch_request(study, size=2):
    result = review_request(study)
    result.update(
        schema_version=5,
        batch_size=size,
        batch_options={
            "sample_count": 16,
            "max_moment_evaluations": 8192,
            "min_batch_distance_normalized": 0.01,
        },
    )
    result["search"]["max_evaluations_total"] = 1024
    if size == 8:
        for model in result["response_models"]:
            model["kernel"]["kind"] = "exponential"
            model["surrogate"] = {"noise_mode": "fixed", "fixed_noise_sd": 0.2}
    return result


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 4},
        {"schema_version": 5.0},
        {"batch_size": True},
        {"batch_size": "2"},
        {"batch_size": 2.0},
        {"batch_size": 0},
        {"batch_size": 9},
        {"batch_options": None},
        {"batch_options": {"sample_count": 15}},
        {"batch_options": {"sample_count": 257}},
        {"batch_options": {"sample_count": 16, "max_moment_evaluations": 0}},
        {"batch_options": {"sample_count": 16, "min_batch_distance_normalized": -0.1}},
    ],
)
def test_invalid_public_batch_contract_rejected_before_worker(tmp_path, monkeypatch, change):
    from app.services import bo_desirability_worker

    def forbidden(*args, **kwargs):
        pytest.fail("invalid public request must not enter either calculation worker")

    monkeypatch.setattr(bo_desirability_worker, "run_desirability_calculation", forbidden)
    monkeypatch.setattr(bo_desirability_worker, "run_desirability_batch_calculation", forbidden)
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        body = batch_request(study)
        body.update(change)
        response = client.post(url(study) + "/desirability-reviews", json=body)
        assert response.status_code == 422, response.text
        assert client.get(url(study)).json() == study
        assert client.get(url(study) + "/desirability-recommendations/latest").json() == {
            "item": None
        }


@pytest.mark.parametrize("size", [2, 8])
def test_real_worker_review_atomic_confirm_partial_measurement_and_restart(
    tmp_path, monkeypatch, size
):
    settings = Settings(workspace_root=tmp_path / "workspace")
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        response = client.post(
            url(study) + "/desirability-reviews", json=batch_request(study, size)
        )
        assert response.status_code == 200, response.text
        review = response.json()
        assert review["schema_version"] == 3
        assert client.get(url(study)).json()["trials"] == study["trials"]
        from app.services import bo_desirability_worker

        def forbidden(*args, **kwargs):
            pytest.fail("confirmation/restore/report must not fit")

        monkeypatch.setattr(bo_desirability_worker, "run_desirability_batch_calculation", forbidden)
        confirm_url = url(study) + f"/desirability-reviews/{review['review_id']}/confirm"
        body = {"expected_config_sha256": review["config_sha256"]}
        response = client.post(confirm_url, json=body)
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["result_schema_version"] == batch["config_schema_version"] == 5
        assert batch["method_version"] == "0.10.0"
        assert batch["model_schema_version"] == 5 and batch["item_schema_version"] == 4
        assert batch["calculation"] == review["calculation"]
        assert len(batch["items"]) == batch["batch_size"] == size
        assert [item["rank"] for item in batch["items"]] == list(range(1, size + 1))
        for item, calculated in zip(batch["items"], batch["calculation"]["items"], strict=True):
            assert item["trial"]["trial_number"] - item["rank"] == len(study["trials"])
            assert item["trial"]["actual_coordinates"] == calculated["actual_coordinates"]
            assert item["trial"]["objective_value"] is None
            assert "response_values" not in item["trial"]
        assert client.post(confirm_url, json=body).json() == batch
        current = client.get(url(study)).json()
        assert current["trial_count"] == len(study["trials"]) + size
        # Complete the second item first; predictions never fill actual vectors.
        observed = client.put(url(study) + "/observations/batch", json=observations(current, (4,)))
        assert observed.status_code == 200, observed.text
        saved_url = url(study) + f"/desirability-recommendations/{batch['batch_id']}"
        partial = client.get(saved_url)
        assert partial.status_code == 200, partial.text
        partial = partial.json()
        assert partial["batch_state"] == "partially_completed"
        assert partial["result_sha256"] == batch["result_sha256"]
        assert partial["calculation"] == batch["calculation"]
        assert partial["items"][1]["current_trial"]["state"] == "completed"
        assert all(item["trial"]["state"] == "pending" for item in partial["items"])
        assert client.post(confirm_url, json=body).json() == partial
        blocked = client.post(
            url(study) + "/desirability-reviews", json=batch_request(observed.json()["study"])
        )
        assert blocked.status_code == 409
        assert (
            blocked.json()["error"]["code"] == "bayesian_optimization_pending_recommendation_exists"
        )
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            immutable_before = db.execute(
                "SELECT result_json,result_sha256 FROM bayesian_recommendation_batches "
                "WHERE batch_id=?",
                (batch["batch_id"],),
            ).fetchone()
            assert json.loads(immutable_before[0])["items"] == batch["items"]
    with TestClient(create_app(settings)) as client:
        assert client.get(saved_url).json() == partial
        assert client.post(confirm_url, json=body).json() == partial
        common = url(study) + "/recommendation-batches"
        assert client.get(common + "/latest").json()["item"] == partial
        assert client.get(common + f"/{batch['batch_id']}").json() == partial
        assert client.get(common).json()["items"] == [partial]
        current = client.get(url(study)).json()
        remaining = tuple(
            i for i, trial in enumerate(current["trials"]) if trial["state"] == "pending"
        )
        response = client.put(
            url(study) + "/observations/batch", json=observations(current, remaining)
        )
        assert response.status_code == 200, response.text
        finished = client.get(saved_url).json()
        assert finished["batch_state"] == "completed"
        assert finished["result_sha256"] == batch["result_sha256"]
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            assert (
                db.execute(
                    "SELECT result_json,result_sha256 FROM bayesian_recommendation_batches "
                    "WHERE batch_id=?",
                    (batch["batch_id"],),
                ).fetchone()
                == immutable_before
            )


def test_concentrated_beta_q8_review_succeeds_without_creating_pending(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed(client)
        body = batch_request(study, 8)
        for model in body["response_models"]:
            model["kernel"]["kind"] = "matern_5_2"
            model["surrogate"] = {"noise_mode": "estimate"}
        reviewed = client.post(url(study) + "/desirability-reviews", json=body)
        assert reviewed.status_code == 200, reviewed.text
        items = reviewed.json()["calculation"]["items"]
        assert len(items) == 8
        assert all(item["acquisition"]["value"] >= 0 for item in items)
        assert items[0]["acquisition"]["value"] > 0
        assert client.get(url(study)).json() == study
        assert (
            client.get(url(study) + "/desirability-recommendations/latest").json()["item"] is None
        )
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            assert db.execute(
                "SELECT COUNT(*) FROM bayesian_recommendation_batches"
            ).fetchone() == (0,)


def test_unresolved_beta_precision_still_creates_no_partial_review_or_trials(tmp_path, monkeypatch):
    from app.statistics.bo_desirability_acquisition import beta_expected_improvement

    def unresolved(*args, **kwargs):
        beta_expected_improvement(0.5, 1e-28, 0.5)

    monkeypatch.setattr(
        "app.services.bo_desirability_worker.run_desirability_batch_calculation", unresolved
    )
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed(client)
        response = client.post(url(study) + "/desirability-reviews", json=batch_request(study))
        assert response.status_code == 409, response.text
        assert (
            response.json()["error"]["code"] == "bayesian_desirability_beta_precision_unsupported"
        )
        assert client.get(url(study)).json() == study
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            assert db.execute(
                "SELECT COUNT(*) FROM bayesian_recommendation_batches"
            ).fetchone() == (0,)


@pytest.fixture
def reviewed_batch(tmp_path, monkeypatch):
    from threadpoolctl import threadpool_limits

    from app.api.v1.schemas.bo_desirability_batch_calculation import (
        DesirabilityBatchCalculationResult,
    )
    from app.statistics.bo_desirability_batch_core import calculate_desirability_batch

    def worker(request):
        with threadpool_limits(limits=1):
            calculated = calculate_desirability_batch(request.worker_payload())
        return SimpleNamespace(
            calculation=DesirabilityBatchCalculationResult.model_validate_json(
                json.dumps(calculated)
            )
        )

    monkeypatch.setattr(
        "app.services.bo_desirability_worker.run_desirability_batch_calculation", worker
    )
    app = create_app(Settings(workspace_root=tmp_path / "workspace"))
    with TestClient(app) as client:
        study = completed(client)
        reviewed = client.post(url(study) + "/desirability-reviews", json=batch_request(study))
        assert reviewed.status_code == 200, reviewed.text
        review = reviewed.json()
        confirm_url = url(study) + f"/desirability-reviews/{review['review_id']}/confirm"
        yield client, app, study, review, confirm_url


def test_atomic_rank2_failure_rolls_back_entire_batch_and_same_review_retries(reviewed_batch):
    client, app, study, review, confirm_url = reviewed_batch
    root = app.state.settings.workspace_root
    body = {"expected_config_sha256": review["config_sha256"]}
    with sqlite3.connect(metadata_db_path(root)) as db:
        db.execute(
            "CREATE TRIGGER synthetic_rank2 BEFORE INSERT ON bayesian_recommendation_batch_items "
            "WHEN NEW.rank=2 BEGIN SELECT RAISE(ABORT,'synthetic rank2'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic rank2"):
        client.post(confirm_url, json=body)
    assert client.get(url(study)).json()["trials"] == study["trials"]
    with sqlite3.connect(metadata_db_path(root)) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_recommendation_batches").fetchone() == (0,)
        assert db.execute(
            "SELECT COUNT(*) FROM bayesian_recommendation_batch_items"
        ).fetchone() == (0,)
        db.execute("DROP TRIGGER synthetic_rank2")
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: client.post(confirm_url, json=body), range(2)))
    assert all(r.status_code == 201 for r in replies), [r.text for r in replies]
    assert replies[0].json() == replies[1].json()
    assert client.get(url(study)).json()["trial_count"] == 5
    app.state.bayesian_reviews.clear()
    assert client.post(confirm_url, json=body).json() == replies[0].json()
    changed = client.post(confirm_url, json={"expected_config_sha256": "0" * 64})
    assert changed.status_code == 409


def test_trial_count_locks_review_even_after_whole_batch_abandoned(reviewed_batch):
    client, _, study, review, confirm_url = reviewed_batch
    second = client.post(url(study) + "/desirability-reviews", json=batch_request(study))
    assert second.status_code == 200, second.text
    second = second.json()
    confirmed = client.post(confirm_url, json={"expected_config_sha256": review["config_sha256"]})
    assert confirmed.status_code == 201, confirmed.text
    for item in confirmed.json()["items"]:
        assert (
            client.post(url(study) + f"/trials/{item['trial']['trial_id']}/abandon").status_code
            == 200
        )
    current = client.get(url(study)).json()
    assert current["observation_history"] == study["observation_history"]
    rejected = client.post(
        url(study) + f"/desirability-reviews/{second['review_id']}/confirm",
        json={"expected_config_sha256": second["config_sha256"]},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "bayesian_optimization_history_stale"
    saved = client.get(url(study) + f"/desirability-recommendations/{review['review_id']}").json()
    assert saved["batch_state"] == "abandoned"


def test_report_uses_whole_saved_batch_exact_source_without_refit(reviewed_batch, monkeypatch):
    import hashlib

    from test_dedicated_report_sources import no_recompute
    from test_managed_report_api import VisibleReport

    client, app, study, review, confirm_url = reviewed_batch
    response = client.post(confirm_url, json={"expected_config_sha256": review["config_sha256"]})
    assert response.status_code == 201, response.text
    batch = response.json()
    root = app.state.settings.workspace_root
    with sqlite3.connect(metadata_db_path(root)) as db:
        stored = db.execute(
            "SELECT result_json,result_sha256 FROM bayesian_recommendation_batches"
        ).fetchone()
    source = {
        "kind": "bayesian_history_revision",
        "study_id": study["study_id"],
        "study_version_id": study["study_version_id"],
        "definition_sha256": study["definition_sha256"],
        "history_revision_id": review["source_history_revision_id"],
        "expected_source_sha256": review["source_observation_history_sha256"],
        "attachment": {
            "kind": "batch",
            "batch_id": batch["batch_id"],
            "result_json_sha256": stored[1],
            "result_payload_sha256": batch["result_sha256"],
        },
    }
    current = client.get(url(study)).json()
    measured = client.put(url(study) + "/observations/batch", json=observations(current, (3,)))
    assert measured.status_code == 200, measured.text
    no_recompute(monkeypatch)

    def no_current(*args, **kwargs):
        pytest.fail("report must not silently advance to current study history")

    for path in (
        "app.statistics.bo_desirability_batch_core.calculate_desirability_batch",
        "app.services.bo_desirability_worker.run_desirability_batch_calculation",
        "app.statistics.bo_surrogate.fit_bo_surrogate",
    ):
        monkeypatch.setattr(path, no_current)
    monkeypatch.setattr("app.services.bayesian_studies.get_bayesian_study", no_current)
    for locale in ("en", "ko"):
        capability = client.post(
            "/api/v1/reports/capability", json={"source": source, "locale": locale}
        )
        assert capability.status_code == 200, capability.text
        created = client.post(
            "/api/v1/reports",
            json={
                "source": source,
                "locale": locale,
                "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
            },
        )
        assert created.status_code == 201, created.text
        record = created.json()
        download = client.post(
            f"/api/v1/reports/{record['export_id']}/download",
            json={"source": source, "expected_sha256": record["sha256"]},
        )
        assert download.status_code == 200, download.text
        assert hashlib.sha256(download.content).hexdigest() == record["sha256"]
        visible = VisibleReport()
        visible.feed(download.text)
        assert 'data-batch-rank="1"' in download.text and 'data-batch-rank="2"' in download.text
        text = "".join(visible.text)
        for item in batch["items"]:
            assert item["trial"]["trial_id"] in text
        assert ("Marginal batch improvement" if locale == "en" else "배치 한계 개선") in text
        assert ("New-observation predictive SD" if locale == "en" else "새 관측 예측 SD") in text
    with sqlite3.connect(metadata_db_path(root)) as db:
        assert (
            db.execute(
                "SELECT result_json,result_sha256 FROM bayesian_recommendation_batches"
            ).fetchone()
            == stored
        )


def test_migration27_bytes_legacy_and_new_batch_backup_restore(tmp_path, monkeypatch):
    from threadpoolctl import threadpool_limits

    from app.api.v1.schemas.bo_desirability_batch_calculation import (
        DesirabilityBatchCalculationResult,
    )
    from app.statistics.bo_desirability_batch_core import calculate_desirability_batch
    from app.storage import metadata

    def worker(request):
        with threadpool_limits(limits=1):
            calculated = calculate_desirability_batch(request.worker_payload())
        return SimpleNamespace(
            calculation=DesirabilityBatchCalculationResult.model_validate_json(
                json.dumps(calculated)
            )
        )

    monkeypatch.setattr(
        "app.services.bo_desirability_worker.run_desirability_batch_calculation", worker
    )
    root = tmp_path / "existing metadata27"
    settings = Settings(workspace_root=root)
    with monkeypatch.context() as context:
        context.setattr(metadata, "SCHEMA_VERSION", 27)
        context.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 27)
        )
        with TestClient(create_app(settings)) as client:
            study = completed(client)
            reviewed = client.post(url(study) + "/desirability-reviews", json=review_request(study))
            assert reviewed.status_code == 200, reviewed.text
            reviewed = reviewed.json()
            legacy = client.post(
                url(study) + f"/desirability-reviews/{reviewed['review_id']}/confirm",
                json={"expected_config_sha256": reviewed["config_sha256"]},
            )
            assert legacy.status_code == 201, legacy.text
            legacy = legacy.json()
    tables = (
        "bayesian_trials",
        "bayesian_study_versions",
        "bayesian_observation_history_revisions",
        "bayesian_recommendation_batches",
        "bayesian_recommendation_batch_items",
    )

    def rows():
        with sqlite3.connect(metadata_db_path(root)) as db:
            return {
                table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in tables
            }

    before = rows()
    assert metadata.initialize_metadata_store(root).schema_version == metadata.SCHEMA_VERSION
    assert rows() == before
    with TestClient(create_app(settings)) as client:
        old_url = url(study) + f"/desirability-recommendations/{legacy['batch_id']}"
        assert client.get(old_url).json() == legacy
        assert (
            client.post(
                url(study) + f"/trials/{legacy['items'][0]['trial']['trial_id']}/abandon"
            ).status_code
            == 200
        )
        study = client.get(url(study)).json()
        reviewed = client.post(url(study) + "/desirability-reviews", json=batch_request(study))
        assert reviewed.status_code == 200, reviewed.text
        reviewed = reviewed.json()
        confirmed = client.post(
            url(study) + f"/desirability-reviews/{reviewed['review_id']}/confirm",
            json={"expected_config_sha256": reviewed["config_sha256"]},
        )
        assert confirmed.status_code == 201, confirmed.text
        batch = confirmed.json()
        old = client.get(old_url).json()
        new_url = url(study) + f"/desirability-recommendations/{batch['batch_id']}"
        with sqlite3.connect(metadata_db_path(root)) as db:
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "UPDATE bayesian_recommendation_batches SET item_schema_version=3 "
                    "WHERE batch_id=?",
                    (batch["batch_id"],),
                )
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "UPDATE bayesian_recommendation_batches SET batch_size=2 WHERE batch_id=?",
                    (legacy["batch_id"],),
                )
    archive = tmp_path / "backup.tar.gz"
    destination = tmp_path / "복원 space"
    backup_workspace(root, archive)
    restore_workspace(archive, destination)
    with TestClient(create_app(Settings(workspace_root=destination))) as client:
        assert client.get(old_url).json() == old
        assert client.get(new_url).json() == batch
