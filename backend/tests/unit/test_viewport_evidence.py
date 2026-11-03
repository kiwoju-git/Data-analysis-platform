"""Screenshot diagnostics must reject an empty or occluded region."""

from __future__ import annotations

import base64
import binascii
import importlib
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def capture(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tests/e2e"))
    return importlib.import_module("viewport_evidence").capture_viewport_evidence


def fixtures() -> tuple[Mock, Mock]:
    page = Mock()
    page.context.new_cdp_session.return_value.send.return_value = {
        "data": base64.b64encode(b"\x89PNG\r\n\x1a\nsynthetic-fixture").decode("ascii")
    }
    page.evaluate.side_effect = [None, {"distinctColors": 64}]
    anchor = Mock()
    anchor.evaluate.side_effect = [
        None,
        {
            "left": 10,
            "right": 310,
            "top": 20,
            "bottom": 320,
            "viewportWidth": 683,
            "viewportHeight": 667,
            "centerVisible": True,
        },
    ]
    return page, anchor


def test_captures_visible_viewport_not_zoomed_element_clip(capture, tmp_path: Path):
    page, anchor = fixtures()
    path = tmp_path / "zoom-150.png"
    result = capture(page, anchor, path)
    anchor.scroll_into_view_if_needed.assert_called_once_with()
    page.context.new_cdp_session.assert_called_once_with(page)
    session = page.context.new_cdp_session.return_value
    session.send.assert_called_once_with(
        "Page.captureScreenshot",
        {"format": "png", "fromSurface": True, "captureBeyondViewport": False},
    )
    session.detach.assert_called_once_with()
    page.screenshot.assert_not_called()
    anchor.screenshot.assert_not_called()
    assert result["capture"] == "viewport"
    assert result["provider"] == "CDP Page.captureScreenshot (clip omitted)"
    assert path.read_bytes() == b"\x89PNG\r\n\x1a\nsynthetic-fixture"
    assert result["pixels"]["distinctColors"] == 64
    assert result["geometry"]["viewportWidth"] == 683


@pytest.mark.parametrize("colors", [0, 1, 15])
def test_blank_capture_is_not_success_evidence(capture, tmp_path: Path, colors: int):
    page, anchor = fixtures()
    page.evaluate.side_effect = [None, {"distinctColors": colors}]
    with pytest.raises(AssertionError):
        capture(page, anchor, tmp_path / "blank.png")


@pytest.mark.parametrize("change", [{"right": 10}, {"bottom": 20}, {"centerVisible": False}])
def test_hidden_or_occluded_anchor_is_rejected(capture, tmp_path: Path, change: dict):
    page, anchor = fixtures()
    geometry = {
        "left": 10,
        "right": 310,
        "top": 20,
        "bottom": 320,
        "viewportWidth": 683,
        "viewportHeight": 667,
        "centerVisible": True,
    }
    anchor.evaluate.side_effect = [None, {**geometry, **change}]
    with pytest.raises(AssertionError):
        capture(page, anchor, tmp_path / "hidden.png")
    page.screenshot.assert_not_called()
    page.context.new_cdp_session.assert_not_called()


def test_cdp_session_detaches_on_capture_failure(capture, tmp_path: Path):
    page, anchor = fixtures()
    session = page.context.new_cdp_session.return_value
    session.send.side_effect = RuntimeError("synthetic capture failure")
    with pytest.raises(RuntimeError, match="synthetic capture failure"):
        capture(page, anchor, tmp_path / "failed.png")
    session.detach.assert_called_once_with()
    assert not (tmp_path / "failed.png").exists()


@pytest.mark.parametrize("data", ["not-base64", base64.b64encode(b"not-png").decode("ascii")])
def test_invalid_capture_bytes_are_rejected(capture, tmp_path: Path, data: str):
    page, anchor = fixtures()
    session = page.context.new_cdp_session.return_value
    session.send.return_value = {"data": data}
    with pytest.raises((AssertionError, binascii.Error)):
        capture(page, anchor, tmp_path / "invalid.png")
    session.detach.assert_called_once_with()
    assert not (tmp_path / "invalid.png").exists()
