from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def dataset(
    client: TestClient,
    contents: bytes = b"value,group\n1,A\n2,A\n3,A\n4,A\n5,A\n1,B\n3,B\n5,B\n7,B\n9,B\n",
) -> dict:
    upload = client.post("/api/v1/datasets", files={"file": ("variance.csv", contents, "text/csv")})
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
                "missing_tokens": ["", "NA"],
            },
            "columns": [],
        },
    )
    assert response.status_code == 201
    return response.json()


def run_body(version: dict) -> dict:
    return {
        "method_id": "quality.two_variances",
        "method_version": "0.1.0",
        "dataset_version_id": version["version_id"],
        "roles": {},
        "options": {
            "response_column_id": version["columns"][0]["column_id"],
            "group_column_id": version["columns"][1]["column_id"],
            "numerator_group_key": "A",
            "denominator_group_key": "B",
        },
    }


def test_preflight_run_restore_and_mismatch(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = dataset(client)
        body = run_body(version)
        preflight = client.post(
            "/api/v1/analysis-methods/quality.two_variances/preflight",
            json={
                "dataset_version_id": version["version_id"],
                **{key: body["options"][key] for key in ("response_column_id", "group_column_id")},
            },
        )
        assert preflight.status_code == 200, preflight.text
        assert preflight.json()["eligible"]
        body["options"]["preflight_fingerprint"] = preflight.json()["fingerprint"]
        response = client.post("/api/v1/analysis-runs", json=body)
        assert response.status_code == 201, response.text
        result = response.json()["result"]
        assert result["sample"]["n_used"] == 10
        assert result["ratio_estimate"]["variance"] == 0.25
        assert result["plot"]["groups"][1]["points"][0]["row_number"] == 6
        assert (
            client.get(f"/api/v1/analysis-runs/{response.json()['analysis_id']}/result").json()[
                "result"
            ]
            == result
        )
        body["options"]["preflight_fingerprint"] = "0" * 64
        assert (
            client.post("/api/v1/analysis-runs", json=body).json()["error"]["code"]
            == "two_variances_preflight_changed"
        )
        body["options"].pop("preflight_fingerprint")
        body["options"]["numerator_group_key"] = "C"
        assert (
            client.post("/api/v1/analysis-runs", json=body).json()["error"]["code"]
            == "two_variances_groups_changed"
        )


def test_three_groups_and_invalid_bf_options(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = dataset(client, b"value,group\n1,A\n2,A\n3,A\n2,B\n4,B\n5,B\n1,C\n2,C\n3,C\n")
        body = run_body(version)
        response = client.post("/api/v1/analysis-runs", json=body)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "two_variances_exactly_two_groups_required"
        body["options"]["alternative"] = "less"
        assert (
            client.post("/api/v1/analysis-runs", json=body).json()["error"]["code"]
            == "invalid_two_variances_options"
        )
