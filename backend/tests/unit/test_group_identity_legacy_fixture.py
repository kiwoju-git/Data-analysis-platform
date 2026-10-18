"""Static results calculated by the pinned pre-F01 source, not reconstructed names."""

import hashlib
import json
from pathlib import Path

import pytest

from app.services.analysis_run_comparisons import (
    _group_labels_from_result,
    _two_sample_t_group_labels,
)
from app.services.basic_eda_report import render_basic_eda_report
from app.services.hypothesis_report import render_hypothesis_report

FIXTURE = Path(__file__).parents[1] / "reference/fixtures/group_identity_legacy_base.json"


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("locale", ["ko", "en"])
def test_base_calculated_legacy_report_does_not_reconstruct_or_rewrite(
    index: int, locale: str
) -> None:
    fixture_bytes = FIXTURE.read_bytes()
    fixture = json.loads(fixture_bytes)
    assert fixture["source_commit"] == "0849aaa279e34a612c5c65d350cfccf220fe581e"
    assert fixture["current_app_helpers_used"] is False
    case = fixture["cases"][index]
    result = case["result"]
    canonical = json.dumps(
        result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == case["result_sha256"]
    assert all("group_value" not in group for group in result["groups"])
    renderer = render_basic_eda_report if index == 0 else render_hypothesis_report
    body = renderer(result, locale)
    assert body.variant_id != "unsupported"
    markup = body.render()
    assert (
        "전체 그룹값이 없습니다" if locale == "ko" else "does not contain full group values"
    ) in markup
    assert ("X" * 121 + "-A") not in markup
    assert result["group_count"] == (2 if index == 1 else 3)
    assert (
        json.dumps(
            result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        == canonical
    )
    assert FIXTURE.read_bytes() == fixture_bytes


def test_stored_comparisons_use_full_values_only_for_affected_paths() -> None:
    label = "X" * 117 + "..."
    result = {
        "groups": [
            {"group_label": label, "group_value": "X" * 121 + "-A"},
            {"group_label": label, "group_value": "X" * 121 + "-B"},
        ]
    }
    expected = ["X" * 121 + "-A", "X" * 121 + "-B"]
    assert _two_sample_t_group_labels(result) == expected
    assert _group_labels_from_result(result, prefer_full_value=True) == expected
    assert _group_labels_from_result(result) == [label, label]
    legacy = {"groups": [{"group_label": label}]}
    assert _two_sample_t_group_labels(legacy) == [label]
    assert _group_labels_from_result(legacy, prefer_full_value=True) == [label]
