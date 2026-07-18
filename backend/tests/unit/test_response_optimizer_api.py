import hashlib
import json
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path


def _create_source_analysis(client: TestClient) -> tuple[dict, dict]:
    design_response = client.post(
        "/api/v1/doe-designs/response-surface",
        json={
            "name": "optimizer source",
            "factors": [
                {"name": "x", "low": -1, "high": 1, "unit": None},
                {"name": "y", "low": -1, "high": 1, "unit": None},
            ],
            "alpha_mode": "face_centered",
            "factorial_replicates": 1,
            "axial_replicates": 1,
            "center_points": 5,
            "randomize": False,
            "randomization_seed": 20260714,
        },
    )
    assert design_response.status_code == 201
    design = design_response.json()
    values = []
    # This residual vector is orthogonal to the full-quadratic design matrix.
    # It preserves the known coefficients while supplying usable pure error.
    residuals = iter(
        (
            0.010217187,
            0.024252324,
            0.006538905,
            0.020574042,
            -0.034469512,
            -0.027112947,
            -0.016756092,
            -0.044826366,
            0.066003936,
            -0.193417106,
            0.147970251,
            -0.018327842,
            0.059353219,
        )
    )
    for run in design["runs"]:
        x = run["coded_levels"]["x"]
        y = run["coded_levels"]["y"]
        response = 10.0 - (x - 0.25) ** 2 - 2.0 * (y + 0.5) ** 2 + next(residuals)
        values.append({"run_order": run["run_order"], "value": response})
    stored = client.put(
        f"/api/v1/doe-designs/response-surface/{design['design_id']}/responses",
        json={"response_name": "Yield", "unit": "%", "values": values},
    )
    assert stored.status_code == 200
    analysis_response = client.post(
        f"/api/v1/doe-designs/response-surface/{design['design_id']}/analyses",
        json={
            "response_name": "Yield",
            "confidence_level": 0.95,
            "point_limit": 256,
            "contour_grid_size": 21,
        },
    )
    assert analysis_response.status_code == 201
    return design, analysis_response.json()


def _optimizer_request(source_analysis_id: str) -> dict:
    return {
        "objectives": [
            {
                "source_analysis_id": source_analysis_id,
                "goal": "maximize",
                "lower": 8.0,
                "target": 10.0,
                "upper": None,
                "lower_weight": 1.0,
                "upper_weight": 1.0,
                "importance": 1.0,
            }
        ],
        "factor_bounds": [],
        "linear_constraints": [
            {
                "name": "combined setting",
                "coefficients": {"x": 1.0, "y": 1.0},
                "relation": "less_than_or_equal",
                "bound": 0.0,
            }
        ],
        "acknowledged_source_warning_codes": [],
        "search": {
            "random_seed": 20260714,
            "random_candidate_count": 128,
            "multi_start_count": 8,
            "max_iterations": 120,
            "max_evaluations": 5000,
            "time_budget_ms": 5000,
        },
    }


def test_response_surface_analysis_catalog_is_paged_redacted_and_validated(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design, analysis = _create_source_analysis(client)
        response = client.get("/api/v1/doe-designs/response-surface-analyses?offset=0&limit=1")
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE experiment_design_analyses SET result_json = result_json || ' ' "
                "WHERE analysis_id = ?",
                (analysis["analysis_id"],),
            )
            connection.commit()
        tampered_response = client.get(
            "/api/v1/doe-designs/response-surface-analyses?offset=0&limit=1"
        )
        selected_response = client.get(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/analyses/"
            f"{analysis['analysis_id']}"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["returned"] == 1
    assert payload["has_previous"] is False
    assert payload["has_next"] is False
    item = payload["analyses"][0]
    assert item["analysis_id"] == analysis["analysis_id"]
    assert item["design_id"] == design["design_id"]
    assert item["design_name"] == "optimizer source"
    assert item["response_name"] == "Yield"
    assert item["response_revision_id"] == analysis["response_revision_id"]
    assert item["response_revision_number"] == 1
    assert item["method_id"] == "doe.response_surface"
    assert item["eligibility_status"] in {"eligible", "acknowledgment_required"}
    assert item["blocking_issue_count"] == 0
    assert "result" not in response.text
    assert "response_value" not in response.text
    assert str(tmp_path) not in response.text

    tampered_item = tampered_response.json()["analyses"][0]
    assert tampered_item["eligibility_status"] == "integrity_error"
    assert tampered_item["availability_code"] == "doe_rsm_analysis_integrity_error"
    assert selected_response.status_code == 409
    assert selected_response.json()["error"]["code"] == "doe_rsm_analysis_checksum_mismatch"
    assert str(tmp_path) not in tampered_response.text


def _replace_source_result(workspace_root, analysis_id: str, mutate) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        (result_json,) = connection.execute(
            "SELECT result_json FROM experiment_design_analyses WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchone()
        payload = json.loads(result_json)
        mutate(payload["result"])
        updated_result_json = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        connection.execute(
            "UPDATE experiment_design_analyses SET result_json = ?, result_sha256 = ? "
            "WHERE analysis_id = ?",
            (
                updated_result_json,
                hashlib.sha256(updated_result_json.encode("utf-8")).hexdigest(),
                analysis_id,
            ),
        )
        connection.commit()


def test_response_optimizer_api_creates_and_restores_bounded_auditable_result(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design, analysis = _create_source_analysis(client)
        created_response = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(analysis["analysis_id"]),
        )
        assert created_response.status_code == 201
        created = created_response.json()
        restored_response = client.get(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}"
            f"/optimizations/{created['optimization_id']}"
        )

    assert restored_response.status_code == 200
    restored = restored_response.json()
    assert restored == created
    assert created["method_id"] == "regression.response_optimizer"
    assert created["method_version"] == METHOD_VERSIONS["regression.response_optimizer"]
    assert created["config_schema_version"] == 2
    assert created["result_schema_version"] == 2
    assert created["source_analysis_ids"] == [analysis["analysis_id"]]
    assert len(created["source_bundle_sha256"]) == 64
    assert len(created["config_sha256"]) == 64
    assert created["python_version"]
    assert created["platform"]
    assert created["package_versions"]["numpy"]
    assert created["package_versions"]["scipy"]
    result = created["result"]
    assert result["schema_version"] == 2
    assert result["source_model_eligibility"]["eligible"] is True
    assert result["source_model_eligibility"]["acknowledgment_required"] is False
    assert result["acknowledged_source_warning_codes"] == []
    assert created["acknowledged_source_warning_codes"] == []
    assert result["summary_type"] == "response_optimizer"
    recommendation = result["recommendation"]
    assert recommendation["actual_coordinates"]["x"] == pytest.approx(0.25, abs=1e-5)
    assert recommendation["actual_coordinates"]["y"] == pytest.approx(-0.5, abs=1e-5)
    assert recommendation["composite_desirability"] == pytest.approx(1.0)
    assert recommendation["all_constraints_satisfied"] is True
    assert result["search"]["global_optimum_guaranteed"] is False
    assert "response_optimizer_confirmation_run_required" in result["warnings"]
    assert str(tmp_path) not in created_response.text


def test_response_optimizer_restore_stays_pinned_after_new_response_revision(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis = _create_source_analysis(client)
        created = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(analysis["analysis_id"]),
        ).json()
        correction = client.post(
            f"/api/v1/doe-designs/{design['design_id']}/response-revisions",
            json={
                "response_name": "Yield",
                "unit": "%",
                "values": [
                    {"run_order": run["run_order"], "value": 100.0 + run["run_order"]}
                    for run in design["runs"]
                ],
                "supersedes_response_revision_id": analysis["response_revision_id"],
            },
        )
        source_restore = client.get(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/analyses/"
            f"{analysis['analysis_id']}"
        )
        optimizer_restore = client.get(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}"
            f"/optimizations/{created['optimization_id']}"
        )

    assert correction.status_code == 201
    assert correction.json()["revision_number"] == 2
    assert source_restore.status_code == 200
    assert source_restore.json()["response_revision_id"] == analysis["response_revision_id"]
    assert optimizer_restore.status_code == 200
    assert optimizer_restore.json() == created


def test_response_optimizer_api_honors_narrow_factor_bounds(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis = _create_source_analysis(client)
        request = _optimizer_request(analysis["analysis_id"])
        request["factor_bounds"] = [{"factor_name": "x", "lower": -1.0, "upper": 0.0}]
        request["linear_constraints"] = []
        response = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=request,
        )

    assert response.status_code == 201
    result = response.json()["result"]
    assert result["recommendation"]["actual_coordinates"]["x"] == pytest.approx(0.0, abs=1e-6)
    assert "response_optimizer_recommendation_on_factor_bound" in result["warnings"]


def test_response_optimizer_api_rejects_missing_source_and_invalid_goal_thresholds(
    tmp_path,
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis = _create_source_analysis(client)
        missing = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(str(uuid4())),
        )
        request = _optimizer_request(analysis["analysis_id"])
        request["objectives"][0]["lower"] = 11
        invalid = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=request,
        )

    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "response_optimizer_source_analysis_missing"
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "response_optimizer_objective_thresholds_invalid"
    assert str(tmp_path) not in missing.text
    assert str(tmp_path) not in invalid.text


def test_response_optimizer_restore_rejects_config_result_relationship_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design, analysis = _create_source_analysis(client)
        created = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(analysis["analysis_id"]),
        ).json()

        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            config_json, result_json = connection.execute(
                "SELECT config_json, result_json FROM experiment_design_analyses "
                "WHERE analysis_id = ?",
                (created["optimization_id"],),
            ).fetchone()
            config = json.loads(config_json)
            config["request"]["objectives"][0]["target"] = 9.5
            updated_config_json = json.dumps(
                config,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            result = json.loads(result_json)
            result["config_sha256"] = hashlib.sha256(
                updated_config_json.encode("utf-8")
            ).hexdigest()
            updated_result_json = json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            connection.execute(
                "UPDATE experiment_design_analyses "
                "SET config_json = ?, result_json = ?, result_sha256 = ? "
                "WHERE analysis_id = ?",
                (
                    updated_config_json,
                    updated_result_json,
                    hashlib.sha256(updated_result_json.encode("utf-8")).hexdigest(),
                    created["optimization_id"],
                ),
            )
            connection.commit()

        restored = client.get(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}"
            f"/optimizations/{created['optimization_id']}"
        )

    assert restored.status_code == 409
    assert restored.json()["error"]["code"] == "response_optimizer_result_config_mismatch"
    assert str(tmp_path) not in restored.text


def test_response_optimizer_restore_rejects_result_checksum_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design, analysis = _create_source_analysis(client)
        created = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(analysis["analysis_id"]),
        ).json()
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE experiment_design_analyses SET result_json = result_json || ' ' "
                "WHERE analysis_id = ?",
                (created["optimization_id"],),
            )
            connection.commit()
        restored = client.get(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}"
            f"/optimizations/{created['optimization_id']}"
        )

    assert restored.status_code == 409
    assert restored.json()["error"]["code"] == "response_optimizer_checksum_mismatch"
    assert str(tmp_path) not in restored.text


@pytest.mark.parametrize(
    "condition",
    ["saturated", "zero_residual_variance", "significant_lack_of_fit"],
)
def test_response_optimizer_api_rejects_ineligible_source_models(tmp_path, condition: str) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis = _create_source_analysis(client)

        def mutate(result: dict) -> None:
            if condition == "saturated":
                result["sample"]["df_residual"] = 0
                result["fit"]["residual_mean_square"] = None
                result["fit"]["residual_standard_error"] = None
            elif condition == "zero_residual_variance":
                result["fit"]["residual_mean_square"] = 0.0
                result["fit"]["residual_standard_error"] = 0.0
            else:
                result["anova"]["lack_of_fit"]["available"] = True
                result["anova"]["lack_of_fit"]["lack_of_fit"]["p_value"] = 0.001

        _replace_source_result(tmp_path, analysis["analysis_id"], mutate)
        response = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(analysis["analysis_id"]),
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "response_optimizer_source_model_ineligible"
    assert "recommendation" not in response.text
    assert str(tmp_path) not in response.text


def test_response_optimizer_api_requires_and_records_source_warning_acknowledgment(
    tmp_path,
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis = _create_source_analysis(client)
        _replace_source_result(
            tmp_path,
            analysis["analysis_id"],
            lambda result: result["sample"].__setitem__("df_residual", 4),
        )
        missing_ack = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(analysis["analysis_id"]),
        )
        request = _optimizer_request(analysis["analysis_id"])
        request["acknowledged_source_warning_codes"] = [
            "response_optimizer_source_residual_df_small"
        ]
        created_response = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=request,
        )

        assert created_response.status_code == 201
        created = created_response.json()
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            (config_json,) = connection.execute(
                "SELECT config_json FROM experiment_design_analyses WHERE analysis_id = ?",
                (created["optimization_id"],),
            ).fetchone()

    acknowledged = ["response_optimizer_source_residual_df_small"]
    assert missing_ack.status_code == 409
    assert (
        missing_ack.json()["error"]["code"]
        == "response_optimizer_source_model_acknowledgment_required"
    )
    assert created["acknowledged_source_warning_codes"] == acknowledged
    assert created["result"]["acknowledged_source_warning_codes"] == acknowledged
    eligibility = created["result"]["source_model_eligibility"]
    assert eligibility["eligible"] is True
    assert eligibility["acknowledgment_required"] is True
    assert eligibility["acknowledged_source_warning_codes"] == acknowledged
    assert any(
        issue["code"] == acknowledged[0] and issue["severity"] == "acknowledgment_required"
        for issue in eligibility["issues"]
    )
    assert json.loads(config_json)["request"]["acknowledged_source_warning_codes"] == acknowledged


def test_response_optimizer_api_rejects_source_checksum_mismatch_without_path_exposure(
    tmp_path,
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis = _create_source_analysis(client)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE experiment_design_analyses SET result_json = result_json || ' ' "
                "WHERE analysis_id = ?",
                (analysis["analysis_id"],),
            )
            connection.commit()
        response = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(analysis["analysis_id"]),
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "response_optimizer_source_model_ineligible"
    assert "recommendation" not in response.text
    assert str(tmp_path) not in response.text
