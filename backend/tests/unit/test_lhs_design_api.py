from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _request() -> dict:
    return {
        "name": "three-factor LHS",
        "factors": [
            {"name": "temperature", "low": 20, "high": 80, "unit": "C"},
            {"name": "time", "low": 1, "high": 5, "unit": "min"},
            {"name": "ratio", "low": 0.1, "high": 0.9, "unit": None},
        ],
        "run_count": 10,
        "seed": 17,
        "randomize_run_order": True,
        "run_order_seed": 29,
        "optimization": "random_cd",
    }


def test_lhs_design_create_restore_response_revision_and_csv(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        created_response = client.post("/api/v1/doe-designs/latin-hypercube", json=_request())
        assert created_response.status_code == 201
        created = created_response.json()
        restored_response = client.get(
            f"/api/v1/doe-designs/latin-hypercube/{created['design_id']}"
        )
        values = [
            {"run_order": run["run_order"], "value": float(run["run_order"])}
            for run in created["runs"]
        ]
        saved_response = client.put(
            f"/api/v1/doe-designs/latin-hypercube/{created['design_id']}/responses",
            json={"response_name": "yield", "unit": "%", "values": values},
        )
        csv_response = client.get(
            f"/api/v1/doe-designs/latin-hypercube/{created['design_id']}/export.csv"
        )

    assert restored_response.status_code == 200
    assert restored_response.json() == created
    assert created["method_id"] == "doe.latin_hypercube"
    assert created["method_version"] == "0.1.0"
    assert created["quality"]["strata_valid"] is True
    assert len(created["runs"]) == 10
    assert saved_response.status_code == 200
    assert saved_response.json()["responses"][0]["response_revision_number"] == 1
    assert csv_response.status_code == 200
    assert csv_response.content.startswith(b"\xef\xbb\xbf")
    assert b"temperature normalized" in csv_response.content
    assert str(tmp_path).encode() not in csv_response.content


def test_lhs_design_rejects_invalid_bounds_and_extra_constraints(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    invalid = _request()
    invalid["factors"][0]["high"] = 20
    unsupported = _request() | {"constraints": []}
    with TestClient(create_app(settings)) as client:
        invalid_response = client.post(
            "/api/v1/doe-designs/latin-hypercube",
            json=invalid,
        )
        unsupported_response = client.post(
            "/api/v1/doe-designs/latin-hypercube",
            json=unsupported,
        )

    assert invalid_response.status_code == 422
    assert unsupported_response.status_code == 422
