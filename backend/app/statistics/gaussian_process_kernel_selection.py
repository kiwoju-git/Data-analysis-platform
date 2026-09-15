"""Standalone GP family comparison; Bayesian Optimization does not import this module."""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Sequence
from dataclasses import replace
from functools import cmp_to_key
from typing import Any

from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    GaussianProcessRegressionError,
    IntArray,
    KernelPreset,
    _assemble_result,
    _cross_validate,
    _fit_model,
    _ParsedRows,
    _validation_metrics,
    _ValidationResult,
    optimizer_start_count,
)

PRESET_PRIORITY: tuple[KernelPreset, ...] = (
    "matern_5_2_ard",
    "matern_3_2_ard",
    "rbf_ard",
    "rational_quadratic",
)
TIE_POLICY = "primary_1e-10_secondary_1e-10_coverage_distance_1e-10_preset_priority"


def rank_candidates(candidates: list[dict[str, Any]], criterion: str) -> list[dict[str, Any]]:
    primary = {"cv_nlpd": "nlpd", "cv_rmse": "rmse", "cv_mae": "mae"}[criterion]
    secondary = "rmse" if primary == "nlpd" else "nlpd"

    def compare(left: dict[str, Any], right: dict[str, Any]) -> int:
        lm, rm = left["metrics"], right["metrics"]
        for a, b in [
            (lm[primary], rm[primary]),
            (lm[secondary], rm[secondary]),
            (abs(lm["interval_coverage_95"] - 0.95), abs(rm["interval_coverage_95"] - 0.95)),
        ]:
            if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10):
                return -1 if a < b else 1
        return PRESET_PRIORITY.index(left["preset"]) - PRESET_PRIORITY.index(right["preset"])

    return sorted(
        [item for item in candidates if item["status"] == "succeeded"], key=cmp_to_key(compare)
    )


def composed_kernel(preset: str, noise_mode: str) -> str:
    label = {
        "matern_5_2_ard": "Matern 5/2 ARD",
        "matern_3_2_ard": "Matern 3/2 ARD",
        "rbf_ard": "RBF ARD",
        "rational_quadratic": "Rational Quadratic",
    }[preset]
    return f"Constant * {label}" + (" + WhiteKernel" if noise_mode == "estimate" else "")


def compare_kernel_candidates(
    parsed: _ParsedRows,
    response: GaussianProcessColumn,
    predictors: Sequence[GaussianProcessColumn],
    options: GaussianProcessOptions,
    splits: list[tuple[IntArray, IntArray]],
    started: float,
) -> dict[str, object]:
    deadline = started + options.time_budget_seconds
    cv_deadline = started + options.time_budget_seconds * 0.75
    presets = [preset for preset in PRESET_PRIORITY if preset in options.kernel_candidates]
    candidates: list[dict[str, Any]] = []
    validations: dict[KernelPreset, _ValidationResult] = {}
    for index, preset in enumerate(presets):
        candidate_started = time.monotonic()
        quota = max(0.0, cv_deadline - candidate_started) / (len(presets) - index)
        active = replace(
            options, kernel_preset=preset, deadline_monotonic=candidate_started + quota
        )
        record: dict[str, Any] = {
            "preset": preset,
            "composed_kernel": composed_kernel(preset, options.noise_mode),
            "status": "failed",
            "metrics": None,
            "selection_rank": None,
            "selected": False,
            "failure_code": None,
            "details": None,
            "details_failure_code": None,
            "converged_folds": 0,
            "warnings": [],
        }
        try:
            validation = _cross_validate(
                parsed, active, splits, started, preset_index=PRESET_PRIORITY.index(preset)
            )
            metrics = _validation_metrics(parsed.y, validation.mean, validation.predictive_std)
            if any(value is None or not math.isfinite(value) for value in metrics.values()):
                raise GaussianProcessRegressionError("gp_cross_validation_failed")
            validations[preset] = validation
            record.update(
                status="succeeded",
                metrics=metrics,
                converged_folds=validation.converged_folds,
                warnings=[] if validation.converged_folds == len(splits) else ["gp_not_converged"],
            )
        except GaussianProcessRegressionError as exc:
            record["failure_code"] = exc.code
        record["elapsed_seconds"] = time.monotonic() - candidate_started
        candidates.append(record)
    ranked = rank_candidates(candidates, options.selection_criterion)
    if not ranked:
        raise GaussianProcessRegressionError("gp_all_kernel_candidates_failed")
    for rank, candidate in enumerate(ranked, 1):
        candidate["selection_rank"] = rank
        candidate["selected"] = rank == 1
    selected: KernelPreset = ranked[0]["preset"]
    refits = [selected] + (
        [item["preset"] for item in ranked[1:]] if options.retain_candidate_details else []
    )
    selected_result: dict[str, Any] | None = None
    for index, preset in enumerate(refits):
        refit_started = time.monotonic()
        active = replace(
            options,
            kernel_preset=preset,
            random_seed=(options.random_seed + PRESET_PRIORITY.index(preset) * 104729)
            % (2**32 - 1),
            deadline_monotonic=refit_started
            + max(0.0, deadline - refit_started) / (len(refits) - index),
        )
        record = next(candidate for candidate in candidates if candidate["preset"] == preset)
        try:
            with threadpool_limits(limits=1):
                final = _fit_model(parsed.x, parsed.y, active)
                result = _assemble_result(
                    parsed,
                    response,
                    predictors,
                    active,
                    splits,
                    validations[preset],
                    final,
                    time.monotonic() - started,
                    include_projections=preset == selected,
                )
            if preset == selected:
                selected_result = result
            if options.retain_candidate_details:
                record["details"] = {
                    key: result[key]
                    for key in ("method", "kernel", "model_summary", "diagnostics", "warnings")
                }
            record["fitted_kernel_summary"] = result["kernel"]
        except GaussianProcessRegressionError as exc:
            if preset == selected:
                raise
            record["details_failure_code"] = exc.code
        record["elapsed_seconds"] += time.monotonic() - refit_started
    if selected_result is None:
        raise GaussianProcessRegressionError("gp_fit_failed")
    if time.monotonic() > deadline:
        raise GaussianProcessRegressionError("gp_time_budget_exhausted")
    validation_indices = [[parsed.row_indices[int(index)] for index in test] for _, test in splits]
    split_sha = hashlib.sha256(
        json.dumps(validation_indices, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    selected_result["kernel_selection"] = {
        "mode": "compare",
        "criterion": options.selection_criterion,
        "candidate_presets": presets,
        "selected_preset": selected,
        "tie_break_policy": TIE_POLICY,
        "retain_candidate_details": options.retain_candidate_details,
        "selection_is_external_validation": False,
        "cv_split_sha256": split_sha,
        "cv_validation_row_indices": validation_indices,
        "base_seed": options.random_seed,
        "optimizer_starts": optimizer_start_count(options, len(splits)),
        "candidate_cv_budget_fraction": 0.75,
    }
    selected_result["kernel_candidates"] = candidates
    selected_result["warnings"] = sorted(
        set(
            selected_result["warnings"]
            + ["gp_kernel_selection_not_external_validation"]
            + (
                ["gp_kernel_candidate_failed"]
                if any(item["status"] == "failed" for item in candidates)
                else []
            )
        )
    )
    selected_result["method"]["elapsed_seconds"] = time.monotonic() - started
    return selected_result
