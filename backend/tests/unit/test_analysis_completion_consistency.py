"""Deterministic metadata publication races; statistical payloads stay immutable."""

import ast
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from test_dataset_schema_cas import _version

from app.core.config import Settings
from app.main import create_app
from app.services.dataset_rows import get_dataset_rows_context
from app.storage import metadata


def _capture(root, version):
    return metadata.AnalysisCompletionDependencies(
        (metadata.DatasetSchemaDependency(version["version_id"], version["schema_hash"]),)
    )


def _change_schema(root, version_id, *, change=True):
    version = metadata.get_dataset_version_record(root, version_id)
    columns = metadata.list_dataset_column_records(root, version_id)
    updated = [replace(column, display_name=column.display_name + " B") for column in columns]
    return metadata.update_dataset_schema_records(
        root,
        version_id,
        hashlib.sha256((version.schema_hash + "B").encode()).hexdigest(),
        updated if change else columns,
        expected_schema_hash=version.schema_hash,
        stale_updated_at="2026-10-18T01:00:00Z",
    )


def _record(version_id, *, config=None, stale=False):
    return metadata.AnalysisRunRecord(
        analysis_id=str(uuid4()),
        method_id="eda.descriptive",
        method_version="0.2.0",
        dataset_version_id=version_id,
        config_json=json.dumps(config or {}),
        status="succeeded",
        result_path="synthetic/result.json",
        result_sha256="a" * 64,
        stale=stale,
        created_at="2026-10-18T00:00:00Z",
        updated_at="2026-10-18T00:00:00Z",
        completed_at="2026-10-18T00:00:00Z",
        app_version="0.1.0",
    )


@pytest.mark.parametrize("writer", ["plain", "artifacts", "model"])
@pytest.mark.parametrize("ordering", ["schema_first", "publication_first", "noop", "stale"])
def test_publication_and_schema_cas_commute_without_rewriting_records(tmp_path, writer, ordering):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        dependencies = _capture(tmp_path, version)
        record = _record(version["version_id"], stale=ordering == "stale")
        artifact = metadata.AnalysisArtifactRecord(
            str(uuid4()),
            record.analysis_id,
            "synthetic",
            "synthetic/data.json",
            "b" * 64,
            "application/json",
            record.created_at,
        )
        model = metadata.RegressionModelRecord(
            str(uuid4()),
            record.analysis_id,
            version["version_id"],
            "regression.linear_model",
            "0.3.0",
            "synthetic/model.json",
            "c" * 64,
            version["schema_hash"],
            record.created_at,
            "0.1.0",
        )
        if ordering in {"schema_first", "noop"}:
            _change_schema(tmp_path, version["version_id"], change=ordering != "noop")
        if writer == "plain":
            metadata.insert_analysis_run_record(tmp_path, record, dependencies=dependencies)
        elif writer == "artifacts":
            metadata.insert_analysis_run_record_with_artifacts(
                tmp_path, record, [artifact], dependencies=dependencies
            )
        else:
            metadata.insert_analysis_run_record_with_artifacts_and_regression_model(
                tmp_path, record, [artifact], model, dependencies=dependencies
            )
        if ordering == "publication_first":
            _change_schema(tmp_path, version["version_id"])
        stored = metadata.get_analysis_run_record(tmp_path, record.analysis_id)
        assert stored.stale is (ordering != "noop")
        assert stored.result_sha256 == record.result_sha256
        assert stored.config_json == record.config_json
        assert record.stale is (ordering == "stale")
        if writer == "model":
            assert metadata.get_regression_model_record(tmp_path, model.model_id) == model


def test_missing_dataset_owner_rolls_back_all_registration(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        record = _record(version["version_id"])
        dependencies = _capture(tmp_path, version)
        with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
            db.execute("DELETE FROM dataset_versions WHERE version_id=?", (version["version_id"],))
        with pytest.raises(
            metadata.AnalysisRunStorageConflict, match="analysis_completion_source_missing"
        ):
            metadata.insert_analysis_run_record_with_artifacts(
                tmp_path, record, [], dependencies=dependencies
            )
        assert metadata.get_analysis_run_record(tmp_path, record.analysis_id) is None


def test_source_read_captures_one_sqlite_revision_even_when_schema_commits_mid_read(
    tmp_path, monkeypatch
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
            assert db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        original = metadata._dataset_version_from_row
        triggered = False

        def convert(row):
            nonlocal triggered
            result = original(row)
            if not triggered:
                triggered = True
                _change_schema(tmp_path, version["version_id"])
            return result

        monkeypatch.setattr(metadata, "_dataset_version_from_row", convert)
        context = get_dataset_rows_context(
            Settings(workspace_root=tmp_path), UUID(version["version_id"])
        )
        assert triggered
        assert context.version.schema_hash == version["schema_hash"]
        assert [c.display_name for c in context.columns] == [
            c["display_name"] for c in version["columns"]
        ]
        assert (
            metadata.get_dataset_version_record(tmp_path, version["version_id"]).schema_hash
            != version["schema_hash"]
        )
        assert metadata.list_dataset_column_records(tmp_path, version["version_id"])[
            0
        ].display_name.endswith(" B")


def test_schema_writer_cannot_enter_between_completion_validation_and_insert(tmp_path, monkeypatch):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        record = _record(version["version_id"])
        validated, attempted = Event(), Event()
        original = metadata._insert_analysis_run

        def pause(connection, current):
            validated.set()
            assert attempted.wait(5)
            original(connection, current)

        def change():
            assert validated.wait(5)
            attempted.set()
            _change_schema(tmp_path, version["version_id"])

        monkeypatch.setattr(metadata, "_insert_analysis_run", pause)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                metadata.insert_analysis_run_record,
                tmp_path,
                record,
                dependencies=_capture(tmp_path, version),
            )
            second = pool.submit(change)
            first.result(timeout=10)
            second.result(timeout=10)
        assert metadata.get_analysis_run_record(tmp_path, record.analysis_id).stale


@pytest.mark.parametrize(
    "method",
    ["regression.predict", "regression.predict_pasted", "regression.linear_model_optimizer"],
)
@pytest.mark.parametrize("ordering", ["schema_first", "publication_first"])
@pytest.mark.parametrize("changed_source", ["source", "target"])
def test_model_source_schema_invalidates_completion_and_existing_derived_results(
    tmp_path, method, ordering, changed_source
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        source, target = _version(client), _version(client)
        owner = _record(source["version_id"])
        model = metadata.RegressionModelRecord(
            str(uuid4()),
            owner.analysis_id,
            source["version_id"],
            "regression.linear_model",
            "0.3.0",
            "synthetic/model.json",
            "c" * 64,
            source["schema_hash"],
            owner.created_at,
            "0.1.0",
        )
        metadata.insert_analysis_run_record_with_artifacts_and_regression_model(
            tmp_path, owner, [], model
        )
        prediction = replace(
            _record(target["version_id"], config={"model_id": model.model_id}), method_id=method
        )
        dependencies = metadata.AnalysisCompletionDependencies(
            (
                metadata.DatasetSchemaDependency(source["version_id"], source["schema_hash"]),
                metadata.DatasetSchemaDependency(target["version_id"], target["schema_hash"]),
            ),
            metadata.AnalysisModelDependency(
                model.model_id,
                owner.analysis_id,
                source["version_id"],
                model.manifest_sha256,
                model.schema_hash,
            ),
        )
        changed = source if changed_source == "source" else target
        unchanged = target if changed_source == "source" else source
        if ordering == "schema_first":
            _change_schema(tmp_path, changed["version_id"])
        metadata.insert_analysis_run_record(tmp_path, prediction, dependencies=dependencies)
        if ordering == "publication_first":
            _change_schema(tmp_path, changed["version_id"])
        assert metadata.get_analysis_run_record(tmp_path, prediction.analysis_id).stale
        assert (
            metadata.get_dataset_version_record(tmp_path, unchanged["version_id"]).schema_hash
            == unchanged["schema_hash"]
        )


@pytest.mark.parametrize("invalid", ["empty", "wrong_owner", "empty_hash", "inconsistent_hash"])
def test_invalid_captured_dependencies_never_register_a_result(tmp_path, invalid):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        dependency = metadata.DatasetSchemaDependency(version["version_id"], version["schema_hash"])
        items = (dependency,)
        record = _record(version["version_id"])
        if invalid == "empty":
            items = ()
        elif invalid == "wrong_owner":
            record = replace(record, dataset_version_id=str(uuid4()))
        elif invalid == "empty_hash":
            items = (replace(dependency, schema_hash=""),)
        else:
            items = (dependency, replace(dependency, schema_hash="b" * 64))
        with pytest.raises(
            metadata.AnalysisRunStorageConflict, match="analysis_completion_dependency_invalid"
        ):
            metadata.insert_analysis_run_record(
                tmp_path, record, dependencies=metadata.AnalysisCompletionDependencies(items)
            )
        assert metadata.get_analysis_run_record(tmp_path, record.analysis_id) is None


@pytest.mark.parametrize("mutation", ["removed", "hash", "owner", "stale"])
def test_captured_model_identity_cannot_be_replaced_at_completion(tmp_path, mutation):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        owner = _record(version["version_id"])
        model = metadata.RegressionModelRecord(
            str(uuid4()),
            owner.analysis_id,
            version["version_id"],
            "regression.linear_model",
            "0.3.0",
            "synthetic/model.json",
            "c" * 64,
            version["schema_hash"],
            owner.created_at,
            "0.1.0",
        )
        metadata.insert_analysis_run_record_with_artifacts_and_regression_model(
            tmp_path, owner, [], model
        )
        record = _record(version["version_id"])
        dependencies = replace(
            _capture(tmp_path, version),
            model=metadata.AnalysisModelDependency(
                model.model_id,
                owner.analysis_id,
                version["version_id"],
                model.manifest_sha256,
                model.schema_hash,
            ),
        )
        with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
            if mutation == "removed":
                db.execute("DELETE FROM regression_models WHERE model_id=?", (model.model_id,))
            elif mutation == "hash":
                db.execute(
                    "UPDATE regression_models SET manifest_sha256=? WHERE model_id=?",
                    ("f" * 64, model.model_id),
                )
            elif mutation == "owner":
                db.execute("DELETE FROM analysis_runs WHERE analysis_id=?", (owner.analysis_id,))
            else:
                db.execute(
                    "UPDATE analysis_runs SET stale=1 WHERE analysis_id=?", (owner.analysis_id,)
                )
        if mutation == "stale":
            metadata.insert_analysis_run_record(tmp_path, record, dependencies=dependencies)
            assert metadata.get_analysis_run_record(tmp_path, record.analysis_id).stale
        else:
            with pytest.raises(
                metadata.AnalysisRunStorageConflict, match="analysis_completion_source_"
            ):
                metadata.insert_analysis_run_record(tmp_path, record, dependencies=dependencies)
            assert metadata.get_analysis_run_record(tmp_path, record.analysis_id) is None


def test_all_production_completion_writers_supply_captured_dependencies():
    root = Path(__file__).resolve().parents[2] / "app" / "services"
    expected = {
        "analysis_run_execution.py",
        "analysis_runners_regression.py",
        "analysis_runner_pls.py",
        "analysis_runner_gaussian_process.py",
        "regression_models.py",
        "regression_pasted_predictions.py",
        "regression_response_optimizer.py",
    }
    found = set()
    for path in root.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id
                in {
                    "insert_analysis_run_record",
                    "insert_analysis_run_record_with_artifacts",
                    "insert_analysis_run_record_with_artifacts_and_regression_model",
                }
            ):
                assert any(keyword.arg == "dependencies" for keyword in node.keywords), (
                    path.name,
                    node.lineno,
                )
                found.add(path.name)
    assert found == expected
