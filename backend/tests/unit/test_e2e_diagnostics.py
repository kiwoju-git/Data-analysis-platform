"""The failure recorder must preserve the failing child, even after a crash."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def diagnostics(monkeypatch):
    path = Path(__file__).resolve().parents[3] / "tests/e2e/app_readiness.py"
    spec = importlib.util.spec_from_file_location("tested_app_readiness", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "source_identity", lambda: {"source_commit": "fixture"})
    monkeypatch.setattr(module.platform, "system", lambda: "diagnostic-test")
    return module


def browser_fixture():
    browser = MagicMock()
    browser.version = "test-browser"
    context = browser.new_context.return_value
    page = context.new_page.return_value
    page.url = "http://127.0.0.1/help"
    page.viewport_size = {"width": 1280, "height": 800}
    page.evaluate.return_value = {"lang": "ko"}
    page.content.return_value = "<html lang='ko'></html>"
    page.screenshot.return_value = b"synthetic-image"
    return browser, context, page


def test_capture_and_cleanup_failures_do_not_replace_original(diagnostics, tmp_path, monkeypatch):
    browser, context, page = browser_fixture()
    page.evaluate.side_effect = RuntimeError("renderer closed")
    page.screenshot.side_effect = RuntimeError("renderer closed")
    page.content.side_effect = RuntimeError("renderer closed")
    context.tracing.stop.side_effect = RuntimeError("trace closed")
    context.close.side_effect = RuntimeError("context closed")
    monkeypatch.setattr(Path, "write_text", MagicMock(side_effect=OSError("disk full")))
    original = AssertionError("original assertion")
    with pytest.raises(AssertionError) as caught:
        with diagnostics.diagnosed_page(browser, tmp_path, "crash"):
            raise original
    assert caught.value is original
    assert original.e2e_child_diagnostics == str(tmp_path / "crash")
    context.tracing.stop.assert_called_once()
    context.close.assert_called_once()


@pytest.mark.parametrize("stage", ["tracing", "page", "init_script"])
def test_setup_failure_still_closes_context(diagnostics, tmp_path, stage):
    browser, context, _ = browser_fixture()
    operation = {
        "tracing": context.tracing.start,
        "page": context.new_page,
        "init_script": context.add_init_script,
    }[stage]
    original = RuntimeError("setup failure")
    operation.side_effect = original
    with pytest.raises(RuntimeError) as caught:
        with diagnostics.diagnosed_page(browser, tmp_path, stage, locale="ko"):
            pytest.fail("Setup must not yield a page")
    assert caught.value is original
    context.close.assert_called_once()
    assert context.tracing.stop.call_count == (0 if stage == "tracing" else 1)


def test_cleanup_failure_is_not_success(diagnostics, tmp_path):
    browser, context, _ = browser_fixture()
    context.tracing.stop.side_effect = RuntimeError("trace failed")
    with pytest.raises(RuntimeError, match="trace failed"):
        with diagnostics.diagnosed_page(browser, tmp_path, "cleanup"):
            pass
    context.close.assert_called_once()


def test_tcp_snapshot_keeps_only_aggregate_states(diagnostics):
    output = """
Active Connections
  Proto  Local Address          Foreign Address        State
  TCP    127.0.0.1:5271          0.0.0.0:0              LISTENING
  TCP    127.0.0.1:5271          127.0.0.1:49156        TIME_WAIT
  TCP    [::1]:5271             [::1]:49157             TIME_WAIT
  TCP    10.0.0.2:443           192.0.2.1:80            ESTABLISHED
  UDP    127.0.0.1:123           *:*
  TCP    127.0.0.1:5271          0.0.0.0:0              UNKNOWN
"""
    assert diagnostics.tcp_state_counts(output) == {
        "ESTABLISHED": 1,
        "LISTENING": 1,
        "TIME_WAIT": 2,
    }


def test_tcp_snapshot_is_bounded_read_only_and_redacts_raw_output(diagnostics, monkeypatch):
    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Windows")
    run = MagicMock(return_value=MagicMock(stdout="TCP 127.0.0.1:1 192.0.2.1:2 TIME_WAIT"))
    monkeypatch.setattr(diagnostics.subprocess, "run", run)
    result = diagnostics.socket_failure_diagnostics()
    assert result == {
        "status": "collected",
        "scope": "host_aggregate_not_browser_attribution",
        "tcp_states": {"TIME_WAIT": 1},
        "total_tcp_sockets": 1,
    }
    run.assert_called_once_with(
        ["netstat.exe", "-an", "-p", "tcp"],
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
        timeout=5,
    )


@pytest.mark.parametrize(
    "failure", [OSError("sensitive path"), subprocess.TimeoutExpired("private", 5)]
)
def test_tcp_snapshot_failure_does_not_expose_error_text(diagnostics, monkeypatch, failure):
    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Windows")
    monkeypatch.setattr(diagnostics.subprocess, "run", MagicMock(side_effect=failure))
    assert diagnostics.socket_failure_diagnostics() == {
        "status": "unavailable",
        "error_type": type(failure).__name__,
    }


def test_other_platform_does_not_spawn_diagnostic(diagnostics, monkeypatch):
    run = MagicMock(side_effect=AssertionError("Must not spawn"))
    monkeypatch.setattr(diagnostics.subprocess, "run", run)
    assert diagnostics.socket_failure_diagnostics()["status"] == "not_collected"
    run.assert_not_called()
