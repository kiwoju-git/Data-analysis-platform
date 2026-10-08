"""Independent sklearn reference with no application imports.

Windows tests default to the committed static reference. Linux and explicitly
configured hosted Windows optimized-kernel tests may call evaluate_frozen_case
on its saved inputs/splits to isolate BLAS/CPU optimizer drift; this never
regenerates inputs or overwrites a fixture. Fixed-hyperparameter posterior
tests remain static on all supported platforms.
"""

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import scipy
import sklearn
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    ConstantKernel,
    Matern,
    RBF,
    RationalQuadratic,
    WhiteKernel,
)
from sklearn.model_selection import KFold
from threadpoolctl import threadpool_limits

PRESETS = ("matern_5_2_ard", "matern_3_2_ard", "rbf_ard", "rational_quadratic")


def kernel(preset, d):
    if preset.startswith("matern"):
        base = Matern(np.ones(d), (0.01, 100), nu=2.5 if preset == PRESETS[0] else 1.5)
    elif preset == "rbf_ard":
        base = RBF(np.ones(d), (0.01, 100))
    else:
        base = RationalQuadratic(1, 1, (0.01, 100), (0.01, 100))
    return ConstantKernel(1, (0.001, 1000)) * base + WhiteKernel(0.01, (1e-8, 10))


def independent_fit(x, y, preset, seed):
    xm, xs = x.mean(axis=0), x.std(axis=0, ddof=1)
    ym, ys = y.mean(), y.std(ddof=1)
    model = GaussianProcessRegressor(
        kernel=kernel(preset, x.shape[1]),
        alpha=1e-8,
        normalize_y=False,
        n_restarts_optimizer=0,
        random_state=seed,
    )
    model.fit((x - xm) / xs, (y - ym) / ys)
    return model, xm, xs, ym, ys


def _evaluate_case(name, x, y, splits, seed):
    candidates = []
    for priority, preset in enumerate(PRESETS):
        mean, sd = np.empty(len(y)), np.empty(len(y))
        for fold, (train, test) in enumerate(splits):
            model, xm, xs, ym, ys = independent_fit(
                x[train], y[train], preset, seed + priority * 104729 + fold * 1009
            )
            mu, sigma = model.predict((x[test] - xm) / xs, return_std=True)
            mean[test], sd[test] = mu * ys + ym, sigma * ys
        residual = y - mean
        variance = np.maximum(sd**2, np.finfo(float).tiny)
        press = float(np.sum(residual**2))
        metrics = {
            "press": press,
            "predicted_r_squared": 1 - press / float(np.sum((y - y.mean()) ** 2)),
            "rmse": float(np.sqrt(np.mean(residual**2))),
            "mae": float(np.mean(np.abs(residual))),
            "nlpd": float(
                np.mean(
                    0.5 * np.log(2 * np.pi * variance) + 0.5 * residual**2 / variance
                )
            ),
            "interval_coverage_95": float(
                np.mean(np.abs(residual) <= 1.959963984540054 * sd)
            ),
            "mean_interval_width": float(np.mean(2 * 1.959963984540054 * sd)),
        }
        model, _, _, _, _ = independent_fit(x, y, preset, seed + priority * 104729)
        candidates.append(
            {
                "preset": preset,
                "metrics": metrics,
                "oof_mean": mean.tolist(),
                "oof_sd": sd.tolist(),
                "fitted_kernel": str(model.kernel_),
                "fitted_log_theta": model.kernel_.theta.tolist(),
                "lml": float(model.log_marginal_likelihood_value_),
            }
        )
    return {
        "name": name,
        "x": x.tolist(),
        "y": y.tolist(),
        "candidates": candidates,
        "selected": {
            metric: min(candidates, key=lambda item: item["metrics"][metric])["preset"]
            for metric in ("nlpd", "rmse", "mae")
        },
    }


def evaluate_frozen_case(case, validation_rows, seed):
    """Refit only frozen observations and folds, independently of application code."""
    x, y = np.asarray(case["x"], dtype=float), np.asarray(case["y"], dtype=float)
    if x.ndim != 2 or y.ndim != 1 or len(x) != len(y):
        raise ValueError("Frozen reference dimensions are invalid")
    rows = [row for fold in validation_rows for row in fold]
    if (
        any(type(row) is not int for row in rows)
        or sorted(rows) != list(range(len(y)))
        or any(not fold or len(fold) >= len(y) - 1 for fold in validation_rows)
    ):
        raise ValueError(
            "Frozen validation folds must partition every row exactly once"
        )
    splits = []
    for validation in validation_rows:
        training = np.asarray(
            [row for row in range(len(y)) if row not in validation], dtype=int
        )
        splits.append((training, np.asarray(validation, dtype=int)))
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return _evaluate_case(case["name"], x, y, splits, seed)


def generate():
    rng = np.random.default_rng(4209)
    x = rng.uniform(-2, 2, (24, 2))
    responses = {
        "smooth": np.sin(x[:, 0]) + 0.2 * x[:, 1] ** 2,
        "rough": np.abs(x[:, 0]) + 0.2 * np.sin(5 * x[:, 1]),
        "multiscale": np.sin(x[:, 0]) + 0.12 * np.sin(8 * x[:, 0]) + 0.3 * x[:, 1],
        "noisy": np.sin(x[:, 0]) + rng.normal(0, 0.3, len(x)),
    }
    splits = list(KFold(3, shuffle=True, random_state=41).split(x))
    records = [_evaluate_case(name, x, y, splits, 41) for name, y in responses.items()]
    return {
        "packages": {
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "seed": 41,
        "splits": [test.tolist() for _, test in splits],
        "absolute_tolerance": 1e-6,
        "relative_tolerance": 1e-6,
        "cases": records,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reference = generate()
    args.output.write_text(
        json.dumps(reference, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
