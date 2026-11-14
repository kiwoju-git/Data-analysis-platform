"""Known, serializable BO mixed-factor signal kernels with explicit category policies."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
    RBF,
    ConstantKernel,
    Hyperparameter,
    Kernel,
    Matern,
    Product,
)

from app.statistics.bo_factor_domains import (
    MAX_BO_CATEGORY_PARAMETERS,
    MAX_BO_FACTORS,
    BoCategoricalFactorDomain,
    BoCorrelationPolicy,
    BoFactorDomain,
    BoNumericFactorDomain,
    BoPseudocomponentFactorDomain,
    category_parameter_count,
    validate_bo_factor_domains,
)
from app.statistics.bo_kernels import BoKernelSpec, kernel_family, signal_kernel

ANGLE_BOUNDS = (1e-4, math.pi - 1e-4)
EQUALITY_BOUNDS = (1e-4, 1e2)
LATENT_GAP_BOUNDS = (1e-4, 10.0)
MAX_COVARIANCE_ENTRIES = 2_000_000


def _invalid() -> ValueError:
    return ValueError("bayesian_factor_kernel_invalid")


def _numeric_array(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        if value.size > 100_000:
            raise _invalid()
    elif isinstance(value, list | tuple):
        if len(value) > 100_000:
            raise _invalid()
        pending = list(value)
        count = 0
        while pending:
            item = pending.pop()
            count += 1
            if count > 110_000:
                raise _invalid()
            if isinstance(item, list | tuple):
                if len(item) > 100_000:
                    raise _invalid()
                pending.extend(item)
            elif isinstance(item, bool | np.bool_) or not isinstance(item, int | float | np.number):
                raise _invalid()
    elif isinstance(value, bool | np.bool_) or not isinstance(value, int | float | np.number):
        raise _invalid()
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf" or not np.all(np.isfinite(raw)):
        raise _invalid()
    with np.errstate(over="ignore", invalid="ignore"):
        result = np.asarray(raw, dtype=float)
    if not np.all(np.isfinite(result)):
        raise _invalid()
    return result


def _positive(value: Any) -> float:
    if isinstance(value, bool | np.bool_) or not isinstance(value, int | float | np.number):
        raise _invalid()
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise _invalid()
    return number


@dataclass(frozen=True)
class BoCategoryKernelSpec:
    index: int
    kind: Literal["nominal", "ordinal"]
    level_count: int
    policy: BoCorrelationPolicy

    def __post_init__(self) -> None:
        if type(self.index) is not int or not 0 <= self.index < MAX_BO_FACTORS:
            raise _invalid()
        if not isinstance(self.kind, str) or self.kind not in {"nominal", "ordinal"}:
            raise _invalid()
        category_parameter_count(self.policy, self.level_count)
        if self.policy == "ordinal_monotone_latent_rbf_v1" and self.kind != "ordinal":
            raise _invalid()

    @property
    def parameter_count(self) -> int:
        return category_parameter_count(self.policy, self.level_count)

    @property
    def parameter_bounds(self) -> tuple[float, float]:
        if self.policy == "equal_positive_correlation_v1":
            return EQUALITY_BOUNDS
        if self.policy == "unequal_hyperspherical_correlation_v1":
            return ANGLE_BOUNDS
        return LATENT_GAP_BOUNDS


def _category_correlation(
    spec: BoCategoryKernelSpec, parameters: Any, gradient: bool
) -> tuple[Any, Any]:
    count = spec.level_count
    if spec.policy == "equal_positive_correlation_v1":
        mismatch = 1.0 - np.eye(count)
        correlation = np.exp(-float(parameters[0]) * mismatch)
        derivative = (-float(parameters[0]) * mismatch * correlation)[:, :, None]
        return correlation, derivative if gradient else None
    if spec.policy == "ordinal_monotone_latent_rbf_v1":
        # Zero anchor removes translation; fixed RBF length 1 removes scale aliasing.
        positions = np.concatenate(([0.0], np.cumsum(parameters)))
        delta = positions[:, None] - positions[None, :]
        correlation = np.exp(-0.5 * delta**2)
        if not gradient:
            return correlation, None
        incidence = (np.arange(count)[:, None] > np.arange(count - 1)[None, :]).astype(float)
        delta_gradient = (incidence[:, None, :] - incidence[None, :, :]) * parameters
        return correlation, -delta[:, :, None] * delta_gradient * correlation[:, :, None]

    lower = np.zeros((count, count))
    lower[0, 0] = 1.0
    derivatives = np.zeros((spec.parameter_count, count, count)) if gradient else None
    offset = 0
    for row in range(1, count):
        angles = parameters[offset : offset + row]
        sine, cosine = np.sin(angles), np.cos(angles)
        preceding = np.concatenate(([1.0], np.cumprod(sine)))
        lower[row, :row] = preceding[:-1] * cosine
        lower[row, row] = preceding[-1]
        if gradient:
            assert derivatives is not None
            for column in range(row):
                derivative = derivatives[offset + column]
                derivative[row, column] = -preceding[column] * sine[column] * angles[column]
                derivative[row, column + 1 : row + 1] = (
                    lower[row, column + 1 : row + 1]
                    * cosine[column]
                    / sine[column]
                    * angles[column]
                )
        offset += row
    correlation = lower @ lower.T
    if not gradient:
        return correlation, None
    assert derivatives is not None
    derivative = np.stack([item @ lower.T + lower @ item.T for item in derivatives], axis=2)
    return correlation, derivative


class BoFactorKernel(Kernel):  # type: ignore[misc]
    """Numeric signal times category correlation matrices; noise/jitter live outside."""

    def __init__(
        self,
        numeric_kernel: Any,
        numeric_indices: tuple[int, ...],
        category_specs: tuple[BoCategoryKernelSpec, ...],
        category_parameters: Any,
        category_parameter_bounds: Any = "fixed",
        numeric_coordinate_upper: tuple[float, ...] | None = None,
    ) -> None:
        # sklearn.clone requires constructor arguments to be retained unchanged.
        self.numeric_kernel = numeric_kernel
        self.numeric_indices = numeric_indices
        self.category_specs = category_specs
        self.category_parameters = category_parameters
        self.category_parameter_bounds = category_parameter_bounds
        self.numeric_coordinate_upper = numeric_coordinate_upper

    def _parameters(self) -> tuple[Any, Any]:
        if not isinstance(self.numeric_indices, tuple) or not isinstance(
            self.category_specs, tuple
        ):
            raise _invalid()
        if any(not isinstance(spec, BoCategoryKernelSpec) for spec in self.category_specs):
            raise _invalid()
        indices = (*self.numeric_indices, *(spec.index for spec in self.category_specs))
        if (
            not 1 <= len(indices) <= MAX_BO_FACTORS
            or not self.category_specs
            or any(type(index) is not int for index in indices)
            or sorted(indices) != list(range(len(indices)))
        ):
            raise _invalid()
        _numeric_kernel_payload(self.numeric_kernel, len(self.numeric_indices))
        if self.numeric_coordinate_upper is not None:
            if not isinstance(self.numeric_coordinate_upper, tuple):
                raise _invalid()
            coordinate_upper = _numeric_array(self.numeric_coordinate_upper)
            if coordinate_upper.shape != (len(self.numeric_indices),) or np.any(
                coordinate_upper < 0
            ):
                raise _invalid()
        count = sum(spec.parameter_count for spec in self.category_specs)
        if count > MAX_BO_CATEGORY_PARAMETERS:
            raise _invalid()
        parameters = _numeric_array(self.category_parameters)
        if parameters.shape != (count,):
            raise _invalid()
        hard_bounds = np.array(
            [
                spec.parameter_bounds
                for spec in self.category_specs
                for _ in range(spec.parameter_count)
            ]
        )
        if np.any(parameters < hard_bounds[:, 0]) or np.any(parameters > hard_bounds[:, 1]):
            raise _invalid()
        if isinstance(self.category_parameter_bounds, str):
            if self.category_parameter_bounds != "fixed":
                raise _invalid()
            return parameters, None
        bounds = _numeric_array(self.category_parameter_bounds)
        if (
            bounds.shape != (count, 2)
            or np.any(bounds[:, 0] >= bounds[:, 1])
            or np.any(bounds[:, 0] < hard_bounds[:, 0])
            or np.any(bounds[:, 1] > hard_bounds[:, 1])
            or np.any(parameters < bounds[:, 0])
            or np.any(parameters > bounds[:, 1])
        ):
            raise _invalid()
        return parameters, bounds

    @property
    def hyperparameters(self) -> list[Any]:
        values, _ = self._parameters()
        result = [
            Hyperparameter(
                "numeric_kernel__" + parameter.name,
                parameter.value_type,
                parameter.bounds,
                parameter.n_elements,
                parameter.fixed,
            )
            for parameter in self.numeric_kernel.hyperparameters
        ]
        result.append(
            Hyperparameter(
                "category_parameters", "numeric", self.category_parameter_bounds, len(values)
            )
        )
        return result

    @property
    def theta(self) -> Any:
        values, bounds = self._parameters()
        return np.concatenate(
            (self.numeric_kernel.theta, np.log(values) if bounds is not None else [])
        )

    @theta.setter
    def theta(self, value: Any) -> None:
        values, bounds = self._parameters()
        raw = _numeric_array(value)
        numeric_count = self.numeric_kernel.n_dims
        if raw.shape != (numeric_count + (len(values) if bounds is not None else 0),):
            raise _invalid()
        with np.errstate(over="ignore", under="ignore"):
            category = np.exp(raw[numeric_count:])
        if bounds is not None:
            tolerance = 32 * np.finfo(float).eps * bounds
            if (
                not np.all(np.isfinite(category))
                or np.any(category < bounds[:, 0] - tolerance[:, 0])
                or np.any(category > bounds[:, 1] + tolerance[:, 1])
            ):
                raise _invalid()
            category = np.clip(category, bounds[:, 0], bounds[:, 1])
        numeric_bounds = self.numeric_kernel.bounds
        if numeric_count and (
            np.any(raw[:numeric_count] < numeric_bounds[:, 0])
            or np.any(raw[:numeric_count] > numeric_bounds[:, 1])
        ):
            raise _invalid()
        self.numeric_kernel.theta = raw[:numeric_count]
        if bounds is not None:
            self.category_parameters = category

    @property
    def bounds(self) -> Any:
        _, bounds = self._parameters()
        numeric = np.asarray(self.numeric_kernel.bounds).reshape(-1, 2)
        return np.vstack((numeric, np.log(bounds))) if bounds is not None else numeric

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
        matrix = _numeric_array(value)
        expected = len(self.numeric_indices) + len(self.category_specs)
        if matrix.ndim != 2 or matrix.shape[1] != expected or not 0 <= len(matrix) <= 10_000:
            raise _invalid()
        numeric = matrix[:, self.numeric_indices]
        upper = (
            1
            if self.numeric_coordinate_upper is None
            else np.asarray(self.numeric_coordinate_upper)
        )
        if np.any(numeric < 0) or np.any(numeric > upper):
            raise _invalid()
        for spec in self.category_specs:
            codes = matrix[:, spec.index]
            if (
                np.any(codes < 0)
                or np.any(codes >= spec.level_count)
                or np.any(codes != np.floor(codes))
            ):
                raise _invalid()
        return matrix

    def category_correlation_matrices(self) -> tuple[Any, ...]:
        parameters, _ = self._parameters()
        matrices = []
        offset = 0
        for spec in self.category_specs:
            matrices.append(
                _category_correlation(
                    spec, parameters[offset : offset + spec.parameter_count], False
                )[0]
            )
            offset += spec.parameter_count
        return tuple(matrices)

    def __call__(self, X: Any, Y: Any = None, eval_gradient: bool = False) -> Any:
        parameters, bounds = self._parameters()
        if eval_gradient and Y is not None:
            raise _invalid()
        x = self._matrix(X)
        y = x if Y is None else self._matrix(Y)
        if len(x) * len(y) > MAX_COVARIANCE_ENTRIES or (eval_gradient and len(x) > 200):
            raise ValueError("bayesian_factor_kernel_resource_limit")
        evaluated = self.numeric_kernel(
            x[:, self.numeric_indices],
            None if Y is None else y[:, self.numeric_indices],
            eval_gradient=eval_gradient,
        )
        numeric, numeric_gradient = evaluated if eval_gradient else (evaluated, None)
        categories, gradients = [], []
        offset = 0
        for spec in self.category_specs:
            covariance, derivative = _category_correlation(
                spec,
                parameters[offset : offset + spec.parameter_count],
                eval_gradient and bounds is not None,
            )
            left, right = x[:, spec.index].astype(int), y[:, spec.index].astype(int)
            categories.append(covariance[left[:, None], right[None, :]])
            if derivative is not None:
                gradients.append(derivative[left[:, None], right[None, :], :])
            offset += spec.parameter_count
        category_product = np.prod(categories, axis=0)
        result = numeric * category_product
        if not eval_gradient:
            return result
        all_gradients = [numeric_gradient * category_product[:, :, None]]
        if bounds is not None:
            # Do not divide by a category correlation: unequal correlations can be zero.
            for index, gradient in enumerate(gradients):
                other = np.ones_like(result)
                for other_index, category in enumerate(categories):
                    if other_index != index:
                        other *= category
                all_gradients.append(gradient * (numeric * other)[:, :, None])
        return result, np.concatenate(all_gradients, axis=2)

    def diag(self, X: Any) -> Any:
        self._parameters()
        return self.numeric_kernel.diag(self._matrix(X)[:, self.numeric_indices])

    def is_stationary(self) -> bool:
        # A category-code translation is not a meaningful operation on this kernel.
        return False


def build_bo_factor_kernel(factors: Sequence[BoFactorDomain], spec: BoKernelSpec) -> Any:
    validate_bo_factor_domains(factors)
    numeric_indices = tuple(
        index for index, factor in enumerate(factors) if isinstance(factor, BoNumericFactorDomain)
    )
    if len(numeric_indices) == len(factors):
        return signal_kernel(len(factors), spec)
    numeric = (
        signal_kernel(len(numeric_indices), spec)
        if numeric_indices
        else ConstantKernel(1.0, (1e-3, 1e3))
    )
    categories = tuple(
        BoCategoryKernelSpec(index, factor.kind, len(factor.levels), factor.correlation_policy)
        for index, factor in enumerate(factors)
        if isinstance(factor, BoCategoricalFactorDomain)
    )
    parameters, bounds = [], []
    for category in categories:
        default = 1.0
        if category.policy == "unequal_hyperspherical_correlation_v1":
            default = math.pi / 2
        elif category.policy == "ordinal_monotone_latent_rbf_v1":
            default = 1.0 / (category.level_count - 1)
        parameters.extend([default] * category.parameter_count)
        bounds.extend([category.parameter_bounds] * category.parameter_count)
    coordinate_upper = _coordinate_upper(factors)
    result = BoFactorKernel(
        numeric, numeric_indices, categories, parameters, bounds, coordinate_upper
    )
    result._parameters()
    return result


def _bounds_payload(value: Any, values: Any) -> Any:
    if isinstance(value, str):
        if value != "fixed":
            raise _invalid()
        return value
    bounds = _numeric_array(value)
    if bounds.shape == (2,):
        bounds = np.tile(bounds, (len(values), 1))
    if (
        bounds.shape != (len(values), 2)
        or np.any(bounds <= 0)
        or np.any(bounds[:, 0] >= bounds[:, 1])
    ):
        raise _invalid()
    # exp(log(bound)) need not reproduce the exact endpoint bit pattern.
    tolerance = 32 * np.finfo(float).eps * bounds
    if np.any(values < bounds[:, 0] - tolerance[:, 0]) or np.any(
        values > bounds[:, 1] + tolerance[:, 1]
    ):
        raise _invalid()
    return bounds.tolist()


def _numeric_kernel_payload(kernel: Any, numeric_count: int) -> dict[str, Any]:
    payload: dict[str, Any]
    if numeric_count:
        if type(kernel) is not Product or type(kernel.k1) is not ConstantKernel:
            raise _invalid()
        amplitude, base = kernel.k1, kernel.k2
        if type(base) not in {Matern, RBF}:
            raise _invalid()
        kind = kernel_family(base)
        lengths = _numeric_array(base.length_scale)
        if lengths.ndim > 1:
            raise _invalid()
        lengths = lengths.reshape(-1)
        if len(lengths) not in {1, numeric_count} or np.any(lengths <= 0):
            raise _invalid()
        payload = {
            "kind": kind,
            "length_scales": lengths.tolist(),
            "length_scale_bounds": _bounds_payload(base.length_scale_bounds, lengths),
        }
    else:
        if type(kernel) is not ConstantKernel:
            raise _invalid()
        amplitude, payload = kernel, {"kind": "constant"}
    value = _positive(amplitude.constant_value)
    payload.update(
        {
            "amplitude": value,
            "amplitude_bounds": _bounds_payload(amplitude.constant_value_bounds, np.array([value])),
        }
    )
    return payload


def bo_factor_kernel_to_payload(kernel: BoFactorKernel) -> dict[str, Any]:
    if type(kernel) is not BoFactorKernel:
        raise _invalid()
    parameters, bounds = kernel._parameters()
    payload = {
        "schema_version": 1 if kernel.numeric_coordinate_upper is None else 2,
        "kind": "bo_product_factor_signal_v1"
        if kernel.numeric_coordinate_upper is None
        else "bo_product_factor_signal_affine_coordinates_v1",
        "numeric_indices": list(kernel.numeric_indices),
        "categories": [
            {
                "index": item.index,
                "kind": item.kind,
                "level_count": item.level_count,
                "policy": item.policy,
            }
            for item in kernel.category_specs
        ],
        "parameters": parameters.tolist(),
        "parameter_bounds": "fixed" if bounds is None else bounds.tolist(),
        "numeric_signal": _numeric_kernel_payload(
            kernel.numeric_kernel, len(kernel.numeric_indices)
        ),
    }
    if kernel.numeric_coordinate_upper is not None:
        payload["numeric_coordinate_upper"] = list(kernel.numeric_coordinate_upper)
    return payload


def bo_factor_kernel_from_payload(payload: Any) -> BoFactorKernel:
    affine = isinstance(payload, dict) and payload.get("schema_version") == 2
    if (
        not isinstance(payload, dict)
        or set(payload)
        != (
            {
                "schema_version",
                "kind",
                "numeric_indices",
                "categories",
                "parameters",
                "parameter_bounds",
                "numeric_signal",
            }
            | ({"numeric_coordinate_upper"} if affine else set())
        )
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != (2 if affine else 1)
        or payload["kind"]
        != (
            "bo_product_factor_signal_affine_coordinates_v1"
            if affine
            else "bo_product_factor_signal_v1"
        )
    ):
        raise _invalid()
    if (
        not isinstance(payload["numeric_indices"], list)
        or not isinstance(payload["categories"], list)
        or not isinstance(payload["parameters"], list)
        or len(payload["numeric_indices"]) + len(payload["categories"]) > MAX_BO_FACTORS
        or len(payload["parameters"]) > MAX_BO_CATEGORY_PARAMETERS
    ):
        raise _invalid()
    categories = []
    for item in payload["categories"]:
        if not isinstance(item, dict) or set(item) != {"index", "kind", "level_count", "policy"}:
            raise _invalid()
        categories.append(
            BoCategoryKernelSpec(item["index"], item["kind"], item["level_count"], item["policy"])
        )
    numeric_indices = tuple(payload["numeric_indices"])
    numeric = payload["numeric_signal"]
    keys = {"kind", "amplitude", "amplitude_bounds"}
    if numeric_indices:
        keys |= {"length_scales", "length_scale_bounds"}
    if not isinstance(numeric, dict) or set(numeric) != keys:
        raise _invalid()
    amplitude_value = _positive(numeric["amplitude"])
    amplitude_bounds = _bounds_payload(numeric["amplitude_bounds"], np.array([amplitude_value]))
    amplitude = ConstantKernel(amplitude_value, amplitude_bounds)
    signal: Any = amplitude
    if numeric_indices:
        if not isinstance(numeric["length_scales"], list):
            raise _invalid()
        lengths = _numeric_array(numeric["length_scales"])
        if (
            lengths.ndim != 1
            or len(lengths) not in {1, len(numeric_indices)}
            or np.any(lengths <= 0)
        ):
            raise _invalid()
        bounds = _bounds_payload(numeric["length_scale_bounds"], lengths)
        kind = numeric["kind"]
        if not isinstance(kind, str):
            raise _invalid()
        if kind == "gaussian":
            correlation = RBF(lengths, bounds)
        elif kind in {"matern_5_2", "matern_3_2", "exponential"}:
            correlation = Matern(
                lengths, bounds, nu={"matern_5_2": 2.5, "matern_3_2": 1.5, "exponential": 0.5}[kind]
            )
        else:
            raise _invalid()
        signal = amplitude * correlation
    elif numeric["kind"] != "constant":
        raise _invalid()
    parameters = _numeric_array(payload["parameters"]).copy()
    bounds_value = payload["parameter_bounds"]
    bounds = bounds_value if isinstance(bounds_value, str) else _numeric_array(bounds_value).copy()
    upper = None
    if affine:
        if type(payload["numeric_coordinate_upper"]) is not list:
            raise _invalid()
        upper = tuple(payload["numeric_coordinate_upper"])
    result = BoFactorKernel(signal, numeric_indices, tuple(categories), parameters, bounds, upper)
    result._parameters()
    return result


def validate_bo_factor_kernel_domains(
    kernel: BoFactorKernel, factors: Sequence[BoFactorDomain]
) -> None:
    """Bind a numeric state payload to its separately stored exact factor identities."""
    validate_bo_factor_domains(factors)
    kernel._parameters()
    numeric = tuple(
        index for index, factor in enumerate(factors) if isinstance(factor, BoNumericFactorDomain)
    )
    categories = tuple(
        BoCategoryKernelSpec(index, factor.kind, len(factor.levels), factor.correlation_policy)
        for index, factor in enumerate(factors)
        if isinstance(factor, BoCategoricalFactorDomain)
    )
    if (
        kernel.numeric_indices != numeric
        or kernel.category_specs != categories
        or kernel.numeric_coordinate_upper != _coordinate_upper(factors)
    ):
        raise ValueError("bayesian_factor_kernel_domain_mismatch")


def _coordinate_upper(factors: Sequence[BoFactorDomain]) -> tuple[float, ...] | None:
    if not any(isinstance(f, BoPseudocomponentFactorDomain) for f in factors):
        return None
    return tuple(
        f.encoded_high if isinstance(f, BoPseudocomponentFactorDomain) else 1.0
        for f in factors
        if isinstance(f, BoNumericFactorDomain)
    )


def hyperspherical_parameters_from_correlation(correlation: Any) -> Any:
    """Convert a validated SPD level matrix to the documented row-wise angle basis."""
    matrix = _numeric_array(correlation)
    if (
        matrix.ndim != 2
        or matrix.shape[0] != matrix.shape[1]
        or not 2 <= len(matrix) <= 8
        or not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12)
        or not np.allclose(np.diag(matrix), 1.0, rtol=0, atol=1e-12)
    ):
        raise _invalid()
    try:
        lower = np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError as exc:
        raise _invalid() from exc
    angles = np.array(
        [
            math.atan2(
                float(np.linalg.norm(lower[row, column + 1 : row + 1])), float(lower[row, column])
            )
            for row in range(1, len(matrix))
            for column in range(row)
        ]
    )
    if np.any(angles < ANGLE_BOUNDS[0]) or np.any(angles > ANGLE_BOUNDS[1]):
        raise _invalid()
    return angles
