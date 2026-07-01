import hashlib
import json
import sqlite3
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHODS, MODULES, analysis_method_catalog
from app.api.v1.schemas.analyses import (
    AnalysisProvenance,
    AnalysisResultEnvelope,
    AnalysisRunStatusResponse,
    AnalysisWarning,
    MethodAvailability,
    RegressionPredictionPreflightResponse,
    RegressionPredictionResponse,
)
from app.api.v1.schemas.common import JobReference, JobState, JobStatusResponse
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    METADATA_DB_RELATIVE_PATH,
    AnalysisRunRecord,
    JobRecord,
    get_analysis_run_record,
    get_dataset_record,
    get_regression_model_record,
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
    assert available_methods == [
        "eda.descriptive",
        "eda.graphical_summary",
        "eda.normality",
        "eda.equal_variances",
        "hypothesis.one_sample_t",
        "hypothesis.paired_t",
        "hypothesis.two_sample_t",
        "hypothesis.one_way_anova",
        "hypothesis.equivalence_tost",
        "hypothesis.one_sample_wilcoxon",
        "hypothesis.mann_whitney",
        "hypothesis.kruskal_wallis",
        "categorical.one_proportion",
        "categorical.two_proportion",
        "categorical.chi_square_association",
        "regression.pearson",
        "regression.xy_correlation",
        "regression.linear_model",
    ]


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
    normality = next(method for method in catalog.methods if method.method_id == "eda.normality")
    equal_variances = next(
        method for method in catalog.methods if method.method_id == "eda.equal_variances"
    )
    assert normality.availability == MethodAvailability.AVAILABLE
    assert normality.disabled_reason is None
    assert equal_variances.availability == MethodAvailability.AVAILABLE
    assert equal_variances.disabled_reason is None
    one_sample_t = next(
        method for method in catalog.methods if method.method_id == "hypothesis.one_sample_t"
    )
    assert one_sample_t.availability == MethodAvailability.AVAILABLE
    assert one_sample_t.disabled_reason is None
    paired_t = next(
        method for method in catalog.methods if method.method_id == "hypothesis.paired_t"
    )
    assert paired_t.availability == MethodAvailability.AVAILABLE
    assert paired_t.disabled_reason is None
    two_sample_t = next(
        method for method in catalog.methods if method.method_id == "hypothesis.two_sample_t"
    )
    assert two_sample_t.availability == MethodAvailability.AVAILABLE
    assert two_sample_t.disabled_reason is None
    one_way_anova = next(
        method for method in catalog.methods if method.method_id == "hypothesis.one_way_anova"
    )
    assert one_way_anova.availability == MethodAvailability.AVAILABLE
    assert one_way_anova.disabled_reason is None
    equivalence_tost = next(
        method for method in catalog.methods if method.method_id == "hypothesis.equivalence_tost"
    )
    assert equivalence_tost.availability == MethodAvailability.AVAILABLE
    assert equivalence_tost.disabled_reason is None
    one_sample_wilcoxon = next(
        method for method in catalog.methods if method.method_id == "hypothesis.one_sample_wilcoxon"
    )
    assert one_sample_wilcoxon.availability == MethodAvailability.AVAILABLE
    assert one_sample_wilcoxon.disabled_reason is None
    mann_whitney = next(
        method for method in catalog.methods if method.method_id == "hypothesis.mann_whitney"
    )
    assert mann_whitney.availability == MethodAvailability.AVAILABLE
    assert mann_whitney.disabled_reason is None
    kruskal_wallis = next(
        method for method in catalog.methods if method.method_id == "hypothesis.kruskal_wallis"
    )
    assert kruskal_wallis.availability == MethodAvailability.AVAILABLE
    assert kruskal_wallis.disabled_reason is None
    one_proportion = next(
        method for method in catalog.methods if method.method_id == "categorical.one_proportion"
    )
    assert one_proportion.availability == MethodAvailability.AVAILABLE
    assert one_proportion.disabled_reason is None
    two_proportion = next(
        method for method in catalog.methods if method.method_id == "categorical.two_proportion"
    )
    assert two_proportion.availability == MethodAvailability.AVAILABLE
    assert two_proportion.disabled_reason is None
    chi_square = next(
        method
        for method in catalog.methods
        if method.method_id == "categorical.chi_square_association"
    )
    assert chi_square.availability == MethodAvailability.AVAILABLE
    assert chi_square.disabled_reason is None
    pearson = next(method for method in catalog.methods if method.method_id == "regression.pearson")
    assert pearson.availability == MethodAvailability.AVAILABLE
    assert pearson.disabled_reason is None
    xy_correlation = next(
        method for method in catalog.methods if method.method_id == "regression.xy_correlation"
    )
    assert xy_correlation.availability == MethodAvailability.AVAILABLE
    assert xy_correlation.disabled_reason is None
    linear_model = next(
        method for method in catalog.methods if method.method_id == "regression.linear_model"
    )
    assert linear_model.availability == MethodAvailability.AVAILABLE
    assert linear_model.disabled_reason is None
    assert [method.module_id.value for method in catalog.methods[-2:]] == ["doe", "doe"]


def test_analysis_methods_api_exposes_only_real_methods_as_available_without_mock_results(
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
    assert available == [
        "eda.descriptive",
        "eda.graphical_summary",
        "eda.normality",
        "eda.equal_variances",
        "hypothesis.one_sample_t",
        "hypothesis.paired_t",
        "hypothesis.two_sample_t",
        "hypothesis.one_way_anova",
        "hypothesis.equivalence_tost",
        "hypothesis.one_sample_wilcoxon",
        "hypothesis.mann_whitney",
        "hypothesis.kruskal_wallis",
        "categorical.one_proportion",
        "categorical.two_proportion",
        "categorical.chi_square_association",
        "regression.pearson",
        "regression.xy_correlation",
        "regression.linear_model",
    ]
    normality = next(
        method for method in payload["methods"] if method["method_id"] == "eda.normality"
    )
    assert normality["availability"] == "available"
    assert normality["disabled_reason"] is None
    assert "p_value" not in response.text
    assert "statistic" not in response.text


def test_analysis_run_rejects_remaining_planned_or_disabled_method_without_fake_result(
    tmp_path,
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.predict",
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


def test_analysis_run_executes_graphical_summary_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_numeric_dataset(client)
        column_id = version["columns"][0]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.graphical_summary",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "column_ids": [column_id],
                    "histogram_bin_count": 2,
                    "point_limit": 10,
                },
            },
        )
        status_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}",
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "eda.graphical_summary"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 2
    assert payload["provenance"]["row_count_included"] == 2
    assert payload["warnings"] == []
    result = payload["result"]
    assert result["summary_type"] == "graphical_summary"
    assert result["histogram_method"] == "fixed_count"
    column = result["columns"][0]
    assert column["display_name"] == "alpha"
    assert column["n_total"] == 2
    assert column["n_used"] == 2
    assert column["histogram"]["bin_count"] == 2
    assert [bin_payload["count"] for bin_payload in column["histogram"]["bins"]] == [1, 1]
    assert column["boxplot"]["lower_whisker"] == 1.0
    assert column["boxplot"]["median"] == 1.5
    assert column["boxplot"]["upper_whisker"] == 2.0
    assert column["qq_plot"]["point_count"] == 2
    assert column["ecdf"]["points"][-1] == {"x": 2.0, "probability": 1.0}
    assert "p_value" not in response.text

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "succeeded"
    assert status_payload["config_schema_version"] == 2
    assert status_payload["result_available"] is True
    assert status_payload["artifact_count"] == 1
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    assert record.result_path is not None
    config_payload = json.loads(record.config_json)
    assert config_payload["schema_version"] == 2
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 2
    assert row_snapshot["row_count_included"] == 2
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
        "row_count_total": 2,
        "row_count_included": 2,
        "row_count_excluded": 0,
    }


def test_analysis_run_executes_normality_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"alpha,beta\n"
        b"-1.5,10\n-0.9,20\n-0.4,30\n-0.1,40\n0,50\n"
        b"0.2,60\n0.5,70\n0.8,80\n1.1,90\n1.6,100\n"
    )

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("normal.csv", content, "text/csv")},
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
        column_id = version["columns"][0]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.normality",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "column_ids": [column_id],
                    "alpha": 0.05,
                    "missing_policy": "available_case_by_column",
                    "qq_point_limit": 10,
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "eda.normality"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 10
    assert payload["provenance"]["row_count_included"] == 10
    assert payload["warnings"] == [
        {
            "code": "normality_not_method_switch",
            "severity": "info",
            "message": "정규성 검정 결과만으로 후속 모수/비모수 검정을 자동 전환하지 않습니다.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "normality_test"
    assert result["alpha"] == 0.05
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    column = result["columns"][0]
    assert column["display_name"] == "alpha"
    assert column["n_total"] == 10
    assert column["n_used"] == 10
    assert column["mean"] == pytest.approx(0.13)
    assert column["shapiro_wilk"]["computed"] is True
    assert column["shapiro_wilk"]["statistic"] == 0.9924829130989719
    assert column["shapiro_wilk"]["p_value"] == 0.9989582346078788
    assert column["anderson_darling"]["computed"] is True
    assert column["anderson_darling"]["decision_at_alpha"] == {
        "alpha": 0.05,
        "critical_value": 0.684,
        "reject_normality": False,
        "method": "tabulated_critical_value",
    }
    assert column["qq_plot"]["point_count"] == 10
    assert column["warnings"] == []
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 10
    assert row_snapshot["row_count_included"] == 10


def test_analysis_run_executes_equal_variances_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"response,group\n" b"8,A\n9,A\n10,A\n" b"11,B\n13,B\n15,B\n" b"7,C\n8,C\n12,C\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("equal-variances.csv", content, "text/csv")},
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
            b"response,group\n999,A\n999,B\n999,C\n",
        )
        response_column_id = version["columns"][0]["column_id"]
        group_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.equal_variances",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "group": group_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "group_column_id": group_column_id,
                    "alpha": 0.05,
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "eda.equal_variances"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 9
    assert payload["provenance"]["row_count_included"] == 9
    assert payload["warnings"] == [
        {
            "code": "equal_variances_not_method_switch",
            "severity": "info",
            "message": (
                "등분산 검정 결과만으로 후속 pooled/Welch 또는 ANOVA 방식을 "
                "자동 전환하지 않습니다."
            ),
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "equal_variances_test"
    assert result["missing_policy"] == "complete_case"
    assert result["alpha"] == 0.05
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["response"]["display_name"] == "response"
    assert result["group"]["display_name"] == "group"
    assert result["n_total"] == 9
    assert result["n_used"] == 9
    assert result["group_count"] == 3
    assert [group["group_label"] for group in result["groups"]] == ["A", "B", "C"]
    assert [group["n"] for group in result["groups"]] == [3, 3, 3]
    tests = {test["method"]: test for test in result["tests"]}
    assert tests["brown_forsythe"]["computed"] is True
    assert tests["brown_forsythe"]["statistic"] == pytest.approx(
        0.388888888888889,
        abs=1e-12,
    )
    assert tests["brown_forsythe"]["p_value"] == pytest.approx(
        0.6937320744908164,
        abs=1e-12,
    )
    assert tests["levene_mean"]["computed"] is True
    assert tests["levene_mean"]["statistic"] == pytest.approx(1.5, abs=1e-12)
    assert tests["levene_mean"]["p_value"] == pytest.approx(
        0.2962962962962963,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 9
    assert row_snapshot["row_count_included"] == 9


def test_analysis_run_executes_two_sample_t_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"response,group\n"
        b"5.1,A\n5.8,A\n6.2,A\n6.4,A\n5.9,A\n"
        b"4.2,B\n4.8,B\n5.0,B\n5.1,B\n4.7,B\n4.9,B\n"
    )

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("two-sample.csv", content, "text/csv")},
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
            b"response,group\n999,A\n999,B\n",
        )
        response_column_id = version["columns"][0]["column_id"]
        group_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "hypothesis.two_sample_t",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "group": group_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "group_column_id": group_column_id,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "alternative": "two_sided",
                    "variance_assumption": "welch",
                    "null_difference": 0,
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "hypothesis.two_sample_t"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 11
    assert payload["provenance"]["row_count_included"] == 11
    assert payload["warnings"] == [
        {
            "code": "two_sample_t_independence_assumption",
            "severity": "info",
            "message": "독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
        },
        {
            "code": "two_sample_t_not_auto_switched",
            "severity": "info",
            "message": "정규성/등분산 진단 결과로 2-표본 t-검정 방식을 자동 전환하지 않습니다.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "two_sample_t_test"
    assert result["method"] == "welch_two_sample_t"
    assert result["variance_assumption"] == "welch"
    assert result["missing_policy"] == "complete_case"
    assert result["alternative"] == "two_sided"
    assert result["alpha"] == 0.05
    assert result["confidence_level"] == 0.95
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 11
    assert result["n_used"] == 11
    assert [group["group_label"] for group in result["groups"]] == ["A", "B"]
    assert [group["n"] for group in result["groups"]] == [5, 6]
    contrast = result["contrast"]
    assert contrast["group_1_label"] == "A"
    assert contrast["group_2_label"] == "B"
    assert contrast["estimate"] == pytest.approx(1.0966666666666667, abs=1e-12)
    assert contrast["standard_error"] == pytest.approx(0.25757415329268674, abs=1e-12)
    assert contrast["df"] == pytest.approx(6.594008456673691, abs=1e-12)
    assert contrast["statistic"] == pytest.approx(4.257673577288254, abs=1e-12)
    assert contrast["p_value"] == pytest.approx(0.004305516567486469, abs=1e-12)
    assert contrast["confidence_interval"]["lower"] == pytest.approx(
        0.47991554689372173,
        abs=1e-12,
    )
    assert contrast["confidence_interval"]["upper"] == pytest.approx(
        1.7134177864396116,
        abs=1e-12,
    )
    assert contrast["effect_size"]["hedges_g"] == pytest.approx(
        2.4590290342918495,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 11
    assert row_snapshot["row_count_included"] == 11


def test_analysis_run_executes_one_way_anova_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"response,group\n"
        b"8,A\n"
        b"9,A\n"
        b"6,A\n"
        b"7,A\n"
        b"10,B\n"
        b"12,B\n"
        b"9,B\n"
        b"11,B\n"
        b"13,C\n"
        b"14,C\n"
        b"12,C\n"
        b"15,C\n"
    )

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("one-way-anova.csv", content, "text/csv")},
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
            b"response,group\n1,A\n",
        )
        response_column_id = version["columns"][0]["column_id"]
        group_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "hypothesis.one_way_anova",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "group": group_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "group_column_id": group_column_id,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "anova_type": "standard",
                    "posthoc_method": "tukey_kramer",
                    "posthoc_policy": "after_significant",
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "hypothesis.one_way_anova"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 12
    assert payload["provenance"]["row_count_included"] == 12
    assert [warning["code"] for warning in payload["warnings"]] == [
        "one_way_anova_independence_assumption",
        "one_way_anova_normality_assumption",
        "one_way_anova_equal_variance_assumption",
        "one_way_anova_not_auto_switched",
        "tukey_kramer_after_standard_anova",
        "small_group_size",
    ]
    result = payload["result"]
    assert result["summary_type"] == "one_way_anova"
    assert result["method"] == "standard_one_way_anova"
    assert result["anova_type"] == "standard"
    assert result["posthoc_method"] == "tukey_kramer"
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 12
    assert result["n_used"] == 12
    assert [group["group_label"] for group in result["groups"]] == ["A", "B", "C"]
    assert [group["mean"] for group in result["groups"]] == [7.5, 10.5, 13.5]
    assert result["anova_table"]["ss_between"] == pytest.approx(72.0, abs=1e-12)
    assert result["anova_table"]["ss_within"] == pytest.approx(15.0, abs=1e-12)
    assert result["test"]["f_statistic"] == pytest.approx(21.6, abs=1e-12)
    assert result["test"]["p_value"] == pytest.approx(0.000366922233939463, abs=1e-12)
    assert result["test"]["effect_size"]["eta_squared"] == pytest.approx(
        0.8275862068965517,
        abs=1e-12,
    )
    assert result["test"]["effect_size"]["omega_squared"] == pytest.approx(
        0.7744360902255639,
        abs=1e-12,
    )
    assert result["posthoc"]["performed"] is True
    assert len(result["posthoc"]["comparisons"]) == 3
    assert result["posthoc"]["comparisons"][0]["adjusted_p_value"] == pytest.approx(
        0.0231730044120374,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 12
    assert row_snapshot["row_count_included"] == 12


def test_analysis_run_executes_mann_whitney_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"response,group\n" b"7,A\n9,A\n10,A\n12,A\n" b"3,B\n5,B\n6,B\n8,B\n11,B\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("mann-whitney.csv", content, "text/csv")},
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
            b"response,group\n999,A\n999,B\n",
        )
        response_column_id = version["columns"][0]["column_id"]
        group_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "hypothesis.mann_whitney",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "group": group_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "group_column_id": group_column_id,
                    "alpha": 0.05,
                    "alternative": "two_sided",
                    "method": "exact",
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "hypothesis.mann_whitney"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 9
    assert payload["provenance"]["row_count_included"] == 9
    assert payload["warnings"] == [
        {
            "code": "mann_whitney_independence_assumption",
            "severity": "info",
            "message": "독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
        },
        {
            "code": "mann_whitney_not_median_test",
            "severity": "info",
            "message": "Mann-Whitney U 결과를 단순 중앙값 차이 검정으로 해석하지 않습니다.",
        },
        {
            "code": "small_group_size",
            "severity": "info",
            "message": "그룹 표본 수가 작아 exact/asymptotic 방식과 설계를 함께 확인하세요.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "mann_whitney_u_test"
    assert result["method"] == "mann_whitney_u"
    assert result["missing_policy"] == "complete_case"
    assert result["alternative"] == "two_sided"
    assert result["alpha"] == 0.05
    assert result["requested_method"] == "exact"
    assert result["resolved_method"] == "exact"
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 9
    assert result["n_used"] == 9
    assert [group["group_label"] for group in result["groups"]] == ["A", "B"]
    assert [group["n"] for group in result["groups"]] == [4, 5]
    assert [group["rank_sum"] for group in result["groups"]] == [26.0, 19.0]
    test = result["test"]
    assert test["group_1_label"] == "A"
    assert test["group_2_label"] == "B"
    assert test["u_statistic"] == 16.0
    assert test["p_value"] == pytest.approx(0.19047619047619047, abs=1e-12)
    assert test["effect_size"]["rank_biserial"] == pytest.approx(
        0.6000000000000001,
        abs=1e-12,
    )
    assert test["effect_size"]["common_language_probability"] == 0.8
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 9
    assert row_snapshot["row_count_included"] == 9


def test_analysis_run_executes_one_sample_t_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"response\n10.2\n9.8\n10.5\n10.1\n9.9\n10.4\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("one-sample.csv", content, "text/csv")},
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
        (settings.workspace_root / dataset_record.stored_path).write_bytes(b"response\n999\n")
        response_column_id = version["columns"][0]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "hypothesis.one_sample_t",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "alternative": "two_sided",
                    "null_mean": 10,
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "hypothesis.one_sample_t"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 6
    assert payload["provenance"]["row_count_included"] == 6
    assert payload["warnings"] == [
        {
            "code": "one_sample_t_design_assumption",
            "severity": "info",
            "message": "독립성 및 표본 설계는 데이터만으로 자동 검증하지 않습니다.",
        },
        {
            "code": "one_sample_t_not_auto_switched",
            "severity": "info",
            "message": "정규성 진단 결과로 1-표본 t-검정을 자동 전환하지 않습니다.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "one_sample_t_test"
    assert result["method"] == "one_sample_t"
    assert result["missing_policy"] == "complete_case"
    assert result["alternative"] == "two_sided"
    assert result["alpha"] == 0.05
    assert result["confidence_level"] == 0.95
    assert result["null_mean"] == 10.0
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 6
    assert result["n_used"] == 6
    sample = result["sample"]
    assert sample["mean"] == pytest.approx(10.15, abs=1e-12)
    assert sample["std"] == pytest.approx(0.27386127875258287, abs=1e-12)
    contrast = result["contrast"]
    assert contrast["estimate"] == pytest.approx(0.15000000000000036, abs=1e-12)
    assert contrast["standard_error"] == pytest.approx(0.11180339887498941, abs=1e-12)
    assert contrast["df"] == pytest.approx(5.0, abs=1e-12)
    assert contrast["statistic"] == pytest.approx(1.3416407864998778, abs=1e-12)
    assert contrast["p_value"] == pytest.approx(0.23741931006324796, abs=1e-12)
    assert contrast["confidence_interval"]["lower"] == pytest.approx(
        -0.13739978631044897,
        abs=1e-12,
    )
    assert contrast["confidence_interval"]["upper"] == pytest.approx(
        0.4373997863104497,
        abs=1e-12,
    )
    assert contrast["effect_size"]["cohen_dz"] == pytest.approx(
        0.5477225575051677,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 6
    assert row_snapshot["row_count_included"] == 6


def test_analysis_run_executes_equivalence_tost_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"response\n9.1\n9.8\n10.4\n10.2\n9.9\n10.1\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("equivalence.csv", content, "text/csv")},
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
        (settings.workspace_root / dataset_record.stored_path).write_bytes(b"response\n999\n")
        response_column_id = version["columns"][0]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "hypothesis.equivalence_tost",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                },
                "options": {
                    "design": "one_sample_mean",
                    "response_column_id": response_column_id,
                    "reference_mean": 10,
                    "lower_bound": -0.8,
                    "upper_bound": 0.8,
                    "alpha": 0.05,
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "hypothesis.equivalence_tost"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 6
    assert payload["provenance"]["row_count_included"] == 6
    assert payload["warnings"] == [
        {
            "code": "equivalence_tost_design_assumption",
            "severity": "info",
            "message": "독립성 및 1표본 평균 설계는 사용자가 확인해야 하는 설계 가정입니다.",
        },
        {
            "code": "equivalence_bounds_user_defined",
            "severity": "info",
            "message": "동등성 한계는 앱이 추정하지 않으며 사용자가 사전에 정의해야 합니다.",
        },
        {
            "code": "non_significance_is_not_equivalence",
            "severity": "info",
            "message": "일반 차이검정의 비유의성은 동등성 근거가 아닙니다.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "equivalence_tost"
    assert result["method"] == "one_sample_mean_tost"
    assert result["input_mode"] == "dataset_one_numeric_column"
    assert result["design"] == "one_sample_mean"
    assert result["missing_policy"] == "complete_case"
    assert result["alpha"] == 0.05
    assert result["confidence_level"] == pytest.approx(0.9, abs=1e-12)
    assert result["reference_mean"] == 10.0
    assert result["equivalence_bounds"]["lower"] == -0.8
    assert result["equivalence_bounds"]["upper"] == 0.8
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 6
    assert result["n_used"] == 6
    assert result["estimate"]["value"] == pytest.approx(
        -0.08333333333333393,
        abs=1e-12,
    )
    assert result["tests"]["lower"]["p_value"] == pytest.approx(
        0.005874834572812872,
        abs=1e-12,
    )
    assert result["tests"]["upper"]["p_value"] == pytest.approx(
        0.0025049679692348533,
        abs=1e-12,
    )
    assert result["tost"]["p_value"] == pytest.approx(
        0.005874834572812872,
        abs=1e-12,
    )
    assert result["tost"]["equivalent"] is True
    assert result["confidence_interval"]["lower"] == pytest.approx(
        -0.45640460349942014,
        abs=1e-12,
    )
    assert result["confidence_interval"]["upper"] == pytest.approx(
        0.2897379368327523,
        abs=1e-12,
    )
    assert result["confidence_interval"]["inside_equivalence_bounds"] is True
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 6
    assert row_snapshot["row_count_included"] == 6


def test_analysis_run_executes_paired_t_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"before,after\n10,12\n12,13\n14,15\n13,15\n15,18\n16,17\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("paired.csv", content, "text/csv")},
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
            b"before,after\n999,1000\n",
        )
        before_column_id = version["columns"][0]["column_id"]
        after_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "hypothesis.paired_t",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "before": before_column_id,
                    "after": after_column_id,
                },
                "options": {
                    "before_column_id": before_column_id,
                    "after_column_id": after_column_id,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "alternative": "two_sided",
                    "null_difference": 0,
                    "missing_policy": "complete_pair",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "hypothesis.paired_t"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 6
    assert payload["provenance"]["row_count_included"] == 6
    assert payload["warnings"] == [
        {
            "code": "paired_t_design_assumption",
            "severity": "info",
            "message": (
                "각 행이 같은 subject/pair의 두 측정값이라는 설계 가정은 "
                "사용자가 확인해야 합니다."
            ),
        },
        {
            "code": "paired_t_not_auto_switched",
            "severity": "info",
            "message": "정규성 진단 결과로 대응표본 t-검정을 자동 전환하지 않습니다.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "paired_t_test"
    assert result["method"] == "paired_t"
    assert result["design"] == "wide_two_measurement_columns"
    assert result["difference_definition"] == "after_minus_before"
    assert result["missing_policy"] == "complete_pair"
    assert result["alternative"] == "two_sided"
    assert result["alpha"] == 0.05
    assert result["confidence_level"] == 0.95
    assert result["null_difference"] == 0.0
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["before"]["display_name"] == "before"
    assert result["after"]["display_name"] == "after"
    assert result["n_total"] == 6
    assert result["n_used"] == 6
    paired_sample = result["paired_sample"]
    assert paired_sample["before_mean"] == pytest.approx(13.333333333333334, abs=1e-12)
    assert paired_sample["after_mean"] == pytest.approx(15.0, abs=1e-12)
    assert paired_sample["mean_difference"] == pytest.approx(
        1.6666666666666667,
        abs=1e-12,
    )
    assert paired_sample["difference_std"] == pytest.approx(
        0.816496580927726,
        abs=1e-12,
    )
    contrast = result["contrast"]
    assert contrast["estimate"] == pytest.approx(1.6666666666666667, abs=1e-12)
    assert contrast["standard_error"] == pytest.approx(0.33333333333333337, abs=1e-12)
    assert contrast["df"] == pytest.approx(5.0, abs=1e-12)
    assert contrast["statistic"] == pytest.approx(5.000000000000001, abs=1e-12)
    assert contrast["p_value"] == pytest.approx(0.004104715980053319, abs=1e-12)
    assert contrast["confidence_interval"]["lower"] == pytest.approx(
        0.8098060547878952,
        abs=1e-12,
    )
    assert contrast["confidence_interval"]["upper"] == pytest.approx(
        2.5235272785454383,
        abs=1e-12,
    )
    assert contrast["effect_size"]["cohen_dz"] == pytest.approx(
        2.041241452319315,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 6
    assert row_snapshot["row_count_included"] == 6


def test_analysis_run_executes_one_sample_wilcoxon_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"response\n8\n11\n14\n18\n23\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("one-sample-wilcoxon.csv", content, "text/csv")},
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
        (settings.workspace_root / dataset_record.stored_path).write_bytes(b"response\n999\n")
        response_column_id = version["columns"][0]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "hypothesis.one_sample_wilcoxon",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "alpha": 0.05,
                    "alternative": "two_sided",
                    "null_location": 10,
                    "method": "exact",
                    "zero_method": "wilcox",
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "hypothesis.one_sample_wilcoxon"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 5
    assert payload["provenance"]["row_count_included"] == 5
    assert payload["warnings"] == [
        {
            "code": "one_sample_wilcoxon_symmetry_assumption",
            "severity": "info",
            "message": "차이값 분포의 대칭성은 설계/진단 가정이며 자동 검증하지 않습니다.",
        },
        {
            "code": "one_sample_wilcoxon_not_median_test",
            "severity": "info",
            "message": "대칭성 가정 없이 1-표본 Wilcoxon을 단순 중앙값 검정으로 단정하지 않습니다.",
        },
        {
            "code": "one_sample_wilcoxon_not_auto_switched",
            "severity": "info",
            "message": "정규성 진단 결과로 1-표본 Wilcoxon을 자동 선택하지 않습니다.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "one_sample_wilcoxon_signed_rank_test"
    assert result["method"] == "one_sample_wilcoxon_signed_rank"
    assert result["missing_policy"] == "complete_case"
    assert result["alternative"] == "two_sided"
    assert result["alpha"] == 0.05
    assert result["null_location"] == 10.0
    assert result["requested_method"] == "exact"
    assert result["resolved_method"] == "exact"
    assert result["zero_method"] == "wilcox"
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 5
    assert result["n_used"] == 5
    assert result["n_nonzero"] == 5
    sample = result["sample"]
    assert sample["median"] == 14.0
    assert sample["median_difference"] == 4.0
    test = result["test"]
    assert test["w_statistic"] == 2.0
    assert test["p_value"] == 0.1875
    assert test["positive_rank_sum"] == 13.0
    assert test["negative_rank_sum"] == 2.0
    assert test["rank_sum_total"] == 15.0
    assert test["effect_size"]["rank_biserial"] == pytest.approx(
        0.7333333333333333,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 5
    assert row_snapshot["row_count_included"] == 5


def test_analysis_run_executes_kruskal_wallis_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"response,group\n" b"1,A\n2,A\n3,A\n" b"4,B\n5,B\n6,B\n" b"7,C\n8,C\n9,C\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("kruskal-wallis.csv", content, "text/csv")},
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
            b"response,group\n999,Z\n",
        )
        response_column_id = version["columns"][0]["column_id"]
        group_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "hypothesis.kruskal_wallis",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "group": group_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "group_column_id": group_column_id,
                    "alpha": 0.05,
                    "posthoc_method": "dunn_holm",
                    "posthoc_policy": "after_significant",
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "hypothesis.kruskal_wallis"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 9
    assert payload["provenance"]["row_count_included"] == 9
    assert payload["warnings"] == [
        {
            "code": "kruskal_wallis_independence_assumption",
            "severity": "info",
            "message": "독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
        },
        {
            "code": "kruskal_wallis_not_median_test",
            "severity": "info",
            "message": "Kruskal-Wallis 결과를 단순 중앙값 차이 검정으로 해석하지 않습니다.",
        },
        {
            "code": "dunn_holm_after_significant",
            "severity": "info",
            "message": "overall 검정이 유의한 경우에만 Dunn 사후검정과 Holm 보정을 수행했습니다.",
        },
        {
            "code": "small_group_size",
            "severity": "info",
            "message": "그룹 표본 수가 작아 rank 기반 근사와 설계를 함께 확인하세요.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "kruskal_wallis_test"
    assert result["method"] == "kruskal_wallis"
    assert result["missing_policy"] == "complete_case"
    assert result["alpha"] == 0.05
    assert result["posthoc_method"] == "dunn_holm"
    assert result["posthoc_policy"] == "after_significant"
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 9
    assert result["n_used"] == 9
    assert result["group_count"] == 3
    assert [group["group_label"] for group in result["groups"]] == ["A", "B", "C"]
    assert [group["rank_sum"] for group in result["groups"]] == [6.0, 15.0, 24.0]
    test = result["test"]
    assert test["h_statistic"] == pytest.approx(7.2, abs=1e-12)
    assert test["df"] == 2
    assert test["p_value"] == pytest.approx(0.02732372244729256, abs=1e-12)
    assert test["effect_size"]["epsilon_squared"] == pytest.approx(
        0.8666666666666667,
        abs=1e-12,
    )
    posthoc = result["posthoc"]
    assert posthoc["performed"] is True
    assert posthoc["multiplicity_method"] == "holm"
    assert posthoc["comparisons"][1]["adjusted_p_value"] == pytest.approx(
        0.02187107427460693,
        abs=1e-12,
    )
    assert posthoc["comparisons"][1]["reject_holm"] is True
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 9
    assert row_snapshot["row_count_included"] == 9


def test_analysis_run_executes_one_proportion_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"outcome\n" b"yes\nyes\nyes\nyes\nyes\nyes\nyes\nyes\nyes\n" b"no\nno\nno\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("one-proportion.csv", content, "text/csv")},
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
            b"outcome\nno\n",
        )
        response_column_id = version["columns"][0]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "categorical.one_proportion",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "event_level": "yes",
                    "null_proportion": 0.5,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "alternative": "two_sided",
                    "ci_method": "wilson",
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "categorical.one_proportion"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 12
    assert payload["provenance"]["row_count_included"] == 12
    assert payload["warnings"] == [
        {
            "code": "one_proportion_binary_design_assumption",
            "severity": "info",
            "message": (
                "이 컬럼이 분석 목적상 이진 사건/비사건 변수라는 가정은 "
                "사용자가 확인해야 합니다."
            ),
        },
        {
            "code": "one_proportion_exact_binomial",
            "severity": "info",
            "message": "p-value는 exact binomial test로 계산했습니다.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "one_proportion_test"
    assert result["method"] == "exact_binomial_test"
    assert result["input_mode"] == "dataset_binary_column"
    assert result["missing_policy"] == "complete_case"
    assert result["alternative"] == "two_sided"
    assert result["alpha"] == 0.05
    assert result["confidence_level"] == 0.95
    assert result["ci_method"] == "wilson"
    assert result["null_proportion"] == 0.5
    assert result["event_level"] == "yes"
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 12
    assert result["n_used"] == 12
    assert result["n_missing"] == 0
    sample = result["sample"]
    assert sample["event_count"] == 9
    assert sample["non_event_count"] == 3
    assert sample["total"] == 12
    assert sample["sample_proportion"] == 0.75
    assert sample["difference_from_null"] == 0.25
    assert sample["odds"] == 3.0
    test = result["test"]
    assert test["statistic"] == 9
    assert test["p_value"] == pytest.approx(0.14599609375, abs=1e-12)
    assert test["exact"] is True
    assert result["confidence_interval"]["lower"] == pytest.approx(
        0.46769466506643426,
        abs=1e-12,
    )
    assert result["confidence_interval"]["upper"] == pytest.approx(
        0.9110583316059453,
        abs=1e-12,
    )
    assert result["effect_size"]["cohen_h"] == pytest.approx(
        0.5235987755982985,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 12
    assert row_snapshot["row_count_included"] == 12


def test_analysis_run_executes_two_proportion_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"outcome,group\n"
        b"yes,A\n"
        b"yes,A\n"
        b"yes,A\n"
        b"yes,A\n"
        b"no,A\n"
        b"no,A\n"
        b"yes,B\n"
        b"no,B\n"
        b"no,B\n"
        b"no,B\n"
        b"no,B\n"
        b"no,B\n"
    )

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("two-proportion.csv", content, "text/csv")},
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
            b"outcome,group\nno,A\n",
        )
        response_column_id = version["columns"][0]["column_id"]
        group_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "categorical.two_proportion",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "group": group_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "group_column_id": group_column_id,
                    "event_level": "yes",
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "alternative": "two_sided",
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "categorical.two_proportion"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 12
    assert payload["provenance"]["row_count_included"] == 12
    assert payload["warnings"] == [
        {
            "code": "two_proportion_binary_design_assumption",
            "severity": "info",
            "message": "반응 컬럼이 이진 사건/비사건 변수라는 가정은 사용자가 확인해야 합니다.",
        },
        {
            "code": "two_proportion_independence_assumption",
            "severity": "info",
            "message": "두 그룹 관측치의 독립성은 설계 가정이며 자동 검증하지 않습니다.",
        },
        {
            "code": "two_proportion_fisher_exact",
            "severity": "info",
            "message": "p-value는 2x2 Fisher exact test로 계산했습니다.",
        },
        {
            "code": "small_expected_counts",
            "severity": "info",
            "message": "기대도수가 작은 셀이 있어 exact test 결과와 설계를 함께 확인하세요.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "two_proportion_test"
    assert result["method"] == "fisher_exact_2x2"
    assert result["input_mode"] == "dataset_binary_response_by_group"
    assert result["missing_policy"] == "complete_case"
    assert result["alternative"] == "two_sided"
    assert result["alpha"] == 0.05
    assert result["confidence_level"] == 0.95
    assert result["ci_method"] == "newcombe_wilson"
    assert result["event_level"] == "yes"
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 12
    assert result["n_used"] == 12
    assert [group["group_label"] for group in result["groups"]] == ["A", "B"]
    assert [group["event_count"] for group in result["groups"]] == [4, 1]
    assert [group["non_event_count"] for group in result["groups"]] == [2, 5]
    assert result["difference"]["estimate"] == pytest.approx(0.5, abs=1e-12)
    assert result["difference"]["confidence_interval"]["lower"] == pytest.approx(
        -0.04030387843204997,
        abs=1e-12,
    )
    assert result["difference"]["confidence_interval"]["upper"] == pytest.approx(
        0.7731752842826356,
        abs=1e-12,
    )
    assert result["test"]["p_value"] == pytest.approx(0.24242424242424238, abs=1e-12)
    assert result["effect_sizes"]["risk_ratio"]["estimate"] == pytest.approx(4.0, abs=1e-12)
    assert result["effect_sizes"]["odds_ratio"]["estimate"] == pytest.approx(10.0, abs=1e-12)
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 12
    assert row_snapshot["row_count_included"] == 12


def test_analysis_run_executes_chi_square_association_from_dataset_version(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"row_factor,column_factor\n" + b"".join(
        [
            b"A,X\n" * 20,
            b"A,Y\n" * 15,
            b"A,Z\n" * 5,
            b"B,X\n" * 10,
            b"B,Y\n" * 20,
            b"B,Z\n" * 10,
            b"C,X\n" * 5,
            b"C,Y\n" * 10,
            b"C,Z\n" * 25,
        ],
    )

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("chi-square.csv", content, "text/csv")},
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
            b"row_factor,column_factor\nA,X\n",
        )
        row_column_id = version["columns"][0]["column_id"]
        column_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "categorical.chi_square_association",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "row": row_column_id,
                    "column": column_column_id,
                },
                "options": {
                    "row_column_id": row_column_id,
                    "column_column_id": column_column_id,
                    "alpha": 0.05,
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "categorical.chi_square_association"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 120
    assert payload["provenance"]["row_count_included"] == 120
    assert payload["warnings"] == [
        {
            "code": "chi_square_independence_assumption",
            "severity": "info",
            "message": "관측치 독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
        },
        {
            "code": "pearson_chi_square_no_continuity_correction",
            "severity": "info",
            "message": "Pearson 카이제곱 검정은 연속성 보정 없이 계산했습니다.",
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "chi_square_association"
    assert result["method"] == "pearson_chi_square_independence"
    assert result["input_mode"] == "dataset_two_categorical_columns"
    assert result["missing_policy"] == "complete_case"
    assert result["alpha"] == 0.05
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 120
    assert result["n_used"] == 120
    assert [level["level"] for level in result["row_levels"]] == ["A", "B", "C"]
    assert [level["level"] for level in result["column_levels"]] == ["X", "Y", "Z"]
    assert result["test"]["statistic"] == pytest.approx(29.58333333333333, abs=1e-12)
    assert result["test"]["df"] == 4
    assert result["test"]["p_value"] == pytest.approx(
        0.0000059496135390747285,
        abs=1e-15,
    )
    assert result["effect_size"]["cramers_v"] == pytest.approx(
        0.35108957388234824,
        abs=1e-12,
    )
    assert result["expected_count_summary"]["rule_of_thumb_passed"] is True
    first_row = result["contingency_table"]["rows"][0]
    assert first_row["row_level"] == "A"
    assert first_row["row_total"] == 40
    assert first_row["cells"][0]["observed"] == 20
    assert first_row["cells"][0]["expected"] == pytest.approx(
        11.666666666666666,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 120
    assert row_snapshot["row_count_included"] == 120


def test_analysis_run_executes_pearson_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"x,y\n1,1\n2,2\n3,1\n4,4\n5,5\n6,7\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("pearson.csv", content, "text/csv")},
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
        (settings.workspace_root / dataset_record.stored_path).write_bytes(b"x,y\n999,999\n")
        x_column_id = version["columns"][0]["column_id"]
        y_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.pearson",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "x": x_column_id,
                    "y": y_column_id,
                },
                "options": {
                    "x_column_id": x_column_id,
                    "y_column_id": y_column_id,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "regression.pearson"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 6
    assert payload["provenance"]["row_count_included"] == 6
    assert payload["warnings"] == [
        {
            "code": "pearson_correlation_not_causation",
            "severity": "info",
            "message": "상관은 인과를 의미하지 않습니다. 설계와 도메인 근거를 별도로 확인하세요.",
        },
        {
            "code": "pearson_linear_relationship_assumption",
            "severity": "info",
            "message": "Pearson 상관은 선형 관계 요약입니다. 비선형 패턴은 별도 진단이 필요합니다.",
        },
        {
            "code": "pearson_outlier_sensitive",
            "severity": "info",
            "message": (
                "Pearson 상관은 이상값에 민감합니다. 산점도와 영향점 후보를 함께 확인하세요."
            ),
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "pearson_correlation"
    assert result["method"] == "pearson_product_moment_correlation"
    assert result["missing_policy"] == "complete_case"
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["n_total"] == 6
    assert result["n_used"] == 6
    assert result["scatterplot"] == {
        "x_column_id": x_column_id,
        "y_column_id": y_column_id,
        "point_count": 6,
        "points_truncated": False,
        "point_limit": 500,
        "points": [
            {"x": 1.0, "y": 1.0},
            {"x": 2.0, "y": 2.0},
            {"x": 3.0, "y": 1.0},
            {"x": 4.0, "y": 4.0},
            {"x": 5.0, "y": 5.0},
            {"x": 6.0, "y": 7.0},
        ],
    }
    assert "row_index" not in result["scatterplot"]["points"][0]
    assert result["association"]["correlation"] == pytest.approx(
        0.9268715709799871,
        abs=1e-12,
    )
    assert result["association"]["covariance"] == pytest.approx(4.2, abs=1e-12)
    assert result["test"]["p_value"] == pytest.approx(0.007826113791877531, abs=1e-12)
    assert result["confidence_interval"]["lower"] == pytest.approx(
        0.46536068630404304,
        abs=1e-12,
    )
    assert result["confidence_interval"]["upper"] == pytest.approx(
        0.9921355297202177,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 6
    assert row_snapshot["row_count_included"] == 6


def test_analysis_run_executes_xy_correlation_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"x1,x2,y1,y2\n1,2,1,2\n2,1,2,1\n3,4,1,4\n4,8,4,3\n5,9,5,7\n6,13,7,8\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("xy-correlation.csv", content, "text/csv")},
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
            b"x1,x2,y1,y2\n999,999,999,999\n",
        )
        x_column_ids = [
            version["columns"][0]["column_id"],
            version["columns"][1]["column_id"],
        ]
        y_column_ids = [
            version["columns"][2]["column_id"],
            version["columns"][3]["column_id"],
        ]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.xy_correlation",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "x": ",".join(x_column_ids),
                    "y": ",".join(y_column_ids),
                },
                "options": {
                    "x_column_ids": x_column_ids,
                    "y_column_ids": y_column_ids,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "pairwise_complete_case",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "regression.xy_correlation"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 6
    assert payload["provenance"]["row_count_included"] == 6
    assert payload["warnings"] == [
        {
            "code": "xy_correlation_not_causation",
            "severity": "info",
            "message": "상관은 인과를 의미하지 않습니다. 설계와 도메인 근거를 별도로 확인하세요.",
        },
        {
            "code": "xy_correlation_linear_relationship_assumption",
            "severity": "info",
            "message": "Pearson 상관은 선형 관계 요약입니다. 비선형 패턴은 별도 진단이 필요합니다.",
        },
        {
            "code": "xy_correlation_outlier_sensitive",
            "severity": "info",
            "message": (
                "Pearson 상관은 이상값에 민감합니다. 산점도와 영향점 후보를 함께 확인하세요."
            ),
        },
    ]
    result = payload["result"]
    assert result["summary_type"] == "xy_correlation_matrix"
    assert result["method"] == "pairwise_pearson_product_moment_correlation"
    assert result["missing_policy"] == "pairwise_complete_case"
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["pair_count"] == 4
    pairs = {
        (pair["x"]["display_name"], pair["y"]["display_name"]): pair for pair in result["pairs"]
    }
    assert pairs[("x1", "y1")]["association"]["correlation"] == pytest.approx(
        0.9268715709799871,
        abs=1e-12,
    )
    assert pairs[("x1", "y2")]["test"]["p_value"] == pytest.approx(
        0.014086754809093853,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload
    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 6
    assert row_snapshot["row_count_included"] == 6


def test_analysis_run_executes_linear_model_from_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"y,x1,x2\n"
        b"10,1,3\n"
        b"13,2,2\n"
        b"15,3,4\n"
        b"18,4,3\n"
        b"21,5,5\n"
        b"23,6,4\n"
        b"26,7,6\n"
        b"29,8,5\n"
    )

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("linear-model.csv", content, "text/csv")},
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
            b"y,x1,x2\n999,999,999\n",
        )
        response_column_id = version["columns"][0]["column_id"]
        predictor_column_ids = [
            version["columns"][1]["column_id"],
            version["columns"][2]["column_id"],
        ]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": ",".join(predictor_column_ids),
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": predictor_column_ids,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )
        model_id = response.json()["result"]["model_manifest"]["model_id"]
        model_response = client.get(f"/api/v1/regression-models/{model_id}")
        model_record = get_regression_model_record(settings.workspace_root, model_id)
        assert model_record is not None
        (settings.workspace_root / model_record.manifest_path).write_bytes(
            b'{"tampered":true}\n',
        )
        tampered_model_response = client.get(f"/api/v1/regression-models/{model_id}")

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "regression.linear_model"
    assert payload["provenance"]["source_schema_hash"] == version["schema_hash"]
    assert payload["provenance"]["row_count_total"] == 8
    assert payload["provenance"]["row_count_included"] == 8
    assert payload["warnings"] == [
        {
            "code": "linear_model_not_causation",
            "severity": "info",
            "message": "회귀계수는 관찰 데이터만으로 인과 효과를 의미하지 않습니다.",
        },
        {
            "code": "linear_model_linearity_assumption",
            "severity": "info",
            "message": "OLS는 반응과 예측변수의 평균 관계가 선형이라는 가정을 사용합니다.",
        },
        {
            "code": "linear_model_independence_assumption",
            "severity": "info",
            "message": "관측 독립성은 소프트웨어가 증명할 수 없으며 연구 설계로 확인해야 합니다.",
        },
        {
            "code": "linear_model_homoscedasticity_assumption",
            "severity": "info",
            "message": "OLS 계수 검정은 잔차 분산이 일정하다는 가정에 민감할 수 있습니다.",
        },
        {
            "code": "linear_model_residual_normality_assumption",
            "severity": "info",
            "message": "작은 표본에서는 잔차 정규성 위반이 계수 검정과 CI에 영향을 줄 수 있습니다.",
        },
        {
            "code": "linear_model_outlier_influence_sensitive",
            "severity": "info",
            "message": (
                "OLS는 이상점과 영향점에 민감합니다. 잔차와 leverage 진단을 함께 확인하세요."
            ),
        },
    ]
    result = payload["result"]
    assert result["schema_version"] == 4
    assert result["summary_type"] == "linear_model"
    assert result["method"] == "ordinary_least_squares_numeric_predictors"
    assert result["missing_policy"] == "complete_case"
    assert "prediction_basis" not in result
    assert result["model_manifest"]["model_id"] == model_id
    assert result["model_manifest"]["manifest_schema_version"] == 2
    assert len(result["model_manifest"]["manifest_sha256"]) == 64
    assert result["package_versions"] == {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert result["sample"] == {
        "n_total": 8,
        "n_used": 8,
        "n_excluded_missing": 0,
        "n_excluded_non_numeric": 0,
        "df_model": 2,
        "df_residual": 5,
    }
    assert result["fit"]["r_squared"] == pytest.approx(0.9982608695652174, abs=1e-12)
    assert result["fit"]["adjusted_r_squared"] == pytest.approx(
        0.9975652173913044,
        abs=1e-12,
    )
    assert result["fit"]["f_p_value"] == pytest.approx(1.2613348298348502e-07, abs=1e-18)
    coefficients = {coefficient["term"]: coefficient for coefficient in result["coefficients"]}
    assert coefficients["Intercept"]["estimate"] == pytest.approx(7.425, abs=1e-12)
    assert coefficients["x1"]["estimate"] == pytest.approx(2.7, abs=1e-12)
    assert coefficients["x1"]["p_value"] == pytest.approx(5.367504823025137e-07, abs=1e-18)
    assert coefficients["x2"]["estimate"] == pytest.approx(-0.05, abs=1e-12)
    assert coefficients["x2"]["vif"] == pytest.approx(2.8, abs=1e-12)
    diagnostics = result["diagnostics"]
    assert diagnostics["residual_summary"]["max_abs_standardized"] == pytest.approx(
        1.5403707996220706,
        abs=1e-12,
    )
    assert diagnostics["leverage"]["threshold"] == pytest.approx(0.75, abs=1e-12)
    assert diagnostics["leverage"]["high_count"] == 0
    assert diagnostics["influence"]["cooks_distance_max"] == pytest.approx(
        0.41374221646330445,
        abs=1e-12,
    )
    assert diagnostics["diagnostic_points"]["points_included"] == 8
    assert diagnostics["diagnostic_points"]["truncated"] is False
    first_point = diagnostics["diagnostic_points"]["points"][0]
    assert first_point["row_index"] == 0
    assert first_point["fitted"] == pytest.approx(9.975, abs=1e-12)
    assert first_point["residual"] == pytest.approx(0.025, abs=1e-12)
    assert result_response.status_code == 200
    assert result_response.json() == payload
    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot = config_payload["row_snapshot"]
    assert row_snapshot["kind"] == "analysis_row_snapshot"
    assert row_snapshot["row_count_total"] == 8
    assert row_snapshot["row_count_included"] == 8
    assert model_response.status_code == 200
    model_payload = model_response.json()
    assert model_payload["model_id"] == model_id
    assert model_payload["analysis_id"] == payload["analysis_id"]
    assert model_payload["dataset_version_id"] == version["version_id"]
    assert model_payload["method_id"] == "regression.linear_model"
    assert model_payload["schema_hash"] == version["schema_hash"]
    assert model_payload["manifest_sha256"] == result["model_manifest"]["manifest_sha256"]
    assert "manifest_path" not in model_response.text
    manifest = model_payload["manifest"]
    assert manifest["manifest_schema_version"] == 2
    assert manifest["model_id"] == model_id
    assert manifest["analysis_id"] == payload["analysis_id"]
    assert manifest["dataset_version_id"] == version["version_id"]
    assert manifest["source_schema_hash"] == version["schema_hash"]
    assert manifest["source_canonical_artifact_sha256"] == version["canonical_artifact"]["sha256"]
    assert manifest["row_snapshot_sha256"] == payload["provenance"]["row_snapshot_sha256"]
    assert manifest["coefficients"][0]["term"] == "Intercept"
    assert manifest["prediction_basis"]["basis_schema_version"] == 1
    assert manifest["prediction_basis"]["coefficient_order"] == ["Intercept", "x1", "x2"]
    assert manifest["prediction_basis"]["df_residual"] == 5
    assert len(manifest["prediction_basis"]["xtx_inverse"]) == 3
    assert (
        "large_standardized_row_indices" not in manifest["diagnostics_summary"]["residual_summary"]
    )
    assert "high_row_indices" not in manifest["diagnostics_summary"]["leverage"]
    assert "diagnostic_points" not in json.dumps(manifest["diagnostics_summary"])
    assert tampered_model_response.status_code == 409
    assert (
        tampered_model_response.json()["error"]["code"]
        == "regression_model_manifest_checksum_mismatch"
    )
    assert model_record.manifest_path not in tampered_model_response.text


def test_regression_prediction_preflight_accepts_same_dataset_version(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"y,x1,x2\n"
        b"10,1,3\n"
        b"13,2,2\n"
        b"15,3,4\n"
        b"18,4,3\n"
        b"21,5,5\n"
        b"23,6,4\n"
        b"26,7,6\n"
        b"29,8,5\n"
    )

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_csv_dataset(
            client,
            content=content,
            filename="linear-model-preflight.csv",
        )
        response_column_id = version["columns"][0]["column_id"]
        predictor_column_ids = [
            version["columns"][1]["column_id"],
            version["columns"][2]["column_id"],
        ]
        analysis_response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": ",".join(predictor_column_ids),
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": predictor_column_ids,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        model_id = analysis_response.json()["result"]["model_manifest"]["model_id"]
        preflight_response = client.post(
            f"/api/v1/regression-models/{model_id}/prediction-preflight",
            json={"dataset_version_id": version["version_id"]},
        )

    assert analysis_response.status_code == 201
    assert preflight_response.status_code == 200
    payload = preflight_response.json()
    RegressionPredictionPreflightResponse.model_validate(payload)
    assert payload["source_dataset_version_id"] == version["version_id"]
    assert payload["target_dataset_version_id"] == version["version_id"]
    assert payload["schema_hash_match"] is True
    assert payload["prediction_ready"] is True
    assert payload["row_count_total"] == 8
    assert payload["row_count_usable"] == 8
    assert payload["issues"] == []
    assert [
        (mapping["display_name"], mapping["match_type"], mapping["status"])
        for mapping in payload["required_columns"]
    ] == [("x1", "column_id", "ok"), ("x2", "column_id", "ok")]
    assert [check["n_valid"] for check in payload["numeric_checks"]] == [8, 8]
    assert all(check["n_below_training_range"] == 0 for check in payload["numeric_checks"])
    assert all(check["n_above_training_range"] == 0 for check in payload["numeric_checks"])
    assert payload["categorical_checks"] == []


def test_regression_prediction_endpoint_returns_ols_predictions_from_manifest(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"y,x1,x2\n"
        b"10,1,3\n"
        b"13,2,2\n"
        b"15,3,4\n"
        b"18,4,3\n"
        b"21,5,5\n"
        b"23,6,4\n"
        b"26,7,6\n"
        b"29,8,5\n"
    )

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_csv_dataset(
            client,
            content=content,
            filename="linear-model-prediction.csv",
        )
        response_column_id = version["columns"][0]["column_id"]
        predictor_column_ids = [
            version["columns"][1]["column_id"],
            version["columns"][2]["column_id"],
        ]
        analysis_response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": ",".join(predictor_column_ids),
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": predictor_column_ids,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        model_id = analysis_response.json()["result"]["model_manifest"]["model_id"]
        prediction_response = client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={
                "dataset_version_id": version["version_id"],
                "confidence_level": 0.95,
                "missing_policy": "complete_case",
                "include_intervals": True,
            },
        )
        prediction_id = prediction_response.json()["prediction_id"]
        stored_result_response = client.get(
            f"/api/v1/analysis-runs/{prediction_id}/result",
        )
        prediction_record = get_analysis_run_record(settings.workspace_root, prediction_id)
        assert prediction_record is not None
        assert prediction_record.result_path is not None
        (settings.workspace_root / prediction_record.result_path).write_bytes(
            b'{"tampered":true}\n',
        )
        tampered_result_response = client.get(
            f"/api/v1/analysis-runs/{prediction_id}/result",
        )

    assert analysis_response.status_code == 201
    assert prediction_response.status_code == 200
    payload = prediction_response.json()
    RegressionPredictionResponse.model_validate(payload)
    assert payload["model_id"] == model_id
    assert payload["source_dataset_version_id"] == version["version_id"]
    assert payload["target_dataset_version_id"] == version["version_id"]
    assert payload["row_count_total"] == 8
    assert payload["row_count_predicted"] == 8
    assert payload["row_count_excluded"] == 0
    assert payload["row_count_omitted"] == 0
    assert payload["truncated"] is False
    assert payload["provenance"]["method_id"] == "regression.predict"
    assert payload["provenance"]["model_manifest_schema_version"] == 2
    assert payload["warnings"][:2] == [
        {
            "code": "regression_prediction_not_causation",
            "severity": "info",
            "message": (
                "회귀 예측은 관찰 데이터 기반의 수학적 예측이며 인과 효과를 의미하지 않습니다."
            ),
            "count": None,
        },
        {
            "code": "regression_prediction_intervals_assumption",
            "severity": "info",
            "message": (
                "신뢰구간과 예측구간은 OLS 선형성, 독립성, 등분산성, 잔차 분포 가정에 민감합니다."
            ),
            "count": None,
        },
    ]
    first_row = payload["rows"][0]
    assert set(first_row) == {
        "row_index",
        "predicted_mean",
        "mean_confidence_interval",
        "prediction_interval",
        "warnings",
    }
    assert first_row["row_index"] == 0
    assert first_row["predicted_mean"] == pytest.approx(9.975, abs=1e-12)
    mean_ci = first_row["mean_confidence_interval"]
    prediction_interval = first_row["prediction_interval"]
    assert mean_ci["lower"] < first_row["predicted_mean"] < mean_ci["upper"]
    assert prediction_interval["lower"] < first_row["predicted_mean"] < prediction_interval["upper"]
    assert (prediction_interval["upper"] - prediction_interval["lower"]) > (
        mean_ci["upper"] - mean_ci["lower"]
    )
    assert stored_result_response.status_code == 200
    stored_payload = stored_result_response.json()
    assert stored_payload["method_id"] == "regression.predict"
    assert stored_payload["result"] == payload
    assert prediction_record.method_id == "regression.predict"
    assert prediction_record.dataset_version_id == version["version_id"]
    assert tampered_result_response.status_code == 409
    assert tampered_result_response.json()["error"]["code"] == "analysis_result_checksum_mismatch"
    assert prediction_record.result_path not in tampered_result_response.text


def test_regression_prediction_endpoint_handles_categorical_factor_terms(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"y,group\n" b"10,A\n" b"11,A\n" b"13,B\n" b"14,B\n" b"16,C\n" b"17,C\n"

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_csv_dataset(
            client,
            content=content,
            filename="linear-model-factor-prediction.csv",
        )
        response_column_id = version["columns"][0]["column_id"]
        predictor_column_id = version["columns"][1]["column_id"]
        analysis_response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": predictor_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": [predictor_column_id],
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        model_id = analysis_response.json()["result"]["model_manifest"]["model_id"]
        prediction_response = client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={
                "dataset_version_id": version["version_id"],
                "confidence_level": 0.95,
                "missing_policy": "complete_case",
                "include_intervals": True,
            },
        )

    assert analysis_response.status_code == 201
    assert prediction_response.status_code == 200
    payload = prediction_response.json()
    RegressionPredictionResponse.model_validate(payload)
    assert payload["row_count_total"] == 6
    assert payload["row_count_predicted"] == 6
    assert payload["row_count_excluded"] == 0
    assert payload["columns"] == [
        {
            "source_column_id": predictor_column_id,
            "display_name": "group",
            "predictor_kind": "categorical",
            "target_column_id": predictor_column_id,
            "match_type": "column_id",
            "status": "ok",
        },
    ]
    predicted_by_row = {row["row_index"]: row["predicted_mean"] for row in payload["rows"]}
    assert predicted_by_row[0] == pytest.approx(10.5, abs=1e-12)
    assert predicted_by_row[1] == pytest.approx(10.5, abs=1e-12)
    assert predicted_by_row[2] == pytest.approx(13.5, abs=1e-12)
    assert predicted_by_row[4] == pytest.approx(16.5, abs=1e-12)
    assert all(row["prediction_interval"] is not None for row in payload["rows"])


def test_regression_prediction_endpoint_reconstructs_numeric_extra_terms(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"y,x1,x2\n"
        b"3.2,-2,0\n"
        b"0.9,-1,1\n"
        b"3.05,0,2\n"
        b"7.5,1,0\n"
        b"12.95,2,1\n"
        b"22.6,3,2\n"
        b"20.8,4,0\n"
        b"34.05,5,1\n"
    )

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_csv_dataset(
            client,
            content=content,
            filename="linear-model-extra-term-prediction.csv",
        )
        response_column_id = version["columns"][0]["column_id"]
        x1_column_id = version["columns"][1]["column_id"]
        x2_column_id = version["columns"][2]["column_id"]
        analysis_response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": ",".join([x1_column_id, x2_column_id]),
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": [x1_column_id, x2_column_id],
                    "quadratic_terms": [x1_column_id],
                    "interaction_terms": [
                        {
                            "left_column_id": x1_column_id,
                            "right_column_id": x2_column_id,
                        },
                    ],
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        model_id = analysis_response.json()["result"]["model_manifest"]["model_id"]
        prediction_response = client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={
                "dataset_version_id": version["version_id"],
                "confidence_level": 0.95,
                "missing_policy": "complete_case",
                "include_intervals": True,
            },
        )

    assert analysis_response.status_code == 201
    assert prediction_response.status_code == 200
    analysis_payload = analysis_response.json()
    prediction_payload = prediction_response.json()
    RegressionPredictionResponse.model_validate(prediction_payload)
    assert prediction_payload["row_count_total"] == 8
    assert prediction_payload["row_count_predicted"] == 8
    assert prediction_payload["row_count_excluded"] == 0
    fitted_by_row = {
        point["row_index"]: point["fitted"]
        for point in analysis_payload["result"]["diagnostics"]["diagnostic_points"]["points"]
    }
    for row in prediction_payload["rows"]:
        assert row["predicted_mean"] == pytest.approx(fitted_by_row[row["row_index"]], abs=1e-12)
        assert row["warnings"] == []


def test_regression_prediction_endpoint_rejects_manifest_without_prediction_basis(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"y,x1,x2\n"
        b"10,1,3\n"
        b"13,2,2\n"
        b"15,3,4\n"
        b"18,4,3\n"
        b"21,5,5\n"
        b"23,6,4\n"
        b"26,7,6\n"
        b"29,8,5\n"
    )

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_csv_dataset(
            client,
            content=content,
            filename="linear-model-missing-prediction-basis.csv",
        )
        response_column_id = version["columns"][0]["column_id"]
        predictor_column_ids = [
            version["columns"][1]["column_id"],
            version["columns"][2]["column_id"],
        ]
        analysis_response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": ",".join(predictor_column_ids),
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": predictor_column_ids,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        model_id = analysis_response.json()["result"]["model_manifest"]["model_id"]
        model_record = get_regression_model_record(settings.workspace_root, model_id)
        assert model_record is not None
        manifest_path = settings.workspace_root / model_record.manifest_path
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_payload.pop("prediction_basis")
        manifest_bytes = json.dumps(
            manifest_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        manifest_path.write_bytes(manifest_bytes)
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        with sqlite3.connect(settings.workspace_root / METADATA_DB_RELATIVE_PATH) as connection:
            connection.execute(
                "UPDATE regression_models SET manifest_sha256 = ? WHERE model_id = ?",
                (manifest_sha256, model_id),
            )
        prediction_response = client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={"dataset_version_id": version["version_id"]},
        )

    assert analysis_response.status_code == 201
    assert prediction_response.status_code == 409
    error = prediction_response.json()["error"]
    assert error["code"] == "regression_prediction_manifest_uncertainty_missing"
    assert model_record.manifest_path not in prediction_response.text


def test_regression_prediction_endpoint_rejects_preflight_errors(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    training_content = (
        b"y,x1,x2\n"
        b"10,1,3\n"
        b"13,2,2\n"
        b"15,3,4\n"
        b"18,4,3\n"
        b"21,5,5\n"
        b"23,6,4\n"
        b"26,7,6\n"
        b"29,8,5\n"
    )
    target_content = b"y,x1\n0,1\n0,2\n"

    with TestClient(create_app(settings)) as client:
        training_version = _upload_confirmed_csv_dataset(
            client,
            content=training_content,
            filename="linear-model-prediction-training.csv",
        )
        response_column_id = training_version["columns"][0]["column_id"]
        predictor_column_ids = [
            training_version["columns"][1]["column_id"],
            training_version["columns"][2]["column_id"],
        ]
        analysis_response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": training_version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": ",".join(predictor_column_ids),
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": predictor_column_ids,
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        target_version = _upload_confirmed_csv_dataset(
            client,
            content=target_content,
            filename="linear-model-prediction-target-missing.csv",
        )
        model_id = analysis_response.json()["result"]["model_manifest"]["model_id"]
        prediction_response = client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={"dataset_version_id": target_version["version_id"]},
        )

    assert analysis_response.status_code == 201
    assert prediction_response.status_code == 409
    error = prediction_response.json()["error"]
    assert error["code"] == "regression_prediction_preflight_failed"
    assert "prediction_required_column_missing" in error["developer_detail"]


def test_regression_prediction_preflight_reports_target_dataset_risks(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    training_content = (
        b"y,x,group\n" b"10,1,A\n" b"12,2,A\n" b"16,3,B\n" b"18,4,B\n" b"22,5,C\n" b"24,6,C\n"
    )
    target_content = b"y,x,group\n" b"0,100,A\n" b"0,2,D\n" b"0,bad,B\n" b"0,,A\n" b"0,3,B\n"

    with TestClient(create_app(settings)) as client:
        training_version = _upload_confirmed_csv_dataset(
            client,
            content=training_content,
            filename="linear-model-training.csv",
            columns=[
                {"column_index": 2, "measurement_level": "nominal", "role": "factor"},
            ],
        )
        response_column_id = training_version["columns"][0]["column_id"]
        x_column_id = training_version["columns"][1]["column_id"]
        group_column_id = training_version["columns"][2]["column_id"]
        analysis_response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": training_version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": ",".join([x_column_id, group_column_id]),
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": [x_column_id, group_column_id],
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        target_version = _upload_confirmed_csv_dataset(
            client,
            content=target_content,
            filename="linear-model-target.csv",
            columns=[
                {
                    "column_index": 1,
                    "data_type": "decimal",
                    "measurement_level": "continuous",
                    "role": "feature",
                },
                {
                    "column_index": 2,
                    "data_type": "text",
                    "measurement_level": "nominal",
                    "role": "factor",
                },
            ],
        )
        model_id = analysis_response.json()["result"]["model_manifest"]["model_id"]
        preflight_response = client.post(
            f"/api/v1/regression-models/{model_id}/prediction-preflight",
            json={"dataset_version_id": target_version["version_id"]},
        )

    assert analysis_response.status_code == 201
    assert preflight_response.status_code == 200
    payload = preflight_response.json()
    RegressionPredictionPreflightResponse.model_validate(payload)
    assert payload["source_dataset_version_id"] == training_version["version_id"]
    assert payload["target_dataset_version_id"] == target_version["version_id"]
    assert payload["schema_hash_match"] is False
    assert payload["prediction_ready"] is True
    assert payload["row_count_total"] == 5
    assert payload["row_count_usable"] == 2
    mappings = {
        mapping["display_name"]: (mapping["match_type"], mapping["status"])
        for mapping in payload["required_columns"]
    }
    assert mappings == {
        "x": ("display_name", "warning"),
        "group": ("display_name", "warning"),
    }
    issue_codes = [issue["code"] for issue in payload["issues"]]
    assert "prediction_schema_hash_mismatch" in issue_codes
    assert issue_codes.count("prediction_column_matched_by_display_name") == 2
    assert "prediction_missing_values_detected" in issue_codes
    assert "prediction_non_numeric_values_detected" in issue_codes
    assert "prediction_extrapolation_risk" in issue_codes
    assert "prediction_unseen_categorical_levels" in issue_codes
    numeric_check = payload["numeric_checks"][0]
    assert numeric_check["display_name"] == "x"
    assert numeric_check["n_valid"] == 3
    assert numeric_check["n_missing"] == 1
    assert numeric_check["n_non_numeric"] == 1
    assert numeric_check["n_above_training_range"] == 1
    categorical_check = payload["categorical_checks"][0]
    assert categorical_check["display_name"] == "group"
    assert categorical_check["training_level_count"] == 3
    assert categorical_check["n_valid"] == 5
    assert categorical_check["n_unseen_level"] == 1


def test_analysis_run_executes_linear_model_with_categorical_factor(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"y,group\n" b"10,A\n" b"11,A\n" b"13,B\n" b"14,B\n" b"16,C\n" b"17,C\n"

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("linear-model-factor.csv", content, "text/csv")},
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
        response_column_id = version["columns"][0]["column_id"]
        predictor_column_id = version["columns"][1]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": predictor_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": [predictor_column_id],
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert payload["method_id"] == "regression.linear_model"
    assert {
        "code": "linear_model_categorical_treatment_coding",
        "severity": "info",
        "message": "범주형 예측변수는 첫 수준을 기준으로 하는 treatment coding으로 적합했습니다.",
    } in payload["warnings"]
    result = payload["result"]
    assert result["schema_version"] == 4
    assert result["method"] == "ordinary_least_squares_main_effects"
    assert result["sample"]["df_model"] == 2
    assert result["sample"]["df_residual"] == 3
    assert result["fit"]["r_squared"] == pytest.approx(0.96, abs=1e-12)
    assert result["model_specification"]["terms"][0]["kind"] == "categorical_main_effect"
    assert result["model_specification"]["terms"][0]["reference_level"] == "A"
    coefficients = {coefficient["term"]: coefficient for coefficient in result["coefficients"]}
    assert coefficients["Intercept"]["estimate"] == pytest.approx(10.5, abs=1e-12)
    assert coefficients["group[B]"]["estimate"] == pytest.approx(3.0, abs=1e-12)
    assert coefficients["group[B]"]["reference_level"] == "A"
    assert coefficients["group[C]"]["estimate"] == pytest.approx(6.0, abs=1e-12)
    assert result_response.status_code == 200
    assert result_response.json() == payload


def test_analysis_run_executes_linear_model_with_numeric_extra_terms(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = (
        b"y,x1,x2\n"
        b"3.2,-2,0\n"
        b"0.9,-1,1\n"
        b"3.05,0,2\n"
        b"7.5,1,0\n"
        b"12.95,2,1\n"
        b"22.6,3,2\n"
        b"20.8,4,0\n"
        b"34.05,5,1\n"
    )

    with TestClient(create_app(settings)) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("linear-model-terms.csv", content, "text/csv")},
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
        response_column_id = version["columns"][0]["column_id"]
        x1_column_id = version["columns"][1]["column_id"]
        x2_column_id = version["columns"][2]["column_id"]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": ",".join([x1_column_id, x2_column_id]),
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": [x1_column_id, x2_column_id],
                    "quadratic_terms": [x1_column_id],
                    "interaction_terms": [
                        {
                            "left_column_id": x1_column_id,
                            "right_column_id": x2_column_id,
                        },
                    ],
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )
        result_response = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result",
        )

    assert response.status_code == 201
    payload = response.json()
    AnalysisResultEnvelope.model_validate(payload)
    assert {
        "code": "linear_model_quadratic_terms_selected",
        "severity": "info",
        "message": ("선택한 숫자형 2차항은 탐색적 모형 항이며, 해석에는 설계 근거가 필요합니다."),
    } in payload["warnings"]
    assert {
        "code": "linear_model_interaction_terms_selected",
        "severity": "info",
        "message": "선택한 숫자형 상호작용 항은 주효과와 함께 해석해야 합니다.",
    } in payload["warnings"]
    result = payload["result"]
    assert result["schema_version"] == 4
    assert result["method"] == "ordinary_least_squares_safe_terms"
    assert result["sample"]["df_model"] == 4
    assert result["sample"]["df_residual"] == 3
    terms = result["model_specification"]["terms"]
    assert terms[-2]["kind"] == "numeric_quadratic"
    assert terms[-2]["source_column_ids"] == [x1_column_id]
    assert terms[-1]["kind"] == "numeric_interaction"
    assert terms[-1]["source_column_ids"] == [x1_column_id, x2_column_id]
    coefficients = {coefficient["term"]: coefficient for coefficient in result["coefficients"]}
    assert coefficients["x1^2"]["estimate"] == pytest.approx(
        0.5040540540540538,
        abs=1e-12,
    )
    assert coefficients["x1:x2"]["estimate"] == pytest.approx(
        1.5542792792792784,
        abs=1e-12,
    )
    assert result_response.status_code == 200
    assert result_response.json() == payload


def test_analysis_run_rejects_normality_grouping_for_first_slice(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        version = _upload_confirmed_numeric_dataset(client)
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.normality",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {"group": version["columns"][1]["column_id"]},
                "options": {
                    "column_ids": [version["columns"][0]["column_id"]],
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "normality_grouping_not_supported"


def test_analysis_run_applies_numeric_filter_and_freezes_row_ranges(tmp_path) -> None:
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
        record = get_analysis_run_record(
            settings.workspace_root,
            response.json()["analysis_id"],
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["provenance"]["row_count_total"] == 2
    assert payload["provenance"]["row_count_included"] == 1
    assert payload["result"]["columns"][0]["n_total"] == 1
    assert payload["result"]["columns"][0]["n_used"] == 1
    assert payload["result"]["columns"][0]["mean"] == 2

    assert record is not None
    config_payload = json.loads(record.config_json)
    row_snapshot_path = settings.workspace_root / config_payload["row_snapshot"]["path"]
    row_snapshot_payload = json.loads(row_snapshot_path.read_text(encoding="utf-8"))
    assert row_snapshot_payload["filter_snapshot"] == {
        "expression_version": 1,
        "conditions": [
            {
                "column_id": version["columns"][0]["column_id"],
                "operator": "gt",
                "value": 1,
            },
        ],
    }
    assert row_snapshot_payload["selection"] == {
        "kind": "row_ranges",
        "row_count_total": 2,
        "row_count_included": 1,
        "row_count_excluded": 1,
        "row_ranges": [{"start": 1, "end": 2}],
    }


def test_analysis_run_rejects_invalid_filter_without_artifacts(tmp_path) -> None:
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
                            "operator": "contains",
                            "value": "1",
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

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "filter_operator_not_supported"
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


def test_linear_model_result_manifest_files_are_removed_when_metadata_insert_fails(
    tmp_path,
    monkeypatch,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    content = b"y,x\n2,1\n4,2\n5,3\n8,4\n9,5\n"

    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        upload_response = client.post(
            "/api/v1/datasets",
            files={"file": ("linear-cleanup.csv", content, "text/csv")},
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
        response_column_id = version["columns"][0]["column_id"]
        predictor_column_id = version["columns"][1]["column_id"]

        def fail_insert(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("metadata insert failed")

        monkeypatch.setattr(
            "app.services.analysis_runs."
            "insert_analysis_run_record_with_artifacts_and_regression_model",
            fail_insert,
        )

        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {
                    "response": response_column_id,
                    "predictors": predictor_column_id,
                },
                "options": {
                    "response_column_id": response_column_id,
                    "predictor_column_ids": [predictor_column_id],
                    "alpha": 0.05,
                    "confidence_level": 0.95,
                    "missing_policy": "complete_case",
                    "include_intercept": True,
                    "covariance_type": "standard",
                },
            },
        )

    assert response.status_code == 500
    assert not list(settings.workspace_root.glob("workspaces/analyses/*/result.json"))
    assert not list(settings.workspace_root.glob("workspaces/analyses/*/row_snapshot.json"))
    assert not list(settings.workspace_root.glob("workspaces/analyses/*/model-*.json"))


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


def _upload_confirmed_csv_dataset(
    client: TestClient,
    *,
    content: bytes,
    filename: str,
    columns: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    upload_response = client.post(
        "/api/v1/datasets",
        files={"file": (filename, content, "text/csv")},
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
            "columns": [] if columns is None else columns,
        },
    )
    assert confirm_response.status_code == 201
    return confirm_response.json()


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
