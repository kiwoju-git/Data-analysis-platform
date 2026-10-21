"""The synthetic BO fixture must obey the same origin guard as browser writes."""

import importlib
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
