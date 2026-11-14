"""Source-owned schema-7 studies in the existing immutable Bayesian store."""

from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError

if TYPE_CHECKING:
    from app.api.v1.schemas.bo_mixture import MixtureStudyResponse
    from app.services.bo_mixture_studies import MixtureValidatedStudy

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.bayesian import (
    BayesianFactorResponse,
    BayesianLinearConstraintResponse,
    BayesianStudyResponse,
    BayesianStudySummaryResponse,
)
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_dataset_source import DatasetImportedInitialDesign
from app.api.v1.schemas.bo_mixed_studies import (
    MixedCategoricalFactorRequest,
    MixedCategoricalFactorResponse,
    MixedFactorResponse,
    MixedInitialDesignResponse,
    MixedStudyCreateRequest,
    MixedStudyResponse,
    MixedTrialResponse,
    mixed_constraint_definitions,
    mixed_factor_domains,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services import bayesian_studies as legacy
from app.services.analysis_run_execution import APP_VERSION, utc_now
from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoFactorDomain,
    BoFactorValue,
    encode_bo_point,
)
from app.statistics.bo_mixed_initial_design import (
    generate_mixed_initial_design,
    mixed_constraints_satisfied,
    validate_mixed_constraints,
)
from app.statistics.doe_factor_domain import DoeFactorDomain
from app.storage.bayesian_studies import (
    BayesianHistoryRevisionRecord,
    BayesianRecommendationBatchRecord,
    BayesianRecommendationRecord,
    BayesianStudyLifecycleEventRecord,
    BayesianStudyRecord,
    BayesianStudyVersionRecord,
    BayesianTrialRecord,
    count_bayesian_recommendation_batch_records,
    count_bayesian_recommendation_records,
    count_bayesian_trial_records,
    get_bayesian_study_lifecycle_event_record,
    get_bayesian_study_record,
    get_bayesian_study_version_record,
    get_current_bayesian_history_revision_record,
    insert_bayesian_study_bundle,
    list_bayesian_recommendation_batch_records,
    list_bayesian_trial_records,
)

_FACTORS = TypeAdapter(list[MixedFactorResponse])
_OBJECTIVE: TypeAdapter[AnyDesirabilityObjective] = TypeAdapter(AnyDesirabilityObjective)


@dataclass(frozen=True)
class MixedValidatedStudy:
    study: BayesianStudyRecord
    version: BayesianStudyVersionRecord
    factors: list[MixedFactorResponse]
    factor_domains: tuple[BoFactorDomain, ...]
    objective: AnyDesirabilityObjective
    constraints: list[BayesianLinearConstraintResponse]
    initial_design: MixedInitialDesignResponse | DatasetImportedInitialDesign
    trials: list[BayesianTrialRecord]
    histories: list[BayesianHistoryRevisionRecord]
    current_history: BayesianHistoryRevisionRecord
    recommendation_batches: list[BayesianRecommendationBatchRecord]
    lifecycle_event: BayesianStudyLifecycleEventRecord | None

    @property
    def recommendations(self) -> list[BayesianRecommendationRecord]:
        # Mixed studies use versioned candidate batches, never the scalar route.
        return []


@dataclass(frozen=True)
class MixedTrialProjection:
    trial_id: str
    trial_number: int
    actual_coordinates: dict[str, BoFactorValue]
    encoded_coordinates: dict[str, float]
    response_values: dict[str, float] | None
    coordinates_sha256: str


def is_mixed_study(settings: Settings, study_id: str) -> bool:
    owner = get_bayesian_study_record(settings.workspace_root, study_id)
    if owner is None:
        return False
    version = get_bayesian_study_version_record(
        settings.workspace_root, study_id=study_id, version_number=owner.current_version
    )
    return version is not None and version.schema_version == 7


def mixed_definition_payload(
    *,
    method_version: str,
    factors: list[MixedFactorResponse],
    objective: AnyDesirabilityObjective,
    constraints: list[BayesianLinearConstraintResponse],
    initial_design: MixedInitialDesignResponse | DatasetImportedInitialDesign,
) -> dict[str, Any]:
    return {
        "study_schema_version": 7,
        "method_id": legacy.BAYESIAN_METHOD_ID,
        "method_version": method_version,
        "factors": [item.model_dump(mode="json") for item in factors],
        "objective": objective.model_dump(mode="json"),
        "constraints": [item.model_dump(mode="json") for item in constraints],
        "initial_design": initial_design.model_dump(mode="json"),
    }


def mixed_coordinate_payload(
    *,
    definition_sha256: str,
    trial_number: int,
    origin: str,
    actual: dict[str, BoFactorValue],
    encoded: dict[str, float],
    replicate_of_trial_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "definition_sha256": definition_sha256,
        "trial_number": trial_number,
        "origin": origin,
        "coordinate_encoding": "numeric_normalized_category_index_v1",
        "actual_coordinates": actual,
        "encoded_coordinates": encoded,
    }
    if origin == "replicate":
        payload["replicate_of_trial_id"] = replicate_of_trial_id
    return payload


def canonical_mixed_point(
    domains: tuple[BoFactorDomain, ...], actual: dict[str, BoFactorValue]
) -> tuple[dict[str, BoFactorValue], dict[str, float]]:
    values = encode_bo_point(domains, actual)
    encoded = dict(zip((item.factor_id for item in domains), values, strict=True))
    canonical: dict[str, BoFactorValue] = {}
    for domain in domains:
        value = actual[domain.factor_id]
        if isinstance(domain, BoCategoricalFactorDomain):
            canonical[domain.factor_id] = value
        elif domain.domain.domain_kind == "discrete_numeric":
            canonical[domain.factor_id] = domain.decode(encoded[domain.factor_id])
        else:
            canonical[domain.factor_id] = float(value)
    return canonical, encoded


def new_mixed_trial_record(
    *,
    study_version_id: str,
    definition_sha256: str,
    domains: tuple[BoFactorDomain, ...],
    trial_number: int,
    actual: dict[str, BoFactorValue],
    created_at: str,
    origin: Literal["initial_design", "recommendation", "replicate"] = "initial_design",
    replicate_of_trial_id: str | None = None,
) -> BayesianTrialRecord:
    if (
        type(trial_number) is not int
        or not 1 <= trial_number <= 200
        or (origin == "replicate") != (replicate_of_trial_id is not None)
    ):
        raise legacy._artifact_error()
    actual, encoded = canonical_mixed_point(domains, actual)
    return BayesianTrialRecord(
        trial_id=str(uuid4()),
        study_version_id=study_version_id,
        trial_number=trial_number,
        origin=origin,
        state="pending",
        actual_coordinates_json=legacy._json_dumps(actual),
        normalized_coordinates_json=legacy._json_dumps(encoded),
        coordinates_sha256=legacy._sha256(
            mixed_coordinate_payload(
                definition_sha256=definition_sha256,
                trial_number=trial_number,
                origin=origin,
                actual=actual,
                encoded=encoded,
                replicate_of_trial_id=replicate_of_trial_id,
            )
        ),
        objective_value=None,
        created_at=created_at,
        closed_at=None,
        replicate_of_trial_id=replicate_of_trial_id,
        response_values_json=None,
    )


def project_mixed_trial(
    bundle: MixedValidatedStudy, trial: BayesianTrialRecord
) -> MixedTrialProjection:
    """Validate full identities before exposing typed actual/encoded source coordinates."""
    try:
        actual = json.loads(trial.actual_coordinates_json)
        encoded = json.loads(trial.normalized_coordinates_json)
        expected_values = encode_bo_point(bundle.factor_domains, actual)
        expected = dict(
            zip((item.factor_id for item in bundle.factor_domains), expected_values, strict=True)
        )
        if (
            not isinstance(encoded, dict)
            or set(encoded) != set(expected)
            or any(
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                for value in encoded.values()
            )
            or encoded != expected
            or trial.study_version_id != bundle.version.study_version_id
        ):
            raise ValueError("coordinates")
        if not mixed_constraints_satisfied(
            actual, mixed_constraint_definitions(bundle.constraints)
        ):
            raise ValueError("constraints")
        payload = mixed_coordinate_payload(
            definition_sha256=bundle.version.definition_sha256,
            trial_number=trial.trial_number,
            origin=trial.origin,
            actual=actual,
            encoded=encoded,
            replicate_of_trial_id=trial.replicate_of_trial_id,
        )
        if legacy._sha256(payload) != trial.coordinates_sha256:
            raise ValueError("hash")
        observation = legacy._trial_observation(trial)
        if trial.objective_value is not None or (
            observation is not None and not isinstance(observation, dict)
        ):
            raise ValueError("observation mode")
        if isinstance(observation, dict) and set(observation) != {
            item.response_id for item in bundle.objective.responses
        }:
            raise ValueError("response identity")
    except (ValueError, TypeError, KeyError) as exc:
        raise legacy._artifact_error() from exc
    return MixedTrialProjection(
        trial.trial_id, trial.trial_number, actual, encoded, observation, trial.coordinates_sha256
    )


def create_mixed_study(settings: Settings, body: MixedStudyCreateRequest) -> MixedStudyResponse:
    domains = mixed_factor_domains(body.factors)
    constraints = [
        BayesianLinearConstraintResponse.model_validate(item.model_dump())
        for item in body.constraints
    ]
    try:
        generated = generate_mixed_initial_design(
            domains,
            mixed_constraint_definitions(constraints),
            seed=body.initial_design_seed,
            size=body.initial_design_size,
        )
    except ValueError as exc:
        code = (
            str(exc)
            if str(exc).startswith("bayesian_")
            else "bayesian_mixed_initial_design_invalid"
        )
        raise ApiError(
            code=code,
            message="The mixed initial design could not be generated within its declared limits.",
            status_code=409,
        ) from exc
    predecessor = None
    if body.predecessor_study_id is not None:
        predecessor = str(body.predecessor_study_id)
        old = (
            load_validated_mixed_study(settings, predecessor)
            if is_mixed_study(settings, predecessor)
            else legacy._load_validated_study(settings, predecessor)
        )
        if old.study.status == "active" or old.lifecycle_event is None:
            raise ApiError(
                code="bayesian_study_predecessor_invalid",
                message="A predecessor study must be closed.",
                status_code=409,
            )
    factors: list[MixedFactorResponse] = []
    for index, item in enumerate(body.factors):
        if isinstance(item, MixedCategoricalFactorRequest):
            factors.append(MixedCategoricalFactorResponse(**item.model_dump(), order=index + 1))
        else:
            domain = DoeFactorDomain(
                item.low, item.high, item.domain_kind, item.step, item.display_decimals
            )
            factors.append(
                BayesianFactorResponse(
                    **item.model_dump(),
                    order=index + 1,
                    scaling_rule="linear_0_1",
                    level_count=domain.level_count,
                )
            )
    initial = MixedInitialDesignResponse.model_validate(generated.metadata)
    method_version, now = METHOD_VERSIONS[legacy.BAYESIAN_METHOD_ID], utc_now()
    definition_hash = legacy._sha256(
        mixed_definition_payload(
            method_version=method_version,
            factors=factors,
            objective=body.objective,
            constraints=constraints,
            initial_design=initial,
        )
    )
    study_id, version_id = str(uuid4()), str(uuid4())
    owner = BayesianStudyRecord(
        study_id=study_id,
        method_id=legacy.BAYESIAN_METHOD_ID,
        method_version=method_version,
        name=body.name.strip(),
        status="active",
        current_version=1,
        created_at=now,
        updated_at=now,
        app_version=APP_VERSION,
        predecessor_study_id=predecessor,
    )
    version = BayesianStudyVersionRecord(
        study_version_id=version_id,
        study_id=study_id,
        version_number=1,
        schema_version=7,
        factors_json=legacy._json_dumps([item.model_dump(mode="json") for item in factors]),
        objective_json=legacy._json_dumps(body.objective.model_dump(mode="json")),
        constraints_json=legacy._json_dumps([item.model_dump(mode="json") for item in constraints]),
        initial_design_json=legacy._json_dumps(initial.model_dump(mode="json")),
        definition_sha256=definition_hash,
        created_at=now,
    )
    trials = [
        new_mixed_trial_record(
            study_version_id=version_id,
            definition_sha256=definition_hash,
            domains=domains,
            trial_number=index + 1,
            actual=point,
            created_at=now,
        )
        for index, point in enumerate(generated.actual_points)
    ]
    history = legacy._new_history_record(
        study_version_id=version_id,
        definition_sha256=definition_hash,
        revision_number=1,
        completed_trials=[],
        previous_history_sha256=None,
        created_at=now,
        schema_version=2,
    )
    insert_bayesian_study_bundle(
        settings.workspace_root,
        study=owner,
        version=version,
        trials=trials,
        initial_history=history,
    )
    return get_mixed_study(settings, UUID(study_id))


def load_validated_mixed_study(settings: Settings, study_id: str) -> MixedValidatedStudy:
    owner = get_bayesian_study_record(settings.workspace_root, study_id)
    if owner is None:
        raise ApiError(
            code="bayesian_study_not_found",
            message="The requested study does not exist.",
            status_code=404,
        )
    version = get_bayesian_study_version_record(
        settings.workspace_root, study_id=study_id, version_number=owner.current_version
    )
    if (
        version is None
        or owner.current_version != 1
        or version.schema_version != 7
        or version.study_id != owner.study_id
        or version.version_number != owner.current_version
        or owner.method_id != legacy.BAYESIAN_METHOD_ID
        or owner.method_version not in legacy.SUPPORTED_BAYESIAN_STUDY_METHOD_VERSIONS
        or owner.status not in {"active", "completed", "abandoned"}
        or not owner.name.strip()
    ):
        raise legacy._metadata_error()
    if owner.predecessor_study_id:
        predecessor = get_bayesian_study_record(settings.workspace_root, owner.predecessor_study_id)
        if (
            predecessor is None
            or predecessor.study_id == study_id
            or predecessor.status not in {"completed", "abandoned"}
        ):
            raise legacy._metadata_error()
    try:
        factors = _FACTORS.validate_python(json.loads(version.factors_json))
        domains = mixed_factor_domains(factors)
        objective = _OBJECTIVE.validate_python(json.loads(version.objective_json))
        constraints = [
            BayesianLinearConstraintResponse.model_validate(item)
            for item in json.loads(version.constraints_json)
        ]
        validate_mixed_constraints(domains, mixed_constraint_definitions(constraints))
        initial_payload = json.loads(version.initial_design_json)
        initial = (
            DatasetImportedInitialDesign.model_validate(initial_payload)
            if initial_payload.get("policy") == "dataset_observations_v1"
            else MixedInitialDesignResponse.model_validate(initial_payload)
        )
        if [item.order for item in factors] != list(range(1, len(factors) + 1)) or any(
            not item.name.strip() for item in factors
        ):
            raise ValueError("factor order")
        if (
            legacy._sha256(
                mixed_definition_payload(
                    method_version=owner.method_version,
                    factors=factors,
                    objective=objective,
                    constraints=constraints,
                    initial_design=initial,
                )
            )
            != version.definition_sha256
        ):
            raise ValueError("definition hash")
        generated = None
        if isinstance(initial, MixedInitialDesignResponse):
            generated = generate_mixed_initial_design(
                domains,
                mixed_constraint_definitions(constraints),
                seed=initial.seed,
                size=initial.requested_size,
            )
            if generated.metadata != initial.model_dump(mode="json"):
                raise ValueError("initial design metadata")
    except (ValueError, TypeError, KeyError, ValidationError) as exc:
        raise legacy._artifact_error() from exc
    trials = list_bayesian_trial_records(
        settings.workspace_root, version.study_version_id, limit=200
    )
    if (
        count_bayesian_trial_records(settings.workspace_root, version.study_version_id)
        != len(trials)
        or not initial.generated_size <= len(trials) <= 200
        or [item.trial_number for item in trials] != list(range(1, len(trials) + 1))
    ):
        raise legacy._artifact_error()
    histories = legacy._load_complete_history_records(
        settings.workspace_root, version.study_version_id
    )
    history = get_current_bayesian_history_revision_record(
        settings.workspace_root, version.study_version_id
    )
    if history is None:
        raise legacy._artifact_error()
    event = get_bayesian_study_lifecycle_event_record(settings.workspace_root, study_id)
    batches = list_bayesian_recommendation_batch_records(
        settings.workspace_root, version.study_version_id, limit=200
    )
    if count_bayesian_recommendation_records(
        settings.workspace_root, version.study_version_id
    ) or count_bayesian_recommendation_batch_records(
        settings.workspace_root, version.study_version_id
    ) != len(batches):
        raise legacy._artifact_error()
    bundle = MixedValidatedStudy(
        owner,
        version,
        factors,
        domains,
        objective,
        constraints,
        initial,
        trials,
        histories,
        history,
        batches,
        event,
    )
    if isinstance(initial, DatasetImportedInitialDesign):
        from app.services.bo_dataset_import import validate_imported_trials

        validate_imported_trials(settings, version, initial, trials)
        expected_actual = tuple(
            json.loads(item.actual_coordinates_json) for item in trials[: initial.generated_size]
        )
        expected_encoded = tuple(
            json.loads(item.normalized_coordinates_json)
            for item in trials[: initial.generated_size]
        )
    else:
        assert generated is not None
        expected_actual, expected_encoded = generated.actual_points, generated.encoded_points
    _validate_mixed_trials(bundle, expected_actual, expected_encoded)
    legacy._validate_histories(version, trials, histories, history)
    from app.services.bayesian_replicates import validate_replicate_requests

    validate_replicate_requests(settings.workspace_root, version, trials, histories)
    from app.services.bo_mixed_batches import validate_mixed_batch_record

    by_history = {item.history_revision_id: item for item in histories}
    owned_trials: list[str] = []
    for batch in batches:
        saved = validate_mixed_batch_record(
            settings,
            version=version,
            factors=factors,
            objective=objective,
            constraints=constraints,
            trials=trials,
            history=by_history.get(batch.source_history_revision_id),
            record=batch,
        )
        owned_trials.extend(str(item.trial.trial_id) for item in saved.items)
    if len(owned_trials) != len(set(owned_trials)) or set(owned_trials) != {
        trial.trial_id for trial in trials if trial.origin == "recommendation"
    }:
        raise legacy._artifact_error()
    legacy._validate_lifecycle_event(
        study=owner,
        version=version,
        trials=trials,
        current_history=history,
        recommendations=[],
        recommendation_batches=batches,
        event=event,
    )
    return bundle


def _validate_mixed_trials(
    bundle: MixedValidatedStudy,
    expected_actual: tuple[dict[str, BoFactorValue], ...],
    expected_encoded: tuple[dict[str, float], ...],
) -> None:
    seen: set[str] = set()
    earlier: dict[str, BayesianTrialRecord] = {}
    for index, trial in enumerate(bundle.trials):
        projection = project_mixed_trial(bundle, trial)
        initial = index < len(expected_actual)
        if (
            trial.state not in {"pending", "completed", "abandoned"}
            or (initial and trial.origin != "initial_design")
            or (not initial and trial.origin not in {"recommendation", "replicate"})
            or (
                initial
                and (
                    projection.actual_coordinates != expected_actual[index]
                    or projection.encoded_coordinates != expected_encoded[index]
                )
            )
        ):
            raise legacy._artifact_error()
        fingerprint = legacy._sha256(
            {
                "actual_coordinates": projection.actual_coordinates,
                "encoded_coordinates": projection.encoded_coordinates,
            }
        )
        if trial.origin == "replicate":
            parent = earlier.get(trial.replicate_of_trial_id or "")
            if (
                parent is None
                or parent.state != "completed"
                or parent.actual_coordinates_json != trial.actual_coordinates_json
                or parent.normalized_coordinates_json != trial.normalized_coordinates_json
            ):
                raise legacy._artifact_error()
        elif trial.replicate_of_trial_id is not None or (
            fingerprint in seen
            and not (initial and isinstance(bundle.initial_design, DatasetImportedInitialDesign))
        ):
            raise legacy._artifact_error()
        seen.add(fingerprint)
        earlier[trial.trial_id] = trial
        if trial.state == "completed":
            if projection.response_values is None or trial.closed_at is None:
                raise legacy._artifact_error()
        elif projection.response_values is not None or (trial.state == "pending") != (
            trial.closed_at is None
        ):
            raise legacy._artifact_error()


def mixed_trial_response(
    bundle: MixedValidatedStudy, trial: BayesianTrialRecord
) -> MixedTrialResponse:
    projection = project_mixed_trial(bundle, trial)
    values = projection.response_values
    return MixedTrialResponse(
        trial_id=UUID(trial.trial_id),
        study_version_id=UUID(trial.study_version_id),
        trial_number=trial.trial_number,
        origin=cast(Literal["initial_design", "recommendation", "replicate"], trial.origin),
        state=cast(Literal["pending", "completed", "abandoned"], trial.state),
        actual_coordinates=projection.actual_coordinates,
        encoded_coordinates=projection.encoded_coordinates,
        coordinates_sha256=trial.coordinates_sha256,
        response_values=values,
        created_at=trial.created_at,
        closed_at=trial.closed_at,
        replicate_of_trial_id=UUID(trial.replicate_of_trial_id)
        if trial.replicate_of_trial_id
        else None,
    )


def mixed_study_response(bundle: MixedValidatedStudy) -> MixedStudyResponse:
    owner, version = bundle.study, bundle.version
    counts = legacy._trial_counts(bundle.trials)
    minimum = max(2, len(bundle.factor_domains) + 1)
    conditions = {
        trial.actual_coordinates_json for trial in bundle.trials if trial.state == "completed"
    }
    ready = counts["completed"] >= minimum and len(conditions) >= minimum
    blockers: list[str] = []
    if not ready:
        blockers.append("bayesian_optimization_history_incomplete")
    if counts["pending"]:
        blockers.append("bayesian_optimization_pending_recommendation_exists")
    if owner.status != "active":
        blockers.append("bayesian_study_not_active")
    if len(bundle.trials) >= 200:
        blockers.append("bayesian_optimization_budget_exhausted")
    return MixedStudyResponse(
        study_id=UUID(owner.study_id),
        study_version_id=UUID(version.study_version_id),
        version_number=1,
        study_schema_version=7,
        method_id="doe.bayesian_optimization",
        method_version=owner.method_version,
        name=owner.name,
        status=cast(Literal["active", "completed", "abandoned"], owner.status),
        predecessor_study_id=UUID(owner.predecessor_study_id)
        if owner.predecessor_study_id
        else None,
        created_at=owner.created_at,
        updated_at=owner.updated_at,
        app_version=owner.app_version,
        definition_sha256=version.definition_sha256,
        factors=bundle.factors,
        objective=bundle.objective,
        constraints=bundle.constraints,
        initial_design=bundle.initial_design,
        trial_count=len(bundle.trials),
        pending_trial_count=counts["pending"],
        completed_trial_count=counts["completed"],
        abandoned_trial_count=counts["abandoned"],
        observation_history=legacy._history_response(bundle.current_history),
        trials=[mixed_trial_response(bundle, trial) for trial in bundle.trials],
        surrogate_available=ready,
        recommendation_available=not blockers,
        recommendation_minimum_completed_observations=minimum,
        recommendation_blockers=blockers,
        lifecycle_event=legacy._lifecycle_event_response(bundle.lifecycle_event)
        if bundle.lifecycle_event
        else None,
    )


def get_mixed_study(settings: Settings, study_id: UUID) -> MixedStudyResponse:
    return mixed_study_response(load_validated_mixed_study(settings, str(study_id)))


def get_any_bayesian_study(
    settings: Settings, study_id: UUID
) -> BayesianStudyResponse | MixedStudyResponse | MixtureStudyResponse:
    from app.services.bo_mixture_studies import (
        is_mixture_study,
        load_validated_mixture_study,
        mixture_study_response,
    )

    if is_mixture_study(settings, str(study_id)):
        return mixture_study_response(load_validated_mixture_study(settings, str(study_id)))
    if is_mixed_study(settings, str(study_id)):
        return get_mixed_study(settings, study_id)
    return legacy.get_bayesian_study(settings, study_id)


def mixed_study_summary(
    bundle: MixedValidatedStudy | MixtureValidatedStudy,
) -> BayesianStudySummaryResponse:
    counts = legacy._trial_counts(bundle.trials)
    return BayesianStudySummaryResponse(
        study_id=UUID(bundle.study.study_id),
        study_version_id=UUID(bundle.version.study_version_id),
        method_id="doe.bayesian_optimization",
        method_version=bundle.study.method_version,
        name=bundle.study.name,
        status=cast(Literal["active", "completed", "abandoned"], bundle.study.status),
        predecessor_study_id=UUID(bundle.study.predecessor_study_id)
        if bundle.study.predecessor_study_id
        else None,
        updated_at=bundle.study.updated_at,
        definition_sha256=bundle.version.definition_sha256,
        pending_trial_count=counts["pending"],
        completed_trial_count=counts["completed"],
        abandoned_trial_count=counts["abandoned"],
        observation_history_sha256=bundle.current_history.observation_history_sha256,
    )


def mixed_initial_design_csv(settings: Settings, study_id: UUID) -> tuple[bytes, str]:
    bundle = load_validated_mixed_study(settings, str(study_id))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(
        [
            "Trial",
            "Trial ID",
            "Origin",
            "State",
            *[
                legacy._csv_cell(f"{item.name} [{item.unit}]" if item.unit else item.name)
                for item in bundle.factors
            ],
            *[
                legacy._csv_cell(f"{item.name} [{item.unit}]" if item.unit else item.name)
                for item in bundle.objective.responses
            ],
            "Objective status",
        ]
    )
    for trial in bundle.trials:
        if trial.origin != "initial_design":
            continue
        row = project_mixed_trial(bundle, trial)
        values = [row.actual_coordinates[item.factor_id] for item in bundle.factors]
        writer.writerow(
            [
                trial.trial_number,
                trial.trial_id,
                trial.origin,
                trial.state,
                *[legacy._csv_cell(value) if isinstance(value, str) else value for value in values],
                *[
                    (row.response_values or {}).get(item.response_id, "")
                    for item in bundle.objective.responses
                ],
                "recorded" if trial.state == "completed" else trial.state,
            ]
        )
    return output.getvalue().encode("utf-8-sig"), f"bayesian-initial-design-{study_id}.csv"
