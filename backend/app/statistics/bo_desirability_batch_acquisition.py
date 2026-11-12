"""Internal conditional MC/Beta marginal planning, not a public batch workflow.

Independent response GPs retain spatial joint latent covariance. Conditional
payoffs use the existing Beta moment approximation; their scores are not an
exact joint EI or an implementation of JMP's named augmentation strategies.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_beta_policy import BETA_NUMERICAL_POLICY
from app.statistics.bo_desirability import (
    DesirabilityGoal,
    composite_desirability,
    finite_number,
    independent_desirability_moments,
    normalized_importance,
)
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_desirability_posterior import (
    DesirabilityResponsePosterior,
    SurrogateDesirability,
    evaluate_surrogate_desirability,
    raw_posterior_standard_deviation,
)
from app.statistics.bo_factor_domains import BoFactorDomain
from app.statistics.bo_surrogate import BoSurrogate

POLICY_VERSION = "conditional_mc_desirability_beta_marginal_v1"
_INPUT_ERROR = "bayesian_desirability_batch_input_invalid"
_COVARIANCE_ERROR = "bayesian_surrogate_covariance_invalid"
_PRECISION_ERROR = "bayesian_desirability_covariance_precision_unsupported"


def _integer(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _numeric_array(value: Any) -> Any:
    import numpy as np

    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = raw.astype(float, copy=False)
        if not np.all(np.isfinite(result)):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise BayesianOptimizationError(_COVARIANCE_ERROR) from exc
    return result


def _raw_variance(sd: float) -> float:
    value = finite_number(sd)
    result = value * value
    if not math.isfinite(result) or (value != 0 and result == 0):
        raise BayesianOptimizationError("bayesian_desirability_raw_variance_precision_unsupported")
    return result


def _rescale_variance(variance: float, scale: float) -> float:
    # Multiplication order avoids squaring a large scale before a tiny variance.
    result = variance * scale * scale
    if not math.isfinite(result) or (variance != 0 and result == 0):
        raise BayesianOptimizationError("bayesian_desirability_raw_variance_precision_unsupported")
    return result


def batch_response_seed(root_seed: int, step: int, response_id: str) -> int:
    if (
        not _integer(root_seed, 0, 2**32 - 1)
        or not _integer(step, 0, 7)
        or not isinstance(response_id, str)
        or not response_id
    ):
        raise BayesianOptimizationError(_INPUT_ERROR)
    # The full response identity is the final field, never a display label/index.
    material = f"{POLICY_VERSION}\0{root_seed}\0latent_selected_responses\0{step}\0{response_id}"
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def _coordinates(value: Any, width: int, maximum: int, *, empty: bool = False) -> Any:
    import numpy as np

    try:
        if not isinstance(value, np.ndarray):
            for scalar in np.asarray(value, dtype=object).flat:
                finite_number(scalar)
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = raw.astype(float, copy=True)
        if (
            result.ndim != 2
            or result.shape[1] != width
            or not (0 if empty else 1) <= len(result) <= maximum
            or not np.all(np.isfinite(result))
            or np.any((result < 0) | (result > 1))
        ):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise BayesianOptimizationError(_INPUT_ERROR) from exc
    return result


@dataclass(frozen=True)
class DesirabilityBatchScores:
    scores: Any
    mc_standard_error: Any
    base_posteriors: tuple[SurrogateDesirability, ...]
    conditional_variance_raw: dict[str, Any]
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class _Condition:
    whitener: Any
    draws: Any
    projector: Any
    rank: int
    negative_eigenvalue_adjustment_scaled: float
    covariance_scale: float


def _condition(
    covariance: Any, model_scale: float, count: int, seed: int, samples: int
) -> tuple[Any, _Condition]:
    import numpy as np
    from scipy.linalg import cholesky, solve_triangular  # type: ignore[import-untyped]

    cov = _numeric_array(covariance)
    if cov.shape != (count, count) or not np.all(np.isfinite(cov)):
        raise BayesianOptimizationError(_COVARIANCE_ERROR)
    scale = max(float(np.abs(cov).max()), model_scale, np.finfo(float).tiny)
    tolerance = 64 * np.finfo(float).eps * scale * count
    if float(np.abs(cov - cov.T).max()) > tolerance:
        raise BayesianOptimizationError(_COVARIANCE_ERROR)
    cov = cov * 0.5 + cov.T * 0.5
    try:
        eigenvalues, vectors = np.linalg.eigh(cov)
    except np.linalg.LinAlgError as exc:
        raise BayesianOptimizationError(_COVARIANCE_ERROR) from exc
    if not np.all(np.isfinite(eigenvalues)):
        raise BayesianOptimizationError(_COVARIANCE_ERROR)
    minimum = float(eigenvalues.min())
    if minimum < -tolerance:
        raise BayesianOptimizationError(_COVARIANCE_ERROR)
    adjustment = max(0.0, -minimum)
    if minimum > tolerance:
        try:
            root = cholesky(cov, lower=True, check_finite=False)
        except np.linalg.LinAlgError as exc:
            raise BayesianOptimizationError(_COVARIANCE_ERROR) from exc
        whitener = solve_triangular(root.T, np.eye(count), lower=False, check_finite=False)
        projector = np.eye(count)
        rank = count
    else:
        # Exact deterministic directions are supported without invented noise.
        # Positive eigenvalues below numerical resolution are not silently lost.
        if np.any((eigenvalues > 0) & (eigenvalues <= tolerance)):
            raise BayesianOptimizationError(_PRECISION_ERROR)
        positive = eigenvalues > 0
        active = vectors[:, positive]
        roots = np.sqrt(eigenvalues[positive])
        root = active * roots
        whitener = active / roots
        projector = active @ active.T
        rank = int(positive.sum())
    draws = np.random.default_rng(seed).standard_normal((samples, rank))
    if not np.all(np.isfinite(whitener)):
        raise BayesianOptimizationError(_PRECISION_ERROR)
    return draws @ root.T, _Condition(whitener, draws, projector, rank, adjustment, scale)


class DesirabilityBatchAcquisition:
    """Read-only scorer for fixed models and an ordered selection of 0..7 points.

    It neither searches nor fits/serializes models, writes observations or creates
    pending trials. Callers must retain fixed source models for its lifetime.
    """

    def __init__(
        self,
        models: Mapping[str, BoSurrogate],
        goals: Sequence[DesirabilityGoal],
        incumbent: float,
        selected_x: Any = None,
        *,
        xi: float = 0.0,
        root_seed: int,
        sample_count: int = 64,
        chunk_size: int = 8,
        max_moment_evaluations: int = 8192,
        check_budget: Callable[[], None] | None = None,
        consume_moments: Callable[[int], None] | None = None,
        factor_domains: Sequence[BoFactorDomain] | None = None,
    ) -> None:
        import numpy as np

        normalized_importance(goals)
        self.goals, self.models = tuple(goals), dict(models)
        self.factor_domains = None if factor_domains is None else tuple(factor_domains)
        if self.factor_domains is not None:
            from app.statistics.bo_factor_domains import validate_bo_factor_domains
            from app.statistics.bo_mixed_surrogate import BoMixedSurrogate

            validate_bo_factor_domains(self.factor_domains)
            if any(
                not isinstance(model, BoMixedSurrogate)
                or model.factor_domains != self.factor_domains
                for model in self.models.values()
            ):
                raise BayesianOptimizationError("bayesian_desirability_model_contract_invalid")
        if set(self.models) != {g.response_id for g in self.goals}:
            raise BayesianOptimizationError("bayesian_desirability_response_mapping_invalid")
        self.incumbent, self.xi = finite_number(incumbent), finite_number(xi)
        if (
            not 0 <= self.incumbent <= 1
            or self.xi < 0
            or not math.isfinite(self.incumbent + self.xi)
            or not _integer(sample_count, 16, 256)
            or not _integer(chunk_size, 1, 128)
            or not _integer(max_moment_evaluations, 1, 65536)
            or (check_budget is not None and not callable(check_budget))
            or (consume_moments is not None and not callable(consume_moments))
        ):
            raise BayesianOptimizationError(_INPUT_ERROR)
        self.sample_count, self.chunk_size = sample_count, chunk_size
        self.root_seed = root_seed
        self.max_moment_evaluations = max_moment_evaluations
        self._check_budget = check_budget
        self._consume_moments = consume_moments
        self.moment_evaluations = self.integration_evaluations = 0
        self.candidate_evaluations = 0
        self.exact_selected_evaluations = 0
        self.width = next(iter(self.models.values())).x_train.shape[1]
        if not 1 <= self.width <= 10:
            raise BayesianOptimizationError(_INPUT_ERROR)
        for model in self.models.values():
            if (
                model.direction_multiplier != 1
                or model.x_train.shape[1] != self.width
                or finite_number(model.normalization_scale) <= 0
                or finite_number(model.covariance_roundoff_scale) < 0
            ):
                raise BayesianOptimizationError("bayesian_desirability_model_contract_invalid")
            finite_number(model.normalization_mean)
        self._selected_x = self._coordinate_matrix(
            np.empty((0, self.width)) if selected_x is None else selected_x,
            self.width,
            7,
            empty=True,
        )
        self.selected_count = len(self._selected_x)
        if len(set(map(tuple, self._selected_x.tolist()))) != self.selected_count:
            raise BayesianOptimizationError(_INPUT_ERROR)
        self._conditions: dict[str, _Condition] = {}
        self._selected_samples_raw: dict[str, Any] = {}
        self._selected_proofs: dict[str, Any] = {}
        self._seeds = {
            g.response_id: batch_response_seed(root_seed, self.selected_count, g.response_id)
            for g in self.goals
        }
        self._conditional_adjustments = {g.response_id: 0.0 for g in self.goals}
        self._thresholds = np.empty(0)
        self._check()
        if self.selected_count == 0:
            return
        for goal in self.goals:
            model = self.models[goal.response_id]
            posterior = model.predict(self._selected_x, joint=True)
            mean = _numeric_array(posterior.mean_scaled)
            if mean.shape != (self.selected_count,) or not np.all(np.isfinite(mean)):
                raise BayesianOptimizationError(_COVARIANCE_ERROR)
            centered, state = _condition(
                posterior.latent_covariance_scaled,
                model.covariance_roundoff_scale,
                self.selected_count,
                self._seeds[goal.response_id],
                sample_count,
            )
            self._selected_proofs[goal.response_id] = {
                "selected_mean_scaled": mean.tolist(),
                "selected_covariance_scaled": _numeric_array(
                    posterior.latent_covariance_scaled
                ).tolist(),
            }
            raw = (mean + centered) * model.normalization_scale + model.normalization_mean
            if not np.all(np.isfinite(raw)):
                raise BayesianOptimizationError(_COVARIANCE_ERROR)
            self._selected_samples_raw[goal.response_id] = raw
            self._conditions[goal.response_id] = state
            self._check()
        sampled = np.array(
            [
                [
                    composite_desirability(
                        {
                            g.response_id: self._selected_samples_raw[g.response_id][m, j]
                            for g in self.goals
                        },
                        self.goals,
                    )
                    for j in range(self.selected_count)
                ]
                for m in range(sample_count)
            ]
        )
        self._thresholds = np.maximum(self.incumbent + self.xi, sampled.max(axis=1))
        self._check()

    @property
    def selected_samples_raw(self) -> dict[str, Any]:
        return {key: value.copy() for key, value in self._selected_samples_raw.items()}

    @property
    def thresholds(self) -> Any:
        return self._thresholds.copy()

    def _check(self) -> None:
        if self._check_budget is not None:
            self._check_budget()

    def _coordinate_matrix(
        self, values: Any, width: int, maximum: int, *, empty: bool = False
    ) -> Any:
        if self.factor_domains is None:
            return _coordinates(values, width, maximum, empty=empty)
        from app.statistics.bo_mixed_surrogate import validate_mixed_coordinates

        matrix = _numeric_array(values)
        if empty and matrix.shape == (0, width):
            return matrix
        return validate_mixed_coordinates(matrix, self.factor_domains, maximum=maximum)

    def _moments(self, posteriors: Mapping[str, tuple[float, float]]) -> Any:
        self._check()
        if self.moment_evaluations >= self.max_moment_evaluations:
            raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
        if self._consume_moments is not None:
            self._consume_moments(1)
        self.moment_evaluations += 1
        value = independent_desirability_moments(posteriors, self.goals)
        self.integration_evaluations += value.integration_evaluations
        self._check()
        return value

    def score(self, candidates: Any, *, include_details: bool = False) -> DesirabilityBatchScores:
        import numpy as np

        points = self._coordinate_matrix(candidates, self.width, 4096)
        if type(include_details) is not bool or (include_details and len(points) != 1):
            raise BayesianOptimizationError(_INPUT_ERROR)
        exact_selected = sum(
            bool(np.any(np.all(self._selected_x == point, axis=1))) for point in points
        )
        required = len(points) + (len(points) - exact_selected) * (
            self.sample_count if self.selected_count else 0
        )
        if required > self.max_moment_evaluations - self.moment_evaluations:
            raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
        if not self.selected_count:
            return self._score_first(points)
        details: dict[str, Any] = {
            "response_proofs": {},
            "thresholds": self._thresholds.tolist(),
            "sample_moments": [],
        }
        all_scores, all_errors, base_results = [], [], []
        conditional: dict[str, list[float]] = {g.response_id: [] for g in self.goals}
        for start in range(0, len(points), self.chunk_size):
            self._check()
            chunk = points[start : start + self.chunk_size]
            base_by_response, planning = {}, {}
            for goal in self.goals:
                key, model = goal.response_id, self.models[goal.response_id]
                posterior = model.predict(chunk)
                mu, var, pred = [
                    _numeric_array(v)
                    for v in (
                        posterior.mean_scaled,
                        posterior.latent_variance_scaled,
                        posterior.predictive_variance_scaled,
                    )
                ]
                if (
                    any(
                        v.shape != (len(chunk),) or not np.all(np.isfinite(v))
                        for v in (mu, var, pred)
                    )
                    or np.any(var < 0)
                    or np.any(pred < var)
                ):
                    raise BayesianOptimizationError(_COVARIANCE_ERROR)
                scale, center = model.normalization_scale, model.normalization_mean
                base_by_response[key] = (
                    mu * scale + center,
                    np.array([raw_posterior_standard_deviation(v, scale) for v in var]),
                    np.array([raw_posterior_standard_deviation(v, scale) for v in pred]),
                )
                if not all(np.all(np.isfinite(value)) for value in base_by_response[key]):
                    raise BayesianOptimizationError(_COVARIANCE_ERROR)
                cond_mu, cond_var = mu[:, None], var.copy()
                if self.selected_count:
                    state = self._conditions[key]
                    cross = _numeric_array(model.latent_cross_covariance(chunk, self._selected_x))
                    if cross.shape != (len(chunk), self.selected_count) or not np.all(
                        np.isfinite(cross)
                    ):
                        raise BayesianOptimizationError(_COVARIANCE_ERROR)
                    if include_details:
                        details["response_proofs"][key] = {
                            **deepcopy(self._selected_proofs[key]),
                            "candidate_mean_scaled": float(mu[0]),
                            "candidate_variance_scaled": float(var[0]),
                            "cross_covariance_scaled": cross[0].tolist(),
                        }
                    null_error = cross - cross @ state.projector
                    tolerance = (
                        64
                        * np.finfo(float).eps
                        * max(state.covariance_scale, float(np.abs(cross).max()))
                        * self.selected_count
                    )
                    if np.any(np.abs(null_error) > tolerance):
                        raise BayesianOptimizationError(_COVARIANCE_ERROR)
                    whitened = cross @ state.whitener
                    reduction = np.einsum("ij,ij->i", whitened, whitened)
                    cond_var = var - reduction
                    tolerance_v = (
                        64
                        * np.finfo(float).eps
                        * np.maximum(np.maximum(var, reduction), state.covariance_scale)
                        * self.selected_count
                    )
                    if np.any(cond_var < -tolerance_v) or not np.all(np.isfinite(cond_var)):
                        raise BayesianOptimizationError(_COVARIANCE_ERROR)
                    self._conditional_adjustments[key] = max(
                        self._conditional_adjustments[key], float(np.maximum(-cond_var, 0).max())
                    )
                    cond_var = np.maximum(cond_var, 0.0)
                    cond_mu = mu[:, None] + whitened @ state.draws.T
                raw_mu = cond_mu * scale + center
                raw_sd = np.array([raw_posterior_standard_deviation(v, scale) for v in cond_var])
                for i, point in enumerate(chunk):
                    matches = np.flatnonzero(np.all(self._selected_x == point, axis=1))
                    if len(matches):
                        # Conditioning at an exactly sampled coordinate is known,
                        # not a tiny-variance Beta approximation.
                        raw_mu[i] = self._selected_samples_raw[key][:, int(matches[0])]
                        raw_sd[i] = 0.0
                if not np.all(np.isfinite(raw_mu)) or not np.all(np.isfinite(raw_sd)):
                    raise BayesianOptimizationError(_COVARIANCE_ERROR)
                planning[key] = (raw_mu, raw_sd)
                conditional[key].extend(_raw_variance(float(sd)) for sd in raw_sd)
                self._check()
            for i in range(len(chunk)):
                responses = tuple(
                    DesirabilityResponsePosterior(
                        g.response_id, *[float(v[i]) for v in base_by_response[g.response_id]]
                    )
                    for g in self.goals
                )
                base = self._moments(
                    {
                        r.response_id: (r.mean_raw, r.latent_standard_deviation_raw)
                        for r in responses
                    }
                )
                base_results.append(SurrogateDesirability(base, responses))
                if np.any(np.all(self._selected_x == chunk[i], axis=1)):
                    # The same random variable cannot improve on a set already
                    # containing it, regardless of floating-point payoff order.
                    all_scores.append(0.0)
                    all_errors.append(0.0)
                    self.exact_selected_evaluations += 1
                else:
                    sampled_scores = []
                    for m, threshold in enumerate(self._thresholds):
                        moment = self._moments(
                            {
                                key: (float(mu[i, m]), float(sd[i]))
                                for key, (mu, sd) in planning.items()
                            }
                        )
                        if include_details:
                            details["sample_moments"].append(asdict(moment))
                        # The helper bounds its incumbent to[0,1]. Split a threshold
                        # above1 without applying the requested xi a second time.
                        sampled_scores.append(
                            beta_expected_improvement(
                                moment.mean,
                                moment.variance,
                                min(float(threshold), 1.0),
                                xi=max(float(threshold) - 1.0, 0.0),
                            ).value
                        )
                    all_scores.append(float(np.mean(sampled_scores)))
                    all_errors.append(
                        float(np.std(sampled_scores, ddof=1) / math.sqrt(self.sample_count))
                    )
                self.candidate_evaluations += 1
        self._check()
        return DesirabilityBatchScores(
            np.array(all_scores),
            np.array(all_errors),
            tuple(base_results),
            {key: np.array(values) for key, values in conditional.items()},
            details if include_details else None,
        )

    def _score_first(self, points: Any) -> DesirabilityBatchScores:
        import numpy as np

        base, scores = [], []
        variance: dict[str, list[float]] = {g.response_id: [] for g in self.goals}
        for point in points:
            self._check()
            if self._consume_moments is not None:
                self._consume_moments(1)
            self.moment_evaluations += 1
            if self.factor_domains is None:
                value = evaluate_surrogate_desirability(self.models, self.goals, point)
            else:
                from app.statistics.bo_mixed_planning import evaluate_mixed_surrogate_desirability

                value = evaluate_mixed_surrogate_desirability(self.models, self.goals, point)
            self.integration_evaluations += value.moments.integration_evaluations
            self._check()
            scores.append(
                beta_expected_improvement(
                    value.moments.mean, value.moments.variance, self.incumbent, xi=self.xi
                ).value
            )
            base.append(value)
            for response in value.responses:
                finite_number(response.mean_raw)
                finite_number(response.predictive_standard_deviation_raw)
                variance[response.response_id].append(
                    _raw_variance(response.latent_standard_deviation_raw)
                )
            self.candidate_evaluations += 1
        self._check()
        return DesirabilityBatchScores(
            np.array(scores),
            np.zeros(len(points)),
            tuple(base),
            {key: np.array(values) for key, values in variance.items()},
        )

    def metadata(self) -> dict[str, Any]:
        result = {
            "policy_version": POLICY_VERSION,
            "numerical_policy": BETA_NUMERICAL_POLICY,
            "root_seed": self.root_seed,
            "response_sample_seeds": {key: str(value) for key, value in self._seeds.items()},
            "batch_step": self.selected_count,
            "requested_sample_count": self.sample_count,
            "effective_sample_count": self.sample_count if self.selected_count else 0,
            "conditioned_on_selected_ranks": list(range(1, self.selected_count + 1)),
            "baseline_threshold": self.incumbent + self.xi,
            "representative_prediction_source": "completed_observations_base_posterior",
            "common_random_numbers": True,
            "response_independence_assumption": True,
            "score_is_exact_joint_ei": False,
            "mc_standard_error_excludes_beta_approximation_error": True,
            "covariance_adjustment_is_measurement_noise": False,
            "selected_covariance": {
                key: {
                    "rank": state.rank,
                    "negative_eigenvalue_adjustment_scaled": (
                        state.negative_eigenvalue_adjustment_scaled
                    ),
                    "negative_eigenvalue_adjustment_raw": _rescale_variance(
                        state.negative_eigenvalue_adjustment_scaled,
                        self.models[key].normalization_scale,
                    ),
                    "roundoff_scale": state.covariance_scale,
                    "conditional_variance_adjustment_max_scaled": self._conditional_adjustments[
                        key
                    ],
                }
                for key, state in self._conditions.items()
            },
            "moment_evaluation_unit": "joint_response_desirability_moments",
            "max_moment_evaluations": self.max_moment_evaluations,
            "moment_evaluations": self.moment_evaluations,
            "response_moment_evaluations": self.moment_evaluations * len(self.goals),
            "integration_evaluations": self.integration_evaluations,
            "candidate_evaluations": self.candidate_evaluations,
            "exact_selected_evaluations": self.exact_selected_evaluations,
        }
        if self.factor_domains is not None:
            result["coordinate_encoding"] = "numeric_normalized_category_index_v1"
        return result
