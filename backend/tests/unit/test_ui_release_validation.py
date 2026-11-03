from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "ui_release_validation",
    Path(__file__).resolve().parents[3] / "scripts/ui_release_validation.py",
)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def receipts() -> tuple[dict, dict]:
    english = {
        "schema_version": 1,
        "status": "succeeded",
        "fixture": "synthetic",
        "source_hashes_preserved": True,
        "analysis_posts_during_locale_changes": 0,
        "run_chart": [{"checked": 10, "failures": []} for _ in range(10)]
        + [
            {"source_sha256": "a" * 64, "user_label_preserved": False},
            {"source_sha256": "b" * 64, "user_label_preserved": True},
        ],
        "capability_errors": [{"cases": 4, "drafts_preserved": True}],
        "coverage": "Run/Capability",
    }
    metrics = {
        "schema_version": 1,
        "status": "succeeded",
        "mechanism": "chrome.tabs.setZoom/getZoom",
        "deviceScaleFactor_override": False,
        "source_hash_preserved": True,
        "analysis_posts_during_resize": 0,
        "pageerror_count": 0,
        "source_sha256": "c" * 64,
        "steps": [
            {
                "locale": locale,
                "physicalViewportWidth": width,
                "browserZoom": zoom,
                "columns": columns,
                "cards": [{"label": {"bottom": 20}, "value": {"top": 28}} for _ in range(4)],
            }
            for locale in ("ko", "en")
            for width, columns in ((1024, 1), (1280, 2), (1440, 4))
            for zoom in (1.0, 1.25, 1.5)
        ],
    }
    return english, metrics


def test_complete_receipts_are_required() -> None:
    assert module.require_ui_release_evidence(*receipts())["status"] == "passed"


@pytest.mark.parametrize(
    "failure", ["missing", "running", "hangul", "changed", "no-zoom", "overlap", "nan"]
)
def test_incomplete_or_failed_ui_cannot_admit_release(failure: str) -> None:
    english, metrics = receipts()
    if failure == "missing":
        english = {}
    elif failure == "running":
        metrics["status"] = "running"
    elif failure == "hangul":
        english["run_chart"][0]["failures"] = ["synthetic missing system translation"]
    elif failure == "changed":
        english["analysis_posts_during_locale_changes"] = 1
    elif failure == "no-zoom":
        metrics["steps"] = metrics["steps"][:1]
    elif failure == "overlap":
        metrics["steps"][0]["cards"][0]["value"]["top"] = 20
    else:
        metrics["steps"][0]["cards"][0]["value"]["top"] = float("nan")
    with pytest.raises(ValueError):
        module.require_ui_release_evidence(english, metrics)
