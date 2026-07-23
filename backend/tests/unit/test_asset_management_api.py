import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    AnalysisRunRecord,
    DatasetColumnRecord,
    DatasetRecord,
    DatasetVersionRecord,
    RegressionModelRecord,
    get_analysis_run_record,
    get_dataset_version_record,
    get_regression_model_record,
    initialize_metadata_store,
    insert_analysis_run_record_with_artifacts_and_regression_model,
    insert_dataset_record,
    insert_dataset_version_record,
    metadata_db_path,
)


def test_asset_metadata_round_trip_order_and_integrity_boundaries(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    initialize_metadata_store(settings.workspace_root)
    dataset_a, version_a = _insert_dataset(settings, created_at="2026-07-20T00:00:00Z")
    _, version_b = _insert_dataset(settings, created_at="2026-07-21T00:00:00Z")
    model_id, analysis_id = _insert_model(settings, version_a)
    version_before = get_dataset_version_record(settings.workspace_root, version_a)
    model_before = get_regression_model_record(settings.workspace_root, model_id)
    analysis_before = get_analysis_run_record(settings.workspace_root, analysis_id)

    with TestClient(create_app(settings)) as client:
        dataset_response = client.patch(
            f"/api/v1/dataset-versions/{version_a}/metadata",
            json={"user_label": "  기준 데이터  ", "note": "  검토 완료  ", "pinned": True},
        )
        model_response = client.patch(
            f"/api/v1/regression-models/{model_id}/metadata",
            json={"user_label": " 수율 모델 ", "note": " Predict 전용 ", "pinned": True},
        )
        dataset_catalog = client.get("/api/v1/dataset-versions?offset=0&limit=20")
        model_catalog = client.get("/api/v1/regression-models?offset=0&limit=20")
        cleared = client.patch(
            f"/api/v1/dataset-versions/{version_a}/metadata",
            json={
                "user_label": "   ",
                "note": "",
                "pinned": False,
                "expected_metadata_updated_at": dataset_response.json()["metadata_updated_at"],
            },
        )
        stale_update = client.patch(
            f"/api/v1/dataset-versions/{version_a}/metadata",
            json={
                "user_label": "stale",
                "pinned": False,
                "expected_metadata_updated_at": "outdated",
            },
        )
        invalid_text = client.patch(
            f"/api/v1/regression-models/{model_id}/metadata",
            json={"user_label": "bad\nlabel", "pinned": False},
        )

    assert dataset_response.status_code == 200
    assert dataset_response.json()["user_label"] == "기준 데이터"
    assert dataset_response.json()["note"] == "검토 완료"
    assert dataset_response.json()["pinned"] is True
    assert model_response.status_code == 200
    assert model_response.json()["user_label"] == "수율 모델"
    assert model_response.json()["note"] == "Predict 전용"
    assert model_response.json()["pinned"] is True
    assert dataset_catalog.status_code == 200
    assert dataset_catalog.json()["versions"][0]["version_id"] == version_a
    assert dataset_catalog.json()["versions"][0]["original_filename"] == (f"{dataset_a}.csv")
    assert dataset_catalog.json()["versions"][0]["user_label"] == "기준 데이터"
    assert dataset_catalog.json()["versions"][1]["version_id"] == version_b
    assert model_catalog.status_code == 200
    assert model_catalog.json()["models"][0]["user_label"] == "수율 모델"
    assert model_catalog.json()["models"][0]["availability"] == "integrity_error"
    assert "manifest_path" not in model_catalog.text
    assert cleared.status_code == 200
    assert cleared.json()["user_label"] is None
    assert cleared.json()["note"] is None
    assert stale_update.status_code == 409
    assert stale_update.json()["error"]["code"] == "asset_user_metadata_conflict"
    assert invalid_text.status_code == 422

    assert get_dataset_version_record(settings.workspace_root, version_a) == version_before
    assert get_regression_model_record(settings.workspace_root, model_id) == model_before
    assert get_analysis_run_record(settings.workspace_root, analysis_id) == analysis_before


def test_schema_14_migrates_asset_metadata_tables(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)):
        pass
    db_path = metadata_db_path(settings.workspace_root)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE regression_model_user_metadata")
        connection.execute("DROP TABLE dataset_version_user_metadata")
        connection.execute("DELETE FROM schema_migrations WHERE version >= 15")
        connection.execute("PRAGMA user_version = 14")

    with TestClient(create_app(settings)):
        pass

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
    assert "dataset_version_user_metadata" in tables
    assert "regression_model_user_metadata" in tables
    assert user_version == 16


def test_dataset_archive_visibility_round_trip_and_schema_15_upgrade(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    initialize_metadata_store(settings.workspace_root)
    _, visible_version = _insert_dataset(
        settings,
        created_at="2026-07-20T00:00:00Z",
    )
    _, archived_version = _insert_dataset(
        settings,
        created_at="2026-07-21T00:00:00Z",
    )

    with TestClient(create_app(settings)) as client:
        archived = client.patch(
            f"/api/v1/dataset-versions/{archived_version}/metadata",
            json={"archived": True},
        )
        visible_catalog = client.get(
            "/api/v1/dataset-versions?offset=0&limit=20&visibility=visible"
        )
        archived_catalog = client.get(
            "/api/v1/dataset-versions?offset=0&limit=20&visibility=archived"
        )
        all_catalog = client.get(
            "/api/v1/dataset-versions?offset=0&limit=20&visibility=all"
        )
        direct = client.get(f"/api/v1/dataset-versions/{archived_version}")
        restored = client.patch(
            f"/api/v1/dataset-versions/{archived_version}/metadata",
            json={
                "archived": False,
                "expected_metadata_updated_at": archived.json()["metadata_updated_at"],
            },
        )

    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert archived.json()["archived_at"] is not None
    assert [item["version_id"] for item in visible_catalog.json()["versions"]] == [
        visible_version
    ]
    assert [item["version_id"] for item in archived_catalog.json()["versions"]] == [
        archived_version
    ]
    assert all_catalog.json()["total"] == 2
    assert direct.status_code == 200
    assert restored.status_code == 200
    assert restored.json()["archived"] is False
    assert restored.json()["archived_at"] is None

    db_path = metadata_db_path(settings.workspace_root)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DELETE FROM schema_migrations WHERE version = 16")
        connection.execute("DROP INDEX idx_dataset_version_user_metadata_visibility")
        connection.execute(
            """
            CREATE TABLE dataset_version_user_metadata_v15 (
                version_id TEXT PRIMARY KEY
                    REFERENCES dataset_versions(version_id) ON DELETE CASCADE,
                user_label TEXT,
                note TEXT,
                pinned INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            """
        )
        connection.execute(
            """
            INSERT INTO dataset_version_user_metadata_v15
                (version_id, user_label, note, pinned, updated_at)
            SELECT version_id, user_label, note, pinned, updated_at
            FROM dataset_version_user_metadata;
            """
        )
        connection.execute("DROP TABLE dataset_version_user_metadata")
        connection.execute(
            "ALTER TABLE dataset_version_user_metadata_v15 "
            "RENAME TO dataset_version_user_metadata"
        )
        connection.execute("PRAGMA user_version = 15")

    initialize_metadata_store(settings.workspace_root)
    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(dataset_version_user_metadata)"
            ).fetchall()
        }
        archived_values = connection.execute(
            "SELECT archived, archived_at FROM dataset_version_user_metadata"
        ).fetchall()
    assert {"archived", "archived_at"}.issubset(columns)
    assert all(row == (0, None) for row in archived_values)


def _insert_dataset(settings: Settings, *, created_at: str) -> tuple[str, str]:
    dataset_id = str(uuid4())
    version_id = str(uuid4())
    insert_dataset_record(
        settings.workspace_root,
        DatasetRecord(
            dataset_id=dataset_id,
            original_filename=f"{dataset_id}.csv",
            safe_filename="dataset.csv",
            media_type="text/csv",
            detected_format="csv",
            stored_path=f"datasets/{dataset_id}/raw.csv",
            sha256="a" * 64,
            size_bytes=10,
            created_at=created_at,
        ),
    )
    insert_dataset_version_record(
        settings.workspace_root,
        DatasetVersionRecord(
            version_id=version_id,
            dataset_id=dataset_id,
            version_number=1,
            source_sha256="a" * 64,
            parsing_options_json='{"kind":"delimited_text"}',
            row_count=2,
            column_count=1,
            schema_hash="b" * 64,
            created_at=created_at,
        ),
        [
            DatasetColumnRecord(
                column_id=str(uuid4()),
                version_id=version_id,
                column_index=0,
                original_name="value",
                display_name="value",
                data_type="decimal",
                measurement_level="continuous",
                role="feature",
                unit=None,
            )
        ],
    )
    return dataset_id, version_id


def _insert_model(settings: Settings, version_id: str) -> tuple[str, str]:
    analysis_id = str(uuid4())
    model_id = str(uuid4())
    created_at = "2026-07-22T00:00:00Z"
    insert_analysis_run_record_with_artifacts_and_regression_model(
        settings.workspace_root,
        AnalysisRunRecord(
            analysis_id=analysis_id,
            method_id="regression.linear_model",
            method_version="0.1.0",
            dataset_version_id=version_id,
            config_json="{}",
            status="succeeded",
            result_path=None,
            result_sha256=None,
            stale=False,
            created_at=created_at,
            updated_at=created_at,
            completed_at=created_at,
            app_version="0.1.0",
        ),
        [],
        RegressionModelRecord(
            model_id=model_id,
            analysis_id=analysis_id,
            dataset_version_id=version_id,
            method_id="regression.linear_model",
            method_version="0.1.0",
            manifest_path="models/missing.json",
            manifest_sha256="c" * 64,
            schema_hash="b" * 64,
            created_at=created_at,
            app_version="0.1.0",
        ),
    )
    return model_id, analysis_id
