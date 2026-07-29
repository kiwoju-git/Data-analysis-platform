import json

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.dataset_cell_corrections import (
    CELL_CORRECTION_PENDING_NAME,
    recover_dataset_cell_correction_files,
)
from app.storage.metadata import (
    get_dataset_version_lineage_record,
    list_dataset_artifact_records,
)


def _confirmation_body() -> dict:
    return {
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
            "xlsx_sheet_name": None,
        },
        "columns": [],
    }


def _create_parent(client: TestClient) -> dict:
    upload = client.post(
        "/api/v1/datasets",
        files={"file": ("sample.csv", b"number,text\n1,SECRET_OLD\n2,\n", "text/csv")},
    )
    assert upload.status_code == 201
    confirmed = client.post(
        f"/api/v1/datasets/{upload.json()['dataset_id']}/confirm-parsing",
        json=_confirmation_body(),
    )
    assert confirmed.status_code == 201
    return confirmed.json()


def _request(parent: dict, *, column_index: int, operation: str, value: str | None) -> dict:
    return {
        "confirmation_parent_version_id": parent["version_id"],
        "expected_parent_schema_hash": parent["schema_hash"],
        "expected_parent_canonical_sha256": parent["canonical_artifact"]["sha256"],
        "edits": [
            {
                "row_index": 0,
                "column_id": parent["columns"][column_index]["column_id"],
                "operation": operation,
                "value": value,
            }
        ],
    }


def test_cell_correction_creates_immutable_child_and_lineage(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        parent = _create_parent(client)
        parent_path = tmp_path / parent["canonical_artifact"]["path"]
        parent_bytes = parent_path.read_bytes()
        response = client.post(
            f"/api/v1/dataset-versions/{parent['version_id']}/cell-corrections",
            json=_request(
                parent,
                column_index=1,
                operation="set_value",
                value="SECRET_NEW",
            ),
        )
        assert response.status_code == 201
        child = response.json()["new_version"]
        child_preview = client.get(f"/api/v1/dataset-versions/{child['version_id']}/rows")
        parent_preview = client.get(f"/api/v1/dataset-versions/{parent['version_id']}/rows")
        parent_preflight = client.get(
            f"/api/v1/dataset-versions/{parent['version_id']}/deletion-preflight"
        )

    assert parent_path.read_bytes() == parent_bytes
    assert child["version_number"] == 2
    assert child["parent_version_id"] == parent["version_id"]
    assert child["lineage_operation_kind"] == "cell_correction"
    assert child_preview.json()["rows"][0]["values"][1] == "SECRET_NEW"
    assert parent_preview.json()["rows"][0]["values"][1] == "SECRET_OLD"
    assert parent_preflight.status_code == 200
    assert parent_preflight.json()["counts"]["child_version_count"] == 1
    assert (
        "dataset_version_deletion_child_version_dependency" in (parent_preflight.json()["blockers"])
    )

    lineage = get_dataset_version_lineage_record(
        settings.workspace_root,
        child["version_id"],
    )
    assert lineage is not None
    assert lineage.parent_version_id == parent["version_id"]
    artifacts = list_dataset_artifact_records(settings.workspace_root, child["version_id"])
    manifest = next(item for item in artifacts if item.kind == "dataset_cell_correction_manifest")
    manifest_text = (tmp_path / manifest.path).read_text(encoding="utf-8")
    assert "SECRET_OLD" not in manifest_text
    assert "SECRET_NEW" not in manifest_text
    assert json.loads(manifest_text)["affected_cell_count"] == 1


def test_cell_correction_distinguishes_empty_missing_invalid_and_no_change(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        parent = _create_parent(client)
        invalid = client.post(
            f"/api/v1/dataset-versions/{parent['version_id']}/cell-corrections",
            json=_request(parent, column_index=0, operation="set_value", value="not-number"),
        )
        unchanged = client.post(
            f"/api/v1/dataset-versions/{parent['version_id']}/cell-corrections",
            json=_request(parent, column_index=0, operation="set_value", value="1"),
        )
        empty = client.post(
            f"/api/v1/dataset-versions/{parent['version_id']}/cell-corrections",
            json=_request(parent, column_index=1, operation="set_value", value=""),
        )
        missing = client.post(
            f"/api/v1/dataset-versions/{parent['version_id']}/cell-corrections",
            json=_request(parent, column_index=1, operation="set_missing", value=None),
        )

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "dataset_cell_correction_value_invalid"
    assert unchanged.status_code == 422
    assert unchanged.json()["error"]["code"] == "dataset_cell_correction_no_change"
    assert empty.status_code == 201
    assert missing.status_code == 201
    assert (
        empty.json()["new_version"]["canonical_artifact"]["sha256"]
        != (missing.json()["new_version"]["canonical_artifact"]["sha256"])
    )


def test_cell_correction_startup_recovery_removes_only_unregistered_owned_files(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        parent = _create_parent(client)
        created = client.post(
            f"/api/v1/dataset-versions/{parent['version_id']}/cell-corrections",
            json=_request(parent, column_index=1, operation="set_value", value="changed"),
        ).json()["new_version"]

    registered_dir = tmp_path / "workspaces" / "datasets" / created["dataset_id"] / "versions"
    registered_marker = registered_dir / created["version_id"] / CELL_CORRECTION_PENDING_NAME
    registered_marker.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": created["dataset_id"],
                "child_version_id": created["version_id"],
            }
        ),
        encoding="utf-8",
    )

    orphan_id = "22222222-2222-4222-8222-222222222222"
    orphan_dir = registered_dir / orphan_id
    orphan_dir.mkdir(parents=True)
    for name in (
        "canonical.rows.jsonl",
        "canonical.manifest.json",
        "cell-correction.manifest.json",
    ):
        (orphan_dir / name).write_text("owned", encoding="utf-8")
    unrelated = orphan_dir / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")
    orphan_marker = orphan_dir / CELL_CORRECTION_PENDING_NAME
    orphan_marker.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": created["dataset_id"],
                "child_version_id": orphan_id,
            }
        ),
        encoding="utf-8",
    )

    recovery = recover_dataset_cell_correction_files(settings.workspace_root)

    assert recovery.retained == 1
    assert recovery.deleted == 1
    assert recovery.pending == 0
    assert not registered_marker.exists()
    assert not orphan_marker.exists()
    assert unrelated.read_text(encoding="utf-8") == "keep"
