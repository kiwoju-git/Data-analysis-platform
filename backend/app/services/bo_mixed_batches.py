"""Atomic mixed pending batches and exact-source immutable readers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bo_mixed_batch import MixedBatchItem, MixedBatchResponse, MixedBatchSource
from app.api.v1.schemas.bo_mixed_studies import mixed_factor_domains
from app.api.v1.schemas.bo_mixed_workflow import MixedSelectionInput
from app.api.v1.schemas.bo_planning import PlanningConfirmRequest
from app.core.config import Settings
from app.services.analysis_run_execution import APP_VERSION, runtime_build_provenance, utc_now
from app.services.bayesian_noise_recommendations import _error, _json, _sha
from app.services.bo_mixed_candidates import read_mixed_candidate
from app.services.bo_mixed_models import read_mixed_model, require_mixed_source
from app.services.bo_mixed_studies import (
    get_mixed_study,
    mixed_trial_response,
    new_mixed_trial_record,
)
from app.storage.bayesian_studies import (
    BayesianRecommendationBatchItemRecord,
    BayesianRecommendationBatchRecord,
    BayesianStorageConflict,
    get_bayesian_recommendation_batch_record,
    get_latest_bayesian_recommendation_batch_record,
    insert_bayesian_recommendation_batch_bundle,
    list_bayesian_recommendation_batch_item_records,
)


def _config(study: Any, request: MixedSelectionInput, source: MixedBatchSource) -> dict[str, Any]:
    return {
        "schema_version": 12 if request.schema_version == 5 else 10,
        "study_id": str(study.study_id),
        "study_version_id": str(study.study_version_id),
        "definition_sha256": study.definition_sha256,
        "source_history_revision_id": str(request.expected_history_revision_id),
        "source_observation_history_sha256": request.expected_history_sha256,
        "source_trial_count": request.expected_trial_count,
        "source": source.model_dump(mode="json"),
        "selection_request": request.model_dump(mode="json"),
    }


def _selected_rows(calculation: Any) -> Any:
    return calculation.items if calculation.schema_version == 2 else calculation.selected_rows


def _projection_context(version: Any, factors: Any, objective: Any, constraints: Any) -> Any:
    return SimpleNamespace(
        version=version,
        factor_domains=mixed_factor_domains(factors),
        objective=objective,
        constraints=constraints,
    )


def confirm_mixed_selection(
    settings: Settings, study_id: UUID, selection_id: UUID, body: PlanningConfirmRequest
) -> MixedBatchResponse:
    from app.services.bo_mixed_selections import get_mixed_selection

    selected = get_mixed_selection(settings, study_id, selection_id)
    if (
        selected.config_sha256 != body.expected_config_sha256
        or selected.result_sha256 != body.expected_result_sha256
    ):
        raise _error("bayesian_planning_selection_mismatch")
    if selected.confirmed_batch_id is not None:
        return get_mixed_batch(settings, study_id, selected.confirmed_batch_id)
    study = get_mixed_study(settings, study_id)
    request = selected.request
    require_mixed_source(study, request)
    if any(trial.state == "pending" for trial in study.trials):
        raise _error("bayesian_optimization_pending_recommendation_exists")
    if len(study.trials) + request.batch_size > request.total_trial_budget:
        raise _error("bayesian_optimization_batch_budget_exceeded")
    snapshot = None
    if request.model_id is not None:
        _, snapshot, _ = read_mixed_model(settings, study, request.model_id)
    source = MixedBatchSource(
        model_id=request.model_id,
        model_sha256=request.expected_model_sha256,
        candidate_revision_id=request.candidate_revision_id,
        rows_sha256=request.expected_rows_sha256,
        selection_id=selection_id,
        selection_config_sha256=selected.config_sha256,
        selection_result_sha256=selected.result_sha256,
    )
    config = _config(study, request, source)
    created = utc_now()
    version = SimpleNamespace(
        study_version_id=str(study.study_version_id), definition_sha256=study.definition_sha256
    )
    context = _projection_context(version, study.factors, study.objective, study.constraints)
    trials, item_records, items = [], [], []
    for rank, point in enumerate(_selected_rows(selected.calculation), 1):
        trial_record = new_mixed_trial_record(
            study_version_id=str(study.study_version_id),
            definition_sha256=study.definition_sha256,
            domains=context.factor_domains,
            trial_number=len(study.trials) + rank,
            actual=point.actual_coordinates,
            created_at=created,
            origin="recommendation",
        )
        trial = mixed_trial_response(context, trial_record)
        if trial.encoded_coordinates != point.encoded_coordinates:
            raise _error("bayesian_planning_artifact_invalid")
        item = MixedBatchItem(
            item_id=uuid4(), batch_id=selection_id, rank=rank, trial=trial, current_trial=trial
        )
        payload = item.model_dump(mode="json")
        trials.append(trial_record)
        items.append(item)
        item_records.append(
            BayesianRecommendationBatchItemRecord(
                item_id=str(item.item_id),
                batch_id=str(selection_id),
                trial_id=trial_record.trial_id,
                rank=rank,
                item_schema_version=5,
                item_result_json=_json(payload),
                item_result_sha256=_sha(payload),
                created_at=created,
            )
        )
    runtime = runtime_build_provenance(settings)
    model_fields = {
        key: None if snapshot is None else snapshot[key]
        for key in ("response_models", "incumbent", "observation_view")
    }
    result = MixedBatchResponse.model_validate(
        {
            "method_version": "0.16.0" if request.schema_version == 5 else "0.15.0",
            "config_schema_version": config["schema_version"],
            "result_schema_version": config["schema_version"],
            "model_schema_version": config["schema_version"],
            "batch_id": selection_id,
            "batch_size": request.batch_size,
            "study_id": study_id,
            "study_version_id": study.study_version_id,
            "source_history_revision_id": request.expected_history_revision_id,
            "source_observation_history_sha256": request.expected_history_sha256,
            "definition_sha256": study.definition_sha256,
            "source": source,
            "objective": study.objective,
            **model_fields,
            "warnings": [] if snapshot is None else snapshot["warnings"],
            "selection_request": request,
            "calculation": selected.calculation,
            "items": items,
            "config_sha256": _sha(config),
            "result_sha256": "0" * 64,
            "created_at": created,
            "requested_total_trial_budget": request.total_trial_budget,
            "provenance": {
                "app_version": APP_VERSION,
                "python_version": runtime["python_version"],
                "platform": runtime["platform"],
                "build_commit": runtime["build_commit"],
                "package_versions": {}
                if snapshot is None
                else snapshot["response_models"][0]["model"]["package_versions"],
            },
        }
    )
    immutable = result.model_dump(mode="json", exclude={"is_latest", "batch_state"})
    immutable["result_sha256"] = _sha(immutable)
    result_json = _json(immutable)
    batch = BayesianRecommendationBatchRecord(
        batch_id=str(selection_id),
        study_version_id=str(study.study_version_id),
        source_history_revision_id=str(request.expected_history_revision_id),
        source_observation_history_sha256=request.expected_history_sha256,
        method_id=result.method_id,
        method_version=result.method_version,
        batch_size=request.batch_size,
        batch_policy=result.batch_policy,
        config_schema_version=result.config_schema_version,
        result_schema_version=result.result_schema_version,
        model_schema_version=result.model_schema_version,
        item_schema_version=5,
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
            items=item_records,
            expected_history_revision_id=str(request.expected_history_revision_id),
            expected_history_sha256=request.expected_history_sha256,
            total_trial_budget=request.total_trial_budget,
            allow_existing=True,
            planning_selection=(str(selection_id), selected.config_sha256, selected.result_sha256),
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    return get_mixed_batch(settings, study_id, selection_id)


def get_mixed_batch(settings: Settings, study_id: UUID, batch_id: UUID) -> MixedBatchResponse:
    from app.services.bayesian_recommendation_batches import _batch_state

    study = get_mixed_study(settings, study_id)
    record = get_bayesian_recommendation_batch_record(settings.workspace_root, str(batch_id))
    if (
        record is None
        or record.study_version_id != str(study.study_version_id)
        or record.result_schema_version not in {10, 12}
    ):
        raise _error("bayesian_planning_not_found")
    saved = MixedBatchResponse.model_validate_json(record.result_json)
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


def validate_mixed_batch_record(
    settings: Settings,
    *,
    version: Any,
    factors: Any,
    objective: Any,
    constraints: Any,
    trials: Any,
    history: Any,
    record: BayesianRecommendationBatchRecord,
) -> MixedBatchResponse:
    """Use explicit historical source records, never recursively load the current study."""
    from app.services.bo_mixed_selections import read_mixed_selection

    def require(value: bool) -> None:
        if not value:
            raise ValueError("mixed source mismatch")

    try:
        require(hashlib.sha256(record.config_json.encode()).hexdigest() == record.config_sha256)
        require(hashlib.sha256(record.result_json.encode()).hexdigest() == record.result_sha256)
        result = MixedBatchResponse.model_validate_json(record.result_json)
        config = json.loads(record.config_json)
        require(_json(config) == record.config_json)
        require(version.schema_version == 7 and history is not None and history.schema_version == 2)
        require(history.study_version_id == version.study_version_id == record.study_version_id)
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
                result.method_version,
                result.config_schema_version,
                result.result_schema_version,
                result.model_schema_version,
                5,
                "source_owned_mixed_planning_v1",
            )
        )
        require(record.batch_size == result.batch_size and record.batch_id == str(result.batch_id))
        require(str(result.study_version_id) == version.study_version_id)
        require(str(result.study_id) == version.study_id)
        require(result.definition_sha256 == version.definition_sha256)
        require(
            str(result.source_history_revision_id)
            == history.history_revision_id
            == record.source_history_revision_id
        )
        require(
            result.source_observation_history_sha256
            == history.observation_history_sha256
            == record.source_observation_history_sha256
        )
        require(
            result.config_sha256 == record.config_sha256 and result.created_at == record.created_at
        )
        immutable = result.model_dump(mode="json", exclude={"is_latest", "batch_state"})
        require(_json(immutable) == record.result_json)
        immutable["result_sha256"] = "0" * 64
        require(_sha(immutable) == result.result_sha256)
        context = _projection_context(version, factors, objective, constraints)
        study = SimpleNamespace(
            study_id=UUID(version.study_id),
            study_version_id=UUID(version.study_version_id),
            definition_sha256=version.definition_sha256,
            factors=factors,
            objective=objective,
            constraints=constraints,
            trials=[mixed_trial_response(context, trial) for trial in trials],
        )
        source = result.source
        selected, request, calculation = read_mixed_selection(settings, study, source.selection_id)
        candidate, rows, _ = read_mixed_candidate(settings, study, source.candidate_revision_id)
        cutoff = result.items[0].trial.trial_number - 1
        require(selected["confirmed_batch_id"] == record.batch_id)
        require(source.selection_config_sha256 == selected["config_sha256"])
        require(source.selection_result_sha256 == selected["result_sha256"])
        require(source.rows_sha256 == candidate["rows_sha256"] == request.expected_rows_sha256)
        require(source.candidate_revision_id == request.candidate_revision_id)
        require(
            source.model_id == request.model_id
            and source.model_sha256 == request.expected_model_sha256
        )
        require(request.expected_trial_count == cutoff == candidate["source_trial_count"])
        require(str(request.expected_history_revision_id) == history.history_revision_id)
        require(request.expected_history_sha256 == history.observation_history_sha256)
        require(request.model_dump(mode="json") == result.selection_request.model_dump(mode="json"))
        require(calculation.model_dump(mode="json") == result.calculation.model_dump(mode="json"))
        require(cutoff + result.batch_size <= request.total_trial_budget)
        require(config == _config(study, request, source))
        require(result.objective.model_dump(mode="json") == objective.model_dump(mode="json"))
        if source.model_id is not None:
            model, snapshot, _ = read_mixed_model(settings, study, source.model_id)
            require(model["snapshot_sha256"] == source.model_sha256)
            require(model["source_history_revision_id"] == history.history_revision_id)
            require(model["history_sha256"] == history.observation_history_sha256)
            dumped = result.model_dump(mode="json")
            for key in ("response_models", "incumbent", "observation_view", "warnings"):
                require(dumped[key] == snapshot[key])
            require(
                all(
                    item["model"]["package_versions"] == result.provenance.package_versions
                    for item in snapshot["response_models"]
                )
            )
        else:
            require(result.warnings == [] and result.provenance.package_versions == {})
        require(result.provenance.app_version == record.app_version)
        item_records = list_bayesian_recommendation_batch_item_records(
            settings.workspace_root, record.batch_id
        )
        require(len(item_records) == result.batch_size)
        by_trial = {trial.trial_id: trial for trial in trials}
        by_row = {row.row_id: row for row in rows}
        for item, stored, planned in zip(
            result.items, item_records, _selected_rows(calculation), strict=True
        ):
            trial = by_trial[str(item.trial.trial_id)]
            row = by_row[planned.row_id]
            require(item.rank == stored.rank)
            require(item.item_id == UUID(stored.item_id) and stored.batch_id == record.batch_id)
            require(stored.trial_id == trial.trial_id and stored.item_schema_version == 5)
            require(item.current_trial == item.trial and item.trial.state == "pending")
            require(item.trial.response_values is None and item.trial.closed_at is None)
            require(stored.item_result_json == _json(item.model_dump(mode="json")))
            require(stored.item_result_sha256 == _sha(item.model_dump(mode="json")))
            require(item.trial.trial_number == trial.trial_number == cutoff + item.rank)
            require(
                trial.study_version_id == version.study_version_id
                and trial.origin == "recommendation"
            )
            original = replace(
                trial,
                state="pending",
                objective_value=None,
                response_values_json=None,
                closed_at=None,
            )
            require(item.trial == mixed_trial_response(context, original))
            require(
                item.trial.actual_coordinates
                == planned.actual_coordinates
                == row.actual_coordinates
            )
            require(
                item.trial.encoded_coordinates
                == planned.encoded_coordinates
                == row.encoded_coordinates
            )
            require(
                planned.source_row_number == row.source_row_number
                and planned.input_coordinates == row.input_coordinates
            )
            require(
                item.trial.created_at == trial.created_at == stored.created_at == record.created_at
            )
        return result
    except (ValueError, KeyError, TypeError, AttributeError, BayesianStorageConflict):
        raise _error("bayesian_planning_artifact_invalid") from None
