from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _dataset(client: TestClient) -> dict[str, object]:
    uploaded = client.post(
        "/api/v1/datasets",
        files={
            "file": (
                "pca.csv",
                b"x1,x2,x3\n1,2,4\n2,4,3\n3,6,5\n4,8,2\n5,10,6\n6,12,1\n",
                "text/csv",
            )
        },
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
                "missing_tokens": ["", "NA"],
            },
            "columns": [],
        },
    )
    assert confirmed.status_code == 201
    return confirmed.json()


def test_principal_components_analysis_runs_and_restores(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _dataset(client)
        column_ids = [column["column_id"] for column in version["columns"]]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.principal_components",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "filter_snapshot": {"expression_version": 1, "conditions": []},
                "roles": {"variables": ",".join(column_ids)},
                "options": {
                    "column_ids": column_ids,
                    "matrix_type": "correlation",
                    "component_selection": "cumulative_threshold",
                    "component_count": None,
                    "cumulative_threshold": 0.9,
                    "outlier_alpha": 0.05,
                    "plot_point_limit": 5000,
                    "missing_policy": "complete_case",
                },
            },
        )
        assert response.status_code == 201, response.text
        result = response.json()["result"]
        restored = client.get(
            f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result"
        )

    assert result["schema_version"] == 1
    assert result["summary_type"] == "principal_components_analysis"
    assert len(result["eigenanalysis"]) == 3
    assert len(result["scores"]) == 6
    assert restored.status_code == 200
    assert restored.json()["result"] == result


def test_principal_components_rejects_constant_variable(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        uploaded = client.post(
            "/api/v1/datasets",
            files={"file": ("constant.csv", b"x,y\n1,1\n1,2\n1,3\n", "text/csv")},
        )
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
        ).json()
        ids = [column["column_id"] for column in confirmed["columns"]]
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.principal_components",
                "method_version": "0.1.0",
                "dataset_version_id": confirmed["version_id"],
                "roles": {},
                "options": {"column_ids": ids},
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "pca_constant_variable"


def test_principal_components_html_report_uses_saved_result_in_both_locales(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _dataset(client)
        column_ids = [column["column_id"] for column in version["columns"]]
        analysis = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.principal_components",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {"column_ids": column_ids},
            },
        ).json()
        exports = [
            client.post(
                f"/api/v1/analysis-runs/{analysis['analysis_id']}/exports/html",
                json={"locale": locale},
            )
            for locale in ("en", "ko")
        ]
        downloads = [
            client.get(
                f"/api/v1/analysis-runs/{analysis['analysis_id']}/exports/"
                f"{export.json()['export_id']}/download"
            )
            for export in exports
        ]
        csv_export = client.post(
            f"/api/v1/analysis-runs/{analysis['analysis_id']}/exports/csv"
        )
        csv_download = client.get(
            f"/api/v1/analysis-runs/{analysis['analysis_id']}/exports/"
            f"{csv_export.json()['export_id']}/download"
        )

    english = downloads[0].content.decode("utf-8")
    korean = downloads[1].content.decode("utf-8")
    assert '<html lang="en">' in english
    assert "Principal Components Analysis" in english
    assert "Eigenanalysis" in english
    assert "Scree Plot" in english
    assert "Score Plot" in english
    assert '<script' not in english
    assert "https://" not in english
    assert '<html lang="ko">' in korean
    assert "PCA 기반 다변량 검토" in korean
    assert "고유값 분석" in korean
    assert csv_export.status_code == 201
    csv_text = csv_download.content.decode("utf-8-sig")
    assert "scores[0].scores[0]" in csv_text
    assert "scores[5].source_row_number" in csv_text
