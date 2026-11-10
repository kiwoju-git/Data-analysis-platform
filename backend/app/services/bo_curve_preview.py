"""Bounded, non-persistent curve comparison. No study, fit or artifact reader."""

import math
from collections.abc import Callable

from app.api.v1.schemas.bo_curve_preview import (
    CurvePreviewMetrics,
    CurvePreviewPoint,
    CurvePreviewRequest,
    CurvePreviewResponse,
)
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import (
    CURVE_POLICY,
    DesirabilityGoal,
    DesirabilityMoments,
    gaussian_desirability_moments,
    individual_desirability,
)
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_target_curve import (
    TARGET_CURVE_POLICY,
    target_desirability,
    target_moments,
)


def preview_target_curve(body: CurvePreviewRequest) -> CurvePreviewResponse:
    curve = body.controls.curve()
    linear = DesirabilityGoal("preview", "match_target", curve.lower, curve.target, curve.upper)
    # Include exact control points; use a bounded grid without coordinate rounding.
    values = sorted(
        {body.plot_lower + (body.plot_upper - body.plot_lower) * (i / 160) for i in range(1, 160)}
        | {body.plot_lower, body.plot_upper, curve.lower, curve.target, curve.upper}
    )
    points = [
        CurvePreviewPoint(
            response_value=x,
            gaussian=target_desirability(x, curve),
            linear=float(individual_desirability(x, linear)),
        )
        for x in values
    ]
    metrics: list[CurvePreviewMetrics] = []
    if body.assumed_distribution is not None:
        assumed = body.assumed_distribution
        calculators: tuple[tuple[str, Callable[[], DesirabilityMoments]], ...] = (
            (
                TARGET_CURVE_POLICY,
                lambda: target_moments(assumed.mean, assumed.standard_deviation, curve),
            ),
            (
                CURVE_POLICY,
                lambda: gaussian_desirability_moments(
                    assumed.mean, assumed.standard_deviation, linear
                ),
            ),
        )
        for policy, calculate in calculators:
            item = CurvePreviewMetrics(policy=policy)
            try:
                moments = calculate()
            except BayesianOptimizationError as exc:
                item.unavailable_code = str(exc)
            else:
                item.mean, item.variance = moments.mean, moments.variance
                item.second_moment = moments.second_moment
                item.normal_tail_bound = moments.normal_tail_bound
                item.integration_error = moments.estimated_absolute_error
                try:
                    ei = beta_expected_improvement(
                        moments.mean, moments.variance, assumed.incumbent, xi=assumed.xi
                    )
                except BayesianOptimizationError as exc:
                    item.ei_unavailable_code = str(exc)
                else:
                    item.beta_ei, item.ei_distribution = ei.value, ei.distribution
            metrics.append(item)
    if any(not math.isfinite(p.response_value) for p in points):
        raise ValueError("bayesian_curve_preview_range_invalid")
    return CurvePreviewResponse(
        request_snapshot=body,
        curve_policy="two_sided_gaussian_target_peak_one_v1",
        comparison_policy="derringer_suich_linear_v1",
        moment_policy="gaussian_target_closed_form_centered_variance_v1",
        points=points,
        gaussian_underflow_count=sum(point.gaussian == 0 for point in points),
        metrics=metrics,
    )
