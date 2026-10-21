"""Versioned BO exact posterior; standalone GPR defaults are intentionally separate."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any, Literal

from app.statistics.bayesian_optimization import BayesianOptimizationError

POLICY_VERSION = "bo_noise_latent_v2"
MODEL_SCHEMA_VERSION = 3


@dataclass(frozen=True)
class BoSurrogatePolicy:
    noise_mode: Literal["estimate", "fixed", "near_noiseless"] = "estimate"
    initial_noise_variance_scaled: float = 1e-2
    lower_noise_variance_scaled: float = 1e-6
    upper_noise_variance_scaled: float = 1.0
    fixed_noise_sd: float | None = None

    def __post_init__(self) -> None:
        if self.noise_mode not in {"estimate", "fixed", "near_noiseless"}:
            raise ValueError("bayesian_surrogate_policy_invalid")
        values = (
            self.lower_noise_variance_scaled,
            self.initial_noise_variance_scaled,
            self.upper_noise_variance_scaled,
        )
        if any(isinstance(v, bool) or not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError("bayesian_surrogate_noise_invalid")
        if not values[0] < values[2] or not values[0] <= values[1] <= values[2]:
            raise ValueError("bayesian_surrogate_noise_invalid")
        if self.noise_mode == "fixed":
            if (
                self.fixed_noise_sd is None
                or isinstance(self.fixed_noise_sd, bool)
                or not math.isfinite(self.fixed_noise_sd)
                or self.fixed_noise_sd <= 0
            ):
                raise ValueError("bayesian_surrogate_noise_invalid")
        elif self.fixed_noise_sd is not None:
            raise ValueError("bayesian_surrogate_noise_invalid")


@dataclass(frozen=True)
class BoPosterior:
    mean_scaled: Any
    latent_variance_scaled: Any
    predictive_variance_scaled: Any
    latent_covariance_scaled: Any | None = None


def split_signal_noise(kernel: Any) -> tuple[Any, float]:
    import numpy as np
    from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
        ConstantKernel,
        Matern,
        Product,
        Sum,
        WhiteKernel,
    )

    signal, noise = kernel, 0.0
    if isinstance(kernel, Sum):
        if not isinstance(kernel.k2, WhiteKernel):
            raise ValueError("bayesian_surrogate_kernel_invalid")
        signal, noise = kernel.k1, float(kernel.k2.noise_level)
    if (
        not isinstance(signal, Product)
        or not isinstance(signal.k1, ConstantKernel)
        or not isinstance(signal.k2, Matern)
        or signal.k2.nu != 2.5
        or not math.isfinite(noise)
        or noise < 0
    ):
        raise ValueError("bayesian_surrogate_kernel_invalid")
    lengths = np.atleast_1d(signal.k2.length_scale)
    if (
        not math.isfinite(float(signal.k1.constant_value))
        or signal.k1.constant_value <= 0
        or not np.all(np.isfinite(lengths))
        or np.any(lengths <= 0)
    ):
        raise ValueError("bayesian_surrogate_kernel_invalid")
    return signal, noise


def _kernel(predictor_count: int, policy: BoSurrogatePolicy, scale: float) -> Any:
    import numpy as np
    from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
        ConstantKernel,
        Matern,
        WhiteKernel,
    )

    signal = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(
        np.ones(predictor_count), (1e-2, 1e2), nu=2.5
    )
    if policy.noise_mode == "near_noiseless":
        return signal
    if policy.noise_mode == "fixed":
        assert policy.fixed_noise_sd is not None
        scaled_sd = policy.fixed_noise_sd / scale
        noise = scaled_sd * scaled_sd
        if not math.isfinite(noise) or noise <= 0:
            raise BayesianOptimizationError("bayesian_surrogate_noise_invalid")
        return signal + WhiteKernel(noise, "fixed")
    return signal + WhiteKernel(
        policy.initial_noise_variance_scaled,
        (policy.lower_noise_variance_scaled, policy.upper_noise_variance_scaled),
    )


def _likelihood(
    theta: Any,
    kernel: Any,
    x: Any,
    y: Any,
    jitter: float,
    counts: Any | None = None,
    within_ss: Any | None = None,
) -> tuple[float, Any, Any, Any]:
    import numpy as np
    from scipy.linalg import cho_solve, cholesky  # type: ignore[import-untyped]

    current = kernel.clone_with_theta(theta)
    covariance, gradient = current(x, eval_gradient=True)
    indices = np.diag_indices_from(covariance)
    correction, noise_derivative = 0.0, 0.0
    estimated_noise = False
    if counts is None:
        covariance[indices] += jitter
    else:
        _, noise = split_signal_noise(current)
        variance = noise + jitter
        counts, within_ss = np.asarray(counts, dtype=float), np.asarray(within_ss, dtype=float)
        if (
            counts.shape != (len(x),)
            or within_ss.shape != (len(x),)
            or not np.all(np.isfinite(counts))
            or np.any(counts < 1)
            or np.any(counts != np.floor(counts))
            or not np.all(np.isfinite(within_ss))
            or np.any(within_ss < 0)
        ):
            raise BayesianOptimizationError("bayesian_observation_group_invalid")
        covariance[indices] += variance / counts - noise
        correction = -0.5 * float(
            np.sum(
                (counts - 1) * math.log(2 * math.pi * variance)
                + within_ss / variance
                + np.log(counts)
            )
        )
        from sklearn.gaussian_process.kernels import Sum  # type: ignore[import-untyped]

        estimated_noise = (
            isinstance(current, Sum) and not current.k2.hyperparameter_noise_level.fixed
        )
        if estimated_noise:
            # WhiteKernel is the final free log parameter in this explicitly validated tree.
            gradient[indices[0], indices[1], -1] = noise / counts
            noise_derivative = (
                -0.5 * noise * float(np.sum((counts - 1) / variance - within_ss / variance**2))
            )
    lower = cholesky(covariance, lower=True, check_finite=False)
    alpha = cho_solve((lower, True), y, check_finite=False)
    value = float(
        -0.5 * y @ alpha
        - np.log(np.diag(lower)).sum()
        - 0.5 * len(x) * math.log(2 * math.pi)
        + correction
    )
    inverse = cho_solve((lower, True), np.eye(len(x)), check_finite=False)
    derivative = 0.5 * np.einsum("ij,ijk->k", np.outer(alpha, alpha) - inverse, gradient)
    if estimated_noise:
        derivative[-1] += noise_derivative
    if not math.isfinite(value) or not np.all(np.isfinite(derivative)):
        raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed")
    return value, derivative, lower, alpha


def checked_variance(values: Any, scale: float) -> Any:
    import numpy as np

    result = np.asarray(values, dtype=float)
    tolerance = 64 * np.finfo(float).eps * max(1.0, float(scale))
    if not np.all(np.isfinite(result)) or np.any(result < -tolerance):
        raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
    return np.maximum(result, 0.0)


@dataclass(frozen=True)
class BoSurrogate:
    kernel: Any
    x_train: Any
    lower: Any
    alpha: Any
    policy: BoSurrogatePolicy
    normalization_mean: float
    normalization_scale: float
    direction_multiplier: float
    jitter: float
    log_marginal_likelihood: float
    optimizer: dict[str, Any]
    warning_codes: tuple[str, ...]
    fit_elapsed_ms: float
    raw_observation_count: int
    group_counts: tuple[int, ...]

    @property
    def covariance_roundoff_scale(self) -> float:
        signal, _ = split_signal_noise(self.kernel)
        return float(signal.k1.constant_value)

    def latent_cross_covariance(self, x: Any, z: Any) -> Any:
        """Bounded cross block for batch planning, without a query-by-query matrix."""
        import numpy as np
        from scipy.linalg import solve_triangular  # type: ignore[import-untyped]

        left, right = np.asarray(x, dtype=float), np.asarray(z, dtype=float)
        for query, maximum in ((left, 256), (right, 8)):
            if (
                query.ndim != 2
                or query.shape[1] != self.x_train.shape[1]
                or not 1 <= len(query) <= maximum
                or not np.all(np.isfinite(query))
            ):
                raise BayesianOptimizationError("bayesian_surrogate_prediction_invalid")
        signal, _ = split_signal_noise(self.kernel)
        left_solved = solve_triangular(
            self.lower, signal(self.x_train, left), lower=True, check_finite=False
        )
        right_solved = solve_triangular(
            self.lower, signal(self.x_train, right), lower=True, check_finite=False
        )
        cross = signal(left, right) - left_solved.T @ right_solved
        if not np.all(np.isfinite(cross)):
            raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
        return cross

    def predict(self, x: Any, *, joint: bool = False) -> BoPosterior:
        import numpy as np
        from scipy.linalg import solve_triangular  # type: ignore[import-untyped]

        query = np.asarray(x, dtype=float)
        if (
            query.ndim != 2
            or query.shape[1] != self.x_train.shape[1]
            or len(query) == 0
            or not np.all(np.isfinite(query))
            or (joint and len(query) > 256)
        ):
            raise BayesianOptimizationError("bayesian_surrogate_prediction_invalid")
        signal, noise = split_signal_noise(self.kernel)
        means, variances = [], []
        joint_covariance = None
        for start in range(0, len(query), 256):
            chunk = query[start : start + 256]
            cross = signal(self.x_train, chunk)
            solved = solve_triangular(self.lower, cross, lower=True, check_finite=False)
            mean = cross.T @ self.alpha
            diagonal = signal.diag(chunk)
            variance = checked_variance(
                diagonal - np.einsum("ij,ij->j", solved, solved), float(diagonal.max())
            )
            if not np.all(np.isfinite(mean)):
                raise BayesianOptimizationError("bayesian_surrogate_prediction_invalid")
            if joint:
                joint_covariance = signal(chunk) - solved.T @ solved
                joint_covariance = (joint_covariance + joint_covariance.T) * 0.5
                tolerance = 64 * np.finfo(float).eps * max(1.0, float(diagonal.max())) * len(chunk)
                if float(np.linalg.eigvalsh(joint_covariance).min()) < -tolerance:
                    raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
                np.fill_diagonal(joint_covariance, variance)
            means.append(mean)
            variances.append(variance)
        latent = np.concatenate(variances)
        return BoPosterior(np.concatenate(means), latent, latent + noise, joint_covariance)

    def metadata(self) -> dict[str, Any]:
        import numpy as np

        signal, noise = split_signal_noise(self.kernel)
        return {
            "schema_version": MODEL_SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "signal_kernel": {
                "kind": "constant_times_matern_5_2_ard",
                "amplitude": float(signal.k1.constant_value),
                "length_scales": np.atleast_1d(signal.k2.length_scale).tolist(),
                "amplitude_bounds": [1e-3, 1e3],
                "length_scale_bounds": [1e-2, 1e2],
            },
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
                "ddof": 0,
                "direction_multiplier": self.direction_multiplier,
            },
            "optimizer": self.optimizer,
            "log_marginal_likelihood": self.log_marginal_likelihood,
            "raw_observation_count": self.raw_observation_count,
            "effective_training_count": len(self.x_train),
            "training_group_counts": list(self.group_counts),
            "fit_elapsed_ms": self.fit_elapsed_ms,
            "package_versions": {
                name: version(name)
                for name in ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl")
            },
        }


def fit_bo_surrogate(
    x: Any,
    raw_y: Any,
    policy: BoSurrogatePolicy,
    search: dict[str, Any],
    *,
    deadline: float,
    goal_type: Literal["maximize", "minimize", "match_target"] = "maximize",
    optimize: bool = True,
    group_member_indices: tuple[tuple[int, ...], ...] | None = None,
) -> BoSurrogate:
    import numpy as np
    from scipy.optimize import minimize  # type: ignore[import-untyped]
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    started = time.perf_counter()
    points, observed = np.asarray(x, dtype=float), np.asarray(raw_y, dtype=float)
    if (
        points.ndim != 2
        or not 1 <= points.shape[1] <= 10
        or not 2 <= len(points) <= 200
        or observed.shape != (len(points),)
        or not np.all(np.isfinite(points))
        or not np.all(np.isfinite(observed))
        or goal_type not in {"maximize", "minimize", "match_target"}
    ):
        raise BayesianOptimizationError("bayesian_optimization_history_incomplete")
    multiplier = -1.0 if goal_type == "minimize" else 1.0
    transformed = multiplier * observed
    mean, scale = float(np.mean(transformed)), float(np.std(transformed, ddof=0))
    warning_codes: list[str] = []
    if not math.isfinite(mean) or not math.isfinite(scale):
        raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed")
    if scale <= max(1e-12, abs(mean) * 1e-12):
        scale = 1.0
        warning_codes.append("bayesian_optimization_constant_objective")
    y = (transformed - mean) / scale
    raw_count = len(points)
    counts, within_ss = None, None
    if group_member_indices is not None:
        flat = [index for group in group_member_indices for index in group]
        if (
            any(not group for group in group_member_indices)
            or any(isinstance(index, bool) or not isinstance(index, int) for index in flat)
            or sorted(flat) != list(range(raw_count))
        ):
            raise BayesianOptimizationError("bayesian_observation_group_invalid")
        for group in group_member_indices:
            if not np.all(points[list(group)] == points[group[0]]):
                raise BayesianOptimizationError("bayesian_observation_group_invalid")
        counts = np.array([len(group) for group in group_member_indices], dtype=float)
        means = np.array([y[list(group)].mean() for group in group_member_indices])
        within_ss = np.array(
            [
                np.sum((y[list(group)] - means[i]) ** 2)
                for i, group in enumerate(group_member_indices)
            ]
        )
        points = points[[group[0] for group in group_member_indices]]
        y = means
    jitter = float(search["jitter"])
    if not math.isfinite(jitter) or not 1e-12 <= jitter <= 1e-3:
        raise BayesianOptimizationError("bayesian_surrogate_noise_invalid")
    kernel = _kernel(points.shape[1], policy, scale)
    evaluations = 0
    traces: list[dict[str, Any]] = []

    def evaluate(theta: Any) -> tuple[float, Any]:
        nonlocal evaluations
        if time.perf_counter() >= deadline:
            raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")
        if evaluations >= search["model_max_evaluations"]:
            raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
        evaluations += 1
        value, derivative, _, _ = _likelihood(theta, kernel, points, y, jitter, counts, within_ss)
        return -value, -derivative

    theta = kernel.theta.copy()
    try:
        with threadpool_limits(limits=1):
            if optimize:
                rng = np.random.default_rng(search["random_seed"])
                starts = [theta] + [
                    rng.uniform(kernel.bounds[:, 0], kernel.bounds[:, 1])
                    for _ in range(search["hyperparameter_restart_count"])
                ]
                best_value = math.inf
                for initial in starts:
                    result = minimize(
                        evaluate,
                        initial,
                        method="L-BFGS-B",
                        jac=True,
                        bounds=kernel.bounds,
                        options={
                            "maxiter": search["model_max_iterations"],
                            "maxfun": search["model_max_evaluations"],
                            "ftol": 1e-12,
                        },
                    )
                    if not np.all(np.isfinite(result.x)) or not math.isfinite(float(result.fun)):
                        raise BayesianOptimizationError(
                            "bayesian_optimization_surrogate_fit_failed"
                        )
                    traces.append(
                        {
                            "success": bool(result.success),
                            "status": int(result.status),
                            "termination_reason": str(result.message),
                            "iterations": int(result.nit),
                            "evaluations": int(result.nfev),
                            "initial_log_parameters": initial.tolist(),
                            "final_log_parameters": result.x.tolist(),
                            "negative_log_likelihood": float(result.fun),
                        }
                    )
                    if result.fun < best_value:
                        best_value, theta = float(result.fun), result.x.copy()
                    if not result.success:
                        warning_codes.append("bayesian_optimization_model_convergence_warning")
            if time.perf_counter() >= deadline:
                raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")
            value, _, lower, alpha = _likelihood(
                theta, kernel, points, y, jitter, counts, within_ss
            )
    except (ArithmeticError, np.linalg.LinAlgError) as exc:
        raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed") from exc
    fitted = kernel.clone_with_theta(theta)
    _, noise = split_signal_noise(fitted)
    if policy.noise_mode == "estimate":
        if math.isclose(noise, policy.lower_noise_variance_scaled, rel_tol=1e-5) or math.isclose(
            noise, policy.upper_noise_variance_scaled, rel_tol=1e-5
        ):
            warning_codes.append("bayesian_surrogate_noise_bound")
    return BoSurrogate(
        fitted,
        points.copy(),
        lower,
        alpha,
        policy,
        mean,
        scale,
        multiplier,
        jitter,
        value,
        {
            "name": "L-BFGS-B",
            "optimized": optimize,
            "seed": search["random_seed"],
            "restarts": search["hyperparameter_restart_count"] if optimize else 0,
            "max_iterations": search["model_max_iterations"],
            "max_evaluations": search["model_max_evaluations"],
            "ftol": 1e-12,
            "evaluations": evaluations,
            "starts": traces,
        },
        tuple(dict.fromkeys(warning_codes)),
        (time.perf_counter() - started) * 1000,
        raw_count,
        tuple(int(count) for count in counts) if counts is not None else (1,) * raw_count,
    )
