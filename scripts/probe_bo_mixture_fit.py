"""Synthetic eight-row/six-response default-fit diagnostic, not an acceptance gate.

Matches tests/e2e/bo_mixture_completion.py and the mixtureFit UI defaults.
No workspace, model artifact, observation values, or fitted coefficients are emitted.
Known budget/numerical failures intentionally exit zero as diagnostic evidence.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

KNOWN_DIAGNOSTIC_ERRORS = frozenset(
    {
        "bayesian_optimization_budget_exhausted",
        "bayesian_optimization_time_budget_exhausted",
        "bayesian_optimization_surrogate_fit_failed",
        "bayesian_surrogate_covariance_invalid",
        "bayesian_surrogate_prediction_invalid",
        "bayesian_desirability_numeric_invalid",
        "bayesian_desirability_moments_invalid",
        "bayesian_desirability_quadrature_not_converged",
        "bayesian_desirability_integration_budget_exceeded",
        "bayesian_desirability_covariance_precision_unsupported",
        "bayesian_desirability_raw_variance_precision_unsupported",
        "bayesian_desirability_weight_precision_unsupported",
        "bayesian_desirability_beta_precision_unsupported",
        "bayesian_target_curve_precision_unsupported",
    }
)


def synthetic_payload() -> dict[str, Any]:
    from app.api.v1.schemas.bo_mixed_workflow import MixedFitOptions
    from app.statistics.bo_factor_domains import (
        BoCategoricalFactorDomain,
        BoNumericFactorDomain,
    )
    from app.statistics.bo_mixture_design import BoMixtureDesign
    from app.statistics.bo_mixture_domain import BoMixtureComponent, BoMixtureDomain
    from app.statistics.doe_factor_domain import DoeFactorDomain

    design = BoMixtureDesign(
        BoMixtureDomain(
            (
                BoMixtureComponent("factor_1", 0.1, 0.8, "g"),
                BoMixtureComponent("factor_3", 0.1, 0.8, "g"),
                BoMixtureComponent("factor_4", 0.1, 0.1, "g"),
            ),
            1.0,
            "lower",
        ),
        (
            BoNumericFactorDomain(
                "factor_5", DoeFactorDomain(10, 30, "discrete_numeric", 10)
            ),
            BoCategoricalFactorDomain(
                "factor_6", "nominal", ("A", "B"), "equal_positive_correlation_v1"
            ),
        ),
        (),
    )
    # Match IDs in the retained Linux trace; they are identities, not distances.
    response_ids = [f"response_{key}" for key in (1, 7, 8, 9, 10, 11)]
    fit = MixedFitOptions.model_validate(
        {
            "response_models": [
                {
                    "response_id": response_id,
                    "kernel": {"kind": "matern_5_2"},
                    "surrogate": {
                        "noise_mode": "estimate",
                        "fixed_noise_sd": None,
                        "initial_noise_variance_scaled": 0.01,
                        "lower_noise_variance_scaled": 0.000001,
                        "upper_noise_variance_scaled": 1,
                    },
                }
                for response_id in response_ids
            ],
            "observation_policy": {
                "mode": "retain_raw",
                "nearby_tolerances": None,
                "nearby_units": "normalized",
            },
            "xi_desirability": 0.01,
            "search": {
                "random_seed": 42,
                "candidate_count_per_step": 32,
                "local_start_count_per_step": 0,
                "max_iterations_per_step": 50,
                "max_evaluations_total": 256,
                "model_max_iterations": 60,
                "model_max_evaluations": 1000,
                "hyperparameter_restart_count": 0,
                "time_budget_ms": 60000,
                "jitter": 1e-8,
                "duplicate_tolerance": 1e-6,
            },
            "fit_policy": {
                "policy": "bounded_typed_factor_starts_v1",
                "deterministic_start_count": 3,
            },
            "max_moment_evaluations": 8192,
        }
    ).model_dump(mode="json")
    rows = (
        (0.2, 0.7, 10, "A"),
        (0.3, 0.6, 20, "A"),
        (0.4, 0.5, 30, "A"),
        (0.5, 0.4, 10, "A"),
        (0.2, 0.7, 30, "B"),
        (0.3, 0.6, 10, "B"),
        (0.4, 0.5, 20, "B"),
        (0.5, 0.4, 30, "B"),
    )
    return {
        "design_domain": design.payload(),
        "objective": {
            "name": "Desirability",
            "goal_type": "desirability",
            "curve_policy": "derringer_suich_linear_v1",
            "observation_policy": "complete_response_vector",
            "unit": None,
            "direction": None,
            "target_value": None,
            "target_tolerance": None,
            "responses": [
                {
                    "response_id": response_id,
                    "name": "Yield" if index == 0 else f"Yield {index + 1}",
                    "unit": None,
                    "goal": "maximize",
                    "lower": 0,
                    "target": 30,
                    "upper": None,
                    "importance": 1,
                }
                for index, response_id in enumerate(response_ids)
            ],
        },
        "fit": fit,
        "observations": [
            {
                "trial_id": str(UUID(int=index + 1)),
                "actual_coordinates": {
                    "factor_1": a,
                    "factor_3": b,
                    "factor_4": 0.1,
                    "factor_5": float(temperature),
                    "factor_6": lot,
                },
                "response_values": {
                    response_id: 20
                    + 3 * a
                    - b
                    + temperature / 100
                    + response_index * 0.1
                    for response_index, response_id in enumerate(response_ids)
                },
            }
            for index, (a, b, temperature, lot) in enumerate(rows)
        ],
    }


def run_probe() -> tuple[dict[str, Any], int]:
    completed: list[dict[str, int]] = []
    receipt: dict[str, Any] = {
        "diagnostics_not_acceptance": True,
        "synthetic": True,
        "settings": {
            "rows": 8,
            "responses": 6,
            "mixture_components": 3,
            "fixed_components": 1,
            "coding": "lower",
            "process_factor_kinds": ["discrete_numeric", "nominal"],
            "kernel": "matern_5_2",
            "noise_mode": "estimate",
            "observation_policy": "retain_raw",
            "model_max_evaluations": 1000,
            "model_max_iterations": 60,
            "deterministic_start_count": 3,
            "time_budget_ms": 60000,
            "random_seed": 42,
            "threads": 1,
        },
        "completed_model_evaluations": completed,
    }
    started = time.perf_counter()
    exit_code = 1
    try:
        from threadpoolctl import threadpool_limits

        from app.statistics import bo_mixture_planning as planning
        from app.statistics.bayesian_optimization import BayesianOptimizationError

        payload = synthetic_payload()
        original = planning.fit_bo_mixed_surrogate

        def observed_fit(*args: Any, **kwargs: Any) -> Any:
            model = original(*args, **kwargs)
            completed.append(
                {
                    "response_index": len(completed) + 1,
                    "optimizer_evaluations": model.optimizer["evaluations"],
                }
            )
            return model

        planning.fit_bo_mixed_surrogate = observed_fit
        try:
            with threadpool_limits(limits=1):
                planning.fit_mixture_planning_model(payload)
        except BayesianOptimizationError as exc:
            known = exc.code in KNOWN_DIAGNOSTIC_ERRORS
            receipt.update(
                status="known_budget_or_numerical_error"
                if known
                else "unexpected_error",
                error_code=exc.code
                if re.fullmatch(r"[a-z][a-z0-9_]{0,127}", exc.code)
                else "unexpected_typed_error",
            )
            exit_code = 0 if known else 1
        else:
            receipt.update(status="success", error_code=None)
            exit_code = 0
        finally:
            planning.fit_bo_mixed_surrogate = original
    except Exception:
        receipt.update(status="unexpected_error", error_code="unexpected_exception")
    receipt["elapsed_seconds"] = time.perf_counter() - started
    return receipt, exit_code


def main() -> int:
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[name] = "1"
    receipt, exit_code = run_probe()
    print(json.dumps(receipt, sort_keys=True, allow_nan=False), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
