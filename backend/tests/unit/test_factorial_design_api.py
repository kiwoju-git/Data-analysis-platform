from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_fractional_factorial_api_persists_catalog_and_alias_metadata(tmp_path) -> None:
    factors = [{"name": name, "low": -1, "high": 1} for name in ("A", "B", "C", "D", "E")]
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "five factor half fraction",
                "design_type": "two_level_fractional",
                "fraction_id": "5-factor-half-r5",
                "factors": factors,
                "replicates": 1,
                "center_points": 0,
                "randomize": False,
                "randomization_seed": 7,
                "block_count": 1,
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        restored = client.get(f"/api/v1/doe-designs/{payload['design_id']}")

    assert payload["family"] == "two_level_regular_fractional_factorial"
    assert payload["design_schema_version"] == 2
    assert payload["run_count"] == 16
    assert payload["fractional"]["fraction"] == "1/2"
    assert payload["fractional"]["resolution"] == 5
    assert payload["fractional"]["generators"] == ["E=ABCD"]
    assert payload["fractional"]["defining_relation"] == ["I", "ABCDE"]
    assert payload["fractional"]["principal_fraction"] is True
    assert restored.status_code == 200
    assert restored.json() == payload


def test_fractional_factorial_api_rejects_unvalidated_generator_choice(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "invalid fraction",
                "design_type": "two_level_fractional",
                "fraction_id": "arbitrary-generator",
                "factors": [{"name": name, "low": -1, "high": 1} for name in ("A", "B", "C", "D")],
                "replicates": 1,
                "center_points": 0,
                "randomize": False,
                "randomization_seed": 7,
                "block_count": 1,
            },
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "doe_fractional_catalog_entry_invalid"


def test_general_factorial_api_creates_three_level_design_and_analyzes_response(
    tmp_path,
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        created = client.post(
            "/api/v1/doe-designs/general-factorial",
            json={
                "name": "three by two general factorial",
                "factors": [
                    {"name": "Temperature", "levels": [60, 70, 80], "unit": "C"},
                    {"name": "Material", "levels": ["A", "B"], "unit": None},
                ],
                "replicates": 2,
                "randomize": False,
                "randomization_seed": 11,
                "max_interaction_order": 2,
            },
        )
        assert created.status_code == 201, created.text
        design = created.json()
        values = [
            {
                "run_order": run["run_order"],
                "value": 20
                + 3 * run["level_indices"]["Temperature"]
                + 2 * run["level_indices"]["Material"]
                + 0.1 * run["replicate_index"],
            }
            for run in design["runs"]
        ]
        saved = client.put(
            f"/api/v1/doe-designs/general-factorial/{design['design_id']}/responses",
            json={"response_name": "Yield", "unit": "%", "values": values},
        )
        analysis = client.post(
            f"/api/v1/doe-designs/general-factorial/{design['design_id']}/analyses",
            json={"response_name": "Yield", "max_interaction_order": 2},
        )

    assert design["method_id"] == "doe.general_factorial_design"
    assert design["method_version"] == "0.1.0"
    assert design["run_count"] == 12
    assert saved.status_code == 200, saved.text
    assert analysis.status_code == 201, analysis.text
    result = analysis.json()["result"]
    assert result["coding"]["policy"] == "treatment"
    assert {row["term_id"] for row in result["anova"]["rows"]} == {
        "Temperature",
        "Material",
        "Temperature:Material",
    }


def test_doe_design_deletion_requires_matching_dependency_preflight(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        created = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "deletion lifecycle",
                "factors": [
                    {"name": "A", "low": -1, "high": 1},
                    {"name": "B", "low": -1, "high": 1},
                ],
                "replicates": 1,
                "center_points": 0,
                "randomize": False,
                "randomization_seed": 3,
                "block_count": 1,
            },
        ).json()
        design_id = created["design_id"]
        first_preflight = client.get(f"/api/v1/doe-designs/{design_id}/deletion-preflight").json()
        saved = client.put(
            f"/api/v1/doe-designs/{design_id}/responses",
            json={
                "response_name": "Yield",
                "unit": "%",
                "values": [
                    {"run_order": run["run_order"], "value": 10 + run["run_order"]}
                    for run in created["runs"]
                ],
            },
        )
        assert saved.status_code == 200
        stale_delete = client.request(
            "DELETE",
            f"/api/v1/doe-designs/{design_id}",
            json={
                "confirmation_design_id": design_id,
                "expected_deletion_manifest_sha256": first_preflight["deletion_manifest_sha256"],
            },
        )
        current = client.get(f"/api/v1/doe-designs/{design_id}/deletion-preflight").json()
        deleted = client.request(
            "DELETE",
            f"/api/v1/doe-designs/{design_id}",
            json={
                "confirmation_design_id": design_id,
                "expected_deletion_manifest_sha256": current["deletion_manifest_sha256"],
            },
        )
        restored = client.get(f"/api/v1/doe-designs/{design_id}")

    assert stale_delete.status_code == 409
    assert current["counts"]["response_revision_count"] == 1
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted_counts"]["response_count"] == 4
    assert restored.status_code == 404
