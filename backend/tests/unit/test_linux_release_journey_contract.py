"""The archive driver must distinguish GP fields, payload digests and stopped servers."""

from __future__ import annotations

import hashlib
import importlib
import json
import urllib.error
from pathlib import Path

import pytest


@pytest.fixture
def drivers(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tests/e2e"))
    return tuple(
        importlib.import_module(name)
        for name in ("linux_release", "linux_release_journey", "managed_reports_live")
    )


def test_prediction_families_preserve_all_distinct_stored_fields(drivers) -> None:
    _, _, reports = drivers
    assert reports.prediction_values({"predicted_value": 1.25}, "pls") == [1.25]
    row = {
        "predicted_mean": -1.25,
        "latent_standard_deviation": 0,
        "latent_interval_95": {"lower": -1.25, "upper": -1.25},
        "predictive_standard_deviation": 0.5,
        "predictive_interval_95": {"lower": -2.23, "upper": -0.27},
    }
    assert reports.prediction_values(row, "gaussian_process") == [
        -1.25,
        0,
        -1.25,
        -1.25,
        0.5,
        -2.23,
        -0.27,
    ]
    with pytest.raises(KeyError):
        reports.prediction_values({"predicted_value": 1.25}, "gaussian_process")
    with pytest.raises(AssertionError, match="Unsupported"):
        reports.prediction_values(row, "unknown")


def test_payload_digest_is_not_an_artifact_byte_checksum(drivers) -> None:
    _, journey, _ = drivers
    data = {"column": "온도", "value": 0.125}
    assert journey.payload_digest(data) == journey.payload_digest(
        dict(reversed(list(data.items())))
    )
    pretty_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    assert journey.payload_digest(data) != hashlib.sha256(pretty_bytes).hexdigest()


def test_journal_starts_pending_and_records_failure_without_success(drivers, tmp_path) -> None:
    _, journey, _ = drivers
    evidence = journey.JourneyEvidence(tmp_path, {"build_commit": "a" * 40}, "initial")
    pending = json.loads((tmp_path / "journey-evidence.json").read_text(encoding="utf-8"))
    assert pending["status"] == "running"
    assert "finished_at" not in pending
    evidence.data["status"] = "failed"
    evidence.save()
    failed = json.loads((tmp_path / "journey-evidence.json").read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["finished_at"] >= failed["started_at"]


@pytest.mark.parametrize("status", [403, 404, 500, 503])
def test_http_error_is_not_evidence_of_stopped_server(drivers, monkeypatch, status) -> None:
    release, _, _ = drivers

    def respond(*_args, **_kwargs):
        raise urllib.error.HTTPError("http://127.0.0.1:8600", status, "response", {}, None)

    monkeypatch.setattr(release.HTTP, "open", respond)
    with pytest.raises(AssertionError, match="still responding"):
        release.require_server_stopped("http://127.0.0.1:8600")


def test_connection_refusal_allows_offline_phase(drivers, monkeypatch) -> None:
    release, _, _ = drivers

    def refused(*_args, **_kwargs):
        raise urllib.error.URLError(ConnectionRefusedError())

    monkeypatch.setattr(release.HTTP, "open", refused)
    release.require_server_stopped("http://127.0.0.1:8600")
