from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from html import escape

import pytest
from fastapi.testclient import TestClient
from test_pls_regression_api import _create_dataset

from app.core.config import Settings
from app.main import create_app
from app.services.pls_regression_report import render_pls_report
from app.storage.metadata import get_analysis_run_record, get_regression_model_record


def create_pls(client, components=2):
    version = _create_dataset(client)
    columns = version["columns"]
    response = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "regression.partial_least_squares",
            "method_version": "0.1.0",
            "dataset_version_id": version["version_id"],
            "roles": {},
            "options": {
                "response_column_id": columns[0]["column_id"],
                "predictor_column_ids": [c["column_id"] for c in columns[1:]],
                "component_selection": "fixed",
                "n_components": components,
                "max_components": 3,
                "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 29},
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("locale,components", [("en", 1), ("en", 2), ("ko", 2)])
def test_pls_html_preserves_stored_results_without_refitting(
    tmp_path, monkeypatch, locale, components
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        saved = create_pls(client, components)
        analysis_id = saved["analysis_id"]
        model_id = saved["result"]["model_manifest"]["model_id"]
        analysis = get_analysis_run_record(tmp_path, analysis_id)
        model = get_regression_model_record(tmp_path, model_id)
        original_result = (tmp_path / analysis.result_path).read_bytes()
        original_model = (tmp_path / model.manifest_path).read_bytes()

        def forbidden(*args, **kwargs):
            pytest.fail("report export tried to fit, predict or read source rows")

        monkeypatch.setattr("sklearn.cross_decomposition.PLSRegression.fit", forbidden)
        monkeypatch.setattr("sklearn.cross_decomposition.PLSRegression.predict", forbidden)
        monkeypatch.setattr("app.services.analysis_runner_pls.iter_rows_for_snapshot", forbidden)
        exported = client.post(
            f"/api/v1/analysis-runs/{analysis_id}/exports/html", json={"locale": locale}
        )
        assert exported.status_code == 201, exported.text
        downloaded = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/{exported.json()['export_id']}/download"
        )
        assert downloaded.status_code == 200
        assert hashlib.sha256(downloaded.content).hexdigest() == exported.json()["sha256"]
        html = downloaded.text
        core = html.split('data-pls-report="1"')[1].split("</section>")[0]
        assert core.count("<svg") >= 6
        assert core.count("<table") >= 7
        assert "<script" not in html and 'src="http' not in html
        assert f'lang="{locale}"' in html
        assert f'data-selected-components="{components}"' in core
        assert len(re.findall(r"data-loading-component=", core)) == components
        assert "data-pls-selection-plot" in core
        assert "data-pls-score-plot" in core
        assert "data-pls-residual-plot" in core
        for coefficient in saved["result"]["coefficients"]:
            assert format(coefficient["coefficient"], ".10g") in core
        assert (tmp_path / analysis.result_path).read_bytes() == original_result
        assert (tmp_path / model.manifest_path).read_bytes() == original_model
        exports = client.get(f"/api/v1/analysis-runs/{analysis_id}/exports").json()
        assert exported.json()["export_id"] in [item["export_id"] for item in exports["exports"]]


def test_pls_saved_preview_is_not_limited_to_frontend_first_hundred(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        payload = deepcopy(create_pls(client, 1)["result"])
    label = '긴 변수 이름 <script>alert("x")</script> & ' + "temperature_" * 12
    payload["predictors"][0]["display_name"] = label
    payload["coefficients"][0]["display_name"] = label
    point = payload["diagnostics"]["points"][0]
    payload["diagnostics"]["points"] = [{**point, "row_index": i} for i in range(125)]
    payload["diagnostics"]["point_count_total"] = 200
    payload["diagnostics"]["point_limit"] = 125
    payload["latent_components"]["x_scores"] = [[float(i)] for i in range(125)]
    payload["latent_components"]["score_row_indices"] = list(range(125))
    html = render_pls_report(payload, "ko")
    assert "125 / 200" in html and "<td>125</td>" in html
    assert escape(label) in html and "<script" not in html
    score_plot = html.split('data-pls-score-plot="1"')[1].split("</svg>")[0]
    assert "Component 2" not in score_plot
    assert score_plot.count("<circle") == 125
    with pytest.raises(ValueError, match="analysis_report_payload_invalid"):
        render_pls_report({"schema_version": 1}, "en")
    with pytest.raises(ValueError, match="analysis_report_schema_unsupported"):
        render_pls_report({**payload, "schema_version": 999}, "en")
