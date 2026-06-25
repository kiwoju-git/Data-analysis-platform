import hashlib
import io
import json
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import get_dataset_record, list_dataset_artifact_records


def test_upload_csv_preserves_raw_file_and_records_metadata(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,2\n3,4\n"

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/datasets",
            files={"file": ("sample.csv", content, "text/csv")},
        )

    assert response.status_code == 201
    payload = response.json()
    dataset_id = str(UUID(payload["dataset_id"]))
    assert payload["original_filename"] == "sample.csv"
    assert payload["size_bytes"] == len(content)
    assert payload["sha256"] == hashlib.sha256(content).hexdigest()
    assert payload["detected_format"] == "csv"
    assert payload["parsing"]["suggested_encoding"] == "utf-8"
    assert payload["parsing"]["suggested_delimiter"] == ","
    assert payload["parsing"]["has_header"] is True
    assert payload["parsing"]["header_row"] == 1
    assert payload["parsing"]["data_start_row"] == 2
    assert payload["next_step"] == "confirm_schema"

    record = get_dataset_record(settings.workspace_root, dataset_id)
    assert record is not None
    assert record.sha256 == payload["sha256"]
    assert record.size_bytes == len(content)
    assert record.stored_path.startswith("workspaces/datasets/")
    assert Path(record.stored_path).is_absolute() is False
    assert (settings.workspace_root / record.stored_path).read_bytes() == content


def test_upload_sanitizes_path_traversal_filename(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"a\tb\n1\t2\n"

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/datasets",
            files={"file": ("..\\secret.tsv", content, "text/tab-separated-values")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "secret.tsv"
    assert payload["detected_format"] == "tsv"
    assert payload["parsing"]["suggested_delimiter"] == "\t"
    assert not (settings.workspace_root / "secret.tsv").exists()


def test_upload_rejects_unsupported_file_without_echoing_content(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/datasets",
            files={"file": ("model.pkl", b"SECRET_VALUE", "application/octet-stream")},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_file_type"
    assert "SECRET_VALUE" not in response.text
    assert "model.pkl" not in response.text


def test_upload_rejects_file_over_size_limit(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path, max_upload_bytes=8)

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/datasets",
            files={"file": ("too-large.csv", b"alpha,beta\n1,2\n", "text/csv")},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert not list((settings.workspace_root / "workspaces").glob("**/source.csv"))


def test_upload_txt_returns_delimited_text_warning(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/datasets",
            files={"file": ("bayesian input.txt", b"x,y\n1,2\n", "text/plain")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["detected_format"] == "delimited_text"
    assert payload["parsing"]["suggested_delimiter"] == ","
    assert payload["parsing"]["has_header"] is True
    assert {warning["code"] for warning in payload["warnings"]} == {
        "nonstandard_text_extension",
    }


def test_upload_txt_suggests_no_header_after_preamble(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        "\n"
        "## Background\n"
        "설명 줄은 데이터가 아닙니다.\n"
        "\n"
        "## raw data\n"
        "\n"
        "S-001\t1.5\t2\tN/T\n"
        "S-002\t3.0\t4\t5\n"
    ).encode()

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/datasets",
            files={"file": ("bayesian input.txt", content, "text/plain")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["detected_format"] == "delimited_text"
    assert payload["parsing"]["suggested_delimiter"] == "\t"
    assert payload["parsing"]["has_header"] is False
    assert payload["parsing"]["header_row"] == 1
    assert payload["parsing"]["data_start_row"] == 7


def test_upload_accepts_minimal_xlsx_container(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = _minimal_xlsx_bytes()

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/datasets",
            files={
                "file": (
                    "sample.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["detected_format"] == "xlsx"
    assert payload["parsing"]["kind"] == "xlsx"
    assert payload["parsing"]["xlsx_requires_sheet_selection"] is True
    assert {warning["code"] for warning in payload["warnings"]} == {
        "xlsx_sheet_selection_required",
    }


def test_cp949_text_upload_is_supported(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = "name,value\n홍길동,1\n".encode("cp949")

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/datasets",
            files={"file": ("korean.csv", content, "text/csv")},
        )

    assert response.status_code == 201
    assert "cp949" in response.json()["parsing"]["encoding_candidates"]


def test_create_dataset_from_pasted_text_preserves_raw_and_can_confirm(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = "alpha\tbeta\n1\tx\n2\tN/T\n"

    with TestClient(create_app(settings)) as client:
        paste_response = client.post(
            "/api/v1/datasets/paste",
            json={"content": content, "original_filename": "clipboard.txt"},
        )
        dataset_id = paste_response.json()["dataset_id"]
        confirm_response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json={
                "parsing": {
                    "kind": "delimited_text",
                    "encoding": "utf-8",
                    "delimiter": "\t",
                    "quote_char": '"',
                    "decimal": ".",
                    "thousands": None,
                    "has_header": True,
                    "header_row": 1,
                    "data_start_row": 2,
                    "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
                    "xlsx_sheet_name": None,
                },
                "columns": [],
            },
        )
        preview_response = client.get(
            f"/api/v1/dataset-versions/{confirm_response.json()['version_id']}/rows",
        )

    assert paste_response.status_code == 201
    paste_payload = paste_response.json()
    assert paste_payload["original_filename"] == "clipboard.txt"
    assert paste_payload["detected_format"] == "delimited_text"
    assert paste_payload["sha256"] == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert paste_payload["parsing"]["suggested_delimiter"] == "\t"

    record = get_dataset_record(settings.workspace_root, dataset_id)
    assert record is not None
    assert (settings.workspace_root / record.stored_path).read_text(encoding="utf-8") == content

    assert confirm_response.status_code == 201
    assert confirm_response.json()["row_count"] == 2
    assert preview_response.status_code == 200
    assert preview_response.json()["rows"] == [
        {"row_index": 0, "values": ["1", "x"]},
        {"row_index": 1, "values": ["2", None]},
    ]


def test_confirm_parsing_creates_immutable_dataset_version_and_columns(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,2.5\n3,4.25\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("sample.csv", content, "text/csv")},
        )
        dataset_id = upload_response.json()["dataset_id"]

        confirm_response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json=_confirmation_body(
                columns=[
                    {
                        "column_index": 0,
                        "measurement_level": "continuous",
                        "unit": "kg",
                    },
                ],
            ),
        )
        repeat_response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json=_confirmation_body(),
        )
        versions_response = client.get(f"/api/v1/datasets/{dataset_id}/versions")

    assert confirm_response.status_code == 201
    payload = confirm_response.json()
    version_id = payload["version_id"]
    assert payload["dataset_id"] == dataset_id
    assert payload["version_number"] == 1
    assert payload["source_sha256"] == hashlib.sha256(content).hexdigest()
    assert payload["row_count"] == 2
    assert payload["column_count"] == 2
    assert len(payload["schema_hash"]) == 64
    assert payload["parsing"]["encoding"] == "utf-8"
    assert payload["parsing"]["delimiter"] == ","
    canonical_artifact = payload["canonical_artifact"]
    assert canonical_artifact["kind"] == "canonical_rows"
    assert Path(canonical_artifact["path"]).is_absolute() is False
    canonical_path = settings.workspace_root / canonical_artifact["path"]
    assert canonical_path.exists()
    assert canonical_artifact["sha256"] == hashlib.sha256(canonical_path.read_bytes()).hexdigest()
    canonical_rows = [
        json.loads(line) for line in canonical_path.read_text(encoding="utf-8").splitlines()
    ]
    assert canonical_rows == [
        {"row_index": 0, "values": ["1", "2.5"]},
        {"row_index": 1, "values": ["3", "4.25"]},
    ]
    artifact_records = list_dataset_artifact_records(settings.workspace_root, version_id)
    assert {artifact.kind for artifact in artifact_records} == {
        "canonical_manifest",
        "canonical_rows",
    }
    manifest_record = next(
        artifact for artifact in artifact_records if artifact.kind == "canonical_manifest"
    )
    manifest_payload = json.loads((settings.workspace_root / manifest_record.path).read_text())
    assert manifest_payload["artifact_format"] == "datalab.canonical.rows-jsonl"
    assert manifest_payload["data"]["sha256"] == canonical_artifact["sha256"]
    assert manifest_payload["row_count"] == 2
    assert payload["columns"][0]["original_name"] == "alpha"
    assert payload["columns"][0]["display_name"] == "alpha"
    assert payload["columns"][0]["data_type"] == "integer"
    assert payload["columns"][0]["measurement_level"] == "continuous"
    assert payload["columns"][0]["unit"] == "kg"
    assert payload["columns"][1]["original_name"] == "beta"
    assert payload["columns"][1]["data_type"] == "decimal"
    assert payload["columns"][1]["measurement_level"] == "unknown"

    assert repeat_response.status_code == 409
    assert repeat_response.json()["error"]["code"] == "dataset_already_confirmed"
    assert versions_response.status_code == 200
    assert versions_response.json()["versions"] == [
        {
            "version_id": version_id,
            "dataset_id": dataset_id,
            "version_number": 1,
            "row_count": 2,
            "column_count": 2,
            "schema_hash": payload["schema_hash"],
            "created_at": payload["created_at"],
        },
    ]

    with TestClient(create_app(settings)) as client:
        version_response = client.get(f"/api/v1/dataset-versions/{version_id}")

    assert version_response.status_code == 200
    assert version_response.json() == payload


def test_confirm_parsing_rejects_raw_upload_integrity_mismatch(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,2\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("sample.csv", content, "text/csv")},
        )
        dataset_id = upload_response.json()["dataset_id"]
        dataset_record = get_dataset_record(settings.workspace_root, dataset_id)
        assert dataset_record is not None
        tampered = b"alpha,beta\n9,9\n"
        assert len(tampered) == len(content)
        (settings.workspace_root / dataset_record.stored_path).write_bytes(tampered)

        confirm_response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json=_confirmation_body(),
        )
        versions_response = client.get(f"/api/v1/datasets/{dataset_id}/versions")

    assert confirm_response.status_code == 409
    assert confirm_response.json()["error"]["code"] == "source_file_integrity_mismatch"
    assert versions_response.status_code == 200
    assert versions_response.json()["versions"] == []
    assert not list(settings.workspace_root.glob("workspaces/datasets/*/versions/*/canonical.*"))


def test_confirm_parsing_preserves_duplicate_and_empty_header_names(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,,alpha\n1,2,3\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("duplicate.csv", content, "text/csv")},
        )
        dataset_id = upload_response.json()["dataset_id"]

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json=_confirmation_body(),
        )

    assert response.status_code == 201
    columns = response.json()["columns"]
    assert [column["original_name"] for column in columns] == ["alpha", "", "alpha"]
    assert [column["display_name"] for column in columns] == ["alpha", "column_2", "alpha_2"]


def test_confirm_parsing_supports_no_header_data_after_preamble(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        "\n"
        "## Background\n"
        "설명 줄은 데이터가 아닙니다.\n"
        "\n"
        "## raw data\n"
        "\n"
        "S-001\t1.5\t2\tN/T\n"
        "S-002\t3.0\t4\t5\n"
    ).encode()

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("bayesian input.txt", content, "text/plain")},
        )
        parsing = upload_response.json()["parsing"]
        dataset_id = upload_response.json()["dataset_id"]

        confirm_response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json=_confirmation_body(
                delimiter="\t",
                has_header=False,
                data_start_row=parsing["data_start_row"],
            ),
        )
        rows_response = client.get(
            f"/api/v1/dataset-versions/{confirm_response.json()['version_id']}/rows",
            params={"offset": 0, "limit": 2},
        )

    assert confirm_response.status_code == 201
    payload = confirm_response.json()
    assert payload["row_count"] == 2
    assert payload["column_count"] == 4
    assert payload["parsing"]["has_header"] is False
    assert payload["parsing"]["data_start_row"] == 7
    assert [column["original_name"] for column in payload["columns"]] == [
        "column_1",
        "column_2",
        "column_3",
        "column_4",
    ]
    assert [column["data_type"] for column in payload["columns"]] == [
        "text",
        "decimal",
        "integer",
        "integer",
    ]

    assert rows_response.status_code == 200
    assert rows_response.json()["rows"] == [
        {"row_index": 0, "values": ["S-001", "1.5", "2", None]},
        {"row_index": 1, "values": ["S-002", "3.0", "4", "5"]},
    ]


def test_confirm_parsing_supports_cp949_headers_without_logging_values(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = "이름,값\n홍길동,1\n".encode("cp949")

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("korean.csv", content, "text/csv")},
        )
        dataset_id = upload_response.json()["dataset_id"]

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json=_confirmation_body(encoding="cp949"),
        )

    assert response.status_code == 201
    assert [column["original_name"] for column in response.json()["columns"]] == ["이름", "값"]
    assert "홍길동" not in response.text


def test_confirm_parsing_rejects_invalid_options_without_echoing_values(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\nSECRET_VALUE,2\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("sample.csv", content, "text/csv")},
        )
        dataset_id = upload_response.json()["dataset_id"]

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json=_confirmation_body(delimiter="||"),
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_delimiter"
    assert "SECRET_VALUE" not in response.text


def test_confirm_parsing_creates_xlsx_dataset_version_and_preview(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = _xlsx_workbook_bytes()

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={
                "file": (
                    "sample.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )
        dataset_id = upload_response.json()["dataset_id"]

        confirm_response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json={
                "parsing": {
                    "kind": "xlsx",
                    "has_header": True,
                    "header_row": 1,
                    "data_start_row": 2,
                    "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
                    "xlsx_sheet_name": None,
                },
            },
        )
        preview_response = client.get(
            f"/api/v1/dataset-versions/{confirm_response.json()['version_id']}/rows",
        )

    assert confirm_response.status_code == 201
    payload = confirm_response.json()
    assert payload["dataset_id"] == dataset_id
    assert payload["source_sha256"] == hashlib.sha256(content).hexdigest()
    assert payload["row_count"] == 2
    assert payload["column_count"] == 3
    assert [column["display_name"] for column in payload["columns"]] == ["alpha", "beta", "flag"]
    assert [column["data_type"] for column in payload["columns"]] == [
        "integer",
        "text",
        "boolean",
    ]
    canonical_path = settings.workspace_root / payload["canonical_artifact"]["path"]
    canonical_rows = [
        json.loads(line) for line in canonical_path.read_text(encoding="utf-8").splitlines()
    ]
    assert canonical_rows == [
        {"row_index": 0, "values": ["1", "x", "TRUE"]},
        {"row_index": 1, "values": ["2", None, "FALSE"]},
    ]
    assert preview_response.status_code == 200
    assert preview_response.json()["rows"] == [
        {"row_index": 0, "values": ["1", "x", "TRUE"]},
        {"row_index": 1, "values": ["2", None, "FALSE"]},
    ]


def test_confirm_parsing_rejects_unknown_xlsx_sheet(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={
                "file": (
                    "sample.xlsx",
                    _xlsx_workbook_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )
        dataset_id = upload_response.json()["dataset_id"]

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
            json={
                "parsing": {
                    "kind": "xlsx",
                    "has_header": True,
                    "header_row": 1,
                    "data_start_row": 2,
                    "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
                    "xlsx_sheet_name": "Missing Sheet",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "xlsx_sheet_not_found"


def test_dataset_schema_can_be_read_and_updated_without_changing_original_names(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,2\n3,4\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, content)
        version_id = version["version_id"]
        first_column = version["columns"][0]

        schema_response = client.get(f"/api/v1/dataset-versions/{version_id}/schema")
        update_response = client.patch(
            f"/api/v1/dataset-versions/{version_id}/schema",
            json={
                "columns": [
                    {
                        "column_id": first_column["column_id"],
                        "display_name": "측정값",
                        "measurement_level": "continuous",
                        "role": "feature",
                        "unit": "kg",
                    },
                ],
            },
        )
        version_response = client.get(f"/api/v1/dataset-versions/{version_id}")

    assert schema_response.status_code == 200
    assert schema_response.json()["schema_hash"] == version["schema_hash"]

    assert update_response.status_code == 200
    updated_schema = update_response.json()
    assert updated_schema["schema_hash"] != version["schema_hash"]
    assert updated_schema["columns"][0]["original_name"] == "alpha"
    assert updated_schema["columns"][0]["display_name"] == "측정값"
    assert updated_schema["columns"][0]["data_type"] == "integer"
    assert updated_schema["columns"][0]["measurement_level"] == "continuous"
    assert updated_schema["columns"][0]["role"] == "feature"
    assert updated_schema["columns"][0]["unit"] == "kg"

    assert version_response.status_code == 200
    assert version_response.json()["schema_hash"] == updated_schema["schema_hash"]
    assert version_response.json()["columns"][0] == updated_schema["columns"][0]


def test_dataset_schema_update_rejects_duplicate_display_names_without_echoing_values(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\nSECRET_VALUE,2\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, content)
        columns = version["columns"]

        response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema",
            json={
                "columns": [
                    {
                        "column_id": columns[0]["column_id"],
                        "display_name": "same",
                        "measurement_level": "continuous",
                        "role": "feature",
                        "unit": None,
                    },
                    {
                        "column_id": columns[1]["column_id"],
                        "display_name": "same",
                        "measurement_level": "continuous",
                        "role": "feature",
                        "unit": None,
                    },
                ],
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "duplicate_column_display_name"
    assert "SECRET_VALUE" not in response.text


def test_dataset_schema_update_rejects_unknown_column(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, b"alpha,beta\n1,2\n")

        response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema",
            json={
                "columns": [
                    {
                        "column_id": str(uuid4()),
                        "display_name": "missing",
                        "measurement_level": "continuous",
                        "role": "feature",
                        "unit": None,
                    },
                ],
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "column_update_not_found"


def test_dataset_rows_preview_is_paginated_and_uses_confirmed_schema(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,\n2,SECRET_VALUE\n3,4\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, content)
        response = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/rows",
            params={"offset": 0, "limit": 2},
        )
        second_page_response = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/rows",
            params={"offset": 2, "limit": 2},
        )
        invalid_limit_response = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/rows",
            params={"offset": 0, "limit": 101},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["offset"] == 0
    assert payload["limit"] == 2
    assert payload["total_rows"] == 3
    assert payload["returned_rows"] == 2
    assert [column["display_name"] for column in payload["columns"]] == ["alpha", "beta"]
    assert payload["rows"] == [
        {"row_index": 0, "values": ["1", None]},
        {"row_index": 1, "values": ["2", "SECRET_VALUE"]},
    ]

    assert second_page_response.status_code == 200
    assert second_page_response.json()["rows"] == [
        {"row_index": 2, "values": ["3", "4"]},
    ]

    assert invalid_limit_response.status_code == 422
    assert invalid_limit_response.json()["error"]["code"] == "validation_error"


def test_dataset_rows_preview_reads_canonical_artifact_after_raw_upload_changes(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,x\n2,y\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, content)
        dataset_record = get_dataset_record(settings.workspace_root, version["dataset_id"])
        assert dataset_record is not None
        (settings.workspace_root / dataset_record.stored_path).write_bytes(
            b"alpha,beta\n999,changed\n999,changed\n",
        )

        response = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/rows",
            params={"offset": 0, "limit": 10},
        )

    assert response.status_code == 200
    assert response.json()["rows"] == [
        {"row_index": 0, "values": ["1", "x"]},
        {"row_index": 1, "values": ["2", "y"]},
    ]


def test_dataset_profile_reports_quality_without_echoing_cell_values(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"id,value,group\nA1,1,same\nA2,,same\nA3,SECRET_VALUE,same\nA4,4,same\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("sample.csv", content, "text/csv")},
        )
        assert upload_response.status_code == 201
        confirm_response = client.post(
            f"/api/v1/datasets/{upload_response.json()['dataset_id']}/confirm-parsing",
            json=_confirmation_body(
                columns=[
                    {
                        "column_index": 1,
                        "data_type": "decimal",
                        "measurement_level": "continuous",
                    },
                ],
            ),
        )
        assert confirm_response.status_code == 201

        response = client.get(
            f"/api/v1/dataset-versions/{confirm_response.json()['version_id']}/profile",
        )

    assert response.status_code == 200
    assert "SECRET_VALUE" not in response.text
    payload = response.json()
    assert payload["profile_schema_version"] == 4
    assert payload["row_count"] == 4
    assert payload["column_count"] == 3
    assert payload["schema_hash"] == confirm_response.json()["schema_hash"]
    assert payload["unique_count_limit"] == 1000

    profiles = {column["display_name"]: column for column in payload["columns"]}
    assert profiles["id"]["n_missing"] == 0
    assert profiles["id"]["unique_count"] == 4
    assert {warning["code"] for warning in profiles["id"]["warnings"]} == {
        "possible_identifier",
    }

    assert profiles["value"]["n_total"] == 4
    assert profiles["value"]["n_present"] == 3
    assert profiles["value"]["n_missing"] == 1
    assert profiles["value"]["missing_rate"] == 0.25
    assert profiles["value"]["n_numeric"] == 2
    assert profiles["value"]["n_non_numeric"] == 1
    assert profiles["value"]["numeric_min"] == 1.0
    assert profiles["value"]["numeric_max"] == 4.0
    assert profiles["value"]["numeric_mean"] == 2.5
    assert {warning["code"] for warning in profiles["value"]["warnings"]} == {
        "non_numeric_values_in_numeric_column",
    }

    assert profiles["group"]["constant"] is True
    assert profiles["group"]["unique_count"] == 1
    assert {warning["code"] for warning in profiles["group"]["warnings"]} == {
        "constant_column",
    }


def test_dataset_profile_reports_canonical_preflight_and_duplicate_rows(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,x\n1,x\n2,y\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, content)
        response = client.get(f"/api/v1/dataset-versions/{version['version_id']}/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_schema_version"] == 4
    assert payload["canonical_artifact"] == version["canonical_artifact"]
    assert payload["preflight"]["estimated_memory_bytes"] > 0
    assert payload["preflight"]["duplicate_row_count"] == 1
    assert payload["preflight"]["duplicate_row_count_capped"] is False
    assert payload["preflight"]["duplicate_row_check_limit"] == 100000
    assert {warning["code"] for warning in payload["warnings"]} == {
        "duplicate_rows_detected",
    }


def test_dataset_profile_reports_datetime_preflight_without_raw_samples(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"event_date,when,mixed,note\n"
        b"2024-01-01,2024-01-01T09:00:00Z,2024-01-01,SECRET_NOTE\n"
        b"2024-01-02,2024-01-02T18:30:00+09:00,not-a-date,plain\n"
    )

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(
            client,
            content,
            columns=[
                {
                    "column_index": 0,
                    "data_type": "datetime",
                    "measurement_level": "datetime",
                    "role": "time",
                },
                {
                    "column_index": 1,
                    "data_type": "datetime",
                    "measurement_level": "datetime",
                    "role": "time",
                },
            ],
        )
        response = client.get(f"/api/v1/dataset-versions/{version['version_id']}/profile")

    assert response.status_code == 200
    assert "SECRET_NOTE" not in response.text
    payload = response.json()
    assert payload["profile_schema_version"] == 4
    profiles = {column["display_name"]: column for column in payload["columns"]}

    event_date_profile = profiles["event_date"]["datetime_profile"]
    assert event_date_profile == {
        "n_datetime": 2,
        "n_non_datetime": 0,
        "datetime_min": "2024-01-01T00:00:00",
        "datetime_max": "2024-01-02T00:00:00",
        "timezone_aware_count": 0,
        "timezone_naive_count": 2,
        "mixed_timezone_awareness": False,
        "format_candidates": [{"format": "YYYY-MM-DD", "n_matched": 2}],
    }

    when_profile = profiles["when"]["datetime_profile"]
    assert when_profile["n_datetime"] == 2
    assert when_profile["n_non_datetime"] == 0
    assert when_profile["timezone_aware_count"] == 2
    assert when_profile["timezone_naive_count"] == 0
    assert when_profile["format_candidates"] == [{"format": "ISO 8601", "n_matched": 2}]

    mixed_profile = profiles["mixed"]["datetime_profile"]
    assert mixed_profile["n_datetime"] == 1
    assert mixed_profile["n_non_datetime"] == 1
    assert mixed_profile["format_candidates"] == [{"format": "YYYY-MM-DD", "n_matched": 1}]

    artifact = payload["profile_artifact"]
    artifact_payload = json.loads(
        (settings.workspace_root / artifact["path"]).read_text(encoding="utf-8"),
    )
    artifact_profiles = {
        column["display_name"]: column for column in artifact_payload["profile"]["columns"]
    }
    assert artifact_payload["profile"]["profile_schema_version"] == 4
    assert artifact_profiles["event_date"]["datetime_profile"] == event_date_profile
    assert "SECRET_NOTE" not in json.dumps(artifact_payload, ensure_ascii=False)


def test_dataset_profile_persists_profile_artifact_without_raw_values(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,SECRET_VALUE\n2,x\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, content)
        first_response = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/profile",
        )
        assert first_response.status_code == 200
        assert "SECRET_VALUE" not in first_response.text
        first_payload = first_response.json()
        first_artifact = first_payload["profile_artifact"]
        assert first_artifact["kind"] == "profile_summary"
        assert first_artifact["media_type"] == "application/json"
        assert Path(first_artifact["path"]).is_absolute() is False

        first_artifact_path = settings.workspace_root / first_artifact["path"]
        first_artifact_bytes = first_artifact_path.read_bytes()
        first_artifact_text = first_artifact_bytes.decode("utf-8")
        second_response = client.get(
            f"/api/v1/dataset-versions/{version['version_id']}/profile",
        )

    assert second_response.status_code == 200
    assert "SECRET_VALUE" not in first_artifact_text
    assert first_artifact["sha256"] == hashlib.sha256(first_artifact_bytes).hexdigest()
    assert first_artifact["size_bytes"] == len(first_artifact_bytes)

    first_artifact_payload = json.loads(first_artifact_text)
    assert first_artifact_payload["artifact_schema_version"] == 1
    assert first_artifact_payload["artifact_kind"] == "profile_summary"
    assert first_artifact_payload["profile_schema_version"] == 4
    assert first_artifact_payload["schema_hash"] == version["schema_hash"]
    assert (
        first_artifact_payload["source_canonical_artifact_sha256"]
        == version["canonical_artifact"]["sha256"]
    )
    assert first_artifact_payload["source_canonical_artifact"] == {
        "kind": "canonical_rows",
        "sha256": version["canonical_artifact"]["sha256"],
        "media_type": "application/x-ndjson",
        "size_bytes": version["canonical_artifact"]["size_bytes"],
    }
    assert "profile_artifact" not in first_artifact_payload["profile"]
    assert first_artifact_payload["profile"]["canonical_artifact"] == version["canonical_artifact"]

    second_artifact = second_response.json()["profile_artifact"]
    assert second_artifact == first_artifact
    artifact_records = list_dataset_artifact_records(
        settings.workspace_root,
        version["version_id"],
    )
    profile_records = [
        artifact for artifact in artifact_records if artifact.kind == "profile_summary"
    ]
    assert len(profile_records) == 1
    assert profile_records[0].path == second_artifact["path"]
    assert profile_records[0].sha256 == second_artifact["sha256"]


def test_dataset_profile_reads_canonical_artifact_after_raw_upload_changes(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,x\n2,y\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, content)
        dataset_record = get_dataset_record(settings.workspace_root, version["dataset_id"])
        assert dataset_record is not None
        (settings.workspace_root / dataset_record.stored_path).write_bytes(
            b"alpha,beta\n999,z\n999,z\n",
        )

        response = client.get(f"/api/v1/dataset-versions/{version['version_id']}/profile")

    assert response.status_code == 200
    payload = response.json()
    profiles = {column["display_name"]: column for column in payload["columns"]}
    assert profiles["alpha"]["n_total"] == 2
    assert profiles["alpha"]["numeric_mean"] == 1.5
    assert profiles["alpha"]["numeric_max"] == 2.0


def test_dataset_profile_rejects_corrupt_canonical_artifact_without_raw_fallback(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,x\n2,y\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_and_confirm(client, content)
        canonical_path = settings.workspace_root / version["canonical_artifact"]["path"]
        canonical_path.write_text(
            '{"row_index":0,"values":["999","SECRET_VALUE"]}\n',
            encoding="utf-8",
        )

        response = client.get(f"/api/v1/dataset-versions/{version['version_id']}/profile")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "canonical_artifact_invalid"
    assert "SECRET_VALUE" not in error["message"]
    assert "999" not in error["message"]
    assert error["developer_detail"] is None


def _minimal_xlsx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("xl/workbook.xml", "<workbook />")
    return buffer.getvalue()


def _xlsx_workbook_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "\n".join(
                [
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
                    '<Default Extension="rels" '
                    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                    '<Default Extension="xml" ContentType="application/xml"/>',
                    '<Override PartName="/xl/workbook.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.'
                    'spreadsheetml.sheet.main+xml"/>',
                    '<Override PartName="/xl/worksheets/sheet1.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.'
                    'spreadsheetml.worksheet+xml"/>',
                    "</Types>",
                ],
            ),
        )
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets>
                <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
              </sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
                Target="worksheets/sheet1.xml"/>
            </Relationships>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>alpha</t></is></c>
                  <c r="B1" t="inlineStr"><is><t>beta</t></is></c>
                  <c r="C1" t="inlineStr"><is><t>flag</t></is></c>
                </row>
                <row r="2">
                  <c r="A2"><v>1</v></c>
                  <c r="B2" t="inlineStr"><is><t>x</t></is></c>
                  <c r="C2" t="b"><v>1</v></c>
                </row>
                <row r="3">
                  <c r="A3"><v>2</v></c>
                  <c r="B3" t="inlineStr"><is><t>N/T</t></is></c>
                  <c r="C3" t="b"><v>0</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )
    return buffer.getvalue()


def _upload_and_confirm(
    client: TestClient,
    content: bytes,
    *,
    columns: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    upload_response = client.post(
        "/api/v1/datasets",
        files={"file": ("sample.csv", content, "text/csv")},
    )
    assert upload_response.status_code == 201
    confirm_response = client.post(
        f"/api/v1/datasets/{upload_response.json()['dataset_id']}/confirm-parsing",
        json=_confirmation_body(columns=columns),
    )
    assert confirm_response.status_code == 201
    return confirm_response.json()


def _confirmation_body(
    *,
    encoding: str = "utf-8",
    delimiter: str = ",",
    has_header: bool = True,
    header_row: int = 1,
    data_start_row: int | None = None,
    columns: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if data_start_row is None:
        data_start_row = header_row + 1 if has_header else header_row
    return {
        "parsing": {
            "kind": "delimited_text",
            "encoding": encoding,
            "delimiter": delimiter,
            "quote_char": '"',
            "decimal": ".",
            "thousands": None,
            "has_header": has_header,
            "header_row": header_row,
            "data_start_row": data_start_row,
            "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
        },
        "columns": [] if columns is None else columns,
    }
