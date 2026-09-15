import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.analysis_run_execution import canonical_json_bytes
from app.storage.metadata import metadata_db_path


def create_full(client, *, general=False, replicates=2, centers=0):
    route = "/api/v1/doe-designs/general-factorial" if general else "/api/v1/doe-designs/factorial"
    factors = (
        [
            {"name": name, "levels": levels}
            for name, levels in [("A", [1, 2, 3]), ("B", ["Low", "High"])]
        ]
        if general
        else [{"name": name, "low": -1, "high": 1} for name in "ABC"]
    )
    request = {
        "name": "Selection reference",
        "factors": factors,
        "replicates": replicates,
        "randomize": False,
        "randomization_seed": 11,
    }
    if not general:
        request.update(center_points=centers, block_count=1)
    created = client.post(route, json=request)
    assert created.status_code == 201, created.text
    design = created.json()
    base = f"/api/v1/doe-designs/{'general-factorial/' if general else ''}{design['design_id']}"
    values = []
    for run in design["runs"]:
        if general:
            levels = run["level_indices"]
            y = 10 + 3 * levels["A"] + 2 * levels["B"] + 0.001 * levels["A"] * levels["B"]
        else:
            a, b, c = (run["coded_levels"][name] for name in "ABC")
            y = (
                10
                + 3 * a
                + 2 * b
                + c
                + 0.02 * a * b
                + 0.03 * a * c
                + 0.04 * b * c
                + 0.01 * a * b * c
            )
        y += 0.5 * (run["replicate_index"] - 1)
        values.append({"run_order": run["run_order"], "value": y})
    saved = client.put(base + "/responses", json={"response_name": "Yield", "values": values})
    assert saved.status_code == 200, saved.text
    return design, base


@pytest.mark.parametrize("general", [False, True])
def test_selection_is_saved_restored_and_bound_to_config_and_revision(tmp_path, general):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, base = create_full(client, general=general)
        analyzed = client.post(
            base + "/analyses",
            json={
                "response_name": "Yield",
                "max_interaction_order": 2 if general else 3,
                "model_selection": {"method": "backward_elimination"},
            },
        )
        assert analyzed.status_code == 201, analyzed.text
        result = analyzed.json()
        assert result["result"]["schema_version"] == 3
        assert result["result"]["model_selection"]["alpha_to_remove"] == 0.05
        assert len(result["result"]["model_selection"]["final_term_ids"]) == (2 if general else 3)
        if general:
            assert result["result"]["model_selection"]["steps"][1]["removal_df"] == 2
        fetched = client.get(base + f"/analyses/{result['analysis_id']}")
        assert fetched.status_code == 200, fetched.text
        assert fetched.json() == result
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            stored = connection.execute(
                "SELECT result_json, config_json FROM experiment_design_analyses "
                "WHERE analysis_id=?",
                (result["analysis_id"],),
            ).fetchone()
            config = json.loads(stored[1])
            config["model_selection"]["alpha_to_remove"] = 0.7
            connection.execute(
                "UPDATE experiment_design_analyses SET config_json=? WHERE analysis_id=?",
                (json.dumps(config), result["analysis_id"]),
            )
        tampered = client.get(base + f"/analyses/{result['analysis_id']}")
        assert tampered.status_code == 409
        assert "config_checksum_mismatch" in tampered.json()["error"]["code"]
        assert len(design["design_sha256"]) == 64


@pytest.mark.parametrize("general", [False, True])
def test_server_term_catalog_and_manual_policy_round_trip(tmp_path, general):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, base = create_full(client, general=general, centers=3)
        route = f"/api/v1/doe-designs/{design['design_id']}/analysis-term-catalog"
        response = client.get(route, params={"max_interaction_order": 2})
        assert response.status_code == 200, response.text
        terms = response.json()["terms"]
        assert terms[0]["default_disposition"] == "forced"
        interaction = next(term for term in terms if term["kind"] == "interaction")
        assert len(interaction["hierarchy_dependencies"]) == 2
        assert interaction["df"] == (2 if general else 1)
        if not general:
            center = next(term for term in terms if term["kind"] == "curvature")
            assert center["default_disposition"] == "candidate"
            assert center["hierarchy_dependencies"] == []
            assert center["hierarchy_role"] == "independent_term"
        analysis = client.post(
            base + "/analyses",
            json={
                "response_name": "Yield",
                "max_interaction_order": 2,
                "model_selection": {
                    "term_policies": [
                        {"term_id": interaction["term_id"], "disposition": "excluded"}
                    ]
                },
            },
        )
        assert analysis.status_code == 201, analysis.text
        selection = analysis.json()["result"]["model_selection"]
        assert selection["initially_excluded_term_ids"] == [interaction["term_id"]]
        assert interaction["term_id"] not in selection["final_term_ids"]
        assert selection["removed_term_ids"] == []
        assert (
            client.get(base + "/analyses/" + analysis.json()["analysis_id"]).json()
            == analysis.json()
        )


def test_saturated_analysis_pools_without_inventing_p_values(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, base = create_full(client, replicates=1)
        result = client.post(
            base + "/analyses",
            json={
                "response_name": "Yield",
                "max_interaction_order": 3,
                "model_selection": {"method": "backward_elimination"},
            },
        )
        assert result.status_code == 201, result.text
        selection = result.json()["result"]["model_selection"]
        assert selection["initial_residual_df"] == 0
        assert selection["target_pool_count"] == 2
        assert len(selection["pooled_term_ids"]) == 2
        assert all(
            step["removal_p_value"] is None
            for step in selection["steps"]
            if step["phase"] == "initial_pooling"
        )


@pytest.mark.parametrize("screening", [False, True])
def test_aliased_designs_reject_automatic_selection_before_fitting(tmp_path, screening):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body = {
            "name": "Aliased selection guard",
            "randomization_seed": 11,
            "factors": [
                {"name": f"X{i}", "low": -1, "high": 1} for i in range(7 if screening else 5)
            ],
            "replicates": 1,
            "center_points": 0,
        }
        body.update(
            {"design_type": "plackett_burman_screening", "screening_catalog_id": "pb-12-run-v1"}
            if screening
            else {"design_type": "two_level_fractional", "fraction_id": "5-factor-half-r5"}
        )
        created = client.post("/api/v1/doe-designs/factorial", json=body)
        assert created.status_code == 201, created.text
        response = client.post(
            f"/api/v1/doe-designs/{created.json()['design_id']}/analyses",
            json={"response_name": "Yield", "model_selection": {"method": "backward_elimination"}},
        )
        assert response.status_code == 409
        assert (
            response.json()["error"]["code"]
            == "doe_factorial_model_selection_unsupported_for_aliased_design"
        )


def test_legacy_schema_one_bytes_remain_readable_without_rewrite(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, base = create_full(client)
        created = client.post(base + "/analyses", json={"response_name": "Yield"})
        assert created.status_code == 201, created.text
        analysis_id = created.json()["analysis_id"]
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            row = connection.execute(
                "SELECT config_json, result_json FROM experiment_design_analyses "
                "WHERE analysis_id=?",
                (analysis_id,),
            ).fetchone()
            config, envelope = map(json.loads, row)
            config["schema_version"] = 2
            config.pop("model_selection")
            envelope["method_version"] = "0.7.0"
            envelope["result"]["schema_version"] = 1
            for key in ("model_selection", "final_model", "config_sha256"):
                envelope["result"].pop(key)
            result_json = json.dumps(envelope, ensure_ascii=False)
            sha = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
            connection.execute(
                "UPDATE experiment_design_analyses SET method_version='0.7.0',"
                "config_json=?,result_json=?,result_sha256=? WHERE analysis_id=?",
                (json.dumps(config), result_json, sha, analysis_id),
            )
        restored = client.get(base + f"/analyses/{analysis_id}")
        assert restored.status_code == 200, restored.text
        assert restored.json()["result"]["schema_version"] == 1
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            assert connection.execute(
                "SELECT result_json,result_sha256 FROM experiment_design_analyses "
                "WHERE analysis_id=?",
                (analysis_id,),
            ).fetchone() == (result_json, sha)


def test_legacy_point_eight_config_and_result_restore_without_rewrite(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, base = create_full(client, centers=3)
        created = client.post(base + "/analyses", json={"response_name": "Yield"})
        assert created.status_code == 201, created.text
        analysis_id = created.json()["analysis_id"]
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            config_json, result_json = connection.execute(
                "SELECT config_json,result_json FROM experiment_design_analyses "
                "WHERE analysis_id=?",
                (analysis_id,),
            ).fetchone()
            config, envelope = json.loads(config_json), json.loads(result_json)
            config["schema_version"] = 3
            config["model_selection"].pop("term_policies", None)
            config_json = canonical_json_bytes(config).decode()
            envelope["method_version"] = "0.8.0"
            envelope["result"]["schema_version"] = 2
            envelope["result"]["config_sha256"] = hashlib.sha256(config_json.encode()).hexdigest()
            selection = envelope["result"]["model_selection"]
            for key in (
                "term_catalog",
                "initially_excluded_term_ids",
                "forced_term_ids",
                "candidate_term_ids",
                "term_policies",
            ):
                selection.pop(key, None)
            result_json = canonical_json_bytes(envelope).decode()
            sha = hashlib.sha256(result_json.encode()).hexdigest()
            connection.execute(
                "UPDATE experiment_design_analyses SET method_version='0.8.0',config_json=?,"
                "result_json=?,result_sha256=? WHERE analysis_id=?",
                (config_json, result_json, sha, analysis_id),
            )
        restored = client.get(base + f"/analyses/{analysis_id}")
        assert restored.status_code == 200, restored.text
        assert restored.json()["result"]["schema_version"] == 2
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            assert connection.execute(
                "SELECT config_json,result_json,result_sha256 FROM experiment_design_analyses "
                "WHERE analysis_id=?",
                (analysis_id,),
            ).fetchone() == (config_json, result_json, sha)
