import hashlib
import os
import shutil
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.dataset_version_retention import recover_dataset_version_quarantine_files
from app.storage.metadata import (
    AnalysisRunRecord,
    DatasetArtifactRecord,
    DatasetColumnRecord,
    DatasetVersionRecord,
    get_dataset_artifact_record,
    get_dataset_record,
    get_dataset_version_record,
    insert_analysis_run_record,
    insert_dataset_version_record,
    list_dataset_artifact_records,
    list_dataset_column_records,
    metadata_db_path,
)


def test_dependency_free_last_dataset_version_deletion_removes_owned_files(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client)
        dataset = get_dataset_record(settings.workspace_root, version["dataset_id"])
        assert dataset is not None
        artifact_paths = [
            settings.workspace_root / artifact["path"] for artifact in _artifacts(settings, version)
        ]
        raw_path = settings.workspace_root / dataset.stored_path

        preflight = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/deletion-preflight"
        )
        assert preflight.status_code == 200
        payload = preflight.json()
        assert payload["deletion_ready"] is True
        assert payload["deletion_scope"] == "dataset_root"
        assert payload["counts"]["raw_upload_file_count"] == 1
        assert "path" not in payload
        deleted = client.request(
            "DELETE",
            f"/api/v1/dataset-versions/{version['version_id']}/deletion",
            json={
                "confirmation_version_id": version["version_id"],
                "expected_deletion_manifest_sha256": payload["deletion_manifest_sha256"],
            },
        )

    assert deleted.status_code == 200
    assert deleted.json()["cleanup_status"] == "deleted"
    assert get_dataset_version_record(settings.workspace_root, version["version_id"]) is None
    assert get_dataset_record(settings.workspace_root, version["dataset_id"]) is None
    assert not raw_path.exists()
    assert all(not path.exists() for path in artifact_paths)


def test_non_last_version_deletion_preserves_shared_raw_upload(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        upload = _upload(client)
        first = _confirm(client, upload["dataset_id"])
        second = _insert_sibling_version(settings, first)
        dataset = get_dataset_record(settings.workspace_root, upload["dataset_id"])
        assert dataset is not None
        raw_path = settings.workspace_root / dataset.stored_path
        preflight = client.get(
            f"/api/v1/dataset-versions/{first['version_id']}/deletion-preflight"
        ).json()
        assert preflight["deletion_scope"] == "version_only"
        assert preflight["counts"]["sibling_version_count"] == 1
        assert preflight["counts"]["raw_upload_file_count"] == 0
        response = client.request(
            "DELETE",
            f"/api/v1/dataset-versions/{first['version_id']}/deletion",
            json={
                "confirmation_version_id": first["version_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )

    assert response.status_code == 200
    assert raw_path.exists()
    assert get_dataset_record(settings.workspace_root, upload["dataset_id"]) is not None
    assert get_dataset_version_record(settings.workspace_root, second["version_id"]) is not None


def test_dataset_version_deletion_blocks_analysis_and_rejects_stale_confirmation(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client)
        ready = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/deletion-preflight"
        ).json()
        metadata = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/metadata",
            json={"user_label": "검토 데이터", "pinned": False},
        )
        assert metadata.status_code == 200
        stale = client.request(
            "DELETE",
            f"/api/v1/dataset-versions/{version['version_id']}/deletion",
            json={
                "confirmation_version_id": version["version_id"],
                "expected_deletion_manifest_sha256": ready["deletion_manifest_sha256"],
            },
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "dataset_version_deletion_confirmation_mismatch"

        now = "2026-07-22T00:00:00Z"
        insert_analysis_run_record(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(uuid4()),
                method_id="eda.descriptive",
                method_version="0.1.0",
                dataset_version_id=version["version_id"],
                config_json="{}",
                status="succeeded",
                result_path=None,
                result_sha256=None,
                stale=False,
                created_at=now,
                updated_at=now,
                completed_at=now,
                app_version="0.1.0",
            ),
        )
        blocked = client.get(f"/api/v1/dataset-versions/{version['version_id']}/deletion-preflight")

    assert blocked.status_code == 200
    payload = blocked.json()
    assert payload["deletion_ready"] is False
    assert payload["counts"]["analysis_run_count"] == 1
    assert "dataset_version_deletion_analysis_dependency" in payload["blockers"]


def test_dataset_version_preflight_rejects_tampered_and_escaped_artifact(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client)
        canonical = get_dataset_artifact_record(
            settings.workspace_root, version["version_id"], "canonical_rows"
        )
        assert canonical is not None
        path = settings.workspace_root / canonical.path
        path.write_bytes(path.read_bytes() + b"tamper")
        tampered = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/deletion-preflight"
        )
        assert tampered.status_code == 409
        assert tampered.json()["error"]["code"] == "dataset_version_artifact_mismatch"

        path.write_bytes(b"restored")
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
            connection.execute(
                "UPDATE dataset_artifacts SET path = ?, sha256 = ?, size_bytes = ? "
                "WHERE artifact_id = ?;",
                (
                    "outside.json",
                    hashlib.sha256(b"restored").hexdigest(),
                    len(b"restored"),
                    canonical.artifact_id,
                ),
            )
        escaped = client.get(f"/api/v1/dataset-versions/{version['version_id']}/deletion-preflight")
    assert escaped.status_code == 409
    assert escaped.json()["error"]["code"] == "dataset_version_path_invalid"


def test_dataset_quarantine_recovery_restores_valid_file(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client)
    artifact = get_dataset_artifact_record(
        settings.workspace_root, version["version_id"], "canonical_rows"
    )
    assert artifact is not None
    original = settings.workspace_root / artifact.path
    owner_token = artifact.artifact_id.replace("-", "")[:12]
    quarantine = original.with_name(f".delete-d-{owner_token}-{'a' * 8}.q")
    os.replace(original, quarantine)

    recovery = recover_dataset_version_quarantine_files(settings.workspace_root)

    assert recovery.restored_file_count == 1
    assert recovery.pending_file_count == 0
    assert original.exists()
    assert not quarantine.exists()


def _upload_and_confirm(client: TestClient) -> dict[str, object]:
    upload = _upload(client)
    return _confirm(client, upload["dataset_id"])


def _upload(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/datasets",
        files={"file": ("sample.csv", b"value,group\n1,A\n2,B\n", "text/csv")},
    )
    assert response.status_code == 201
    return response.json()


def _confirm(
    client: TestClient,
    dataset_id: object,
    *,
    columns: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/datasets/{dataset_id}/confirm-parsing",
        json={
            "parsing": {
                "kind": "delimited_text",
                "encoding": "utf-8",
                "delimiter": ",",
                "quote_char": '"',
                "decimal": ".",
                "thousands": None,
                "has_header": True,
                "header_row": 1,
                "data_start_row": 2,
                "missing_tokens": ["", "NA"],
            },
            "columns": [] if columns is None else columns,
        },
    )
    assert response.status_code == 201
    return response.json()


def _artifacts(settings: Settings, version: dict[str, object]) -> list[dict[str, object]]:
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        rows = connection.execute(
            "SELECT path FROM dataset_artifacts WHERE version_id = ?;",
            (version["version_id"],),
        ).fetchall()
    return [{"path": str(row[0])} for row in rows]


def _insert_sibling_version(
    settings: Settings,
    first: dict[str, object],
) -> dict[str, object]:
    first_id = str(first["version_id"])
    second_id = str(uuid4())
    source = get_dataset_version_record(settings.workspace_root, first_id)
    assert source is not None
    columns = list_dataset_column_records(settings.workspace_root, first_id)
    artifacts = list_dataset_artifact_records(settings.workspace_root, first_id)
    second_artifacts: list[DatasetArtifactRecord] = []
    for artifact in artifacts:
        target_relative = artifact.path.replace(first_id, second_id)
        target = settings.workspace_root / target_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(settings.workspace_root / artifact.path, target)
        second_artifacts.append(
            DatasetArtifactRecord(
                artifact_id=str(uuid4()),
                version_id=second_id,
                kind=artifact.kind,
                path=target_relative,
                sha256=artifact.sha256,
                media_type=artifact.media_type,
                size_bytes=artifact.size_bytes,
                created_at=artifact.created_at,
            )
        )
    insert_dataset_version_record(
        settings.workspace_root,
        DatasetVersionRecord(
            version_id=second_id,
            dataset_id=source.dataset_id,
            version_number=2,
            source_sha256=source.source_sha256,
            parsing_options_json=source.parsing_options_json,
            row_count=source.row_count,
            column_count=source.column_count,
            schema_hash=source.schema_hash,
            created_at="2026-07-22T00:00:01Z",
        ),
        [
            DatasetColumnRecord(
                column_id=str(uuid4()),
                version_id=second_id,
                column_index=column.column_index,
                original_name=column.original_name,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            )
            for column in columns
        ],
        second_artifacts,
    )
    return {"dataset_id": source.dataset_id, "version_id": second_id}
