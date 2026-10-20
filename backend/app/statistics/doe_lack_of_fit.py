"""Stored SS/DF decomposition is distinct from availability of an F test."""

from __future__ import annotations

from math import isfinite
from typing import Any

import numpy as np
from scipy import stats  # type: ignore[import-untyped]

REPLICATION_POLICY = "all_design_factor_settings_and_block"


def decompose_lack_of_fit(
    *,
    sse: float,
    pure_error_ss: float,
    pure_error_df: int,
    lack_of_fit_df: int,
) -> dict[str, Any]:
    residual_df = pure_error_df + lack_of_fit_df
    tolerance = (
        64
        * np.finfo(float).eps
        * max(1, residual_df)
        * max(abs(sse), abs(pure_error_ss), np.finfo(float).tiny)
    )
    difference = sse - pure_error_ss
    decomposition_available = bool(
        all(isfinite(value) for value in (sse, pure_error_ss, difference, tolerance))
        and sse >= 0
        and pure_error_ss >= 0
        and pure_error_df >= 0
        and lack_of_fit_df >= 0
        and difference >= -tolerance
    )
    ss = max(0.0, difference) if decomposition_available else None
    stored_pure_ss = (
        float(pure_error_ss) if isfinite(pure_error_ss) and pure_error_ss >= 0 else None
    )
    pure_ms = (
        stored_pure_ss / pure_error_df if stored_pure_ss is not None and pure_error_df > 0 else None
    )
    ms = ss / lack_of_fit_df if ss is not None and lack_of_fit_df > 0 else None
    reason = (
        "numerical_decomposition_failure"
        if not decomposition_available
        else "no_replicated_design_points"
        if pure_error_df == 0
        else "no_lack_of_fit_df"
        if lack_of_fit_df == 0
        else "pure_error_variance_zero"
        if pure_ms == 0
        else None
    )
    statistic = ms / pure_ms if reason is None and ms is not None and pure_ms else None
    p_value = (
        float(stats.f.sf(statistic, lack_of_fit_df, pure_error_df))
        if statistic is not None and isfinite(statistic)
        else None
    )
    if reason is None and (
        statistic is None or not isfinite(statistic) or p_value is None or not isfinite(p_value)
    ):
        reason = "numerical_decomposition_failure"
    if reason is not None:
        statistic = p_value = None
    return {
        "available": reason is None,
        "reason": reason,
        "decomposition_available": decomposition_available,
        "replication_grouping_policy": REPLICATION_POLICY,
        "decomposition_tolerance": float(tolerance) if isfinite(tolerance) else None,
        "pure_error": {
            "df": pure_error_df,
            "sum_squares": stored_pure_ss,
            "mean_square": pure_ms if pure_ms is None or isfinite(pure_ms) else None,
        },
        "lack_of_fit": {
            "df": lack_of_fit_df,
            "sum_squares": ss,
            "mean_square": ms if ms is None or isfinite(ms) else None,
            "f_statistic": statistic,
            "p_value": p_value,
        },
        "residual_df": residual_df,
    }
