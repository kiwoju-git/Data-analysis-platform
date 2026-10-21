"""The archive restart guard allows exact read-only routes, not POST in general."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

IDENTITY = "12345678-1234-4567-8123-123456789abc"


@pytest.fixture
def forbidden(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tests/e2e"))
    return importlib.import_module("bo_gp_release_resume")._forbidden


def request(path: str, method: str = "POST", body=None):
    return SimpleNamespace(
        url="http://127.0.0.1:8600" + path,
        method=method,
        post_data_json={} if body is None else body,
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/reports/capability",
        "/api/v1/reports/source-snapshot",
        "/api/v1/reports/artifacts/query",
        f"/api/v1/reports/{IDENTITY}/download",
    ],
)
def test_exact_managed_report_read_only_posts_are_allowed(forbidden, path) -> None:
    assert not forbidden(request(path))


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/reports",
        "/api/v1/reports/artifacts",
        "/api/v1/reports/artifacts/query/create",
        "/api/v1/reports/capability/create",
        "/api/v1/reports/not-a-uuid/download",
        f"/api/v1/reports/{IDENTITY}/download/delete",
        f"/api/v1/reports/{IDENTITY}/regenerate",
        "/other/reports/source-snapshot",
        "/api/v1/reports%2Fsource-snapshot",
        "/api/v1/analysis-runs",
        f"/api/v1/bayesian-studies/{IDENTITY}/recommendation-batches",
        f"/api/v1/bayesian-studies/{IDENTITY}/trials/{IDENTITY}/replicates",
        f"/api/v1/bayesian-studies/{IDENTITY}/observations",
    ],
)
def test_mutating_and_lookalike_posts_remain_forbidden(forbidden, path) -> None:
    assert forbidden(request(path))


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "CONNECT", "TRACE"])
def test_read_only_route_does_not_allow_mutating_or_unknown_methods(forbidden, method) -> None:
    assert forbidden(request("/api/v1/reports/capability", method))


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_safe_read_methods_are_allowed(forbidden, method) -> None:
    assert not forbidden(request(f"/api/v1/reports/{IDENTITY}", method))


@pytest.mark.parametrize("body", [{}, {"save_result": False}])
def test_exact_unsaved_prediction_is_allowed(forbidden, body) -> None:
    path = f"/api/v1/regression-models/{IDENTITY}/gaussian-process-predictions"
    assert not forbidden(request(path, body=body))


@pytest.mark.parametrize("body", [{"save_result": True}, {"save_result": "false"}, [], 0])
def test_saved_or_malformed_prediction_is_forbidden(forbidden, body) -> None:
    path = f"/api/v1/regression-models/{IDENTITY}/gaussian-process-predictions"
    assert forbidden(request(path, body=body))


@pytest.mark.parametrize(
    "path",
    [
        "/other/gaussian-process-predictions",
        "/api/v1/regression-models/not-a-uuid/gaussian-process-predictions",
        f"/api/v1/regression-models/{IDENTITY}/gaussian-process-predictions/save",
    ],
)
def test_unsaved_prediction_does_not_allow_suffix_lookalikes(forbidden, path) -> None:
    assert forbidden(request(path, body={"save_result": False}))
