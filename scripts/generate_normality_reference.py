from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate SciPy-backed normality reference results from synthetic inputs.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("backend/tests/reference/fixtures/normality_input.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/tests/reference/fixtures/normality_scipy_reference.json"),
    )
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 10):
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": "python_version_unsupported",
                    "python_version": sys.version,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        return 2

    try:
        import numpy as np
        from scipy import stats
    except ModuleNotFoundError as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": "stat_dependency_missing",
                    "missing_module": exc.name,
                    "python_version": sys.version,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        return 2

    fixture = _load_fixture(args.input)
    cases = []
    for case in fixture["cases"]:
        values = _case_values(case, np)
        shapiro = stats.shapiro(values)
        anderson = stats.anderson(values, dist="norm")
        _require_finite("shapiro.statistic", float(shapiro.statistic))
        _require_probability("shapiro.pvalue", float(shapiro.pvalue))
        _require_finite("anderson.statistic", float(anderson.statistic))
        shapiro_payload: dict[str, object] = {
            "statistic": float(shapiro.statistic),
            "pvalue": float(shapiro.pvalue),
        }
        if int(values.size) > 5000:
            shapiro_payload["scipy_note"] = "p-value accuracy is limited for N > 5000"
        cases.append(
            {
                "case_id": case["case_id"],
                "n": int(values.size),
                "methods": list(case["methods"]),
                "expected_warning_codes": list(case.get("expected_warning_codes", [])),
                "shapiro": shapiro_payload,
                "anderson_norm": {
                    "statistic": float(anderson.statistic),
                    "critical_values": [float(value) for value in anderson.critical_values],
                    "significance_level": [
                        float(value) for value in anderson.significance_level
                    ],
                },
            },
        )

    payload = {
        "reference_schema_version": 1,
        "source_fixture_id": fixture["fixture_id"],
        "generator": "scripts/generate_normality_reference.py",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "passed",
                "output": str(args.output),
                "case_count": len(cases),
                "numpy": payload["dependencies"]["numpy"],
                "scipy": payload["dependencies"]["scipy"],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    return 0


def _load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("fixture_schema_version") != 1:
        raise ValueError("unsupported fixture_schema_version")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixture cases must be a non-empty list")
    return payload


def _case_values(case: dict[str, Any], np: Any) -> Any:
    if "values" in case:
        values = case["values"]
        if not isinstance(values, list) or len(values) < 3:
            raise ValueError(f"{case.get('case_id')}: values must contain at least 3 entries")
        return np.array(values, dtype=float)

    spec = case.get("values_spec")
    if not isinstance(spec, dict):
        raise ValueError(f"{case.get('case_id')}: values or values_spec is required")
    if spec.get("kind") != "linear_space":
        raise ValueError(f"{case.get('case_id')}: unsupported values_spec kind")
    count = spec.get("count")
    if not isinstance(count, int) or count < 3:
        raise ValueError(f"{case.get('case_id')}: values_spec count must be >= 3")
    start = _number(spec.get("start"), "start")
    stop = _number(spec.get("stop"), "stop")
    return np.linspace(start, stop, count, dtype=float)


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    parsed = float(value)
    _require_finite(name, parsed)
    return parsed


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise RuntimeError(f"{name} is not finite")


def _require_probability(name: str, value: float) -> None:
    _require_finite(name, value)
    if value < 0.0 or value > 1.0:
        raise RuntimeError(f"{name} is outside [0, 1]")


if __name__ == "__main__":
    raise SystemExit(main())
