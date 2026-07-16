from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any


PACKAGE_NAMES = ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated scikit-learn GP spike probe."
    )
    parser.add_argument("--mode", choices=("empty", "import", "gp"), required=True)
    parser.add_argument("--hold-seconds", type=float, default=0.0)
    args = parser.parse_args()
    if args.hold_seconds < 0.0 or args.hold_seconds > 5.0:
        raise ValueError("--hold-seconds must be between 0 and 5")

    if sys.version_info[:2] != (3, 10):
        raise RuntimeError("The dependency spike requires CPython 3.10.x")
    if args.mode == "empty":
        print('{"status":"passed"}')
        time.sleep(args.hold_seconds)
        return 0

    import numpy as np
    import scipy
    import sklearn

    if args.mode == "import":
        print(
            json.dumps(
                {
                    "status": "passed",
                    "versions": {
                        "numpy": np.__version__,
                        "scipy": scipy.__version__,
                        "scikit-learn": sklearn.__version__,
                    },
                },
                sort_keys=True,
            )
        )
        time.sleep(args.hold_seconds)
        return 0

    payload = run_gp_probe(np)
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2))
    time.sleep(args.hold_seconds)
    return 0


def run_gp_probe(np: Any) -> dict[str, Any]:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    from threadpoolctl import threadpool_info

    x_train = np.array([[0.0], [0.2], [0.4], [0.6], [0.8], [1.0]], dtype=float)
    y_train = np.array([0.05, 0.31, 0.59, 0.72, 0.55, 0.12], dtype=float)
    x_predict = np.array([[0.1], [0.3], [0.5], [0.7], [0.9]], dtype=float)
    kernel = ConstantKernel(1.0, constant_value_bounds="fixed") * Matern(
        length_scale=0.25, length_scale_bounds="fixed", nu=2.5
    ) + WhiteKernel(noise_level=1e-6, noise_level_bounds="fixed")
    model = GaussianProcessRegressor(
        kernel=kernel,
        alpha=1e-10,
        optimizer=None,
        normalize_y=True,
        random_state=20260715,
    )
    model.fit(x_train, y_train)
    predicted_mean, predicted_std = model.predict(x_predict, return_std=True)

    mean_values = [_finite_round(value) for value in predicted_mean]
    std_values = [_finite_round(value) for value in predicted_std]
    if any(value <= 0.0 for value in std_values):
        raise RuntimeError(
            "GP smoke returned non-positive posterior standard deviation"
        )

    deterministic_payload = {
        "kernel": str(model.kernel_),
        "log_marginal_likelihood": _finite_round(model.log_marginal_likelihood_value_),
        "predicted_mean": mean_values,
        "predicted_std": std_values,
        "seed": 20260715,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            deterministic_payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    threadpools = sorted(
        (
            {
                "internal_api": entry.get("internal_api"),
                "num_threads": entry.get("num_threads"),
                "prefix": entry.get("prefix"),
                "user_api": entry.get("user_api"),
                "version": entry.get("version"),
            }
            for entry in threadpool_info()
        ),
        key=lambda entry: (
            str(entry["user_api"]),
            str(entry["internal_api"]),
            str(entry["prefix"]),
        ),
    )
    return {
        "status": "passed",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "architecture": platform.architecture()[0],
        "packages": [_package_record(name) for name in PACKAGE_NAMES],
        "threadpools": threadpools,
        "deterministic": deterministic_payload,
        "deterministic_fingerprint": fingerprint,
    }


def _package_record(name: str) -> dict[str, Any]:
    distribution = importlib.metadata.distribution(name)
    metadata = distribution.metadata
    license_value = (
        metadata.get("License-Expression") or metadata.get("License") or "unknown"
    )
    license_summary = license_value.splitlines()[0].strip()
    return {
        "name": name,
        "version": distribution.version,
        "license": license_summary,
        "installed_size_bytes": _distribution_size(distribution),
    }


def _distribution_size(distribution: importlib.metadata.Distribution) -> int:
    total = 0
    for package_path in distribution.files or ():
        resolved = Path(distribution.locate_file(package_path))
        try:
            if resolved.is_file():
                total += resolved.stat().st_size
        except OSError:
            continue
    return total


def _finite_round(value: object) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise RuntimeError("GP smoke returned a non-finite value")
    return round(parsed, 12)


if __name__ == "__main__":
    raise SystemExit(main())
