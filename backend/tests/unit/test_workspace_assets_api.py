from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_unified_asset_catalog_lists_dataset_analysis_and_doe_without_paths(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        upload = client.post(
            "/api/v1/datasets",
            files={"file": ("asset-fixture.csv", b"x,y\n1,2\n2,4\n3,6\n", "text/csv")},
        )
        dataset_id = upload.json()["dataset_id"]
        confirmed = client.post(
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
                    "missing_tokens": ["", "NA"],
                },
                "columns": [],
            },
        )
        assert confirmed.status_code == 201, confirmed.text
        version = confirmed.json()
        analysis = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.descriptive",
                "method_version": "0.2.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "column_ids": [version["columns"][0]["column_id"]],
                    "missing_policy": "available_case_by_column",
                },
            },
        )
        assert analysis.status_code == 201, analysis.text
        design = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "asset DOE",
                "factors": [
                    {"name": "A", "low": -1, "high": 1},
                    {"name": "B", "low": -1, "high": 1},
                ],
                "replicates": 1,
                "center_points": 0,
                "randomize": False,
                "randomization_seed": 1,
                "block_count": 1,
            },
        )
        assert design.status_code == 201, design.text
        general_design = client.post(
            "/api/v1/doe-designs/general-factorial",
            json={
                "name": "three-level general design",
                "factors": [
                    {"name": "Temperature", "levels": [60, 70, 80], "unit": "C"},
                    {"name": "Material", "levels": ["A", "B", "C"]},
                ],
                "replicates": 1,
                "randomize": False,
                "randomization_seed": 2,
                "max_interaction_order": 2,
            },
        )
        assert general_design.status_code == 201, general_design.text
        metadata = client.patch(
            f"/api/v1/assets/analysis_run/{analysis.json()['analysis_id']}/metadata",
            json={
                "user_label": "기준 기술통계",
                "note": "발표 검토용",
                "pinned": True,
            },
        )
        assert metadata.status_code == 200, metadata.text
        stale_metadata = client.patch(
            f"/api/v1/assets/analysis_run/{analysis.json()['analysis_id']}/metadata",
            json={
                "user_label": "충돌하는 이름",
                "expected_metadata_updated_at": "2000-01-01T00:00:00Z",
            },
        )
        response = client.get("/api/v1/assets?limit=50")
        filtered = client.get("/api/v1/assets?category=designs&search=asset%20DOE")
        method_filtered = client.get(
            "/api/v1/assets?method_id=doe.factorial_design&status=designed&sort=name_asc"
        )
        pinned_filtered = client.get("/api/v1/assets?pinned=true")

    assert response.status_code == 200, response.text
    assert stale_metadata.status_code == 409, stale_metadata.text
    payload = response.json()
    assert {item["asset_type"] for item in payload["items"]} >= {
        "dataset_version",
        "analysis_run",
        "doe_design",
    }
    assert all("sha256" not in item for item in payload["items"])
    assert all(
        not item["open_target"]["path"].startswith(("C:", "/tmp", "/home"))
        for item in payload["items"]
    )
    general_item = next(
        item for item in payload["items"] if item["method_id"] == "doe.general_factorial_design"
    )
    analysis_item = next(
        item for item in payload["items"] if item["asset_id"] == analysis.json()["analysis_id"]
    )
    assert analysis_item["display_name"] == "기준 기술통계"
    assert analysis_item["note"] == "발표 검토용"
    assert analysis_item["pinned"] is True
    assert analysis_item["metadata_updated_at"] == metadata.json()["metadata_updated_at"]
    assert general_item["open_target"]["path"].endswith(
        f"design_id={general_design.json()['design_id']}&design_kind=general"
    )
    assert filtered.status_code == 200
    assert [item["display_name"] for item in filtered.json()["items"]] == ["asset DOE"]
    assert method_filtered.status_code == 200
    assert [item["display_name"] for item in method_filtered.json()["items"]] == ["asset DOE"]
    assert pinned_filtered.status_code == 200
    assert [item["asset_id"] for item in pinned_filtered.json()["items"]] == [
        analysis.json()["analysis_id"]
    ]
