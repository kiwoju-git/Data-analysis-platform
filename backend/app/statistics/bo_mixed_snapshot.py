"""Versioned numeric-only mixed BO state; no fitting, pickle, or executable objects."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_factor_domains import (
    BoFactorDomain,
    bo_factor_domains_from_payload,
    bo_factor_domains_to_payload,
)
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_mixed_surrogate import (
    BoMixedSurrogate,
    ParameterRole,
    mixed_bound_hits,
    mixed_parameter_descriptors,
    mixed_training_coverage,
    split_mixed_signal_noise,
    validate_mixed_coordinates,
)
from app.statistics.bo_surrogate import BoSurrogatePolicy

ERROR_CODE = "bayesian_mixed_snapshot_invalid"
SNAPSHOT_SCHEMA_VERSION = 2
SNAPSHOT_POLICY = "bo_mixed_surrogate_state_v1"
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Positive = Annotated[Number, Field(gt=0)]
Vector = Annotated[list[Number], Field(min_length=1, max_length=200)]
Parameters = Annotated[list[Number], Field(max_length=76)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


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


class _Parameter(_Strict):
    index: int = Field(ge=0, le=75)
    role: ParameterRole
    factor_index: int | None = Field(ge=0, le=9)
    factor_id: str | None = Field(max_length=128)
    level_indices: list[Annotated[int, Field(ge=0, le=31)]] = Field(max_length=2)


class _Bound(_Parameter):
    side: Literal["lower", "upper"]
    value: Positive
    bound: Positive


class _Screen(_Strict):
    log_parameters: Parameters
    negative_log_likelihood: Number


class _Selected(_Screen):
    stage: Literal["screen", "local"]
    index: int = Field(ge=0, le=9)
    evaluation: int = Field(ge=1, le=2000)


class _Start(_Strict):
    success: bool
    status: int
    termination_reason: str = Field(max_length=512)
    iterations: int = Field(ge=0, le=200)
    evaluations: int = Field(ge=1, le=2000)
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
    evaluations: int = Field(ge=1, le=2000)
    starts: list[_Start] = Field(max_length=6)


class _Diagnostics(_Strict):
    schema_version: Literal[2]
    policy: Literal["bounded_typed_factor_starts_v1"]
    deterministic_start_count: int = Field(ge=1, le=3)
    parameter_descriptors: list[_Parameter] = Field(max_length=76)
    screening: list[_Screen] = Field(max_length=10)
    selected: _Selected | None
    bound_hits: list[_Bound] = Field(max_length=76)
    global_optimum_guaranteed: Literal[False]
    final_factorization_evaluations: Literal[1]


class _Training(_Strict):
    x_encoded: list[Annotated[list[Number], Field(min_length=1, max_length=10)]] = Field(
        min_length=1, max_length=200
    )
    targets_scaled: Vector
    within_ss_scaled: Vector
    group_counts: list[Annotated[int, Field(ge=1, le=200)]] = Field(min_length=1, max_length=200)
    raw_observation_count: int = Field(ge=2, le=200)


class _Factorization(_Strict):
    lower: list[Vector] = Field(min_length=1, max_length=200)
    alpha: Vector


class _Fit(_Strict):
    log_marginal_likelihood: Number
    optimizer: _Optimizer
    diagnostics: _Diagnostics
    warning_codes: list[str] = Field(max_length=32)
    elapsed_ms: Number = Field(ge=0)
    package_versions: dict[str, str]


class _Snapshot(_Strict):
    schema_version: Literal[2]
    policy: Literal["bo_mixed_surrogate_state_v1"]
    factor_domains: dict[str, Any]
    signal_kernel: dict[str, Any]
    numeric_kernel_family: Literal["matern_5_2", "matern_3_2", "gaussian", "exponential"]
    noise_policy: _Noise
    noise_variance_scaled: Number = Field(ge=0)
    jitter: Number = Field(ge=1e-12, le=1e-3)
    normalization: _Normalization
    training: _Training
    factorization: _Factorization
    fit: _Fit


def _invalid() -> BayesianOptimizationError:
    return BayesianOptimizationError(ERROR_CODE)


def _json_tree(payload: Any) -> None:
    pending, visited = [(payload, 0)], 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if visited > 60_000 or depth > 12:
            raise _invalid()
        kind = type(value)
        if kind is dict:
            if len(value) > 128 or any(type(key) is not str or len(key) > 128 for key in value):
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
            if len(value) > 1024:
                raise _invalid()
        elif kind is int:
            if abs(value) > 2**53:
                raise _invalid()
        elif kind not in {bool, type(None)}:
            raise _invalid()


def _state(payload: Any) -> _Snapshot:
    _json_tree(payload)
    if type(payload) is not dict or type(payload.get("schema_version")) is not int:
        raise _invalid()
    try:
        state = _Snapshot.model_validate(payload)
    except ValidationError:
        raise _invalid() from None
    if (
        type(payload["normalization"]["ddof"]) is not int
        or type(payload["fit"]["diagnostics"]["schema_version"]) is not int
        or type(payload["fit"]["diagnostics"]["final_factorization_evaluations"]) is not int
        or type(payload["fit"]["diagnostics"]["global_optimum_guaranteed"]) is not bool
    ):
        raise _invalid()
    return state


def _restore_kernel(
    state: _Snapshot, domains: Sequence[BoFactorDomain]
) -> tuple[Any, BoSurrogatePolicy]:
    import numpy as np
    from sklearn.gaussian_process.kernels import WhiteKernel  # type: ignore[import-untyped]

    from app.statistics.bo_factor_kernels import (
        bo_factor_kernel_from_payload,
        validate_bo_factor_kernel_domains,
    )
    from app.statistics.bo_kernels import kernel_family

    signal = bo_factor_kernel_from_payload(state.signal_kernel)
    validate_bo_factor_kernel_domains(signal, domains)
    if (
        signal.numeric_indices
        and kernel_family(signal.numeric_kernel.k2) != state.numeric_kernel_family
    ):
        raise _invalid()
    policy = BoSurrogatePolicy(**state.noise_policy.model_dump())
    noise, tolerance = state.noise_variance_scaled, 32 * np.finfo(float).eps
    if policy.noise_mode == "near_noiseless":
        if noise != 0:
            raise _invalid()
        return signal, policy
    if noise <= 0:
        raise _invalid()
    if policy.noise_mode == "fixed":
        assert policy.fixed_noise_sd is not None
        expected = (policy.fixed_noise_sd / state.normalization.scale) ** 2
        if not math.isfinite(expected) or not math.isclose(noise, expected, rel_tol=tolerance):
            raise _invalid()
        return signal + WhiteKernel(noise, "fixed"), policy
    if (
        not policy.lower_noise_variance_scaled * (1 - tolerance)
        <= noise
        <= policy.upper_noise_variance_scaled * (1 + tolerance)
    ):
        raise _invalid()
    return signal + WhiteKernel(
        noise, (policy.lower_noise_variance_scaled, policy.upper_noise_variance_scaled)
    ), policy


def _check_fit(state: _Snapshot, kernel: Any, domains: Sequence[BoFactorDomain]) -> None:
    import numpy as np

    fit, optimizer, diagnostics = state.fit, state.fit.optimizer, state.fit.diagnostics
    descriptors = [item.payload() for item in mixed_parameter_descriptors(kernel, domains)]
    if [item.model_dump() for item in diagnostics.parameter_descriptors] != descriptors or [
        item.model_dump() for item in diagnostics.bound_hits
    ] != mixed_bound_hits(kernel, domains):
        raise _invalid()
    if (
        optimizer.evaluations > optimizer.max_evaluations
        or optimizer.ftol != 1e-12
        or set(fit.package_versions)
        != {"numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl"}
        or any(not value or len(value) > 64 for value in fit.package_versions.values())
    ):
        raise _invalid()
    if len(set(fit.warning_codes)) != len(fit.warning_codes) or any(
        not code.startswith("bayesian_")
        or not code.isascii()
        or len(code) > 128
        or not code.replace("_", "").isalnum()
        for code in fit.warning_codes
    ):
        raise _invalid()
    if optimizer.evaluations != 1 + len(diagnostics.screening) + sum(
        item.evaluations for item in optimizer.starts
    ):
        raise _invalid()
    if not optimizer.optimized:
        if (
            optimizer.starts
            or optimizer.restarts
            or diagnostics.screening
            or diagnostics.selected is not None
            or optimizer.evaluations != 1
        ):
            raise _invalid()
    elif (
        diagnostics.selected is None
        or len(optimizer.starts)
        != (diagnostics.deterministic_start_count if diagnostics.screening else 1)
        + optimizer.restarts
    ):
        raise _invalid()
    for start in optimizer.starts:
        if start.iterations > optimizer.max_iterations:
            raise _invalid()
    parameters = [item.log_parameters for item in diagnostics.screening]
    parameters += [
        vector
        for item in optimizer.starts
        for vector in (item.initial_log_parameters, item.final_log_parameters)
    ]
    if diagnostics.selected is not None:
        selected = diagnostics.selected
        parameters.append(selected.log_parameters)
        # Stored positive parameters pass through exp/log on reconstruction.
        # Match codec roundoff only; source hashes and likelihood remain checked.
        theta = kernel.theta
        theta_tolerance = 32 * np.finfo(float).eps * np.maximum(1, np.abs(theta))
        if (
            selected.evaluation >= optimizer.evaluations
            or selected.index
            >= (len(diagnostics.screening) if selected.stage == "screen" else len(optimizer.starts))
            or len(selected.log_parameters) != len(theta)
            or np.any(np.abs(np.asarray(selected.log_parameters) - theta) > theta_tolerance)
        ):
            raise _invalid()
        tolerance = 64 * np.finfo(float).eps * max(1, abs(fit.log_marginal_likelihood))
        if abs(selected.negative_log_likelihood + fit.log_marginal_likelihood) > tolerance:
            raise _invalid()
    for vector in parameters:
        if len(vector) != len(descriptors):
            raise _invalid()
        bounds = kernel.bounds
        bound_tolerance = 32 * np.finfo(float).eps * np.maximum(1, np.abs(bounds))
        if np.any(vector < bounds[:, 0] - bound_tolerance[:, 0]) or np.any(
            vector > bounds[:, 1] + bound_tolerance[:, 1]
        ):
            raise _invalid()


def load_bo_mixed_surrogate(
    payload: Any,
    *,
    expected_factor_domains: Sequence[BoFactorDomain] | None = None,
    expected_training_targets_scaled: Any | None = None,
    expected_within_ss_scaled: Any | None = None,
) -> BoMixedSurrogate:
    """Validate known state and likelihood receipts, without optimizing or refitting.

    Source/history/owner hashes remain the service's responsibility. Domain
    comparison binds exact level order as well as labels; source-derived targets
    and within-SS can be independently bound without changing this artifact.
    """
    import numpy as np

    from app.statistics.bo_factor_kernels import _numeric_array

    state = _state(payload)
    try:
        domains = bo_factor_domains_from_payload(state.factor_domains)
        if (
            expected_factor_domains is not None
            and bo_factor_domains_to_payload(expected_factor_domains) != state.factor_domains
        ):
            raise _invalid()
        kernel, policy = _restore_kernel(state, domains)
        points = validate_mixed_coordinates(state.training.x_encoded, domains, maximum=200)
        _check_fit(state, kernel, domains)
    except (ValueError, OverflowError):
        raise _invalid() from None
    n = len(points)
    training = state.training
    if (
        len(training.targets_scaled) != n
        or len(training.within_ss_scaled) != n
        or len(training.group_counts) != n
        or sum(training.group_counts) != training.raw_observation_count
        or len(state.factorization.lower) != n
        or any(len(row) != n for row in state.factorization.lower)
        or len(state.factorization.alpha) != n
        or state.normalization.direction_multiplier not in {-1, 1}
    ):
        raise _invalid()
    targets, within_ss = np.array(training.targets_scaled), np.array(training.within_ss_scaled)
    counts = np.array(training.group_counts)
    lower, alpha = np.array(state.factorization.lower), np.array(state.factorization.alpha)
    if (
        np.any(within_ss < 0)
        or np.any(within_ss[counts == 1] != 0)
        or np.any(np.triu(lower, 1) != 0)
        or np.any(np.diag(lower) <= 0)
    ):
        raise _invalid()
    # Distinct declared process/condition groups can share coordinates. Their
    # mean observations retain separate diagonal variance/count contributions;
    # the planning reader binds each group back to immutable source membership.
    for actual, expected in (
        (targets, expected_training_targets_scaled),
        (within_ss, expected_within_ss_scaled),
    ):
        if expected is not None:
            try:
                expected_array = _numeric_array(expected)
            except ValueError:
                raise _invalid() from None
            if expected_array.shape != actual.shape or not np.array_equal(actual, expected_array):
                raise _invalid()
    signal, noise = split_mixed_signal_noise(kernel)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        covariance = signal(points)
        variance = noise + state.jitter
        covariance[np.diag_indices(n)] += variance / counts
        product = lower @ lower.T
        solved = covariance @ alpha
        relative = 64 * n * np.finfo(float).eps
        covariance_tolerance = relative * np.max(np.abs(covariance))
        solve_tolerance = relative * (np.abs(covariance) @ np.abs(alpha) + np.abs(targets))
        correction_terms = (
            (counts - 1) * math.log(2 * math.pi * variance) + within_ss / variance + np.log(counts)
        )
        likelihood_terms = np.array(
            [
                -0.5 * targets @ alpha,
                -np.log(np.diag(lower)).sum(),
                -0.5 * n * math.log(2 * math.pi),
                -0.5 * correction_terms.sum(),
            ]
        )
        lml = float(likelihood_terms.sum())
        lml_tolerance = relative * max(1, float(np.abs(likelihood_terms).sum()))
    if (
        not np.all(np.isfinite(product))
        or not np.all(np.isfinite(solved))
        or not np.all(np.isfinite(solve_tolerance))
        or np.any(np.abs(product - covariance) > covariance_tolerance)
        or np.any(np.abs(solved - targets) > solve_tolerance)
        or not math.isfinite(lml)
        or abs(lml - state.fit.log_marginal_likelihood) > lml_tolerance
    ):
        raise _invalid()
    coverage = mixed_training_coverage(points, domains, training.group_counts)
    if (
        any(item["unobserved_level_indices"] for item in coverage)
        and "bayesian_category_unobserved_level_prior_dependent" not in state.fit.warning_codes
    ):
        raise _invalid()
    if (
        any(item["observed_level_count"] == 1 for item in coverage)
        and "bayesian_category_correlation_unidentified" not in state.fit.warning_codes
    ):
        raise _invalid()
    return BoMixedSurrogate(
        kernel=kernel,
        x_train=points,
        lower=lower,
        alpha=alpha,
        policy=policy,
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
        kernel_spec=BoKernelSpec(state.numeric_kernel_family),
        fit_diagnostics=state.fit.diagnostics.model_dump(mode="json"),
        factor_domains=domains,
        training_targets_scaled=targets,
        training_within_ss_scaled=within_ss,
    )


def dump_bo_mixed_surrogate(model: BoMixedSurrogate) -> dict[str, Any]:
    import numpy as np

    from app.statistics.bo_factor_kernels import bo_factor_kernel_to_payload

    if type(model) is not BoMixedSurrogate or model.kernel_spec is None:
        raise _invalid()
    arrays = (
        model.x_train,
        model.lower,
        model.alpha,
        model.training_targets_scaled,
        model.training_within_ss_scaled,
    )
    if any(not isinstance(value, np.ndarray) or value.dtype.kind not in "iuf" for value in arrays):
        raise _invalid()
    signal, noise = split_mixed_signal_noise(model.kernel)
    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "policy": SNAPSHOT_POLICY,
        "factor_domains": bo_factor_domains_to_payload(model.factor_domains),
        "signal_kernel": bo_factor_kernel_to_payload(signal),
        "numeric_kernel_family": model.kernel_spec.kind,
        "noise_policy": asdict(model.policy),
        "noise_variance_scaled": noise,
        "jitter": model.jitter,
        "normalization": {
            "mean": model.normalization_mean,
            "scale": model.normalization_scale,
            "direction_multiplier": model.direction_multiplier,
            "ddof": 0,
        },
        "training": {
            "x_encoded": model.x_train.tolist(),
            "targets_scaled": model.training_targets_scaled.tolist(),
            "within_ss_scaled": model.training_within_ss_scaled.tolist(),
            "group_counts": list(model.group_counts),
            "raw_observation_count": model.raw_observation_count,
        },
        "factorization": {"lower": model.lower.tolist(), "alpha": model.alpha.tolist()},
        "fit": {
            "log_marginal_likelihood": model.log_marginal_likelihood,
            "optimizer": model.optimizer,
            "diagnostics": model.fit_diagnostics,
            "warning_codes": list(model.warning_codes),
            "elapsed_ms": model.fit_elapsed_ms,
            "package_versions": model.metadata()["package_versions"],
        },
    }
    detached = _state(payload).model_dump(mode="json")
    load_bo_mixed_surrogate(detached)
    return detached
