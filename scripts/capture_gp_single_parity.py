"""Capture a declared baseline checkout; not an independent statistical reference."""

import argparse
import json
from pathlib import Path

import numpy as np

from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn, GaussianProcessOptions, calculate_gaussian_process_regression,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline-sha", required=True)
    args = parser.parse_args()
    rng = np.random.default_rng(938)
    x = rng.uniform(-2, 2, (24, 2))
    y = np.sin(x[:, 0]) + 0.3 * x[:, 1] ** 2 + rng.normal(0, 0.12, 24)
    rows = [[*(str(v) for v in row), str(response)] for row, response in zip(x, y)]
    columns = [GaussianProcessColumn(name, index, name, "decimal", "continuous", role, None)
               for index, (name, role) in enumerate([("x1", "predictor"), ("x2", "predictor"), ("y", "response")])]
    results = {}
    for preset in ("matern_5_2_ard", "matern_3_2_ard", "rbf_ard", "rational_quadratic"):
        result = calculate_gaussian_process_regression(rows, columns[-1], columns[:-1], options=GaussianProcessOptions(
            kernel_preset=preset, optimizer_restarts=0, cv_folds=3, random_seed=41,
            profile_points=10, surface_grid_size=10, plot_point_limit=100,
        ))
        results[preset] = {key: result[key] for key in ("model_summary", "kernel", "diagnostics", "warnings")}
    args.output.write_text(json.dumps({"baseline_sha": args.baseline_sha,
        "purpose": "Legacy numerical parity; independent reference is maintained separately.",
        "absolute_tolerance": 1e-8, "relative_tolerance": 1e-7,
        "rows": rows, "results": results}, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
