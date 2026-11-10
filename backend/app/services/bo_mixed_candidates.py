"""Persistent mixed candidate rows; all mutation is source-CAS and explicit."""

import json
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bo_mixed_planning import MixedCandidateRow
from app.api.v1.schemas.bo_mixed_workflow import (
    MixedCandidateCreateRequest,
    MixedCandidateList,
    MixedCandidatePage,
    MixedCandidateSummary,
)
from app.core.config import Settings
from app.services.analysis_run_execution import utc_now
from app.services.bayesian_noise_recommendations import _error
from app.services.bo_mixed_models import calculation_factors, read_mixed_model, require_mixed_source
from app.services.bo_mixed_studies import get_mixed_study
from app.services.bo_planning import _current, _not_found, _run
from app.storage import bo_planning as storage
from app.storage.bayesian_studies import (
    BayesianStorageConflict,
    get_bayesian_history_revision_record,
)


def mixed_excluded(study: Any, count: int | None = None) -> list[dict[str, float]]:
    return [
        trial.encoded_coordinates
        for trial in study.trials
        if count is None or trial.trial_number <= count
    ]


def read_mixed_candidate(
    settings: Settings, study: Any, revision_id: UUID
) -> tuple[dict[str, Any], list[MixedCandidateRow], MixedCandidateCreateRequest]:
    try:
        record = storage.get_candidate_revision(
            settings.workspace_root, str(revision_id), str(study.study_version_id)
        )
        if record is None:
            raise _not_found()
        config = json.loads(record["config_json"])
        body = MixedCandidateCreateRequest.model_validate(config["request"])
        rows = [MixedCandidateRow.model_validate(row) for row in json.loads(record["rows_json"])]
        require_mixed_source(study, body, current=False)
        history = get_bayesian_history_revision_record(
            settings.workspace_root, str(body.expected_history_revision_id)
        )
        if (
            record["schema_version"] != 3
            or history is None
            or history.study_version_id != str(study.study_version_id)
            or history.observation_history_sha256 != body.expected_history_sha256
            or record["source_history_revision_id"] != history.history_revision_id
            or record["history_sha256"] != history.observation_history_sha256
            or record["definition_sha256"] != study.definition_sha256
            or set(config) != {"request", "generation"}
            or config["request"] != body.model_dump(mode="json")
            or storage.planning_json(config) != record["config_json"]
            or storage.planning_json([row.model_dump(mode="json") for row in rows])
            != record["rows_json"]
            or len(rows) != record["row_count"]
            or len({row.row_id for row in rows}) != len(rows)
            or [row.source_row_number for row in rows] != list(range(1, len(rows) + 1))
            or str(body.candidate_set_id) != record["candidate_set_id"]
            or (None if body.model_id is None else str(body.model_id)) != record["model_id"]
            or str(body.request_id) != record["request_id"]
            or (
                None
                if body.expected_head_revision_id is None
                else str(body.expected_head_revision_id)
            )
            != record["parent_revision_id"]
            or body.expected_trial_count != record["source_trial_count"]
            or storage.planning_sha(mixed_excluded(study, body.expected_trial_count))
            != record["excluded_coordinates_sha256"]
        ):
            raise ValueError
        if body.model_id is not None:
            model, snapshot, _ = read_mixed_model(settings, study, body.model_id)
            if (
                model["snapshot_sha256"] != body.expected_model_sha256
                or any(
                    model[key] != record[key]
                    for key in (
                        "source_history_revision_id",
                        "history_sha256",
                        "definition_sha256",
                    )
                )
                or snapshot["calculation_request"]["search"]["duplicate_tolerance"]
                != body.duplicate_tolerance
            ):
                raise ValueError
        return record, rows, body
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    except (ValueError, TypeError, KeyError, AttributeError):
        raise _error("bayesian_planning_artifact_invalid") from None


def list_mixed_candidates(settings: Settings, study_id: UUID) -> MixedCandidateList:
    study = get_mixed_study(settings, study_id)
    result = []
    for row in storage.list_candidate_sets(settings.workspace_root, str(study.study_version_id)):
        values = {
            key: row[key]
            for key in MixedCandidateSummary.model_fields
            if key != "source_is_current"
        }
        values["source_is_current"] = _current(study, row, row["source_trial_count"])
        result.append(MixedCandidateSummary.model_validate(values))
    return MixedCandidateList(items=result)


def mixed_candidate_page(
    settings: Settings, study_id: UUID, revision_id: UUID, *, offset: int = 0, limit: int = 50
) -> MixedCandidatePage:
    if (
        type(offset) is not int
        or not 0 <= offset <= 10000
        or type(limit) is not int
        or not 1 <= limit <= 100
    ):
        raise _error("bayesian_candidate_input_invalid")
    study = get_mixed_study(settings, study_id)
    record, rows, body = read_mixed_candidate(settings, study, revision_id)
    values = {
        key: record[key]
        for key in MixedCandidateSummary.model_fields
        if key
        not in {
            "name",
            "model_sha256",
            "eligible_count",
            "source_is_current",
            "duplicate_tolerance",
            "ordinal_rank_distance",
        }
    } | {
        "name": body.name,
        "model_sha256": body.expected_model_sha256,
        "eligible_count": sum(row.eligible for row in rows),
        "source_is_current": _current(study, record, body.expected_trial_count),
        "duplicate_tolerance": body.duplicate_tolerance,
        "ordinal_rank_distance": body.ordinal_rank_distance,
    }
    return MixedCandidatePage(
        revision=MixedCandidateSummary.model_validate(values),
        offset=offset,
        limit=limit,
        items=rows[offset : offset + limit],
    )


def create_mixed_candidate(
    settings: Settings, study_id: UUID, body: MixedCandidateCreateRequest
) -> MixedCandidatePage:
    study = get_mixed_study(settings, study_id)
    try:
        old = storage.find_planning_request(
            settings.workspace_root,
            str(study.study_version_id),
            str(body.request_id),
            kind="candidate",
        )
        if old is not None:
            if old["schema_version"] != 3 or json.loads(old["config_json"])[
                "request"
            ] != body.model_dump(mode="json"):
                raise _error("bayesian_planning_request_conflict")
            return mixed_candidate_page(settings, study_id, UUID(old["revision_id"]))
        require_mixed_source(study, body)
        source = {
            "study_version_id": str(study.study_version_id),
            "definition_sha256": study.definition_sha256,
            "source_history_revision_id": str(body.expected_history_revision_id),
            "history_sha256": body.expected_history_sha256,
        }
        if body.model_id is not None:
            model, snapshot, _ = read_mixed_model(settings, study, body.model_id)
            if (
                model["snapshot_sha256"] != body.expected_model_sha256
                or any(model[key] != value for key, value in source.items())
                or snapshot["calculation_request"]["search"]["duplicate_tolerance"]
                != body.duplicate_tolerance
            ):
                raise _error("bayesian_planning_model_mismatch")
        previous = None
        previous_rows: list[MixedCandidateRow] = []
        if body.expected_head_revision_id is not None:
            previous, previous_rows, _ = read_mixed_candidate(
                settings, study, body.expected_head_revision_id
            )
            if previous["candidate_set_id"] != str(body.candidate_set_id):
                raise _error("bayesian_candidate_revision_conflict")
        generation = body.source.model_dump(mode="json")
        if body.source.kind == "append_rows":
            generation = {
                "kind": "explicit_rows",
                "points": [*(row.input_coordinates for row in previous_rows), *body.source.points],
            }
        elif body.source.kind == "remove_rows":
            removed = set(body.source.row_ids)
            if len(removed) != len(body.source.row_ids) or not removed <= {
                row.row_id for row in previous_rows
            }:
                raise _error("bayesian_candidate_input_invalid")
            generation = {
                "kind": "explicit_rows",
                "points": [
                    row.input_coordinates for row in previous_rows if row.row_id not in removed
                ],
            }
        excluded = mixed_excluded(study)
        generated = _run(
            "mixed_candidates",
            {
                "source": generation,
                "factors": calculation_factors(study),
                "constraints": [row.model_dump(mode="json") for row in study.constraints],
                "excluded": [
                    [row[factor.factor_id] for factor in study.factors] for row in excluded
                ],
                "tolerance": body.duplicate_tolerance,
                "include_violations": body.include_constraint_violations,
                "ordinal_rank_distance": body.ordinal_rank_distance,
            },
        )
        rows = [
            MixedCandidateRow.model_validate(row).model_dump(mode="json")
            for row in generated["rows"]
        ]
        config = {"request": body.model_dump(mode="json"), "generation": generated["generation"]}
        record = {
            **source,
            "revision_id": str(uuid4()),
            "candidate_set_id": str(body.candidate_set_id),
            "model_id": None if body.model_id is None else str(body.model_id),
            "revision_number": 1 if previous is None else previous["revision_number"] + 1,
            "schema_version": 3,
            "request_id": str(body.request_id),
            "parent_revision_id": None if previous is None else previous["revision_id"],
            "source_trial_count": len(study.trials),
            "excluded_coordinates_sha256": storage.planning_sha(excluded),
            "config_json": storage.planning_json(config),
            "config_sha256": storage.planning_sha(config),
            "rows_json": storage.planning_json(rows),
            "rows_sha256": storage.planning_sha(rows),
            "row_count": len(rows),
            "created_at": utc_now(),
        }
        identity = storage.insert_candidate_revision(
            settings.workspace_root,
            record,
            name=body.name,
            expected_head=None if previous is None else previous["revision_id"],
        )
        return mixed_candidate_page(settings, study_id, UUID(identity))
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
