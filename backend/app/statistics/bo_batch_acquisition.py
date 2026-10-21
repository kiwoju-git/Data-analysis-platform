"""Bounded conditional MC marginal improvement from a fixed latent posterior."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_acquisition import (
    BoAcquisitionContext,
    acquisition_scores,
    expected_improvement,
    expected_target_improvement,
)

POLICY_VERSION = "greedy_mc_joint_latent_improvement_v2"


def _integer(value: Any, minimum: int, maximum: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum


def batch_sample_seed(root_seed: int, step: int) -> int:
    if not _integer(root_seed, 0, 2**32 - 1) or not _integer(step, 0, 7):
        raise BayesianOptimizationError("bayesian_batch_acquisition_input_invalid")
    material = f"{POLICY_VERSION}\0{root_seed}\0latent_selected_samples\0{step}".encode("ascii")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _coordinates(value: Any, width: int, *, allow_empty: bool = False) -> Any:
    import numpy as np

    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = raw.astype(float, copy=False)
        if result.ndim != 2 or result.shape[1] != width or not np.all(np.isfinite(result)):
            raise ValueError
        if not allow_empty and len(result) == 0:
            raise ValueError
        return result
    except (TypeError, ValueError, OverflowError) as exc:
        raise BayesianOptimizationError("bayesian_batch_acquisition_input_invalid") from exc


@dataclass(frozen=True)
class BoBatchScores:
    scores_scaled: Any
    mean_scaled: Any
    latent_variance_scaled: Any
    predictive_variance_scaled: Any
    conditional_variance_scaled: Any
    conditional_variance_adjustment_max_scaled: float = 0.0


class BoBatchAcquisition:
    def __init__(
        self,
        model: Any,
        context: BoAcquisitionContext,
        selected_x: Any = None,
        *,
        sample_count: int = 64,
        root_seed: int,
        step: int,
        chunk_size: int = 128,
    ) -> None:
        import numpy as np
        from scipy.linalg import cho_solve, cholesky  # type: ignore[import-untyped]

        if not _integer(sample_count, 16, 256) or not _integer(chunk_size, 1, 256):
            raise BayesianOptimizationError("bayesian_batch_acquisition_input_invalid")
        self.model, self.context = model, context
        self.sample_count, self.chunk_size = sample_count, chunk_size
        self.root_seed, self.step = root_seed, step
        self.sample_seed = batch_sample_seed(root_seed, step)
        self.width = model.x_train.shape[1]
        self.covariance_roundoff_scale = float(getattr(model, "covariance_roundoff_scale", 0.0))
        if not np.isfinite(self.covariance_roundoff_scale) or self.covariance_roundoff_scale < 0:
            raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
        self.selected_x = _coordinates(
            np.empty((0, self.width)) if selected_x is None else selected_x,
            self.width,
            allow_empty=True,
        ).copy()
        self.selected_count = len(self.selected_x)
        if self.selected_count > 7 or step != self.selected_count:
            raise BayesianOptimizationError("bayesian_batch_acquisition_input_invalid")
        self.selected_covariance_adjustment = 0.0
        self.lower = self.condition_weights = self.selected_samples = None
        if self.selected_count == 0:
            return
        posterior = model.predict(self.selected_x, joint=True)
        mean = np.asarray(posterior.mean_scaled, dtype=float)
        covariance = np.asarray(posterior.latent_covariance_scaled, dtype=float)
        if (
            mean.shape != (self.selected_count,)
            or covariance.shape != (self.selected_count, self.selected_count)
            or not np.all(np.isfinite(mean))
            or not np.all(np.isfinite(covariance))
        ):
            raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
        # The posterior subtracts quantities on the signal-kernel scale. Its
        # near-zero remainder alone would underestimate floating-point error.
        scale = max(
            float(np.abs(covariance).max()),
            self.covariance_roundoff_scale,
            np.finfo(float).tiny,
        )
        tolerance = max(
            float(64 * np.finfo(float).eps * scale * self.selected_count),
            float(np.finfo(float).tiny),
        )
        if float(np.abs(covariance - covariance.T).max()) > tolerance:
            raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
        covariance = (covariance + covariance.T) * 0.5
        minimum = float(np.linalg.eigvalsh(covariance).min())
        if minimum < -tolerance:
            raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
        if minimum <= tolerance:
            self.selected_covariance_adjustment = tolerance - min(minimum, 0.0)
            covariance = (
                covariance + np.eye(self.selected_count) * self.selected_covariance_adjustment
            )
        try:
            self.lower = cholesky(covariance, lower=True, check_finite=False)
        except np.linalg.LinAlgError as exc:
            raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid") from exc
        # One joint draw matrix is cached for every candidate evaluation in a step.
        draws = np.random.default_rng(self.sample_seed).standard_normal(
            (sample_count, self.selected_count)
        )
        centered = draws @ self.lower.T
        self.selected_samples = mean + centered
        self.condition_weights = cho_solve((self.lower, True), centered.T, check_finite=False)

    def score(self, candidates: Any) -> BoBatchScores:
        import numpy as np
        from scipy.linalg import solve_triangular  # type: ignore[import-untyped]

        points = _coordinates(candidates, self.width)
        scores, means, latent, predictive, conditional = [], [], [], [], []
        adjustment = 0.0
        for start in range(0, len(points), self.chunk_size):
            chunk = points[start : start + self.chunk_size]
            base = self.model.predict(chunk)
            mu, variance, observation = [
                np.asarray(value, dtype=float)
                for value in (
                    base.mean_scaled,
                    base.latent_variance_scaled,
                    base.predictive_variance_scaled,
                )
            ]
            if (
                any(value.shape != (len(chunk),) for value in (mu, variance, observation))
                or any(not np.all(np.isfinite(value)) for value in (mu, variance, observation))
                or np.any(variance < 0)
                or np.any(observation < variance)
            ):
                raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
            planning_variance = variance
            if self.selected_count == 0:
                values = acquisition_scores(mu, np.sqrt(variance), self.context)
            else:
                cross = np.asarray(
                    self.model.latent_cross_covariance(chunk, self.selected_x), dtype=float
                )
                if cross.shape != (len(chunk), self.selected_count) or not np.all(
                    np.isfinite(cross)
                ):
                    raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
                solved = solve_triangular(self.lower, cross.T, lower=True, check_finite=False)
                reduction = np.einsum("ij,ij->j", solved, solved)
                planning_variance = variance - reduction
                scale = np.maximum(
                    np.maximum(variance, reduction),
                    max(self.covariance_roundoff_scale, np.finfo(float).tiny),
                )
                tolerance = 64 * np.finfo(float).eps * scale * max(1, self.selected_count)
                if np.any(planning_variance < -tolerance) or not np.all(
                    np.isfinite(planning_variance)
                ):
                    raise BayesianOptimizationError("bayesian_surrogate_covariance_invalid")
                adjustment = max(adjustment, float(np.maximum(-planning_variance, 0).max()))
                planning_variance = np.maximum(planning_variance, 0.0)
                conditional_mean = mu[:, None] + cross @ self.condition_weights
                assert self.selected_samples is not None
                if self.context.goal_type == "match_target":
                    radius = np.minimum(
                        max(0.0, self.context.incumbent_scaled - self.context.xi_standardized),
                        np.abs(self.selected_samples - self.context.target_scaled).min(axis=1),
                    )
                    sampled = expected_target_improvement(
                        conditional_mean,
                        np.sqrt(planning_variance)[:, None],
                        self.context.target_scaled,
                        radius[None, :],
                        0.0,
                    )
                else:
                    threshold = np.maximum(
                        self.context.incumbent_scaled + self.context.xi_standardized,
                        self.selected_samples.max(axis=1),
                    )
                    sampled = expected_improvement(
                        conditional_mean,
                        np.sqrt(planning_variance)[:, None],
                        threshold[None, :],
                        0.0,
                    )
                values = sampled.mean(axis=1)
            scores.append(values)
            means.append(mu)
            latent.append(variance)
            predictive.append(observation)
            conditional.append(planning_variance)
        return BoBatchScores(
            np.concatenate(scores),
            np.concatenate(means),
            np.concatenate(latent),
            np.concatenate(predictive),
            np.concatenate(conditional),
            adjustment,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "policy_version": POLICY_VERSION,
            "root_seed": self.root_seed,
            "sample_seed": str(self.sample_seed),
            "seed_stage": "latent_selected_samples",
            "batch_step": self.step,
            "requested_sample_count": self.sample_count,
            "effective_sample_count": self.sample_count if self.selected_count else 0,
            "conditioned_on_selected_ranks": list(range(1, self.selected_count + 1)),
            "selected_covariance_adjustment_scaled": self.selected_covariance_adjustment,
            "covariance_roundoff_scale": self.covariance_roundoff_scale,
            "covariance_adjustment_is_measurement_noise": False,
            "representative_prediction_source": "completed_observations_base_posterior",
            "common_random_numbers": True,
        }
