"""All-or-nothing pending trials for an immutable augmentation selection."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bayesian import BayesianTrialResponse
from app.api.v1.schemas.bayesian_desirability import BayesianDesirabilityObjective
from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityOrderedBatchItem,
    DesirabilityProvenance,
)
from app.api.v1.schemas.bo_augmentation import (
    AUGMENTATION_RESULT,
    AugmentationRequest,
    AugmentationSelectionResponse,
    AutoAugmentationCalculation,
    AutoAugmentationSelectionRequest,
)
from app.api.v1.schemas.bo_augmentation_batch import (
    AugmentationBatchResponse,
    AugmentationBatchSource,
)
from app.api.v1.schemas.bo_planning import CandidateRow, PlanningConfirmRequest
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import APP_VERSION, runtime_build_provenance, utc_now
from app.services.bayesian_noise_recommendations import _error, _json, _sha
from app.services.bo_augmentation import (
    _routing_context,
    _source_candidate,
    _verify_binding,
    get_augmentation_selection,
    validate_augmentation_for_commit,
    validate_saved_augmentation,
)
from app.services.bo_auto_evidence import validate_auto_evidence
from app.services.bo_planning import _current, _read_model, get_planning_model
from app.statistics.bayesian_optimization import BayesianOptimizationError
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


def _config(
    study: Any, request: AugmentationRequest, source: AugmentationBatchSource
) -> dict[str, Any]:
    return {
        "schema_version": 11 if request.schema_version == 4 else 9,
        "study_id": str(study.study_id),
        "study_version_id": str(study.study_version_id),
        "definition_sha256": study.definition_sha256,
        "source_history_revision_id": str(request.expected_history_revision_id),
        "source_observation_history_sha256": request.expected_history_sha256,
        "source_trial_count": request.expected_trial_count,
        "source": source.model_dump(mode="json"),
        "selection_request": request.model_dump(mode="json"),
    }


def confirm_augmentation_selection(
    settings: Settings, study_id: UUID, selection_id: UUID, body: PlanningConfirmRequest
) -> AugmentationBatchResponse:
    selected = get_augmentation_selection(settings, study_id, selection_id)
    if (
        selected.config_sha256 != body.expected_config_sha256
        or selected.result_sha256 != body.expected_result_sha256
    ):
        raise _error("bayesian_planning_selection_mismatch")
    if selected.confirmed_batch_id is not None:
        return get_augmentation_batch(settings, study_id, selected.confirmed_batch_id)
    try:
        return _confirm_uncommitted_augmentation(settings, study_id, selection_id, selected)
    except ApiError:
        # Another confirmation may commit after our unconfirmed snapshot read.
        replay = _confirmed_augmentation(settings, study_id, selection_id, body)
        if replay is not None:
            return replay
        raise


def _confirmed_augmentation(
    settings: Settings, study_id: UUID, selection_id: UUID, body: PlanningConfirmRequest
) -> AugmentationBatchResponse | None:
    selected = get_augmentation_selection(settings, study_id, selection_id)
    if (
        selected.config_sha256 != body.expected_config_sha256
        or selected.result_sha256 != body.expected_result_sha256
    ):
        raise _error("bayesian_planning_selection_mismatch")
    if selected.confirmed_batch_id is None:
        return None
    if selected.confirmed_batch_id != selection_id:
        raise _error("bayesian_planning_selection_mismatch")
    return get_augmentation_batch(settings, study_id, selected.confirmed_batch_id)


def _confirm_uncommitted_augmentation(
    settings: Settings,
    study_id: UUID,
    selection_id: UUID,
    selected: AugmentationSelectionResponse,
) -> AugmentationBatchResponse:
    from app.services.bayesian_studies import get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    if not isinstance(study.objective, BayesianDesirabilityObjective):
        raise _error("bayesian_augmentation_model_policy_mismatch")
    candidate, rows, identity, tolerance = _source_candidate(
        settings, study, selected.candidate_revision_id
    )
    request = selected.request
    _verify_binding(study, candidate, identity, tolerance, request)
    if not _current(study, identity, request.expected_trial_count):
        raise _error("bayesian_candidate_source_changed")
    if any(trial.state == "pending" for trial in study.trials):
        raise _error("bayesian_optimization_pending_recommendation_exists")
    if len(study.trials) + request.batch_size > request.total_trial_budget:
        raise _error("bayesian_optimization_batch_budget_exceeded")
    snapshot = None
    if request.model_id is not None:
        _, snapshot, _ = _read_model(settings, study, request.model_id)
    try:
        validate_augmentation_for_commit(study, request, selected.calculation, rows, snapshot)
    except BayesianOptimizationError as exc:
        raise _error("bayesian_planning_artifact_invalid") from exc
    source = AugmentationBatchSource(
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
    trials, records, items = [], [], []
    for rank, point in enumerate(selected.calculation.selected_rows, 1):
        trial_id, item_id = uuid4(), uuid4()
        number = len(study.trials) + rank
        coordinates = {
            "definition_sha256": study.definition_sha256,
            "trial_number": number,
            "origin": "recommendation",
            "actual_coordinates": point.actual_coordinates,
            "normalized_coordinates": point.normalized_coordinates,
        }
        trial = BayesianTrialResponse(
            trial_id=trial_id,
            study_version_id=study.study_version_id,
            trial_number=number,
            origin="recommendation",
            state="pending",
            actual_coordinates=point.actual_coordinates,
            normalized_coordinates=point.normalized_coordinates,
            coordinates_sha256=_sha(coordinates),
            objective_value=None,
            created_at=created,
            closed_at=None,
        )
        item = DesirabilityOrderedBatchItem(
            item_id=item_id, batch_id=selection_id, rank=rank, trial=trial, current_trial=trial
        )
        trials.append(
            BayesianTrialRecord(
                trial_id=str(trial_id),
                study_version_id=str(study.study_version_id),
                trial_number=number,
                origin="recommendation",
                state="pending",
                actual_coordinates_json=_json(point.actual_coordinates),
                normalized_coordinates_json=_json(point.normalized_coordinates),
                coordinates_sha256=trial.coordinates_sha256,
                objective_value=None,
                created_at=created,
                closed_at=None,
            )
        )
        payload = item.model_dump(mode="json")
        records.append(
            BayesianRecommendationBatchItemRecord(
                item_id=str(item_id),
                batch_id=str(selection_id),
                trial_id=str(trial_id),
                rank=rank,
                item_schema_version=4,
                item_result_json=_json(payload),
                item_result_sha256=_sha(payload),
                created_at=created,
            )
        )
        items.append(item)
    model = (
        None
        if request.model_id is None
        else get_planning_model(settings, study_id, request.model_id)
    )
    runtime = runtime_build_provenance(settings)
    result = AugmentationBatchResponse(
        method_version="0.16.0" if request.schema_version == 4 else "0.14.0",
        config_schema_version=11 if request.schema_version == 4 else 9,
        result_schema_version=11 if request.schema_version == 4 else 9,
        model_schema_version=11 if request.schema_version == 4 else 9,
        batch_id=selection_id,
        batch_size=request.batch_size,
        study_id=study_id,
        study_version_id=study.study_version_id,
        source_history_revision_id=request.expected_history_revision_id,
        source_observation_history_sha256=request.expected_history_sha256,
        definition_sha256=study.definition_sha256,
        source=source,
        objective=study.objective,
        model=model,
        calculation=selected.calculation,
        selection_request=request,
        items=items,
        config_sha256=_sha(config),
        result_sha256="0" * 64,
        created_at=created,
        requested_total_trial_budget=request.total_trial_budget,
        provenance=DesirabilityProvenance.model_validate(
            {
                "app_version": APP_VERSION,
                "python_version": runtime["python_version"],
                "platform": runtime["platform"],
                "build_commit": runtime["build_commit"],
                "package_versions": {}
                if model is None
                else model.response_models[0].model.package_versions,
            }
        ),
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
            expected_history_revision_id=str(request.expected_history_revision_id),
            expected_history_sha256=request.expected_history_sha256,
            total_trial_budget=request.total_trial_budget,
            allow_existing=True,
            planning_selection=(str(selection_id), selected.config_sha256, selected.result_sha256),
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    return get_augmentation_batch(settings, study_id, selection_id)


def get_augmentation_batch(
    settings: Settings, study_id: UUID, batch_id: UUID
) -> AugmentationBatchResponse:
    from app.services.bayesian_recommendation_batches import _batch_state
    from app.services.bayesian_studies import get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    record = get_bayesian_recommendation_batch_record(settings.workspace_root, str(batch_id))
    if (
        record is None
        or record.study_version_id != str(study.study_version_id)
        or record.result_schema_version not in {9, 11}
    ):
        raise _error("bayesian_planning_not_found")
    saved = AugmentationBatchResponse.model_validate_json(record.result_json)
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


def validate_augmentation_batch_record(
    settings: Settings,
    *,
    version: Any,
    factors: Any,
    objective: Any,
    constraints: Any,
    trials: Any,
    history: Any,
    record: BayesianRecommendationBatchRecord,
) -> AugmentationBatchResponse:
    from app.services.bayesian_studies import _trial_response

    def require(condition: bool) -> None:
        if not condition:
            raise ValueError("augmentation source mismatch")

    try:
        require(hashlib.sha256(record.config_json.encode()).hexdigest() == record.config_sha256)
        require(hashlib.sha256(record.result_json.encode()).hexdigest() == record.result_sha256)
        result = AugmentationBatchResponse.model_validate_json(record.result_json)
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
                4,
                "source_owned_augmentation_v1",
            )
        )
        require(record.batch_size == result.batch_size and record.batch_id == str(result.batch_id))
        require(record.study_version_id == version.study_version_id == str(result.study_version_id))
        require(
            str(result.study_id) == version.study_id
            and result.definition_sha256 == version.definition_sha256
        )
        require(
            history is not None
            and history.schema_version == 2
            and history.study_version_id == version.study_version_id
        )
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
        study = SimpleNamespace(
            study_id=UUID(version.study_id),
            study_version_id=UUID(version.study_version_id),
            definition_sha256=version.definition_sha256,
            factors=factors,
            objective=objective,
            constraints=constraints,
            trials=[_trial_response(trial) for trial in trials],
        )
        request, source = result.selection_request, result.source
        candidate, rows, identity, tolerance = _source_candidate(
            settings, study, source.candidate_revision_id
        )
        _verify_binding(study, candidate, identity, tolerance, request)
        selected = storage.get_planning_selection(
            settings.workspace_root, str(source.selection_id), version.study_version_id
        )
        require(selected is not None)
        assert selected is not None
        require(
            selected["schema_version"] == request.schema_version
            and selected["confirmed_batch_id"] == record.batch_id
        )
        require(
            selected["config_sha256"] == source.selection_config_sha256
            and selected["result_sha256"] == source.selection_result_sha256
        )
        require(selected["config_json"] == _json(request.model_dump(mode="json")))
        require(AUGMENTATION_RESULT.validate_json(selected["result_json"]) == result.calculation)
        require(selected["model_id"] == (None if source.model_id is None else str(source.model_id)))
        require(
            selected["candidate_revision_id"]
            == str(source.candidate_revision_id)
            == str(request.candidate_revision_id)
        )
        require(source.rows_sha256 == request.expected_rows_sha256)
        require(
            source.model_id == request.model_id
            and source.model_sha256 == request.expected_model_sha256
        )
        require(_json(_config(study, request, source)) == record.config_json)
        require(result.objective.model_dump(mode="json") == objective.model_dump(mode="json"))
        require(result.requested_total_trial_budget == request.total_trial_budget)
        require(request.expected_trial_count + result.batch_size <= request.total_trial_budget)
        require(result.provenance.app_version == record.app_version)
        snapshot = None
        if source.model_id is not None:
            model_record, snapshot, model_body = _read_model(settings, study, source.model_id)
            require(result.model is not None)
            assert result.model is not None
            require(source.model_sha256 == model_record["snapshot_sha256"])
            require(
                result.model.model_id == source.model_id
                and result.model.snapshot_sha256 == source.model_sha256
            )
            require(result.model.fit == model_body.fit)
            for key in (
                "objective",
                "response_models",
                "incumbent",
                "observation_view",
                "warnings",
            ):
                expected = (
                    snapshot["calculation_request"]["objective"]
                    if key == "objective"
                    else snapshot[key]
                )
                require(result.model.model_dump(mode="json")[key] == expected)
        else:
            require(result.model is None and not result.provenance.package_versions)
        validate_saved_augmentation(study, request, result.calculation, rows, snapshot)
        if isinstance(request, AutoAugmentationSelectionRequest):
            require(isinstance(result.calculation, AutoAugmentationCalculation))
            assert isinstance(result.calculation, AutoAugmentationCalculation)
            routing = _routing_context(settings, study, identity, request)
            validate_auto_evidence(
                result.calculation.auto_evidence,
                request.auto_strategy,
                identity=routing["identity"],
                snapshot=routing["snapshot"],
                policy=request.policy,
            )
        item_records = list_bayesian_recommendation_batch_item_records(
            settings.workspace_root, record.batch_id
        )
        require(len(item_records) == result.batch_size)
        by_trial, by_row = (
            {trial.trial_id: trial for trial in trials},
            {row.row_id: row for row in rows},
        )
        for item, stored, planned in zip(
            result.items, item_records, result.calculation.selected_rows, strict=True
        ):
            trial, row = by_trial[str(item.trial.trial_id)], by_row[planned.row_id]
            require(item.rank == stored.rank and item.item_id == UUID(stored.item_id))
            require(
                stored.batch_id == record.batch_id
                and stored.trial_id == trial.trial_id
                and stored.item_schema_version == 4
            )
            require(item.current_trial == item.trial and item.trial.state == "pending")
            require(item.trial.objective_value is None and item.trial.closed_at is None)
            require(
                stored.item_result_json == _json(item.model_dump(mode="json"))
                and stored.item_result_sha256 == _sha(item.model_dump(mode="json"))
            )
            require(
                item.trial.trial_number
                == trial.trial_number
                == request.expected_trial_count + item.rank
            )
            require(
                trial.study_version_id == version.study_version_id
                and trial.origin == "recommendation"
            )
            require(
                item.trial.actual_coordinates
                == planned.actual_coordinates
                == json.loads(trial.actual_coordinates_json)
            )
            require(
                item.trial.normalized_coordinates
                == planned.normalized_coordinates
                == json.loads(trial.normalized_coordinates_json)
            )
            require(
                all(getattr(planned, key) == getattr(row, key) for key in CandidateRow.model_fields)
            )
            require(item.trial.coordinates_sha256 == trial.coordinates_sha256)
            require(
                item.trial.created_at == trial.created_at == stored.created_at == record.created_at
            )
        return result
    except (ValueError, KeyError, TypeError, AttributeError, BayesianStorageConflict):
        raise _error("bayesian_planning_artifact_invalid") from None
