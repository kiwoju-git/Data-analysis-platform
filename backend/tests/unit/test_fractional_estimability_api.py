from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_fraction_second_order_preflight_backward_restore_and_source_integrity(
    tmp_path: Path,
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        created = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "Synthetic fraction",
                "design_type": "two_level_fractional",
                "fraction_id": "5-factor-half-r5",
                "factors": [{"name": name, "low": -1, "high": 1} for name in "ABCDE"],
                "replicates": 1,
                "center_points": 0,
                "randomize": False,
                "randomization_seed": 7,
                "block_count": 1,
            },
        )
        assert created.status_code == 201, created.text
        design = created.json()
        path = f"/api/v1/doe-designs/{design['design_id']}"
        options = {"method": "backward_elimination", "alpha_to_remove": 0.05}
        preflight = client.post(
            path + "/analysis-term-preflight",
            json={
                "max_interaction_order": 2,
                "model_selection": options,
            },
        )
        assert preflight.status_code == 200, preflight.text
        plan = preflight.json()["estimability"]
        assert plan["requested_parameter_count"] == plan["rank"] == 16
        assert plan["saturated"] is True
        saved = client.put(
            path + "/responses",
            json={
                "response_name": "Y",
                "unit": "mm",
                "values": [
                    {
                        "run_order": run["run_order"],
                        "value": 10
                        + 2 * run["coded_levels"]["A"]
                        - run["coded_levels"]["B"]
                        + 0.4 * run["coded_levels"]["A"] * run["coded_levels"]["B"]
                        + (run["run_order"] * 17 % 11) * 0.023,
                    }
                    for run in design["runs"]
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        analysis = client.post(
            path + "/analyses",
            json={
                "response_name": "Y",
                "max_interaction_order": 2,
                "model_selection": options,
            },
        )
        assert analysis.status_code == 201, analysis.text
        payload = analysis.json()
        assert payload["method_version"] == "0.10.0"
        assert payload["result"]["schema_version"] == 4
        assert payload["result"]["estimability"] == plan
        assert payload["result"]["model_policy"]["effective_interaction_order"] == 2
        assert len(payload["result"]["model_selection"]["pooled_term_ids"]) == 4
        restored = client.get(path + "/analyses/" + payload["analysis_id"])
        assert restored.status_code == 200, restored.text
        assert restored.json() == payload
        assert client.get(path).json()["design_sha256"] == design["design_sha256"]
        report = client.post(
            path + "/analyses/" + payload["analysis_id"] + "/exports/html",
            json={"locale": "en"},
        )
        assert report.status_code == 201, report.text
        html = client.get(
            path
            + "/analyses/"
            + payload["analysis_id"]
            + f"/exports/{report.json()['asset_id']}/download"
        )
        assert html.status_code == 200, html.text
        assert "I = ABCDE" in html.text
        assert "Independent representative basis" in html.text
        assert "Initial pooling" in html.text
        assert client.get(path + "/analyses/" + payload["analysis_id"]).json() == payload
        unsupported = client.post(
            path + "/analyses",
            json={
                "response_name": "Y",
                "max_interaction_order": 3,
            },
        )
        assert unsupported.status_code == 409
        assert unsupported.json()["error"]["code"] == "doe_fractional_interaction_order_unsupported"


def test_forced_alias_conflict_names_the_controlled_term_ids(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "Conflict",
                "design_type": "two_level_fractional",
                "fraction_id": "4-factor-half-r4",
                "randomization_seed": 7,
                "factors": [{"name": name, "low": -1, "high": 1} for name in "ABCD"],
            },
        ).json()
        response = client.post(
            f"/api/v1/doe-designs/{design['design_id']}/analysis-term-preflight",
            json={
                "max_interaction_order": 2,
                "model_selection": {
                    "term_policies": [
                        {"term_id": term_id, "disposition": "forced"}
                        for term_id in ["factor_1:factor_2", "factor_3:factor_4"]
                    ],
                },
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "doe_fractional_forced_terms_conflict"
        assert "factor_1:factor_2" in response.json()["error"]["message"]
        assert "factor_3:factor_4" in response.json()["error"]["message"]
