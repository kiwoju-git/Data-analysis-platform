"""Require actual archive UI evidence, separate from source/SSR test results."""

from __future__ import annotations

import math
import re
from typing import Any


def require_ui_release_evidence(english: Any, metrics: Any) -> dict[str, Any]:
    for receipt in (english, metrics):
        if (
            not isinstance(receipt, dict)
            or receipt.get("schema_version") != 1
            or receipt.get("status") != "succeeded"
        ):
            raise ValueError("Successful exact-archive UI receipts are required")
    scans = [*english.get("run_chart", []), *english.get("capability_errors", [])]
    text_scans = [
        item for item in scans if isinstance(item, dict) and "checked" in item
    ]
    sources = [
        item for item in scans if isinstance(item, dict) and "source_sha256" in item
    ]
    if (
        english.get("fixture") != "synthetic"
        or english.get("source_hashes_preserved") is not True
        or english.get("analysis_posts_during_locale_changes") != 0
        or len(text_scans) < 10
        or any(
            item.get("failures") != []
            or not isinstance(item.get("checked"), int)
            or item["checked"] <= 0
            for item in text_scans
        )
        or len(sources) != 2
        or {item.get("user_label_preserved") for item in sources} != {True, False}
        or any(
            re.fullmatch(r"[a-f0-9]{64}", str(item.get("source_sha256", ""))) is None
            for item in sources
        )
        or not any(
            item.get("cases") == 4 and item.get("drafts_preserved") is True
            for item in scans
            if isinstance(item, dict)
        )
    ):
        raise ValueError("English display-boundary evidence is incomplete")
    if (
        metrics.get("mechanism") != "chrome.tabs.setZoom/getZoom"
        or metrics.get("deviceScaleFactor_override") is not False
        or metrics.get("source_hash_preserved") is not True
        or metrics.get("analysis_posts_during_resize") != 0
        or metrics.get("pageerror_count") != 0
        or re.fullmatch(r"[a-f0-9]{64}", str(metrics.get("source_sha256", ""))) is None
    ):
        raise ValueError("Real browser zoom and unchanged-source evidence is required")
    steps = metrics.get("steps")
    if (
        not isinstance(steps, list)
        or not steps
        or not all(isinstance(item, dict) for item in steps)
    ):
        raise ValueError("Metric geometry evidence is missing")
    required = {
        (locale, width, zoom)
        for locale in ("ko", "en")
        for width in (1024, 1280, 1440)
        for zoom in (1.0, 1.25, 1.5)
    }
    actual = {
        (step.get("locale"), step.get("physicalViewportWidth"), step.get("browserZoom"))
        for step in steps
    }
    if not required.issubset(actual) or {step.get("columns") for step in steps} != {
        1,
        2,
        4,
    }:
        raise ValueError("Metric viewport/zoom/column coverage is incomplete")
    for step in steps:
        cards = step.get("cards")
        if not isinstance(cards, list) or len(cards) != 4:
            raise ValueError("Four measured metric cards are required")
        for card in cards:
            if not isinstance(card, dict):
                raise ValueError("Invalid metric geometry")
            label, value = card.get("label"), card.get("value")
            if not isinstance(label, dict) or not isinstance(value, dict):
                raise ValueError("Separate label/value rectangles are required")
            top, bottom = value.get("top"), label.get("bottom")
            if (
                not isinstance(top, (int, float))
                or not isinstance(bottom, (int, float))
                or not math.isfinite(top - bottom)
                or top - bottom < 5
            ):
                raise ValueError("Metric label/value spacing was not verified")
    return {
        "status": "passed",
        "english_scope": english.get("coverage"),
        "geometry_steps": len(steps),
        "source_preserved": True,
    }
