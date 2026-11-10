"""Persist an exact automatic selection, separately from manual/conditional MC scoring."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bo_augmentation import (
    AugmentationCalculation,
    AugmentationSelectionRequest,
    AugmentationSelectionResponse,
)
from app.api.v1.schemas.bo_planning import CandidateRow
from app.core.config import Settings
from app.services.analysis_run_execution import utc_now
from app.services.bayesian_noise_recommendations import _error
from app.services.bayesian_studies import get_bayesian_study
from app.services.bo_augmentation_contract import validate_augmentation_binding
from app.services.bo_candidates_v2 import read_candidate_revision_v2
from app.services.bo_planning import (
    _current,
    _excluded,
    _not_found,
    _read_model,
    _read_revision,
    _run,
)
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.storage import bo_planning as storage
from app.storage.bayesian_studies import BayesianStorageConflict


def validate_saved_augmentation(
    study: Any,
    body: AugmentationSelectionRequest,
    calculation: AugmentationCalculation,
    rows: list[CandidateRow],
    snapshot: dict[str, Any] | None,
) -> None:
    validate_augmentation_binding(
        calculation.model_dump(mode="json", exclude_unset=True),
        request={
            **body.model_dump(mode="json"),
            "factors": snapshot["calculation_request"]["factors"]
            if snapshot is not None
            else [factor.model_dump(mode="json") for factor in study.factors],
        },
        snapshot=snapshot,
        rows=[row.model_dump(mode="json") for row in rows],
        existing_coordinates=[
            [trial.normalized_coordinates[factor.factor_id] for factor in study.factors]
            for trial in study.trials
            if trial.trial_number <= body.expected_trial_count
        ],
    )


def _source_candidate(
    settings: Settings, study: Any, revision_id: UUID
) -> tuple[dict[str, Any], list[CandidateRow], dict[str, Any], float]:
    stored = storage.get_candidate_revision(
        settings.workspace_root, str(revision_id), str(study.study_version_id)
    )
    if stored is None:
        raise _not_found()
    if stored["schema_version"] == 2:
        record, rows, body = read_candidate_revision_v2(settings, study, revision_id)
        return record, rows, record, body.duplicate_tolerance
    record, rows, old_body = _read_revision(settings, study, revision_id)
    source, snapshot, _ = _read_model(settings, study, old_body.model_id)
    return record, rows, source, snapshot["calculation_request"]["search"]["duplicate_tolerance"]


def _verify_binding(
    study: Any,
    candidate: dict[str, Any],
    source: dict[str, Any],
    tolerance: float,
    body: AugmentationSelectionRequest,
) -> None:
    if (
        str(body.expected_study_version_id) != str(study.study_version_id)
        or body.expected_definition_sha256 != study.definition_sha256
        or body.expected_definition_sha256 != source["definition_sha256"]
        or str(body.expected_history_revision_id) != source["source_history_revision_id"]
        or body.expected_history_sha256 != source["history_sha256"]
        or body.expected_trial_count != candidate["source_trial_count"]
        or body.expected_rows_sha256 != candidate["rows_sha256"]
        or body.duplicate_tolerance != tolerance
    ):
        raise _error("bayesian_candidate_source_changed")


def get_augmentation_selection(
    settings: Settings, study_id: UUID, selection_id: UUID
) -> AugmentationSelectionResponse:
    study = get_bayesian_study(settings, study_id)
    try:
        record = storage.get_planning_selection(
            settings.workspace_root, str(selection_id), str(study.study_version_id)
        )
        if record is None:
            raise _not_found()
        body = AugmentationSelectionRequest.model_validate_json(record["config_json"])
        calculation = AugmentationCalculation.model_validate_json(record["result_json"])
        candidate, rows, source, tolerance = _source_candidate(
            settings, study, body.candidate_revision_id
        )
        _verify_binding(study, candidate, source, tolerance, body)
        if (
            record["schema_version"] != 2
            or str(body.request_id) != record["request_id"]
            or str(body.candidate_revision_id) != record["candidate_revision_id"]
            or (None if body.model_id is None else str(body.model_id)) != record["model_id"]
            or storage.planning_json(body.model_dump(mode="json")) != record["config_json"]
            or storage.planning_json(calculation.model_dump(mode="json", exclude_unset=True))
            != record["result_json"]
            or calculation.augmentation.policy != body.policy
            or len(calculation.selected_rows) != body.batch_size
            or calculation.source_row_count != len(rows)
            or calculation.augmentation.source.model_dump(mode="json")
            != {
                "model_snapshot_id": None if body.model_id is None else str(body.model_id),
                "model_snapshot_sha256": body.expected_model_sha256,
                "candidate_revision_id": str(body.candidate_revision_id),
                "candidate_revision_sha256": body.expected_rows_sha256,
                "history_sha256": body.expected_history_sha256,
            }
        ):
            raise ValueError
        by_id = {row.row_id: row for row in rows}
        for row in calculation.selected_rows:
            original = by_id.get(row.row_id)
            if original is None or any(
                getattr(row, field) != getattr(original, field)
                for field in CandidateRow.model_fields
            ):
                raise ValueError
        snapshot = None
        if body.model_id is not None:
            model, snapshot, _ = _read_model(settings, study, body.model_id)
            if model["snapshot_sha256"] != body.expected_model_sha256 or any(
                model[key] != source[key]
                for key in ("definition_sha256", "history_sha256", "source_history_revision_id")
            ):
                raise ValueError
        validate_saved_augmentation(study, body, calculation, rows, snapshot)
        return AugmentationSelectionResponse(
            selection_id=selection_id,
            study_id=study_id,
            study_version_id=study.study_version_id,
            model_id=body.model_id,
            candidate_revision_id=body.candidate_revision_id,
            config_sha256=record["config_sha256"],
            result_sha256=record["result_sha256"],
            request=body,
            calculation=calculation,
            created_at=record["created_at"],
            source_is_current=_current(study, source, body.expected_trial_count),
            confirmed_batch_id=record["confirmed_batch_id"],
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    except (ValueError, KeyError, TypeError, AttributeError, BayesianOptimizationError):
        raise _error("bayesian_planning_artifact_invalid") from None


def create_augmentation_selection(
    settings: Settings, study_id: UUID, body: AugmentationSelectionRequest
) -> AugmentationSelectionResponse:
    study = get_bayesian_study(settings, study_id)
    if study.objective.goal_type != "desirability":
        raise _error("bayesian_planning_objective_unsupported")
    config = body.model_dump(mode="json")
    try:
        old = storage.find_planning_request(
            settings.workspace_root,
            str(study.study_version_id),
            str(body.request_id),
            kind="selection",
        )
        if old is not None:
            if old["schema_version"] != 2 or old["config_sha256"] != storage.planning_sha(config):
                raise _error("bayesian_planning_request_conflict")
            return get_augmentation_selection(settings, study_id, UUID(old["selection_id"]))
        candidate, rows, source, tolerance = _source_candidate(
            settings, study, body.candidate_revision_id
        )
        _verify_binding(study, candidate, source, tolerance, body)
        if not _current(study, source, body.expected_trial_count):
            raise _error("bayesian_candidate_source_changed")
        if any(trial.state == "pending" for trial in study.trials):
            raise _error("bayesian_optimization_pending_recommendation_exists")
        if len(study.trials) + body.batch_size > body.total_trial_budget:
            raise _error("bayesian_optimization_batch_budget_exceeded")
        snapshot = None
        if body.model_id is not None:
            model, snapshot, _ = _read_model(settings, study, body.model_id)
            if model["snapshot_sha256"] != body.expected_model_sha256 or any(
                model[key] != source[key]
                for key in ("definition_sha256", "history_sha256", "source_history_revision_id")
            ):
                raise _error("bayesian_planning_model_mismatch")
        raw = _run(
            "augmentation",
            {
                "factors": snapshot["calculation_request"]["factors"]
                if snapshot is not None
                else [factor.model_dump(mode="json") for factor in study.factors],
                "constraints": snapshot["calculation_request"]["constraints"]
                if snapshot is not None
                else [constraint.model_dump(mode="json") for constraint in study.constraints],
                "points": [row.input_coordinates for row in rows],
                "source_rows": [row.model_dump(mode="json") for row in rows],
                "existing_coordinates": [
                    [row[factor.factor_id] for factor in study.factors] for row in _excluded(study)
                ],
                "source": {
                    "model_snapshot_id": None if body.model_id is None else str(body.model_id),
                    "model_snapshot_sha256": body.expected_model_sha256,
                    "candidate_revision_id": str(body.candidate_revision_id),
                    "candidate_revision_sha256": body.expected_rows_sha256,
                    "history_sha256": body.expected_history_sha256,
                },
                "policy": body.policy,
                "batch_size": body.batch_size,
                "snapshot": snapshot,
                "duplicate_tolerance": body.duplicate_tolerance,
                "min_batch_distance_normalized": body.min_batch_distance_normalized,
                "max_evaluations": body.max_evaluations,
                "max_moment_evaluations": body.max_moment_evaluations,
                "time_budget_ms": body.time_budget_ms,
            },
            time_budget_ms=body.time_budget_ms,
        )
        result = AugmentationCalculation.model_validate(raw).model_dump(
            mode="json", exclude_unset=True
        )
        record = {
            "selection_id": str(uuid4()),
            "study_version_id": str(study.study_version_id),
            "model_id": None if body.model_id is None else str(body.model_id),
            "candidate_revision_id": str(body.candidate_revision_id),
            "request_id": str(body.request_id),
            "schema_version": 2,
            "config_json": storage.planning_json(config),
            "config_sha256": storage.planning_sha(config),
            "result_json": storage.planning_json(result),
            "result_sha256": storage.planning_sha(result),
            "created_at": utc_now(),
        }
        identity = storage.insert_planning_selection(settings.workspace_root, record)
        return get_augmentation_selection(settings, study_id, UUID(identity))
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
