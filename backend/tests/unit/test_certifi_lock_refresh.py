from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml


def refresh_module(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "certifi_refresh", root / "scripts/refresh_certifi_lock.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def test_only_certifi_version_and_hash_may_change(monkeypatch):
    module = refresh_module(monkeypatch)
    before = {
        "certifi": {"version": "old", "sha256": "a"},
        "numpy": {"version": "2.2.6", "sha256": "b"},
    }
    after = {**before, "certifi": {"version": "2026.10.19", "sha256": "c"}}
    module.validate_refresh(before, after)
    with pytest.raises(ValueError, match="Unrelated"):
        module.validate_refresh(before, {**after, "numpy": {"version": "2.3", "sha256": "d"}})
    with pytest.raises(ValueError, match="distribution set"):
        module.validate_refresh(before, {**after, "extra": {}})
    with pytest.raises(ValueError, match="Unexpected certifi"):
        module.validate_refresh(before, before)


def test_native_refresh_workflow_is_valid_and_not_a_release_gate():
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load(
        (root / ".github/workflows/security-lock-refresh.yml").read_text("utf-8")
    )
    triggers = workflow.get("on", workflow.get(True))
    assert "workflow_call" in triggers
    job = workflow["jobs"]["native-certifi"]
    assert job["permissions"] == {"contents": "read"}
    assert {entry["target"] for entry in job["strategy"]["matrix"]["include"]} == {
        "py310-win",
        "py311-linux",
        "py312-linux",
    }
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "refresh_certifi_lock.py" in commands
    assert "release_readiness" not in commands
