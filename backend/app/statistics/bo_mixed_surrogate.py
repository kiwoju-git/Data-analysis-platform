"""Explicit mixed-factor BO adapter; legacy numeric fitting remains unchanged."""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any, Literal

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoFactorDomain,
    BoPseudocomponentFactorDomain,
    bo_factor_domains_to_payload,
    validate_bo_factor_domains,
)
from app.statistics.bo_fit_policy import BoFitPolicy
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_surrogate import BoPosterior, BoSurrogate, BoSurrogatePolicy, _likelihood

MODEL_SCHEMA_VERSION = 6
POLICY_VERSION = "bo_mixed_noise_latent_v1"
FIT_POLICY_VERSION = "bounded_typed_factor_starts_v1"
ParameterRole = Literal[
    "signal_amplitude",
    "numeric_length_scale",
    "category_mismatch",
    "category_hyperspherical_angle",
    "ordinal_latent_gap",
    "measurement_variance",
]


def _invalid(code: str = "bayesian_mixed_surrogate_invalid") -> BayesianOptimizationError:
    return BayesianOptimizationError(code)


def split_mixed_signal_noise(kernel: Any) -> tuple[Any, float]:
    from sklearn.gaussian_process.kernels import Sum, WhiteKernel  # type: ignore[import-untyped]

    from app.statistics.bo_factor_kernels import BoFactorKernel, bo_factor_kernel_to_payload

    signal, noise = kernel, 0.0
    if type(kernel) is Sum:
        if type(kernel.k2) is not WhiteKernel:
            raise _invalid()
        signal, noise = kernel.k1, float(kernel.k2.noise_level)
    if type(signal) is not BoFactorKernel or not math.isfinite(noise) or noise < 0:
        raise _invalid()
    bo_factor_kernel_to_payload(signal)
    return signal, noise


@dataclass(frozen=True)
class BoMixedParameter:
    index: int
    role: ParameterRole
    factor_index: int | None
    factor_id: str | None
    level_indices: tuple[int, ...] = ()

    def payload(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "role": self.role,
            "factor_index": self.factor_index,
            "factor_id": self.factor_id,
            "level_indices": list(self.level_indices),
        }


def mixed_parameter_descriptors(
    kernel: Any, domains: Sequence[BoFactorDomain]
) -> tuple[BoMixedParameter, ...]:
    """Describe free theta entries, never interpreting a category parameter as length."""
    from sklearn.gaussian_process.kernels import Sum

    from app.statistics.bo_factor_kernels import validate_bo_factor_kernel_domains

    signal, _ = split_mixed_signal_noise(kernel)
    validate_bo_factor_kernel_domains(signal, domains)
    parameters: list[BoMixedParameter] = []

    def add(role: ParameterRole, index: int | None = None, levels: tuple[int, ...] = ()) -> None:
        parameters.append(
            BoMixedParameter(
                len(parameters),
                role,
                index,
                domains[index].factor_id if index is not None else None,
                levels,
            )
        )

    numeric = signal.numeric_kernel
    amplitude = numeric.k1 if signal.numeric_indices else numeric
    if not amplitude.hyperparameter_constant_value.fixed:
        add("signal_amplitude")
    if signal.numeric_indices and not numeric.k2.hyperparameter_length_scale.fixed:
        if numeric.k2.hyperparameter_length_scale.n_elements != len(signal.numeric_indices):
            raise _invalid("bayesian_mixed_numeric_ard_required")
        for index in signal.numeric_indices:
            add("numeric_length_scale", index)
    if not signal.hyperparameters[-1].fixed:
        for spec in signal.category_specs:
            if spec.policy == "equal_positive_correlation_v1":
                add("category_mismatch", spec.index)
            elif spec.policy == "ordinal_monotone_latent_rbf_v1":
                for level in range(spec.level_count - 1):
                    add("ordinal_latent_gap", spec.index, (level, level + 1))
            else:
                for row in range(1, spec.level_count):
                    for column in range(row):
                        add("category_hyperspherical_angle", spec.index, (row, column))
    if type(kernel) is Sum and not kernel.k2.hyperparameter_noise_level.fixed:
        add("measurement_variance")
    if len(parameters) != len(kernel.theta) or len(parameters) > 76:
        raise _invalid()
    return tuple(parameters)


def validate_mixed_coordinates(
    values: Any, domains: Sequence[BoFactorDomain], *, maximum: int = 10_000
) -> Any:
    import numpy as np

    from app.statistics.bo_factor_kernels import _numeric_array

    validate_bo_factor_domains(domains)
    if not any(isinstance(item, BoCategoricalFactorDomain) for item in domains):
        raise _invalid("bayesian_mixed_factor_required")
    try:
        matrix = _numeric_array(values)
        if matrix.ndim != 2 or matrix.shape[1] != len(domains) or not 1 <= len(matrix) <= maximum:
            raise _invalid()
        for index, domain in enumerate(domains):
            column = matrix[:, index]
            if isinstance(domain, BoCategoricalFactorDomain):
                if (
                    np.any(column < 0)
                    or np.any(column >= len(domain.levels))
                    or np.any(column != np.floor(column))
                ):
                    raise _invalid("bayesian_category_code_invalid")
            elif isinstance(domain, BoPseudocomponentFactorDomain):
                if np.any(column < 0) or np.any(column > domain.encoded_high):
                    raise _invalid("bayesian_factor_value_not_executable")
            else:
                if np.any(column < 0) or np.any(column > 1):
                    raise _invalid("bayesian_factor_value_not_executable")
                if domain.domain.domain_kind == "discrete_numeric":
                    for value in column:
                        domain.decode(float(value))
        return matrix
    except ValueError as exc:
        raise _invalid("bayesian_mixed_coordinates_invalid") from exc


def mixed_training_coverage(
    points: Any, domains: Sequence[BoFactorDomain], counts: Sequence[int]
) -> list[dict[str, Any]]:
    coverage = []
    for index, domain in enumerate(domains):
        if isinstance(domain, BoCategoricalFactorDomain):
            observations = [
                sum(int(n) for row, n in zip(points, counts, strict=True) if row[index] == level)
                for level in range(len(domain.levels))
            ]
            coverage.append(
                {
                    "factor_id": domain.factor_id,
                    "factor_index": index,
                    "declared_level_count": len(domain.levels),
                    "observed_level_count": sum(count > 0 for count in observations),
                    "raw_observation_counts": observations,
                    "unobserved_level_indices": [
                        i for i, count in enumerate(observations) if count == 0
                    ],
                    "correlation_policy": domain.correlation_policy,
                    "unobserved_level_policy": "prior_dependent_prediction_with_warning_v1",
                }
            )
    return coverage


@dataclass(frozen=True, kw_only=True)
class BoMixedSurrogate(BoSurrogate):
    factor_domains: tuple[BoFactorDomain, ...]
    training_targets_scaled: Any
    training_within_ss_scaled: Any

    def _signal_and_noise(self) -> tuple[Any, float]:
        return split_mixed_signal_noise(self.kernel)

    @property
    def covariance_roundoff_scale(self) -> float:
        signal, _ = self._signal_and_noise()
        numeric = signal.numeric_kernel
        return float(
            numeric.k1.constant_value if signal.numeric_indices else numeric.constant_value
        )

    def predict(self, x: Any, *, joint: bool = False) -> BoPosterior:
        query = validate_mixed_coordinates(x, self.factor_domains)
        return super().predict(query, joint=joint)

    def latent_cross_covariance(self, x: Any, z: Any) -> Any:
        left = validate_mixed_coordinates(x, self.factor_domains, maximum=256)
        right = validate_mixed_coordinates(z, self.factor_domains, maximum=8)
        return super().latent_cross_covariance(left, right)

    def metadata(self) -> dict[str, Any]:
        from app.statistics.bo_factor_kernels import bo_factor_kernel_to_payload

        signal, noise = self._signal_and_noise()
        return {
            "schema_version": MODEL_SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "factor_domains": bo_factor_domains_to_payload(self.factor_domains),
            "signal_kernel": bo_factor_kernel_to_payload(signal),
            "parameter_descriptors": [
                item.payload()
                for item in mixed_parameter_descriptors(self.kernel, self.factor_domains)
            ],
            "noise": {
                "mode": self.policy.noise_mode,
                "initial_variance_scaled": self.policy.initial_noise_variance_scaled
                if self.policy.noise_mode == "estimate"
                else noise,
                "bounds_scaled": [
                    self.policy.lower_noise_variance_scaled,
                    self.policy.upper_noise_variance_scaled,
                ]
                if self.policy.noise_mode == "estimate"
                else None,
                "fixed_sd_raw": self.policy.fixed_noise_sd,
                "fitted_variance_scaled": noise,
            },
            "observation_noise_sd_raw": math.sqrt(noise) * self.normalization_scale,
            "jitter": self.jitter,
            "normalization": {
                "mean": self.normalization_mean,
                "scale": self.normalization_scale,
                "direction_multiplier": self.direction_multiplier,
                "ddof": 0,
            },
            "optimizer": self.optimizer,
            "fit_diagnostics": self.fit_diagnostics,
            "log_marginal_likelihood": self.log_marginal_likelihood,
            "raw_observation_count": self.raw_observation_count,
            "effective_training_count": len(self.x_train),
            "training_group_counts": list(self.group_counts),
            "training_level_coverage": mixed_training_coverage(
                self.x_train, self.factor_domains, self.group_counts
            ),
            "warning_codes": list(self.warning_codes),
            "fit_elapsed_ms": self.fit_elapsed_ms,
            "package_versions": {
                name: version(name)
                for name in ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl")
            },
        }


def mixed_likelihood(
    theta: Any,
    kernel: Any,
    x: Any,
    y: Any,
    jitter: float,
    counts: Any,
    within_ss: Any,
) -> tuple[float, Any, Any, Any]:
    return _likelihood(
        theta,
        kernel,
        x,
        y,
        jitter,
        counts,
        within_ss,
        signal_noise_splitter=split_mixed_signal_noise,
    )


def _search_options(search: dict[str, Any]) -> None:
    limits = {
        "random_seed": (0, 2**32 - 1),
        "hyperparameter_restart_count": (0, 3),
        "model_max_iterations": (1, 200),
        "model_max_evaluations": (2, 2000),
    }
    for key, (lower, upper) in limits.items():
        if type(search.get(key)) is not int or not lower <= search[key] <= upper:
            raise _invalid("bayesian_mixed_fit_budget_invalid")
    jitter = search.get("jitter")
    if (
        isinstance(jitter, bool)
        or not isinstance(jitter, int | float)
        or not math.isfinite(jitter)
        or not 1e-12 <= jitter <= 1e-3
    ):
        raise _invalid("bayesian_surrogate_noise_invalid")


def _typed_starts(theta: Any, bounds: Any, descriptors: Sequence[BoMixedParameter]) -> list[Any]:
    import numpy as np

    positions = [
        item.index
        for item in descriptors
        if item.role not in {"signal_amplitude", "measurement_variance"}
    ]
    starts = [theta.copy()]
    for fraction in np.linspace(0, 1, 9):
        candidate = theta.copy()
        candidate[positions] = (
            bounds[positions, 0] * (1 - fraction) + bounds[positions, 1] * fraction
        )
        if not any(
            np.allclose(candidate, prior, rtol=0, atol=8 * np.finfo(float).eps) for prior in starts
        ):
            starts.append(candidate)
    return starts


def mixed_bound_hits(kernel: Any, domains: Sequence[BoFactorDomain]) -> list[dict[str, Any]]:
    hits = []
    for descriptor, value, bounds in zip(
        mixed_parameter_descriptors(kernel, domains), kernel.theta, kernel.bounds, strict=True
    ):
        for side, bound in zip(("lower", "upper"), bounds, strict=True):
            if math.isclose(math.exp(float(value)), math.exp(float(bound)), rel_tol=1e-5):
                hits.append(
                    {
                        **descriptor.payload(),
                        "side": side,
                        "value": math.exp(float(value)),
                        "bound": math.exp(float(bound)),
                    }
                )
    return hits


def fit_bo_mixed_surrogate(
    x: Any,
    targets_scaled: Any,
    factor_domains: Sequence[BoFactorDomain],
    policy: BoSurrogatePolicy,
    search: dict[str, Any],
    *,
    deadline: float,
    normalization_mean: float,
    normalization_scale: float,
    direction_multiplier: float = 1.0,
    group_counts: Sequence[int] | None = None,
    within_ss_scaled: Any | None = None,
    raw_observation_count: int | None = None,
    kernel_spec: BoKernelSpec | None = None,
    fit_policy: BoFitPolicy | None = None,
    optimize: bool = True,
    initial_signal_payload: dict[str, Any] | None = None,
) -> BoMixedSurrogate:
    """Fit an explicit training view; normalization belongs to the original raw rows.

    For compressed exact repeats, callers must provide raw counts and within-cell
    sum of squares in the same standardized response coordinates. No implicit
    averaging, category merging, scaling, or jitter/noise substitution occurs.
    """
    import numpy as np
    from scipy.optimize import minimize  # type: ignore[import-untyped]
    from sklearn.gaussian_process.kernels import WhiteKernel
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    from app.statistics.bo_factor_kernels import (
        _numeric_array,
        bo_factor_kernel_from_payload,
        build_bo_factor_kernel,
        validate_bo_factor_kernel_domains,
    )

    started = time.perf_counter()
    _search_options(search)
    if (
        type(optimize) is not bool
        or not isinstance(policy, BoSurrogatePolicy)
        or (fit_policy is not None and (not isinstance(fit_policy, BoFitPolicy) or not optimize))
    ):
        raise _invalid()
    if (
        any(
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            for value in (normalization_mean, normalization_scale, direction_multiplier, deadline)
        )
        or normalization_scale <= 0
        or direction_multiplier not in {-1, 1}
    ):
        raise _invalid()
    domains = tuple(factor_domains)
    points = validate_mixed_coordinates(x, domains, maximum=200)
    y = _numeric_array(targets_scaled)
    if y.shape != (len(points),):
        raise _invalid()
    counts = tuple(group_counts) if group_counts is not None else (1,) * len(points)
    if len(counts) != len(points) or any(
        type(value) is not int or not 1 <= value <= 200 for value in counts
    ):
        raise _invalid("bayesian_observation_group_invalid")
    raw_count = sum(counts)
    if not 2 <= raw_count <= 200 or (
        raw_observation_count is not None
        and (type(raw_observation_count) is not int or raw_observation_count != raw_count)
    ):
        raise _invalid("bayesian_observation_group_invalid")
    if within_ss_scaled is None and any(value != 1 for value in counts):
        raise _invalid("bayesian_observation_group_invalid")
    within_ss = (
        np.zeros(len(points)) if within_ss_scaled is None else _numeric_array(within_ss_scaled)
    )
    if (
        within_ss.shape != y.shape
        or np.any(within_ss < 0)
        or any(count == 1 and value != 0 for count, value in zip(counts, within_ss, strict=True))
    ):
        raise _invalid("bayesian_observation_group_invalid")
    # Distinct declared condition groups can have identical coordinates. Keep
    # their means/counts/within-SS separate; source membership is bound by planning.
    specification = kernel_spec or BoKernelSpec()
    signal = (
        build_bo_factor_kernel(domains, specification)
        if initial_signal_payload is None
        else bo_factor_kernel_from_payload(initial_signal_payload)
    )
    validate_bo_factor_kernel_domains(signal, domains)
    if signal.numeric_indices:
        from app.statistics.bo_kernels import kernel_family

        if kernel_family(signal.numeric_kernel.k2) != specification.kind:
            raise _invalid()
    kernel = signal
    if policy.noise_mode != "near_noiseless":
        noise = policy.initial_noise_variance_scaled
        bounds: Any = (policy.lower_noise_variance_scaled, policy.upper_noise_variance_scaled)
        if policy.noise_mode == "fixed":
            assert policy.fixed_noise_sd is not None
            noise, bounds = (policy.fixed_noise_sd / normalization_scale) ** 2, "fixed"
        if not math.isfinite(noise) or noise <= 0:
            raise _invalid("bayesian_surrogate_noise_invalid")
        kernel = signal + WhiteKernel(noise, bounds)
    descriptors = mixed_parameter_descriptors(kernel, domains)
    if optimize and not descriptors:
        raise _invalid("bayesian_mixed_no_free_parameters")
    theta, bounds = kernel.theta.copy(), kernel.bounds.copy()
    evaluations = 0
    screening: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    best_value, best_theta = math.inf, theta.copy()
    selected: dict[str, Any] | None = None
    warnings: list[str] = []
    jitter = float(search["jitter"])

    def evaluate(point: Any, stage: str, index: int | None) -> tuple[float, Any]:
        nonlocal evaluations, best_value, best_theta, selected
        if time.perf_counter() >= deadline:
            raise _invalid("bayesian_optimization_time_budget_exhausted")
        # Reserve the final factorization in the same total likelihood budget.
        if evaluations >= search["model_max_evaluations"] - 1:
            raise _invalid("bayesian_optimization_budget_exhausted")
        evaluations += 1
        value, derivative, _, _ = mixed_likelihood(
            point, kernel, points, y, jitter, counts, within_ss
        )
        objective = -value
        if objective < best_value:
            best_value, best_theta = objective, point.copy()
            selected = {
                "stage": stage,
                "index": index,
                "evaluation": evaluations,
                "log_parameters": point.tolist(),
                "negative_log_likelihood": objective,
            }
        return objective, -derivative

    try:
        with threadpool_limits(limits=1):
            if optimize:
                starts = [theta]
                if fit_policy is not None:
                    screens = _typed_starts(theta, bounds, descriptors)
                    for index, initial in enumerate(screens):
                        value, _ = evaluate(initial, "screen", index)
                        screening.append(
                            {"log_parameters": initial.tolist(), "negative_log_likelihood": value}
                        )
                    order = sorted(
                        range(len(screens)),
                        key=lambda i: (screening[i]["negative_log_likelihood"], i),
                    )[: fit_policy.deterministic_start_count]
                    starts = [screens[index] for index in order]
                rng = np.random.default_rng(search["random_seed"])
                starts.extend(
                    rng.uniform(bounds[:, 0], bounds[:, 1])
                    for _ in range(search["hyperparameter_restart_count"])
                )
                for index, initial in enumerate(starts):
                    before = evaluations
                    result = minimize(
                        lambda point, start_index=index: evaluate(point, "local", start_index),
                        initial,
                        method="L-BFGS-B",
                        jac=True,
                        bounds=bounds,
                        options={
                            "maxiter": search["model_max_iterations"],
                            "maxfun": search["model_max_evaluations"],
                            "ftol": 1e-12,
                        },
                    )
                    if not np.all(np.isfinite(result.x)) or not math.isfinite(float(result.fun)):
                        raise _invalid("bayesian_optimization_surrogate_fit_failed")
                    traces.append(
                        {
                            "success": bool(result.success),
                            "status": int(result.status),
                            "termination_reason": str(result.message),
                            "iterations": int(result.nit),
                            "evaluations": evaluations - before,
                            "initial_log_parameters": initial.tolist(),
                            "final_log_parameters": result.x.tolist(),
                            "negative_log_likelihood": float(result.fun),
                        }
                    )
                    if not result.success:
                        warnings.append("bayesian_optimization_model_convergence_warning")
                theta = best_theta
            if time.perf_counter() >= deadline:
                raise _invalid("bayesian_optimization_time_budget_exhausted")
            evaluations += 1
            value, _, lower, alpha = mixed_likelihood(
                theta, kernel, points, y, jitter, counts, within_ss
            )
    except (ArithmeticError, np.linalg.LinAlgError) as exc:
        raise _invalid("bayesian_optimization_surrogate_fit_failed") from exc
    fitted = kernel.clone_with_theta(theta)
    hits = mixed_bound_hits(fitted, domains)
    if any(hit["role"] == "measurement_variance" for hit in hits):
        warnings.append("bayesian_surrogate_noise_bound")
    if any(hit["role"] != "measurement_variance" for hit in hits):
        warnings.append("bayesian_surrogate_signal_bound")
    coverage = mixed_training_coverage(points, domains, counts)
    if any(item["unobserved_level_indices"] for item in coverage):
        warnings.append("bayesian_category_unobserved_level_prior_dependent")
    if any(item["observed_level_count"] == 1 for item in coverage):
        warnings.append("bayesian_category_correlation_unidentified")
    optimizer = {
        "name": "L-BFGS-B",
        "optimized": optimize,
        "seed": search["random_seed"],
        "restarts": search["hyperparameter_restart_count"] if optimize else 0,
        "max_iterations": search["model_max_iterations"],
        "max_evaluations": search["model_max_evaluations"],
        "ftol": 1e-12,
        "evaluations": evaluations,
        "starts": traces,
    }
    diagnostics = {
        "schema_version": 2,
        "policy": FIT_POLICY_VERSION,
        "deterministic_start_count": fit_policy.deterministic_start_count if fit_policy else 1,
        "parameter_descriptors": [item.payload() for item in descriptors],
        "screening": screening,
        "selected": selected,
        "bound_hits": hits,
        "global_optimum_guaranteed": False,
        "final_factorization_evaluations": 1,
    }
    return BoMixedSurrogate(
        kernel=fitted,
        x_train=points.copy(),
        lower=lower,
        alpha=alpha,
        policy=policy,
        normalization_mean=float(normalization_mean),
        normalization_scale=float(normalization_scale),
        direction_multiplier=float(direction_multiplier),
        jitter=jitter,
        log_marginal_likelihood=value,
        optimizer=optimizer,
        warning_codes=tuple(dict.fromkeys(warnings)),
        fit_elapsed_ms=(time.perf_counter() - started) * 1000,
        raw_observation_count=raw_count,
        group_counts=counts,
        kernel_spec=specification,
        fit_diagnostics=diagnostics,
        factor_domains=domains,
        training_targets_scaled=y.copy(),
        training_within_ss_scaled=within_ss.copy(),
    )
