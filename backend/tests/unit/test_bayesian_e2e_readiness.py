"""BO route readiness waits for source catalog state, not network inactivity."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[3]
ROUTE = "/analysis/doe/doe.bayesian_optimization"


@pytest.fixture
def readiness():
    spec = importlib.util.spec_from_file_location(
        "tested_bo_readiness", ROOT / "tests/e2e/app_readiness.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _catalog_fixture(monkeypatch, readiness, *, visible=True, loading=0, errors=0):
    events = []
    catalog = MagicMock()
    catalog.get_by_role.side_effect = lambda role: role
    page = MagicMock()
    page.locator.return_value = catalog
    app_ready = MagicMock(side_effect=lambda *args, **kwargs: events.append("app-ready"))
    monkeypatch.setattr(readiness, "wait_for_app_ready", app_ready)

    class Assertion:
        def __init__(self, target):
            self.target = target

        def to_be_visible(self, *, timeout):
            assert self.target is catalog
            events.append(("catalog-visible", timeout))
            assert visible

        def to_have_count(self, expected, *, timeout):
            events.append((self.target, expected, timeout))
            actual = {"status": loading, "alert": errors}[self.target]
            assert actual == expected

    monkeypatch.setattr(readiness, "expect", Assertion)
    return page, app_ready, events


@pytest.mark.parametrize("timeout_ms", [15_000, 2_000])
def test_bayesian_ready_orders_shell_route_then_catalog_state(readiness, monkeypatch, timeout_ms):
    page, app_ready, events = _catalog_fixture(monkeypatch, readiness)
    readiness.wait_for_bayesian_ready(page, "en", ROUTE, timeout_ms=timeout_ms)
    app_ready.assert_called_once_with(page, "en", ROUTE, timeout_ms=timeout_ms)
    page.locator.assert_called_once_with('section[aria-labelledby="bayesian-study-catalog-title"]')
    assert events == [
        "app-ready",
        ("catalog-visible", timeout_ms),
        ("status", 0, timeout_ms),
        ("alert", 0, timeout_ms),
    ]
    page.wait_for_load_state.assert_not_called()
    page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("state", [{"visible": False}, {"loading": 1}, {"errors": 1}])
def test_bayesian_ready_does_not_accept_hidden_loading_or_failed_catalog(
    readiness, monkeypatch, state
):
    page, _, _ = _catalog_fixture(monkeypatch, readiness, **state)
    with pytest.raises(AssertionError):
        readiness.wait_for_bayesian_ready(page, "ko", ROUTE)


def test_bayesian_ready_preserves_app_readiness_failure(readiness, monkeypatch):
    page, app_ready, events = _catalog_fixture(monkeypatch, readiness)
    failure = AssertionError("synthetic app not ready")
    app_ready.side_effect = failure
    with pytest.raises(AssertionError) as caught:
        readiness.wait_for_bayesian_ready(page, "en", ROUTE)
    assert caught.value is failure
    page.locator.assert_not_called()
    assert events == []


def test_new_bo_journeys_use_catalog_readiness_only_for_bo_routes():
    for name in (
        "bo_vector_history",
        "bo_desirability_review",
        "bo_target_curve_preview",
        "bo_persistent_planning",
        "bo_augmentation",
        "bo_mixed_workflow",
    ):
        tree = ast.parse((ROOT / f"tests/e2e/{name}.py").read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        ready = [node for node in calls if node.func.id == "wait_for_bayesian_ready"]
        assert ready, name
        assert all(
            isinstance(node.args[2], ast.Name) and node.args[2].id == "ROUTE" for node in ready
        )
        for node in calls:
            if node.func.id == "wait_for_app_ready":
                assert isinstance(node.args[2], ast.Constant) and node.args[2].value == "/reports"
