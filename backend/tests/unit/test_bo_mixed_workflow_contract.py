"""No-refit selected-source, posterior, conditional proof, and budget checks."""

import time
from copy import deepcopy

import pytest

from app.services.bo_mixed_workflow_contract import (
    validate_mixed_evaluation,
    validate_mixed_selection,
)
from app.statistics.bo_mixed_augmentation import build_mixed_augmentation
from app.statistics.bo_mixed_planning import (
    evaluate_mixed_planning_points,
    fit_mixed_planning_model,
    score_mixed_ordered_selection,
)
from tests.unit.test_bo_mixed_planning import payload


@pytest.fixture(scope="module")
def source_model():
    return fit_mixed_planning_model(payload())


@pytest.fixture(scope="module")
def ordered(source_model):
    body = {
        "snapshot": source_model,
        "points": [{"x": 0.35, "material": "C"}, {"x": 0.45, "material": "C"}],
        "eligibility_excluded_encoded": [],
        "sample_count": 16,
        "min_batch_distance": 0.0,
        "max_moment_evaluations": 4096,
        "ordinal_rank_distance": False,
        "time_budget_ms": 60000,
    }
    return body, score_mixed_ordered_selection(**body)


def test_mixed_ordered_validation_no_refit_with_category_code_two(ordered, monkeypatch):
    monkeypatch.setattr(
        "app.statistics.bo_mixed_planning.fit_bo_mixed_surrogate",
        lambda *a, **k: pytest.fail("validation must not fit"),
    )
    validate_mixed_selection("mixed_selection", *ordered, deadline=time.perf_counter() + 60)


@pytest.mark.parametrize(
    "path,value",
    [
        (("items", 1, "planning", "score"), 0.5),
        (("items", 1, "planning", "sampler", "requested_sample_count"), 32),
        (("items", 1, "planning", "sampler", "root_seed"), 41),
        (("items", 1, "planning", "sampler", "moment_evaluations"), 18),
        (
            (
                "items",
                1,
                "planning",
                "proof",
                "response_proofs",
                "yield",
                "cross_covariance_scaled",
                0,
            ),
            0.0,
        ),
        (("items", 1, "planning", "proof", "thresholds", 0), 0.9),
        (("items", 0, "response_predictions", 0, "mean_raw"), 999.0),
        (("items", 0, "encoded_coordinates", "material"), 1.0),
        (("moment_evaluations",), 2),
    ],
)
def test_mixed_ordered_forged_posterior_proof_budget_rejected(ordered, path, value):
    body, original = ordered
    result = deepcopy(original)
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        validate_mixed_selection("mixed_selection", body, result, deadline=time.perf_counter() + 60)


def test_mixed_evaluation_confirm_null_acquisition_and_actual_posterior(source_model):
    body = {
        "snapshot": source_model,
        "points": [{"x": 0.35, "material": "C"}],
        "eligibility_excluded_encoded": [],
        "compute_acquisition": False,
        "ordinal_rank_distance": True,
        "max_moment_evaluations": 4096,
    }
    rows = evaluate_mixed_planning_points(**body)
    assert rows[0]["acquisition"] is None
    validate_mixed_evaluation(body, rows, deadline=time.perf_counter() + 60)
    changed = deepcopy(rows)
    changed[0]["response_predictions"][0]["mean_raw"] = 999.0
    with pytest.raises(ValueError):
        validate_mixed_evaluation(body, changed, deadline=time.perf_counter() + 60)
    with pytest.raises(ValueError, match="time_budget_exhausted"):
        validate_mixed_evaluation(body, rows, deadline=0)


def augmentation_payload(source_model, *, model_free):
    raw = source_model["calculation_request"]
    return {
        "factors": raw["factors"],
        "constraints": raw["constraints"],
        "points": [
            {"x": x, "material": category}
            for x in (0.25, 0.35, 0.45)
            for category in ("A", "B", "C")
        ],
        "existing_coordinates": raw["excluded_encoded"],
        "source": {
            "model_snapshot_id": None if model_free else "00000000-0000-0000-0000-000000000001",
            "model_snapshot_sha256": None if model_free else "a" * 64,
            "candidate_revision_id": "00000000-0000-0000-0000-000000000002",
            "candidate_revision_sha256": "b" * 64,
            "history_sha256": "c" * 64,
        },
        "policy": "greedy_mixed_maximin_v1"
        if model_free
        else "refine_ei_alternating_desirability_response_sd_v2",
        "batch_size": 3,
        "snapshot": None if model_free else source_model,
        "duplicate_tolerance": 1e-6,
        "ordinal_rank_distance": False,
        "min_batch_distance": 0.0,
        "max_evaluations": 1000,
        "max_moment_evaluations": 4096,
        "time_budget_ms": 60000,
    }


@pytest.mark.parametrize("model_free", [True, False])
def test_mixed_augmentation_binding_and_score_tamper(source_model, model_free):
    body = augmentation_payload(source_model, model_free=model_free)
    result = build_mixed_augmentation(**body)
    validate_mixed_selection("mixed_augmentation", body, result, deadline=time.perf_counter() + 60)
    assert [row["encoded_coordinates"]["material"] for row in result["selected_rows"]]
    changed = deepcopy(result)
    changed["augmentation"]["steps"][1]["score"] += 0.1
    with pytest.raises(ValueError):
        validate_mixed_selection(
            "mixed_augmentation", body, changed, deadline=time.perf_counter() + 60
        )
