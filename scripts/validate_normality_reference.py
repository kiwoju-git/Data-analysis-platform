from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_normality_reference import _case_values, _load_fixture


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate generated SciPy normality reference results.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("backend/tests/reference/fixtures/normality_input.json"),
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path("backend/tests/reference/fixtures/normality_scipy_reference.json"),
    )
    args = parser.parse_args()

    fixture = _load_fixture(args.input)
    reference = load_reference(args.reference)
    summary = validate_reference(reference, fixture)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def load_reference(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("reference payload must be an object")
    return payload


def validate_reference(
    reference: dict[str, Any],
    fixture: dict[str, Any],
) -> dict[str, object]:
    if reference.get("reference_schema_version") != 1:
        raise ValueError("unsupported reference_schema_version")
    if reference.get("source_fixture_id") != fixture.get("fixture_id"):
        raise ValueError("reference source_fixture_id does not match input fixture")
    python_version = _string(reference.get("python_version"), "python_version")
    if not python_version.startswith("3.10."):
        raise ValueError(f"python_version must be 3.10.x, got {python_version!r}")
    dependencies = _dict(reference.get("dependencies"), "dependencies")
    numpy_version = _string(dependencies.get("numpy"), "dependencies.numpy")
    scipy_version = _string(dependencies.get("scipy"), "dependencies.scipy")

    fixture_cases = {
        _string(case.get("case_id"), "case.case_id"): case for case in fixture["cases"]
    }
    reference_cases = _list(reference.get("cases"), "cases")
    if len(reference_cases) != len(fixture_cases):
        raise ValueError("reference case count does not match input fixture")

    seen: set[str] = set()
    for raw_case in reference_cases:
        case = _dict(raw_case, "case")
        case_id = _string(case.get("case_id"), "case.case_id")
        if case_id in seen:
            raise ValueError(f"duplicate reference case_id: {case_id}")
        seen.add(case_id)
        fixture_case = fixture_cases.get(case_id)
        if fixture_case is None:
            raise ValueError(f"reference case not present in input fixture: {case_id}")
        _validate_case(case, fixture_case)

    missing = set(fixture_cases) - seen
    if missing:
        raise ValueError(f"reference missing fixture cases: {sorted(missing)}")

    return {
        "status": "passed",
        "case_count": len(reference_cases),
        "numpy": numpy_version,
        "scipy": scipy_version,
        "python_version": python_version,
    }


def _validate_case(case: dict[str, Any], fixture_case: dict[str, Any]) -> None:
    expected_n = _expected_n(fixture_case)
    if case.get("n") != expected_n:
        raise ValueError(f"{fixture_case['case_id']}: n does not match fixture")
    if case.get("methods") != fixture_case.get("methods"):
        raise ValueError(f"{fixture_case['case_id']}: methods do not match fixture")
    expected_warning_codes = list(fixture_case.get("expected_warning_codes", []))
    if case.get("expected_warning_codes", []) != expected_warning_codes:
        raise ValueError(f"{fixture_case['case_id']}: expected_warning_codes mismatch")

    shapiro = _dict(case.get("shapiro"), f"{fixture_case['case_id']}.shapiro")
    _finite(shapiro.get("statistic"), f"{fixture_case['case_id']}.shapiro.statistic")
    _probability(shapiro.get("pvalue"), f"{fixture_case['case_id']}.shapiro.pvalue")

    anderson = _dict(case.get("anderson_norm"), f"{fixture_case['case_id']}.anderson_norm")
    _finite(anderson.get("statistic"), f"{fixture_case['case_id']}.anderson_norm.statistic")
    critical_values = _number_list(
        anderson.get("critical_values"),
        f"{fixture_case['case_id']}.anderson_norm.critical_values",
    )
    significance_level = _number_list(
        anderson.get("significance_level"),
        f"{fixture_case['case_id']}.anderson_norm.significance_level",
    )
    if len(critical_values) == 0:
        raise ValueError(f"{fixture_case['case_id']}: Anderson critical values are empty")
    if len(critical_values) != len(significance_level):
        raise ValueError(f"{fixture_case['case_id']}: Anderson level arrays do not align")


def _expected_n(fixture_case: dict[str, Any]) -> int:
    if "values" in fixture_case:
        values = _list(fixture_case["values"], "values")
        return len(values)

    class CountOnlyNp:
        @staticmethod
        def linspace(start: float, stop: float, count: int, *, dtype: object) -> list[float]:
            return [start if index == 0 else stop for index in range(count)]

    values = _case_values(fixture_case, CountOnlyNp())
    return len(values)


def _dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _probability(value: Any, name: str) -> float:
    parsed = _finite(value, name)
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return parsed


def _number_list(value: Any, name: str) -> list[float]:
    values = _list(value, name)
    return [_finite(item, f"{name}[]") for item in values]


if __name__ == "__main__":
    raise SystemExit(main())
