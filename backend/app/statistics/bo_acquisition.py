"""Latent, posterior-mean plug-in acquisitions for the versioned BO policy."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from app.statistics.bayesian_optimization import BayesianOptimizationError

GoalType = Literal["maximize", "minimize", "match_target"]


def _numeric(value: Any) -> Any:
    import numpy as np

    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = raw.astype(float, copy=False)
        if not np.all(np.isfinite(result)):
            raise ValueError
        return result
    except (TypeError, ValueError, OverflowError) as exc:
        raise BayesianOptimizationError("bayesian_acquisition_input_invalid") from exc


def _inputs(*values: Any) -> tuple[Any, ...]:
    import numpy as np

    try:
        return tuple(np.broadcast_arrays(*[_numeric(value) for value in values]))
    except ValueError as exc:
        raise BayesianOptimizationError("bayesian_acquisition_input_invalid") from exc


def _checked_result(value: Any, scale: Any) -> Any:
    import numpy as np

    tolerance = 64 * np.finfo(float).eps * np.maximum(np.abs(scale), np.finfo(float).tiny)
    if not np.all(np.isfinite(value)) or np.any(value < -tolerance):
        raise BayesianOptimizationError("bayesian_acquisition_numeric_invalid")
    return np.maximum(value, 0.0)


def expected_improvement(mean: Any, standard_deviation: Any, incumbent: Any, xi: Any = 0.0) -> Any:
    """Broadcasting EI in standardized, larger-is-better latent coordinates."""
    import numpy as np
    from scipy.special import erfcx, ndtr  # type: ignore[import-untyped]

    mu, sd, baseline, exploration = _inputs(mean, standard_deviation, incumbent, xi)
    if np.any(sd < 0) or np.any(exploration < 0):
        raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        gain = mu - baseline - exploration
    if not np.all(np.isfinite(gain)):
        raise BayesianOptimizationError("bayesian_acquisition_numeric_invalid")
    result = np.maximum(gain, 0.0)
    positive = sd > 0
    if np.any(positive):
        delta, sigma = gain[positive], sd[positive]
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            z = delta / sigma
        values = np.maximum(delta, 0.0)
        finite = np.isfinite(z)
        zf = z[finite]
        with np.errstate(over="ignore", under="ignore"):
            density = np.exp(-0.5 * zf**2) / math.sqrt(2 * math.pi)
        regular = zf >= -8
        evaluated = np.empty_like(zf)
        evaluated[regular] = (
            delta[finite][regular] * ndtr(zf[regular]) + sigma[finite][regular] * density[regular]
        )
        # The scaled complementary error function avoids subtracting two tails.
        tail = zf[~regular]
        evaluated[~regular] = (
            sigma[finite][~regular]
            * density[~regular]
            * (1 + tail * math.sqrt(math.pi / 2) * erfcx(-tail / math.sqrt(2)))
        )
        values[finite] = evaluated
        result = np.array(result, copy=True)
        result[positive] = values
    return _checked_result(result, np.maximum(np.abs(gain), sd))


def _normal_interval(lower: Any, upper: Any) -> Any:
    import numpy as np
    from scipy.special import ndtr  # type: ignore[import-untyped]

    return np.where(lower > 0, ndtr(-lower) - ndtr(-upper), ndtr(upper) - ndtr(lower))


@lru_cache(maxsize=1)
def _target_quadrature_nodes() -> tuple[Any, Any]:
    import numpy as np

    nodes, weights = np.polynomial.legendre.leggauss(32)
    shifted_nodes, shifted_weights = (nodes + 1) / 2, weights / 2
    shifted_nodes.flags.writeable = shifted_weights.flags.writeable = False
    return shifted_nodes, shifted_weights


def expected_target_improvement(
    mean: Any,
    standard_deviation: Any,
    target: Any,
    incumbent_distance: Any,
    xi: Any = 0.0,
) -> Any:
    """Expected triangular target gain; per-sample radii broadcast explicitly."""
    import numpy as np

    mu, sd, center, distance, exploration = _inputs(
        mean, standard_deviation, target, incumbent_distance, xi
    )
    if np.any(sd < 0) or np.any(distance < 0) or np.any(exploration < 0):
        raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
    with np.errstate(over="ignore", invalid="ignore"):
        delta = mu - center
        radius = np.maximum(distance - exploration, 0.0)
    if not np.all(np.isfinite(delta)):
        raise BayesianOptimizationError("bayesian_acquisition_numeric_invalid")
    result = np.maximum(radius - np.abs(delta), 0.0)
    positive = (sd > 0) & (radius > 0)
    if np.any(positive):
        d, sigma, r = delta[positive], sd[positive], radius[positive]
        with np.errstate(over="ignore", divide="ignore", invalid="ignore", under="ignore"):
            lo, mid, hi = (-r - d) / sigma, -d / sigma, (r - d) / sigma
            left, right = _normal_interval(lo, mid), _normal_interval(mid, hi)

            def phi(z: Any) -> Any:
                return np.exp(-0.5 * z**2) / math.sqrt(2 * math.pi)

            evaluated = (
                (r + d) * left + (r - d) * right + sigma * (phi(lo) - 2 * phi(mid) + phi(hi))
            )
        tolerance = (
            64 * np.finfo(float).eps * np.maximum(r + np.abs(d) + sigma, np.finfo(float).tiny)
        )
        if np.any(evaluated < -tolerance) or not np.all(np.isfinite(evaluated)):
            raise BayesianOptimizationError("bayesian_acquisition_numeric_invalid")
        # Tiny target windows cancel in the closed form. Integrate the same
        # positive triangular integrand on two fixed, bounded unit intervals.
        cancellation = (np.abs(evaluated) <= tolerance) & (r <= sigma)
        if np.any(cancellation):
            u, w = _target_quadrature_nodes()
            rr, ss, dd = r[cancellation], sigma[cancellation], d[cancellation]
            integrals = np.empty(len(rr))
            for start in range(0, len(rr), 256):
                rc, sc, dc = (
                    rr[start : start + 256],
                    ss[start : start + 256],
                    dd[start : start + 256],
                )
                with np.errstate(over="ignore", under="ignore", divide="ignore"):
                    location = rc[:, None] * u
                    density = phi((location - dc[:, None]) / sc[:, None]) + phi(
                        (-location - dc[:, None]) / sc[:, None]
                    )
                    integrals[start : start + 256] = (
                        rc * (rc / sc) * (density * (1 - u) * w).sum(axis=1)
                    )
            evaluated[cancellation] = integrals
        result = np.array(result, copy=True)
        result[positive] = evaluated
    return _checked_result(result, radius)


@dataclass(frozen=True)
class BoAcquisitionContext:
    goal_type: GoalType
    xi_standardized: float
    incumbent_scaled: float
    target_scaled: float | None = None

    def __post_init__(self) -> None:
        if self.goal_type not in {"maximize", "minimize", "match_target"}:
            raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
        xi, incumbent = _inputs(self.xi_standardized, self.incumbent_scaled)
        if xi.ndim != 0 or incumbent.ndim != 0 or float(xi) < 0:
            raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
        if self.goal_type == "match_target":
            target = _numeric(self.target_scaled)
            if target.ndim != 0 or float(incumbent) < 0:
                raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
        elif self.target_scaled is not None:
            raise BayesianOptimizationError("bayesian_acquisition_input_invalid")


def acquisition_scores(
    mean_scaled: Any, latent_std_scaled: Any, context: BoAcquisitionContext
) -> Any:
    if context.goal_type == "match_target":
        return expected_target_improvement(
            mean_scaled,
            latent_std_scaled,
            context.target_scaled,
            context.incumbent_scaled,
            context.xi_standardized,
        )
    return expected_improvement(
        mean_scaled, latent_std_scaled, context.incumbent_scaled, context.xi_standardized
    )


def build_acquisition_context(
    model: Any,
    completed_x: Any,
    raw_y: Any,
    trial_ids: list[str],
    *,
    goal_type: GoalType,
    xi_standardized: float,
    target_value: float | None = None,
) -> tuple[BoAcquisitionContext, dict[str, Any]]:
    import numpy as np

    x, y = _numeric(completed_x), _numeric(raw_y)
    if (
        x.ndim != 2
        or len(x) == 0
        or y.shape != (len(x),)
        or len(trial_ids) != len(x)
        or any(not isinstance(value, str) or not value for value in trial_ids)
        or len(set(trial_ids)) != len(trial_ids)
        or goal_type not in {"maximize", "minimize", "match_target"}
        or model.direction_multiplier != (-1.0 if goal_type == "minimize" else 1.0)
        or not math.isfinite(model.normalization_scale)
        or model.normalization_scale <= 0
        or not math.isfinite(model.normalization_mean)
    ):
        raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
    means = _numeric(model.predict(x).mean_scaled)
    if means.shape != (len(x),):
        raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
    target_scaled = None
    observed_distance = latent_distance = None
    if goal_type == "match_target":
        target = _numeric(target_value)
        if target.ndim != 0:
            raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
        target_scaled = (float(target) - model.normalization_mean) / model.normalization_scale
        distances = np.abs(means - target_scaled)
        best_index = int(np.argmin(np.abs(y - float(target))))
        latent_index = int(np.argmin(distances))
        incumbent = float(distances[latent_index])
        observed_distance = float(abs(y[best_index] - float(target)))
        latent_distance = incumbent * model.normalization_scale
    else:
        if target_value is not None:
            raise BayesianOptimizationError("bayesian_acquisition_input_invalid")
        best_index = int(np.argmax(model.direction_multiplier * y))
        latent_index = int(np.argmax(means))
        incumbent = float(means[latent_index])
    context = BoAcquisitionContext(goal_type, xi_standardized, incumbent, target_scaled)
    latent_raw = model.direction_multiplier * (
        float(means[latent_index]) * model.normalization_scale + model.normalization_mean
    )
    xi_raw = xi_standardized * model.normalization_scale
    if not all(
        value is None or math.isfinite(value)
        for value in (latent_raw, xi_raw, observed_distance, latent_distance, target_scaled)
    ):
        raise BayesianOptimizationError("bayesian_acquisition_numeric_invalid")
    return context, {
        "incumbent_policy": "posterior_mean_at_completed_locations_v2",
        "incumbent_kind": "latent_target_distance"
        if goal_type == "match_target"
        else "directional_latent_mean",
        "best_observed_objective": float(y[best_index]),
        "best_observed_trial_id": trial_ids[best_index],
        "best_observed_target_distance_raw": observed_distance,
        "latent_incumbent_value_scaled": float(means[latent_index]),
        "latent_incumbent_value_raw": latent_raw,
        "latent_incumbent_distance_scaled": incumbent if goal_type == "match_target" else None,
        "latent_incumbent_distance_raw": latent_distance,
        "latent_incumbent_trial_id": trial_ids[latent_index],
        "latent_incumbent_coordinates_normalized": x[latent_index].tolist(),
        "target_scaled": target_scaled,
        "xi_standardized": xi_standardized,
        "xi_raw": xi_raw,
    }
