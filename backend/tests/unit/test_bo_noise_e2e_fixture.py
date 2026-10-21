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
