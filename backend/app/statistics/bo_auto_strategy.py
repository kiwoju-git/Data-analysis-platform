"""Decision-only routing of conditional LOO metrics; never select or fit rows."""

import math
from typing import Any


def suggest_augmentation(
    responses: list[dict[str, Any]], factor_kinds: list[str], threshold: float
) -> dict[str, Any]:
    if (
        type(threshold) not in {int, float}
        or not math.isfinite(threshold)
        or not 0 <= threshold <= 1
        or not 1 <= len(responses) <= 4
        or not 1 <= len(factor_kinds) <= 10
        or any(
            kind not in {"continuous", "discrete_numeric", "nominal", "ordinal"}
            for kind in factor_kinds
        )
    ):
        raise ValueError("bayesian_auto_strategy_invalid")
    ids, below, unavailable = [], [], []
    # Validate every response before deciding; an early low score cannot hide
    # a missing/undefined response or a corrupt diagnostic later in the list.
    for row in responses:
        key, value = row.get("response_id"), row.get("r_squared")
        if (
            not isinstance(key, str)
            or not key
            or key in ids
            or "r_squared" not in row
            or (
                value is not None
                and (type(value) not in {int, float} or not math.isfinite(value) or value > 1)
            )
        ):
            raise ValueError("bayesian_auto_strategy_invalid")
        ids.append(key)
        if value is None:
            unavailable.append(key)
        elif value < threshold:
            below.append(key)
    warnings = ["conditional_loo_not_external_validation", "not_verified_jmp_auto_parity"]
    policy: str | None = None
    if unavailable:
        reason = "r_squared_unavailable"
    elif below:
        reason = "any_response_below_threshold"
        policy = "greedy_incremental_maxpro_v1"
        if any(kind != "continuous" for kind in factor_kinds):
            policy = "greedy_mixed_maximin_v1"
            warnings.append("mixed_maximin_is_product_policy")
    else:
        reason = "all_responses_meet_threshold"
        policy = "refine_ei_alternating_desirability_response_sd_v2"
        warnings.append("all_pass_refine_is_product_policy")
    return {
        "schema_version": 1,
        "policy": "conditional_loo_any_low_explore_else_refine_v1",
        "threshold": float(threshold),
        "comparison": "strictly_less_than",
        "recommended_policy": policy,
        "reason": reason,
        "response_ids": ids,
        "below_threshold_response_ids": below,
        "unavailable_response_ids": unavailable,
        "ordinal_rank_distance_requires_consent": "ordinal" in factor_kinds,
        "warnings": warnings,
    }
