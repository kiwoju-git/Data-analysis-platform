import copy
import csv
import io
import json
import sqlite3
from dataclasses import replace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.bo_mixed_studies import MixedStudyCreateRequest, mixed_factor_domains
from app.core.config import Settings
from app.core.errors import ApiError
from app.services import bayesian_studies as legacy
from app.services.bo_mixed_studies import (
    canonical_mixed_point,
    create_mixed_study,
    get_any_bayesian_study,
    get_mixed_study,
    load_validated_mixed_study,
    mixed_initial_design_csv,
    project_mixed_trial,
)
from app.storage.bayesian_studies import (
    complete_bayesian_trial_batch_records,
    get_bayesian_study_version_record,
)
from app.storage.metadata import initialize_metadata_store, metadata_db_path


def request():
    return {
        "schema_version": 7,
        "name": "Synthetic mixed study",
        "factors": [
            {
                "factor_id": "x",
                "name": "Numeric condition",
                "domain_kind": "discrete_numeric",
                "low": 1000.1,
                "high": 1000.3,
                "step": 0.1,
                "display_decimals": 1,
            },
            {
                "factor_id": "kind",
                "name": "Material",
                "domain_kind": "nominal",
                "levels": ["1", "한글", "=FORMULA()"],
                "correlation_policy": "equal_positive_correlation_v1",
            },
        ],
        "objective": {
            "name": "Synthetic response goal",
            "goal_type": "desirability",
            "observation_policy": "complete_response_vector",
            "curve_policy": "derringer_suich_linear_v1",
            "responses": [
                {
                    "response_id": "yield",
                    "name": "Yield",
                    "unit": "g",
                    "goal": "maximize",
                    "lower": 0.0,
                    "target": 10.0,
                    "upper": None,
                    "importance": 1.0,
                }
            ],
        },
        "initial_design_seed": 31,
        "initial_design_size": 8,
    }


@pytest.fixture
def settings(tmp_path):
    root = tmp_path / "mixed source 한글 workspace"
    initialize_metadata_store(root)
    return Settings(workspace_root=root)


def test_creation_exact_restore_and_catalog_share_existing_owner_tables(settings):
    raw = request()
    before = copy.deepcopy(raw)
    first = create_mixed_study(settings, MixedStudyCreateRequest.model_validate(raw))
    second = create_mixed_study(settings, MixedStudyCreateRequest.model_validate(raw))
    assert raw == before
    assert first.study_schema_version == 7 and first.observation_history.schema_version == 2
    assert first.definition_sha256 == second.definition_sha256
    assert first.study_id != second.study_id
    assert [item.actual_coordinates for item in first.trials] == [
        item.actual_coordinates for item in second.trials
    ]
    assert get_any_bayesian_study(settings, first.study_id) == first
    assert legacy.list_bayesian_studies(settings, offset=0, limit=10).total == 2
    assert all(
        item.response_values is None and item.objective_value is None for item in first.trials
    )
    assert first.recommendation_available is False
    assert first.recommendation_workflow == "fixed_candidate_mixed_planning_v1"
    assert "bayesian_optimization_history_incomplete" in first.recommendation_blockers
    assert first.factors[1].levels == raw["factors"][1]["levels"]
    assert all("normalized_coordinates" not in item.model_dump() for item in first.trials)
    assert any(item.encoded_coordinates["kind"] == 2 for item in first.trials)


def test_vector_storage_observations_keep_source_hash_and_history2(settings):
    created = create_mixed_study(settings, MixedStudyCreateRequest.model_validate(request()))
    bundle = load_validated_mixed_study(settings, str(created.study_id))
    original = get_bayesian_study_version_record(
        settings.workspace_root, study_id=str(created.study_id), version_number=1
    )
    stamp = legacy.utc_now()
    completed = [
        replace(
            trial,
            state="completed",
            closed_at=stamp,
            response_values_json=legacy._json_dumps({"yield": float(index)}),
        )
        for index, trial in enumerate(bundle.trials)
    ]
    next_history = legacy._new_history_record(
        study_version_id=bundle.version.study_version_id,
        definition_sha256=bundle.version.definition_sha256,
        revision_number=2,
        completed_trials=completed,
        previous_history_sha256=bundle.current_history.observation_history_sha256,
        created_at=stamp,
        schema_version=2,
    )
    observations = [(item.trial_id, json.loads(item.response_values_json)) for item in completed]
    result = complete_bayesian_trial_batch_records(
        settings.workspace_root,
        observations=observations,
        closed_at=stamp,
        expected_history_revision_id=bundle.current_history.history_revision_id,
        expected_history_sha256=bundle.current_history.observation_history_sha256,
        new_history=next_history,
    )
    assert result == "created"
    restored = get_mixed_study(settings, created.study_id)
    assert restored.surrogate_available
    assert restored.observation_history.schema_version == 2
    assert [item.response_values for item in restored.trials] == [
        {"yield": float(index)} for index in range(8)
    ]
    assert [item.coordinates_sha256 for item in restored.trials] == [
        item.coordinates_sha256 for item in created.trials
    ]
    assert (
        get_bayesian_study_version_record(
            settings.workspace_root, study_id=str(created.study_id), version_number=1
        )
        == original
    )


def test_csv_escapes_category_formula_without_mutating_stored_identity(settings):
    created = create_mixed_study(settings, MixedStudyCreateRequest.model_validate(request()))
    contents, name = mixed_initial_design_csv(settings, created.study_id)
    rows = list(csv.reader(io.StringIO(contents.decode("utf-8-sig"))))
    assert name.endswith(".csv") and len(rows) == 9
    assert any("'=FORMULA()" in row for row in rows)
    assert all("=FORMULA()" not in row for row in rows)
    assert any(
        item.actual_coordinates["kind"] == "=FORMULA()"
        for item in get_mixed_study(settings, created.study_id).trials
    )
    assert legacy.bayesian_initial_design_csv(settings, created.study_id) == (contents, name)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: body["factors"][1].update(levels=["a", "a"]),
        lambda body: body["factors"][1].update(levels=[1, 2]),
        lambda body: body["factors"][1].update(correlation_policy="arbitrary"),
        lambda body: body["factors"][1].update(correlation_policy="ordinal_monotone_latent_rbf_v1"),
        lambda body: body.update(initial_design_policy="latin_hypercube_random_cd_v1"),
        lambda body: body.update(
            constraints=[
                {
                    "constraint_id": "bad",
                    "name": "Bad",
                    "terms": [{"factor_id": "kind", "coefficient": 1.0}],
                    "relation": "less_than_or_equal",
                    "bound": 1.0,
                }
            ]
        ),
        lambda body: body.update(schema_version=6),
    ],
)
def test_schema_rejects_silent_numeric_category_or_lhs_coercion(mutate):
    raw = request()
    MixedStudyCreateRequest.model_validate(raw)
    mutate(raw)
    with pytest.raises(ValidationError):
        MixedStudyCreateRequest.model_validate(raw)


@pytest.mark.parametrize(
    "column,payload",
    [
        ("actual_coordinates_json", {"x": 1000.1, "kind": 1}),
        ("actual_coordinates_json", {"x": 1000.1, "kind": "unknown"}),
        ("normalized_coordinates_json", {"x": 0.0, "kind": 0.5}),
        ("normalized_coordinates_json", {"x": 0.0, "kind": 32}),
    ],
)
def test_source_reader_rejects_tampered_coordinates(settings, column, payload):
    created = create_mixed_study(settings, MixedStudyCreateRequest.model_validate(request()))
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        connection.execute(
            f"UPDATE bayesian_trials SET {column}=? WHERE trial_id=?",
            (json.dumps(payload), str(created.trials[0].trial_id)),
        )
    with pytest.raises(ApiError):
        get_mixed_study(settings, created.study_id)


def test_projection_is_typed_and_domain_aware_not_a_numeric_dictionary(settings):
    study = create_mixed_study(settings, MixedStudyCreateRequest.model_validate(request()))
    bundle = load_validated_mixed_study(settings, str(study.study_id))
    for stored, response in zip(bundle.trials, study.trials, strict=True):
        projection = project_mixed_trial(bundle, stored)
        assert projection.actual_coordinates == response.actual_coordinates
        assert projection.encoded_coordinates == response.encoded_coordinates
        assert isinstance(projection.actual_coordinates["kind"], str)
        assert projection.response_values is None
    assert (
        get_any_bayesian_study(settings, UUID(str(study.study_id))).definition_sha256
        == study.definition_sha256
    )


def test_projection_canonicalizes_only_validated_discrete_lattice_without_mutating_input():
    source = MixedStudyCreateRequest.model_validate(request())
    original = {"x": 1000.1 + 0.1, "kind": "1"}
    before = original.copy()
    actual, encoded = canonical_mixed_point(mixed_factor_domains(source.factors), original)
    assert original == before
    assert actual == {"x": 1000.2, "kind": "1"}
    assert encoded["kind"] == 0
    with pytest.raises(ValueError):
        canonical_mixed_point(mixed_factor_domains(source.factors), {"x": 1000.15, "kind": "1"})
