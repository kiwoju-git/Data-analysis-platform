import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path


def test_app_startup_initializes_metadata_store(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path / "workspace")

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health")
        store = client.app.state.metadata_store

    assert response.status_code == 200
    assert store.path == metadata_db_path(settings.workspace_root)
    assert store.path.exists()


@pytest.mark.parametrize(
    "origin",
    ["http://127.0.0.1:5173", "http://localhost:5173"],
)
def test_local_frontend_cors_allows_doe_response_put(tmp_path, origin: str) -> None:
    settings = Settings(workspace_root=tmp_path / "workspace")

    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/api/v1/doe-designs/00000000-0000-4000-8000-000000000000/responses",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "PUT" in response.headers["access-control-allow-methods"]
