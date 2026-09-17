"""Synthetic sensitivity study, not a claim that smoothing always improves CV."""

from __future__ import annotations

import json
import time

import numpy as np

from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    calculate_gaussian_process_regression,
)


def main() -> None:
    rng = np.random.default_rng(872)
    grid = np.linspace(-2.5, 2.5, 50).reshape(-1, 1)
    multi = rng.normal(size=(50, 3))
    cases = [
        ("smooth_noisy", grid, np.sin(grid[:, 0]) + rng.normal(0, 0.2, 50)),
        ("rapid_noisy", grid, np.sin(7 * grid[:, 0]) + rng.normal(0, 0.12, 50)),
        ("multivariate", multi, np.sin(multi[:, 0]) + 0.3 * multi[:, 1] ** 2
         - multi[:, 2] + rng.normal(0, 0.15, 50)),
    ]
    evidence = []
    for name, x, y in cases:
        def column(index: int, response: bool = False) -> GaussianProcessColumn:
            return GaussianProcessColumn(
                column_id="y" if response else f"x{index}", column_index=index,
                display_name="y" if response else f"x{index}", data_type="decimal",
                measurement_level="continuous", role="response" if response else "predictor",
                unit=None,
            )
        rows = [[*map(str, row), str(value)] for row, value in zip(x, y, strict=True)]
        for lower in (0.01, 0.5, 1.0):
            started = time.monotonic()
            result = calculate_gaussian_process_regression(
                rows, column(x.shape[1], True), [column(i) for i in range(x.shape[1])],
                options=GaussianProcessOptions(
                    kernel_preset="rbf_ard", length_scale_lower=lower,
                    validation_method="k_fold", cv_folds=5, optimizer_restarts=0,
                    cv_optimizer_restarts=0, random_seed=872,
                    profile_points=10, surface_grid_size=10, time_budget_seconds=120,
                ),
            )
            evidence.append({"case": name, "lower": lower, "n": len(y),
                "predictors": x.shape[1], "elapsed_seconds": time.monotonic()-started,
                "summary": result["model_summary"], "warnings": result["warnings"]})
    print(json.dumps(evidence, ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
