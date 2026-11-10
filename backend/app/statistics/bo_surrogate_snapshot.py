"""Bounded numeric BO state; callers own its source hash and artifact permissions.

Loading validates the stored factorization and solves, but does not refit or
recompute the raw likelihood correction of compressed replicates. Reports use
the stored package versions, not ``restored.metadata()``'s runtime versions.
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_kernels import BoKernelSpec, kernel_family, signal_kernel
from app.statistics.bo_surrogate import BoSurrogate, BoSurrogatePolicy, split_signal_noise

SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOT_POLICY = "bo_numeric_surrogate_state_v1"
ERROR_CODE = "bayesian_surrogate_snapshot_invalid"

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Positive = Annotated[Number, Field(gt=0)]
Nonnegative = Annotated[Number, Field(ge=0)]
Count = Annotated[int, Field(strict=True, ge=1, le=200)]
Parameters = Annotated[list[Number], Field(min_length=2, max_length=12)]
Vector = Annotated[list[Number], Field(min_length=1, max_length=200)]
KernelKind = Literal["matern_5_2", "matern_3_2", "gaussian", "exponential"]
_TARGETS = TypeAdapter(Vector, config=ConfigDict(strict=True))


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Kernel(_Strict):
    family: KernelKind
    amplitude: Positive
    length_scales: list[Positive] = Field(min_length=1, max_length=10)
    explicit_family: bool


class _Noise(_Strict):
    noise_mode: Literal["estimate", "fixed", "near_noiseless"]
    initial_noise_variance_scaled: Positive
    lower_noise_variance_scaled: Positive
    upper_noise_variance_scaled: Positive
    fixed_noise_sd: Positive | None


class _Normalization(_Strict):
    mean: Number
    scale: Positive
    direction_multiplier: Number
    ddof: Literal[0]


class _Start(_Strict):
    success: bool
    status: int
    termination_reason: str = Field(max_length=512)
    iterations: int = Field(ge=0, le=200)
    evaluations: int = Field(ge=0, le=2000)
    initial_log_parameters: Parameters
    final_log_parameters: Parameters
    negative_log_likelihood: Number


class _Optimizer(_Strict):
    name: Literal["L-BFGS-B"]
    optimized: bool
    seed: int = Field(ge=0, le=2**32 - 1)
    restarts: int = Field(ge=0, le=3)
    max_iterations: int = Field(ge=1, le=200)
    max_evaluations: int = Field(ge=2, le=2000)
    ftol: Positive
    evaluations: int = Field(ge=0, le=2000)
    starts: list[_Start] = Field(max_length=6)


class _Screen(_Strict):
    log_parameters: Parameters
    negative_log_likelihood: Number


class _Best(_Screen):
    evaluation_index: int = Field(ge=0, le=1999)


class _Selected(_Screen):
    stage: Literal["screen", "local_evaluation"]
    screen_index: int | None = Field(ge=0, le=8)
    start_index: int | None = Field(ge=0, le=5)

    @model_validator(mode="after")
    def validate_origin(self) -> _Selected:
        if (self.stage == "screen") != (self.screen_index is not None) or (
            self.stage == "local_evaluation"
        ) != (self.start_index is not None):
            raise ValueError(ERROR_CODE)
        return self


class _Bound(_Strict):
    parameter: Literal["signal_amplitude", "length_scale", "measurement_variance"]
    factor_index: int | None = Field(ge=0, le=9)
    side: Literal["lower", "upper"]
    value: Positive
    bound: Positive


class _Diagnostics(_Strict):
    schema_version: Literal[1]
    policy: Literal["bounded_multiscale_starts_v1"]
    deterministic_start_count: int = Field(ge=1, le=3)
    screening: list[_Screen] = Field(min_length=9, max_length=9)
    refined_screen_indices: list[Annotated[int, Field(ge=0, le=8)]] = Field(
        min_length=1, max_length=3
    )
    start_initial_negative_log_likelihoods: list[Number] = Field(min_length=1, max_length=6)
    start_best_evaluations: list[_Best] = Field(min_length=1, max_length=6)
    selected: _Selected
    bound_hits: list[_Bound] = Field(max_length=12)
    global_optimum_guaranteed: Literal[False]


class _Training(_Strict):
    x_normalized: list[Annotated[list[Number], Field(min_length=1, max_length=10)]] = Field(
        min_length=1, max_length=200
    )
    targets_scaled: Vector
    group_counts: list[Count] = Field(min_length=1, max_length=200)
    raw_observation_count: int = Field(ge=2, le=200)


class _Factorization(_Strict):
    lower: list[Vector] = Field(min_length=1, max_length=200)
    alpha: Vector


class _Fit(_Strict):
    log_marginal_likelihood: Number
    optimizer: _Optimizer
    warning_codes: list[str] = Field(max_length=32)
    elapsed_ms: Nonnegative
    diagnostics: _Diagnostics | None
    package_versions: dict[str, str]


class _Snapshot(_Strict):
    schema_version: Literal[1]
    policy: Literal["bo_numeric_surrogate_state_v1"]
    kernel: _Kernel
    noise_policy: _Noise
    noise_variance_scaled: Nonnegative
    normalization: _Normalization
    jitter: Number = Field(ge=1e-12, le=1e-3)
    training: _Training
    factorization: _Factorization
    fit: _Fit


def _invalid() -> BayesianOptimizationError:
    return BayesianOptimizationError(ERROR_CODE)


def _check_json_tree(payload: Any) -> None:
    pending = [(payload, 0)]
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if visited > 50000 or depth > 8:
            raise _invalid()
        kind = type(value)
        if kind is dict:
            if len(value) > 64 or any(type(key) is not str or len(key) > 64 for key in value):
                raise _invalid()
            pending.extend((item, depth + 1) for item in value.values())
        elif kind is list:
            if len(value) > 200:
                raise _invalid()
            pending.extend((item, depth + 1) for item in value)
        elif kind is float:
            if not math.isfinite(value):
                raise _invalid()
        elif kind is str:
            if len(value) > 512:
                raise _invalid()
        elif kind not in {int, str, bool, type(None)}:
            raise _invalid()


def _validated_snapshot(payload: Any) -> _Snapshot:
    _check_json_tree(payload)
    if (
        type(payload) is not dict
        or type(payload.get("schema_version")) is not int
        or type(payload.get("normalization")) is not dict
        or type(payload["normalization"].get("ddof")) is not int
    ):
        raise _invalid()
    try:
        result = _Snapshot.model_validate(payload)
    except ValidationError:
        raise _invalid() from None
    diagnostics = payload["fit"]["diagnostics"]
    if diagnostics is not None and (
        type(diagnostics["schema_version"]) is not int
        or type(diagnostics["global_optimum_guaranteed"]) is not bool
    ):
        raise _invalid()
    return result


def _restore_kernel(state: _Snapshot, predictor_count: int) -> tuple[Any, BoSurrogatePolicy]:
    import numpy as np
    from sklearn.gaussian_process.kernels import WhiteKernel  # type: ignore[import-untyped]

    item = state.kernel
    if len(item.length_scales) != predictor_count or (
        not item.explicit_family and item.family != "matern_5_2"
    ):
        raise _invalid()
    tolerance = 32 * np.finfo(float).eps
    if not 1e-3 * (1 - tolerance) <= item.amplitude <= 1e3 * (1 + tolerance) or any(
        not 1e-2 * (1 - tolerance) <= value <= 1e2 * (1 + tolerance) for value in item.length_scales
    ):
        raise _invalid()
    try:
        policy = BoSurrogatePolicy(**state.noise_policy.model_dump())
    except ValueError:
        raise _invalid() from None
    signal = signal_kernel(predictor_count, BoKernelSpec(item.family))
    signal.k1.constant_value = item.amplitude
    signal.k2.length_scale = np.array(item.length_scales, dtype=float)
    noise = state.noise_variance_scaled
    if policy.noise_mode == "near_noiseless":
        if noise != 0:
            raise _invalid()
        return signal, policy
    if noise <= 0:
        raise _invalid()
    if policy.noise_mode == "fixed":
        assert policy.fixed_noise_sd is not None
        scaled_sd = policy.fixed_noise_sd / state.normalization.scale
        expected = scaled_sd * scaled_sd
        if not math.isfinite(expected) or not math.isclose(noise, expected, rel_tol=tolerance):
            raise _invalid()
        return signal + WhiteKernel(noise, "fixed"), policy
    if not (
        policy.lower_noise_variance_scaled * (1 - tolerance)
        <= noise
        <= policy.upper_noise_variance_scaled * (1 + tolerance)
    ):
        raise _invalid()
    return signal + WhiteKernel(
        noise, (policy.lower_noise_variance_scaled, policy.upper_noise_variance_scaled)
    ), policy


def _check_fit(state: _Snapshot, parameter_count: int) -> None:
    fit, optimizer = state.fit, state.fit.optimizer
    if (
        optimizer.evaluations > optimizer.max_evaluations
        or (not optimizer.optimized and (optimizer.evaluations or optimizer.starts))
        or set(fit.package_versions)
        != {"numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl"}
        or any(not value or len(value) > 64 for value in fit.package_versions.values())
        or any(
            not code.startswith("bayesian_")
            or not code.isascii()
            or len(code) > 128
            or not code.replace("_", "").isalnum()
            for code in fit.warning_codes
        )
    ):
        raise _invalid()
    for start in optimizer.starts:
        if (
            len(start.initial_log_parameters) != parameter_count
            or len(start.final_log_parameters) != parameter_count
            or start.iterations > optimizer.max_iterations
        ):
            raise _invalid()
    diagnostics = fit.diagnostics
    expected_start_count = (
        (diagnostics.deterministic_start_count if diagnostics else 1) + optimizer.restarts
        if optimizer.optimized
        else 0
    )
    if len(optimizer.starts) != expected_start_count or optimizer.evaluations != sum(
        start.evaluations for start in optimizer.starts
    ) + (len(diagnostics.screening) if diagnostics else 0):
        raise _invalid()
    if diagnostics is not None:
        if (
            not state.kernel.explicit_family
            or not optimizer.optimized
            or len(diagnostics.refined_screen_indices) != diagnostics.deterministic_start_count
            or len(set(diagnostics.refined_screen_indices))
            != len(diagnostics.refined_screen_indices)
            or len(diagnostics.start_best_evaluations) != len(optimizer.starts)
            or len(diagnostics.start_initial_negative_log_likelihoods) != len(optimizer.starts)
            or any(
                len(item.log_parameters) != parameter_count
                for item in [
                    *diagnostics.screening,
                    *diagnostics.start_best_evaluations,
                    diagnostics.selected,
                ]
            )
        ):
            raise _invalid()


def load_bo_surrogate(
    payload: Any, *, expected_training_targets_scaled: Any | None = None
) -> BoSurrogate:
    """Restore known numeric kernels and validated arrays, without fitting.

    The optional expected targets bind the solve to an independently verified
    source snapshot. The service must additionally check source/owner hashes.
    """
    import numpy as np

    state = _validated_snapshot(payload)
    training = state.training
    n, dimensions = len(training.x_normalized), len(training.x_normalized[0])
    if (
        any(len(row) != dimensions for row in training.x_normalized)
        or len(training.targets_scaled) != n
        or len(training.group_counts) != n
        or sum(training.group_counts) != training.raw_observation_count
        or len(state.factorization.lower) != n
        or any(len(row) != n for row in state.factorization.lower)
        or len(state.factorization.alpha) != n
        or state.normalization.direction_multiplier not in {-1.0, 1.0}
    ):
        raise _invalid()
    points = np.array(training.x_normalized, dtype=float)
    # Match SciPy's fitted Cholesky layout so restore uses the same triangular
    # solve path, rather than a transposed LAPACK path with different roundoff.
    lower = np.array(state.factorization.lower, dtype=float, order="F")
    alpha = np.array(state.factorization.alpha, dtype=float)
    targets = np.array(training.targets_scaled, dtype=float)
    if (
        np.any(points < 0)
        or np.any(points > 1)
        or np.any(np.triu(lower, 1) != 0)
        or np.any(np.diag(lower) <= 0)
    ):
        raise _invalid()
    if expected_training_targets_scaled is not None:
        try:
            expected_targets = _TARGETS.validate_python(
                _target_list(expected_training_targets_scaled)
            )
        except ValidationError:
            raise _invalid() from None
        if len(expected_targets) != n or not np.array_equal(targets, expected_targets):
            raise _invalid()
    kernel, noise_policy = _restore_kernel(state, dimensions)
    _check_fit(state, dimensions + 1 + (noise_policy.noise_mode == "estimate"))
    signal, noise = split_signal_noise(kernel)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        covariance = signal(points)
        covariance[np.diag_indices(n)] += (noise + state.jitter) / np.array(training.group_counts)
        product = lower @ lower.T
        solved_targets = covariance @ alpha
        # Backward-error bounds scale with matrix size and cancellation, not Y units.
        relative = 64 * n * np.finfo(float).eps
        covariance_tolerance = relative * float(np.max(np.abs(covariance)))
        solve_tolerance = relative * (np.abs(covariance) @ np.abs(alpha) + np.abs(targets))
    if (
        not np.all(np.isfinite(product))
        or not np.all(np.isfinite(solved_targets))
        or not np.all(np.isfinite(solve_tolerance))
        or np.any(np.abs(product - covariance) > covariance_tolerance)
        or np.any(np.abs(solved_targets - targets) > solve_tolerance)
    ):
        raise _invalid()
    return BoSurrogate(
        kernel=kernel,
        x_train=points,
        lower=lower,
        alpha=alpha,
        policy=noise_policy,
        normalization_mean=state.normalization.mean,
        normalization_scale=state.normalization.scale,
        direction_multiplier=state.normalization.direction_multiplier,
        jitter=state.jitter,
        log_marginal_likelihood=state.fit.log_marginal_likelihood,
        optimizer=state.fit.optimizer.model_dump(mode="json"),
        warning_codes=tuple(state.fit.warning_codes),
        fit_elapsed_ms=state.fit.elapsed_ms,
        raw_observation_count=training.raw_observation_count,
        group_counts=tuple(training.group_counts),
        kernel_spec=BoKernelSpec(state.kernel.family) if state.kernel.explicit_family else None,
        fit_diagnostics=state.fit.diagnostics.model_dump(mode="json")
        if state.fit.diagnostics is not None
        else None,
    )


def _target_list(values: Any) -> Any:
    import numpy as np

    if isinstance(values, np.ndarray):
        if values.ndim != 1 or values.dtype.kind not in {"f", "i", "u"} or len(values) > 200:
            raise _invalid()
        return values.tolist()
    return values


def dump_bo_surrogate(model: BoSurrogate, *, training_targets_scaled: Any) -> dict[str, Any]:
    """Create a new snapshot; never infer missing targets from the stored solve."""
    import numpy as np

    for array in (model.x_train, model.lower, model.alpha):
        if not isinstance(array, np.ndarray) or array.dtype.kind not in {"f", "i", "u"}:
            raise _invalid()
    try:
        signal, noise = split_signal_noise(model.kernel)
    except ValueError:
        raise _invalid() from None
    family = kernel_family(signal.k2)
    if model.kernel_spec is not None and model.kernel_spec.kind != family:
        raise _invalid()
    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "policy": SNAPSHOT_POLICY,
        "kernel": {
            "family": family,
            "amplitude": float(signal.k1.constant_value),
            "length_scales": np.atleast_1d(signal.k2.length_scale).tolist(),
            "explicit_family": model.kernel_spec is not None,
        },
        "noise_policy": asdict(model.policy),
        "noise_variance_scaled": noise,
        "normalization": {
            "mean": model.normalization_mean,
            "scale": model.normalization_scale,
            "direction_multiplier": model.direction_multiplier,
            "ddof": 0,
        },
        "jitter": model.jitter,
        "training": {
            "x_normalized": model.x_train.tolist(),
            "targets_scaled": _target_list(training_targets_scaled),
            "group_counts": list(model.group_counts),
            "raw_observation_count": model.raw_observation_count,
        },
        "factorization": {"lower": model.lower.tolist(), "alpha": model.alpha.tolist()},
        "fit": {
            "log_marginal_likelihood": model.log_marginal_likelihood,
            "optimizer": model.optimizer,
            "warning_codes": list(model.warning_codes),
            "elapsed_ms": model.fit_elapsed_ms,
            "diagnostics": model.fit_diagnostics,
            "package_versions": model.metadata()["package_versions"],
        },
    }
    state = _validated_snapshot(payload)
    detached = state.model_dump(mode="json")
    load_bo_surrogate(detached)
    return detached
