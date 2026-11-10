"""Immutable model-free candidate revisions with the same history/CAS ownership."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bo_candidates_v2 import (
    CandidatePageV2,
    CandidateRevisionCreateRequestV2,
    CandidateRevisionSummaryV2,
    CandidateSetListV2,
)
from app.api.v1.schemas.bo_planning import CandidateRevisionSummary, CandidateRow
from app.core.config import Settings
from app.services.analysis_run_execution import utc_now
from app.services.bayesian_noise_recommendations import _error
from app.services.bayesian_studies import get_bayesian_study
from app.services.bo_planning import _current, _excluded, _not_found, _read_model, _run
from app.storage import bo_planning as storage
from app.storage.bayesian_studies import (
    BayesianStorageConflict,
    get_bayesian_history_revision_record,
)


def list_candidate_sets_v2(settings: Settings, study_id: UUID) -> CandidateSetListV2:
    study = get_bayesian_study(settings, study_id)
    records = storage.list_candidate_sets(settings.workspace_root, str(study.study_version_id))
    items: list[CandidateRevisionSummary | CandidateRevisionSummaryV2] = []
    for record in records:
        contract = (
            CandidateRevisionSummary
            if record["schema_version"] == 1
            else CandidateRevisionSummaryV2
        )
        values = {key: record[key] for key in contract.model_fields if key != "source_is_current"}
        values["source_is_current"] = _current(study, record, record["source_trial_count"])
        items.append(contract.model_validate(values))
    return CandidateSetListV2(items=items)


def candidate_page_any(
    settings: Settings, study_id: UUID, revision_id: UUID, *, offset: int, limit: int
) -> Any:
    from app.services.bo_planning import candidate_page

    study = get_bayesian_study(settings, study_id)
    record = storage.get_candidate_revision(
        settings.workspace_root, str(revision_id), str(study.study_version_id)
    )
    if record is None:
        raise _not_found()
    reader = candidate_page_v2 if record["schema_version"] == 2 else candidate_page
    return reader(settings, study_id, revision_id, offset=offset, limit=limit)


def read_candidate_revision_v2(
    settings: Settings, study: Any, revision_id: UUID
) -> tuple[dict[str, Any], list[CandidateRow], CandidateRevisionCreateRequestV2]:
    try:
        record = storage.get_candidate_revision(
            settings.workspace_root, str(revision_id), str(study.study_version_id)
        )
        if record is None:
            raise _not_found()
        config = json.loads(record["config_json"])
        body = CandidateRevisionCreateRequestV2.model_validate(config["request"])
        rows = [CandidateRow.model_validate(row) for row in json.loads(record["rows_json"])]
        source = {
            "study_version_id": str(body.expected_study_version_id),
            "source_history_revision_id": str(body.expected_history_revision_id),
            "history_sha256": body.expected_history_sha256,
            "definition_sha256": body.expected_definition_sha256,
        }
        history = get_bayesian_history_revision_record(
            settings.workspace_root, source["source_history_revision_id"]
        )
        if (
            record["schema_version"] != 2
            or any(record[key] != value for key, value in source.items())
            or source["study_version_id"] != str(study.study_version_id)
            or source["definition_sha256"] != study.definition_sha256
            or history is None
            or history.study_version_id != source["study_version_id"]
            or history.observation_history_sha256 != source["history_sha256"]
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
            or body.expected_trial_count > len(study.trials)
        ):
            raise ValueError
        if body.model_id is not None:
            model, _, _ = _read_model(settings, study, body.model_id)
            if model["snapshot_sha256"] != body.expected_model_sha256 or any(
                model[key] != value for key, value in source.items()
            ):
                raise ValueError
        excluded = [
            trial.normalized_coordinates
            for trial in study.trials
            if trial.trial_number <= body.expected_trial_count
        ]
        if storage.planning_sha(excluded) != record["excluded_coordinates_sha256"]:
            raise ValueError
        return record, rows, body
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    except (ValueError, KeyError, TypeError, AttributeError):
        raise _error("bayesian_planning_artifact_invalid") from None


def candidate_page_v2(
    settings: Settings, study_id: UUID, revision_id: UUID, *, offset: int, limit: int
) -> CandidatePageV2:
    if (
        type(offset) is not int
        or not 0 <= offset <= 10000
        or type(limit) is not int
        or not 1 <= limit <= 100
    ):
        raise _error("bayesian_candidate_input_invalid")
    study = get_bayesian_study(settings, study_id)
    record, rows, body = read_candidate_revision_v2(settings, study, revision_id)
    return CandidatePageV2(
        revision=CandidateRevisionSummaryV2.model_validate(
            {
                **{
                    key: record[key]
                    for key in CandidateRevisionSummaryV2.model_fields
                    if key
                    not in {
                        "name",
                        "model_sha256",
                        "eligible_count",
                        "source_is_current",
                        "duplicate_tolerance",
                    }
                },
                "name": body.name,
                "duplicate_tolerance": body.duplicate_tolerance,
                "model_sha256": body.expected_model_sha256,
                "eligible_count": sum(row.eligible for row in rows),
                "source_is_current": _current(study, record, body.expected_trial_count),
            }
        ),
        offset=offset,
        limit=limit,
        items=rows[offset : offset + limit],
    )


def create_candidate_revision_v2(
    settings: Settings, study_id: UUID, body: CandidateRevisionCreateRequestV2
) -> CandidatePageV2:
    study = get_bayesian_study(settings, study_id)
    if study.objective.goal_type != "desirability":
        raise _error("bayesian_planning_objective_unsupported")
    try:
        old = storage.find_planning_request(
            settings.workspace_root,
            str(study.study_version_id),
            str(body.request_id),
            kind="candidate",
        )
        if old is not None:
            if old["schema_version"] != 2 or json.loads(old["config_json"])[
                "request"
            ] != body.model_dump(mode="json"):
                raise _error("bayesian_planning_request_conflict")
            return candidate_page_v2(
                settings, study_id, UUID(old["revision_id"]), offset=0, limit=50
            )
        source = {
            "study_version_id": str(body.expected_study_version_id),
            "source_history_revision_id": str(body.expected_history_revision_id),
            "history_sha256": body.expected_history_sha256,
            "definition_sha256": body.expected_definition_sha256,
        }
        if source["study_version_id"] != str(study.study_version_id) or not _current(
            study, source, body.expected_trial_count
        ):
            raise _error("bayesian_candidate_source_changed")
        if body.model_id is not None:
            model, snapshot, _ = _read_model(settings, study, body.model_id)
            if model["snapshot_sha256"] != body.expected_model_sha256 or any(
                model[key] != value for key, value in source.items()
            ):
                raise _error("bayesian_planning_model_mismatch")
            if (
                snapshot["calculation_request"]["search"]["duplicate_tolerance"]
                != body.duplicate_tolerance
            ):
                raise _error("bayesian_planning_model_mismatch")
        previous = None
        previous_rows: list[CandidateRow] = []
        if body.expected_head_revision_id is not None:
            from app.services.bo_planning import _read_revision

            previous_record = storage.get_candidate_revision(
                settings.workspace_root,
                str(body.expected_head_revision_id),
                str(study.study_version_id),
            )
            if previous_record is None:
                raise _not_found()
            reader = (
                read_candidate_revision_v2
                if previous_record["schema_version"] == 2
                else _read_revision
            )
            previous, previous_rows, _ = reader(settings, study, body.expected_head_revision_id)
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
        excluded = _excluded(study)
        generated = _run(
            "candidates",
            {
                "source": generation,
                "factors": [factor.model_dump(mode="json") for factor in study.factors],
                "constraints": [
                    constraint.model_dump(mode="json") for constraint in study.constraints
                ],
                "excluded": [
                    [row[factor.factor_id] for factor in study.factors] for row in excluded
                ],
                "tolerance": body.duplicate_tolerance,
                "include_violations": body.include_constraint_violations,
            },
        )
        rows = [
            CandidateRow.model_validate(row).model_dump(mode="json") for row in generated["rows"]
        ]
        config = {"request": body.model_dump(mode="json"), "generation": generated["generation"]}
        record = {
            **source,
            "revision_id": str(uuid4()),
            "candidate_set_id": str(body.candidate_set_id),
            "model_id": None if body.model_id is None else str(body.model_id),
            "revision_number": 1 if previous is None else previous["revision_number"] + 1,
            "schema_version": 2,
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
        return candidate_page_v2(settings, study_id, UUID(identity), offset=0, limit=50)
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
