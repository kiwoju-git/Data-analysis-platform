"""Browser snapshot checks allow only the documented null metadata omission."""

from __future__ import annotations

import copy
import importlib
import math
from pathlib import Path

import pytest


@pytest.fixture
def assert_response(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tests/e2e"))
    return importlib.import_module("gp_prediction_context")._assert_snapshot_response


def response() -> dict:
    return {
        "model_id": "synthetic-model",
        "rows": [
            {"client_row_id": "row-2", "predicted_mean": 0.08685245621124293},
            {"client_row_id": "row-1", "predicted_mean": 0.9483308395057364},
        ],
    }


@pytest.mark.parametrize("include_null", [False, True])
def test_only_absent_persistence_metadata_may_be_omitted(assert_response, include_null):
    delivered = response()
    if include_null:
        delivered["saved_prediction"] = None
    original = copy.deepcopy(delivered)
    assert_response(response(), delivered)
    assert delivered == original


def test_non_null_saved_descriptor_must_be_preserved(assert_response):
    delivered = {**response(), "saved_prediction": {"artifact_id": "saved-result"}}
    assert_response(copy.deepcopy(delivered), delivered)
    with pytest.raises(AssertionError):
        assert_response(response(), delivered)


@pytest.mark.parametrize("change", ["one_ulp", "row_order", "extra_field", "missing_field"])
def test_prediction_assertion_does_not_relax_values_or_structure(assert_response, change):
    delivered = response()
    snapshot = copy.deepcopy(delivered)
    if change == "one_ulp":
        value = snapshot["rows"][0]["predicted_mean"]
        snapshot["rows"][0]["predicted_mean"] = math.nextafter(value, math.inf)
    elif change == "row_order":
        snapshot["rows"].reverse()
    elif change == "extra_field":
        snapshot["unexpected"] = None
    else:
        del snapshot["model_id"]
    with pytest.raises(AssertionError):
        assert_response(snapshot, delivered)
