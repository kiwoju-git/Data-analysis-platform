"""Shared display/solver fixtures use explicit independently calculated values."""

import json
from pathlib import Path

import pytest

from app.statistics.bo_desirability import DesirabilityGoal, composite_desirability
from app.statistics.bo_target_curve import GaussianTargetGoal


def test_progress_display_matches_stored_goal_policy() -> None:
    path = Path(__file__).resolve().parents[3] / "tests/fixtures/bo_progress_desirability.json"
    for case in json.loads(path.read_text(encoding="utf-8")):
        goals = []
        for raw in case["goals"]:
            fields = {key: value for key, value in raw.items() if key != "curve"}
            if curve := raw.get("curve"):
                goals.append(
                    GaussianTargetGoal(
                        **fields, **{key: value for key, value in curve.items() if key != "policy"}
                    )
                )
            else:
                goals.append(DesirabilityGoal(**fields))
        assert composite_desirability(case["values"], goals) == pytest.approx(
            case["expected"], rel=0, abs=1e-14
        ), case["name"]
