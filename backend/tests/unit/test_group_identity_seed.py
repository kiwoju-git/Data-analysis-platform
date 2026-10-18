"""The archive fixture provisioner only inserts new BASE-shaped stored records."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import get_analysis_run_record

ROOT = Path(__file__).parents[3]
FIXTURE = ROOT / "backend/tests/reference/fixtures/group_identity_legacy_base.json"
SPEC = importlib.util.spec_from_file_location(
    "seed_pilot_legacy", ROOT / "tests/e2e/seed_pilot_legacy.py"
)
assert SPEC is not None and SPEC.loader is not None
SEED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEED)


def test_seed_rejects_existing_workspace_without_modification(tmp_path: Path) -> None:
    sentinel = tmp_path / "user-data.txt"
    sentinel.write_bytes(b"preserve existing data")
    with pytest.raises(ValueError, match="legacy_seed_requires_empty_workspace"):
        SEED.seed_legacy(tmp_path, FIXTURE)
    assert sentinel.read_bytes() == b"preserve existing data"
    assert list(tmp_path.iterdir()) == [sentinel]


def test_seed_rejects_fixture_digest_before_workspace_creation(tmp_path: Path) -> None:
    fixture = json.loads(FIXTURE.read_bytes())
    fixture["cases"][0]["result"]["n_used"] += 1
    modified = tmp_path / "invalid.json"
    modified.write_text(json.dumps(fixture), encoding="utf-8")
    workspace = tmp_path / "workspace"
    with pytest.raises(ValueError, match="legacy_seed_fixture_digest_mismatch"):
        SEED.seed_legacy(workspace, modified)
    assert not workspace.exists()


def test_seeded_base_results_restore_and_report_without_payload_changes(tmp_path: Path) -> None:
    workspace = tmp_path / "new-legacy-workspace"
    receipt = SEED.seed_legacy(workspace, FIXTURE)
    assert receipt["status"] == "seeded_new_workspace"
    assert receipt["existing_records_modified"] is False
    assert receipt["analysis_calculations_executed"] == 0
    fixture = json.loads(FIXTURE.read_bytes())
    with TestClient(create_app(Settings(workspace_root=workspace))) as client:
        for case, expected in zip(receipt["cases"], fixture["cases"], strict=True):
            analysis_id = case["analysis_id"]
            record = get_analysis_run_record(workspace, analysis_id)
            assert record is not None and record.result_path is not None
            original = (workspace / record.result_path).read_bytes()
            assert hashlib.sha256(original).hexdigest() == case["artifact_file_sha256"]
            restored = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")
            assert restored.status_code == 200
            assert restored.json()["result"] == expected["result"]
            assert restored.json()["method_version"] == expected["method_version"]
            for locale in ("ko", "en"):
                report = client.post(
                    f"/api/v1/analysis-runs/{analysis_id}/exports/html", json={"locale": locale}
                )
                assert report.status_code == 201, report.text
            assert (workspace / record.result_path).read_bytes() == original
            assert (
                hashlib.sha256(SEED.canonical_payload(restored.json()["result"])).hexdigest()
                == case["result_payload_sha256"]
            )
