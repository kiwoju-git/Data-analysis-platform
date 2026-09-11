"""Optional reference generator. Never imported by the application or test runtime.

Run with statsmodels 0.14.5, NumPy 2.2.6 and SciPy 1.15.3 in an isolated
environment. No imports from app; expected inference uses statsmodels OLS.
"""

from __future__ import annotations

import argparse
import json
from itertools import combinations, product
from pathlib import Path

import numpy as np
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor


def reference_case(replicates):
    corners = np.asarray(list(product((-1.0, 1.0), repeat=3)) * replicates)
    names = [tuple(indexes) for order in (1, 2, 3) for indexes in combinations(range(3), order)]
    matrix = np.column_stack(
        [np.ones(len(corners)), *[np.prod(corners[:, indexes], axis=1) for indexes in names]]
    )
    response = matrix @ np.array([10, 3, 2, 1, 0.02, 0.03, 0.04, 0.01])
    if replicates == 2:
        response += np.repeat([-0.5, 0.5], 8)
    active = list(range(8))
    removed = []
    pooled = []
    while True:
        fit = sm.OLS(response, matrix[:, active]).fit()
        eligible = [
            column
            for column in active[1:]
            if not any(set(names[column - 1]) < set(names[other - 1]) for other in active[1:])
        ]
        if not eligible:
            break
        candidates = [
            (column, sm.OLS(response, matrix[:, [item for item in active if item != column]]).fit())
            for column in eligible
        ]
        if replicates == 1 and len(pooled) < 2:
            column, reduced = min(candidates, key=lambda item: (item[1].ssr - fit.ssr, -item[0]))
            pooled.append(column)
        else:
            column, reduced = max(
                candidates, key=lambda item: (fit.compare_f_test(item[1])[1], item[0])
            )
            if fit.compare_f_test(reduced)[1] <= 0.05:
                break
            removed.append(column)
        active.remove(column)
    fit = sm.OLS(response, matrix[:, active]).fit()
    influence = fit.get_influence()
    press = float(np.sum(influence.resid_press**2))
    prediction = fit.get_prediction(np.array([[1, 0.2, -0.4, 0.7]])).summary_frame(alpha=0.05)
    return {
        "replicates": replicates,
        "corners": corners.tolist(),
        "response": response.tolist(),
        "pooled_columns": pooled,
        "removed_columns": removed,
        "final_columns": active,
        "coefficients": fit.params.tolist(),
        "standard_errors": fit.bse.tolist(),
        "p_values": fit.pvalues.tolist(),
        "residual_df": int(fit.df_resid),
        "s": float(np.sqrt(fit.mse_resid)),
        "r_squared": float(fit.rsquared),
        "adjusted_r_squared": float(fit.rsquared_adj),
        "press": press,
        "predicted_r_squared": 1.0 - press / float(fit.centered_tss),
        "vif": [
            float(variance_inflation_factor(matrix[:, active], index))
            for index in range(1, len(active))
        ],
        "prediction_coded": [0.2, -0.4, 0.7],
        "prediction": prediction.to_dict(orient="records")[0],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "schema_version": 1,
        "reference": "statsmodels OLS / compare_f_test / OLSInfluence / get_prediction",
        "statsmodels_version": statsmodels.__version__,
        "numpy_version": np.__version__,
        "absolute_tolerance": 1e-9,
        "relative_tolerance": 1e-8,
        "source": "https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.compare_f_test.html",
        "cases": [reference_case(1), reference_case(2)],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
