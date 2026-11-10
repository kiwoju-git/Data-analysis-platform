"""Atomic manual-candidate confirmation and immutable schema8 readers."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bayesian import BayesianTrialResponse
from app.api.v1.schemas.bayesian_desirability_recommendations import DesirabilityOrderedBatchItem
from app.api.v1.schemas.bo_planning import PlanningConfirmRequest, PlanningSelectionCreateRequest
from app.api.v1.schemas.bo_planning_batch import PlanningBatchResponse, PlanningBatchSource
from app.core.config import Settings
from app.services.analysis_run_execution import APP_VERSION, runtime_build_provenance, utc_now
from app.services.bayesian_noise_recommendations import _error, _json, _sha
from app.services.bo_planning import (
    _read_model,
    _read_revision,
    _require_source,
    get_planning_selection,
)
from app.storage import bo_planning as storage
from app.storage.bayesian_studies import (
    BayesianRecommendationBatchItemRecord,
    BayesianRecommendationBatchRecord,
    BayesianStorageConflict,
    BayesianTrialRecord,
    get_bayesian_recommendation_batch_record,
    get_latest_bayesian_recommendation_batch_record,
    insert_bayesian_recommendation_batch_bundle,
    list_bayesian_recommendation_batch_item_records,
)


def confirm_planning_selection(
    settings: Settings,
    study_id: UUID,
    selection_id: UUID,
    body: PlanningConfirmRequest,
) -> PlanningBatchResponse:
    from app.services.bayesian_studies import get_bayesian_study

    selected = get_planning_selection(settings, study_id, selection_id)
    if (
        selected.config_sha256 != body.expected_config_sha256
        or selected.result_sha256 != body.expected_result_sha256
    ):
        raise _error("bayesian_planning_selection_mismatch")
    if selected.confirmed_batch_id is not None:
        return get_planning_batch(settings, study_id, selected.confirmed_batch_id)
    study = get_bayesian_study(settings, study_id)
    model, snapshot, _ = _read_model(settings, study, selected.model_id)
    _require_source(study, model, selected.request)
    if any(trial.state == "pending" for trial in study.trials):
        raise _error("bayesian_optimization_pending_recommendation_exists")
    count = len(selected.calculation.items)
    if len(study.trials) + count > selected.request.total_trial_budget:
        raise _error("bayesian_optimization_batch_budget_exceeded")
    source = PlanningBatchSource(
        model_id=selected.model_id,
        model_sha256=selected.model_sha256,
        candidate_revision_id=selected.candidate_revision_id,
        rows_sha256=selected.rows_sha256,
        selection_id=selection_id,
        selection_config_sha256=selected.config_sha256,
        selection_result_sha256=selected.result_sha256,
    )
    config = {
        "schema_version": 8,
        "study_id": str(study_id),
        "study_version_id": str(study.study_version_id),
        "definition_sha256": study.definition_sha256,
        "source_history_revision_id": str(selected.request.expected_history_revision_id),
        "source_observation_history_sha256": selected.request.expected_history_sha256,
        "source_trial_count": len(study.trials),
        "source": source.model_dump(mode="json"),
        "selection_request": selected.request.model_dump(mode="json"),
    }
    created = utc_now()
    trials, records, items = [], [], []
    for candidate in selected.calculation.items:
        trial_id, item_id = uuid4(), uuid4()
        number = len(study.trials) + candidate.rank
        coordinates_sha = _sha(
            {
                "definition_sha256": study.definition_sha256,
                "trial_number": number,
                "origin": "recommendation",
                "actual_coordinates": candidate.actual_coordinates,
                "normalized_coordinates": candidate.normalized_coordinates,
            }
        )
        trial = BayesianTrialResponse(
            trial_id=trial_id,
            study_version_id=study.study_version_id,
            trial_number=number,
            origin="recommendation",
            state="pending",
            actual_coordinates=candidate.actual_coordinates,
            normalized_coordinates=candidate.normalized_coordinates,
            coordinates_sha256=coordinates_sha,
            objective_value=None,
            created_at=created,
            closed_at=None,
        )
        item = DesirabilityOrderedBatchItem(
            item_id=item_id,
            batch_id=selection_id,
            rank=candidate.rank,
            trial=trial,
            current_trial=trial,
        )
        trials.append(
            BayesianTrialRecord(
                trial_id=str(trial_id),
                study_version_id=str(study.study_version_id),
                trial_number=number,
                origin="recommendation",
                state="pending",
                actual_coordinates_json=_json(trial.actual_coordinates),
                normalized_coordinates_json=_json(trial.normalized_coordinates),
                coordinates_sha256=coordinates_sha,
                objective_value=None,
                created_at=created,
                closed_at=None,
            )
        )
        item_payload = item.model_dump(mode="json")
        records.append(
            BayesianRecommendationBatchItemRecord(
                item_id=str(item_id),
                batch_id=str(selection_id),
                trial_id=str(trial_id),
                rank=candidate.rank,
                item_schema_version=4,
                item_result_json=_json(item_payload),
                item_result_sha256=_sha(item_payload),
                created_at=created,
            )
        )
        items.append(item)
    runtime = runtime_build_provenance(settings)
    result = PlanningBatchResponse.model_validate(
        {
            "batch_size": count,
            "batch_id": selection_id,
            "study_id": study_id,
            "study_version_id": study.study_version_id,
            "source_history_revision_id": selected.request.expected_history_revision_id,
            "source_observation_history_sha256": selected.request.expected_history_sha256,
            "definition_sha256": study.definition_sha256,
            "source": source,
            "objective": snapshot["calculation_request"]["objective"],
            "response_models": snapshot["response_models"],
            "incumbent": snapshot["incumbent"],
            "observation_view": snapshot["observation_view"],
            "warnings": snapshot["warnings"],
            "calculation": selected.calculation,
            "items": items,
            "config_sha256": _sha(config),
            "result_sha256": "0" * 64,
            "created_at": created,
            "requested_total_trial_budget": selected.request.total_trial_budget,
            "provenance": {
                "app_version": APP_VERSION,
                "python_version": runtime["python_version"],
                "platform": runtime["platform"],
                "build_commit": runtime["build_commit"],
                "package_versions": snapshot["response_models"][0]["model"]["package_versions"],
            },
        }
    )
    immutable = result.model_dump(mode="json", exclude={"is_latest", "batch_state"})
    immutable["result_sha256"] = _sha(immutable)
    result_json = _json(immutable)
    batch = BayesianRecommendationBatchRecord(
        batch_id=str(selection_id),
        study_version_id=str(study.study_version_id),
        source_history_revision_id=str(selected.request.expected_history_revision_id),
        source_observation_history_sha256=selected.request.expected_history_sha256,
        method_id=result.method_id,
        method_version=result.method_version,
        batch_size=count,
        batch_policy=result.batch_policy,
        config_schema_version=8,
        result_schema_version=8,
        model_schema_version=8,
        item_schema_version=4,
        config_json=_json(config),
        config_sha256=_sha(config),
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode()).hexdigest(),
        created_at=created,
        app_version=APP_VERSION,
    )
    try:
        insert_bayesian_recommendation_batch_bundle(
            settings.workspace_root,
            trials=trials,
            batch=batch,
            items=records,
            expected_history_revision_id=str(selected.request.expected_history_revision_id),
            expected_history_sha256=selected.request.expected_history_sha256,
            total_trial_budget=selected.request.total_trial_budget,
            allow_existing=True,
            planning_selection=(str(selection_id), selected.config_sha256, selected.result_sha256),
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    return get_planning_batch(settings, study_id, selection_id)


def get_planning_batch(settings: Settings, study_id: UUID, batch_id: UUID) -> PlanningBatchResponse:
    from app.services.bayesian_recommendation_batches import _batch_state
    from app.services.bayesian_studies import get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    record = get_bayesian_recommendation_batch_record(settings.workspace_root, str(batch_id))
    if (
        record is None
        or record.study_version_id != str(study.study_version_id)
        or record.result_schema_version != 8
    ):
        raise _error("bayesian_planning_not_found")
    saved = PlanningBatchResponse.model_validate_json(record.result_json)
    current = {trial.trial_id: trial for trial in study.trials}
    items = [
        item.model_copy(update={"current_trial": current[item.trial.trial_id]})
        for item in saved.items
    ]
    latest = get_latest_bayesian_recommendation_batch_record(
        settings.workspace_root, record.study_version_id
    )
    return saved.model_copy(
        update={
            "items": items,
            "batch_state": _batch_state(items),
            "is_latest": latest is not None and latest.batch_id == record.batch_id,
        }
    )


def validate_planning_batch_record(
    settings: Settings,
    *,
    version: Any,
    factors: Any,
    objective: Any,
    constraints: Any,
    trials: Any,
    history: Any,
    record: BayesianRecommendationBatchRecord,
) -> PlanningBatchResponse:
    from app.services.bayesian_studies import _trial_response

    def require(value: bool) -> None:
        if not value:
            raise ValueError("planning source mismatch")

    try:
        require(hashlib.sha256(record.config_json.encode()).hexdigest() == record.config_sha256)
        require(hashlib.sha256(record.result_json.encode()).hexdigest() == record.result_sha256)
        result = PlanningBatchResponse.model_validate_json(record.result_json)
        config = json.loads(record.config_json)
        require(_json(config) == record.config_json)
        require(history is not None and history.study_version_id == version.study_version_id)
        require(
            history.schema_version == 2
            and history.observation_history_sha256 == record.source_observation_history_sha256
        )
        require(
            (
                record.method_id,
                record.method_version,
                record.config_schema_version,
                record.result_schema_version,
                record.model_schema_version,
                record.item_schema_version,
                record.batch_policy,
            )
            == (
                result.method_id,
                "0.13.0",
                8,
                8,
                8,
                4,
                "manual_ordered_fixed_model_v1",
            )
        )
        require(record.batch_size == result.batch_size and record.batch_id == str(result.batch_id))
        require(record.study_version_id == version.study_version_id == str(result.study_version_id))
        require(
            str(result.study_id) == version.study_id
            and result.definition_sha256 == version.definition_sha256
        )
        require(
            str(result.source_history_revision_id)
            == history.history_revision_id
            == record.source_history_revision_id
        )
        require(result.source_observation_history_sha256 == history.observation_history_sha256)
        require(
            result.config_sha256 == record.config_sha256 and result.created_at == record.created_at
        )
        immutable = result.model_dump(mode="json", exclude={"is_latest", "batch_state"})
        require(_json(immutable) == record.result_json)
        immutable["result_sha256"] = "0" * 64
        require(_sha(immutable) == result.result_sha256)
        study = SimpleNamespace(
            study_id=UUID(version.study_id),
            study_version_id=UUID(version.study_version_id),
            definition_sha256=version.definition_sha256,
            factors=factors,
            objective=objective,
            constraints=constraints,
            trials=[_trial_response(trial) for trial in trials],
        )
        source = result.source
        model, snapshot, _ = _read_model(settings, study, source.model_id)
        candidate, rows, _ = _read_revision(settings, study, source.candidate_revision_id)
        selected = storage.get_planning_selection(
            settings.workspace_root, str(source.selection_id), version.study_version_id
        )
        require(selected is not None)
        assert selected is not None
        request = PlanningSelectionCreateRequest.model_validate_json(selected["config_json"])
        count = result.items[0].trial.trial_number - 1
        require(source.model_sha256 == model["snapshot_sha256"] == request.expected_model_sha256)
        require(source.rows_sha256 == candidate["rows_sha256"] == request.expected_rows_sha256)
        require(source.selection_config_sha256 == selected["config_sha256"])
        require(source.selection_result_sha256 == selected["result_sha256"])
        require(selected["confirmed_batch_id"] == record.batch_id)
        require(
            selected["model_id"] == str(source.model_id)
            and selected["candidate_revision_id"] == str(source.candidate_revision_id)
        )
        require(result.calculation.model_dump(mode="json") == json.loads(selected["result_json"]))
        require([item.row_id for item in result.calculation.items] == request.row_ids)
        require(request.expected_trial_count == count == candidate["source_trial_count"])
        require(str(request.expected_history_revision_id) == history.history_revision_id)
        require(request.expected_history_sha256 == history.observation_history_sha256)
        require(model["source_history_revision_id"] == history.history_revision_id)
        require(model["history_sha256"] == history.observation_history_sha256)
        require(result.requested_total_trial_budget == request.total_trial_budget)
        require(count + result.batch_size <= request.total_trial_budget)
        require(
            config
            == {
                "schema_version": 8,
                "study_id": version.study_id,
                "study_version_id": version.study_version_id,
                "definition_sha256": version.definition_sha256,
                "source_history_revision_id": history.history_revision_id,
                "source_observation_history_sha256": history.observation_history_sha256,
                "source_trial_count": count,
                "source": source.model_dump(mode="json"),
                "selection_request": request.model_dump(mode="json"),
            }
        )
        require(
            result.objective.model_dump(mode="json") == snapshot["calculation_request"]["objective"]
        )
        for key in ("response_models", "incumbent", "observation_view", "warnings"):
            require(result.model_dump(mode="json")[key] == snapshot[key])
        require(result.provenance.app_version == record.app_version)
        require(
            all(
                item.model.package_versions == result.provenance.package_versions
                for item in result.response_models
            )
        )
        item_records = list_bayesian_recommendation_batch_item_records(
            settings.workspace_root, record.batch_id
        )
        require(len(item_records) == result.batch_size)
        by_trial = {trial.trial_id: trial for trial in trials}
        by_row = {row.row_id: row for row in rows}
        for item, stored, planned in zip(
            result.items, item_records, result.calculation.items, strict=True
        ):
            trial = by_trial[str(item.trial.trial_id)]
            row = by_row[planned.row_id]
            require(item.rank == stored.rank == planned.rank)
            require(item.item_id == UUID(stored.item_id) and stored.batch_id == record.batch_id)
            require(stored.trial_id == trial.trial_id and stored.item_schema_version == 4)
            require(item.current_trial == item.trial and item.trial.state == "pending")
            require(item.trial.objective_value is None and item.trial.closed_at is None)
            require(stored.item_result_json == _json(item.model_dump(mode="json")))
            require(stored.item_result_sha256 == _sha(item.model_dump(mode="json")))
            require(item.trial.trial_number == trial.trial_number == count + item.rank)
            require(
                trial.study_version_id == version.study_version_id
                and trial.origin == "recommendation"
            )
            require(
                item.trial.actual_coordinates
                == planned.actual_coordinates
                == row.actual_coordinates
                == json.loads(trial.actual_coordinates_json)
            )
            require(
                item.trial.normalized_coordinates
                == planned.normalized_coordinates
                == row.normalized_coordinates
                == json.loads(trial.normalized_coordinates_json)
            )
            require(
                planned.source_row_number == row.source_row_number
                and planned.input_coordinates == row.input_coordinates
            )
            require(item.trial.coordinates_sha256 == trial.coordinates_sha256)
            require(
                item.trial.created_at == trial.created_at == stored.created_at == record.created_at
            )
        return result
    except (ValueError, KeyError, TypeError, AttributeError, BayesianStorageConflict):
        raise _error("bayesian_planning_artifact_invalid") from None
