"""The synthetic BO fixture must obey the same origin guard as browser writes."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("base", ["http://127.0.0.1:5199", "http://192.0.2.10:8600"])
def test_bo_synthetic_seed_supplies_exact_origin_for_every_write(monkeypatch, base):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    fixture = importlib.import_module("bo_noise_extension")
    study = {
        "study_id": "synthetic-study",
        "observation_history": {"history_revision_id": "synthetic-history"},
        "trials": [
            {"trial_id": f"trial-{index}", "actual_coordinates": {"x": index / 4}}
            for index in range(4)
        ],
    }
    request = Mock()
    request.post.return_value = SimpleNamespace(status=201, json=lambda: study)
    request.put.return_value = SimpleNamespace(status=200, json=lambda: study)
    request.get.return_value = SimpleNamespace(status=200, json=lambda: study)

    assert fixture._seed(SimpleNamespace(request=request), base) == study
    assert request.post.call_count == 1
    assert request.put.call_count == 4
    for call in [*request.post.call_args_list, *request.put.call_args_list]:
        assert call.kwargs.get("headers") == {"Origin": base}
        assert call.args[0].startswith(base + "/api/v1/bayesian-studies")


def test_bo_native_receipt_excludes_raw_values_and_preserves_archive_return(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    fixture = importlib.import_module("bo_noise_extension")
    receipt = {
        "schema_version": 1,
        "synthetic": True,
        "status": "succeeded",
        "q1_target_ui": True,
        "raw_n": 9,
        "effective_n": 7,
        "locales_viewports": [{"locale": "ko", "width": 1024, "raw_value": "SENSITIVE"}],
        "study_id": "SENSITIVE-STUDY",
        "source_history_sha256": "SENSITIVE-HASH",
        "raw_values": ["SENSITIVE"],
        "actual_coordinates": {"SENSITIVE-COLUMN": 1},
    }
    output = tmp_path / "native diagnostics" / "한글"
    returned = fixture._record_receipt(output, receipt)
    assert returned is receipt
    assert receipt["study_id"] == "SENSITIVE-STUDY"
    contents = (output / "bo-validation-receipt.json").read_text(encoding="utf-8")
    assert "SENSITIVE" not in contents
    assert json.loads(contents) == {
        "schema_version": 1,
        "synthetic": True,
        "status": "succeeded",
        "checks": {"q1_target_ui": True},
        "counts": {"raw_n": 9, "effective_n": 7},
        "locales_viewports": [{"locale": "ko", "width": 1024}],
    }


@pytest.mark.parametrize(
    "change",
    [
        {"status": "failed"},
        {"q1_target_ui": "SENSITIVE"},
        {"raw_n": "SENSITIVE"},
        {"locales_viewports": [{"locale": "SENSITIVE", "width": 1024}]},
    ],
)
def test_bo_native_receipt_rejects_invalid_metadata_before_writing(monkeypatch, tmp_path, change):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    fixture = importlib.import_module("bo_noise_extension")
    receipt = {
        "schema_version": 1,
        "synthetic": True,
        "status": "succeeded",
        "q1_target_ui": True,
        **change,
    }
    with pytest.raises(AssertionError):
        fixture._record_receipt(tmp_path, receipt)
    assert not (tmp_path / "bo-validation-receipt.json").exists()


@pytest.mark.parametrize(
    "invalid", [None, "sidebar_right", "main_left", "title_right", "control_left"]
)
def test_bo_resize_waits_for_transition_then_checks_actual_bounds(monkeypatch, invalid):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    fixture = importlib.import_module("bo_noise_extension")
    geometry = {
        "width": 1024,
        "main_left": 0,
        "main_right": 1024,
        "sidebar_right": -6.2,
        "sidebar_hidden": True,
        "title_left": 20,
        "title_right": 300,
        "control_left": 20,
        "control_right": 490,
    }
    if invalid:
        geometry[invalid] = 1100 if invalid.endswith("right") else -25
    page = Mock()
    page.evaluate.side_effect = [None, geometry]
    if invalid:
        with pytest.raises(AssertionError):
            fixture._settled_layout(page)
    else:
        assert fixture._settled_layout(page) == geometry
    transition_script = page.evaluate.call_args_list[0].args[0]
    assert "getAnimations" in transition_script and ".finished" in transition_script
    assert "setTimeout" not in transition_script


def test_bo_layout_receipt_only_keeps_finite_bounds(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    fixture = importlib.import_module("bo_noise_extension")
    geometry = {
        "locale": "ko",
        "width": 1024,
        "main_left": 0,
        "main_right": 1024,
        "sidebar_right": -6.2,
        "sidebar_hidden": True,
        "title_left": 20,
        "title_right": 300,
        "control_left": 20,
        "control_right": 490,
        "raw_title": "SENSITIVE",
    }
    receipt = {
        "schema_version": 1,
        "synthetic": True,
        "status": "succeeded",
        "q1_target_ui": True,
        "layout_geometry": [geometry],
        "managed_report": {"snapshot": {"payload": "SENSITIVE"}},
    }
    fixture._record_receipt(tmp_path, receipt)
    stored = (tmp_path / "bo-validation-receipt.json").read_text(encoding="utf-8")
    assert "SENSITIVE" not in stored
    assert json.loads(stored)["layout_geometry"] == [
        {key: value for key, value in geometry.items() if key != "raw_title"}
    ]
    geometry["control_right"] = float("nan")
    with pytest.raises(AssertionError):
        fixture._record_receipt(tmp_path / "invalid", receipt)
    assert not (tmp_path / "invalid" / "bo-validation-receipt.json").exists()


@pytest.mark.parametrize("changed_cell", [False, True])
def test_bo_offline_html_fixture_reads_visible_table_values(monkeypatch, tmp_path, changed_cell):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    fixture = importlib.import_module("bo_noise_extension")
    checks = Mock()
    monkeypatch.setattr(fixture, "expect", lambda _: checks)
    item = {
        "rank": 1,
        "actual_coordinates": {"x": 0.5},
        "predicted_objective_mean": 1.5,
        "latent_standard_deviation": 1e-6,
        "predictive_standard_deviation": 2e-6,
        "acquisition_value_standardized": 0.003,
        "acquisition_value_raw": 0.001,
    }
    payload = {"definition": {"factors": [{"factor_id": "x"}]}, "attachment": {"items": [item]}}
    page, section, table, rows, cells = (Mock() for _ in range(5))
    page.locator.side_effect = [Mock(), section]
    section.locator.return_value.nth.return_value = table
    table.locator.return_value = rows
    rows.nth.return_value.locator.return_value = cells
    shown = ["1", "0.5", "1.5", "0" if changed_cell else "1e-6", "2e-6", "0.003", "0.001"]
    cells.nth.side_effect = [
        SimpleNamespace(inner_text=lambda value=value: value) for value in shown
    ]
    if changed_cell:
        with pytest.raises(AssertionError):
            fixture.verify_bo_report_html(page, tmp_path / "synthetic.html", payload)
    else:
        fixture.verify_bo_report_html(page, tmp_path / "synthetic.html", payload)
        checks.to_have_attribute.assert_any_call("data-report-section-status", "rendered")
        checks.to_contain_text.assert_any_call("New-observation predictive SD (mg)")
        checks.to_have_count.assert_called_once_with(1)
    page.goto.assert_called_once()
