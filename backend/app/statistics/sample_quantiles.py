from __future__ import annotations

from collections.abc import Sequence

import numpy as np

QUANTILE_METHOD = "hyndman_fan_6_weibull"
QUANTILE_POSITION = "p_times_n_plus_1"


def sample_quantile_hf6(values: Sequence[float], probability: float) -> float | None:
    """Return the bounded Hyndman-Fan type 6 sample quantile."""
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between zero and one")
    if not values:
        return None
    return float(np.quantile(np.asarray(values, dtype=float), probability, method="weibull"))


def sample_quartiles_hf6(values: Sequence[float]) -> tuple[float | None, float | None]:
    return sample_quantile_hf6(values, 0.25), sample_quantile_hf6(values, 0.75)
