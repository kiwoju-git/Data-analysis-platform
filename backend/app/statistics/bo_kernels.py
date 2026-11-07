"""Numeric BO covariance choices, separate from standalone GPR defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

BoKernelKind = Literal["matern_5_2", "matern_3_2", "gaussian", "exponential"]


@dataclass(frozen=True)
class BoKernelSpec:
    kind: BoKernelKind = "matern_5_2"

    def __post_init__(self) -> None:
        if self.kind not in ("matern_5_2", "matern_3_2", "gaussian", "exponential"):
            raise ValueError("bayesian_surrogate_kernel_invalid")


def signal_kernel(predictor_count: int, spec: BoKernelSpec) -> Any:
    import numpy as np
    from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
        RBF,
        ConstantKernel,
        Matern,
    )

    lengths = np.ones(predictor_count)
    if spec.kind == "gaussian":
        correlation = RBF(lengths, (1e-2, 1e2))
    else:
        nu = {"matern_5_2": 2.5, "matern_3_2": 1.5, "exponential": 0.5}[spec.kind]
        correlation = Matern(lengths, (1e-2, 1e2), nu=nu)
    return ConstantKernel(1.0, (1e-3, 1e3)) * correlation


def kernel_family(correlation: Any) -> BoKernelKind:
    from sklearn.gaussian_process.kernels import RBF, Matern  # type: ignore[import-untyped]

    # Matern subclasses RBF; test it first, without parsing its display string.
    if isinstance(correlation, Matern):
        if correlation.nu == 2.5:
            return "matern_5_2"
        if correlation.nu == 1.5:
            return "matern_3_2"
        if correlation.nu == 0.5:
            return "exponential"
    elif type(correlation) is RBF:
        return "gaussian"
    raise ValueError("bayesian_surrogate_kernel_invalid")
