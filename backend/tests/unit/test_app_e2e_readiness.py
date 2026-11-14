"""Readiness stages use real-state boundaries, not one combined startup budget."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def readiness():
    path = Path(__file__).resolve().parents[3] / "tests/e2e/app_readiness.py"
    spec = importlib.util.spec_from_file_location("tested_staged_readiness", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scheduled_page(monkeypatch, readiness, *, mounted=0, app=11_053, compatible=16_584):
    """Virtual DOM timing from CI43563002774; no sleeps or browser dependency."""
    clock = [0]
    events = []
    page = MagicMock(url="http://synthetic.invalid/help")

    def locator(selector):
        target = MagicMock()
        target.selector = selector
        target.locator.side_effect = locator
        target.get_attribute.return_value = "help-title"
        return target

    page.locator.side_effect = locator

    class Assertion:
        def __init__(self, target):
            self.selector = target.selector

        def wait(self, operation, ready_at, timeout):
            events.append((self.selector, operation, timeout))
            if ready_at is None or ready_at > clock[0] + timeout:
                raise AssertionError(f"{self.selector}: {operation} not ready")
            clock[0] = max(clock[0], ready_at)

        def to_be_visible(self, *, timeout=5_000):
            ready_at = {
                "#root > *": mounted,
                "#root [data-runtime-state]": app,
                "#root .app-shell": compatible,
            }.get(self.selector, compatible)
            self.wait("visible", ready_at, timeout)

        def to_have_attribute(self, name, value, *, timeout=5_000):
            ready_at = compatible if name == "data-runtime-state" else mounted
            self.wait(f"{name}={value}", ready_at, timeout)

        def to_have_count(self, count, *, timeout=5_000):
            assert count == 0
            self.wait("count=0", compatible, timeout)

    monkeypatch.setattr(readiness, "expect", Assertion)
    return page, clock, events


def test_cold_module_and_runtime_have_separate_bounded_readiness(readiness, monkeypatch):
    page, clock, events = scheduled_page(monkeypatch, readiness)
    readiness.wait_for_app_ready(page, "en", "/help")
    assert clock == [16_584]
    assert events[:4] == [
        ("#root > *", "visible", 15_000),
        ("#root [data-runtime-state]", "visible", 15_000),
        ("#root [data-runtime-state]", "data-runtime-state=compatible", 15_000),
        ("#root .app-shell", "visible", 15_000),
    ]
    page.goto.assert_not_called()
    page.reload.assert_not_called()
    page.wait_for_timeout.assert_not_called()
    page.wait_for_load_state.assert_not_called()


@pytest.mark.parametrize(
    ("timing", "stage"),
    [
        ({"mounted": None}, "#root > *"),
        ({"app": None}, "#root [data-runtime-state]"),
        ({"app": 15_001}, "#root [data-runtime-state]"),
        ({"compatible": None}, "data-runtime-state=compatible"),
        ({"compatible": 26_054}, "data-runtime-state=compatible"),
    ],
)
def test_each_unfinished_stage_is_rejected(readiness, monkeypatch, timing, stage):
    page, _, events = scheduled_page(monkeypatch, readiness, **timing)
    with pytest.raises(AssertionError) as caught:
        readiness.wait_for_app_ready(page, "en", "/help")
    assert stage in str(caught.value)
    assert not any(selector.startswith(".workspace") for selector, _, _ in events)


def test_runtime_marker_alone_never_accepts_blocked_or_checking(readiness, monkeypatch):
    page, _, events = scheduled_page(monkeypatch, readiness, app=0, compatible=None)
    with pytest.raises(AssertionError, match="data-runtime-state=compatible"):
        readiness.wait_for_app_ready(page, "en", "/help")
    assert events[-1][1] == "data-runtime-state=compatible"


def test_stage_budget_override_is_respected(readiness, monkeypatch):
    page, clock, events = scheduled_page(monkeypatch, readiness, app=900, compatible=1_800)
    readiness.wait_for_app_ready(page, "en", "/help", timeout_ms=1_000)
    assert clock == [1_800]
    assert all(timeout == 1_000 for _, _, timeout in events[:4])
