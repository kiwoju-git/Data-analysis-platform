import hashlib
import json
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.analyses.registry import METHODS, MODULES, analysis_method_catalog
from app.api.v1.schemas.analyses import (
    AnalysisProvenance,
    AnalysisResultEnvelope,
    AnalysisRunStatusResponse,
    AnalysisWarning,
    MethodAvailability,
)
from app.api.v1.schemas.common import JobReference, JobState, JobStatusResponse
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    AnalysisRunRecord,
    JobRecord,
    get_analysis_run_record,
    get_dataset_record,
    initialize_metadata_store,
    insert_analysis_run_record,
    insert_job_record,
)


def test_job_state_values_are_stable() -> None:
    assert [state.value for state in JobState] == [
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancel_requested",
        "cancelled",
    ]


def test_job_reference_serializes_uuid_and_state() -> None:
    job_id = uuid4()

    payload = JobReference(job_id=job_id, state=JobState.QUEUED).model_dump(mode="json")

    assert payload == {
        "job_id": str(job_id),
        "state": "queued",
    }
    assert UUID(payload["job_id"]) == job_id


def test_analysis_registry_module_and_method_ids_are_stable() -> None:
    assert [module.module_id.value for module in MODULES] == [
        "exploration",
        "hypothesis",
        "categorical",
        "regression",
        "quality",
        "doe",
    ]

    method_ids = [method.method_id for method in METHODS]
    assert len(method_ids) == 29
    assert len(set(method_ids)) == len(method_ids)
    assert method_ids[:4] == [
        "eda.descriptive",
        "eda.graphical_summary",
        "eda.normality",
        "eda.equal_variances",
    ]
    assert "regression.response_optimizer" in method_ids
    assert "doe.response_surface" in method_ids
    available_methods = [
        method.method_id
        for method in METHODS
        if method.availability == MethodAvailability.AVAILABLE
    ]
    assert available_methods == ["eda.descriptive"]


def test_analysis_method_catalog_response_groups_planned_and_disabled_methods() -> None:
    catalog = analysis_method_catalog()

    assert len(catalog.modules) == 6
    assert len(catalog.methods) == 29
    assert {method.availability.value for method in catalog.methods} == {
        "available",
        "planned",
        "disabled",
    }
    assert catalog.methods[0].method_id == "eda.descriptive"
    assert catalog.methods[0].availability == MethodAvailability.AVAILABLE
    assert [method.method_id for method in catalog.methods[:4]] == [
        "eda.descriptive",
        "eda.graphical_summary",
        "eda.normality",
        "eda.equal_variances",
    ]
    assert [method.module_id.value for method in catalog.methods[-2:]] == ["doe", "doe"]


def test_analysis_methods_api_exposes_only_descriptive_as_available_without_mock_results(
    tmp_path,
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.get("/api/v1/analysis-methods")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["modules"]) == 6
    assert len(payload["methods"]) == 29
    assert {method["availability"] for method in payload["methods"]} == {
        "available",
        "planned",
        "disabled",
    }
    available = [
        method["method_id"]
        for method in payload["methods"]
        if method["availability"] == "available"
    ]
    assert available == ["eda.descriptive"]
    assert "p_value" not in response.text
    assert "statistic" not in response.text


def test_analysis_run_rejects_planned_method_without_fake_result(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.graphical_summary",
                "method_version": "0.1.0",
                "dataset_version_id": str(uuid4()),
                "roles": {},
                "options": {},
            },
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analysis_method_not_available"
    assert "p_value" not in response.text
    assert "statistic" not in response.text
    assert "result" not in response.text


def test_analysis_run_executes_descriptive_statistics_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"alpha,beta\n1,10\n2,\n3,30\n4,40\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("sample.csv", content, "text/csv")},
        )
        dataset_id = upload_response.json()["dataset_id"]
        confirm_response = client.post(
            f"/api/v1/datasets/{dataset_id}/confirm-parsing",
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
                    "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
                },
                "columns": [],
            },
        )
        version = confirm_response.json()
        dataset_record = get_dataset_record(settings.workspace_root, dataset_id)
        assert dataset_record is not None
        (settings.workspace_root / dataset_record.stored_path).write_bytes(
            b"alpha,beta\n999,999\n999,999\n",
        )
        column_ids = [column["column_id"] for column in version["columns"]]

        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.descriptive",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "column_ids": column_ids,
                    "missing_policy": "available_case_by_column",
                },
            },
        )
        status_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["status"] == "succeeded"
    assert payload["method_id"] == "eda.descriptive"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 4
    assert payload["provenance"]["row_count_included"] == 4
    result = payload["result"]
    assert result["missing_policy"] == "available_case_by_column"
    assert result["quartile_method"] == "median_of_halves"

    alpha = result["columns"][0]
    assert alpha["display_name"] == "alpha"
    assert alpha["n_total"] == 4
    assert alpha["n_used"] == 4
    assert alpha["mean"] == 2.5
    assert alpha["q1"] == 1.5
    assert alpha["median"] == 2.5
    assert alpha["q3"] == 3.5

    beta = result["columns"][1]
    assert beta["display_name"] == "beta"
    assert beta["n_total"] == 4
    assert beta["n_used"] == 3
    assert beta["n_missing"] == 1
    assert beta["mean"] == 80 / 3
    assert beta["median"] == 30
    assert payload["warnings"] == []
    assert "p_value" not in response.text

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "succeeded"
    assert status_payload["config_schema_version"] == 2
    assert status_payload["result_available"] is True
    assert status_payload["artifact_count"] == 1

    assert record is not None
    config_payload = json.loads(record.config_json)
    assert config_payload["schema_version"] == 2
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 4
    assert row_snapshot["row_count_included"] == 4
    assert (
        payload["provenance"]["filter_snapshot_sha256"] == config_payload["filter_snapshot_sha256"]
    )
    assert payload["provenance"]["row_snapshot_sha256"] == row_snapshot["sha256"]

    row_snapshot_path = settings.workspace_root / row_snapshot["path"]
    row_snapshot_bytes = row_snapshot_path.read_bytes()
    assert row_snapshot["sha256"] == hashlib.sha256(row_snapshot_bytes).hexdigest()
    row_snapshot_payload = json.loads(row_snapshot_bytes.decode("utf-8"))
    assert row_snapshot_payload["artifact_kind"] == "analysis_row_snapshot"
    assert row_snapshot_payload["source_schema_hash"] == version["schema_hash"]
    assert (
        row_snapshot_payload["source_canonical_artifact"]["sha256"]
        == version["canonical_artifact"]["sha256"]
    )
    assert row_snapshot_payload["filter_snapshot"] == {
        "expression_version": 1,
        "conditions": [],
    }
    assert row_snapshot_payload["selection"] == {
        "kind": "all_rows",
        "row_count_total": 4,
        "row_count_included": 4,
        "row_count_excluded": 0,
    }
    assert "999" not in row_snapshot_bytes.decode("utf-8")


def test_analysis_run_rejects_filter_conditions_until_filter_engine_exists(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_numeric_dataset(client)
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.descriptive",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "filter_snapshot": {
                    "expression_version": 1,
                    "conditions": [
                        {
                            "column_id": version["columns"][0]["column_id"],
                            "operator": "gt",
                            "value": 1,
                        },
                    ],
                },
                "roles": {},
                "options": {
                    "column_ids": [version["columns"][0]["column_id"]],
                    "missing_policy": "available_case_by_column",
                },
            },
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analysis_filters_not_supported"
    assert not list(settings.workspace_root.glob("workspaces/analyses/*/row_snapshot.json"))


def test_analysis_result_api_returns_persisted_envelope_and_detects_checksum_mismatch(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_numeric_dataset(client)
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.descriptive",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "column_ids": [version["columns"][0]["column_id"]],
                    "missing_policy": "available_case_by_column",
                },
            },
        )
        analysis_id = response.json()["analysis_id"]
        result_response = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")

        record = get_analysis_run_record(settings.workspace_root, analysis_id)
        assert record is not None
        assert record.result_path is not None
        (settings.workspace_root / record.result_path).write_bytes(b'{"tampered":true}\n')
        tampered_response = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")

    assert response.status_code == 201
    assert result_response.status_code == 200
    assert result_response.json() == response.json()
    assert "result_path" not in result_response.text
    assert tampered_response.status_code == 409
    assert tampered_response.json()["error"]["code"] == "analysis_result_checksum_mismatch"
    assert record.result_path not in tampered_response.text


def test_dataset_schema_update_marks_existing_analysis_run_stale(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_numeric_dataset(client)
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.descriptive",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "column_ids": [version["columns"][0]["column_id"]],
                    "missing_policy": "available_case_by_column",
                },
            },
        )
        analysis_id = response.json()["analysis_id"]
        initial_status = client.get(f"/api/v1/analysis-runs/{analysis_id}")
        patch_response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema",
            json={
                "columns": [
                    {
                        "column_id": version["columns"][0]["column_id"],
                        "display_name": "측정값",
                        "measurement_level": "continuous",
                        "role": "feature",
                        "unit": "kg",
                    },
                ],
            },
        )
        stale_status = client.get(f"/api/v1/analysis-runs/{analysis_id}")

    assert response.status_code == 201
    assert initial_status.status_code == 200
    assert initial_status.json()["stale"] is False
    assert patch_response.status_code == 200
    assert stale_status.status_code == 200
    assert stale_status.json()["stale"] is True


def test_descriptive_result_file_is_removed_when_analysis_run_insert_fails(
    tmp_path,
    monkeypatch,
) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        version = _upload_confirmed_numeric_dataset(client)

        def fail_insert(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("metadata insert failed")

        monkeypatch.setattr(
            "app.services.analysis_runs.insert_analysis_run_record_with_artifacts",
            fail_insert,
        )

        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.descriptive",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "column_ids": [version["columns"][0]["column_id"]],
                    "missing_policy": "available_case_by_column",
                },
            },
        )

    assert response.status_code == 500
    assert not list(settings.workspace_root.glob("workspaces/analyses/*/result.json"))
    assert not list(settings.workspace_root.glob("workspaces/analyses/*/row_snapshot.json"))


def test_analysis_run_rejects_unknown_method(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "unknown.method",
                "method_version": "0.1.0",
                "dataset_version_id": str(uuid4()),
            },
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_method_not_found"


def test_analysis_run_status_and_cancel_skeleton_without_fake_result(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    initialize_metadata_store(settings.workspace_root)
    analysis_id = uuid4()
    insert_analysis_run_record(
        settings.workspace_root,
        AnalysisRunRecord(
            analysis_id=str(analysis_id),
            method_id="eda.descriptive",
            method_version="0.1.0",
            dataset_version_id=None,
            config_json='{"schema_version":1,"roles":{},"options":{}}',
            status="queued",
            result_path=None,
            result_sha256=None,
            stale=False,
            created_at="2026-06-24T00:00:00.000Z",
            updated_at="2026-06-24T00:00:00.000Z",
            completed_at=None,
            app_version="0.1.0",
        ),
    )

    with TestClient(create_app(settings)) as client:
        response = client.get(f"/api/v1/analysis-runs/{analysis_id}")
        cancel_response = client.delete(f"/api/v1/analysis-runs/{analysis_id}")

    assert response.status_code == 200
    payload = response.json()
    AnalysisRunStatusResponse.model_validate(payload)
    assert payload["status"] == "queued"
    assert payload["result_available"] is False
    assert payload["artifact_count"] == 0
    assert "result_path" not in response.text
    assert "p_value" not in response.text

    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["status"] == "cancel_requested"
    assert cancel_payload["result_available"] is False
    assert "result_path" not in cancel_response.text
    assert "p_value" not in cancel_response.text


def test_analysis_run_status_rejects_missing_run(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.get(f"/api/v1/analysis-runs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_run_not_found"


def test_job_status_and_cancel_skeleton(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    initialize_metadata_store(settings.workspace_root)
    job_id = uuid4()
    insert_job_record(
        settings.workspace_root,
        JobRecord(
            job_id=str(job_id),
            analysis_id=None,
            job_type="analysis",
            state="running",
            progress=0.5,
            cancel_requested=False,
            error_code=None,
            created_at="2026-06-24T00:00:00.000Z",
            updated_at="2026-06-24T00:00:00.000Z",
            completed_at=None,
        ),
    )

    with TestClient(create_app(settings)) as client:
        response = client.get(f"/api/v1/jobs/{job_id}")
        cancel_response = client.delete(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    payload = response.json()
    JobStatusResponse.model_validate(payload)
    assert payload["state"] == "running"
    assert payload["progress"] == 0.5
    assert payload["cancel_requested"] is False

    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["state"] == "cancel_requested"
    assert cancel_payload["cancel_requested"] is True


def test_job_status_rejects_missing_job(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.get(f"/api/v1/jobs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "job_not_found"


def _upload_confirmed_numeric_dataset(client: TestClient) -> dict[str, object]:
    upload_response = client.post(
        "/api/v1/datasets",
        files={"file": ("sample.csv", b"alpha,beta\n1,10\n2,20\n", "text/csv")},
    )
    assert upload_response.status_code == 201
    confirm_response = client.post(
        f"/api/v1/datasets/{upload_response.json()['dataset_id']}/confirm-parsing",
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
                "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
            },
            "columns": [],
        },
    )
    assert confirm_response.status_code == 201
    return confirm_response.json()


def test_analysis_result_envelope_allows_empty_result_only_as_schema_contract() -> None:
    analysis_id = uuid4()
    dataset_version_id = uuid4()
    envelope = AnalysisResultEnvelope(
        analysis_id=analysis_id,
        method_id="eda.descriptive",
        method_version="0.1.0",
        dataset_version_id=dataset_version_id,
        status="failed",
        warnings=[
            AnalysisWarning(
                code="not_available",
                severity="error",
                message="메서드를 아직 실행할 수 없습니다.",
            ),
        ],
        provenance=AnalysisProvenance(
            method_id="eda.descriptive",
            method_version="0.1.0",
            dataset_version_id=dataset_version_id,
            app_version="0.1.0",
        ),
        result=None,
    )

    payload = envelope.model_dump(mode="json")
    assert payload["result"] is None
    assert payload["analysis_id"] == str(analysis_id)
    assert payload["provenance"]["dataset_version_id"] == str(dataset_version_id)
