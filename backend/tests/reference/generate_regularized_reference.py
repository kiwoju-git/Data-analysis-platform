"""Offline reference generation, independent of all application helpers.

Run explicitly from the repository root with the project Python interpreter.
This is not imported by production or executed during tests.
"""

import json
from pathlib import Path

import numpy as np
import scipy
import sklearn
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


def estimator(kind, alpha=0.2, ratio=0.7):
    if kind == "ridge":
        return Ridge(alpha=alpha, solver="svd")
    if kind == "lasso":
        return Lasso(alpha=alpha, max_iter=100_000, tol=1e-10, selection="cyclic")
    return ElasticNet(alpha=alpha, l1_ratio=ratio, max_iter=100_000, tol=1e-10, selection="cyclic")


def pipeline(kind, alpha=0.2, ratio=0.7):
    return Pipeline([("scale", StandardScaler()), ("model", estimator(kind, alpha, ratio))])


def fit_payload(model, x, new_x):
    scale = model.named_steps["scale"]
    fit = model.named_steps["model"]
    original = fit.coef_ / scale.scale_
    intercept = float(fit.intercept_ - scale.mean_ @ original)
    return {
        "standardized_coefficients": fit.coef_.tolist(),
        "coefficients": original.tolist(),
        "intercept": intercept,
        "fitted": model.predict(x).tolist(),
        "prediction": model.predict(new_x).tolist(),
        "scaler_means": scale.mean_.tolist(),
        "scaler_scales": scale.scale_.tolist(),
    }


def main():
    rng = np.random.default_rng(731)
    x = rng.normal(size=(24, 3))
    x[:, 1] = 0.85 * x[:, 0] + 0.15 * x[:, 1]
    x[:, 2] = 30 + 4 * x[:, 2]
    y = 3 + 2 * x[:, 0] - 0.4 * x[:, 2] + rng.normal(0, 0.3, 24)
    new_x = np.array([[0.2, 0.3, 32], [-0.4, -0.2, 28]])
    payload = {
        "fixture_schema_version": 1,
        "source": "Independent sklearn Pipeline/GridSearchCV script; no app imports",
        "versions": {
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "tolerance": {"absolute": 1e-7, "relative": 1e-7},
        "input": {"x": x.tolist(), "y": y.tolist(), "new_x": new_x.tolist()},
        "fixed": {},
        "automatic": {},
    }
    for kind in ("ridge", "lasso", "elastic_net"):
        model = pipeline(kind).fit(x, y)
        payload["fixed"][kind] = fit_payload(model, x, new_x)
        if kind == "ridge":
            z = (x - x.mean(axis=0)) / x.std(axis=0)
            closed = np.linalg.solve(z.T @ z + 0.2 * np.eye(3), z.T @ (y - y.mean()))
            np.testing.assert_allclose(closed, model.named_steps["model"].coef_, atol=1e-12)
            payload["fixed"][kind]["independent_normal_equations"] = closed.tolist()
        grid = {"model__alpha": np.logspace(-3, 1, 5)}
        if kind == "elastic_net":
            grid["model__l1_ratio"] = [0.1, 0.7]
        outer = KFold(n_splits=3, shuffle=True, random_state=20260907)
        oof = np.empty(len(y))
        folds = []
        for train, test in outer.split(x):
            inner = KFold(n_splits=3, shuffle=True, random_state=20260907)
            search = GridSearchCV(
                pipeline(kind), grid, cv=inner, scoring="neg_mean_squared_error", n_jobs=1
            )
            search.fit(x[train], y[train])
            oof[test] = search.predict(x[test])
            folds.append({"test_indices": test.tolist(), "selected": search.best_params_})
        final = GridSearchCV(
            pipeline(kind),
            grid,
            cv=KFold(3, shuffle=True, random_state=20260907),
            scoring="neg_mean_squared_error",
            n_jobs=1,
        ).fit(x, y)
        residual = y - oof
        press = float(residual @ residual)
        payload["automatic"][kind] = {
            **fit_payload(final.best_estimator_, x, new_x),
            "selected": final.best_params_,
            "oof_predictions": oof.tolist(),
            "folds": folds,
            "press": press,
            "predicted_r_squared": 1 - press / float(np.sum((y - y.mean()) ** 2)),
            "rmse": float(np.sqrt(np.mean(residual**2))),
            "mae": float(np.mean(np.abs(residual))),
        }
    destination = Path(__file__).parent / "fixtures" / "regularized_linear_model_reference.json"
    destination.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(destination.name)


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
