"""Verify stored fit-policy evidence without evaluating a likelihood or refitting."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_fit_policy import parameter_bound_hits, screened_starts
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_surrogate import BoSurrogatePolicy, _kernel


def _same_regenerated_numbers(actual: Any, expected: Any, *, log_space: bool = True) -> bool:
    left, right = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if left.shape != right.shape or not np.all(np.isfinite(left)):
        return False
    # Recreated libm/log-space arithmetic may differ across supported OS builds.
    # Stored receipt-to-selection comparisons below remain exact.
    scale = np.maximum(1.0 if log_space else np.finfo(float).tiny, np.abs(right))
    return bool(np.all(np.abs(left - right) <= 16 * np.finfo(float).eps * scale))


def validate_fit_evidence(model: Any, fit_policy: Any, search: Any, specification: Any) -> int:
    def require(condition: bool) -> None:
        if not condition:
            raise BayesianOptimizationError("bayesian_desirability_result_invalid")

    diag = model.fit_diagnostics
    require(
        diag.policy == fit_policy.kind
        and diag.deterministic_start_count == fit_policy.deterministic_start_count
    )
    kernel = _kernel(
        len(model.factor_ids),
        BoSurrogatePolicy(**specification.surrogate.model_dump()),
        model.normalization.scale,
        kernel_spec=BoKernelSpec(specification.kernel.kind),
    )
    starts = screened_starts(kernel.theta, kernel.bounds, len(model.factor_ids))
    require(_same_regenerated_numbers([s.log_parameters for s in diag.screening], starts))
    indices = sorted(
        range(len(starts)), key=lambda i: (diag.screening[i].negative_log_likelihood, i)
    )[: fit_policy.deterministic_start_count]
    require(diag.refined_screen_indices == indices)
    rng = np.random.default_rng(search.random_seed)
    local = [starts[i] for i in indices] + [
        rng.uniform(kernel.bounds[:, 0], kernel.bounds[:, 1])
        for _ in range(search.hyperparameter_restart_count)
    ]
    traces = model.optimizer.starts
    require(len(traces) == len(local) == len(diag.start_initial_negative_log_likelihoods))
    require(len(traces) == len(diag.start_best_evaluations))
    for trace, best, initial_value in zip(
        traces,
        diag.start_best_evaluations,
        diag.start_initial_negative_log_likelihoods,
        strict=True,
    ):
        require(best.evaluation_index < trace.evaluations)
        require(
            best.negative_log_likelihood
            <= min(initial_value, trace.negative_log_likelihood) + 1e-10
        )
    require(_same_regenerated_numbers([t.initial_log_parameters for t in traces], local))
    require(
        diag.start_initial_negative_log_likelihoods[: len(indices)]
        == [diag.screening[i].negative_log_likelihood for i in indices]
    )
    selected = diag.selected
    require(len(selected.log_parameters) == len(kernel.theta))
    for values in [
        selected.log_parameters,
        *[t.final_log_parameters for t in traces],
        *[b.log_parameters for b in diag.start_best_evaluations],
    ]:
        require(len(values) == len(kernel.theta))
        require(
            all(
                low - 1e-12 <= value <= high + 1e-12
                for value, (low, high) in zip(values, kernel.bounds, strict=True)
            )
        )
    nll = -model.log_marginal_likelihood
    require(math.isclose(selected.negative_log_likelihood, nll, rel_tol=2e-11, abs_tol=1e-12))
    require(
        all(
            nll <= value + 1e-10
            for value in [
                *[s.negative_log_likelihood for s in diag.screening],
                *diag.start_initial_negative_log_likelihoods,
                *[t.negative_log_likelihood for t in traces],
            ]
        )
    )
    if selected.stage == "screen":
        if selected.screen_index is None or selected.screen_index >= len(starts):
            raise BayesianOptimizationError("bayesian_desirability_result_invalid")
        require(selected.log_parameters == diag.screening[selected.screen_index].log_parameters)
        require(
            selected.negative_log_likelihood
            == diag.screening[selected.screen_index].negative_log_likelihood
        )
    else:
        if selected.start_index is None or selected.start_index >= len(traces):
            raise BayesianOptimizationError("bayesian_desirability_result_invalid")
        receipt = diag.start_best_evaluations[selected.start_index]
        require(selected.log_parameters == receipt.log_parameters)
        require(selected.negative_log_likelihood == receipt.negative_log_likelihood)
    require(all(nll <= b.negative_log_likelihood + 1e-10 for b in diag.start_best_evaluations))
    actual = [model.signal_kernel.amplitude, *model.signal_kernel.length_scales]
    if model.noise.mode == "estimate":
        actual.append(model.noise.fitted_variance_scaled)
    require(len(actual) == len(selected.log_parameters))
    require(
        all(
            math.isclose(math.exp(log_value), value, rel_tol=2e-12)
            for log_value, value in zip(selected.log_parameters, actual, strict=True)
        )
    )
    expected_hits = parameter_bound_hits(
        np.array(selected.log_parameters), kernel.bounds, len(model.factor_ids)
    )
    require(len(diag.bound_hits) == len(expected_hits))
    for actual_hit, expected_hit in zip(diag.bound_hits, expected_hits, strict=True):
        require(
            all(
                getattr(actual_hit, key) == expected_hit[key]
                for key in ("parameter", "factor_index", "side")
            )
        )
        require(
            _same_regenerated_numbers(
                [actual_hit.value, actual_hit.bound],
                [expected_hit["value"], expected_hit["bound"]],
                log_space=False,
            )
        )
    return len(starts)
