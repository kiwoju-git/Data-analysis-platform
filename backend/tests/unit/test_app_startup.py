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
