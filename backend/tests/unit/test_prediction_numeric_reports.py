import json
from xml.etree import ElementTree as ET

import pytest

from app.services.completed_prediction_report import render_completed_prediction
from app.services.report_contract import ReportSection
from app.services.stored_prediction_report import _render


def _completed(family="gaussian_process"):
    return {
        "family": family,
        "model_id": "model-synthetic",
        "model_manifest_sha256": "a" * 64,
        "source_analysis_id": "source-synthetic",
        "source_result_sha256": "b" * 64,
        "created_at": "2026-10-19T00:00:00Z",
        "request_sha256": "c" * 64,
        "result_sha256": "d" * 64,
        "predictors": [{"column_id": "x", "display_name": "X <user>", "unit": "s"}],
        "response": {"display_name": "Response", "unit": "mg/L"},
        "request": {"rows": [{"client_row_id": "raw <row>", "values": {"x": 1000000000001.0}}]},
        "result": {
            "rows": [
                {
                    "client_row_id": "raw <row>",
                    "predicted_mean": 1e-6,
                    "predicted_value": 2e-6,
                    "latent_standard_deviation": 2e-6,
                    "latent_interval_95": {"lower": 1e12 + 1, "upper": 1e12 + 2},
                    "predictive_standard_deviation": 0.0004,
                    "predictive_interval_95": {"lower": 1000.0000001, "upper": 1000.0000002},
                    "warnings": [],
                }
            ]
        },
    }


def _cells(body):
    section = next(item for item in body.sections if item.section_id == "predictions")
    return [node.text for node in ET.fromstring(section.markup).findall(".//tbody/tr/td")]


@pytest.mark.parametrize("locale", ["ko", "en"])
def test_completed_gp_intervals_have_shared_endpoint_precision(locale):
    payload = _completed()
    before = json.dumps(payload)
    cells = _cells(render_completed_prediction(payload, locale))
    assert cells[0] == "raw <row>"
    assert float(cells[1]) == 1e-6
    assert float(cells[2]) == 2e-6
    assert cells[3] != cells[4]
    assert float(cells[3]) == 1e12 + 1 and float(cells[4]) == 1e12 + 2
    assert cells[6] != cells[7]
    assert float(cells[6]) == 1000.0000001 and float(cells[7]) == 1000.0000002
    assert json.dumps(payload) == before


@pytest.mark.parametrize("locale", ["ko", "en"])
def test_stored_prediction_intervals_remain_distinct_and_missing_remains_dash(locale):
    payload = {
        "prediction_id": "prediction-synthetic",
        "model_id": "model-synthetic",
        "model_manifest_sha256": "a" * 64,
        "confidence_level": 0.95,
        "row_count_predicted": 1,
        "row_count_excluded": 0,
        "rows": [
            {
                "row_index": 0,
                "predicted_mean": -1e-6,
                "mean_confidence_interval": {"lower": 1e12 + 1, "upper": 1e12 + 2},
                "prediction_interval": None,
            }
        ],
    }
    before = json.dumps(payload)
    cells = _cells(
        _render(
            payload, ReportSection("inputs", "Stored inputs", "rendered", "<p>Stored</p>"), locale
        )
    )
    assert cells[0] == "1" and float(cells[1]) == -1e-6
    assert cells[2] != cells[3]
    assert float(cells[2]) == 1e12 + 1 and float(cells[3]) == 1e12 + 2
    assert cells[4:6] == ["-", "-"]
    assert json.dumps(payload) == before


def test_completed_pls_remains_point_only():
    body = render_completed_prediction(_completed("pls"), "en")
    assert len(_cells(body)) == 2
    assert float(_cells(body)[1]) == 2e-6


def test_completed_gp_mixed_integer_float_interval_remains_distinct():
    payload = _completed()
    payload["result"]["rows"][0]["latent_interval_95"] = {"lower": 1, "upper": 1.0000000000000002}
    before = json.dumps(payload)
    cells = _cells(render_completed_prediction(payload, "en"))
    assert cells[3:5] == ["1", "1.0000000000000002"]
    assert json.dumps(payload) == before
