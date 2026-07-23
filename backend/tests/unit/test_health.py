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


def test_runtime_info_reports_current_contract_without_workspace_details(tmp_path) -> None:
    client = TestClient(create_app(Settings(workspace_root=tmp_path)))

    response = client.get("/api/v1/runtime-info")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "service": "datalab-studio-api",
        "app_version": "0.1.0",
        "api_contract_version": 3,
        "metadata_schema_version": 16,
        "build_commit": "unknown",
        "capabilities": {
            "asset_management": True,
            "dataset_version_metadata": True,
            "dataset_version_deletion": True,
            "dataset_version_archiving": True,
            "dataset_version_cascade_deletion": True,
            "dataset_version_preserve_unverified_cleanup": True,
            "regression_model_metadata": True,
            "regression_model_deletion": True,
            "dedicated_predict": True,
            "dedicated_response_optimizer": True,
            "bayesian_optimization": True,
        },
    }
    body = response.text.lower()
    assert str(tmp_path).lower() not in body
    assert "workspace" not in body


def test_runtime_info_uses_configured_build_commit(tmp_path) -> None:
    client = TestClient(
        create_app(Settings(workspace_root=tmp_path, git_commit="runtime-contract-test"))
    )

    response = client.get("/api/v1/runtime-info")

    assert response.status_code == 200
    assert response.json()["build_commit"] == "runtime-contract-test"


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
