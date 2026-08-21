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


def test_two_level_factorial_supports_categorical_pseudo_centers(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "mixed two-level factorial",
                "factors": [
                    {
                        "factor_kind": "numeric",
                        "name": "Temperature",
                        "low": 60,
                        "high": 80,
                        "unit": "C",
                    },
                    {
                        "factor_kind": "categorical",
                        "name": "Material",
                        "low_label": "A",
                        "high_label": "B",
                    },
                ],
                "replicates": 1,
                "center_points": 1,
                "randomize": False,
                "randomization_seed": 17,
                "block_count": 1,
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        restored = client.get(f"/api/v1/doe-designs/{payload['design_id']}")

    assert payload["method_version"] == "0.6.0"
    assert payload["design_schema_version"] == 2
    assert payload["run_count"] == 6
    assert payload["factors"][0]["factor_kind"] == "numeric"
    assert payload["factors"][1] == {
        "factor_kind": "categorical",
        "name": "Material",
        "low_label": "A",
        "high_label": "B",
        "unit": None,
        "level_count": 2,
    }
    center_runs = [run for run in payload["runs"] if run["center_point"]]
    assert [run["factor_levels"] for run in center_runs] == [
        {"Temperature": 70.0, "Material": "A"},
        {"Temperature": 70.0, "Material": "B"},
    ]
    assert [run["coded_levels"]["Material"] for run in center_runs] == [-1, 1]
    assert all(run["coded_levels"]["Temperature"] == 0 for run in center_runs)
    assert restored.status_code == 200
    assert restored.json() == payload


def test_categorical_fraction_keeps_generator_and_alias_structure(tmp_path) -> None:
    factors = [
        {"factor_kind": "numeric", "name": "A", "low": -1, "high": 1},
        {"factor_kind": "numeric", "name": "B", "low": -1, "high": 1},
        {"factor_kind": "numeric", "name": "C", "low": -1, "high": 1},
        {
            "factor_kind": "categorical",
            "name": "Material",
            "low_label": "Low grade",
            "high_label": "High grade",
        },
    ]
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "mixed half fraction",
                "design_type": "two_level_fractional",
                "fraction_id": "4-factor-half-r4",
                "factors": factors,
                "replicates": 1,
                "center_points": 0,
                "randomize": False,
                "randomization_seed": 3,
                "block_count": 1,
            },
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["run_count"] == 8
    assert payload["fractional"]["generators"] == ["D=ABC"]
    assert payload["fractional"]["resolution"] == 4
    assert {run["factor_levels"]["Material"] for run in payload["runs"]} == {
        "Low grade",
        "High grade",
    }


def test_all_categorical_factorial_rejects_center_points(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "all categorical",
                "factors": [
                    {
                        "factor_kind": "categorical",
                        "name": "Material",
                        "low_label": "A",
                        "high_label": "B",
                    },
                    {
                        "factor_kind": "categorical",
                        "name": "Supplier",
                        "low_label": "S1",
                        "high_label": "S2",
                    },
                ],
                "replicates": 1,
                "center_points": 1,
                "randomize": False,
                "randomization_seed": 3,
                "block_count": 1,
            },
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "doe_factorial_center_requires_numeric_factor"


def test_categorical_pseudo_centers_expand_within_each_block(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "blocked mixed factorial",
                "factors": [
                    {"factor_kind": "numeric", "name": "Temperature", "low": 60, "high": 80},
                    {
                        "factor_kind": "categorical",
                        "name": "Material",
                        "low_label": "A",
                        "high_label": "B",
                    },
                ],
                "replicates": 1,
                "center_points": 1,
                "randomize": False,
                "randomization_seed": 5,
                "block_count": 2,
            },
        )

    assert response.status_code == 201, response.text
    center_runs = [run for run in response.json()["runs"] if run["center_point"]]
    assert len(center_runs) == 4
    assert [run["block_index"] for run in center_runs] == [1, 1, 2, 2]
    assert [run["factor_levels"]["Material"] for run in center_runs] == ["A", "B", "A", "B"]
    assert all(run["factor_levels"]["Temperature"] == 70 for run in center_runs)


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
