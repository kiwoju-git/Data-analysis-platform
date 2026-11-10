"""Persistent candidate planning, exact-source restore and no-refit profiler views."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.api.v1.schemas import bo_planning as dto
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import utc_now
from app.services.bayesian_desirability_recommendations import (
    _calculation_request,
    _vector_observation,
)
from app.services.bayesian_noise_recommendations import _error
from app.services.bayesian_studies import get_bayesian_study
from app.services.bo_planning_worker import run_planning_operation
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.storage import bo_planning as storage
from app.storage.bayesian_studies import (
    BayesianStorageConflict,
    get_bayesian_history_revision_record,
)


def _run(operation: str, payload: dict[str, Any], *, time_budget_ms: int = 60000) -> Any:
    try:
        return run_planning_operation(operation, payload, time_budget_ms=time_budget_ms)
    except BayesianOptimizationError as exc:
        raise _error(exc.code) from exc


def _not_found() -> ApiError:
    return ApiError(
        code="bayesian_planning_not_found",
        message="The saved planning source was not found.",
        status_code=404,
    )


def _current(study: Any, record: dict[str, Any], count: int | None = None) -> bool:
    history = study.observation_history
    return bool(
        study.status == "active"
        and study.definition_sha256 == record["definition_sha256"]
        and str(history.history_revision_id) == record["source_history_revision_id"]
        and history.observation_history_sha256 == record["history_sha256"]
        and (count is None or len(study.trials) == count)
    )


def _read_model(
    settings: Settings,
    study: Any,
    model_id: UUID,
) -> tuple[dict[str, Any], dict[str, Any], dto.PlanningModelCreateRequest]:
    try:
        record = storage.get_planning_model(
            settings.workspace_root, str(model_id), str(study.study_version_id)
        )
        if record is None:
            raise _not_found()
        config = json.loads(record["config_json"])
        snapshot = json.loads(record["snapshot_json"])
        body = dto.PlanningModelCreateRequest.model_validate(config["request"])
        count = config["source_trial_count"]
        if (
            config
            != {
                "request": body.model_dump(mode="json"),
                "study_id": str(study.study_id),
                "study_version_id": str(study.study_version_id),
                "definition_sha256": study.definition_sha256,
                "source_trial_count": count,
            }
            or type(count) is not int
            or not 1 <= count <= len(study.trials)
        ):
            raise ValueError
        history = get_bayesian_history_revision_record(
            settings.workspace_root, record["source_history_revision_id"]
        )
        if history is None or (
            history.study_version_id != str(study.study_version_id)
            or history.schema_version != 2
            or history.observation_history_sha256 != record["history_sha256"]
            or str(body.fit.expected_history_revision_id) != history.history_revision_id
            or body.fit.expected_history_sha256 != history.observation_history_sha256
            or record["definition_sha256"] != study.definition_sha256
            or record["request_id"] != str(body.request_id)
            or storage.planning_json(config) != record["config_json"]
            or storage.planning_json(snapshot) != record["snapshot_json"]
        ):
            raise ValueError
        source_ids = json.loads(history.completed_trial_ids_json)
        trials = {str(trial.trial_id): trial for trial in study.trials}
        source_trials = [trials[key] for key in source_ids]
        if any(trial.trial_number > count for trial in source_trials):
            raise ValueError
        expected = _calculation_request(
            study.factors,
            study.objective,
            study.constraints,
            [_vector_observation(trial) for trial in source_trials],
            [trial.normalized_coordinates for trial in study.trials if trial.trial_number <= count],
            body.fit,
        ).worker_payload()
        if snapshot["calculation_request"] != expected:
            raise ValueError
        return record, snapshot, body
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    except (ValueError, KeyError, TypeError, AttributeError):
        raise _error("bayesian_planning_artifact_invalid") from None


def _summary(study: Any, record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in (
            "model_id",
            "study_version_id",
            "source_history_revision_id",
            "history_sha256",
            "definition_sha256",
            "snapshot_sha256",
            "config_sha256",
            "created_at",
        )
    } | {"study_id": study.study_id, "source_is_current": _current(study, record)}


def get_planning_model(
    settings: Settings, study_id: UUID, model_id: UUID
) -> dto.PlanningModelDetail:
    study = get_bayesian_study(settings, study_id)
    record, snapshot, body = _read_model(settings, study, model_id)
    try:
        return dto.PlanningModelDetail.model_validate(
            {
                **_summary(study, record),
                "fit": body.fit,
                "objective": snapshot["calculation_request"]["objective"],
                **{
                    key: snapshot[key]
                    for key in (
                        "response_models",
                        "incumbent",
                        "observation_view",
                        "warnings",
                    )
                },
            }
        )
    except (ValidationError, KeyError):
        raise _error("bayesian_planning_artifact_invalid") from None


def list_planning_models(settings: Settings, study_id: UUID) -> dto.PlanningModelList:
    study = get_bayesian_study(settings, study_id)
    records = storage.list_planning_models(settings.workspace_root, str(study.study_version_id))
    # List metadata is bounded. Full state validation occurs before evaluation.
    return dto.PlanningModelList(
        items=[
            dto.PlanningModelSummary.model_validate(_summary(study, record)) for record in records
        ]
    )


def create_planning_model(
    settings: Settings,
    study_id: UUID,
    body: dto.PlanningModelCreateRequest,
) -> dto.PlanningModelDetail:
    study = get_bayesian_study(settings, study_id)
    try:
        old = storage.find_planning_request(
            settings.workspace_root,
            str(study.study_version_id),
            str(body.request_id),
            kind="model",
        )
        if old is not None:
            if json.loads(old["config_json"])["request"] != body.model_dump(mode="json"):
                raise _error("bayesian_planning_request_conflict")
            return get_planning_model(settings, study_id, UUID(old["model_id"]))
        history = study.observation_history
        if study.status != "active":
            raise _error("bayesian_study_closed")
        if (
            body.fit.expected_history_revision_id != history.history_revision_id
            or body.fit.expected_history_sha256 != history.observation_history_sha256
        ):
            raise _error("bayesian_optimization_history_stale")
        completed = [trial for trial in study.trials if trial.state == "completed"]
        if len({storage.planning_json(trial.actual_coordinates) for trial in completed}) < (
            study.recommendation_minimum_completed_observations
        ):
            raise _error("bayesian_optimization_history_incomplete")
        # A fit consumes no trial budget and can inspect completed observations
        # while a real experiment is pending. Selection has its own lifecycle gate.
        request = _calculation_request(
            study.factors,
            study.objective,
            study.constraints,
            [_vector_observation(trial) for trial in completed],
            _excluded(study),
            body.fit,
        )
        config = {
            "request": body.model_dump(mode="json"),
            "study_id": str(study.study_id),
            "study_version_id": str(study.study_version_id),
            "definition_sha256": study.definition_sha256,
            "source_trial_count": len(study.trials),
        }
        snapshot = _run(
            "fit", request.worker_payload(), time_budget_ms=request.search.time_budget_ms
        )
        try:
            if snapshot["calculation_request"] != request.worker_payload() or set(snapshot) != {
                "schema_version",
                "policy",
                "calculation_request",
                "response_states",
                "response_models",
                "incumbent",
                "observation_view",
                "warnings",
                "fit_evaluations",
                "fit_elapsed_ms",
            }:
                raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
        except (BayesianOptimizationError, KeyError, TypeError):
            raise _error("bayesian_planning_snapshot_invalid") from None
        record = {
            "model_id": str(uuid4()),
            "study_version_id": str(study.study_version_id),
            "source_history_revision_id": str(body.fit.expected_history_revision_id),
            "definition_sha256": study.definition_sha256,
            "history_sha256": body.fit.expected_history_sha256,
            "schema_version": 1,
            "request_id": str(body.request_id),
            "config_json": storage.planning_json(config),
            "config_sha256": storage.planning_sha(config),
            "snapshot_json": storage.planning_json(snapshot),
            "snapshot_sha256": storage.planning_sha(snapshot),
            "created_at": utc_now(),
        }
        model_id = storage.insert_planning_model(settings.workspace_root, record)
        return get_planning_model(settings, study_id, UUID(model_id))
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc


def _require_source(study: Any, record: dict[str, Any], body: dto.PlanningSourceRequest) -> None:
    if (
        str(body.model_id) != record["model_id"]
        or body.expected_model_sha256 != record["snapshot_sha256"]
        or str(body.expected_history_revision_id) != record["source_history_revision_id"]
        or body.expected_history_sha256 != record["history_sha256"]
        or not _current(study, record, body.expected_trial_count)
    ):
        raise _error("bayesian_candidate_source_changed")


def _excluded(study: Any) -> list[dict[str, float]]:
    return [trial.normalized_coordinates for trial in study.trials]


def _read_revision(
    settings: Settings,
    study: Any,
    revision_id: UUID,
) -> tuple[dict[str, Any], list[dto.CandidateRow], dto.CandidateRevisionCreateRequest]:
    try:
        record = storage.get_candidate_revision(
            settings.workspace_root, str(revision_id), str(study.study_version_id)
        )
        if record is None:
            raise _not_found()
        config = json.loads(record["config_json"])
        body = dto.CandidateRevisionCreateRequest.model_validate(config["request"])
        rows = [dto.CandidateRow.model_validate(row) for row in json.loads(record["rows_json"])]
        if (
            config.keys() != {"request", "generation"}
            or storage.planning_json(config) != record["config_json"]
            or storage.planning_json([row.model_dump(mode="json") for row in rows])
            != record["rows_json"]
            or len(rows) != record["row_count"]
            or len({row.row_id for row in rows}) != len(rows)
            or [row.source_row_number for row in rows] != list(range(1, len(rows) + 1))
            or str(body.candidate_set_id) != record["candidate_set_id"]
            or str(body.model_id) != record["model_id"]
            or str(body.request_id) != record["request_id"]
            or (
                None
                if body.expected_head_revision_id is None
                else str(body.expected_head_revision_id)
            )
            != record["parent_revision_id"]
            or body.expected_trial_count != record["source_trial_count"]
        ):
            raise ValueError
        model, _, _ = _read_model(settings, study, body.model_id)
        if body.expected_model_sha256 != model["snapshot_sha256"] or (
            str(body.expected_history_revision_id) != model["source_history_revision_id"]
            or body.expected_history_sha256 != model["history_sha256"]
        ):
            raise ValueError
        excluded = [
            trial.normalized_coordinates
            for trial in study.trials
            if trial.trial_number <= record["source_trial_count"]
        ]
        if storage.planning_sha(excluded) != record["excluded_coordinates_sha256"]:
            raise ValueError
        return record, rows, body
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    except (ValueError, KeyError, TypeError, AttributeError):
        raise _error("bayesian_planning_artifact_invalid") from None


def _revision_summary(
    settings: Settings,
    study: Any,
    record: dict[str, Any],
    rows: list[dto.CandidateRow],
    body: dto.CandidateRevisionCreateRequest,
) -> dto.CandidateRevisionSummary:
    model, _, _ = _read_model(settings, study, body.model_id)
    return dto.CandidateRevisionSummary.model_validate(
        {
            **{
                key: record[key]
                for key in (
                    "candidate_set_id",
                    "revision_id",
                    "revision_number",
                    "parent_revision_id",
                    "model_id",
                    "rows_sha256",
                    "config_sha256",
                    "excluded_coordinates_sha256",
                    "source_trial_count",
                    "row_count",
                    "created_at",
                )
            },
            "name": body.name,
            "model_sha256": model["snapshot_sha256"],
            "eligible_count": sum(row.eligible for row in rows),
            "source_is_current": _current(study, model, body.expected_trial_count),
        }
    )


def candidate_page(
    settings: Settings,
    study_id: UUID,
    revision_id: UUID,
    *,
    offset: int,
    limit: int,
) -> dto.CandidatePage:
    if (
        type(offset) is not int
        or not 0 <= offset <= 10000
        or type(limit) is not int
        or not 1 <= limit <= 100
    ):
        raise _error("bayesian_candidate_input_invalid")
    study = get_bayesian_study(settings, study_id)
    record, rows, body = _read_revision(settings, study, revision_id)
    return dto.CandidatePage(
        revision=_revision_summary(settings, study, record, rows, body),
        offset=offset,
        limit=limit,
        items=rows[offset : offset + limit],
    )


def list_candidate_sets(settings: Settings, study_id: UUID) -> dto.CandidateSetList:
    study = get_bayesian_study(settings, study_id)
    records = storage.list_candidate_sets(settings.workspace_root, str(study.study_version_id))
    # Like the model/selection catalog, list metadata only. The exact revision
    # reader verifies payload hashes and ownership before any row is used.
    return dto.CandidateSetList(
        items=[
            dto.CandidateRevisionSummary.model_validate(
                {
                    **{
                        key: record[key]
                        for key in dto.CandidateRevisionSummary.model_fields
                        if key not in {"schema_version", "source_is_current"}
                    },
                    "source_is_current": _current(study, record, record["source_trial_count"]),
                }
            )
            for record in records
        ]
    )


def create_candidate_revision(
    settings: Settings,
    study_id: UUID,
    body: dto.CandidateRevisionCreateRequest,
) -> dto.CandidatePage:
    study = get_bayesian_study(settings, study_id)
    try:
        old = storage.find_planning_request(
            settings.workspace_root,
            str(study.study_version_id),
            str(body.request_id),
            kind="candidate",
        )
        if old is not None:
            if json.loads(old["config_json"])["request"] != body.model_dump(mode="json"):
                raise _error("bayesian_planning_request_conflict")
            return candidate_page(settings, study_id, UUID(old["revision_id"]), offset=0, limit=50)
        model, snapshot, _ = _read_model(settings, study, body.model_id)
        _require_source(study, model, body)
        previous = None
        previous_rows: list[dto.CandidateRow] = []
        if body.expected_head_revision_id is not None:
            previous, previous_rows, _ = _read_revision(
                settings, study, body.expected_head_revision_id
            )
            if previous["candidate_set_id"] != str(body.candidate_set_id):
                raise _error("bayesian_candidate_revision_conflict")
        request = snapshot["calculation_request"]
        excluded = _excluded(study)
        factor_ids = [factor["factor_id"] for factor in request["factors"]]
        source = body.source.model_dump(mode="json")
        if body.source.kind == "append_rows":
            source = {
                "kind": "explicit_rows",
                "points": [
                    *(row.input_coordinates for row in previous_rows),
                    *body.source.points,
                ],
            }
        elif body.source.kind == "remove_rows":
            removed = set(body.source.row_ids)
            if len(removed) != len(body.source.row_ids) or not removed <= {
                row.row_id for row in previous_rows
            }:
                raise _error("bayesian_candidate_input_invalid")
            source = {
                "kind": "explicit_rows",
                "points": [
                    row.input_coordinates for row in previous_rows if row.row_id not in removed
                ],
            }
        payload = {
            "source": source,
            "factors": request["factors"],
            "constraints": request["constraints"],
            "excluded": [[row[key] for key in factor_ids] for row in excluded],
            "tolerance": request["search"]["duplicate_tolerance"],
            "include_violations": body.include_constraint_violations,
        }
        generated = _run("candidates", payload)
        try:
            rows = [
                row.model_dump(mode="json")
                for row in [dto.CandidateRow.model_validate(item) for item in generated["rows"]]
            ]
        except (BayesianOptimizationError, ValidationError, KeyError, TypeError):
            raise _error("bayesian_planning_result_invalid") from None
        config = {"request": body.model_dump(mode="json"), "generation": generated["generation"]}
        record = {
            "revision_id": str(uuid4()),
            "candidate_set_id": str(body.candidate_set_id),
            "study_version_id": str(study.study_version_id),
            "model_id": str(body.model_id),
            "revision_number": 1 if previous is None else previous["revision_number"] + 1,
            "schema_version": 1,
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
        revision_id = storage.insert_candidate_revision(
            settings.workspace_root,
            record,
            name=body.name,
            expected_head=None if previous is None else str(previous["revision_id"]),
        )
        return candidate_page(settings, study_id, UUID(revision_id), offset=0, limit=50)
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc


def evaluate_planning_model(
    settings: Settings,
    study_id: UUID,
    model_id: UUID,
    body: dto.PlanningEvaluationRequest,
) -> dto.PlanningEvaluationResponse:
    study = get_bayesian_study(settings, study_id)
    record, snapshot, _ = _read_model(settings, study, model_id)
    if body.expected_model_sha256 != record["snapshot_sha256"]:
        raise _error("bayesian_planning_model_mismatch")
    excluded = _excluded(study)
    factor_ids = [factor.factor_id for factor in study.factors]
    rows = _run(
        "evaluate",
        {
            "snapshot": snapshot,
            "points": body.model_dump(mode="json")["points"],
            "time_budget_ms": body.time_budget_ms,
            "eligibility_excluded_normalized": [
                [row[key] for key in factor_ids] for row in excluded
            ],
        },
        time_budget_ms=body.time_budget_ms,
    )
    # Restored historical models remain inspectable, but never become current by viewing.
    current = get_bayesian_study(settings, study_id)
    try:
        verified = [dto.EvaluatedCandidateRow.model_validate(row) for row in rows]
    except (BayesianOptimizationError, ValidationError, KeyError):
        raise _error("bayesian_planning_result_invalid") from None
    return dto.PlanningEvaluationResponse(
        model_id=model_id,
        model_sha256=record["snapshot_sha256"],
        request_sha256=storage.planning_sha(body.model_dump(mode="json")),
        items=verified,
        source_is_current=_current(current, record),
        eligibility_source_trial_count=len(study.trials),
        eligibility_coordinates_sha256=storage.planning_sha(excluded),
        eligibility_is_current=_excluded(current) == excluded,
    )


def create_planning_selection(
    settings: Settings,
    study_id: UUID,
    body: dto.PlanningSelectionCreateRequest,
) -> dto.PlanningSelectionResponse:
    study = get_bayesian_study(settings, study_id)
    config = body.model_dump(mode="json")
    try:
        old = storage.find_planning_request(
            settings.workspace_root,
            str(study.study_version_id),
            str(body.request_id),
            kind="selection",
        )
        if old is not None:
            if old["config_sha256"] != storage.planning_sha(config):
                raise _error("bayesian_planning_request_conflict")
            return get_planning_selection(settings, study_id, UUID(old["selection_id"]))
        model, snapshot, _ = _read_model(settings, study, body.model_id)
        _require_source(study, model, body)
        candidate, rows, _ = _read_revision(settings, study, body.candidate_revision_id)
        if (
            candidate["model_id"] != str(body.model_id)
            or candidate["rows_sha256"] != body.expected_rows_sha256
            or candidate["source_trial_count"] != body.expected_trial_count
        ):
            raise _error("bayesian_candidate_source_changed")
        if any(trial.state == "pending" for trial in study.trials):
            raise _error("bayesian_optimization_pending_recommendation_exists")
        if len(study.trials) + len(body.row_ids) > body.total_trial_budget:
            raise _error("bayesian_optimization_batch_budget_exceeded")
        by_id = {row.row_id: row for row in rows}
        if any(key not in by_id or not by_id[key].eligible for key in body.row_ids):
            raise _error("bayesian_planning_selection_ineligible")
        result = _run(
            "selection",
            {
                "snapshot": snapshot,
                "points": [by_id[key].actual_coordinates for key in body.row_ids],
                "eligibility_excluded_normalized": [
                    [row[factor.factor_id] for factor in study.factors] for row in _excluded(study)
                ],
            },
        )
        try:
            result = dto.PlanningSelectionCalculation.model_validate(result).model_dump(mode="json")
        except (BayesianOptimizationError, ValidationError, KeyError):
            raise _error("bayesian_planning_result_invalid") from None
        # Preserve original candidate row identity/order provenance, not page-relative indices.
        for item, key in zip(result["items"], body.row_ids, strict=True):
            if item["row_id"] != key:
                raise _error("bayesian_planning_artifact_invalid")
            item["source_row_number"] = by_id[key].source_row_number
            item["input_coordinates"] = by_id[key].input_coordinates
        result = dto.PlanningSelectionCalculation.model_validate(result).model_dump(mode="json")
        record = {
            "selection_id": str(uuid4()),
            "study_version_id": str(study.study_version_id),
            "model_id": str(body.model_id),
            "candidate_revision_id": str(body.candidate_revision_id),
            "request_id": str(body.request_id),
            "schema_version": 1,
            "config_json": storage.planning_json(config),
            "config_sha256": storage.planning_sha(config),
            "result_json": storage.planning_json(result),
            "result_sha256": storage.planning_sha(result),
            "created_at": utc_now(),
        }
        selection_id = storage.insert_planning_selection(settings.workspace_root, record)
        return get_planning_selection(settings, study_id, UUID(selection_id))
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc


def get_planning_selection(
    settings: Settings,
    study_id: UUID,
    selection_id: UUID,
) -> dto.PlanningSelectionResponse:
    study = get_bayesian_study(settings, study_id)
    try:
        record = storage.get_planning_selection(
            settings.workspace_root, str(selection_id), str(study.study_version_id)
        )
        if record is None:
            raise _not_found()
        body = dto.PlanningSelectionCreateRequest.model_validate_json(record["config_json"])
        result = dto.PlanningSelectionCalculation.model_validate_json(record["result_json"])
        model, _, _ = _read_model(settings, study, body.model_id)
        candidate, rows, _ = _read_revision(settings, study, body.candidate_revision_id)
        by_id = {row.row_id: row for row in rows}
        if (
            str(body.model_id) != record["model_id"]
            or str(body.candidate_revision_id) != record["candidate_revision_id"]
            or str(body.request_id) != record["request_id"]
            or body.expected_model_sha256 != model["snapshot_sha256"]
            or body.expected_rows_sha256 != candidate["rows_sha256"]
            or str(body.expected_history_revision_id) != model["source_history_revision_id"]
            or body.expected_history_sha256 != model["history_sha256"]
            or body.expected_trial_count != candidate["source_trial_count"]
            or [item.row_id for item in result.items] != body.row_ids
            or storage.planning_json(body.model_dump(mode="json")) != record["config_json"]
            or storage.planning_json(result.model_dump(mode="json")) != record["result_json"]
            or any(
                item.row_id not in by_id
                or item.actual_coordinates != by_id[item.row_id].actual_coordinates
                or item.normalized_coordinates != by_id[item.row_id].normalized_coordinates
                or item.source_row_number != by_id[item.row_id].source_row_number
                for item in result.items
            )
        ):
            raise ValueError
        return dto.PlanningSelectionResponse(
            selection_id=selection_id,
            study_id=study_id,
            study_version_id=study.study_version_id,
            model_id=body.model_id,
            model_sha256=model["snapshot_sha256"],
            candidate_revision_id=body.candidate_revision_id,
            rows_sha256=candidate["rows_sha256"],
            config_sha256=record["config_sha256"],
            result_sha256=record["result_sha256"],
            request=body,
            calculation=result,
            created_at=record["created_at"],
            source_is_current=_current(study, model, body.expected_trial_count),
            confirmed_batch_id=record["confirmed_batch_id"],
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    except (ValueError, KeyError, TypeError, AttributeError):
        raise _error("bayesian_planning_artifact_invalid") from None


def list_planning_selections(settings: Settings, study_id: UUID) -> dto.PlanningSelectionList:
    study = get_bayesian_study(settings, study_id)
    rows = storage.list_planning_selection_summaries(
        settings.workspace_root, str(study.study_version_id)
    )
    return dto.PlanningSelectionList(
        items=[
            dto.PlanningSelectionSummary.model_validate(
                {
                    **{
                        key: row[key]
                        for key in dto.PlanningSelectionSummary.model_fields
                        if key not in {"study_id", "source_is_current"}
                    },
                    "study_id": study_id,
                    "source_is_current": _current(study, row, row["source_trial_count"]),
                }
            )
            for row in rows
        ]
    )
