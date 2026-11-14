"""Explicit mixture import uses existing canonical row/filter/provenance flow."""

from copy import deepcopy

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.unit.test_bo_dataset_import_api import ROOT, commit_request, preflight
from tests.unit.test_bo_mixture_lifecycle_api import request
from tests.unit.test_dataset_version_retention_api import _confirm


def test_mixture_import_fixed_component_repeats_and_restart_preserve_actual(tmp_path):
    settings = Settings(workspace_root=tmp_path / "mixture import workspace")
    with TestClient(create_app(settings)) as client:
        upload = client.post(
            "/api/v1/datasets",
            files={
                "file": (
                    "synthetic.csv",
                    b"a,b,fixed,y\n0.2,0.7,0.1,1\n0.3,0.6,0.1,2\n0.4,0.5,0.1,3\n0.4,0.5,0.1,4\n",
                    "text/csv",
                )
            },
        )
        assert upload.status_code == 201, upload.text
        version = _confirm(client, upload.json()["dataset_id"])
        definition = request()
        body = {
            "schema_version": 2,
            "name": "Measured mixture",
            "dataset_version_id": version["version_id"],
            "expected_schema_hash": version["schema_hash"],
            "mixture": definition["mixture"],
            "factor_mappings": [
                {
                    "column_id": version["columns"][i]["column_id"],
                    "factor": {**c, "domain_kind": "mixture_component"},
                }
                for i, c in enumerate(definition["mixture"]["components"])
            ],
            "objective": definition["objective"],
            "response_mappings": [
                {"column_id": version["columns"][3]["column_id"], "response_id": "yield"}
            ],
            "filter_snapshot": {"expression_version": 1, "conditions": []},
            "missing_policy": "reject",
        }
        preview = preflight(client, body)
        assert preview["schema_version"] == 2
        assert preview["n_used"] == 4 and preview["repeated_coordinate_count"] == 1
        commit = commit_request(body, preview)
        response = client.post(f"{ROOT}/from-dataset", json=commit)
        assert response.status_code == 201, response.text
        study = response.json()
        assert study["study_schema_version"] == 8
        assert study["initial_design"]["import_schema_version"] == 2
        assert "seed" not in study["initial_design"]
        assert study["completed_trial_count"] == 4
        assert [t["actual_coordinates"]["a"] for t in study["trials"]] == [0.2, 0.3, 0.4, 0.4]
        assert client.post(f"{ROOT}/from-dataset", json=commit).json() == study
        missing = deepcopy(body)
        missing["factor_mappings"] = missing["factor_mappings"][:-1]
        assert client.post(f"{ROOT}/import-preflight", json=missing).status_code == 422
        # Altering declared total cannot silently renormalize measured amounts.
        wrong_total = deepcopy(body)
        wrong_total["mixture"]["total"] = 1.1
        assert client.post(f"{ROOT}/import-preflight", json=wrong_total).status_code == 409
        conflict = {**commit, "name": "Another name"}
        assert client.post(f"{ROOT}/from-dataset", json=conflict).status_code == 409
        endpoint = f"{ROOT}/{study['study_id']}"
    with TestClient(create_app(settings)) as client:
        assert client.get(endpoint).json() == study
