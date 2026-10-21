"""Sklearn-compatible numeric times nominal-equality signal kernel, without pickle."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
    RBF,
    ConstantKernel,
    Hyperparameter,
    Kernel,
    Matern,
    Product,
    RationalQuadratic,
)


def _invalid() -> ValueError:
    return ValueError("gp_mixed_kernel_invalid")


class MixedPredictorKernel(Kernel):  # type: ignore[misc]
    """Nominal codes index equality only; inactive one-level categories are omitted."""

    def __init__(
        self,
        numeric_kernel: Any,
        numeric_indices: tuple[int, ...],
        categorical_indices: tuple[int, ...],
        categorical_theta: Any = 1.0,
        categorical_theta_bounds: Any = (1e-4, 1e2),
    ) -> None:
        # Keep constructor objects unchanged, as required by sklearn.clone.
        self.numeric_kernel = numeric_kernel
        self.numeric_indices = numeric_indices
        self.categorical_indices = categorical_indices
        self.categorical_theta = categorical_theta
        self.categorical_theta_bounds = categorical_theta_bounds

    def _parameters(self) -> tuple[Any, Any]:
        indices = (*self.numeric_indices, *self.categorical_indices)
        if (
            len(self.numeric_indices) + len(self.categorical_indices) > 12
            or len(self.categorical_indices) > 4
            or any(type(index) is not int or not 0 <= index < 12 for index in indices)
            or len(set(indices)) != len(indices)
        ):
            raise _invalid()
        _signal_payload(self.numeric_kernel, len(self.numeric_indices))
        count = len(self.categorical_indices)
        if isinstance(self.categorical_theta, list | tuple) and any(
            isinstance(value, bool | np.bool_) for value in self.categorical_theta
        ):
            raise _invalid()
        raw = np.asarray(self.categorical_theta)
        if raw.dtype.kind not in "iuf":
            raise _invalid()
        values = np.asarray(raw, dtype=float)
        if values.ndim == 0:
            values = np.full(count, float(values))
        if values.shape != (count,) or not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise _invalid()
        if isinstance(self.categorical_theta_bounds, str):
            if self.categorical_theta_bounds != "fixed":
                raise _invalid()
            return values, None
        bounds = np.asarray(self.categorical_theta_bounds)
        if bounds.dtype.kind not in "iuf":
            raise _invalid()
        bounds = np.asarray(bounds, dtype=float)
        if bounds.shape == (2,):
            bounds = np.tile(bounds, (count, 1))
        if (
            bounds.shape != (count, 2)
            or not np.all(np.isfinite(bounds))
            or np.any(bounds <= 0)
            or np.any(bounds[:, 0] >= bounds[:, 1])
            or np.any(values < bounds[:, 0])
            or np.any(values > bounds[:, 1])
        ):
            raise _invalid()
        return values, bounds

    @property
    def hyperparameters(self) -> list[Any]:
        values, _ = self._parameters()
        parameters = [
            Hyperparameter(
                "numeric_kernel__" + item.name,
                item.value_type,
                item.bounds,
                item.n_elements,
                item.fixed,
            )
            for item in self.numeric_kernel.hyperparameters
        ]
        if len(values):
            parameters.append(
                Hyperparameter(
                    "categorical_theta", "numeric", self.categorical_theta_bounds, len(values)
                )
            )
        return parameters

    @property
    def theta(self) -> Any:
        values, bounds = self._parameters()
        return np.concatenate(
            (self.numeric_kernel.theta, np.log(values) if bounds is not None else [])
        )

    @theta.setter
    def theta(self, theta: Any) -> None:
        values, bounds = self._parameters()
        numeric_count = self.numeric_kernel.n_dims
        expected = numeric_count + (len(values) if bounds is not None else 0)
        raw = np.asarray(theta)
        if raw.dtype.kind not in "iuf" or raw.shape != (expected,) or not np.all(np.isfinite(raw)):
            raise _invalid()
        with np.errstate(over="ignore", under="ignore"):
            categorical = np.exp(raw[numeric_count:])
        if np.any(categorical <= 0) or not np.all(np.isfinite(categorical)):
            raise _invalid()
        if bounds is not None:
            tolerance = 32 * np.finfo(float).eps * bounds
            if np.any(categorical < bounds[:, 0] - tolerance[:, 0]) or np.any(
                categorical > bounds[:, 1] + tolerance[:, 1]
            ):
                raise _invalid()
            categorical = np.clip(categorical, bounds[:, 0], bounds[:, 1])
        self.numeric_kernel.theta = raw[:numeric_count]
        if bounds is not None:
            self.categorical_theta = categorical

    @property
    def bounds(self) -> Any:
        _, bounds = self._parameters()
        numeric_bounds = np.asarray(self.numeric_kernel.bounds).reshape(-1, 2)
        return np.vstack((numeric_bounds, np.log(bounds))) if bounds is not None else numeric_bounds

    def get_params(self, deep: bool = True) -> dict[str, Any]:
        result = super().get_params(deep=False)
        if deep:
            result.update(
                {
                    "numeric_kernel__" + key: value
                    for key, value in self.numeric_kernel.get_params().items()
                }
            )
        return result  # type: ignore[no-any-return]

    def _matrix(self, value: Any) -> Any:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or raw.ndim != 2 or not np.all(np.isfinite(raw)):
            raise _invalid()
        indices = (*self.numeric_indices, *self.categorical_indices)
        if indices and max(indices) >= raw.shape[1]:
            raise _invalid()
        for index in self.categorical_indices:
            codes = raw[:, index]
            if np.any(codes < 0) or np.any(codes >= 32) or np.any(codes != np.floor(codes)):
                raise _invalid()
        return np.asarray(raw, dtype=float)

    def __call__(self, X: Any, Y: Any = None, eval_gradient: bool = False) -> Any:
        values, bounds = self._parameters()
        if eval_gradient and Y is not None:
            raise _invalid()
        x, y = self._matrix(X), None if Y is None else self._matrix(Y)
        if y is not None and x.shape[1] != y.shape[1]:
            raise _invalid()
        numeric_x = x[:, self.numeric_indices]
        numeric_y = None if y is None else y[:, self.numeric_indices]
        evaluated = self.numeric_kernel(numeric_x, numeric_y, eval_gradient=eval_gradient)
        numeric, gradient = evaluated if eval_gradient else (evaluated, None)
        other = x if y is None else y
        mismatch = (
            np.stack(
                [x[:, index, None] != other[None, :, index] for index in self.categorical_indices],
                axis=2,
            )
            if len(values)
            else np.empty((len(x), len(other), 0))
        )
        category = np.exp(-np.einsum("ijk,k->ij", mismatch, values))
        covariance = numeric * category
        if not eval_gradient:
            return covariance
        numeric_gradient = gradient * category[:, :, None]
        if bounds is None or len(values) == 0:
            return covariance, numeric_gradient
        category_gradient = -(mismatch * values) * covariance[:, :, None]
        return covariance, np.concatenate((numeric_gradient, category_gradient), axis=2)

    def diag(self, X: Any) -> Any:
        self._parameters()
        return self.numeric_kernel.diag(self._matrix(X)[:, self.numeric_indices])

    def is_stationary(self) -> bool:
        return bool(self.numeric_kernel.is_stationary())


def _positive(value: Any) -> float:
    if isinstance(value, bool | np.bool_) or not isinstance(value, int | float | np.number):
        raise _invalid()
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise _invalid()
    return number


def _signal_payload(signal: Any, numeric_count: int) -> dict[str, Any]:
    if numeric_count == 0:
        if not isinstance(signal, ConstantKernel):
            raise _invalid()
        return {"preset": "constant", "amplitude": _positive(signal.constant_value)}
    if not isinstance(signal, Product) or not isinstance(signal.k1, ConstantKernel):
        raise _invalid()
    base = signal.k2
    if isinstance(base, Matern):
        if base.nu not in {1.5, 2.5}:
            raise _invalid()
        preset = "matern_5_2_ard" if base.nu == 2.5 else "matern_3_2_ard"
    elif isinstance(base, RBF):
        preset = "rbf_ard"
    elif isinstance(base, RationalQuadratic):
        preset = "rational_quadratic"
    else:
        raise _invalid()
    lengths = np.asarray(base.length_scale, dtype=float).reshape(-1)
    if len(lengths) not in {1, numeric_count}:
        raise _invalid()
    result: dict[str, Any] = {
        "preset": preset,
        "amplitude": _positive(signal.k1.constant_value),
        "length_scales": [_positive(value) for value in lengths],
    }
    if preset == "rational_quadratic":
        if len(lengths) != 1:
            raise _invalid()
        result["rational_quadratic_alpha"] = _positive(base.alpha)
    return result


def mixed_kernel_to_payload(kernel: MixedPredictorKernel) -> dict[str, Any]:
    values, _ = kernel._parameters()
    return {
        "schema_version": 1,
        "kind": "numeric_times_nominal_equal_correlation",
        "numeric_indices": list(kernel.numeric_indices),
        "categorical_indices": list(kernel.categorical_indices),
        "categorical_theta": values.tolist(),
        "signal": _signal_payload(kernel.numeric_kernel, len(kernel.numeric_indices)),
    }


def mixed_kernel_warning_codes(kernel: MixedPredictorKernel) -> tuple[str, ...]:
    values, bounds = kernel._parameters()
    if bounds is not None and (
        np.any(np.isclose(values, bounds[:, 0], rtol=1e-5, atol=0))
        or np.any(np.isclose(values, bounds[:, 1], rtol=1e-5, atol=0))
    ):
        return ("gp_category_theta_bound",)
    return ()


def mixed_kernel_from_payload(payload: Any) -> MixedPredictorKernel:
    try:
        return _read_kernel_payload(payload)
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise ValueError("gp_mixed_kernel_payload_invalid") from exc


def _read_kernel_payload(payload: Any) -> MixedPredictorKernel:
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "kind",
        "numeric_indices",
        "categorical_indices",
        "categorical_theta",
        "signal",
    }:
        raise _invalid()
    if (
        type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
        or payload["kind"] != "numeric_times_nominal_equal_correlation"
        or any(
            not isinstance(payload[key], list)
            for key in ("numeric_indices", "categorical_indices", "categorical_theta")
        )
    ):
        raise _invalid()
    numeric_indices = tuple(payload["numeric_indices"])
    categorical_indices = tuple(payload["categorical_indices"])
    signal = payload["signal"]
    if not isinstance(signal, dict):
        raise _invalid()
    preset = signal.get("preset")
    keys = {"preset", "amplitude"}
    if numeric_indices:
        keys.add("length_scales")
        if preset == "rational_quadratic":
            keys.add("rational_quadratic_alpha")
    if set(signal) != keys:
        raise _invalid()
    amplitude = ConstantKernel(_positive(signal["amplitude"]), "fixed")
    numeric_kernel: Any = amplitude
    if not numeric_indices:
        if preset != "constant":
            raise _invalid()
    else:
        if not isinstance(signal["length_scales"], list) or not signal["length_scales"]:
            raise _invalid()
        lengths = np.array([_positive(value) for value in signal["length_scales"]])
        if preset in {"matern_5_2_ard", "matern_3_2_ard"}:
            base = Matern(lengths, "fixed", nu=2.5 if preset == "matern_5_2_ard" else 1.5)
        elif preset == "rbf_ard":
            base = RBF(lengths, "fixed")
        elif preset == "rational_quadratic":
            if len(lengths) != 1:
                raise _invalid()
            base = RationalQuadratic(
                float(lengths[0]), _positive(signal["rational_quadratic_alpha"]), "fixed", "fixed"
            )
        else:
            raise _invalid()
        numeric_kernel = amplitude * base
    result = MixedPredictorKernel(
        numeric_kernel,
        numeric_indices,
        categorical_indices,
        payload["categorical_theta"],
        "fixed",
    )
    result._parameters()
    return result
