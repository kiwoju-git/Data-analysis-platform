import json
import math
from copy import deepcopy

import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_augmentation import (
    CONFIRM,
    MAXPRO,
    MIXED_MAXIMIN,
    REFINE,
    select_augmentation,
)


def _source(*, model=False):
    return {
        "model_snapshot_id": "00000000-0000-4000-8000-000000000001" if model else None,
        "model_snapshot_sha256": "a" * 64 if model else None,
        "candidate_revision_id": "00000000-0000-4000-8000-000000000002",
        "candidate_revision_sha256": "b" * 64,
        "history_sha256": "c" * 64,
    }


def _row(index, point, *, mean=None, variance=None, ei=None):
    result = {
        "row_id": f"{index:064x}",
        "normalized_coordinates": point,
        "eligible": True,
        "novel": True,
        "constraints_satisfied": True,
    }
    if mean is not None:
        result["desirability_moments"] = {"mean": mean, "variance": variance}
        result["acquisition"] = {"value": ei}
    return result


def _select(rows, *, policy=MAXPRO, **kwargs):
    arguments = {
        "factor_kinds": {"x": "continuous"},
        "existing_coordinates": [{"x": 0}, {"x": 1}],
        "source": _source(model=policy in {REFINE, CONFIRM}),
        "policy": policy,
        "batch_size": 1,
    }
    return select_augmentation(rows, **(arguments | kwargs))


def test_maxpro_hand_calculation_and_row_id_tie_break_without_model():
    rows = [_row(3, {"x": 0.75}), _row(1, {"x": 0.25}), _row(2, {"x": 0.5})]
    original = deepcopy(rows)
    result = _select(rows, batch_size=3)
    assert result["selected_row_ids"] == [rows[2]["row_id"], rows[1]["row_id"], rows[0]["row_id"]]
    assert math.exp(result["steps"][0]["score"]) == pytest.approx(8, rel=1e-14)
    assert math.exp(result["steps"][1]["score"]) == pytest.approx(16 + 16 / 9 + 16, rel=1e-14)
    assert result["steps"][0]["optimization_direction"] == "minimize"
    assert result["steps"][0]["score_scale"] == "natural_log"
    assert result["steps"][1]["nearest_selected_distance"] == 0.25
    assert result["evaluations"] == 6
    assert result["source"]["model_snapshot_id"] is None
    assert not result["model_refit"] and not result["fantasy_observations"]
    assert rows == original
    json.dumps(result, allow_nan=False)


def test_maxpro_matches_independent_direct_product_criterion_in_two_dimensions():
    reference = [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}]
    rows = [
        _row(index, dict(zip(("x", "y"), values, strict=True)))
        for index, values in enumerate(((0.2, 0.8), (0.4, 0.6), (0.7, 0.3), (0.6, 0.5)), 1)
    ]
    expected_ids, expected_costs = [], []
    points = [list(point.values()) for point in reference]
    for _ in range(3):
        costs = []
        for row in rows:
            if row["row_id"] in expected_ids:
                continue
            point = list(row["normalized_coordinates"].values())
            cost = sum(
                1 / math.prod((a - b) ** 2 for a, b in zip(point, old, strict=True))
                for old in points
            )
            costs.append((cost, row["row_id"], point))
        score, row_id, selected = min(costs)
        expected_ids.append(row_id)
        expected_costs.append(score)
        points.append(selected)
    result = _select(
        rows,
        factor_kinds={"x": "continuous", "y": "continuous"},
        existing_coordinates=reference,
        batch_size=3,
    )
    assert result["selected_row_ids"] == expected_ids
    assert [math.exp(step["score"]) for step in result["steps"]] == pytest.approx(
        expected_costs, rel=1e-14
    )


def test_projection_collision_is_not_hidden_by_epsilon_or_different_policy():
    rows = [_row(1, {"x": 0.0, "y": 0.5})]
    with pytest.raises(BayesianOptimizationError, match="bayesian_maxpro_projection_collision"):
        _select(
            rows,
            factor_kinds={"x": "continuous", "y": "continuous"},
            existing_coordinates=[{"x": 0, "y": 0}],
        )


def test_projection_collision_trace_uses_null_not_json_infinity():
    rows = [_row(1, {"x": 0.0, "y": 0.5}), _row(2, {"x": 0.5, "y": 0.5})]
    result = _select(
        rows,
        factor_kinds={"x": "continuous", "y": "continuous"},
        existing_coordinates=[{"x": 0, "y": 0}],
    )
    assert result["selected_row_ids"] == [rows[1]["row_id"]]
    assert result["unscorable_candidates"] == [
        {
            "row_id": rows[0]["row_id"],
            "first_rank": 1,
            "score": None,
            "status": "projection_collision",
        }
    ]
    json.dumps(result, allow_nan=False)


def test_incremental_maxpro_fixed_reference_collision_and_duplicate_geometry_are_explicit():
    result = _select(
        [_row(1, {"x": 0.5, "y": 0.5})],
        factor_kinds={"x": "continuous", "y": "continuous"},
        existing_coordinates=[{"x": 0, "y": 0}, {"x": 0, "y": 1}, {"x": 0, "y": 0}],
    )
    assert result["raw_reference_count"] == 3
    assert result["reference_count"] == 2
    assert math.exp(result["steps"][0]["score"]) == pytest.approx(32, rel=1e-14)
    assert "bayesian_maxpro_fixed_reference_projection_collisions" in result["warnings"]


def test_log_maxpro_cost_stays_finite_when_raw_inverse_product_would_overflow():
    rows = [_row(1, {"x": 1e-200, "y": 0.5})]
    result = _select(
        rows,
        factor_kinds={"x": "continuous", "y": "continuous"},
        existing_coordinates=[{"x": 0, "y": 0}],
    )
    assert result["steps"][0]["score"] == pytest.approx(-2 * (math.log(1e-200) + math.log(0.5)))
    json.dumps(result, allow_nan=False)


def test_refine_first_base_ei_then_base_desirability_sd_not_fantasies():
    rows = [
        _row(1, {"x": 0.2}, mean=0.5, variance=0.01, ei=0.5),
        _row(2, {"x": 0.4}, mean=0.5, variance=0.09, ei=0.2),
        _row(3, {"x": 0.6}, mean=0.5, variance=0.04, ei=0.4),
        _row(4, {"x": 0.8}, mean=0.5, variance=0.16, ei=0.01),
    ]
    original = deepcopy(rows)
    result = _select(rows, policy=REFINE, batch_size=3)
    assert result["selected_row_ids"] == [rows[index]["row_id"] for index in (0, 3, 1)]
    assert [step["score"] for step in result["steps"]] == pytest.approx([0.5, 0.4, 0.3])
    assert [step["criterion"] for step in result["steps"]] == [
        "base_desirability_beta_ei",
        "base_desirability_standard_deviation",
        "base_desirability_standard_deviation",
    ]
    assert "bayesian_refine_multimodel_sd_not_implemented" in result["warnings"]
    assert not result["fantasy_observations"]
    assert rows == original


def test_confirm_observed_location_incumbent_defines_competitive_subset():
    rows = [
        _row(1, {"x": 0.2}, mean=0.9, variance=0.01, ei=0.01),
        _row(2, {"x": 0.4}, mean=0.8, variance=0.04, ei=0.05),
        _row(3, {"x": 0.6}, mean=0.5, variance=0.25, ei=0.2),
        _row(4, {"x": 0.8}, mean=0.7, variance=0.15, ei=0.1),
    ]
    result = _select(rows, policy=CONFIRM, latent_incumbent=0.7, batch_size=3)
    assert result["selected_row_ids"] == [rows[index]["row_id"] for index in (0, 3, 1)]
    assert [step["competitive_threshold"] for step in result["steps"]] == [None, 0.7, 0.7]
    assert result["steps"][1]["compared_candidate_count"] == 2
    assert result["steps"][0]["score"] == 0.9
    with pytest.raises(
        BayesianOptimizationError, match="bayesian_augmentation_insufficient_candidates"
    ):
        _select(rows, policy=CONFIRM, latent_incumbent=0.95, batch_size=2)


def test_selection_is_row_order_independent_and_source_inputs_are_not_mutated():
    rows = [_row(i, {"x": x}) for i, x in enumerate((0.25, 0.5, 0.75), 1)]
    source = _source()
    original = deepcopy((rows, source))
    first = _select(rows, batch_size=3, source=source)
    reverse = _select(rows[::-1], batch_size=3, source=source)
    assert first == reverse
    assert (rows, source) == original
    first["source"]["history_sha256"] = "d" * 64
    assert source == original[1]


def test_mixed_maximin_uses_nominal_equality_not_integer_code_distance():
    rows = [
        _row(1, {"x": 0.2, "kind": 31}),
        _row(2, {"x": 0.2, "kind": 1}),
        _row(3, {"x": 0.7, "kind": 0}),
    ]
    arguments = {
        "policy": MIXED_MAXIMIN,
        "factor_kinds": {"x": "continuous", "kind": "nominal"},
        "existing_coordinates": [{"x": 0.0, "kind": 0}],
        "batch_size": 2,
    }
    result = _select(rows, **arguments)
    assert result["selected_row_ids"][0] == rows[0]["row_id"]
    assert result["steps"][0]["score"] == pytest.approx(math.sqrt(1.04), rel=1e-14)
    renamed = deepcopy(rows)
    names = {31: "resin A", 1: "resin B", 0: "control"}
    for row in renamed:
        row["normalized_coordinates"]["kind"] = names[row["normalized_coordinates"]["kind"]]
    renamed_result = _select(
        renamed, **(arguments | {"existing_coordinates": [{"x": 0, "kind": "control"}]})
    )
    assert result == renamed_result


@pytest.mark.parametrize("kind", ["nominal", "ordinal", "discrete_numeric"])
def test_noncontinuous_maxpro_has_no_implicit_mixed_fallback(kind):
    with pytest.raises(BayesianOptimizationError, match="bayesian_maxpro_continuous_only"):
        _select([_row(1, {"x": 0.5})], factor_kinds={"x": kind})


def test_ordinal_rank_distance_requires_explicit_assumption():
    arguments = {"policy": MIXED_MAXIMIN, "factor_kinds": {"x": "ordinal"}}
    rows = [_row(1, {"x": 0.25}), _row(2, {"x": 0.5})]
    with pytest.raises(
        BayesianOptimizationError, match="bayesian_augmentation_ordinal_distance_required"
    ):
        _select(rows, **arguments)
    result = _select(rows, ordinal_rank_distance=True, **arguments)
    assert result["selected_row_ids"] == [rows[1]["row_id"]]
    assert result["ordinal_rank_distance"] is True


def test_explicit_discrete_maximin_compares_only_supplied_executable_rows():
    rows = [_row(1, {"x": 0.25}), _row(2, {"x": 0.5}), _row(3, {"x": 0.75})]
    result = _select(
        rows, policy=MIXED_MAXIMIN, factor_kinds={"x": "discrete_numeric"}, batch_size=2
    )
    assert result["selected_row_ids"] == [rows[1]["row_id"], rows[0]["row_id"]]
    assert [step["score"] for step in result["steps"]] == [0.5, 0.25]


def test_eligibility_and_exact_novelty_are_rechecked_without_partial_selection():
    rows = [_row(1, {"x": 0.0}), _row(2, {"x": 0.25}), _row(3, {"x": 0.5})]
    rows[1].update(eligible=False, constraints_satisfied=False)
    result = _select(rows)
    assert result["selected_row_ids"] == [rows[2]["row_id"]]
    assert result["eligible_candidate_count"] == 1
    original = deepcopy(rows)
    with pytest.raises(
        BayesianOptimizationError, match="bayesian_augmentation_insufficient_candidates"
    ):
        _select(rows, batch_size=2)
    assert rows == original


def test_minimum_distance_failure_is_not_reported_as_projection_collision():
    rows = [_row(1, {"x": 0.2}), _row(2, {"x": 0.3})]
    with pytest.raises(
        BayesianOptimizationError, match="bayesian_augmentation_insufficient_candidates"
    ):
        _select(rows, batch_size=2, min_batch_distance_normalized=0.4)


def test_evaluation_budget_aborts_without_returning_partial_batch():
    rows = [_row(i, {"x": x}) for i, x in enumerate((0.2, 0.4, 0.7), 1)]
    original = deepcopy(rows)
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_budget_exhausted"):
        _select(rows, batch_size=2, max_evaluations=3)
    assert rows == original


def test_deadline_is_checked_before_candidate_work(monkeypatch):
    clock = iter((0.0, 2.0))
    monkeypatch.setattr("app.statistics.bo_augmentation.time.perf_counter", lambda: next(clock))
    with pytest.raises(
        BayesianOptimizationError, match="bayesian_augmentation_time_budget_exhausted"
    ):
        _select([_row(1, {"x": 0.5})], time_budget_ms=1000)


@pytest.mark.parametrize(
    "value", [True, "0.5", float("nan"), float("inf"), -0.1, 1.1, 10**1000, None, [], {}]
)
def test_normalized_coordinates_reject_nonfinite_coercions_and_out_of_range(value):
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_input_invalid"):
        _select([_row(1, {"x": value})])


@pytest.mark.parametrize(
    "change",
    [
        {"factor_kinds": {"x": []}},
        {"factor_kinds": {"x": "unknown"}},
        {"batch_size": True},
        {"batch_size": 0},
        {"batch_size": 9},
        {"duplicate_tolerance": 0},
        {"duplicate_tolerance": float("nan")},
        {"min_batch_distance_normalized": -0.1},
        {"min_batch_distance_normalized": 2},
        {"existing_coordinates": []},
        {"existing_coordinates": [{"wrong": 0}]},
        {"time_budget_ms": True},
        {"max_evaluations": 0},
        {"ordinal_rank_distance": 1},
    ],
)
def test_invalid_policy_arguments_are_rejected(change):
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_input_invalid"):
        _select([_row(1, {"x": 0.5})], **change)


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_snapshot_id", None),
        ("model_snapshot_sha256", None),
        ("model_snapshot_id", "unsafe path"),
        ("candidate_revision_id", "not-a-uuid"),
        ("history_sha256", "a" * 63),
        ("candidate_revision_sha256", "G" * 64),
    ],
)
def test_exact_source_identity_contract_is_mandatory(field, value):
    source = _source(model=True)
    source[field] = value
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_input_invalid"):
        _select([_row(1, {"x": 0.5}, mean=0.5, variance=0.1, ei=0.2)], policy=REFINE, source=source)


def test_unknown_source_fields_and_duplicate_row_ids_or_points_rejected():
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_input_invalid"):
        _select([_row(1, {"x": 0.5})], source=_source() | {"path": "not-read"})
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_input_invalid"):
        _select([_row(1, {"x": 0.25}), _row(1, {"x": 0.5})])
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_duplicate_row"):
        _select([_row(1, {"x": 0.5}), _row(2, {"x": 0.5})])


@pytest.mark.parametrize(
    "field,value",
    [
        ("mean", -0.1),
        ("mean", 1.1),
        ("variance", -1e-10),
        ("variance", 0.251),
        ("variance", float("nan")),
        ("ei", float("inf")),
        ("ei", -1e-10),
    ],
)
def test_model_policy_does_not_hide_invalid_moments_or_acquisition(field, value):
    values = {"mean": 0.5, "variance": 0.1, "ei": 0.2, field: value}
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_input_invalid"):
        _select([_row(1, {"x": 0.5}, **values)], policy=REFINE)


def test_flags_are_boolean_consistent_and_no_model_scores_are_required_for_space_filling():
    row = _row(1, {"x": 0.5})
    row["novel"] = False
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_input_invalid"):
        _select([row])
    row["novel"] = 1
    with pytest.raises(BayesianOptimizationError, match="bayesian_augmentation_input_invalid"):
        _select([row])
    assert _select([_row(1, {"x": 0.5})])["selected_row_ids"] == [row["row_id"]]


def test_model_free_selection_cannot_call_fit_or_prediction(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Augmentation must only compare the verified saved candidate rows")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    monkeypatch.setattr(
        "app.statistics.bo_planning_model.evaluate_surrogate_desirability", forbidden
    )
    assert _select([_row(1, {"x": 0.5})])["steps"][0]["score"] == pytest.approx(math.log(8))


def test_confirm_requires_moments_but_does_not_require_unused_ei():
    rows = [
        _row(1, {"x": 0.2}, mean=0.5, variance=1e-12),
        _row(2, {"x": 0.7}, mean=0.6, variance=2e-12),
    ]
    for row in rows:
        row["acquisition"] = None
    result = _select(rows, policy=CONFIRM, latent_incumbent=0.4, batch_size=2)
    assert result["selected_row_ids"] == [rows[1]["row_id"], rows[0]["row_id"]]
    assert result["steps"][1]["score"] == pytest.approx(1e-6)
    with pytest.raises(BayesianOptimizationError, match="input_invalid"):
        _select(rows, policy=REFINE)


def _response_context():
    return [
        {"response_id": "a", "normalization_scale": 2.0, "normalized_importance": 0.25},
        {"response_id": "b", "normalization_scale": 10.0, "normalized_importance": 0.75},
    ]


def _multimodel_rows():
    rows = [
        _row(1, {"x": 0.1}, mean=0.5, variance=0.01, ei=0.4),
        _row(2, {"x": 0.3}, mean=0.5, variance=0.16, ei=0.2),
        _row(3, {"x": 0.5}, mean=0.5, variance=0.01, ei=0.1),
        _row(4, {"x": 0.7}, mean=0.5, variance=0.09, ei=0.1),
        _row(5, {"x": 0.9}, mean=0.5, variance=0.04, ei=0.1),
    ]
    for row, sd_a, sd_b in zip(rows, (1, 1, 4, 2, 2), (1, 1, 30, 5, 20), strict=True):
        row["response_predictions"] = [
            {"response_id": "a", "latent_standard_deviation_raw": sd_a},
            {"response_id": "b", "latent_standard_deviation_raw": sd_b},
        ]
    return rows


def test_refine_v2_alternates_desirability_and_weighted_response_sd_hand_values():
    from app.statistics.bo_augmentation import REFINE_V2

    rows = _multimodel_rows()
    original = deepcopy(rows)
    result = _select(
        rows,
        policy=REFINE_V2,
        batch_size=5,
        source=_source(model=True),
        response_uncertainty_context=_response_context(),
    )
    assert result["selected_row_ids"] == [row["row_id"] for row in rows]
    assert [step["criterion"] for step in result["steps"]] == [
        "base_desirability_beta_ei",
        "base_desirability_standard_deviation",
        "base_response_normalized_latent_standard_deviation",
        "base_desirability_standard_deviation",
        "base_response_normalized_latent_standard_deviation",
    ]
    # Independent arithmetic: sqrt(.25*(4/2)^2 + .75*(30/10)^2).
    assert result["steps"][2]["score"] == pytest.approx(math.sqrt(7.75), rel=1e-14)
    assert result["steps"][4]["score"] == pytest.approx(math.sqrt(3.25), rel=1e-14)
    assert result["response_uncertainty"]["context"] == _response_context()
    assert result["response_uncertainty"]["variance_kind"] == "latent"
    assert "bayesian_refine_multimodel_sd_not_implemented" not in result["warnings"]
    assert "bayesian_refine_weighted_rms_schedule_product_policy" in result["warnings"]
    assert rows == original
    json.dumps(result, allow_nan=False)


def test_refine_v2_is_invariant_to_response_order_and_response_unit_scaling():
    from app.statistics.bo_augmentation import REFINE_V2

    rows, context = _multimodel_rows(), _response_context()
    expected = _select(
        rows,
        policy=REFINE_V2,
        batch_size=5,
        source=_source(model=True),
        response_uncertainty_context=context,
    )
    for row in rows:
        row["response_predictions"][0]["latent_standard_deviation_raw"] *= 1e6
        row["response_predictions"].reverse()
    context[0]["normalization_scale"] *= 1e6
    actual = _select(
        rows[::-1],
        policy=REFINE_V2,
        batch_size=5,
        source=_source(model=True),
        response_uncertainty_context=context[::-1],
    )
    assert actual["selected_row_ids"] == expected["selected_row_ids"]
    assert actual["steps"] == expected["steps"]


@pytest.mark.parametrize(
    "change",
    [
        lambda rows, context: context[0].update(normalization_scale=0),
        lambda rows, context: context[0].update(normalization_scale=True),
        lambda rows, context: context[0].update(normalized_importance=0),
        lambda rows, context: context[0].update(normalized_importance=0.5),
        lambda rows, context: context[0].update(response_id="b"),
        lambda rows, context: rows[0]["response_predictions"].pop(),
        lambda rows, context: rows[0]["response_predictions"][0].update(response_id="unknown"),
        lambda rows, context: rows[0]["response_predictions"][0].update(
            latent_standard_deviation_raw=float("inf")
        ),
        lambda rows, context: rows[0]["response_predictions"][0].update(
            latent_standard_deviation_raw=-1
        ),
    ],
)
def test_refine_v2_rejects_invalid_response_uncertainty_before_selection(change):
    from app.statistics.bo_augmentation import REFINE_V2

    rows, context = _multimodel_rows(), _response_context()
    change(rows, context)
    with pytest.raises(BayesianOptimizationError, match="input_invalid"):
        _select(
            rows, policy=REFINE_V2, source=_source(model=True), response_uncertainty_context=context
        )


def test_refine_v1_does_not_silently_accept_v2_uncertainty_configuration():
    with pytest.raises(BayesianOptimizationError, match="input_invalid"):
        _select(_multimodel_rows(), policy=REFINE, response_uncertainty_context=_response_context())


@pytest.mark.parametrize("multimodel", [False, True])
def test_typed_trace_round_trip_preserves_v1_and_exact_v2_context(multimodel):
    from app.api.v1.schemas.bo_augmentation import AugmentationTrace
    from app.statistics.bo_augmentation import REFINE_V2

    options = {"response_uncertainty_context": _response_context()} if multimodel else {}
    result = _select(
        _multimodel_rows(),
        policy=REFINE_V2 if multimodel else REFINE,
        source=_source(model=True),
        **options,
    )
    parsed = AugmentationTrace.model_validate(result)
    assert parsed.model_dump(mode="json", exclude_unset=True) == result
    if not multimodel:
        assert "response_uncertainty" not in result
    else:
        result.pop("response_uncertainty")
        with pytest.raises(ValueError, match="result_invalid"):
            AugmentationTrace.model_validate(result)


@pytest.mark.parametrize(
    "sd,scale,expected", [(0.0, 1.0, 0.0), (1e-300, 1e-300, 1.0), (1e300, 1e300, 1.0)]
)
def test_response_rms_retains_zero_and_extreme_representable_unit_ratios(sd, scale, expected):
    from app.statistics.bo_augmentation import REFINE_V2

    rows = _multimodel_rows()[:3]
    for row in rows:
        row["response_predictions"] = [{"response_id": "a", "latent_standard_deviation_raw": sd}]
    context = [{"response_id": "a", "normalization_scale": scale, "normalized_importance": 1.0}]
    result = _select(
        rows,
        policy=REFINE_V2,
        batch_size=3,
        source=_source(model=True),
        response_uncertainty_context=context,
    )
    assert result["steps"][2]["score"] == expected


@pytest.mark.parametrize("sd,scale", [(1e300, 1e-300), (1e-300, 1e300)])
def test_response_rms_rejects_unrepresentable_nonzero_ratio(sd, scale):
    from app.statistics.bo_augmentation import REFINE_V2

    rows = _multimodel_rows()[:1]
    rows[0]["response_predictions"] = [{"response_id": "a", "latent_standard_deviation_raw": sd}]
    with pytest.raises(ValueError, match="score_invalid"):
        _select(
            rows,
            policy=REFINE_V2,
            source=_source(model=True),
            response_uncertainty_context=[
                {"response_id": "a", "normalization_scale": scale, "normalized_importance": 1.0}
            ],
        )


def test_response_rms_uses_all_four_latent_models_not_measurement_uncertainty():
    from app.statistics.bo_augmentation import REFINE_V2

    rows = _multimodel_rows()[:3]
    context = []
    predictions = []
    for index, scale in enumerate((1.0, 10.0, 100.0, 1000.0), start=1):
        context.append(
            {
                "response_id": str(index),
                "normalization_scale": scale,
                "normalized_importance": index / 10,
            }
        )
        predictions.append(
            {
                "response_id": str(index),
                "latent_standard_deviation_raw": index * scale,
                "predictive_standard_deviation_raw": 1e10,
            }
        )
    for row in rows:
        row["response_predictions"] = deepcopy(predictions[::-1])
    result = _select(
        rows,
        policy=REFINE_V2,
        batch_size=3,
        source=_source(model=True),
        response_uncertainty_context=context,
    )
    # .1*1 + .2*4 + .3*9 + .4*16 = 10, irrespective of predictive noise.
    assert result["steps"][2]["score"] == pytest.approx(math.sqrt(10), rel=1e-14)
