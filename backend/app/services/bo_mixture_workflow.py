"""Source-owned mixture planning artifacts using the existing atomic BO stores."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bo_mixed_workflow import MixedEvaluationRequest, MixedModelCreateRequest
from app.api.v1.schemas.bo_mixture import (
    MixtureCandidateCreateRequest,
    MixtureEvaluatedRow,
    MixtureSelectionCalculation,
    MixtureSelectionCreateRequest,
)
from app.api.v1.schemas.bo_planning import PlanningConfirmRequest
from app.core.config import Settings
from app.services.analysis_run_execution import APP_VERSION, utc_now
from app.services.bayesian_noise_recommendations import _error
from app.services.bo_mixture_studies import (
    METHOD_VERSION,
    MixtureValidatedStudy,
    load_validated_mixture_study,
    mixture_trial_response,
    new_mixture_trial_record,
)
from app.services.bo_planning import _run
from app.storage import bayesian_studies as studies
from app.storage import bo_planning as storage


def _source(bundle: MixtureValidatedStudy, body: Any, *, current: bool = True) -> None:
    if (
        str(body.expected_study_version_id) != bundle.version.study_version_id
        or body.expected_definition_sha256 != bundle.version.definition_sha256
        or body.expected_trial_count > len(bundle.trials)
    ):
        raise _error("bayesian_candidate_source_changed")
    if current and (
        str(body.expected_history_revision_id) != bundle.current_history.history_revision_id
        or body.expected_history_sha256 != bundle.current_history.observation_history_sha256
        or body.expected_trial_count != len(bundle.trials)
    ):
        raise _error("bayesian_optimization_history_stale")
    if current and bundle.study.status != "active":
        raise _error("bayesian_study_closed")


def _calculation(bundle: MixtureValidatedStudy, body: MixedModelCreateRequest) -> dict[str, Any]:
    history = next(
        (
            h
            for h in bundle.histories
            if h.history_revision_id == str(body.expected_history_revision_id)
        ),
        None,
    )
    if history is None or history.observation_history_sha256 != body.expected_history_sha256:
        raise _error("bayesian_planning_artifact_invalid")
    by_id = {t.trial_id: t for t in bundle.trials}
    rows = []
    for key in json.loads(history.completed_trial_ids_json):
        trial = by_id[key]
        projected = mixture_trial_response(bundle, trial)
        if trial.state != "completed" or trial.trial_number > body.expected_trial_count:
            raise _error("bayesian_planning_artifact_invalid")
        rows.append(
            {
                "trial_id": key,
                "actual_coordinates": projected.actual_coordinates,
                "response_values": projected.response_values,
            }
        )
    return {
        "design_domain": bundle.design.payload(),
        "objective": bundle.objective.model_dump(mode="json"),
        "fit": body.fit.model_dump(mode="json"),
        "observations": rows,
    }


def read_mixture_model(
    settings: Settings, bundle: MixtureValidatedStudy, model_id: UUID
) -> tuple[dict[str, Any], dict[str, Any], MixedModelCreateRequest]:
    record = storage.get_planning_model(
        settings.workspace_root, str(model_id), bundle.version.study_version_id
    )
    try:
        if record is None or record["schema_version"] != 2:
            raise ValueError
        body = MixedModelCreateRequest.model_validate_json(record["config_json"])
        snapshot = json.loads(record["snapshot_json"])
        _source(bundle, body, current=False)
        storage._documents(
            record, (("config_json", "config_sha256"), ("snapshot_json", "snapshot_sha256"))
        )
        if (
            record["request_id"] != str(body.request_id)
            or record["config_json"] != storage.planning_json(body.model_dump(mode="json"))
            or record["definition_sha256"] != bundle.version.definition_sha256
            or record["history_sha256"] != body.expected_history_sha256
            or record["source_history_revision_id"] != str(body.expected_history_revision_id)
            or snapshot["schema_version"] != 3
            or snapshot["policy"] != "source_locked_mixture_bo_planning_model_v1"
            or snapshot["calculation_request"] != _calculation(bundle, body)
            or snapshot["design_domain"] != bundle.design.payload()
        ):
            raise ValueError
        return record, snapshot, body
    except (ValueError, TypeError, KeyError, studies.BayesianStorageConflict):
        raise _error("bayesian_planning_artifact_invalid") from None


def _model_view(
    bundle: MixtureValidatedStudy,
    record: dict[str, Any],
    snapshot: dict[str, Any],
    body: MixedModelCreateRequest,
) -> dict[str, Any]:
    return {
        "schema_version": 3,
        "model_id": record["model_id"],
        "study_id": bundle.study.study_id,
        "study_version_id": bundle.version.study_version_id,
        "source_history_revision_id": record["source_history_revision_id"],
        "definition_sha256": record["definition_sha256"],
        "history_sha256": record["history_sha256"],
        "snapshot_sha256": record["snapshot_sha256"],
        "config_sha256": record["config_sha256"],
        "created_at": record["created_at"],
        "source_is_current": record["history_sha256"]
        == bundle.current_history.observation_history_sha256
        and body.expected_trial_count == len(bundle.trials),
        "fit": body.fit.model_dump(mode="json"),
        "objective": bundle.objective.model_dump(mode="json"),
        "design_domain": snapshot["design_domain"],
        "response_models": snapshot["response_models"],
        "incumbent": snapshot["incumbent"],
        "warnings": snapshot["warnings"],
        "model_reusable_without_refit": True,
    }


def get_mixture_model(settings: Settings, study_id: UUID, model_id: UUID) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    return _model_view(bundle, *read_mixture_model(settings, bundle, model_id))


def list_mixture_models(settings: Settings, study_id: UUID) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    return {
        "items": [
            _model_view(bundle, *read_mixture_model(settings, bundle, UUID(row["model_id"])))
            for row in storage.list_planning_models(
                settings.workspace_root, bundle.version.study_version_id
            )
        ]
    }


def create_mixture_model(
    settings: Settings, study_id: UUID, body: MixedModelCreateRequest
) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    config = body.model_dump(mode="json")
    old = storage.find_planning_request(
        settings.workspace_root, bundle.version.study_version_id, str(body.request_id), kind="model"
    )
    if old is not None:
        if old["config_sha256"] != storage.planning_sha(config):
            raise _error("bayesian_planning_request_conflict")
        return get_mixture_model(settings, study_id, UUID(old["model_id"]))
    _source(bundle, body)
    calculation = _calculation(bundle, body)
    snapshot = _run("mixture_fit", calculation, time_budget_ms=body.fit.search.time_budget_ms)
    record = {
        "model_id": str(uuid4()),
        "study_version_id": bundle.version.study_version_id,
        "source_history_revision_id": str(body.expected_history_revision_id),
        "definition_sha256": bundle.version.definition_sha256,
        "history_sha256": body.expected_history_sha256,
        "schema_version": 2,
        "request_id": str(body.request_id),
        "config_json": storage.planning_json(config),
        "config_sha256": storage.planning_sha(config),
        "snapshot_json": storage.planning_json(snapshot),
        "snapshot_sha256": storage.planning_sha(snapshot),
        "created_at": utc_now(),
    }
    try:
        identity = storage.insert_planning_model(settings.workspace_root, record)
    except studies.BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    return get_mixture_model(settings, study_id, UUID(identity))


def evaluate_mixture_model(
    settings: Settings, study_id: UUID, model_id: UUID, body: MixedEvaluationRequest
) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    record, snapshot, config = read_mixture_model(settings, bundle, model_id)
    if record["snapshot_sha256"] != body.expected_model_sha256:
        raise _error("bayesian_planning_model_mismatch")
    payload = {
        "snapshot": snapshot,
        "points": body.points,
        "time_budget_ms": body.time_budget_ms,
        "max_moment_evaluations": body.max_moment_evaluations,
        "excluded_actual": [json.loads(t.actual_coordinates_json) for t in bundle.trials],
    }
    rows = _run("mixture_evaluate", payload, time_budget_ms=body.time_budget_ms)
    return {
        "model_id": str(model_id),
        "snapshot_sha256": record["snapshot_sha256"],
        "items": rows,
        "eligibility_history_sha256": bundle.current_history.observation_history_sha256,
        "eligibility_is_current": config.expected_history_sha256
        == bundle.current_history.observation_history_sha256
        and config.expected_trial_count == len(bundle.trials),
    }


def create_mixture_candidate(
    settings: Settings, study_id: UUID, body: MixtureCandidateCreateRequest
) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    config = body.model_dump(mode="json")
    old = storage.find_planning_request(
        settings.workspace_root,
        bundle.version.study_version_id,
        str(body.request_id),
        kind="candidate",
    )
    if old is not None:
        if old["config_sha256"] != storage.planning_sha(config):
            raise _error("bayesian_planning_request_conflict")
        return get_mixture_candidate(settings, study_id, UUID(old["revision_id"]))
    _source(bundle, body)
    model, snapshot, _ = read_mixture_model(settings, bundle, body.model_id)
    if (
        model["snapshot_sha256"] != body.expected_model_sha256
        or model["history_sha256"] != body.expected_history_sha256
    ):
        raise _error("bayesian_planning_model_mismatch")
    result = _run(
        "mixture_candidates",
        {
            "snapshot": snapshot,
            "source": body.source.model_dump(mode="json"),
            "excluded_actual": [json.loads(t.actual_coordinates_json) for t in bundle.trials],
            "time_budget_ms": body.time_budget_ms,
            "max_moment_evaluations": body.max_moment_evaluations,
        },
        time_budget_ms=body.time_budget_ms,
    )
    parent = (
        None
        if body.expected_head_revision_id is None
        else storage.get_candidate_revision(
            settings.workspace_root,
            str(body.expected_head_revision_id),
            bundle.version.study_version_id,
        )
    )
    if body.expected_head_revision_id is not None and parent is None:
        raise _error("bayesian_candidate_revision_conflict")
    record = {
        "revision_id": str(uuid4()),
        "candidate_set_id": str(body.candidate_set_id),
        "study_version_id": bundle.version.study_version_id,
        "model_id": str(body.model_id),
        "revision_number": 1 if parent is None else parent["revision_number"] + 1,
        "schema_version": 4,
        "request_id": str(body.request_id),
        "parent_revision_id": None if parent is None else parent["revision_id"],
        "source_trial_count": len(bundle.trials),
        "excluded_coordinates_sha256": storage.planning_sha(
            [json.loads(t.actual_coordinates_json) for t in bundle.trials]
        ),
        "config_json": storage.planning_json(config),
        "config_sha256": storage.planning_sha(config),
        "rows_json": storage.planning_json(result),
        "rows_sha256": storage.planning_sha(result),
        "row_count": len(result["items"]),
        "created_at": utc_now(),
        "source_history_revision_id": str(body.expected_history_revision_id),
        "history_sha256": body.expected_history_sha256,
        "definition_sha256": bundle.version.definition_sha256,
    }
    try:
        identity = storage.insert_candidate_revision(
            settings.workspace_root,
            record,
            name=body.name,
            expected_head=None if parent is None else parent["revision_id"],
        )
    except studies.BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    return get_mixture_candidate(settings, study_id, UUID(identity))


def read_mixture_candidate(
    settings: Settings, bundle: MixtureValidatedStudy, revision_id: UUID
) -> tuple[dict[str, Any], dict[str, Any], MixtureCandidateCreateRequest]:
    row = storage.get_candidate_revision(
        settings.workspace_root, str(revision_id), bundle.version.study_version_id
    )
    try:
        if row is None or row["schema_version"] != 4:
            raise ValueError
        storage._documents(row, (("config_json", "config_sha256"), ("rows_json", "rows_sha256")))
        config = MixtureCandidateCreateRequest.model_validate_json(row["config_json"])
        model, _, _ = read_mixture_model(settings, bundle, config.model_id)
        result = json.loads(row["rows_json"])
        if type(result) is not dict or set(result) != {"generation", "items"}:
            raise ValueError
        typed_rows = [MixtureEvaluatedRow.model_validate(item) for item in result["items"]]
        if [item.model_dump(mode="json") for item in typed_rows] != result["items"]:
            raise ValueError
        if (
            row["model_id"] != str(config.model_id)
            or config.expected_model_sha256 != model["snapshot_sha256"]
            or row["history_sha256"] != config.expected_history_sha256
            or row["source_history_revision_id"] != str(config.expected_history_revision_id)
            or row["definition_sha256"] != bundle.version.definition_sha256
            or row["row_count"] != len(result["items"])
            or row["source_trial_count"] != config.expected_trial_count
            or row["config_json"] != storage.planning_json(config.model_dump(mode="json"))
        ):
            raise ValueError
        excluded = [
            json.loads(t.actual_coordinates_json)
            for t in bundle.trials
            if t.trial_number <= row["source_trial_count"]
        ]
        if row["excluded_coordinates_sha256"] != storage.planning_sha(excluded):
            raise ValueError
        for item in result["items"]:
            actual, encoded = bundle.design.canonical(item["input_coordinates"])
            if (
                actual != item["actual_coordinates"]
                or dict(zip(bundle.design.keys, encoded, strict=True))
                != item["encoded_coordinates"]
                or item["row_id"] != storage.planning_sha(actual)
            ):
                raise ValueError
        return row, result, config
    except (ValueError, TypeError, KeyError, studies.BayesianStorageConflict):
        raise _error("bayesian_planning_artifact_invalid") from None


def get_mixture_candidate(
    settings: Settings, study_id: UUID, revision_id: UUID, *, offset: int = 0, limit: int = 50
) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    row, result, body = read_mixture_candidate(settings, bundle, revision_id)
    return {
        "revision": {k: v for k, v in row.items() if k not in {"config_json", "rows_json"}},
        "generation": result["generation"],
        "source_is_current": body.expected_history_sha256
        == bundle.current_history.observation_history_sha256
        and body.expected_trial_count == len(bundle.trials),
        "offset": offset,
        "limit": limit,
        "items": result["items"][offset : offset + limit],
    }


def create_mixture_selection(
    settings: Settings, study_id: UUID, body: MixtureSelectionCreateRequest
) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    config = body.model_dump(mode="json")
    old = storage.find_planning_request(
        settings.workspace_root,
        bundle.version.study_version_id,
        str(body.request_id),
        kind="selection",
    )
    if old is not None:
        if old["config_sha256"] != storage.planning_sha(config):
            raise _error("bayesian_planning_request_conflict")
        return get_mixture_selection(settings, study_id, UUID(old["selection_id"]))
    _source(bundle, body)
    if any(t.state == "pending" for t in bundle.trials):
        raise _error("bayesian_optimization_pending_recommendation_exists")
    if len(bundle.trials) + body.batch_size > body.total_trial_budget:
        raise _error("bayesian_optimization_budget_exhausted")
    candidate, rows, _ = read_mixture_candidate(settings, bundle, body.candidate_revision_id)
    model, snapshot, _ = read_mixture_model(settings, bundle, body.model_id)
    if (
        candidate["rows_sha256"] != body.expected_rows_sha256
        or candidate["model_id"] != str(body.model_id)
        or model["snapshot_sha256"] != body.expected_model_sha256
        or candidate["source_trial_count"] != len(bundle.trials)
    ):
        raise _error("bayesian_candidate_source_changed")
    payload = {
        "snapshot": snapshot,
        "rows": rows["items"],
        "config": config,
        "excluded_actual": [json.loads(t.actual_coordinates_json) for t in bundle.trials],
    }
    result = _run("mixture_selection", payload, time_budget_ms=body.time_budget_ms)
    record = {
        "selection_id": str(uuid4()),
        "study_version_id": bundle.version.study_version_id,
        "model_id": str(body.model_id),
        "candidate_revision_id": str(body.candidate_revision_id),
        "request_id": str(body.request_id),
        "schema_version": 6,
        "config_json": storage.planning_json(config),
        "config_sha256": storage.planning_sha(config),
        "result_json": storage.planning_json(result),
        "result_sha256": storage.planning_sha(result),
        "created_at": utc_now(),
    }
    try:
        identity = storage.insert_planning_selection(settings.workspace_root, record)
    except studies.BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    return get_mixture_selection(settings, study_id, UUID(identity))


def read_mixture_selection(
    settings: Settings, bundle: MixtureValidatedStudy, selection_id: UUID
) -> tuple[dict[str, Any], dict[str, Any], MixtureSelectionCreateRequest]:
    row = storage.get_planning_selection(
        settings.workspace_root, str(selection_id), bundle.version.study_version_id
    )
    try:
        if row is None or row["schema_version"] != 6:
            raise ValueError
        storage._documents(
            row, (("config_json", "config_sha256"), ("result_json", "result_sha256"))
        )
        config = MixtureSelectionCreateRequest.model_validate_json(row["config_json"])
        candidate, candidate_result, _ = read_mixture_candidate(
            settings, bundle, config.candidate_revision_id
        )
        model, _, _ = read_mixture_model(settings, bundle, config.model_id)
        raw_result = json.loads(row["result_json"])
        result = MixtureSelectionCalculation.model_validate(raw_result).model_dump(mode="json")
        if (
            row["config_json"] != storage.planning_json(config.model_dump(mode="json"))
            or row["model_id"] != str(config.model_id)
            or row["candidate_revision_id"] != str(config.candidate_revision_id)
            or config.expected_rows_sha256 != candidate["rows_sha256"]
            or config.expected_model_sha256 != model["snapshot_sha256"]
            or len(result["items"]) != config.batch_size
            or result != raw_result
            or result["selection_policy"] != config.policy
        ):
            raise ValueError
        by_id = {item["row_id"]: item for item in candidate_result["items"]}
        if len({item["row_id"] for item in result["items"]}) != config.batch_size:
            raise ValueError
        for rank, item in enumerate(result["items"], 1):
            base = by_id.get(item["row_id"])
            if base is None or item["rank"] != rank or not item["eligible"]:
                raise ValueError
            if (
                any(item[key] != value for key, value in base.items() if key != "source_row_number")
                or item["source_row_number"] != rank
            ):
                raise ValueError
        if (
            config.policy == "manual_mixture_base_posterior_v1"
            and [item["row_id"] for item in result["items"]] != config.row_ids
        ):
            raise ValueError
        return row, result, config
    except (ValueError, TypeError, KeyError, studies.BayesianStorageConflict):
        raise _error("bayesian_planning_artifact_invalid") from None


def get_mixture_selection(settings: Settings, study_id: UUID, selection_id: UUID) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    row, result, body = read_mixture_selection(settings, bundle, selection_id)
    return {
        "selection_id": str(selection_id),
        "config_sha256": row["config_sha256"],
        "result_sha256": row["result_sha256"],
        "created_at": row["created_at"],
        "config": body.model_dump(mode="json"),
        "result": result,
    }


def confirm_mixture_selection(
    settings: Settings, study_id: UUID, selection_id: UUID, body: PlanningConfirmRequest
) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    row, result, config = read_mixture_selection(settings, bundle, selection_id)
    if (
        body.expected_config_sha256 != row["config_sha256"]
        or body.expected_result_sha256 != row["result_sha256"]
    ):
        raise _error("bayesian_planning_selection_mismatch")
    old = studies.get_bayesian_recommendation_batch_record(
        settings.workspace_root, str(selection_id)
    )
    if old is not None:
        if old.study_version_id != bundle.version.study_version_id:
            raise _error("bayesian_planning_selection_mismatch")
        return get_mixture_batch(settings, study_id, selection_id)
    _source(bundle, config)
    candidate, rows, _ = read_mixture_candidate(settings, bundle, config.candidate_revision_id)
    _, snapshot, _ = read_mixture_model(settings, bundle, config.model_id)
    recomputed = _run(
        "mixture_selection",
        {
            "snapshot": snapshot,
            "rows": rows["items"],
            "config": config.model_dump(mode="json"),
            "excluded_actual": [json.loads(t.actual_coordinates_json) for t in bundle.trials],
        },
        time_budget_ms=config.time_budget_ms,
    )
    if recomputed != result or candidate["source_trial_count"] != len(bundle.trials):
        raise _error("bayesian_planning_selection_mismatch")
    now = utc_now()
    trials = [
        new_mixture_trial_record(
            study_version_id=bundle.version.study_version_id,
            definition_sha256=bundle.version.definition_sha256,
            design=bundle.design,
            trial_number=len(bundle.trials) + i + 1,
            actual=item["actual_coordinates"],
            created_at=now,
            origin="recommendation",
        )
        for i, item in enumerate(result["items"])
    ]
    batch = studies.BayesianRecommendationBatchRecord(
        batch_id=str(selection_id),
        study_version_id=bundle.version.study_version_id,
        source_history_revision_id=str(config.expected_history_revision_id),
        source_observation_history_sha256=config.expected_history_sha256,
        method_id=bundle.study.method_id,
        method_version=METHOD_VERSION,
        batch_size=len(trials),
        batch_policy="source_owned_mixture_planning_v1",
        config_schema_version=13,
        result_schema_version=13,
        model_schema_version=13,
        item_schema_version=6,
        config_json=row["config_json"],
        config_sha256=row["config_sha256"],
        result_json=row["result_json"],
        result_sha256=row["result_sha256"],
        created_at=now,
        app_version=APP_VERSION,
    )
    items = [
        studies.BayesianRecommendationBatchItemRecord(
            item_id=str(uuid4()),
            batch_id=str(selection_id),
            trial_id=t.trial_id,
            rank=i + 1,
            item_schema_version=6,
            item_result_json=storage.planning_json(item),
            item_result_sha256=storage.planning_sha(item),
            created_at=now,
        )
        for i, (t, item) in enumerate(zip(trials, result["items"], strict=True))
    ]
    try:
        studies.insert_bayesian_recommendation_batch_bundle(
            settings.workspace_root,
            trials=trials,
            batch=batch,
            items=items,
            expected_history_revision_id=str(config.expected_history_revision_id),
            expected_history_sha256=config.expected_history_sha256,
            total_trial_budget=config.total_trial_budget,
            allow_existing=True,
            planning_selection=(str(selection_id), row["config_sha256"], row["result_sha256"]),
        )
    except studies.BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    return get_mixture_batch(settings, study_id, selection_id)


def get_mixture_batch(settings: Settings, study_id: UUID, batch_id: UUID) -> dict[str, Any]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    batch = studies.get_bayesian_recommendation_batch_record(settings.workspace_root, str(batch_id))
    if batch is None:
        raise _error("bayesian_planning_artifact_invalid")
    return validate_mixture_batch_record(settings, bundle, batch)


def validate_mixture_batch_record(
    settings: Settings,
    bundle: MixtureValidatedStudy,
    batch: studies.BayesianRecommendationBatchRecord,
    *,
    immutable_selected_trials: bool = False,
) -> dict[str, Any]:
    if type(immutable_selected_trials) is not bool:
        raise _error("bayesian_planning_artifact_invalid")
    try:
        batch_id = UUID(batch.batch_id)
        storage._documents(
            {
                "config_json": batch.config_json,
                "config_sha256": batch.config_sha256,
                "result_json": batch.result_json,
                "result_sha256": batch.result_sha256,
            },
            (("config_json", "config_sha256"), ("result_json", "result_sha256")),
        )
    except (ValueError, TypeError, studies.BayesianStorageConflict):
        raise _error("bayesian_planning_artifact_invalid") from None
    row, result, config = read_mixture_selection(settings, bundle, batch_id)
    if (
        batch.study_version_id != bundle.version.study_version_id
        or batch.config_sha256 != row["config_sha256"]
        or batch.result_sha256 != row["result_sha256"]
        or batch.config_json != row["config_json"]
        or batch.result_json != row["result_json"]
        or batch.config_json != storage.planning_json(config.model_dump(mode="json"))
        or batch.result_json != storage.planning_json(result)
        or batch.config_schema_version != 13
        or batch.result_schema_version != 13
        or batch.model_schema_version != 13
        or batch.item_schema_version != 6
        or batch.batch_size != config.batch_size
        or batch.method_id != bundle.study.method_id
        or batch.source_history_revision_id != str(config.expected_history_revision_id)
        or batch.source_observation_history_sha256 != config.expected_history_sha256
        or batch.method_version != METHOD_VERSION
        or batch.batch_policy != "source_owned_mixture_planning_v1"
    ):
        raise _error("bayesian_planning_artifact_invalid")
    items = studies.list_bayesian_recommendation_batch_item_records(
        settings.workspace_root, str(batch_id)
    )
    by_id = {t.trial_id: t for t in bundle.trials}
    if len(items) != config.batch_size:
        raise _error("bayesian_planning_artifact_invalid")
    output = []
    for i, (stored, expected) in enumerate(zip(items, result["items"], strict=True)):
        trial = by_id.get(stored.trial_id)
        if (
            trial is None
            or trial.study_version_id != bundle.version.study_version_id
            or trial.trial_number != config.expected_trial_count + i + 1
            or trial.origin != "recommendation"
            or trial.replicate_of_trial_id is not None
            or trial.created_at != batch.created_at
            or stored.item_schema_version != 6
            or stored.rank != i + 1
            or stored.item_result_json != storage.planning_json(expected)
            or stored.item_result_sha256 != storage.planning_sha(expected)
        ):
            raise _error("bayesian_planning_artifact_invalid")
        # Report source histories predate these selected trials' observations.
        # Validate their immutable original pending receipt, never a later overlay.
        projected_trial = (
            replace(
                trial,
                state="pending",
                objective_value=None,
                response_values_json=None,
                closed_at=None,
            )
            if immutable_selected_trials
            else trial
        )
        projected = mixture_trial_response(bundle, projected_trial)
        if projected.actual_coordinates != expected["actual_coordinates"]:
            raise _error("bayesian_planning_artifact_invalid")
        output.append(
            {
                "rank": i + 1,
                "result": expected,
                "trial": projected.model_dump(mode="json"),
            }
        )
    return {
        "batch_id": str(batch_id),
        "schema_version": 13,
        "config_sha256": batch.config_sha256,
        "result_sha256": batch.result_sha256,
        "config": config.model_dump(mode="json"),
        "result": result,
        "items": output,
        "created_at": batch.created_at,
    }
