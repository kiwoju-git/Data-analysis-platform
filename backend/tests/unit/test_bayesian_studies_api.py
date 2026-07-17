import hashlib
import json
import sqlite3
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.bayesian import (
    MAX_COMPLETED_OBSERVATIONS,
    MAX_HISTORY_REVISIONS,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services.bayesian_studies import (
    _load_complete_history_records,
    _load_validated_study,
    _validate_histories,
    canonical_bayesian_observation_history_sha256,
)
from app.storage.bayesian_studies import (
    BayesianHistoryRevisionRecord,
    BayesianStudyVersionRecord,
    BayesianTrialRecord,
)
from app.storage.metadata import metadata_db_path


def _study_request(*, seed: int = 20260715, initial_design_size: int = 4) -> dict:
    return {
        "name": "bounded manual study",
        "factors": [
            {
                "factor_id": "temperature",
                "name": "Temperature",
                "low": 20.0,
                "high": 80.0,
                "unit": "C",
            },
            {
                "factor_id": "time",
                "name": "Time",
                "low": 1.0,
                "high": 5.0,
                "unit": "min",
            },
        ],
        "objective": {
            "name": "Yield",
            "unit": "%",
            "direction": "maximize",
            "observation_policy": "manual_single_observation",
        },
        "constraints": [
            {
                "constraint_id": "resource_limit",
                "name": "Resource limit",
                "terms": [
                    {"factor_id": "temperature", "coefficient": 1.0},
                    {"factor_id": "time", "coefficient": 2.0},
                ],
                "relation": "less_than_or_equal",
                "bound": 90.0,
            }
        ],
        "initial_design_seed": seed,
        "initial_design_size": initial_design_size,
    }


def _create_study(client: TestClient, **kwargs) -> dict:
    response = client.post("/api/v1/bayesian-studies", json=_study_request(**kwargs))
    assert response.status_code == 201
    return response.json()


def _canonical_sha256(payload: object) -> str:
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _complete_trial(
    client: TestClient,
    study: dict,
    trial_index: int,
    *,
    objective_value: float,
    expected_history_revision_id: str | None = None,
):
    trial = study["trials"][trial_index]
    return client.put(
        f"/api/v1/bayesian-studies/{study['study_id']}" f"/trials/{trial['trial_id']}/observation",
        json={
            "objective_value": objective_value,
            "expected_history_revision_id": expected_history_revision_id
            or study["observation_history"]["history_revision_id"],
        },
    )


def test_bayesian_study_create_restore_and_list_are_typed_and_deterministic(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        first = _create_study(client)
        second = _create_study(client)
        restored_response = client.get(f"/api/v1/bayesian-studies/{first['study_id']}")
        list_response = client.get("/api/v1/bayesian-studies?offset=0&limit=10")
        trials_response = client.get(
            f"/api/v1/bayesian-studies/{first['study_id']}/trials?offset=1&limit=2"
        )

    assert restored_response.status_code == 200
    assert restored_response.json() == first
    assert first["method_id"] == "doe.bayesian_optimization"
    assert first["method_version"] == METHOD_VERSIONS["doe.bayesian_optimization"]
    assert first["study_schema_version"] == 1
    assert first["initial_design"]["policy"] == ("sha256_counter_uniform_feasible_v1")
    assert first["initial_design"]["seed"] == 20260715
    assert first["trial_count"] == 4
    assert first["pending_trial_count"] == 4
    assert first["completed_trial_count"] == 0
    assert first["observation_history"]["revision_number"] == 1
    assert first["observation_history"]["completed_trial_ids"] == []
    assert first["surrogate_available"] is False
    assert first["recommendation_available"] is False
    assert len(first["definition_sha256"]) == 64

    first_coordinates = [item["actual_coordinates"] for item in first["trials"]]
    second_coordinates = [item["actual_coordinates"] for item in second["trials"]]
    assert first_coordinates == second_coordinates
    assert first["definition_sha256"] == second["definition_sha256"]
    assert [item["coordinates_sha256"] for item in first["trials"]] == [
        item["coordinates_sha256"] for item in second["trials"]
    ]
    for trial in first["trials"]:
        actual = trial["actual_coordinates"]
        normalized = trial["normalized_coordinates"]
        assert 20.0 <= actual["temperature"] <= 80.0
        assert 1.0 <= actual["time"] <= 5.0
        assert actual["temperature"] + 2.0 * actual["time"] <= 90.0 + 1e-10
        assert normalized["temperature"] == pytest.approx((actual["temperature"] - 20.0) / 60.0)
        assert normalized["time"] == pytest.approx((actual["time"] - 1.0) / 4.0)

    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 2
    assert len(listed["items"]) == 2
    assert listed["items"][0]["study_id"] == second["study_id"]
    assert trials_response.status_code == 200
    assert trials_response.json()["total"] == 4
    assert [item["trial_number"] for item in trials_response.json()["items"]] == [
        2,
        3,
    ]


def test_bayesian_v01_study_restores_without_relabeling_or_hash_reinterpretation(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client, initial_design_size=3)

        definition_payload = {
            "study_schema_version": 1,
            "method_id": "doe.bayesian_optimization",
            "method_version": "0.1.0",
            "factors": study["factors"],
            "objective": study["objective"],
            "constraints": study["constraints"],
            "initial_design": study["initial_design"],
        }
        definition_sha256 = _canonical_sha256(definition_payload)
        history_sha256 = _canonical_sha256(
            {
                "schema_version": 1,
                "definition_sha256": definition_sha256,
                "completed_observations": [],
            }
        )
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE bayesian_studies SET method_version = '0.1.0' WHERE study_id = ?",
                (study["study_id"],),
            )
            connection.execute(
                """
                UPDATE bayesian_study_versions SET definition_sha256 = ?
                WHERE study_version_id = ?
                """,
                (definition_sha256, study["study_version_id"]),
            )
            for trial in study["trials"]:
                coordinates_sha256 = _canonical_sha256(
                    {
                        "definition_sha256": definition_sha256,
                        "trial_number": trial["trial_number"],
                        "origin": "initial_design",
                        "actual_coordinates": trial["actual_coordinates"],
                        "normalized_coordinates": trial["normalized_coordinates"],
                    }
                )
                connection.execute(
                    "UPDATE bayesian_trials SET coordinates_sha256 = ? WHERE trial_id = ?",
                    (coordinates_sha256, trial["trial_id"]),
                )
            connection.execute(
                """
                UPDATE bayesian_observation_history_revisions
                SET observation_history_sha256 = ?
                WHERE history_revision_id = ?
                """,
                (
                    history_sha256,
                    study["observation_history"]["history_revision_id"],
                ),
            )

        restored_response = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")

    assert restored_response.status_code == 200
    restored = restored_response.json()
    assert restored["method_version"] == "0.1.0"
    assert restored["definition_sha256"] == definition_sha256
    assert restored["observation_history"]["observation_history_sha256"] == history_sha256
    assert restored["surrogate_available"] is False
    assert restored["recommendation_available"] is False


def test_bayesian_observations_append_immutable_ordered_history(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client)
        initial_history = study["observation_history"]

        first_response = _complete_trial(client, study, 2, objective_value=91.25)
        assert first_response.status_code == 200
        first_transition = first_response.json()
        first_history = first_transition["observation_history"]

        stale_response = _complete_trial(
            client,
            study,
            0,
            objective_value=89.5,
            expected_history_revision_id=initial_history["history_revision_id"],
        )
        duplicate_response = _complete_trial(
            client,
            study,
            2,
            objective_value=999.0,
            expected_history_revision_id=first_history["history_revision_id"],
        )
        second_response = _complete_trial(
            client,
            study,
            0,
            objective_value=89.5,
            expected_history_revision_id=first_history["history_revision_id"],
        )
        assert second_response.status_code == 200
        second_history = second_response.json()["observation_history"]
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        history_page = client.get(f"/api/v1/bayesian-studies/{study['study_id']}/history")
        old_history = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/history/{first_history['history_revision_id']}"
        )

    assert stale_response.status_code == 409
    assert stale_response.json()["error"]["code"] == "bayesian_observation_history_stale"
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "bayesian_trial_state_conflict"
    assert first_history["revision_number"] == 2
    assert first_history["previous_history_sha256"] == initial_history["observation_history_sha256"]
    assert second_history["revision_number"] == 3
    assert second_history["previous_history_sha256"] == first_history["observation_history_sha256"]
    assert second_history["completed_trial_count"] == 2
    # History IDs are ordered by trial_number even when trial 3 completes first.
    assert second_history["completed_trial_ids"] == [
        study["trials"][0]["trial_id"],
        study["trials"][2]["trial_id"],
    ]
    payload = restored.json()
    assert payload["completed_trial_count"] == 2
    assert payload["trials"][0]["objective_value"] == 89.5
    assert payload["trials"][2]["objective_value"] == 91.25
    assert history_page.status_code == 200
    assert [item["revision_number"] for item in history_page.json()["items"]] == [
        3,
        2,
        1,
    ]
    assert old_history.status_code == 200
    assert old_history.json() == first_history


def test_bayesian_trial_abandon_is_terminal_and_does_not_change_observation_history(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client, initial_design_size=4)
        trial = study["trials"][0]
        abandoned_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}" f"/trials/{trial['trial_id']}/abandon"
        )
        completed_response = _complete_trial(client, study, 0, objective_value=77.0)
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()

    assert abandoned_response.status_code == 200
    abandoned = abandoned_response.json()
    assert abandoned["trial"]["state"] == "abandoned"
    assert abandoned["trial"]["objective_value"] is None
    assert abandoned["observation_history"] == study["observation_history"]
    assert completed_response.status_code == 409
    assert completed_response.json()["error"]["code"] == "bayesian_trial_state_conflict"
    assert restored["abandoned_trial_count"] == 1
    assert restored["completed_trial_count"] == 0
    assert restored["observation_history"] == study["observation_history"]


def test_bayesian_initial_trial_abandon_cannot_strand_minimum_design(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client, initial_design_size=3)
        trial = study["trials"][0]
        response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}" f"/trials/{trial['trial_id']}/abandon"
        )
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == ("bayesian_trial_abandon_would_strand_study")
    assert restored["pending_trial_count"] == 3
    assert restored["abandoned_trial_count"] == 0
    assert restored["observation_history"] == study["observation_history"]
    public_error = json.dumps(response.json()["error"], ensure_ascii=False).lower()
    assert "objective" not in public_error
    assert str(tmp_path).lower() not in public_error


def test_bayesian_study_rejects_invalid_semantics_without_fallback(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    duplicate = _study_request()
    duplicate["factors"][1]["factor_id"] = "temperature"
    unknown_constraint = _study_request()
    unknown_constraint["constraints"][0]["terms"][0]["factor_id"] = "missing"
    infeasible = _study_request(initial_design_size=3)
    infeasible["constraints"] = [
        {
            "constraint_id": "impossible",
            "name": "Impossible",
            "terms": [{"factor_id": "temperature", "coefficient": 1.0}],
            "relation": "less_than_or_equal",
            "bound": 0.0,
        }
    ]
    with TestClient(create_app(settings)) as client:
        duplicate_response = client.post("/api/v1/bayesian-studies", json=duplicate)
        unknown_response = client.post("/api/v1/bayesian-studies", json=unknown_constraint)
        infeasible_response = client.post("/api/v1/bayesian-studies", json=infeasible)

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == ("bayesian_study_factor_space_invalid")
    assert unknown_response.status_code == 409
    assert unknown_response.json()["error"]["code"] == ("bayesian_study_constraint_invalid")
    assert infeasible_response.status_code == 409
    assert infeasible_response.json()["error"]["code"] == (
        "bayesian_study_initial_design_infeasible"
    )
    for response in (duplicate_response, unknown_response, infeasible_response):
        text = response.text.lower()
        assert "recommendation" not in text
        assert "traceback" not in text
        assert str(tmp_path).lower() not in text


def test_bayesian_restore_rejects_definition_trial_and_history_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        definition_study = _create_study(client, seed=1)
        trial_study = _create_study(client, seed=2)
        history_study = _create_study(client, seed=3)
        version_study = _create_study(client, seed=4)
        generator_study = _create_study(client, seed=5)
        completed_response = _complete_trial(client, history_study, 0, objective_value=42.5)
        assert completed_response.status_code == 200

        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
            connection.execute(
                "UPDATE bayesian_study_versions SET objective_json = ? WHERE study_id = ?",
                ('{"direction":"minimize"}', definition_study["study_id"]),
            )
            trial_id = trial_study["trials"][0]["trial_id"]
            connection.execute(
                "UPDATE bayesian_trials SET actual_coordinates_json = ? WHERE trial_id = ?",
                ('{"temperature":999,"time":2}', trial_id),
            )
            history_trial_id = history_study["trials"][0]["trial_id"]
            connection.execute(
                "UPDATE bayesian_trials SET objective_value = ? WHERE trial_id = ?",
                (999.0, history_trial_id),
            )
            connection.execute(
                "UPDATE bayesian_studies SET method_version = ? WHERE study_id = ?",
                ("9.9.9", version_study["study_id"]),
            )
            (
                generator_version_id,
                factors_json,
                objective_json,
                constraints_json,
                initial_design_json,
            ) = connection.execute(
                """
                SELECT study_version_id, factors_json, objective_json,
                       constraints_json, initial_design_json
                FROM bayesian_study_versions
                WHERE study_id = ?
                """,
                (generator_study["study_id"],),
            ).fetchone()
            initial_design = json.loads(initial_design_json)
            initial_design["seed"] = 999
            definition_payload = {
                "study_schema_version": 1,
                "method_id": "doe.bayesian_optimization",
                "method_version": METHOD_VERSIONS["doe.bayesian_optimization"],
                "factors": json.loads(factors_json),
                "objective": json.loads(objective_json),
                "constraints": json.loads(constraints_json),
                "initial_design": initial_design,
            }
            forged_definition_sha = _canonical_sha256(definition_payload)
            connection.execute(
                """
                UPDATE bayesian_study_versions
                SET initial_design_json = ?, definition_sha256 = ?
                WHERE study_id = ?
                """,
                (
                    json.dumps(
                        initial_design,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    forged_definition_sha,
                    generator_study["study_id"],
                ),
            )
            generator_trials = connection.execute(
                """
                SELECT trial_id, trial_number, origin,
                       actual_coordinates_json, normalized_coordinates_json
                FROM bayesian_trials
                WHERE study_version_id = ?
                """,
                (generator_version_id,),
            ).fetchall()
            for (
                generator_trial_id,
                trial_number,
                origin,
                actual_json,
                normalized_json,
            ) in generator_trials:
                forged_coordinates_sha = _canonical_sha256(
                    {
                        "definition_sha256": forged_definition_sha,
                        "trial_number": trial_number,
                        "origin": origin,
                        "actual_coordinates": json.loads(actual_json),
                        "normalized_coordinates": json.loads(normalized_json),
                    }
                )
                connection.execute(
                    "UPDATE bayesian_trials SET coordinates_sha256 = ? WHERE trial_id = ?",
                    (forged_coordinates_sha, generator_trial_id),
                )
            connection.commit()

        definition_response = client.get(f"/api/v1/bayesian-studies/{definition_study['study_id']}")
        trial_response = client.get(f"/api/v1/bayesian-studies/{trial_study['study_id']}")
        history_response = client.get(f"/api/v1/bayesian-studies/{history_study['study_id']}")
        version_response = client.get(f"/api/v1/bayesian-studies/{version_study['study_id']}")
        generator_response = client.get(f"/api/v1/bayesian-studies/{generator_study['study_id']}")

    assert definition_response.status_code == 409
    assert definition_response.json()["error"]["code"] in {
        "bayesian_study_metadata_invalid",
        "bayesian_study_artifact_mismatch",
    }
    assert trial_response.status_code == 409
    assert trial_response.json()["error"]["code"] == "bayesian_study_artifact_mismatch"
    assert history_response.status_code == 409
    assert history_response.json()["error"]["code"] == ("bayesian_study_artifact_mismatch")
    assert version_response.status_code == 409
    assert version_response.json()["error"]["code"] == "bayesian_study_metadata_invalid"
    assert generator_response.status_code == 409
    assert generator_response.json()["error"]["code"] == ("bayesian_study_artifact_mismatch")
    for response in (
        definition_response,
        trial_response,
        history_response,
        version_response,
        generator_response,
    ):
        public_error = response.json()["error"].copy()
        public_error.pop("correlation_id", None)
        text = json.dumps(public_error, ensure_ascii=False).lower()
        assert "traceback" not in text
        assert str(metadata_db_path(settings.workspace_root)).lower() not in text
        assert "999" not in text


def test_bayesian_history_checksum_depends_on_ordered_ids_coordinates_and_values(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client, initial_design_size=3)
        first = _complete_trial(client, study, 1, objective_value=20.0).json()
        current = first["observation_history"]
        second_response = _complete_trial(
            client,
            study,
            0,
            objective_value=10.0,
            expected_history_revision_id=current["history_revision_id"],
        )
        assert second_response.status_code == 200
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()

    completed = [item for item in restored["trials"] if item["state"] == "completed"]
    payload = {
        "schema_version": 1,
        "definition_sha256": restored["definition_sha256"],
        "completed_observations": [
            {
                "trial_id": item["trial_id"],
                "trial_number": item["trial_number"],
                "coordinates_sha256": item["coordinates_sha256"],
                "objective_value": item["objective_value"],
            }
            for item in completed
        ],
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert (
        hashlib.sha256(canonical).hexdigest()
        == restored["observation_history"]["observation_history_sha256"]
    )


def test_bayesian_missing_resources_return_stable_errors(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    missing_study_id = uuid4()
    with TestClient(create_app(settings)) as client:
        study_response = client.get(f"/api/v1/bayesian-studies/{missing_study_id}")
        study = _create_study(client, initial_design_size=3)
        trial_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}" f"/trials/{uuid4()}/abandon"
        )
        history_response = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/history/{uuid4()}"
        )

    assert study_response.status_code == 404
    assert study_response.json()["error"]["code"] == "bayesian_study_not_found"
    assert trial_response.status_code == 404
    assert trial_response.json()["error"]["code"] == "bayesian_trial_not_found"
    assert history_response.status_code == 404
    assert history_response.json()["error"]["code"] == ("bayesian_observation_history_not_found")


@pytest.mark.parametrize("factor_count", [1, 2, 6])
def test_bayesian_initial_design_minimum_matches_factor_count(
    tmp_path,
    factor_count: int,
) -> None:
    settings = Settings(workspace_root=tmp_path / str(factor_count))
    minimum = max(2, factor_count + 1)
    request = _study_request(initial_design_size=minimum)
    request["factors"] = [
        {
            "factor_id": f"x{index + 1}",
            "name": f"Input {index + 1}",
            "low": -1.0,
            "high": 1.0,
            "unit": None,
        }
        for index in range(factor_count)
    ]
    request["constraints"] = []
    too_small = {**request, "initial_design_size": minimum - 1}
    with TestClient(create_app(settings)) as client:
        rejected = client.post("/api/v1/bayesian-studies", json=too_small)
        accepted = client.post("/api/v1/bayesian-studies", json=request)

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "bayesian_study_initial_design_too_small"
    assert accepted.status_code == 201
    assert accepted.json()["initial_design"]["generated_size"] == minimum


@pytest.mark.parametrize("completed_count", [199, MAX_COMPLETED_OBSERVATIONS])
def test_bayesian_history_validation_accepts_completed_observation_boundary(
    completed_count: int,
) -> None:
    version, trials, histories = _history_boundary_records(completed_count)

    _validate_histories(version, trials, histories, histories[-1])

    assert len(histories) == completed_count + 1
    if completed_count == MAX_COMPLETED_OBSERVATIONS:
        assert len(histories) == MAX_HISTORY_REVISIONS


def test_bayesian_history_validation_rejects_observation_over_limit() -> None:
    version, trials, histories = _history_boundary_records(MAX_COMPLETED_OBSERVATIONS + 1)

    with pytest.raises(ApiError) as captured:
        _validate_histories(version, trials, histories, histories[-1])

    assert captured.value.code == "bayesian_study_artifact_mismatch"


def test_internal_history_loader_and_public_page_accept_201_revision_boundary(
    tmp_path,
    monkeypatch,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client, initial_design_size=3)
        bundle = _load_validated_study(settings, study["study_id"])
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            for revision_number in range(2, MAX_HISTORY_REVISIONS + 1):
                connection.execute(
                    """
                    INSERT INTO bayesian_observation_history_revisions (
                        history_revision_id, study_version_id, revision_number,
                        schema_version, completed_trial_ids_json,
                        completed_trial_count, observation_history_sha256,
                        previous_history_sha256, created_at
                    ) VALUES (?, ?, ?, 1, '[]', 0, ?, ?, ?);
                    """,
                    (
                        str(uuid4()),
                        study["study_version_id"],
                        revision_number,
                        f"{revision_number:064x}",
                        f"{revision_number - 1:064x}",
                        "2026-07-16T00:00:01Z",
                    ),
                )
        loaded = _load_complete_history_records(
            tmp_path,
            study["study_version_id"],
        )
        monkeypatch.setattr(
            "app.services.bayesian_studies._load_validated_study",
            lambda _settings, _study_id: replace(
                bundle,
                histories=loaded,
                current_history=loaded[-1],
            ),
        )
        page = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/history" "?offset=190&limit=100"
        )

        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                """
                INSERT INTO bayesian_observation_history_revisions (
                    history_revision_id, study_version_id, revision_number,
                    schema_version, completed_trial_ids_json,
                    completed_trial_count, observation_history_sha256,
                    previous_history_sha256, created_at
                ) VALUES (?, ?, 202, 1, '[]', 0, ?, ?, ?);
                """,
                (
                    str(uuid4()),
                    study["study_version_id"],
                    "f" * 64,
                    "e" * 64,
                    "2026-07-16T00:00:02Z",
                ),
            )
        with pytest.raises(ApiError) as over_limit:
            _load_complete_history_records(tmp_path, study["study_version_id"])

    assert len(loaded) == MAX_HISTORY_REVISIONS
    assert page.status_code == 200
    assert page.json()["total"] == MAX_HISTORY_REVISIONS
    assert len(page.json()["items"]) == 11
    assert page.json()["items"][0]["revision_number"] == 11
    assert page.json()["items"][-1]["revision_number"] == 1
    assert over_limit.value.code == "bayesian_study_artifact_mismatch"


def _history_boundary_records(
    completed_count: int,
) -> tuple[
    BayesianStudyVersionRecord,
    list[BayesianTrialRecord],
    list[BayesianHistoryRevisionRecord],
]:
    study_id = str(uuid4())
    study_version_id = str(uuid4())
    definition_sha256 = "d" * 64
    version = BayesianStudyVersionRecord(
        study_version_id=study_version_id,
        study_id=study_id,
        version_number=1,
        schema_version=1,
        factors_json="[]",
        objective_json="{}",
        constraints_json="[]",
        initial_design_json="{}",
        definition_sha256=definition_sha256,
        created_at="2026-07-16T00:00:00Z",
    )
    trials = [
        BayesianTrialRecord(
            trial_id=str(uuid4()),
            study_version_id=study_version_id,
            trial_number=index + 1,
            origin="initial_design" if index < 64 else "recommendation",
            state="completed",
            actual_coordinates_json=json.dumps({"x": index / max(1, completed_count)}),
            normalized_coordinates_json=json.dumps({"x": index / max(1, completed_count)}),
            coordinates_sha256=f"{index:064x}",
            objective_value=float(index),
            created_at="2026-07-16T00:00:00Z",
            closed_at="2026-07-16T00:00:01Z",
        )
        for index in range(completed_count)
    ]
    histories: list[BayesianHistoryRevisionRecord] = []
    previous_sha: str | None = None
    for completed_so_far in range(completed_count + 1):
        included = trials[:completed_so_far]
        history_sha = canonical_bayesian_observation_history_sha256(
            definition_sha256=definition_sha256,
            completed_trials=included,
        )
        histories.append(
            BayesianHistoryRevisionRecord(
                history_revision_id=str(uuid4()),
                study_version_id=study_version_id,
                revision_number=completed_so_far + 1,
                schema_version=1,
                completed_trial_ids_json=json.dumps(
                    [item.trial_id for item in included],
                    separators=(",", ":"),
                ),
                completed_trial_count=completed_so_far,
                observation_history_sha256=history_sha,
                previous_history_sha256=previous_sha,
                created_at="2026-07-16T00:00:01Z",
            )
        )
        previous_sha = history_sha
    return version, trials, histories
