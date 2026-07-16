from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from typing import Any, Final, Literal, cast
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS, get_analysis_method
from app.api.v1.schemas.analyses import MethodAvailability
from app.api.v1.schemas.bayesian import (
    BayesianConstraintTermResponse,
    BayesianFactorResponse,
    BayesianHistoryListResponse,
    BayesianHistoryRevisionResponse,
    BayesianInitialDesignResponse,
    BayesianLinearConstraintResponse,
    BayesianObjectiveResponse,
    BayesianObservationCreateRequest,
    BayesianStudyCreateRequest,
    BayesianStudyListResponse,
    BayesianStudyResponse,
    BayesianStudySummaryResponse,
    BayesianTrialListResponse,
    BayesianTrialResponse,
    BayesianTrialTransitionResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import APP_VERSION, canonical_json_bytes, utc_now
from app.services.bayesian_recommendation_consistency import (
    validate_bayesian_recommendation_record,
)
from app.storage.bayesian_studies import (
    BayesianHistoryRevisionRecord,
    BayesianRecommendationRecord,
    BayesianStorageConflict,
    BayesianStudyRecord,
    BayesianStudyVersionRecord,
    BayesianTrialRecord,
    abandon_bayesian_trial_record,
    complete_bayesian_trial_record,
    count_bayesian_history_revision_records,
    count_bayesian_recommendation_records,
    count_bayesian_study_records,
    count_bayesian_trial_records,
    get_bayesian_history_revision_record,
    get_bayesian_recommendation_record_for_trial,
    get_bayesian_study_record,
    get_bayesian_study_version_record,
    get_current_bayesian_history_revision_record,
    insert_bayesian_study_bundle,
    list_bayesian_history_revision_records,
    list_bayesian_recommendation_records,
    list_bayesian_study_records,
    list_bayesian_trial_records,
)

BAYESIAN_METHOD_ID: Final = "doe.bayesian_optimization"
BAYESIAN_STUDY_SCHEMA_VERSION: Final[Literal[1]] = 1
BAYESIAN_HISTORY_SCHEMA_VERSION: Final[Literal[1]] = 1
SUPPORTED_BAYESIAN_STUDY_METHOD_VERSIONS: Final = frozenset({"0.1.0", "0.2.0"})
INITIAL_DESIGN_POLICY: Final[Literal["sha256_counter_uniform_feasible_v1"]] = (
    "sha256_counter_uniform_feasible_v1"
)
MAX_GENERATION_ATTEMPTS_PER_TRIAL: Final = 1_000


@dataclass(frozen=True)
class _ValidatedStudy:
    study: BayesianStudyRecord
    version: BayesianStudyVersionRecord
    factors: list[BayesianFactorResponse]
    objective: BayesianObjectiveResponse
    constraints: list[BayesianLinearConstraintResponse]
    initial_design: BayesianInitialDesignResponse
    trials: list[BayesianTrialRecord]
    histories: list[BayesianHistoryRevisionRecord]
    current_history: BayesianHistoryRevisionRecord
    recommendations: list[BayesianRecommendationRecord]


def create_bayesian_study(
    settings: Settings, body: BayesianStudyCreateRequest
) -> BayesianStudyResponse:
    method = get_analysis_method(BAYESIAN_METHOD_ID)
    method_version = METHOD_VERSIONS[BAYESIAN_METHOD_ID]
    if (
        method is None
        or method.method_version != method_version
        or method.availability != MethodAvailability.AVAILABLE
    ):
        raise _metadata_error()
    if not body.name.strip():
        raise ApiError(
            code="bayesian_study_name_invalid",
            message="Bayesian study 이름이 필요합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    factors = _validated_factor_payload(body)
    objective = _validated_objective_payload(body)
    constraints = _validated_constraint_payload(body, factors)
    actual_points, normalized_points, attempts_consumed = _generate_initial_design(
        factors=factors,
        constraints=constraints,
        seed=body.initial_design_seed,
        size=body.initial_design_size,
    )
    initial_design = BayesianInitialDesignResponse(
        policy=INITIAL_DESIGN_POLICY,
        seed=body.initial_design_seed,
        requested_size=body.initial_design_size,
        generated_size=len(actual_points),
        attempt_limit=body.initial_design_size * MAX_GENERATION_ATTEMPTS_PER_TRIAL,
        attempts_consumed=attempts_consumed,
    )
    definition_payload = _definition_payload(
        method_version=method_version,
        factors=factors,
        objective=objective,
        constraints=constraints,
        initial_design=initial_design,
    )
    definition_sha256 = _sha256(definition_payload)
    now = utc_now()
    study_id = str(uuid4())
    study_version_id = str(uuid4())
    study = BayesianStudyRecord(
        study_id=study_id,
        method_id=BAYESIAN_METHOD_ID,
        method_version=method_version,
        name=body.name.strip(),
        status="active",
        current_version=1,
        created_at=now,
        updated_at=now,
        app_version=APP_VERSION,
    )
    version = BayesianStudyVersionRecord(
        study_version_id=study_version_id,
        study_id=study_id,
        version_number=1,
        schema_version=BAYESIAN_STUDY_SCHEMA_VERSION,
        factors_json=_json_dumps([item.model_dump(mode="json") for item in factors]),
        objective_json=_json_dumps(objective.model_dump(mode="json")),
        constraints_json=_json_dumps([item.model_dump(mode="json") for item in constraints]),
        initial_design_json=_json_dumps(initial_design.model_dump(mode="json")),
        definition_sha256=definition_sha256,
        created_at=now,
    )
    trials = [
        _new_trial_record(
            study_version_id=study_version_id,
            definition_sha256=definition_sha256,
            trial_number=index + 1,
            actual=actual,
            normalized=normalized,
            created_at=now,
        )
        for index, (actual, normalized) in enumerate(
            zip(actual_points, normalized_points, strict=True)
        )
    ]
    initial_history = _new_history_record(
        study_version_id=study_version_id,
        definition_sha256=definition_sha256,
        revision_number=1,
        completed_trials=[],
        previous_history_sha256=None,
        created_at=now,
    )
    insert_bayesian_study_bundle(
        settings.workspace_root,
        study=study,
        version=version,
        trials=trials,
        initial_history=initial_history,
    )
    return _study_response(
        _ValidatedStudy(
            study=study,
            version=version,
            factors=factors,
            objective=objective,
            constraints=constraints,
            initial_design=initial_design,
            trials=trials,
            histories=[initial_history],
            current_history=initial_history,
            recommendations=[],
        )
    )


def get_bayesian_study(settings: Settings, study_id: UUID) -> BayesianStudyResponse:
    return _study_response(_load_validated_study(settings, str(study_id)))


def list_bayesian_studies(
    settings: Settings, *, offset: int, limit: int
) -> BayesianStudyListResponse:
    records = list_bayesian_study_records(settings.workspace_root, offset=offset, limit=limit)
    items = [_study_summary(_load_validated_study(settings, record.study_id)) for record in records]
    return BayesianStudyListResponse(
        total=count_bayesian_study_records(settings.workspace_root),
        offset=offset,
        limit=limit,
        items=items,
    )


def list_bayesian_trials(
    settings: Settings,
    study_id: UUID,
    *,
    offset: int,
    limit: int,
) -> BayesianTrialListResponse:
    bundle = _load_validated_study(settings, str(study_id))
    page = bundle.trials[offset : offset + limit]
    return BayesianTrialListResponse(
        study_id=UUID(bundle.study.study_id),
        study_version_id=UUID(bundle.version.study_version_id),
        total=len(bundle.trials),
        offset=offset,
        limit=limit,
        items=[_trial_response(item) for item in page],
    )


def complete_bayesian_trial(
    settings: Settings,
    study_id: UUID,
    trial_id: UUID,
    body: BayesianObservationCreateRequest,
) -> BayesianTrialTransitionResponse:
    bundle = _load_validated_study(settings, str(study_id))
    trial = _trial_for_transition(bundle, str(trial_id))
    if trial.state != "pending":
        raise _trial_state_error()
    if str(body.expected_history_revision_id) != bundle.current_history.history_revision_id:
        raise _history_stale_error()
    if trial.origin == "recommendation":
        recommendation = get_bayesian_recommendation_record_for_trial(
            settings.workspace_root, trial.trial_id
        )
        if (
            recommendation is None
            or recommendation.source_observation_history_sha256
            != bundle.current_history.observation_history_sha256
        ):
            raise ApiError(
                code="bayesian_optimization_history_stale",
                message="Recommendation 생성 이후 관측 이력이 변경되어 새 추천이 필요합니다.",
                status_code=status.HTTP_409_CONFLICT,
            )

    now = utc_now()
    completed_trial = replace(
        trial,
        state="completed",
        objective_value=float(body.objective_value),
        closed_at=now,
    )
    completed = [item for item in bundle.trials if item.state == "completed"]
    completed.append(completed_trial)
    completed.sort(key=lambda item: item.trial_number)
    new_history = _new_history_record(
        study_version_id=bundle.version.study_version_id,
        definition_sha256=bundle.version.definition_sha256,
        revision_number=bundle.current_history.revision_number + 1,
        completed_trials=completed,
        previous_history_sha256=bundle.current_history.observation_history_sha256,
        created_at=now,
    )
    try:
        complete_bayesian_trial_record(
            settings.workspace_root,
            trial_id=trial.trial_id,
            objective_value=float(body.objective_value),
            closed_at=now,
            expected_history_revision_id=bundle.current_history.history_revision_id,
            new_history=new_history,
        )
    except BayesianStorageConflict as exc:
        raise _history_stale_error() from exc
    return BayesianTrialTransitionResponse(
        study_id=study_id,
        trial=_trial_response(completed_trial),
        observation_history=_history_response(new_history),
    )


def abandon_bayesian_trial(
    settings: Settings, study_id: UUID, trial_id: UUID
) -> BayesianTrialTransitionResponse:
    bundle = _load_validated_study(settings, str(study_id))
    trial = _trial_for_transition(bundle, str(trial_id))
    if trial.state != "pending":
        raise _trial_state_error()
    now = utc_now()
    abandoned = replace(trial, state="abandoned", closed_at=now)
    try:
        abandon_bayesian_trial_record(
            settings.workspace_root,
            trial_id=trial.trial_id,
            study_version_id=bundle.version.study_version_id,
            closed_at=now,
        )
    except BayesianStorageConflict as exc:
        raise _trial_state_error() from exc
    return BayesianTrialTransitionResponse(
        study_id=study_id,
        trial=_trial_response(abandoned),
        observation_history=_history_response(bundle.current_history),
    )


def list_bayesian_history(
    settings: Settings,
    study_id: UUID,
    *,
    offset: int,
    limit: int,
) -> BayesianHistoryListResponse:
    bundle = _load_validated_study(settings, str(study_id))
    descending = list(reversed(bundle.histories))
    page = descending[offset : offset + limit]
    return BayesianHistoryListResponse(
        study_id=study_id,
        study_version_id=UUID(bundle.version.study_version_id),
        total=len(bundle.histories),
        offset=offset,
        limit=limit,
        items=[_history_response(item) for item in page],
    )


def get_bayesian_history(
    settings: Settings, study_id: UUID, history_revision_id: UUID
) -> BayesianHistoryRevisionResponse:
    bundle = _load_validated_study(settings, str(study_id))
    record = get_bayesian_history_revision_record(settings.workspace_root, str(history_revision_id))
    if record is None or record.study_version_id != bundle.version.study_version_id:
        raise ApiError(
            code="bayesian_observation_history_not_found",
            message="요청한 Bayesian 관측 history revision을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    matched = next(
        (
            item
            for item in bundle.histories
            if item.history_revision_id == record.history_revision_id
        ),
        None,
    )
    if matched is None:
        raise _metadata_error()
    return _history_response(matched)


def canonical_bayesian_observation_history_sha256(
    *, definition_sha256: str, completed_trials: list[BayesianTrialRecord]
) -> str:
    ordered = sorted(completed_trials, key=lambda item: item.trial_number)
    return _sha256(
        {
            "schema_version": BAYESIAN_HISTORY_SCHEMA_VERSION,
            "definition_sha256": definition_sha256,
            "completed_observations": [
                {
                    "trial_id": item.trial_id,
                    "trial_number": item.trial_number,
                    "coordinates_sha256": item.coordinates_sha256,
                    "objective_value": item.objective_value,
                }
                for item in ordered
            ],
        }
    )


def _load_validated_study(settings: Settings, study_id: str) -> _ValidatedStudy:
    study = get_bayesian_study_record(settings.workspace_root, study_id)
    if study is None:
        raise ApiError(
            code="bayesian_study_not_found",
            message="요청한 Bayesian study를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    method = get_analysis_method(BAYESIAN_METHOD_ID)
    expected_version = METHOD_VERSIONS[BAYESIAN_METHOD_ID]
    if (
        study.method_id != BAYESIAN_METHOD_ID
        or study.method_version not in SUPPORTED_BAYESIAN_STUDY_METHOD_VERSIONS
        or method is None
        or method.method_version != expected_version
        or method.availability != MethodAvailability.AVAILABLE
        or study.status not in {"active", "completed", "abandoned"}
        or study.current_version != 1
        or not study.name.strip()
    ):
        raise _metadata_error()
    version = get_bayesian_study_version_record(
        settings.workspace_root,
        study_id=study.study_id,
        version_number=study.current_version,
    )
    if (
        version is None
        or version.study_id != study.study_id
        or version.version_number != study.current_version
        or version.schema_version != BAYESIAN_STUDY_SCHEMA_VERSION
    ):
        raise _metadata_error()
    try:
        factors = [
            BayesianFactorResponse.model_validate(item) for item in _json_list(version.factors_json)
        ]
        objective = BayesianObjectiveResponse.model_validate(_json_dict(version.objective_json))
        constraints = [
            BayesianLinearConstraintResponse.model_validate(item)
            for item in _json_list(version.constraints_json)
        ]
        initial_design = BayesianInitialDesignResponse.model_validate(
            _json_dict(version.initial_design_json)
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise _metadata_error() from exc
    if (
        _sha256(
            _definition_payload(
                method_version=study.method_version,
                factors=factors,
                objective=objective,
                constraints=constraints,
                initial_design=initial_design,
            )
        )
        != version.definition_sha256
    ):
        raise _artifact_error()
    _validate_factor_and_constraint_metadata(factors, constraints)
    try:
        expected_actual, expected_normalized, expected_attempts = _generate_initial_design(
            factors=factors,
            constraints=constraints,
            seed=initial_design.seed,
            size=initial_design.requested_size,
        )
    except ApiError as exc:
        raise _artifact_error() from exc
    if (
        initial_design.policy != INITIAL_DESIGN_POLICY
        or initial_design.generated_size != initial_design.requested_size
        or initial_design.generated_size != len(expected_actual)
        or initial_design.attempt_limit
        != initial_design.requested_size * MAX_GENERATION_ATTEMPTS_PER_TRIAL
        or initial_design.attempts_consumed != expected_attempts
    ):
        raise _artifact_error()
    trials = list_bayesian_trial_records(
        settings.workspace_root, version.study_version_id, limit=200
    )
    if (
        count_bayesian_trial_records(settings.workspace_root, version.study_version_id)
        != len(trials)
        or not initial_design.generated_size <= len(trials) <= 200
    ):
        raise _artifact_error()
    _validate_trials(
        version,
        factors,
        constraints,
        trials,
        expected_actual=expected_actual,
        expected_normalized=expected_normalized,
    )
    histories = list_bayesian_history_revision_records(
        settings.workspace_root,
        version.study_version_id,
        limit=200,
        ascending=True,
    )
    if count_bayesian_history_revision_records(
        settings.workspace_root, version.study_version_id
    ) != len(histories):
        raise _artifact_error()
    current_history = get_current_bayesian_history_revision_record(
        settings.workspace_root, version.study_version_id
    )
    if current_history is None:
        raise _artifact_error()
    _validate_histories(version, trials, histories, current_history)
    recommendations = list_bayesian_recommendation_records(
        settings.workspace_root,
        version.study_version_id,
        limit=200,
    )
    if count_bayesian_recommendation_records(
        settings.workspace_root, version.study_version_id
    ) != len(recommendations):
        raise _artifact_error()
    _validate_recommendations(
        version,
        factors,
        objective,
        constraints,
        trials,
        histories,
        recommendations,
    )
    return _ValidatedStudy(
        study=study,
        version=version,
        factors=factors,
        objective=objective,
        constraints=constraints,
        initial_design=initial_design,
        trials=trials,
        histories=histories,
        current_history=current_history,
        recommendations=recommendations,
    )


def _validated_factor_payload(
    body: BayesianStudyCreateRequest,
) -> list[BayesianFactorResponse]:
    factors = [
        BayesianFactorResponse(
            factor_id=item.factor_id,
            name=item.name.strip(),
            low=float(item.low),
            high=float(item.high),
            unit=None if item.unit is None else item.unit.strip() or None,
            order=index + 1,
            scaling_rule="linear_0_1",
        )
        for index, item in enumerate(body.factors)
    ]
    ids = [item.factor_id for item in factors]
    names = [item.name.casefold() for item in factors]
    if (
        len(set(ids)) != len(ids)
        or len(set(names)) != len(names)
        or any(not item.name or not item.low < item.high for item in factors)
    ):
        raise ApiError(
            code="bayesian_study_factor_space_invalid",
            message="Bayesian study 요인은 고유한 ID/이름과 유한한 low < high가 필요합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return factors


def _validated_objective_payload(
    body: BayesianStudyCreateRequest,
) -> BayesianObjectiveResponse:
    name = body.objective.name.strip()
    if not name:
        raise ApiError(
            code="bayesian_study_objective_invalid",
            message="Bayesian study의 수동 관측 objective 이름이 필요합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return BayesianObjectiveResponse(
        name=name,
        unit=None if body.objective.unit is None else body.objective.unit.strip() or None,
        direction=body.objective.direction,
        observation_policy=body.objective.observation_policy,
    )


def _validated_constraint_payload(
    body: BayesianStudyCreateRequest,
    factors: list[BayesianFactorResponse],
) -> list[BayesianLinearConstraintResponse]:
    factor_ids = {item.factor_id for item in factors}
    ids: set[str] = set()
    constraints: list[BayesianLinearConstraintResponse] = []
    for item in body.constraints:
        term_ids = [term.factor_id for term in item.terms]
        if (
            item.constraint_id in ids
            or not item.name.strip()
            or len(set(term_ids)) != len(term_ids)
            or not set(term_ids).issubset(factor_ids)
            or all(float(term.coefficient) == 0.0 for term in item.terms)
        ):
            raise ApiError(
                code="bayesian_study_constraint_invalid",
                message=(
                    "Bayesian study 제약은 고유 ID와 알려진 요인의 " "유한한 선형 항이 필요합니다."
                ),
                status_code=status.HTTP_409_CONFLICT,
            )
        ids.add(item.constraint_id)
        constraints.append(
            BayesianLinearConstraintResponse(
                constraint_id=item.constraint_id,
                name=item.name.strip(),
                terms=[
                    BayesianConstraintTermResponse(
                        factor_id=term.factor_id,
                        coefficient=float(term.coefficient),
                    )
                    for term in item.terms
                ],
                relation=item.relation,
                bound=float(item.bound),
            )
        )
    return constraints


def _generate_initial_design(
    *,
    factors: list[BayesianFactorResponse],
    constraints: list[BayesianLinearConstraintResponse],
    seed: int,
    size: int,
) -> tuple[list[dict[str, float]], list[dict[str, float]], int]:
    attempt_limit = size * MAX_GENERATION_ATTEMPTS_PER_TRIAL
    actual_points: list[dict[str, float]] = []
    normalized_points: list[dict[str, float]] = []
    fingerprints: set[str] = set()
    attempts = 0
    while len(actual_points) < size and attempts < attempt_limit:
        attempts += 1
        normalized = {
            item.factor_id: _counter_uniform(seed, attempts, item.order) for item in factors
        }
        actual = {
            item.factor_id: item.low + normalized[item.factor_id] * (item.high - item.low)
            for item in factors
        }
        if not _constraints_satisfied(actual, constraints):
            continue
        fingerprint = _sha256({"actual_coordinates": actual})
        if fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        actual_points.append(actual)
        normalized_points.append(normalized)
    if len(actual_points) != size:
        raise ApiError(
            code="bayesian_study_initial_design_infeasible",
            message="지정된 attempt 예산 안에서 제약을 만족하는 초기 실험점을 만들 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return actual_points, normalized_points, attempts


def _new_trial_record(
    *,
    study_version_id: str,
    definition_sha256: str,
    trial_number: int,
    actual: dict[str, float],
    normalized: dict[str, float],
    created_at: str,
) -> BayesianTrialRecord:
    coordinates_sha256 = _sha256(
        {
            "definition_sha256": definition_sha256,
            "trial_number": trial_number,
            "origin": "initial_design",
            "actual_coordinates": actual,
            "normalized_coordinates": normalized,
        }
    )
    return BayesianTrialRecord(
        trial_id=str(uuid4()),
        study_version_id=study_version_id,
        trial_number=trial_number,
        origin="initial_design",
        state="pending",
        actual_coordinates_json=_json_dumps(actual),
        normalized_coordinates_json=_json_dumps(normalized),
        coordinates_sha256=coordinates_sha256,
        objective_value=None,
        created_at=created_at,
        closed_at=None,
    )


def _new_history_record(
    *,
    study_version_id: str,
    definition_sha256: str,
    revision_number: int,
    completed_trials: list[BayesianTrialRecord],
    previous_history_sha256: str | None,
    created_at: str,
) -> BayesianHistoryRevisionRecord:
    ordered = sorted(completed_trials, key=lambda item: item.trial_number)
    return BayesianHistoryRevisionRecord(
        history_revision_id=str(uuid4()),
        study_version_id=study_version_id,
        revision_number=revision_number,
        schema_version=BAYESIAN_HISTORY_SCHEMA_VERSION,
        completed_trial_ids_json=_json_dumps([item.trial_id for item in ordered]),
        completed_trial_count=len(ordered),
        observation_history_sha256=canonical_bayesian_observation_history_sha256(
            definition_sha256=definition_sha256,
            completed_trials=ordered,
        ),
        previous_history_sha256=previous_history_sha256,
        created_at=created_at,
    )


def _validate_factor_and_constraint_metadata(
    factors: list[BayesianFactorResponse],
    constraints: list[BayesianLinearConstraintResponse],
) -> None:
    ids = [item.factor_id for item in factors]
    names = [item.name.casefold() for item in factors]
    expected_order = list(range(1, len(factors) + 1))
    constraint_ids = [item.constraint_id for item in constraints]
    if (
        not 1 <= len(factors) <= 6
        or len(ids) != len(set(ids))
        or len(names) != len(set(names))
        or [item.order for item in factors] != expected_order
        or any(not math.isfinite(item.low) or not item.low < item.high for item in factors)
        or len(constraint_ids) != len(set(constraint_ids))
    ):
        raise _metadata_error()
    factor_ids = set(ids)
    for constraint in constraints:
        term_ids = [term.factor_id for term in constraint.terms]
        if (
            not term_ids
            or len(term_ids) != len(set(term_ids))
            or not set(term_ids).issubset(factor_ids)
            or all(term.coefficient == 0.0 for term in constraint.terms)
        ):
            raise _metadata_error()


def _validate_trials(
    version: BayesianStudyVersionRecord,
    factors: list[BayesianFactorResponse],
    constraints: list[BayesianLinearConstraintResponse],
    trials: list[BayesianTrialRecord],
    *,
    expected_actual: list[dict[str, float]],
    expected_normalized: list[dict[str, float]],
) -> None:
    factor_ids = {item.factor_id for item in factors}
    if [item.trial_number for item in trials] != list(range(1, len(trials) + 1)):
        raise _artifact_error()
    seen_coordinates: set[str] = set()
    for trial in trials:
        try:
            actual = _numeric_json_dict(trial.actual_coordinates_json)
            normalized = _numeric_json_dict(trial.normalized_coordinates_json)
        except (TypeError, ValueError) as exc:
            raise _artifact_error() from exc
        initial_index = trial.trial_number - 1
        is_initial = initial_index < len(expected_actual)
        if (
            trial.study_version_id != version.study_version_id
            or trial.origin not in {"initial_design", "recommendation"}
            or (is_initial and trial.origin != "initial_design")
            or (not is_initial and trial.origin != "recommendation")
            or trial.state not in {"pending", "completed", "abandoned"}
            or set(actual) != factor_ids
            or set(normalized) != factor_ids
            or not _constraints_satisfied(actual, constraints)
            or (is_initial and actual != expected_actual[initial_index])
            or (is_initial and normalized != expected_normalized[initial_index])
        ):
            raise _artifact_error()
        for factor in factors:
            value = actual[factor.factor_id]
            normalized_value = normalized[factor.factor_id]
            expected_normalized_value = (value - factor.low) / (factor.high - factor.low)
            if (
                value < factor.low
                or value > factor.high
                or normalized_value < 0.0
                or normalized_value > 1.0
                or not math.isclose(
                    normalized_value,
                    expected_normalized_value,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                raise _artifact_error()
        expected_sha = _sha256(
            {
                "definition_sha256": version.definition_sha256,
                "trial_number": trial.trial_number,
                "origin": trial.origin,
                "actual_coordinates": actual,
                "normalized_coordinates": normalized,
            }
        )
        coordinate_fingerprint = _sha256(
            {
                "actual_coordinates": actual,
                "normalized_coordinates": normalized,
            }
        )
        if expected_sha != trial.coordinates_sha256 or coordinate_fingerprint in seen_coordinates:
            raise _artifact_error()
        seen_coordinates.add(coordinate_fingerprint)
        if trial.state == "pending" and (
            trial.objective_value is not None or trial.closed_at is not None
        ):
            raise _artifact_error()
        if trial.state == "completed" and (
            trial.objective_value is None
            or not math.isfinite(trial.objective_value)
            or trial.closed_at is None
        ):
            raise _artifact_error()
        if trial.state == "abandoned" and (
            trial.objective_value is not None or trial.closed_at is None
        ):
            raise _artifact_error()


def _validate_histories(
    version: BayesianStudyVersionRecord,
    trials: list[BayesianTrialRecord],
    histories: list[BayesianHistoryRevisionRecord],
    current: BayesianHistoryRevisionRecord,
) -> None:
    completed_by_id = {item.trial_id: item for item in trials if item.state == "completed"}
    if (
        len(histories) != len(completed_by_id) + 1
        or [item.revision_number for item in histories] != list(range(1, len(histories) + 1))
        or current.history_revision_id != histories[-1].history_revision_id
        or current.study_version_id != version.study_version_id
    ):
        raise _artifact_error()
    previous_ids: list[str] = []
    previous_sha: str | None = None
    for index, history in enumerate(histories):
        try:
            completed_ids = _json_string_list(history.completed_trial_ids_json)
        except (TypeError, ValueError) as exc:
            raise _artifact_error() from exc
        if (
            history.study_version_id != version.study_version_id
            or history.schema_version != BAYESIAN_HISTORY_SCHEMA_VERSION
            or history.completed_trial_count != len(completed_ids)
            or history.previous_history_sha256 != previous_sha
            or len(completed_ids) != index
            or len(completed_ids) != len(set(completed_ids))
            or not set(completed_ids).issubset(completed_by_id)
        ):
            raise _artifact_error()
        ordered_ids = sorted(
            completed_ids, key=lambda trial_id: completed_by_id[trial_id].trial_number
        )
        if completed_ids != ordered_ids:
            raise _artifact_error()
        if index == 0 and completed_ids:
            raise _artifact_error()
        if index > 0 and (
            not set(previous_ids).issubset(completed_ids)
            or len(set(completed_ids) - set(previous_ids)) != 1
        ):
            raise _artifact_error()
        expected_sha = canonical_bayesian_observation_history_sha256(
            definition_sha256=version.definition_sha256,
            completed_trials=[completed_by_id[trial_id] for trial_id in completed_ids],
        )
        if history.observation_history_sha256 != expected_sha:
            raise _artifact_error()
        previous_ids = completed_ids
        previous_sha = history.observation_history_sha256
    if set(previous_ids) != set(completed_by_id):
        raise _artifact_error()


def _validate_recommendations(
    version: BayesianStudyVersionRecord,
    factors: list[BayesianFactorResponse],
    objective: BayesianObjectiveResponse,
    constraints: list[BayesianLinearConstraintResponse],
    trials: list[BayesianTrialRecord],
    histories: list[BayesianHistoryRevisionRecord],
    recommendations: list[BayesianRecommendationRecord],
) -> None:
    recommendation_trials = {
        item.trial_id: item for item in trials if item.origin == "recommendation"
    }
    trial_by_id = {item.trial_id: item for item in trials}
    history_by_id = {item.history_revision_id: item for item in histories}
    if len(recommendations) != len(recommendation_trials):
        raise _artifact_error()
    pending_count = 0
    for record in recommendations:
        trial = recommendation_trials.get(record.trial_id)
        history = history_by_id.get(record.source_history_revision_id)
        if trial is None or history is None:
            raise _artifact_error()
        try:
            completed_ids = _json_string_list(history.completed_trial_ids_json)
        except (KeyError, TypeError, ValueError) as exc:
            raise _artifact_error() from exc
        source_observation_values: list[float] = []
        for trial_id in completed_ids:
            source_trial = trial_by_id.get(trial_id)
            if source_trial is None or source_trial.objective_value is None:
                raise _artifact_error()
            source_observation_values.append(float(source_trial.objective_value))
        if trial.state == "pending":
            pending_count += 1
        try:
            validate_bayesian_recommendation_record(
                record=record,
                study_id=version.study_id,
                study_version_id=version.study_version_id,
                definition_sha256=version.definition_sha256,
                source_history_revision_id=history.history_revision_id,
                source_history_sha256=history.observation_history_sha256,
                source_observation_values=source_observation_values,
                factors=factors,
                constraints=constraints,
                objective_direction=objective.direction,
                current_trial=_trial_response(trial),
                current_method_version=METHOD_VERSIONS[BAYESIAN_METHOD_ID],
            )
        except ValueError as exc:
            raise _artifact_error() from exc
    if pending_count > 1:
        raise _artifact_error()


def _study_response(bundle: _ValidatedStudy) -> BayesianStudyResponse:
    counts = _trial_counts(bundle.trials)
    return BayesianStudyResponse(
        study_id=UUID(bundle.study.study_id),
        study_version_id=UUID(bundle.version.study_version_id),
        version_number=bundle.version.version_number,
        study_schema_version=cast(Literal[1], bundle.version.schema_version),
        method_id=BAYESIAN_METHOD_ID,
        method_version=bundle.study.method_version,
        name=bundle.study.name,
        status=cast(Literal["active", "completed", "abandoned"], bundle.study.status),
        created_at=bundle.study.created_at,
        updated_at=bundle.study.updated_at,
        app_version=bundle.study.app_version,
        definition_sha256=bundle.version.definition_sha256,
        factors=bundle.factors,
        objective=bundle.objective,
        constraints=bundle.constraints,
        initial_design=bundle.initial_design,
        trial_count=len(bundle.trials),
        pending_trial_count=counts["pending"],
        completed_trial_count=counts["completed"],
        abandoned_trial_count=counts["abandoned"],
        observation_history=_history_response(bundle.current_history),
        trials=[_trial_response(item) for item in bundle.trials],
        surrogate_available=_surrogate_available(bundle),
        recommendation_available=_recommendation_available(bundle),
    )


def _study_summary(bundle: _ValidatedStudy) -> BayesianStudySummaryResponse:
    counts = _trial_counts(bundle.trials)
    return BayesianStudySummaryResponse(
        study_id=UUID(bundle.study.study_id),
        study_version_id=UUID(bundle.version.study_version_id),
        method_id=BAYESIAN_METHOD_ID,
        method_version=bundle.study.method_version,
        name=bundle.study.name,
        status=cast(Literal["active", "completed", "abandoned"], bundle.study.status),
        updated_at=bundle.study.updated_at,
        definition_sha256=bundle.version.definition_sha256,
        pending_trial_count=counts["pending"],
        completed_trial_count=counts["completed"],
        abandoned_trial_count=counts["abandoned"],
        observation_history_sha256=bundle.current_history.observation_history_sha256,
    )


def _trial_response(trial: BayesianTrialRecord) -> BayesianTrialResponse:
    return BayesianTrialResponse(
        trial_id=UUID(trial.trial_id),
        study_version_id=UUID(trial.study_version_id),
        trial_number=trial.trial_number,
        origin=cast(Literal["initial_design", "recommendation"], trial.origin),
        state=cast(Literal["pending", "completed", "abandoned"], trial.state),
        actual_coordinates=_numeric_json_dict(trial.actual_coordinates_json),
        normalized_coordinates=_numeric_json_dict(trial.normalized_coordinates_json),
        coordinates_sha256=trial.coordinates_sha256,
        objective_value=trial.objective_value,
        created_at=trial.created_at,
        closed_at=trial.closed_at,
    )


def _history_response(
    history: BayesianHistoryRevisionRecord,
) -> BayesianHistoryRevisionResponse:
    return BayesianHistoryRevisionResponse(
        history_revision_id=UUID(history.history_revision_id),
        study_version_id=UUID(history.study_version_id),
        revision_number=history.revision_number,
        schema_version=cast(Literal[1], history.schema_version),
        completed_trial_ids=[
            UUID(item) for item in _json_string_list(history.completed_trial_ids_json)
        ],
        completed_trial_count=history.completed_trial_count,
        observation_history_sha256=history.observation_history_sha256,
        previous_history_sha256=history.previous_history_sha256,
        created_at=history.created_at,
    )


def _definition_payload(
    *,
    method_version: str,
    factors: list[BayesianFactorResponse],
    objective: BayesianObjectiveResponse,
    constraints: list[BayesianLinearConstraintResponse],
    initial_design: BayesianInitialDesignResponse,
) -> dict[str, Any]:
    return {
        "study_schema_version": BAYESIAN_STUDY_SCHEMA_VERSION,
        "method_id": BAYESIAN_METHOD_ID,
        "method_version": method_version,
        "factors": [item.model_dump(mode="json") for item in factors],
        "objective": objective.model_dump(mode="json"),
        "constraints": [item.model_dump(mode="json") for item in constraints],
        "initial_design": initial_design.model_dump(mode="json"),
    }


def _constraints_satisfied(
    actual: dict[str, float], constraints: list[BayesianLinearConstraintResponse]
) -> bool:
    for constraint in constraints:
        lhs = sum(term.coefficient * actual[term.factor_id] for term in constraint.terms)
        scale = max(1.0, abs(lhs), abs(constraint.bound))
        tolerance = 1e-12 * scale
        if constraint.relation == "less_than_or_equal":
            if lhs > constraint.bound + tolerance:
                return False
        elif lhs < constraint.bound - tolerance:
            return False
    return True


def _trial_for_transition(bundle: _ValidatedStudy, trial_id: str) -> BayesianTrialRecord:
    matched = next((item for item in bundle.trials if item.trial_id == trial_id), None)
    if matched is None:
        raise ApiError(
            code="bayesian_trial_not_found",
            message="요청한 Bayesian trial을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return matched


def _trial_counts(trials: list[BayesianTrialRecord]) -> dict[str, int]:
    return {
        state: sum(item.state == state for item in trials)
        for state in ("pending", "completed", "abandoned")
    }


def _surrogate_available(bundle: _ValidatedStudy) -> bool:
    completed = sum(item.state == "completed" for item in bundle.trials)
    pending_initial = any(
        item.origin == "initial_design" and item.state == "pending" for item in bundle.trials
    )
    return (
        bundle.study.status == "active"
        and not pending_initial
        and completed >= max(2, len(bundle.factors) + 1)
    )


def _recommendation_available(bundle: _ValidatedStudy) -> bool:
    pending_recommendation = any(
        item.origin == "recommendation" and item.state == "pending" for item in bundle.trials
    )
    return _surrogate_available(bundle) and not pending_recommendation and len(bundle.trials) < 200


def _json_list(payload: str) -> list[dict[str, Any]]:
    parsed = json.loads(payload)
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise TypeError("expected JSON object list")
    return parsed


def _json_dict(payload: str) -> dict[str, Any]:
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise TypeError("expected JSON object")
    return parsed


def _numeric_json_dict(payload: str) -> dict[str, float]:
    parsed = json.loads(payload)
    if not isinstance(parsed, dict) or not all(isinstance(key, str) for key in parsed):
        raise TypeError("expected numeric JSON object")
    result: dict[str, float] = {}
    for key, value in parsed.items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError("expected numeric JSON value")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("expected finite JSON value")
        result[key] = numeric
    return result


def _json_string_list(payload: str) -> list[str]:
    parsed = json.loads(payload)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise TypeError("expected JSON string list")
    return parsed


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _counter_uniform(seed: int, attempt: int, factor_order: int) -> float:
    digest = hashlib.sha256(f"{seed}:{attempt}:{factor_order}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) / 2**64


def _metadata_error() -> ApiError:
    return ApiError(
        code="bayesian_study_metadata_invalid",
        message="저장된 Bayesian study metadata 관계가 올바르지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _artifact_error() -> ApiError:
    return ApiError(
        code="bayesian_study_artifact_mismatch",
        message="저장된 Bayesian study, trial 또는 history checksum 관계가 일치하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _trial_state_error() -> ApiError:
    return ApiError(
        code="bayesian_trial_state_conflict",
        message="pending trial만 완료하거나 abandon할 수 있습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _history_stale_error() -> ApiError:
    return ApiError(
        code="bayesian_observation_history_stale",
        message="관측 history가 변경되었습니다. 최신 revision을 확인한 뒤 다시 시도하세요.",
        status_code=status.HTTP_409_CONFLICT,
    )
