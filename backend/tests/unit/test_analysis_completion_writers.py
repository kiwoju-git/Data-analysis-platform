"""Real synthetic analyses at the seven completion boundaries, without refitting on publish."""

import hashlib
import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient
from test_analysis_completion_consistency import _change_schema
from test_gaussian_process_regression_api import _create_dataset
from test_regression_workflow_extensions_api import _fit_model

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.storage import metadata

TRAINING = [
    ("eda.descriptive", "analysis_run_execution", "artifacts", {}),
    ("regression.linear_model", "analysis_runners_regression", "model", {"estimator": "ols"}),
    (
        "regression.linear_model",
        "analysis_runners_regression",
        "model",
        {
            "estimator": "ridge",
            "fixed_alpha": 1.0,
            "regularization": {"mode": "fixed", "validation": "none"},
        },
    ),
    (
        "regression.partial_least_squares",
        "analysis_runner_pls",
        "model",
        {
            "component_selection": "fixed",
            "n_components": 2,
            "max_components": 2,
            "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 19},
        },
    ),
    (
        "regression.gaussian_process",
        "analysis_runner_gaussian_process",
        "model",
        {
            "optimizer_restarts": 0,
            "cv_optimizer_restarts": 0,
            "cv": {"method": "none"},
            "profile_points": 10,
            "surface_grid_size": 10,
            "time_budget_seconds": 30,
        },
    ),
]


def _writer(module, kind):
    return (
        importlib.import_module("app.services." + module),
        {
            "plain": "insert_analysis_run_record",
            "artifacts": "insert_analysis_run_record_with_artifacts",
            "model": "insert_analysis_run_record_with_artifacts_and_regression_model",
        }[kind],
    )


def _owned_bytes(root, record, args, kwargs):
    artifacts = kwargs.get("artifacts", args[0] if args else [])
    return {
        relative: (root / relative).read_bytes()
        for relative in [record.result_path, *(item.path for item in artifacts)]
    }


def _install_interleaving(
    monkeypatch, root, version_id, module, kind, *, delete=False, noop=False, missing_model=None
):
    service, name = _writer(module, kind)
    original = getattr(service, name)
    evidence = []

    def publish(workspace, record, *args, **kwargs):
        assert kwargs["dependencies"].datasets
        before = _owned_bytes(root, record, args, kwargs)
        evidence.append((record, before))
        if missing_model is not None:
            with sqlite3.connect(metadata.metadata_db_path(root)) as db:
                db.execute("DELETE FROM regression_models WHERE model_id=?", (missing_model,))
        elif delete:
            with sqlite3.connect(metadata.metadata_db_path(root)) as db:
                db.execute("DELETE FROM dataset_versions WHERE version_id=?", (version_id,))
        else:
            _change_schema(root, version_id, change=not noop)
        original(workspace, record, *args, **kwargs)
        assert _owned_bytes(root, record, args, kwargs) == before

    monkeypatch.setattr(service, name, publish)
    return evidence


def _request(version, method, options):
    columns = version["columns"]
    selection = (
        {"column_ids": [columns[0]["column_id"]]}
        if method == "eda.descriptive"
        else {
            "response_column_id": columns[0]["column_id"],
            "predictor_column_ids": [column["column_id"] for column in columns[1:]],
        }
    )
    return {
        "method_id": method,
        "method_version": METHOD_VERSIONS[method],
        "dataset_version_id": version["version_id"],
        "roles": {},
        "options": {**selection, **options},
    }


@pytest.mark.parametrize("method,module,kind,options", TRAINING)
def test_actual_training_completion_keeps_captured_schema_and_artifact_bytes(
    tmp_path, monkeypatch, method, module, kind, options
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _create_dataset(client)
        evidence = _install_interleaving(monkeypatch, tmp_path, version["version_id"], module, kind)
        response = client.post("/api/v1/analysis-runs", json=_request(version, method, options))
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
        assert len(evidence) == 1
        record, before = evidence[0]
        stored = metadata.get_analysis_run_record(tmp_path, record.analysis_id)
        assert stored.status == "succeeded" and stored.stale
        assert stored.result_sha256 == hashlib.sha256(before[record.result_path]).hexdigest()
        if kind == "model":
            pointer = payload["result"]["model_manifest"]
            model = metadata.get_regression_model_record(tmp_path, pointer["model_id"])
            assert model.schema_hash == version["schema_hash"]
            assert (
                hashlib.sha256((tmp_path / model.manifest_path).read_bytes()).hexdigest()
                == model.manifest_sha256
            )
            assert pointer["manifest_sha256"] == model.manifest_sha256


@pytest.mark.parametrize(
    "method,module,kind,options", [item for item in TRAINING if item[3].get("estimator") != "ridge"]
)
def test_deleted_training_owner_rejects_publication_and_cleans_only_own_outputs(
    tmp_path, monkeypatch, method, module, kind, options
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _create_dataset(client)
        source_files = {
            path: path.read_bytes()
            for path in tmp_path.rglob("*")
            if path.is_file() and path.suffix not in {".sqlite3", ".lock"}
        }
        evidence = _install_interleaving(
            monkeypatch, tmp_path, version["version_id"], module, kind, delete=True
        )
        response = client.post("/api/v1/analysis-runs", json=_request(version, method, options))
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "analysis_completion_source_missing"
        assert len(evidence) == 1
        record, owned = evidence[0]
        assert metadata.get_analysis_run_record(tmp_path, record.analysis_id) is None
        assert all(not (tmp_path / path).exists() for path in owned)
        assert all(path.read_bytes() == content for path, content in source_files.items())


def test_actual_noop_schema_save_does_not_stale_pending_analysis(tmp_path, monkeypatch):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _create_dataset(client)
        evidence = _install_interleaving(
            monkeypatch,
            tmp_path,
            version["version_id"],
            "analysis_run_execution",
            "artifacts",
            noop=True,
        )
        response = client.post(
            "/api/v1/analysis-runs", json=_request(version, "eda.descriptive", {})
        )
        assert response.status_code == 201, response.text
        assert not metadata.get_analysis_run_record(tmp_path, evidence[0][0].analysis_id).stale


@pytest.mark.parametrize("workflow", ["dataset_prediction", "pasted_prediction", "optimizer"])
@pytest.mark.parametrize("mutation", ["schema", "model_deleted"])
def test_actual_model_derived_completion_records_schema_change_without_altering_prediction(
    tmp_path, monkeypatch, workflow, mutation
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version, model_id, manifest_sha = _fit_model(client)
        base = f"/api/v1/regression-models/{model_id}"
        if workflow == "pasted_prediction":
            request = {
                "content": "x1\tx2\n2\t4\n4\t3\n",
                "has_header": True,
                "delimiter": "tab",
                "column_mappings": [],
                "expected_model_manifest_sha256": manifest_sha,
            }
            preflight = client.post(base + "/pasted-prediction-preflight", json=request)
            assert preflight.status_code == 200, preflight.text
            request.update(
                expected_normalized_input_sha256=preflight.json()["normalized_input_sha256"],
                confidence_level=0.95,
                include_intervals=True,
            )
            path, module, kind = "/pasted-predictions", "regression_pasted_predictions", "artifacts"
        elif workflow == "optimizer":
            request = {
                "expected_model_manifest_sha256": manifest_sha,
                "goal": {"kind": "maximize", "lower": 8.0, "target": 30.0, "upper": None},
                "search": {
                    "random_seed": 11,
                    "random_candidate_count": 64,
                    "multi_start_count": 2,
                    "max_iterations": 50,
                    "max_evaluations": 2000,
                    "profile_point_count": 11,
                },
            }
            path, module, kind = "/response-optimizations", "regression_response_optimizer", "plain"
        else:
            request = {
                "dataset_version_id": version["version_id"],
                "confidence_level": 0.95,
                "missing_policy": "complete_case",
                "include_intervals": True,
            }
            path, module, kind = "/predictions", "regression_models", "artifacts"
        model = metadata.get_regression_model_record(tmp_path, model_id)
        source_manifest = (tmp_path / model.manifest_path).read_bytes()
        evidence = _install_interleaving(
            monkeypatch,
            tmp_path,
            version["version_id"],
            module,
            kind,
            missing_model=model_id if mutation == "model_deleted" else None,
        )
        response = client.post(base + path, json=request)
        assert len(evidence) == 1
        record, before = evidence[0]
        if mutation == "model_deleted":
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "analysis_completion_source_missing"
            assert metadata.get_analysis_run_record(tmp_path, record.analysis_id) is None
            assert all(not (tmp_path / relative).exists() for relative in before)
            assert (tmp_path / model.manifest_path).read_bytes() == source_manifest
            return
        assert response.status_code in {200, 201}, response.text
        stored = metadata.get_analysis_run_record(tmp_path, record.analysis_id)
        assert stored.stale and stored.status == "succeeded"
        assert stored.result_sha256 == hashlib.sha256(before[record.result_path]).hexdigest()
        assert response.json()["model_manifest_sha256"] == manifest_sha
