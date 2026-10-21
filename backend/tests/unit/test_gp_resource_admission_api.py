from __future__ import annotations

import hashlib
import sqlite3

from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path


def test_extended_memory_rejection_preserves_source_and_commits_no_partial_model(tmp_path):
    workspace = tmp_path / "synthetic workspace"
    header = ["response", *(f"x{column}" for column in range(12))]
    rows = [",".join(header)]
    for index in range(2000):
        values = [str(index / 1000), *(str((index * (2 * j + 1)) % 2003) for j in range(12))]
        rows.append(",".join(values))
    csv_bytes = ("\n".join(rows) + "\n").encode("utf-8")
    with TestClient(create_app(Settings(workspace_root=workspace))) as client:
        uploaded = client.post(
            "/api/v1/datasets", files={"file": ("synthetic.csv", csv_bytes, "text/csv")}
        )
        assert uploaded.status_code == 201
        confirmed = client.post(
            f"/api/v1/datasets/{uploaded.json()['dataset_id']}/confirm-parsing",
            json={
                "parsing": {
                    "kind": "delimited_text",
                    "encoding": "utf-8",
                    "delimiter": ",",
                    "quote_char": '"',
                    "decimal": ".",
                    "thousands": None,
                    "has_header": True,
                    "header_row": 1,
                    "data_start_row": 2,
                    "missing_tokens": [""],
                },
                "columns": [],
            },
        )
        assert confirmed.status_code == 201
        version = confirmed.json()
        source_files = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in workspace.rglob("*")
            if path.is_file()
            and path.suffix not in {".db", ".sqlite", ".sqlite3"}
            and path.name != ".workspace.lock"
            and not path.name.endswith(("-wal", "-shm"))
        }
        columns = [column["column_id"] for column in version["columns"]]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.gaussian_process",
                "method_version": METHOD_VERSIONS["regression.gaussian_process"],
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "response_column_id": columns[0],
                    "predictor_column_ids": columns[1:],
                    "resource_profile": "extended_exact",
                    "cv": {"method": "none"},
                    "noise_mode": "estimate",
                    "optimizer_restarts": 0,
                    "time_budget_seconds": 120,
                },
            },
        )
        assert response.status_code == 400, response.text
        assert response.json()["error"]["code"] == "gp_memory_budget_exceeded"
        with sqlite3.connect(metadata_db_path(workspace)) as database:
            assert database.execute("SELECT COUNT(*) FROM regression_models").fetchone()[0] == 0
            assert database.execute("SELECT COUNT(*) FROM analysis_artifacts").fetchone()[0] == 0
            runs = database.execute("SELECT status FROM analysis_runs").fetchall()
        # This inline runner commits the analysis record only with a complete result.
        assert runs == []
        assert client.get(f"/api/v1/dataset-versions/{version['version_id']}").status_code == 200
        assert all(
            path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest
            for path, digest in source_files.items()
        )
        assert not list(workspace.rglob("*.npz"))
