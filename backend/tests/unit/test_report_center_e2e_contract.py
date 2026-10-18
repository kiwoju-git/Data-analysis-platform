"""Report Center's smoke checks actual selected-result capability, not old labels."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def validate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tests/e2e"))
    return importlib.import_module("critical_path").validate_selected_report_capability


def capability() -> dict:
    return {
        "analysis_id": "selected-analysis",
        "method_id": "hypothesis.two_sample_t",
        "report_level": "full",
        "html_available": True,
        "renderer_id": "two_sample_t_test",
        "renderer_version": "2.0.0",
        "source_result_sha256": "a" * 64,
        "sections": [
            {"status": "rendered"},
            {"status": "not_applicable"},
        ],
    }


def test_selected_full_report_and_optional_sections_are_verified(validate):
    validate(capability(), "selected-analysis")


@pytest.mark.parametrize(
    "change",
    [
        {"analysis_id": "previous-analysis"},
        {"method_id": "eda.descriptive"},
        {"report_level": "summary"},
        {"report_level": "unsupported"},
        {"html_available": False},
        {"renderer_id": None},
        {"renderer_version": ""},
        {"source_result_sha256": "invalid"},
        {"sections": []},
        {"sections": [{"status": "missing"}]},
    ],
)
def test_stale_wrong_or_incomplete_report_cannot_pass_smoke(validate, change):
    with pytest.raises(AssertionError):
        validate({**capability(), **change}, "selected-analysis")
