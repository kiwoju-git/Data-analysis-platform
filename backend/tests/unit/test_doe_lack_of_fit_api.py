import hashlib
import json
import sqlite3
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient
from test_factorial_model_selection_api import create_full

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


@pytest.mark.parametrize("general", [False, True])
def test_zero_pure_error_api_restore_and_visible_report(tmp_path, general):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, base = create_full(client, general=general)
        values = []
        for run in design["runs"]:
            levels = run["level_indices"] if general else run["coded_levels"]
            a, b = levels["A"], levels["B"]
            values.append({"run_order": run["run_order"], "value": 10 + 3 * a + 2 * a * b})
        saved = client.put(base + "/responses", json={"response_name": "Yield", "values": values})
        assert saved.status_code == 200, saved.text
        response = client.post(
            base + "/analyses",
            json={"response_name": "Yield", "max_interaction_order": 1},
        )
        assert response.status_code == 201, response.text
        analysis = response.json()
        lack = analysis["result"]["anova"]["lack_of_fit"]
        assert lack["reason"] == "pure_error_variance_zero"
        assert lack["available"] is False
        assert lack["decomposition_available"] is True
        row = lack if general else lack["lack_of_fit"]
        assert row["p_value"] is row["f_statistic"] is None
        assert row["df"] > 0 and row["sum_squares"] > 0
        report_base = (
            f"/api/v1/doe-designs/{design['design_id']}/analyses/{analysis['analysis_id']}"
        )
        exported = client.post(report_base + "/exports/html", json={"locale": "en"})
        assert exported.status_code == 201, exported.text
        html = client.get(report_base + f"/exports/{exported.json()['asset_id']}/download")
        assert html.status_code == 200
        visible = VisibleText()
        visible.feed(html.text)
        assert "Pure-error variance is zero" in " ".join(visible.parts)
        assert (
            'data-term-id="A"' in html.text if general else 'data-term-id="factor_1"' in html.text
        )
        assert ">Retained</p>" in html.text
        assert client.get(base + f"/analyses/{analysis['analysis_id']}").json() == analysis


def test_rsm_zero_pure_error_and_previous_method_reader(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        created = client.post(
            "/api/v1/doe-designs/response-surface",
            json={
                "name": "Synthetic LoF",
                "factors": [{"name": name, "low": -1, "high": 1} for name in "AB"],
                "alpha_mode": "rotatable",
                "center_points": 5,
                "randomize": False,
                "randomization_seed": 7,
            },
        )
        assert created.status_code == 201, created.text
        design = created.json()
        base = f"/api/v1/doe-designs/response-surface/{design['design_id']}"
        values = [
            {
                "run_order": run["run_order"],
                "value": 20 + run["coded_levels"]["A"] + run["coded_levels"]["B"] ** 3,
            }
            for run in design["runs"]
        ]
        assert (
            client.put(
                base + "/responses", json={"response_name": "Y", "values": values}
            ).status_code
            == 200
        )
        response = client.post(base + "/analyses", json={"response_name": "Y"})
        assert response.status_code == 201, response.text
        analysis = response.json()
        assert analysis["result"]["anova"]["lack_of_fit"]["reason"] == "pure_error_variance_zero"
        assert client.get(base + f"/analyses/{analysis['analysis_id']}").json() == analysis
        # A synthetic previous-version envelope: keep the old result bytes unchanged on read.
        analysis["method_version"] = "0.3.0"
        analysis["analysis_schema_version"] = 2
        analysis["result"]["schema_version"] = 1
        analysis["result"]["method"] = "full_quadratic_ordinary_least_squares"
        analysis["result"]["coding"].pop("factors", None)
        for field in (
            "term_preset",
            "model_selection",
            "final_basis",
            "press",
            "predicted_r_squared",
        ):
            analysis["result"].pop(field, None)
        analysis["result"]["stationary_point"].pop("reason", None)
        for field in (
            "reason",
            "decomposition_available",
            "replication_grouping_policy",
            "decomposition_tolerance",
        ):
            analysis["result"]["anova"]["lack_of_fit"].pop(field, None)
        encoded = json.dumps(analysis, ensure_ascii=False)
        checksum = hashlib.sha256(encoded.encode()).hexdigest()
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            config = json.loads(
                connection.execute(
                    "SELECT config_json FROM experiment_design_analyses WHERE analysis_id=?",
                    (analysis["analysis_id"],),
                ).fetchone()[0]
            )
            config["schema_version"] = 2
            config.pop("term_preset", None)
            config.pop("model_selection", None)
            connection.execute(
                "UPDATE experiment_design_analyses SET method_version=?, result_json=?, "
                "result_sha256=?, config_json=? WHERE analysis_id=?",
                ("0.3.0", encoded, checksum, json.dumps(config), analysis["analysis_id"]),
            )
        restored = client.get(base + f"/analyses/{analysis['analysis_id']}")
        assert restored.status_code == 200, restored.text
        assert restored.json()["method_version"] == "0.3.0"
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            assert connection.execute(
                "SELECT result_json, result_sha256 FROM experiment_design_analyses "
                "WHERE analysis_id=?",
                (analysis["analysis_id"],),
            ).fetchone() == (encoded, checksum)
