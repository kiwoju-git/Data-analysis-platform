import asyncio
import hashlib
import io
import threading

import httpx
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services import dataset_upload
from app.storage.metadata import get_dataset_record, initialize_metadata_store


def test_upload_limits_and_openapi_preserve_typed_file(tmp_path):
    settings = Settings(workspace_root=tmp_path, max_upload_bytes=20)
    with TestClient(create_app(settings)) as client:
        limits = client.get("/api/v1/datasets/intake-limits").json()
        assert limits["file_bytes"] == limits["paste_utf8_bytes"] == 20
        assert limits["multipart_files"] == 1
        assert limits["json_request_bytes"] == 6 * 20 + 1024 * 1024
        spec = client.get("/api/openapi.json").json()
        body = spec["paths"]["/api/v1/datasets"]["post"]["requestBody"]
        schema = body["content"]["multipart/form-data"]["schema"]["$ref"].split("/")[-1]
        assert spec["components"]["schemas"][schema]["properties"]["file"]["format"] == "binary"
        response = client.post(
            "/api/v1/datasets",
            files=[("file", ("a.csv", b"x\n1\n")), ("file", ("b.csv", b"x\n2\n"))],
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "multipart_limit_exceeded"
        assert not list(tmp_path.glob("workspaces/datasets/**/source.*"))


@pytest.mark.parametrize("data", [{"field": "x" * 9}, {"a": "x", "b": "y"}])
def test_multipart_field_limits(tmp_path, data):
    settings = Settings(
        workspace_root=tmp_path, max_multipart_fields=1, max_multipart_field_bytes=8
    )
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/datasets", data=data, files={"file": ("a.csv", b"x\n1\n")})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "multipart_limit_exceeded"


def test_json_body_limit_is_distinct_from_utf8_file_limit(tmp_path):
    settings = Settings(workspace_root=tmp_path, max_upload_bytes=20, max_request_bytes=40)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/datasets/paste", json={"content": "a" * 40})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "request_body_too_large"


@pytest.mark.parametrize("size,status", [(20, 201), (21, 413)])
def test_file_limit_at_parser_boundary(tmp_path, size, status):
    with TestClient(create_app(Settings(workspace_root=tmp_path, max_upload_bytes=20))) as client:
        response = client.post(
            "/api/v1/datasets", files={"file": ("a.csv", b"x\n" + b"1" * (size - 2))}
        )
        assert response.status_code == status
        if status == 413:
            assert response.json()["error"]["code"] == "file_too_large"
            assert not list(tmp_path.glob("workspaces/datasets/**/source.*"))


def test_truncated_upload_never_calls_storage(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("An incomplete multipart request must not reach storage")

    monkeypatch.setattr(dataset_upload, "_create_dataset_from_upload", forbidden)
    body = (
        b'--b\r\nContent-Disposition: form-data; name="file"; '
        b'filename="a.csv"\r\n\r\nx\n1\r\n--b\r\n'
    )
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/datasets",
            content=body,
            headers={"Content-Type": "multipart/form-data; boundary=b"},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_multipart"


def test_disk_failure_cleans_temp_and_does_not_commit(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    initialize_metadata_store(tmp_path)
    monkeypatch.setattr(
        dataset_upload.os, "fsync", lambda _: (_ for _ in ()).throw(OSError("synthetic disk full"))
    )
    file = UploadFile(io.BytesIO(b"x\n1\n"), filename="a.csv")
    with pytest.raises(OSError, match="synthetic disk full"):
        asyncio.run(dataset_upload.create_dataset_from_upload(file, settings))
    assert not list(tmp_path.glob("workspaces/datasets/**/*.*"))
    file.file.close()


def test_cancellation_waits_for_worker_and_preserves_committed_upload(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    initialize_metadata_store(tmp_path)
    started, release = threading.Event(), threading.Event()
    original = dataset_upload._create_dataset_from_upload
    results = []
    upload = UploadFile(io.BytesIO(b"x\n1\n"), filename="a.csv")

    def blocked(*args):
        started.set()
        assert release.wait(10)
        assert not upload.file.closed
        result = original(*args)
        results.append(result)
        return result

    monkeypatch.setattr(dataset_upload, "_create_dataset_from_upload", blocked)

    async def scenario():
        task = asyncio.create_task(dataset_upload.create_dataset_from_upload(upload, settings))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert len(results) == 1
    record = get_dataset_record(tmp_path, str(results[0].dataset_id))
    assert record is not None
    assert record.sha256 == hashlib.sha256(b"x\n1\n").hexdigest()
    assert (tmp_path / record.stored_path).read_bytes() == b"x\n1\n"
    upload.file.close()


def test_blocked_upload_worker_does_not_block_health(tmp_path, monkeypatch):
    app = create_app(Settings(workspace_root=tmp_path))
    started, release = threading.Event(), threading.Event()
    original = dataset_upload._create_dataset_from_upload

    def blocked(*args):
        started.set()
        assert release.wait(10)
        return original(*args)

    monkeypatch.setattr(dataset_upload, "_create_dataset_from_upload", blocked)

    async def scenario():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://testserver"
            ) as client:
                upload = asyncio.create_task(
                    client.post("/api/v1/datasets", files={"file": ("a.csv", b"x\n1\n")})
                )
                try:
                    assert await asyncio.to_thread(started.wait, 5)
                    health = await asyncio.wait_for(client.get("/api/v1/health"), 2)
                    assert health.status_code == 200
                finally:
                    release.set()
                assert (await upload).status_code == 201

    asyncio.run(scenario())
