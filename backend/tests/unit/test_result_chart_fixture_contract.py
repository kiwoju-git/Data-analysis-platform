"""Unit checks for the chart fixture boundary, not browser execution evidence."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_result_chart_failure_records_actual_child_context(tmp_path, monkeypatch):
    fixture_root = Path(__file__).resolve().parents[3] / "tests" / "e2e"
    monkeypatch.syspath_prepend(str(fixture_root))
    spec = importlib.util.spec_from_file_location(
        "tested_result_charts", fixture_root / "result_charts.py"
    )
    assert spec is not None and spec.loader is not None
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    import app_readiness

    monkeypatch.setattr(app_readiness, "source_identity", lambda: {"source_commit": "fixture"})
    monkeypatch.setattr(app_readiness.platform, "system", lambda: "synthetic-test")
    browser = MagicMock()
    browser.version = "fixture-browser"
    context = browser.new_context.return_value
    page = context.new_page.return_value
    page.url = "http://127.0.0.1/tests/result-charts.html"
    page.viewport_size = {"width": 1440, "height": 900}
    page.evaluate.return_value = {"lang": "en", "rootMounted": True}
    page.content.return_value = "<html lang='en'>synthetic chart</html>"
    page.screenshot.return_value = b"synthetic"
    failure = AssertionError("synthetic chart assertion")
    verify = MagicMock(side_effect=failure)
    monkeypatch.setattr(fixture, "_verify_result_chart_models", verify)

    with pytest.raises(AssertionError) as caught:
        fixture.verify_result_chart_models(browser, "http://127.0.0.1", tmp_path)

    assert caught.value is failure
    verify.assert_called_once_with(page, "http://127.0.0.1", tmp_path)
    evidence_root = tmp_path / "result-chart-models"
    assert failure.e2e_child_diagnostics == str(evidence_root)
    evidence = json.loads((evidence_root / "failure.json").read_text(encoding="utf-8"))
    assert evidence["url"] == page.url
    assert evidence["document"]["lang"] == "en"
    assert evidence["stage"] == "result-chart-models"
    assert evidence["fixture"] == "synthetic"
    context.tracing.stop.assert_called_once_with(path=str(evidence_root / "trace.zip"))
    context.close.assert_called_once()
