from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_graphical_preview_reuses_filter_and_does_not_create_analysis_history(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_version(
            client,
            b"temperature,pressure,line,order\n1,10,A,1\n2,11,A,2\n3,12,B,3\n4,13,B,4\n",
        )
        temperature, pressure, _line, _order = version["columns"]
        response = client.post(
            "/api/v1/visualizations/preview",
            json={
                "dataset_version_id": version["version_id"],
                "graph_type": "histogram",
                "value_column_ids": [temperature["column_id"], pressure["column_id"]],
                "layout": "small_multiples",
                "filter_snapshot": {
                    "expression_version": 1,
                    "conditions": [
                        {
                            "column_id": temperature["column_id"],
                            "operator": "gt",
                            "value": "2",
                        }
                    ],
                },
            },
        )
        history = client.get("/api/v1/analysis-runs")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["visualization_schema_version"] == 1
    assert payload["row_count_total"] == 4
    assert payload["row_count_included"] == 2
    assert len(payload["filter_snapshot_sha256"]) == 64
    assert len(payload["preview_config_sha256"]) == 64
    assert [panel["result"]["n_used"] for panel in payload["panels"]] == [2, 2]
    assert history.status_code == 200
    assert history.json()["returned_count"] == 0


def test_box_plot_group_mode_and_unit_guard(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_version(
            client,
            b"temperature,pressure,line\n1,10,A\n2,11,A\n3,12,B\n4,13,B\n",
            columns=[
                {"column_index": 0, "measurement_level": "continuous", "unit": "C"},
                {"column_index": 1, "measurement_level": "continuous", "unit": "bar"},
                {"column_index": 2, "measurement_level": "nominal", "unit": None},
            ],
        )
        temperature, pressure, line = version["columns"]
        grouped = client.post(
            "/api/v1/visualizations/preview",
            json={
                "dataset_version_id": version["version_id"],
                "graph_type": "box_plot",
                "value_column_ids": [temperature["column_id"]],
                "group_column_id": line["column_id"],
                "layout": "combined",
            },
        )
        mismatched = client.post(
            "/api/v1/visualizations/preview",
            json={
                "dataset_version_id": version["version_id"],
                "graph_type": "box_plot",
                "value_column_ids": [temperature["column_id"], pressure["column_id"]],
                "layout": "combined",
            },
        )

    assert grouped.status_code == 200, grouped.text
    assert [panel["label"] for panel in grouped.json()["panels"]] == [
        "temperature · A",
        "temperature · B",
    ]
    assert [panel["result"]["n_used"] for panel in grouped.json()["panels"]] == [2, 2]
    assert mismatched.status_code == 400
    assert mismatched.json()["error"]["code"] == "graph_preview_unit_mismatch"


def test_individual_value_preview_rejects_over_limit_without_sampling(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    rows = "\n".join(str(index) for index in range(1, 13))
    with TestClient(create_app(settings)) as client:
        version = _create_version(client, f"value\n{rows}\n".encode())
        response = client.post(
            "/api/v1/visualizations/preview",
            json={
                "dataset_version_id": version["version_id"],
                "graph_type": "individual_value_plot",
                "value_column_ids": [version["columns"][0]["column_id"]],
                "point_limit": 10,
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "individual_value_point_limit_exceeded"


def test_run_and_imr_preview_return_independent_panels(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_version(
            client,
            b"first,second,order\n1,10,1\n2,12,2\n4,11,3\n3,15,4\n5,14,5\n",
        )
        first, second, order = version["columns"]
        common = {
            "dataset_version_id": version["version_id"],
            "value_column_ids": [first["column_id"], second["column_id"]],
            "order_column_id": order["column_id"],
            "layout": "small_multiples",
        }
        run = client.post(
            "/api/v1/visualizations/preview",
            json={**common, "graph_type": "run_chart"},
        )
        imr = client.post(
            "/api/v1/visualizations/preview",
            json={**common, "graph_type": "imr_chart"},
        )

    assert run.status_code == 200, run.text
    assert [panel["kind"] for panel in run.json()["panels"]] == [
        "run_chart",
        "run_chart",
    ]
    assert imr.status_code == 200, imr.text
    assert [panel["kind"] for panel in imr.json()["panels"]] == ["imr_chart", "imr_chart"]
    assert all(
        panel["result"]["summary_type"] == "individuals_chart" for panel in imr.json()["panels"]
    )


def _create_version(
    client: TestClient,
    content: bytes,
    *,
    columns: list[dict[str, object]] | None = None,
) -> dict:
    upload = client.post(
        "/api/v1/datasets",
        files={"file": ("graph-preview.csv", content, "text/csv")},
    )
    assert upload.status_code == 201
    response = client.post(
        f"/api/v1/datasets/{upload.json()['dataset_id']}/confirm-parsing",
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
    assert response.status_code == 201, response.text
    return response.json()
