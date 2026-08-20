from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "pls_minitab_wine_aroma_reference.json"


def test_minitab_wine_aroma_reference_uses_press_selection_contract() -> None:
    reference = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = reference["rows"]
    total_sum_squares = [float(row["error"]) / (1.0 - float(row["r_squared"])) for row in rows]
    reference_tss = sum(total_sum_squares) / len(total_sum_squares)

    assert total_sum_squares == pytest.approx([reference_tss] * len(rows), rel=2e-5)
    for row in rows:
        expected = 1.0 - float(row["press"]) / reference_tss
        assert float(row["predicted_r_squared"]) == pytest.approx(expected, abs=2e-6)

    selected = max(rows, key=lambda row: float(row["predicted_r_squared"]))
    assert selected["components"] == reference["selected_components"] == 4
    assert selected["predicted_r_squared"] == pytest.approx(0.559056, abs=1e-6)
