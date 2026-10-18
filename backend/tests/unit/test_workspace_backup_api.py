"""Offline archive round-trip of real, exclusively synthetic API-owned assets."""

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from test_bayesian_recommendations_api import _complete_initial_trials, _create_study
from test_factorial_prediction import _analyze
from test_gaussian_process_regression_api import _create_dataset, _create_gp_analysis
from test_lhs_design_api import _request as lhs_request
from test_workspace_asset_retention_api import _create_limit_set, _create_linear_model

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.services import dataset_rows
from app.storage.metadata import initialize_metadata_store, metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace, verify_backup


def _json(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def _logical_database(root: Path) -> list[str]:
    with sqlite3.connect(f"{metadata_db_path(root).as_uri()}?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        return list(db.iterdump())


def _owned_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in (root / "workspaces", root / "artifacts")
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file()
    }


def _pls(client, version):
    response_id = version["columns"][0]["column_id"]
    predictors = [column["column_id"] for column in version["columns"][1:]]
    return _json(
        client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.partial_least_squares",
                "method_version": METHOD_VERSIONS["regression.partial_least_squares"],
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "response_column_id": response_id,
                    "predictor_column_ids": predictors,
                    "scale": True,
                    "component_selection": "fixed",
                    "n_components": 2,
                    "max_components": 2,
                    "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 19},
                },
            },
        ),
        201,
    )


def _point_request(analysis):
    return {
        "expected_model_manifest_sha256": analysis["result"]["model_manifest"]["manifest_sha256"],
        "rows": [
            {
                "client_row_id": "synthetic-input",
                "values": {
                    column["column_id"]: value
                    for column, value in zip(
                        analysis["result"]["predictors"], (2.5, 1.0), strict=True
                    )
                },
            }
        ],
    }


def test_backup_restore_reopens_models_results_reports_and_database_assets(tmp_path, monkeypatch):
    source = tmp_path / "source workspace"
    target = tmp_path / "restored \uac80\uc99d workspace"
    archive = tmp_path / "offline backup.zip"
    originals = {}
    predictions = []
    with TestClient(create_app(Settings(workspace_root=source))) as client:
        version = _create_dataset(client)
        gp = _create_gp_analysis(client, version)
        pls = _pls(client, version)
        for analysis, suffix in (
            (gp, "gaussian-process-predictions"),
            (pls, "pls-point-predictions"),
        ):
            model_id = analysis["result"]["model_manifest"]["model_id"]
            path = f"/api/v1/regression-models/{model_id}/{suffix}"
            request = _point_request(analysis)
            predictions.append((path, request, _json(client.post(path, json=request))))
            analysis_path = f"/api/v1/analysis-runs/{analysis['analysis_id']}"
            originals[analysis_path + "/result"] = client.get(analysis_path + "/result").content
            export = _json(client.post(analysis_path + "/exports/html", json={"locale": "ko"}), 201)
            download = analysis_path + f"/exports/{export['export_id']}/download"
            originals[download] = client.get(download).content
            assert b"<svg" in originals[download]

        # Stored OLS predictions exercise the analysis-owned prediction artifacts.
        linear = _create_linear_model(client)
        saved_prediction = _json(
            client.post(
                f"/api/v1/regression-models/{linear['model_id']}/predictions",
                json={
                    "dataset_version_id": linear["dataset_version_id"],
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intervals": True,
                },
            )
        )
        prediction_path = f"/api/v1/analysis-runs/{saved_prediction['prediction_id']}/result"
        originals[prediction_path] = client.get(prediction_path).content
        limit_set = _create_limit_set(client)
        limit_path = f"/api/v1/quality/attribute-control-limit-sets/{limit_set['limit_set_id']}"
        originals[limit_path] = client.get(limit_path).content

        _, _, factorial_path = _analyze(client, replicates=1)
        factorial_report = _json(
            client.post(factorial_path + "/exports/html", json={"locale": "en"}), 201
        )
        factorial_download = factorial_path + f"/exports/{factorial_report['asset_id']}/download"
        originals[factorial_download] = client.get(factorial_download).content
        assert b"<svg" in originals[factorial_download]
        originals[factorial_path] = client.get(factorial_path).content

        lhs = _json(client.post("/api/v1/doe-designs/latin-hypercube", json=lhs_request()), 201)
        lhs_path = f"/api/v1/doe-designs/latin-hypercube/{lhs['design_id']}"
        _json(
            client.put(
                lhs_path + "/responses",
                json={
                    "response_name": "Synthetic yield",
                    "unit": "%",
                    "values": [
                        {"run_order": run["run_order"], "value": float(run["run_order"])}
                        for run in lhs["runs"]
                    ],
                },
            )
        )
        originals[lhs_path] = client.get(lhs_path).content
        study = _complete_initial_trials(client, _create_study(client))
        study_path = f"/api/v1/bayesian-studies/{study['study_id']}"
        originals[study_path] = client.get(study_path).content
        # An upload with no confirmed version must also survive the archive.
        _json(
            client.post(
                "/api/v1/datasets", files={"file": ("unconfirmed.csv", b"x\n1\n", "text/csv")}
            ),
            201,
        )
        for path, content in originals.items():
            assert client.get(path).status_code == 200, path
            assert content, path

    database_before = _logical_database(source)
    files_before = _owned_hashes(source)
    assert any(path.endswith(".npz") for path in files_before)
    assert any(path.startswith("artifacts/attribute-control-limit-sets/") for path in files_before)

    def forbidden(*args, **kwargs):
        raise AssertionError("Archive/restore/report must not refit or reload source rows")

    monkeypatch.setattr("sklearn.gaussian_process.GaussianProcessRegressor.fit", forbidden)
    monkeypatch.setattr("sklearn.cross_decomposition.PLSRegression.fit", forbidden)
    canonical_reader = dataset_rows._iter_canonical_rows_jsonl
    monkeypatch.setattr("app.services.dataset_rows._iter_canonical_rows_jsonl", forbidden)
    monkeypatch.setattr(
        "app.services.doe_factorial_analysis.calculate_factorial_analysis", forbidden
    )
    monkeypatch.setattr("app.services.bayesian_recommendations._run_worker", forbidden)
    manifest = backup_workspace(source, archive)
    verified = verify_backup(archive)
    assert verified == manifest
    restore_workspace(archive, target)
    assert _logical_database(source) == database_before
    assert _logical_database(target) == database_before
    assert _owned_hashes(source) == files_before
    assert _owned_hashes(target) == files_before

    for _restart in range(2):
        with TestClient(create_app(Settings(workspace_root=target))) as client:
            for path, content in originals.items():
                # The existing limit-set reader verifies source integrity, without refitting.
                with monkeypatch.context() as read_guard:
                    if path == limit_path:
                        read_guard.setattr(
                            dataset_rows, "_iter_canonical_rows_jsonl", canonical_reader
                        )
                    response = client.get(path)
                assert response.status_code == 200, response.text
                assert response.content == content, path
            for path, request, expected in predictions:
                assert _json(client.post(path, json=request)) == expected
    assert _owned_hashes(target) == files_before
    assert _logical_database(target) == database_before


def test_cli_processes_preserve_existing_output_and_restore_to_new_path(tmp_path):
    source = tmp_path / "source \uac80\uc99d workspace"
    restored = tmp_path / "restored \uac80\uc99d workspace"
    archive = tmp_path / "backup \uac80\uc99d archive.zip"
    initialize_metadata_store(source)
    before = _logical_database(source)
    scripts = Path(__file__).resolve().parents[3] / "scripts"

    def run(*arguments):
        return subprocess.run(
            [sys.executable, *map(str, arguments)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )

    backup = run(scripts / "backup_workspace.py", "--workspace", source, "--output", archive)
    assert backup.returncode == 0, backup.stderr
    assert json.loads(backup.stdout)["status"] == "verified"
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    verify = run("-m", "app.storage.workspace_backup", "verify", "--archive", archive)
    assert verify.returncode == 0, verify.stderr
    restore = run(scripts / "restore_workspace.py", "--archive", archive, "--workspace", restored)
    assert restore.returncode == 0, restore.stderr
    assert _logical_database(restored) == before
    repeated = run(scripts / "backup_workspace.py", "--workspace", source, "--output", archive)
    assert repeated.returncode != 0
    assert "workspace_backup_output_exists" in repeated.stderr
    assert str(source) not in repeated.stderr
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == archive_hash
    assert _logical_database(source) == before
