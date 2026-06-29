from __future__ import annotations

import importlib.metadata
import json
import math
import platform
import sys
from typing import Any


def main() -> int:
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

    normal_values = np.array(
        [-1.5, -0.9, -0.4, -0.1, 0.0, 0.2, 0.5, 0.8, 1.1, 1.6],
        dtype=float,
    )
    group_a = np.array([8.0, 9.0, 10.0, 11.0, 12.0], dtype=float)
    group_b = np.array([7.0, 8.0, 9.0, 10.0, 11.0], dtype=float)
    group_c = np.array([6.0, 8.0, 10.0, 12.0, 14.0], dtype=float)

    shapiro = stats.shapiro(normal_values)
    _require_probability("shapiro_pvalue", float(shapiro.pvalue))
    _require_finite("shapiro_statistic", float(shapiro.statistic))

    anderson = stats.anderson(normal_values, dist="norm")
    _require_finite("anderson_statistic", float(anderson.statistic))
    if len(anderson.critical_values) == 0 or len(anderson.significance_level) == 0:
        raise RuntimeError("anderson returned no critical values")

    levene_mean = stats.levene(group_a, group_b, group_c, center="mean")
    _require_finite("levene_mean_statistic", float(levene_mean.statistic))
    _require_probability("levene_mean_pvalue", float(levene_mean.pvalue))

    brown_forsythe = stats.levene(group_a, group_b, group_c, center="median")
    _require_finite("brown_forsythe_statistic", float(brown_forsythe.statistic))
    _require_probability("brown_forsythe_pvalue", float(brown_forsythe.pvalue))

    payload: dict[str, Any] = {
        "status": "passed",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "smoke_results": {
            "shapiro": {
                "statistic": float(shapiro.statistic),
                "pvalue": float(shapiro.pvalue),
                "n": int(normal_values.size),
            },
            "anderson_norm": {
                "statistic": float(anderson.statistic),
                "critical_values": [float(value) for value in anderson.critical_values],
                "significance_level": [
                    float(value) for value in anderson.significance_level
                ],
                "n": int(normal_values.size),
            },
            "levene_mean": {
                "statistic": float(levene_mean.statistic),
                "pvalue": float(levene_mean.pvalue),
                "group_count": 3,
            },
            "brown_forsythe": {
                "statistic": float(brown_forsythe.statistic),
                "pvalue": float(brown_forsythe.pvalue),
                "group_count": 3,
            },
        },
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise RuntimeError(f"{name} is not finite")


def _require_probability(name: str, value: float) -> None:
    _require_finite(name, value)
    if value < 0.0 or value > 1.0:
        raise RuntimeError(f"{name} is outside [0, 1]")


if __name__ == "__main__":
    raise SystemExit(main())
