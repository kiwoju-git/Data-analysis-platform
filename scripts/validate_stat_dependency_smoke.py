from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate recorded statistical dependency smoke output.",
    )
    parser.add_argument("result_path", type=Path)
    args = parser.parse_args()

    payload = load_payload(args.result_path)
    summary = validate_payload(payload)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def load_payload(result_path: Path) -> dict[str, Any]:
    payload = json.loads(result_path.read_text(encoding="utf-8-sig"))
    _require_dict(payload, "payload")
    return payload


def validate_payload(payload: dict[str, Any]) -> dict[str, str]:
    _require_equal(payload.get("status"), "passed", "status")
    python_version = _require_string(payload.get("python_version"), "python_version")
    if not python_version.startswith("3.10."):
        raise ValueError(f"python_version must be 3.10.x, got {python_version!r}")

    dependencies = _require_dict(payload.get("dependencies"), "dependencies")
    _require_string(dependencies.get("numpy"), "dependencies.numpy")
    _require_string(dependencies.get("scipy"), "dependencies.scipy")

    smoke_results = _require_dict(payload.get("smoke_results"), "smoke_results")
    _validate_probability_result(smoke_results, "shapiro")
    _validate_anderson(smoke_results)
    _validate_probability_result(smoke_results, "levene_mean")
    _validate_probability_result(smoke_results, "brown_forsythe")

    return {
        "status": "passed",
        "numpy": dependencies["numpy"],
        "scipy": dependencies["scipy"],
        "python_version": python_version,
    }


def _validate_probability_result(smoke_results: dict[str, Any], key: str) -> None:
    result = _require_dict(smoke_results.get(key), f"smoke_results.{key}")
    _require_finite_number(result.get("statistic"), f"{key}.statistic")
    pvalue = _require_finite_number(result.get("pvalue"), f"{key}.pvalue")
    if pvalue < 0.0 or pvalue > 1.0:
        raise ValueError(f"{key}.pvalue must be in [0, 1], got {pvalue!r}")


def _validate_anderson(smoke_results: dict[str, Any]) -> None:
    result = _require_dict(smoke_results.get("anderson_norm"), "smoke_results.anderson_norm")
    _require_finite_number(result.get("statistic"), "anderson_norm.statistic")
    critical_values = _require_number_list(
        result.get("critical_values"),
        "anderson_norm.critical_values",
    )
    significance_level = _require_number_list(
        result.get("significance_level"),
        "anderson_norm.significance_level",
    )
    if len(critical_values) == 0:
        raise ValueError("anderson_norm.critical_values must not be empty")
    if len(critical_values) != len(significance_level):
        raise ValueError("anderson critical values and significance levels must align")


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_equal(value: Any, expected: str, name: str) -> None:
    if value != expected:
        raise ValueError(f"{name} must be {expected!r}, got {value!r}")


def _require_finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _require_number_list(value: Any, name: str) -> list[float]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return [_require_finite_number(item, f"{name}[]") for item in value]


if __name__ == "__main__":
    raise SystemExit(main())
