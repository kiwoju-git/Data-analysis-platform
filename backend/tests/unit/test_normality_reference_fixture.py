import json
from pathlib import Path

from scripts.generate_normality_reference import _case_values, _load_fixture

FIXTURE_PATH = Path("backend/tests/reference/fixtures/normality_input.json")


def test_normality_reference_input_fixture_contains_no_expected_statistics() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    forbidden_keys = {"pvalue", "p_value", "statistic", "critical_values"}

    assert payload["fixture_schema_version"] == 1
    assert payload["cases"]
    for case in payload["cases"]:
        assert forbidden_keys.isdisjoint(case)
        assert "case_id" in case
        assert "methods" in case
        assert "values" in case or "values_spec" in case


def test_normality_reference_input_fixture_loads_with_supported_schema() -> None:
    payload = _load_fixture(FIXTURE_PATH)

    assert payload["fixture_id"] == "normality_reference_inputs_v1"


def test_normality_reference_linear_space_spec_expands_without_scipy() -> None:
    class MinimalNp:
        @staticmethod
        def linspace(start: float, stop: float, count: int, *, dtype: object) -> list[float]:
            assert dtype is float
            step = (stop - start) / (count - 1)
            return [start + step * index for index in range(count)]

    values = _case_values(
        {
            "case_id": "linear",
            "values_spec": {
                "kind": "linear_space",
                "start": -1,
                "stop": 1,
                "count": 5,
            },
        },
        MinimalNp(),
    )

    assert values == [-1.0, -0.5, 0.0, 0.5, 1.0]
