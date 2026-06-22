from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_root_response_points_to_api_entrypoints(tmp_path) -> None:
    client = TestClient(create_app(Settings(workspace_root=tmp_path)))

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "datalab-studio-api",
        "version": "0.1.0",
        "api": {
            "base": "/api/v1",
            "health": "/api/v1/health",
            "docs": "/api/docs",
            "openapi": "/api/openapi.json",
        },
    }


def test_health_response_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "datalab-studio-api",
        "version": "0.1.0",
    }


def test_unknown_route_returns_no_traceback_or_path() -> None:
    client = TestClient(create_app())

    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["correlation_id"]
    body_text = response.text.lower()
    assert "traceback" not in body_text
    assert "/mnt/" not in body_text
    assert "c:\\" not in body_text
