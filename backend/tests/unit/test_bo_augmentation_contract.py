"""Bounded receipt checks, without GP fitting or whole-candidate reranking."""

import math
from copy import deepcopy
from dataclasses import asdict
from uuid import UUID

import pytest

from app.services.bo_augmentation_contract import validate_augmentation_binding
from app.statistics.bo_augmentation import (
    CONFIRM,
    MAXPRO,
    MIXED_MAXIMIN,
    REFINE,
    REFINE_V2,
    select_augmentation,
)
from app.statistics.bo_candidate_points import validated_candidate_rows
from app.statistics.bo_desirability_acquisition import beta_expected_improvement


def receipt(policy=MAXPRO, batch_size=3):
    # Non-alphabetical factor order makes accidental JSON-key ordering observable.
    factors = [
        {"factor_id": "z", "low": 0.0, "high": 1.0, "domain_kind": "continuous"},
        {"factor_id": "a", "low": 0.0, "high": 1.0, "domain_kind": "continuous"},
    ]
    existing = [[0.0, 0.2], [1.0, 0.7], [0.0, 0.2]]
    points = [{"z": z, "a": a} for z, a in ((0.2, 0.3), (0.4, 0.5), (0.6, 0.8), (0.8, 0.9))]
    rows = validated_candidate_rows(
        points,
        factors,
        [],
        excluded_normalized=existing,
        duplicate_tolerance=1e-6,
        include_constraint_violations=True,
    )
    source = {
        "model_snapshot_id": None,
        "model_snapshot_sha256": None,
        "candidate_revision_id": str(UUID(int=2)),
        "candidate_revision_sha256": "a" * 64,
        "history_sha256": "b" * 64,
    }
    request = {
        "factors": factors,
        "source": source,
        "policy": policy,
        "batch_size": batch_size,
        "time_budget_ms": 60000,
        "max_evaluations": 1000,
        "max_moment_evaluations": 4096,
        "duplicate_tolerance": 1e-6,
        "min_batch_distance_normalized": 0.0,
    }
    snapshot = None
    predictions = deepcopy(rows)
    context = None
    if policy in {REFINE, REFINE_V2, CONFIRM}:
        source.update(model_snapshot_id=str(UUID(int=1)), model_snapshot_sha256="c" * 64)
        snapshot = {
            "calculation_request": {
                "factors": factors,
                "objective": {
                    "responses": [
                        {"response_id": "r1", "importance": 1.0},
                        {"response_id": "r2", "importance": 3.0},
                    ]
                },
                "xi_desirability": 0.05,
                "search": {"duplicate_tolerance": 1e-6},
            },
            "response_models": [
                {
                    "response_id": "r2",
                    "model": {"normalization": {"scale": 10.0}, "observation_noise_sd_raw": 0.5},
                },
                {
                    "response_id": "r1",
                    "model": {"normalization": {"scale": 2.0}, "observation_noise_sd_raw": 0.1},
                },
            ],
            "incumbent": {"latent_incumbent_value": 0.25},
        }
        for row in predictions:
            row.update(
                response_predictions=[
                    {
                        "response_id": "r1",
                        "mean_raw": 3.0,
                        "latent_standard_deviation_raw": 4.0,
                        "predictive_standard_deviation_raw": math.hypot(4.0, 0.1),
                    },
                    {
                        "response_id": "r2",
                        "mean_raw": 20.0,
                        "latent_standard_deviation_raw": 30.0,
                        "predictive_standard_deviation_raw": math.hypot(30.0, 0.5),
                    },
                ],
                desirability_moments={
                    "mean": 0.5,
                    "second_moment": 1 / 3,
                    "variance": 1 / 12,
                    "estimated_absolute_error": 1e-12,
                    "normal_tail_bound": 0.0,
                    "integration_evaluations": 20,
                },
                acquisition=None
                if policy == CONFIRM
                else {
                    "kind": "desirability_beta_expected_improvement",
                    **asdict(beta_expected_improvement(0.5, 1 / 12, 0.25, xi=0.05)),
                    "xi_desirability": 0.05,
                },
                prediction_source="completed_observations_base_posterior",
            )
        if policy == REFINE_V2:
            context = [
                {"response_id": "r1", "normalization_scale": 2.0, "normalized_importance": 0.25},
                {"response_id": "r2", "normalization_scale": 10.0, "normalized_importance": 0.75},
            ]
    trace = select_augmentation(
        predictions,
        factor_kinds={factor["factor_id"]: factor["domain_kind"] for factor in factors},
        existing_coordinates=[dict(zip(("z", "a"), point, strict=True)) for point in existing],
        source=source,
        policy=policy,
        batch_size=batch_size,
        latent_incumbent=None if snapshot is None else 0.25,
        max_evaluations=1000,
        response_uncertainty_context=context,
    )
    by_id = {row["row_id"]: row for row in predictions}
    result = {
        "schema_version": 1,
        "augmentation": trace,
        "selected_rows": [by_id[key] for key in trace["selected_row_ids"]],
        "source_row_count": len(rows),
        "prediction_evaluations": 0 if snapshot is None else len(rows),
        "max_moment_evaluations": 4096,
        "time_budget_ms": 60000,
        "model_refit": False,
    }
    return result, {
        "request": request,
        "snapshot": snapshot,
        "rows": rows,
        "existing_coordinates": existing,
    }


@pytest.mark.parametrize("policy", [MAXPRO, MIXED_MAXIMIN, REFINE, REFINE_V2, CONFIRM])
def test_valid_receipt_uses_bounded_selected_rows_only(policy, monkeypatch):
    result, arguments = receipt(policy)
    original = deepcopy((result, arguments))

    def forbidden(*args, **kwargs):
        pytest.fail("receipt validation must not refit, restore or rerank all candidates")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    monkeypatch.setattr("app.statistics.bo_planning_model.restore_planning_model", forbidden)
    monkeypatch.setattr("app.statistics.bo_augmentation.select_augmentation", forbidden)
    validate_augmentation_binding(result, **arguments)
    assert (result, arguments) == original


def test_independent_hand_scores_for_maxpro_and_refine():
    result, arguments = receipt(MAXPRO)
    selected = []
    reference = [(0.0, 0.2), (1.0, 0.7)]
    for row, step in zip(result["selected_rows"], result["augmentation"]["steps"], strict=True):
        point = tuple(row["normalized_coordinates"][key] for key in ("z", "a"))
        cost = sum(
            1 / ((point[0] - old[0]) ** 2 * (point[1] - old[1]) ** 2)
            for old in reference + selected
        )
        assert step["score"] == pytest.approx(math.log(cost), rel=2e-15)
        selected.append(point)
    validate_augmentation_binding(result, **arguments)
    result, arguments = receipt(REFINE_V2)
    assert result["augmentation"]["steps"][0]["score"] == pytest.approx(0.7**2 / 2)
    assert result["augmentation"]["steps"][2]["score"] == pytest.approx(math.sqrt(7.75))
    validate_augmentation_binding(result, **arguments)


@pytest.mark.parametrize("field", ["time_budget_ms", "max_moment_evaluations"])
def test_top_level_request_budget_mismatch_is_rejected(field):
    result, arguments = receipt()
    result[field] -= 1
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


@pytest.mark.parametrize(
    "field",
    [
        "time_budget_ms",
        "max_evaluations",
        "raw_reference_count",
        "reference_count",
        "eligible_candidate_count",
        "evaluations",
    ],
)
def test_trace_request_or_count_mismatch_is_rejected(field):
    result, arguments = receipt()
    result["augmentation"][field] += 1
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


@pytest.mark.parametrize(
    "field,value",
    [
        ("score", 12345.0),
        ("criterion", "unrelated"),
        ("nearest_existing_distance", 0.01),
        ("nearest_selected_distance", 0.01),
        ("score_scale", "original"),
        ("optimization_direction", "maximize"),
    ],
)
def test_selected_step_mismatch_is_rejected(field, value):
    result, arguments = receipt()
    result["augmentation"]["steps"][1][field] = value
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


@pytest.mark.parametrize("policy", [MAXPRO, REFINE_V2, CONFIRM])
def test_original_candidate_and_source_binding_is_exact(policy):
    result, arguments = receipt(policy)
    result["selected_rows"][0]["actual_coordinates"]["z"] += 0.01
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)
    result, arguments = receipt(policy)
    result["augmentation"]["source"]["history_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


@pytest.mark.parametrize("field", ["normalization_scale", "normalized_importance"])
def test_refine_context_must_match_original_saved_model(field):
    result, arguments = receipt(REFINE_V2)
    context = result["augmentation"]["response_uncertainty"]["context"]
    if field == "normalization_scale":
        context[0][field] *= 2
    else:
        context[0][field], context[1][field] = context[1][field], context[0][field]
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


def test_refine_acquisition_is_bound_to_stored_moments_and_incumbent():
    result, arguments = receipt(REFINE)
    result["selected_rows"][0]["acquisition"]["value"] = 0.99
    result["augmentation"]["steps"][0]["score"] = 0.99
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


def test_confirm_requires_no_acquisition_and_keeps_competitive_threshold():
    result, arguments = receipt(CONFIRM)
    result["augmentation"]["steps"][1]["competitive_threshold"] = 0.2
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)
    result, arguments = receipt(CONFIRM)
    result["selected_rows"][0]["acquisition"] = receipt(REFINE)[0]["selected_rows"][0][
        "acquisition"
    ]
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


def test_model_free_cannot_emit_fabricated_model_predictions():
    result, arguments = receipt()
    result["prediction_evaluations"] = 1
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


def test_original_factor_order_is_not_sorted_json_key_order():
    result, arguments = receipt()
    arguments["request"]["factors"] = list(reversed(arguments["request"]["factors"]))
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


def test_raised_minimum_distance_cannot_validate_old_selection():
    result, arguments = receipt(MIXED_MAXIMIN)
    arguments["request"]["min_batch_distance_normalized"] = 1.0
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


def test_confirm_does_not_reintroduce_ei_precision_restrictions(monkeypatch):
    result, arguments = receipt(CONFIRM)
    for row, step in zip(result["selected_rows"], result["augmentation"]["steps"], strict=True):
        row["desirability_moments"].update(second_moment=0.25 + 1e-12, variance=1e-12)
        step["score"] = 0.5 if step["rank"] == 1 else 1e-6

    def forbidden(*args, **kwargs):
        pytest.fail("Confirm must not evaluate EI")

    monkeypatch.setattr(
        "app.services.bo_augmentation_contract.stored_beta_expected_improvement", forbidden
    )
    validate_augmentation_binding(result, **arguments)


def test_predictive_uncertainty_retains_saved_noise_not_jitter():
    result, arguments = receipt(REFINE_V2)
    result["selected_rows"][0]["response_predictions"][0]["predictive_standard_deviation_raw"] = 4.0
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


def test_policy_warning_is_part_of_saved_receipt_contract():
    result, arguments = receipt(REFINE_V2)
    result["augmentation"]["warnings"].remove(
        "bayesian_refine_weighted_rms_schedule_product_policy"
    )
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


@pytest.mark.parametrize("field", ["score", "nearest_existing_distance"])
def test_tiny_regenerated_roundoff_is_tolerated_but_not_material_error(field):
    result, arguments = receipt()
    value = result["augmentation"]["steps"][0][field]
    result["augmentation"]["steps"][0][field] = math.nextafter(value, math.inf)
    validate_augmentation_binding(result, **arguments)
    result["augmentation"]["steps"][0][field] = value + 100 * math.ulp(value)
    with pytest.raises(ValueError, match="augmentation_result_invalid"):
        validate_augmentation_binding(result, **arguments)


def test_result_does_not_claim_global_reranking_validation():
    result, arguments = receipt(MIXED_MAXIMIN, batch_size=1)
    # Unselected moments/rank optimality are intentionally not recomputed by this
    # binding validator; independent selector tests cover the selection policy.
    assert len(result["selected_rows"]) == 1
    validate_augmentation_binding(result, **arguments)
