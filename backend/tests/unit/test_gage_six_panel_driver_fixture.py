"""Validate the synthetic browser input independently of application calculations."""

import csv
import importlib
from collections import Counter
from io import StringIO
from pathlib import Path
from statistics import fmean

import pytest


@pytest.fixture
def driver(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    return importlib.import_module("gage_six_panel")


def test_hand60_browser_fixture_and_type7_operator_quantiles(driver):
    rows = list(csv.DictReader(StringIO(driver._fixture())))
    counts = Counter((row["part"], row["operator"]) for row in rows)
    assert len(rows) == 60 and len(counts) == 30 and set(counts.values()) == {2}
    assert list(dict.fromkeys(row["part"] for row in rows)) == [str(i) for i in range(1, 11)]
    assert sorted({row["part"] for row in rows})[1] == "10"
    assert fmean(float(row[driver.MEASUREMENT]) for row in rows if row["part"] == "10") == 68
    values = sorted(float(row[driver.MEASUREMENT]) for row in rows if row["operator"] == "O00")
    assert len(values) == 20
    assert fmean(values) == pytest.approx(58.8, abs=1e-12)
    assert values[4] * 0.25 + values[5] * 0.75 == pytest.approx(53.85, abs=1e-12)
    assert (values[9] + values[10]) / 2 == pytest.approx(58.8, abs=1e-12)
    assert values[14] * 0.75 + values[15] * 0.25 == pytest.approx(63.75, abs=1e-12)
    assert values[0] == 49.7 and values[-1] == 67.9


def test_filter_retains_complete_cells_and_pagination_fixture_has_two_pages(driver):
    rows = list(csv.DictReader(StringIO(driver._fixture())))
    filtered = [row for row in rows if float(row[driver.MEASUREMENT]) < 67]
    cells = Counter((row["part"], row["operator"]) for row in filtered)
    assert len(filtered) == 54 and len(cells) == 27 and set(cells.values()) == {2}
    large = list(csv.DictReader(StringIO(driver._fixture(11, 4))))
    assert len(large) == 88
    assert len({row["part"] for row in large}) == 11
    assert len({row["operator"] for row in large}) == 4
