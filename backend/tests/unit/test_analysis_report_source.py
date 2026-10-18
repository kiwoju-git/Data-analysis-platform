import hashlib
import json
import os
import sqlite3
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from test_analysis_export_retention_api import _create_analysis
from test_attribute_control_phase_2_api import (
    _create_limit_set,
    _run_phase_2,
    _upload_confirmed_csv,
)

from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services import analysis_report_source as reader
from app.storage.metadata import (
    get_analysis_run_record,
    get_attribute_control_limit_set_record,
    metadata_db_path,
)


def _forbidden(*args, **kwargs):
    pytest.fail("report source reader must not open canonical rows or calculate")


def _guard_raw_reads(monkeypatch):
    for module in ("app.services.dataset_rows", "app.services.attribute_control_phase_2"):
        monkeypatch.setattr(f"{module}.verify_canonical_rows_artifact", _forbidden)
    monkeypatch.setattr("app.services.dataset_rows.iter_dataset_rows", _forbidden)
    monkeypatch.setattr(
        "app.services.attribute_control_limit_sets._validate_source_baseline", _forbidden
    )


def test_report_source_uses_frozen_snapshot_even_after_schema_changes(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        saved = _create_analysis(client)
        analysis_id = UUID(saved["analysis_id"])
        version = client.get(f"/api/v1/dataset-versions/{saved['dataset_version_id']}").json()
        columns = version["columns"]
        updated = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema",
            json={
                "expected_schema_hash": version["schema_hash"],
                "columns": [
                    {
                        "column_id": column["column_id"],
                        "display_name": column["display_name"],
                        "measurement_level": column["measurement_level"],
                        "role": column["role"],
                        "unit": "new unit",
                    }
                    for column in columns
                ],
            },
        )
        assert updated.status_code == 200, updated.text
        _guard_raw_reads(monkeypatch)
        stored = reader.load_analysis_report_source(settings, analysis_id)
        assert stored.envelope.model_dump(mode="json") == saved
        assert stored.record.stale is True
        assert stored.envelope.provenance.source_schema_hash != updated.json()["schema_hash"]


@pytest.mark.parametrize(
    "field,value", [("method_version", "wrong"), ("dataset_version_id", None), ("status", "failed")]
)
def test_report_source_rejects_owner_envelope_mismatch(tmp_path, monkeypatch, field, value):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        saved = _create_analysis(client)
        analysis_id = UUID(saved["analysis_id"])
        stored = reader.load_analysis_run_result_base(settings, analysis_id)
        monkeypatch.setattr(
            reader,
            "load_analysis_run_result_base",
            lambda *args: replace(stored, record=replace(stored.record, **{field: value})),
        )
        with pytest.raises(ApiError) as failure:
            reader.load_analysis_report_source(settings, analysis_id)
        assert failure.value.code == "analysis_report_source_dependency_mismatch"


def test_report_source_rejects_corrupt_selection_snapshot(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        saved = _create_analysis(client)
        record = get_analysis_run_record(tmp_path, saved["analysis_id"])
        reference = json.loads(record.config_json)["row_snapshot"]
        (tmp_path / reference["path"]).write_bytes(b"{}")
        with pytest.raises(ApiError) as failure:
            reader.load_analysis_report_source(settings, UUID(saved["analysis_id"]))
        assert failure.value.code == "analysis_report_source_dependency_mismatch"


def test_phase_two_report_validates_frozen_limit_and_result_without_raw_read(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limits = _create_limit_set(client, chart_type="p")
        target = _upload_confirmed_csv(client, b"defectives,denominator\n6,20\n1,40\n5,10\n")
        response = _run_phase_2(
            client,
            limits,
            target,
            count_id=target["columns"][0]["column_id"],
            denominator_id=target["columns"][1]["column_id"],
        )
        assert response.status_code == 201, response.text
        saved = response.json()
        record = get_analysis_run_record(tmp_path, saved["analysis_id"])
        before = (tmp_path / record.result_path).read_bytes()
        _guard_raw_reads(monkeypatch)
        stored = reader.load_analysis_report_source(settings, UUID(saved["analysis_id"]))
        assert stored.envelope.model_dump(mode="json") == saved
        assert hashlib.sha256(before).hexdigest() == record.result_sha256
        assert (tmp_path / record.result_path).read_bytes() == before


def _phase_two(client):
    limits = _create_limit_set(client, chart_type="p")
    target = _upload_confirmed_csv(client, b"defectives,denominator\n6,20\n1,40\n5,10\n")
    response = _run_phase_2(
        client,
        limits,
        target,
        count_id=target["columns"][0]["column_id"],
        denominator_id=target["columns"][1]["column_id"],
    )
    assert response.status_code == 201, response.text
    return limits, target, response.json()


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_phase_two_capability_and_html_preserve_frozen_bytes_without_recalculation(
    tmp_path, monkeypatch, locale
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limits, _, saved = _phase_two(client)
        analysis_id = saved["analysis_id"]
        paths = []
        for owner in (analysis_id, limits["source_analysis_id"]):
            record = get_analysis_run_record(tmp_path, owner)
            paths.extend(
                [record.result_path, json.loads(record.config_json)["row_snapshot"]["path"]]
            )
        asset = get_attribute_control_limit_set_record(tmp_path, limits["limit_set_id"])
        paths.append(asset.asset_path)
        before = {path: (tmp_path / path).read_bytes() for path in paths}
        _guard_raw_reads(monkeypatch)
        for name in (
            "calculate_attribute_control_chart",
            "calculate_attribute_control_chart_phase_2",
        ):
            monkeypatch.setattr(
                f"app.services.analysis_runner_attribute_control_chart.{name}", _forbidden
            )
        monkeypatch.setattr(
            "app.services.analysis_run_exports._analysis_result_csv_rows", _forbidden
        )
        capability = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/report-capability", params={"locale": locale}
        )
        assert capability.status_code == 200, capability.text
        report = capability.json()
        assert report["source_validation"] == "stored_dependencies_only"
        assert report["report_level"] == "full"
        assert report["source_result_sha256"] == hashlib.sha256(before[paths[0]]).hexdigest()
        created = client.post(
            f"/api/v1/analysis-runs/{analysis_id}/exports/html",
            json={
                "locale": locale,
                "expected_source_result_sha256": report["source_result_sha256"],
            },
        )
        assert created.status_code == 201, created.text
        downloaded = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/{created.json()['export_id']}/download"
        )
        assert downloaded.status_code == 200, downloaded.text
        body = downloaded.text.split("<details", 1)[0]
        assert 'data-report-section="attribute_chart"' in body
        assert "<svg" in body and "UCL" in body and "LCL" in body
        assert "phase_2_frozen_three_sigma" in body
        assert limits["limit_set_id"] in body
        assert ("품질 분석 요약" if locale == "ko" else "Quality Analysis Summary") in body
        assert {path: (tmp_path / path).read_bytes() for path in paths} == before


def test_phase_two_report_rejects_corrupt_frozen_asset_before_render(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limits, _, saved = _phase_two(client)
        asset = get_attribute_control_limit_set_record(tmp_path, limits["limit_set_id"])
        (tmp_path / asset.asset_path).write_bytes(b"{}")
        _guard_raw_reads(monkeypatch)
        response = client.get(f"/api/v1/analysis-runs/{saved['analysis_id']}/report-capability")
        assert response.status_code == 409, response.text
        assert (
            response.json()["error"]["code"]
            == "attribute_control_chart_limit_set_checksum_mismatch"
        )
        assert (
            client.get(f"/api/v1/analysis-runs/{saved['analysis_id']}/exports").json()["exports"]
            == []
        )


@pytest.mark.parametrize("phase", [None, "phase_1"])
def test_phase_two_report_rejects_rehashed_phase_mismatch(tmp_path, monkeypatch, phase):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        _, _, saved = _phase_two(client)
        record = get_analysis_run_record(tmp_path, saved["analysis_id"])
        envelope = json.loads((tmp_path / record.result_path).read_bytes())
        if phase is None:
            del envelope["result"]["phase"]
        else:
            envelope["result"]["phase"] = phase
        encoded = json.dumps(envelope, sort_keys=True, ensure_ascii=False).encode("utf-8")
        (tmp_path / record.result_path).write_bytes(encoded)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_runs SET result_sha256=? WHERE analysis_id=?",
                (hashlib.sha256(encoded).hexdigest(), saved["analysis_id"]),
            )
        _guard_raw_reads(monkeypatch)
        response = client.get(f"/api/v1/analysis-runs/{saved['analysis_id']}/report-capability")
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "analysis_report_source_dependency_mismatch"


def _rewrite_config(root, analysis_id, change):
    record = get_analysis_run_record(root, analysis_id)
    config = json.loads(record.config_json)
    change(config)
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.execute(
            "UPDATE analysis_runs SET config_json=? WHERE analysis_id=?",
            (
                json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
                analysis_id,
            ),
        )


def _rewrite_snapshot_and_hashes(root, analysis_id, change):
    """Corrupt a synthetic snapshot but keep byte hashes internally consistent."""
    record = get_analysis_run_record(root, analysis_id)
    config = json.loads(record.config_json)
    reference = config["row_snapshot"]
    snapshot = json.loads((root / reference["path"]).read_bytes())
    change(snapshot)
    snapshot_bytes = json.dumps(
        snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    new_hash = hashlib.sha256(snapshot_bytes).hexdigest()
    (root / reference["path"]).write_bytes(snapshot_bytes)
    reference["sha256"] = new_hash
    envelope = json.loads((root / record.result_path).read_bytes())
    envelope["provenance"]["row_snapshot_sha256"] = new_hash
    result_bytes = json.dumps(
        envelope, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    (root / record.result_path).write_bytes(result_bytes)
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.execute(
            "UPDATE analysis_artifacts SET sha256=? WHERE artifact_id=?",
            (new_hash, reference["artifact_id"]),
        )
        connection.execute(
            "UPDATE analysis_runs SET config_json=?, result_sha256=? WHERE analysis_id=?",
            (
                json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
                hashlib.sha256(result_bytes).hexdigest(),
                analysis_id,
            ),
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda snapshot: snapshot.update(artifact_schema_version=999),
        lambda snapshot: snapshot.update(artifact_schema_version=True),
        lambda snapshot: snapshot.update(row_identity={"kind": "canonical_row_index", "base": 1}),
        lambda snapshot: snapshot.update(
            row_identity={"kind": "canonical_row_index", "base": False}
        ),
        lambda snapshot: snapshot["selection"].update(kind="unexpected"),
        lambda snapshot: snapshot["selection"].update(row_count_excluded=99),
        lambda snapshot: snapshot["source_canonical_artifact"].update(kind="raw_upload"),
        lambda snapshot: snapshot["filter_snapshot"].update(expression_version=999),
    ],
)
def test_report_source_rejects_resigned_snapshot_semantic_corruption(tmp_path, monkeypatch, change):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        saved = _create_analysis(client)
        _rewrite_snapshot_and_hashes(tmp_path, saved["analysis_id"], change)
        _guard_raw_reads(monkeypatch)
        with pytest.raises(ApiError) as failure:
            reader.load_analysis_report_source(settings, UUID(saved["analysis_id"]))
        assert failure.value.code == "analysis_report_source_dependency_mismatch"


@pytest.mark.parametrize(
    "change",
    [
        lambda config: config.update(method_id="wrong.owner"),
        lambda config: config["row_snapshot"].update(path="workspaces/other/snapshot.json"),
        lambda config: config["filter_snapshot"].update(expression_version=999),
    ],
)
def test_report_source_rejects_config_relationship_corruption(tmp_path, change):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        saved = _create_analysis(client)
        _rewrite_config(tmp_path, saved["analysis_id"], change)
        with pytest.raises(ApiError) as failure:
            reader.load_analysis_report_source(settings, UUID(saved["analysis_id"]))
        assert failure.value.code == "analysis_report_source_dependency_mismatch"


def test_phase_two_report_keeps_frozen_sources_when_both_current_schemas_change(
    tmp_path, monkeypatch
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limits, target, saved = _phase_two(client)
        record = get_analysis_run_record(tmp_path, saved["analysis_id"])
        before = (tmp_path / record.result_path).read_bytes()
        for version_id in (limits["source_dataset_version_id"], target["version_id"]):
            version = client.get(f"/api/v1/dataset-versions/{version_id}").json()
            response = client.patch(
                f"/api/v1/dataset-versions/{version_id}/schema",
                json={
                    "expected_schema_hash": version["schema_hash"],
                    "columns": [
                        {
                            "column_id": column["column_id"],
                            "display_name": column["display_name"],
                            "measurement_level": column["measurement_level"],
                            "role": column["role"],
                            "unit": "new current unit",
                        }
                        for column in version["columns"]
                    ],
                },
            )
            assert response.status_code == 200, response.text
        _guard_raw_reads(monkeypatch)
        stored = reader.load_analysis_report_source(settings, UUID(saved["analysis_id"]))
        assert stored.record.stale is True
        assert stored.envelope.model_dump(mode="json") == saved
        assert (tmp_path / record.result_path).read_bytes() == before


def test_phase_two_report_rejects_corrupt_baseline_selection_without_raw_read(
    tmp_path, monkeypatch
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limits, _, saved = _phase_two(client)
        source = get_analysis_run_record(tmp_path, limits["source_analysis_id"])
        reference = json.loads(source.config_json)["row_snapshot"]
        (tmp_path / reference["path"]).write_bytes(b"{}")
        _guard_raw_reads(monkeypatch)
        with pytest.raises(ApiError) as failure:
            reader.load_analysis_report_source(settings, UUID(saved["analysis_id"]))
        assert failure.value.code == "analysis_report_source_dependency_mismatch"


def test_phase_two_report_validates_baseline_envelope_owner(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limits, _, saved = _phase_two(client)
        original = reader.load_analysis_run_result_base

        def tampered(settings, analysis_id):
            stored = original(settings, analysis_id)
            if str(analysis_id) == limits["source_analysis_id"]:
                return replace(
                    stored, envelope=stored.envelope.model_copy(update={"method_version": "wrong"})
                )
            return stored

        monkeypatch.setattr(reader, "load_analysis_run_result_base", tampered)
        _guard_raw_reads(monkeypatch)
        with pytest.raises(ApiError) as failure:
            reader.load_analysis_report_source(settings, UUID(saved["analysis_id"]))
        assert failure.value.code == "analysis_report_source_dependency_mismatch"


@pytest.mark.parametrize("target", ["result", "snapshot"])
def test_report_source_rejects_actual_symlink_before_read(tmp_path, monkeypatch, target):
    settings = Settings(workspace_root=tmp_path / "workspace")
    with TestClient(create_app(settings)) as client:
        saved = _create_analysis(client)
        record = get_analysis_run_record(settings.workspace_root, saved["analysis_id"])
        path = settings.workspace_root / (
            record.result_path
            if target == "result"
            else json.loads(record.config_json)["row_snapshot"]["path"]
        )
        outside = tmp_path / "outside.json"
        outside.write_bytes(path.read_bytes())
        probe = tmp_path / "probe-link"
        try:
            probe.symlink_to(outside)
        except OSError as exc:
            if os.name == "nt" and exc.winerror == 1314:
                pytest.skip("Windows account lacks symlink privilege")
            raise
        probe.unlink()
        path.unlink()
        path.symlink_to(outside)
        original_read = Path.read_bytes
        blocked = path

        def guarded_read(candidate):
            assert candidate != outside and candidate != blocked
            return original_read(candidate)

        monkeypatch.setattr(Path, "read_bytes", guarded_read)
        with pytest.raises(ApiError) as failure:
            reader.load_analysis_report_source(settings, UUID(saved["analysis_id"]))
        assert failure.value.code == "analysis_report_source_dependency_mismatch"


@pytest.mark.parametrize(
    "selection,valid",
    [
        (
            {
                "kind": "all_rows",
                "row_count_total": 3,
                "row_count_included": 3,
                "row_count_excluded": 0,
            },
            True,
        ),
        (
            {
                "kind": "row_ranges",
                "row_count_total": 5,
                "row_count_included": 3,
                "row_count_excluded": 2,
                "row_ranges": [{"start": 0, "end": 1}, {"start": 3, "end": 5}],
            },
            True,
        ),
        (
            {
                "kind": "row_ranges",
                "row_count_total": 5,
                "row_count_included": 3,
                "row_count_excluded": 2,
                "row_ranges": [{"start": 0, "end": 2}, {"start": 1, "end": 2}],
            },
            False,
        ),
        (
            {
                "kind": "row_ranges",
                "row_count_total": 5,
                "row_count_included": 3,
                "row_count_excluded": 2,
                "row_ranges": [{"start": 3, "end": 6}],
            },
            False,
        ),
        (
            {
                "kind": "all_rows",
                "row_count_total": True,
                "row_count_included": 1,
                "row_count_excluded": 0,
            },
            False,
        ),
    ],
)
def test_selection_validation_does_not_expand_or_read_rows(selection, valid):
    assert reader._selection_is_valid(selection) is valid
