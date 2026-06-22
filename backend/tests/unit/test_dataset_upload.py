import hashlib
import io
import zipfile
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import get_dataset_record


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
    assert payload["parsing"]["suggested_encoding"] == "utf-8-sig"
    assert payload["parsing"]["suggested_delimiter"] == ","
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
    assert {warning["code"] for warning in payload["warnings"]} == {
        "nonstandard_text_extension",
    }


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


def _minimal_xlsx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("xl/workbook.xml", "<workbook />")
    return buffer.getvalue()
