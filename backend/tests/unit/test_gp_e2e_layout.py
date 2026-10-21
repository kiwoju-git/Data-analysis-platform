"""Harness assertions only; native browser evidence is recorded separately."""

import importlib
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("width", [1024, 1440])
@pytest.mark.parametrize(
    "invalid", [None, "main_left", "surface_right", "surface_left", "sidebar_right"]
)
def test_gp_layout_waits_for_drawer_then_checks_result_bounds(monkeypatch, width, invalid):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    fixture = importlib.import_module("gp_validation_extension")
    main_left = 0 if width < 1100 else 248
    geometry = {
        "width": width,
        "main_left": main_left,
        "main_right": width,
        "surface_left": main_left + 20,
        "surface_right": width - 20,
        "sidebar_right": -6 if width < 1100 else main_left,
        "sidebar_hidden": width < 1100,
    }
    if invalid:
        geometry[invalid] = width + 50 if invalid.endswith("right") else -20
    page = Mock()
    page.evaluate.side_effect = [None, geometry]
    if invalid:
        with pytest.raises(AssertionError):
            fixture._settled_gp_layout(page)
    else:
        assert fixture._settled_gp_layout(page) == geometry
    transition = page.evaluate.call_args_list[0].args[0]
    assert "getAnimations" in transition and ".finished" in transition
    assert "requestAnimationFrame" in transition and "setTimeout" not in transition
