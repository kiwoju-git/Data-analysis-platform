"""Source-locked versioned review, atomic confirmation and no-refit vector readers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.api.v1.schemas.bayesian import (
    BayesianTrialResponse,
    BayesianVectorReplicateTrialResponse,
    BayesianVectorTrialResponse,
)
from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityAnyBatchResponse,
    DesirabilityAnyLatestResponse,
    DesirabilityAnyReviewRequest,
    DesirabilityAnyReviewResponse,
    DesirabilityBatchItem,
    DesirabilityCurveReviewResponse,
    DesirabilityFitReviewResponse,
    DesirabilityOrderedBatchItem,
    DesirabilityOrderedReviewResponse,
    DesirabilityProvenance,
    DesirabilityReviewResponse,
    parse_desirability_batch,
    parse_desirability_request,
)
from app.api.v1.schemas.bayesian_review import BayesianRecommendationReviewConfirmRequest
from app.api.v1.schemas.bo_curve_calculation import (
    DesirabilityCurveCalculationRequest,
    DesirabilityCurveCalculationResult,
)
from app.api.v1.schemas.bo_curve_policy import (
    AnyDesirabilityObjective as BayesianDesirabilityObjective,
)
from app.api.v1.schemas.bo_curve_policy import BayesianVersionedCurveObjective
from app.api.v1.schemas.bo_desirability_batch_calculation import (
    DesirabilityBatchCalculationRequest,
    DesirabilityBatchCalculationResult,
)
from app.api.v1.schemas.bo_desirability_calculation import DesirabilityCalculationRequest
from app.api.v1.schemas.bo_fit_quality import (
    DesirabilityFitCalculationRequest,
    DesirabilityFitCalculationResult,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import APP_VERSION, runtime_build_provenance, utc_now
from app.services.bayesian_noise_recommendations import _error, _json, _sha
from app.services.bo_desirability_batch_contract import validate_batch_calculation_result
from app.services.bo_desirability_contract import validate_calculation_result
from app.statistics.bayesian_optimization import BayesianOptimizationError
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


def _config(study: Any, body: DesirabilityAnyReviewRequest) -> dict[str, Any]:
    return {
        "schema_version": body.schema_version,
        "study_id": str(study.study_id),
        "study_version_id": str(study.study_version_id),
        "definition_sha256": study.definition_sha256,
        "source_trial_count": len(study.trials),
        "source_history_revision_id": str(body.expected_history_revision_id),
        "source_observation_history_sha256": body.expected_history_sha256,
        "request": body.model_dump(mode="json"),
    }


def _vector_observation(trial: Any) -> dict[str, Any]:
    if (
        not isinstance(trial, BayesianVectorTrialResponse | BayesianVectorReplicateTrialResponse)
        or trial.state != "completed"
    ):
        raise _error("bayesian_desirability_response_mapping_invalid")
    return {
        "trial_id": str(trial.trial_id),
        "actual_coordinates": trial.actual_coordinates,
        "normalized_coordinates": trial.normalized_coordinates,
        "response_values": trial.response_values,
        "condition_key": None,
    }


def _calculation_request(
    factors: list[Any],
    objective: Any,
    constraints: list[Any],
    observations: list[dict[str, Any]],
    excluded: list[dict[str, float]],
    body: DesirabilityAnyReviewRequest,
) -> (
    DesirabilityCalculationRequest
    | DesirabilityBatchCalculationRequest
    | DesirabilityFitCalculationRequest
    | DesirabilityCurveCalculationRequest
):
    payload = {
        "schema_version": body.schema_version,
        "batch_size": body.batch_size,
        "factors": [
            {
                key: getattr(f, key)
                for key in ("factor_id", "low", "high", "domain_kind", "step", "display_decimals")
            }
            for f in factors
        ],
        "objective": objective.model_dump(mode="json", include={"responses"}),
        "constraints": [c.model_dump(mode="json") for c in constraints],
        "observations": observations,
        "excluded_normalized": [[point[f.factor_id] for f in factors] for point in excluded],
        **body.model_dump(
            mode="json",
            include={
                "response_models",
                "observation_policy",
                "xi_desirability",
                "search",
                "batch_options",
                "fit_policy",
            },
        ),
    }
    if (body.schema_version == 7) != isinstance(objective, BayesianVersionedCurveObjective):
        raise _error("bayesian_desirability_response_mapping_invalid")
    if body.schema_version == 7:
        return DesirabilityCurveCalculationRequest.model_validate_json(_json(payload))
    if body.schema_version == 6:
        return DesirabilityFitCalculationRequest.model_validate_json(_json(payload))
    if body.schema_version == 5:
        return DesirabilityBatchCalculationRequest.model_validate_json(_json(payload))
    return DesirabilityCalculationRequest.model_validate_json(_json(payload))


def _source(
    settings: Settings, study_id: UUID, body: DesirabilityAnyReviewRequest
) -> tuple[Any, Any]:
    from app.services.bayesian_studies import get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    if not isinstance(study.objective, BayesianDesirabilityObjective):
        raise _error("bayesian_desirability_response_mapping_invalid")
    history = study.observation_history
    if study.status != "active":
        raise _error("bayesian_study_closed")
    if (
        body.expected_history_revision_id != history.history_revision_id
        or body.expected_history_sha256 != history.observation_history_sha256
    ):
        raise _error("bayesian_optimization_history_stale")
    if any(t.state == "pending" for t in study.trials):
        raise _error("bayesian_optimization_pending_recommendation_exists")
    completed = [t for t in study.trials if t.state == "completed"]
    unique = {_json(t.actual_coordinates) for t in completed}
    if len(unique) < study.recommendation_minimum_completed_observations:
        raise _error("bayesian_optimization_history_incomplete")
    if len(study.trials) + body.batch_size > body.total_trial_budget:
        raise _error("bayesian_optimization_batch_budget_exceeded")
    try:
        request = _calculation_request(
            study.factors,
            study.objective,
            study.constraints,
            [_vector_observation(t) for t in completed],
            [t.normalized_coordinates for t in study.trials],
            body,
        )
    except (ValidationError, AttributeError) as exc:
        raise _error("bayesian_desirability_response_mapping_invalid") from exc
    return study, request


def create_desirability_review(
    settings: Settings, store: Any, study_id: UUID, body: DesirabilityAnyReviewRequest
) -> DesirabilityAnyReviewResponse:
    from app.services import bo_desirability_worker
    from app.services.bayesian_review import REVIEW_TTL_SECONDS

    with store.calculation_slot():
        study, request = _source(settings, study_id, body)
        try:
            result = (
                bo_desirability_worker.run_desirability_batch_calculation(request).calculation
                if isinstance(
                    request,
                    DesirabilityBatchCalculationRequest
                    | DesirabilityFitCalculationRequest
                    | DesirabilityCurveCalculationRequest,
                )
                else bo_desirability_worker.run_desirability_calculation(request).calculation
            )
            current, current_request = _source(settings, study_id, body)
            _validate_calculation(current_request, result)
        except BayesianOptimizationError as exc:
            raise _error(exc.code) from exc
        if _config(study, body) != _config(current, body):
            raise _error("bayesian_optimization_history_stale")
    review_data = dict(
        review_id=uuid4(),
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        source_history_revision_id=body.expected_history_revision_id,
        source_observation_history_sha256=body.expected_history_sha256,
        config_sha256=_sha(_config(study, body)),
        calculation=result,
        expires_at=(datetime.now(timezone.utc) + timedelta(seconds=REVIEW_TTL_SECONDS)).isoformat(),
    )
    review = (
        DesirabilityCurveReviewResponse.model_validate(review_data)
        if body.schema_version == 7
        else DesirabilityFitReviewResponse.model_validate(review_data)
        if body.schema_version == 6
        else DesirabilityOrderedReviewResponse.model_validate(review_data)
        if body.schema_version == 5
        else DesirabilityReviewResponse.model_validate(review_data)
    )
    store.put_desirability(body, review)
    return review


def _validate_calculation(request: Any, result: Any) -> None:
    if isinstance(
        request,
        DesirabilityBatchCalculationRequest
        | DesirabilityFitCalculationRequest
        | DesirabilityCurveCalculationRequest,
    ):
        if not isinstance(
            result,
            DesirabilityBatchCalculationResult
            | DesirabilityFitCalculationResult
            | DesirabilityCurveCalculationResult,
        ):
            raise BayesianOptimizationError("bayesian_desirability_result_invalid")
        validate_batch_calculation_result(request, result)
    else:
        validate_calculation_result(request, result)


def _commit(
    settings: Settings,
    study: Any,
    body: DesirabilityAnyReviewRequest,
    review: DesirabilityAnyReviewResponse,
) -> None:
    created_at = utc_now()
    items: list[Any] = []
    trial_records = []
    item_records = []
    item_version = 4 if body.schema_version in {5, 6, 7} else 3
    for rank in range(1, len(review.calculation.items) + 1):
        candidate = review.calculation.items[rank - 1]
        number, trial_id, item_id = len(study.trials) + rank, uuid4(), uuid4()
        coordinates_hash = _sha(
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
            coordinates_sha256=coordinates_hash,
            objective_value=None,
            created_at=created_at,
            closed_at=None,
        )
        data = {
            "item_id": item_id,
            "batch_id": review.review_id,
            "rank": rank,
            "trial": trial,
            "current_trial": trial,
        }
        item = (
            DesirabilityOrderedBatchItem.model_validate(data)
            if body.schema_version in {5, 6, 7}
            else DesirabilityBatchItem.model_validate(data)
        )
        items.append(item)
        trial_records.append(
            BayesianTrialRecord(
                trial_id=str(trial_id),
                study_version_id=str(study.study_version_id),
                trial_number=number,
                origin="recommendation",
                state="pending",
                actual_coordinates_json=_json(trial.actual_coordinates),
                normalized_coordinates_json=_json(trial.normalized_coordinates),
                coordinates_sha256=coordinates_hash,
                objective_value=None,
                created_at=created_at,
                closed_at=None,
            )
        )
        item_payload = item.model_dump(mode="json")
        item_records.append(
            BayesianRecommendationBatchItemRecord(
                item_id=str(item_id),
                batch_id=str(review.review_id),
                trial_id=str(trial_id),
                rank=rank,
                item_schema_version=item_version,
                item_result_json=_json(item_payload),
                item_result_sha256=_sha(item_payload),
                created_at=created_at,
            )
        )
    runtime = runtime_build_provenance(settings)
    result = parse_desirability_batch(
        dict(
            result_schema_version=body.schema_version,
            batch_size=body.batch_size,
            batch_id=review.review_id,
            study_id=study.study_id,
            study_version_id=study.study_version_id,
            source_history_revision_id=body.expected_history_revision_id,
            source_observation_history_sha256=body.expected_history_sha256,
            definition_sha256=study.definition_sha256,
            calculation=review.calculation,
            items=items,
            config_sha256=review.config_sha256,
            result_sha256="0" * 64,
            created_at=created_at,
            requested_total_trial_budget=body.total_trial_budget,
            provenance=DesirabilityProvenance.model_validate(
                {
                    "app_version": APP_VERSION,
                    "python_version": runtime["python_version"],
                    "platform": runtime["platform"],
                    "build_commit": runtime["build_commit"],
                    "package_versions": review.calculation.shared_model.response_models[
                        0
                    ].model.package_versions,
                }
            ),
        )
    )
    immutable = result.model_dump(mode="json", exclude={"is_latest", "batch_state"})
    immutable["result_sha256"] = _sha(immutable)
    result_json = _json(immutable)
    config_json = _json(_config(study, body))
    record = BayesianRecommendationBatchRecord(
        batch_id=str(review.review_id),
        study_version_id=str(study.study_version_id),
        source_history_revision_id=str(body.expected_history_revision_id),
        source_observation_history_sha256=body.expected_history_sha256,
        method_id=result.method_id,
        method_version=result.method_version,
        batch_size=result.batch_size,
        batch_policy=result.batch_policy,
        config_schema_version=result.config_schema_version,
        result_schema_version=result.result_schema_version,
        model_schema_version=result.model_schema_version,
        item_schema_version=result.item_schema_version,
        config_json=config_json,
        config_sha256=review.config_sha256,
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode()).hexdigest(),
        created_at=created_at,
        app_version=APP_VERSION,
    )
    try:
        insert_bayesian_recommendation_batch_bundle(
            settings.workspace_root,
            trials=trial_records,
            batch=record,
            items=item_records,
            expected_history_revision_id=str(body.expected_history_revision_id),
            expected_history_sha256=body.expected_history_sha256,
            total_trial_budget=body.total_trial_budget,
            allow_existing=True,
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc


def _replay(
    settings: Settings, study_id: UUID, review_id: UUID, expected_hash: str
) -> DesirabilityAnyBatchResponse | None:
    record = get_bayesian_recommendation_batch_record(settings.workspace_root, str(review_id))
    if record is None:
        return None
    if record.config_sha256 != expected_hash or record.result_schema_version not in {4, 5, 6, 7}:
        raise _error("bayesian_review_mismatch")
    return get_desirability_recommendation(settings, study_id, review_id)


def confirm_desirability_review(
    settings: Settings,
    store: Any,
    study_id: UUID,
    review_id: UUID,
    body: BayesianRecommendationReviewConfirmRequest,
) -> DesirabilityAnyBatchResponse:
    existing = _replay(settings, study_id, review_id, body.expected_config_sha256)
    if existing is not None:
        return existing
    try:
        request, review = store.get_desirability(review_id)
        if review.study_id != study_id or review.config_sha256 != body.expected_config_sha256:
            raise _error("bayesian_review_mismatch")
        study, payload = _source(settings, study_id, request)
        if _sha(_config(study, request)) != review.config_sha256:
            raise _error("bayesian_optimization_history_stale")
        try:
            _validate_calculation(payload, review.calculation)
        except BayesianOptimizationError as exc:
            raise _error(exc.code) from exc
        _commit(settings, study, request, review)
    except ApiError:
        replay = _replay(settings, study_id, review_id, body.expected_config_sha256)
        if replay is not None:
            return replay
        raise
    result = _replay(settings, study_id, review_id, body.expected_config_sha256)
    if result is None:
        raise _error()
    store.discard(review_id)
    return result


def current_desirability_response(
    study: Any, record: BayesianRecommendationBatchRecord, *, is_latest: bool
) -> DesirabilityAnyBatchResponse:
    # Called only after the entire study graph has been validated.
    from app.services.bayesian_recommendation_batches import _batch_state

    result = parse_desirability_batch(json.loads(record.result_json))
    current = {t.trial_id: t for t in study.trials}
    items = [
        item.model_copy(update={"current_trial": current[item.trial.trial_id]})
        for item in result.items
    ]
    return result.model_copy(
        update={
            "items": items,
            "is_latest": is_latest,
            "batch_state": _batch_state(items),
        }
    )


def get_desirability_recommendation(
    settings: Settings, study_id: UUID, batch_id: UUID
) -> DesirabilityAnyBatchResponse:
    from app.services.bayesian_studies import get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    record = get_bayesian_recommendation_batch_record(settings.workspace_root, str(batch_id))
    if (
        record is None
        or record.study_version_id != str(study.study_version_id)
        or record.result_schema_version not in {4, 5, 6, 7}
    ):
        raise ApiError(
            code="bayesian_recommendation_batch_not_found",
            message="The requested recommendation was not found.",
            status_code=404,
        )
    latest = get_latest_bayesian_recommendation_batch_record(
        settings.workspace_root, record.study_version_id
    )
    return current_desirability_response(
        study, record, is_latest=latest is not None and latest.batch_id == record.batch_id
    )


def latest_desirability_recommendation(
    settings: Settings, study_id: UUID
) -> DesirabilityAnyLatestResponse:
    from app.services.bayesian_studies import get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    if not isinstance(study.objective, BayesianDesirabilityObjective):
        raise _error("bayesian_desirability_response_mapping_invalid")
    record = get_latest_bayesian_recommendation_batch_record(
        settings.workspace_root, str(study.study_version_id), automatic_desirability_only=True
    )
    latest = get_latest_bayesian_recommendation_batch_record(
        settings.workspace_root, str(study.study_version_id)
    )
    return DesirabilityAnyLatestResponse(
        item=None
        if record is None
        else current_desirability_response(
            study, record, is_latest=latest is not None and latest.batch_id == record.batch_id
        )
    )


def validate_desirability_record(
    settings: Settings,
    *,
    version: Any,
    factors: list[Any],
    objective: Any,
    constraints: list[Any],
    trials: list[Any],
    history: Any,
    record: BayesianRecommendationBatchRecord,
) -> DesirabilityAnyBatchResponse:
    from app.services.bayesian_studies import _json_dict, _trial_response

    def require(condition: bool) -> None:
        if not condition:
            raise _error()

    try:
        require(isinstance(objective, BayesianDesirabilityObjective))
        require(hashlib.sha256(record.config_json.encode()).hexdigest() == record.config_sha256)
        require(hashlib.sha256(record.result_json.encode()).hexdigest() == record.result_sha256)
        config = _json_dict(record.config_json)
        require(_json(config) == record.config_json)
        body = parse_desirability_request(config["request"])
        result = parse_desirability_batch(json.loads(record.result_json))
        schema = body.schema_version
        method_version = {4: "0.9.0", 5: "0.10.0", 6: "0.11.0", 7: "0.12.0"}[schema]
        item_schema = 4 if schema in {5, 6, 7} else 3
        require(result.result_schema_version == schema and result.batch_size == body.batch_size)
        identity = {
            "study_id": version.study_id,
            "study_version_id": version.study_version_id,
            "definition_sha256": version.definition_sha256,
            "source_history_revision_id": record.source_history_revision_id,
            "source_observation_history_sha256": record.source_observation_history_sha256,
        }
        require(
            config
            == {
                "schema_version": schema,
                **identity,
                "request": body.model_dump(mode="json"),
                "source_trial_count": result.items[0].trial.trial_number - 1,
            }
        )
        require(all(str(getattr(result, k)) == v for k, v in identity.items()))
        require(
            (
                record.method_id,
                record.method_version,
                record.config_schema_version,
                record.result_schema_version,
                record.model_schema_version,
                record.item_schema_version,
                record.batch_size,
                record.batch_policy,
            )
            == (
                result.method_id,
                method_version,
                schema,
                schema,
                schema if schema in {6, 7} else 5,
                item_schema,
                body.batch_size,
                result.batch_policy,
            )
        )
        require(record.study_version_id == version.study_version_id)
        require(record.batch_id == str(result.batch_id) and record.created_at == result.created_at)
        require(result.config_sha256 == record.config_sha256)
        require(result.requested_total_trial_budget == body.total_trial_budget)
        require(result.provenance.app_version == record.app_version)
        require(
            all(
                m.model.package_versions == result.provenance.package_versions
                for m in result.calculation.shared_model.response_models
            )
        )
        immutable = result.model_dump(mode="json", exclude={"is_latest", "batch_state"})
        require(_json(immutable) == record.result_json)
        immutable["result_sha256"] = "0" * 64
        require(_sha(immutable) == result.result_sha256)
        require(
            history is not None
            and history.schema_version == 2
            and history.study_version_id == version.study_version_id
            and history.observation_history_sha256 == record.source_observation_history_sha256
        )
        require(
            str(body.expected_history_revision_id) == record.source_history_revision_id
            and body.expected_history_sha256 == record.source_observation_history_sha256
        )
        trial_map = {t.trial_id: t for t in trials}
        number = result.items[0].trial.trial_number
        source = [
            _trial_response(trial_map[k]) for k in json.loads(history.completed_trial_ids_json)
        ]
        request = _calculation_request(
            factors,
            objective,
            constraints,
            [_vector_observation(t) for t in source],
            [json.loads(t.normalized_coordinates_json) for t in trials if t.trial_number < number],
            body,
        )
        _validate_calculation(request, result.calculation)
        records = list_bayesian_recommendation_batch_item_records(
            settings.workspace_root, record.batch_id
        )
        require(
            len(records) == len(result.items) == len(result.calculation.items) == body.batch_size
        )
        require(len({str(item.trial.trial_id) for item in result.items}) == body.batch_size)
        for rank in range(1, body.batch_size + 1):
            stored = records[rank - 1]
            item = result.items[rank - 1]
            candidate = result.calculation.items[rank - 1]
            trial = trial_map[str(item.trial.trial_id)]
            require(
                (
                    stored.item_id,
                    stored.batch_id,
                    stored.trial_id,
                    stored.rank,
                    stored.item_schema_version,
                )
                == (str(item.item_id), record.batch_id, trial.trial_id, rank, item_schema)
            )
            require(item.rank == candidate.rank == rank)
            require(item.trial.trial_number - rank == config["source_trial_count"])
            require(item.batch_id == result.batch_id and stored.created_at == record.created_at)
            require(
                stored.item_result_json == _json(item.model_dump(mode="json"))
                and stored.item_result_sha256 == _sha(item.model_dump(mode="json"))
            )
            require(
                trial.origin == "recommendation"
                and trial.study_version_id == record.study_version_id
            )
            require(
                item.current_trial == item.trial
                and item.trial.state == "pending"
                and item.trial.objective_value is None
                and item.trial.closed_at is None
            )
            require(
                item.trial.actual_coordinates
                == candidate.actual_coordinates
                == json.loads(trial.actual_coordinates_json)
            )
            require(
                item.trial.normalized_coordinates
                == candidate.normalized_coordinates
                == json.loads(trial.normalized_coordinates_json)
            )
            require(
                item.trial.trial_number == trial.trial_number
                and item.trial.created_at == trial.created_at == result.created_at
                and str(item.trial.study_version_id) == record.study_version_id
                and item.trial.coordinates_sha256 == trial.coordinates_sha256
            )
        require(
            number + body.batch_size - 1 <= body.total_trial_budget
            and all(t.trial_number < number for t in source)
        )
        return result
    except (KeyError, TypeError, ValueError, AttributeError, BayesianOptimizationError) as exc:
        raise _error() from exc
