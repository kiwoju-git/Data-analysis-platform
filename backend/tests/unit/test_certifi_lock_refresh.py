from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


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
