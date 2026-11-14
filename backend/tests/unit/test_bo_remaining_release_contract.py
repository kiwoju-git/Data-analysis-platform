"""Pure evidence validation; these tests do not install or run a browser."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _contract():
    path = ROOT / "tests/e2e/bo_remaining_release.py"
    assert path.is_file(), "The exact-archive BO completion contract is missing"
    spec = importlib.util.spec_from_file_location("bo_remaining_release_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "override",
    [None, {"width": 0}, {"height": 721}, {"x": -2}, {"y": 150}, {"width": float("nan")}],
)
def test_report_capture_is_bounded_and_includes_every_chart(tmp_path, override):
    captures = []

    class Chart:
        def scroll_into_view_if_needed(self):
            pass

        def bounding_box(self):
            return {"x": 24, "y": 0, "width": 1200, "height": 576} | (override or {})

        def screenshot(self, *, path):
            captures.append(path.name)

    class Page:
        viewport_size = {"width": 1280, "height": 720}

        def evaluate(self, expression):
            assert expression == "window.scrollTo(0, 0)"

        def screenshot(self, *, path, full_page):
            assert full_page is False
            captures.append(path.name)

        def locator(self, selector):
            assert selector == "svg"
            return self

        def all(self):
            return [Chart() for _ in range(7)]

    if override is not None:
        with pytest.raises(AssertionError):
            _contract().capture_report_charts(Page(), tmp_path, "numeric")
        assert captures == ["numeric-server-stopped.png"]
        return
    assert _contract().capture_report_charts(Page(), tmp_path, "numeric") == 7
    assert captures == ["numeric-server-stopped.png"] + [
        f"numeric-server-stopped-chart-{index}.png" for index in range(1, 8)
    ]


def _view(kind: str) -> dict:
    source = {
        "study_id": "study-" + kind,
        "model_id": "model-" + kind,
        "model_sha256": "a" * 64,
        "history_sha256": "b" * 64,
    }
    payload = {
        "kind": "profiler_matrix",
        "schema_version": 2 if kind == "mixture" else 1,
        "source": source,
        "axes": [{"factor_id": "x", "points": [{"value": 1.0}]}],
    }
    saved = {
        "view_id": "view-" + kind,
        "source": source,
        "payload": payload,
        "view_sha256": _digest(payload),
    }
    return {
        "synthetic": True,
        "saved": saved,
        "report": {
            "descriptor": {"export_id": "report-" + kind, "sha256": "c" * 64},
            "path": "synthetic/" + kind + ".html",
        },
    }


def _initial() -> dict:
    return {
        "schema_version": 1,
        "phase": "initial",
        "status": "succeeded",
        "synthetic": True,
        "numeric": {
            "fit_posts": 1,
            "pageerrors": [],
            "saved_matrix": _view("numeric"),
            "legacy_renewal": {
                "synthetic": True,
                "old_bytes_unchanged": True,
                "fit_posts": 0,
                "pageerrors": [],
                "original_selection": {
                    "selection_id": "old",
                    "config_sha256": "d" * 64,
                    "result_sha256": "e" * 64,
                },
                "renewal": {
                    "selection": {
                        "selection_id": "new",
                        "config_sha256": "f" * 64,
                        "result_sha256": "1" * 64,
                    },
                    "lineage": {
                        "original_selection_id": "old",
                        "original_config_sha256": "d" * 64,
                        "original_result_sha256": "e" * 64,
                        "numerical_policy": "positive_beta_integral_v2",
                    },
                },
                "batch": {"batch_id": "batch"},
            },
        },
        "mixture": {
            "synthetic": True,
            "import_schema": 2,
            "completed_before": 8,
            "completed_after": 10,
            "candidate_count": 32,
            "source_model_sha256": "a" * 64,
            "next_model_sha256": "2" * 64,
            "saved_view_sha256": _view("mixture")["saved"]["view_sha256"],
            "saved_matrix": _view("mixture"),
        },
    }


def _phase(contract, original: dict, phase: str) -> dict:
    identity = contract.initial_identity(original)
    return {
        "schema_version": 1,
        "phase": phase,
        "status": "succeeded",
        "identity": identity,
        "identity_sha256": _digest(identity),
        "forbidden_mutation_requests": [],
        "pageerrors": [],
        "exact_sources_visible": phase == "resume",
        "original_server_unreachable": phase == "offline",
        "http_request_count": 0,
        "visible_report_count": 2 if phase == "offline" else 0,
    }


def test_complete_archive_bo_roundtrip_requires_both_installations() -> None:
    contract = _contract()
    original = _initial()
    resume = _phase(contract, original, "resume")
    offline = _phase(contract, original, "offline")
    result = contract.require_roundtrip(original, [resume, copy.deepcopy(resume)], offline)
    assert result["status"] == "succeeded"
    assert result["same_install_restart"] and result["second_install_shared_workspace"]
    with pytest.raises(ValueError):
        contract.require_roundtrip(original, [resume], offline)


@pytest.mark.parametrize("missing", ["numeric", "mixture"])
def test_archive_cannot_pass_with_only_the_older_bo_receipt(missing: str) -> None:
    contract = _contract()
    original = _initial()
    original.pop(missing)
    with pytest.raises(ValueError):
        contract.initial_identity(original)


@pytest.mark.parametrize("fault", ["payload", "model", "lineage", "refit", "unchanged"])
def test_initial_evidence_rejects_changed_source_or_legacy_recomputation(fault: str) -> None:
    contract = _contract()
    original = _initial()
    numeric = original["numeric"]
    if fault == "payload":
        numeric["saved_matrix"]["saved"]["payload"]["axes"][0]["points"][0]["value"] = 9
    elif fault == "model":
        original["mixture"]["source_model_sha256"] = "9" * 64
    elif fault == "lineage":
        numeric["legacy_renewal"]["renewal"]["lineage"]["original_result_sha256"] = "9" * 64
    elif fault == "refit":
        numeric["legacy_renewal"]["fit_posts"] = 1
    else:
        numeric["legacy_renewal"]["old_bytes_unchanged"] = False
    with pytest.raises(ValueError):
        contract.initial_identity(original)


@pytest.mark.parametrize(
    "fault", ["different_source", "mutation", "network", "running", "invisible"]
)
def test_roundtrip_rejects_false_restore_or_offline_success(fault: str) -> None:
    contract = _contract()
    original = _initial()
    resumes = [_phase(contract, original, "resume") for _ in range(2)]
    offline = _phase(contract, original, "offline")
    if fault == "different_source":
        resumes[1]["identity"]["numeric"]["view_sha256"] = "9" * 64
        resumes[1]["identity_sha256"] = _digest(resumes[1]["identity"])
    elif fault == "mutation":
        resumes[0]["forbidden_mutation_requests"] = ["POST /planning-models"]
    elif fault == "network":
        offline["http_request_count"] = 1
    elif fault == "running":
        offline["original_server_unreachable"] = False
    else:
        offline["visible_report_count"] = 1
    with pytest.raises(ValueError):
        contract.require_roundtrip(original, resumes, offline)


def test_archive_main_cannot_omit_or_make_completion_receipt_optional(monkeypatch) -> None:
    path = ROOT / "scripts/verify_linux_release.py"
    spec = importlib.util.spec_from_file_location("bo_remaining_archive_consumer", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec.loader.exec_module(module)
    with pytest.raises(ValueError):
        module.require_bo_remaining_roundtrip({}, [{}, {}], {})
    contract, original = _contract(), _initial()
    resumes = [{"bo_remaining_receipt": _phase(contract, original, "resume")} for _ in range(2)]
    assert (
        module.require_bo_remaining_roundtrip(
            {"bo_remaining_receipt": original},
            resumes,
            {"bo_remaining_receipt": _phase(contract, original, "offline")},
        )["status"]
        == "succeeded"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    main = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    parents = {child: node for node in ast.walk(main) for child in ast.iter_child_nodes(node)}
    calls = [
        node
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "require_bo_remaining_roundtrip"
    ]
    assert len(calls) == 1
    current = calls[0]
    while current is not main:
        current = parents[current]
        assert not isinstance(current, ast.If | ast.For | ast.While), "BO gate became optional"
