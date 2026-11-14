"""Immutable study-8 definitions and actual-coordinate trial receipts."""

from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

from app.api.v1.schemas.bo_mixture import (
    MixtureStudyCreateRequest,
    MixtureStudyDefinition,
    MixtureStudyResponse,
    MixtureTrialResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services import bayesian_studies as legacy
from app.services.analysis_run_execution import APP_VERSION, utc_now
from app.statistics.bo_mixed_initial_design import mixed_constraints_satisfied
from app.statistics.bo_mixture_design import POLICY as ENCODING
from app.statistics.bo_mixture_design import BoMixtureDesign
from app.storage import bayesian_studies as storage
from app.storage.bo_planning import planning_json, planning_sha

METHOD_VERSION = "0.17.0"


@dataclass(frozen=True)
class MixtureValidatedStudy:
    study: storage.BayesianStudyRecord
    version: storage.BayesianStudyVersionRecord
    definition: MixtureStudyDefinition
    design: BoMixtureDesign
    trials: list[storage.BayesianTrialRecord]
    histories: list[storage.BayesianHistoryRevisionRecord]
    current_history: storage.BayesianHistoryRevisionRecord
    lifecycle_event: storage.BayesianStudyLifecycleEventRecord | None
    recommendation_batches: list[storage.BayesianRecommendationBatchRecord]

    @property
    def objective(self) -> Any:
        return self.definition.objective

    @property
    def recommendations(self) -> list[storage.BayesianRecommendationRecord]:
        return []

    @property
    def constraints(self) -> Any:
        return self.definition.constraints

    @property
    def factors(self) -> list[dict[str, Any]]:
        return mixture_factors(self.definition)


def mixture_factors(body: MixtureStudyDefinition) -> list[dict[str, Any]]:
    result = [
        {
            **c.model_dump(mode="json"),
            "domain_kind": "mixture_component",
            "order": i + 1,
            "scaling_rule": ENCODING,
        }
        for i, c in enumerate(body.mixture.components)
    ]
    offset = len(result)
    result.extend(
        {**f.model_dump(mode="json"), "order": i + offset + 1}
        for i, f in enumerate(body.process_factors)
    )
    return result


def is_mixture_study(settings: Settings, study_id: str) -> bool:
    owner = storage.get_bayesian_study_record(settings.workspace_root, study_id)
    if owner is None:
        return False
    version = storage.get_bayesian_study_version_record(
        settings.workspace_root, study_id=study_id, version_number=owner.current_version
    )
    return version is not None and version.schema_version == 8


def mixture_coordinate_payload(
    *,
    definition_sha256: str,
    trial_number: int,
    origin: str,
    actual: dict[str, Any],
    encoded: dict[str, float],
    replicate_of_trial_id: str | None = None,
) -> dict[str, Any]:
    result = {
        "schema_version": 3,
        "definition_sha256": definition_sha256,
        "trial_number": trial_number,
        "origin": origin,
        "coordinate_encoding": ENCODING,
        "actual_coordinates": actual,
        "encoded_coordinates": encoded,
    }
    if origin == "replicate":
        result["replicate_of_trial_id"] = replicate_of_trial_id
    return result


def new_mixture_trial_record(
    *,
    study_version_id: str,
    definition_sha256: str,
    design: BoMixtureDesign,
    trial_number: int,
    actual: dict[str, Any],
    created_at: str,
    origin: str = "initial_design",
    replicate_of_trial_id: str | None = None,
) -> storage.BayesianTrialRecord:
    values, vector = design.canonical(actual)
    if (
        not mixed_constraints_satisfied(values, design.constraints)
        or not 1 <= trial_number <= 200
        or origin not in {"initial_design", "recommendation", "replicate"}
        or (origin == "replicate") != (replicate_of_trial_id is not None)
    ):
        raise legacy._artifact_error()
    encoded = dict(zip(design.keys, vector, strict=True))
    return storage.BayesianTrialRecord(
        trial_id=str(uuid4()),
        study_version_id=study_version_id,
        trial_number=trial_number,
        origin=origin,
        state="pending",
        actual_coordinates_json=planning_json(values),
        normalized_coordinates_json=planning_json(encoded),
        coordinates_sha256=planning_sha(
            mixture_coordinate_payload(
                definition_sha256=definition_sha256,
                trial_number=trial_number,
                origin=origin,
                actual=values,
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


def create_mixture_study(
    settings: Settings, body: MixtureStudyCreateRequest
) -> MixtureStudyResponse:
    design = body.domain()
    from app.services.bo_planning import _run

    generated = _run(
        "mixture_initial",
        {
            "design_domain": design.payload(),
            "seed": body.initial_design_seed,
            "count": body.initial_design_size,
            "max_attempts": body.initial_design_size * 1000,
        },
        time_budget_ms=60000,
    )
    initial = {
        **generated["generation"],
        "generated_size": len(generated["points"]),
        "points_sha256": planning_sha(generated["points"]),
    }
    now, study_id, version_id = utc_now(), str(uuid4()), str(uuid4())
    definition = {
        "schema_version": 8,
        "method_version": METHOD_VERSION,
        "request": body.model_dump(mode="json"),
        "design_domain": design.payload(),
        "initial_design": initial,
    }
    digest = planning_sha(definition)
    owner = storage.BayesianStudyRecord(
        study_id=study_id,
        method_id=legacy.BAYESIAN_METHOD_ID,
        method_version=METHOD_VERSION,
        name=body.name.strip(),
        status="active",
        current_version=1,
        created_at=now,
        updated_at=now,
        app_version=APP_VERSION,
    )
    version = storage.BayesianStudyVersionRecord(
        study_version_id=version_id,
        study_id=study_id,
        version_number=1,
        schema_version=8,
        factors_json=planning_json(
            {"request": body.model_dump(mode="json"), "design_domain": design.payload()}
        ),
        objective_json=planning_json(body.objective.model_dump(mode="json")),
        constraints_json=planning_json([c.model_dump(mode="json") for c in body.constraints]),
        initial_design_json=planning_json(initial),
        definition_sha256=digest,
        created_at=now,
    )
    trials = [
        new_mixture_trial_record(
            study_version_id=version_id,
            definition_sha256=digest,
            design=design,
            trial_number=i + 1,
            actual=p,
            created_at=now,
        )
        for i, p in enumerate(generated["points"])
    ]
    history = legacy._new_history_record(
        study_version_id=version_id,
        definition_sha256=digest,
        revision_number=1,
        completed_trials=[],
        previous_history_sha256=None,
        created_at=now,
        schema_version=2,
    )
    storage.insert_bayesian_study_bundle(
        settings.workspace_root,
        study=owner,
        version=version,
        trials=trials,
        initial_history=history,
    )
    return get_mixture_study(settings, UUID(study_id))


def load_validated_mixture_definition(
    settings: Settings, study_id: str
) -> tuple[
    storage.BayesianStudyRecord,
    storage.BayesianStudyVersionRecord,
    MixtureStudyDefinition,
    BoMixtureDesign,
    dict[str, Any],
]:
    owner = storage.get_bayesian_study_record(settings.workspace_root, study_id)
    if owner is None:
        raise ApiError(
            code="bayesian_study_not_found",
            message="The requested study does not exist.",
            status_code=404,
        )
    version = storage.get_bayesian_study_version_record(
        settings.workspace_root, study_id=study_id, version_number=owner.current_version
    )
    if (
        version is None
        or version.schema_version != 8
        or version.study_id != study_id
        or version.version_number != 1
        or owner.current_version != 1
        or owner.method_id != legacy.BAYESIAN_METHOD_ID
        or owner.method_version != METHOD_VERSION
        or owner.status not in {"active", "completed", "abandoned"}
        or owner.predecessor_study_id is not None
    ):
        raise legacy._metadata_error()
    try:
        factors = json.loads(version.factors_json)
        if set(factors) != {"request", "design_domain"}:
            raise ValueError
        initial = json.loads(version.initial_design_json)
        imported = initial.get("policy") == "dataset_observations_v1"
        if imported:
            from app.api.v1.schemas.bo_mixture_dataset_import import (
                MixtureDatasetImportedInitialDesign,
            )

            MixtureDatasetImportedInitialDesign.model_validate(initial)
            body = MixtureStudyDefinition.model_validate(factors["request"])
        else:
            body = MixtureStudyCreateRequest.model_validate(factors["request"])
        design = BoMixtureDesign.from_payload(factors["design_domain"])
        if (
            body.domain() != design
            or body.objective.model_dump(mode="json") != json.loads(version.objective_json)
            or [c.model_dump(mode="json") for c in body.constraints]
            != json.loads(version.constraints_json)
        ):
            raise ValueError
        definition = {
            "schema_version": 8,
            "method_version": owner.method_version,
            "request": body.model_dump(mode="json"),
            "design_domain": design.payload(),
            "initial_design": initial,
        }
        if planning_sha(definition) != version.definition_sha256:
            raise ValueError
        if isinstance(body, MixtureStudyCreateRequest) and (
            set(initial)
            != {
                "policy",
                "seed",
                "requested_count",
                "attempt_count",
                "max_attempts",
                "stop_reason",
                "exact_uniform",
                "generated_size",
                "points_sha256",
            }
            or initial["policy"] != "bounded_seeded_mixture_polytope_v1"
            or initial["seed"] != body.initial_design_seed
            or initial["requested_count"] != body.initial_design_size
            or initial["generated_size"] != body.initial_design_size
            or initial["max_attempts"] != body.initial_design_size * 1000
            or type(initial["attempt_count"]) is not int
            or not initial["generated_size"] <= initial["attempt_count"] <= initial["max_attempts"]
            or initial["stop_reason"] != "requested_count_reached"
            or initial["exact_uniform"] is not False
        ):
            raise ValueError
        return owner, version, body, design, initial
    except (ValueError, KeyError, TypeError, AttributeError):
        raise legacy._artifact_error() from None


def load_validated_mixture_study(settings: Settings, study_id: str) -> MixtureValidatedStudy:
    owner, version, body, design, initial = load_validated_mixture_definition(settings, study_id)
    imported = initial.get("policy") == "dataset_observations_v1"
    imported_initial = None
    if imported:
        from app.api.v1.schemas.bo_mixture_dataset_import import MixtureDatasetImportedInitialDesign

        imported_initial = MixtureDatasetImportedInitialDesign.model_validate(initial)
    try:
        trials = storage.list_bayesian_trial_records(
            settings.workspace_root, version.study_version_id, limit=200
        )
        if (
            len(trials)
            != storage.count_bayesian_trial_records(
                settings.workspace_root, version.study_version_id
            )
            or not initial["generated_size"] <= len(trials) <= 200
            or [t.trial_number for t in trials] != list(range(1, len(trials) + 1))
        ):
            raise ValueError
        if not imported and (
            planning_sha(
                [json.loads(t.actual_coordinates_json) for t in trials[: initial["generated_size"]]]
            )
            != initial["points_sha256"]
        ):
            raise ValueError
        histories = legacy._load_complete_history_records(
            settings.workspace_root, version.study_version_id
        )
        history = storage.get_current_bayesian_history_revision_record(
            settings.workspace_root, version.study_version_id
        )
        if history is None:
            raise ValueError
        event = storage.get_bayesian_study_lifecycle_event_record(settings.workspace_root, study_id)
        batches = storage.list_bayesian_recommendation_batch_records(
            settings.workspace_root, version.study_version_id, limit=200
        )
        if storage.count_bayesian_recommendation_batch_records(
            settings.workspace_root, version.study_version_id
        ) != len(batches) or storage.count_bayesian_recommendation_records(
            settings.workspace_root, version.study_version_id
        ):
            raise ValueError
        bundle = MixtureValidatedStudy(
            owner, version, body, design, trials, histories, history, event, batches
        )
        if imported_initial is not None:
            from app.services.bo_dataset_import import validate_imported_trials

            validate_imported_trials(settings, version, imported_initial, trials)
        seen: set[str] = set()
        earlier: dict[str | None, storage.BayesianTrialRecord] = {}
        for index, trial in enumerate(trials):
            projected = mixture_trial_response(bundle, trial)
            actual = projected.actual_coordinates
            fingerprint = planning_sha(actual)
            initial_trial = index < initial["generated_size"]
            if initial_trial:
                if trial.origin != "initial_design":
                    raise ValueError
            elif trial.origin not in {"recommendation", "replicate"}:
                raise ValueError
            if trial.origin == "replicate":
                parent = earlier.get(trial.replicate_of_trial_id)
                if (
                    parent is None
                    or parent.state != "completed"
                    or parent.actual_coordinates_json != trial.actual_coordinates_json
                    or parent.normalized_coordinates_json != trial.normalized_coordinates_json
                ):
                    raise ValueError
            elif (
                fingerprint in seen and not (imported and initial_trial)
            ) or trial.replicate_of_trial_id is not None:
                raise ValueError
            seen.add(fingerprint)
            earlier[trial.trial_id] = trial
        legacy._validate_histories(version, trials, histories, history)
        from app.services.bayesian_replicates import validate_replicate_requests

        validate_replicate_requests(settings.workspace_root, version, trials, histories)
        from app.services.bo_mixture_workflow import validate_mixture_batch_record

        owned: list[str] = []
        for batch in batches:
            owned.extend(
                item["trial"]["trial_id"]
                for item in validate_mixture_batch_record(settings, bundle, batch)["items"]
            )
        if len(set(owned)) != len(owned) or set(owned) != {
            t.trial_id for t in trials if t.origin == "recommendation"
        }:
            raise ValueError
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
    except (ValueError, KeyError, TypeError, AttributeError):
        raise legacy._artifact_error() from None


def mixture_trial_response(
    bundle: MixtureValidatedStudy, trial: storage.BayesianTrialRecord
) -> MixtureTrialResponse:
    try:
        actual = json.loads(trial.actual_coordinates_json)
        values, vector = bundle.design.canonical(actual)
        encoded = dict(zip(bundle.design.keys, vector, strict=True))
        if (
            values != actual
            or encoded != json.loads(trial.normalized_coordinates_json)
            or not mixed_constraints_satisfied(actual, bundle.design.constraints)
            or trial.study_version_id != bundle.version.study_version_id
            or planning_sha(
                mixture_coordinate_payload(
                    definition_sha256=bundle.version.definition_sha256,
                    trial_number=trial.trial_number,
                    origin=trial.origin,
                    actual=actual,
                    encoded=encoded,
                    replicate_of_trial_id=trial.replicate_of_trial_id,
                )
            )
            != trial.coordinates_sha256
        ):
            raise ValueError
        response = (
            None if trial.response_values_json is None else json.loads(trial.response_values_json)
        )
        if (
            trial.objective_value is not None
            or (trial.state == "completed") != (response is not None)
            or (trial.state == "pending") != (trial.closed_at is None)
        ):
            raise ValueError
        if response is not None and (
            set(response) != {r.response_id for r in bundle.objective.responses}
            or any(type(v) not in {float, int} or not math.isfinite(v) for v in response.values())
        ):
            raise ValueError
        return MixtureTrialResponse(
            trial_id=UUID(trial.trial_id),
            study_version_id=UUID(trial.study_version_id),
            trial_number=trial.trial_number,
            origin=cast(Any, trial.origin),
            state=cast(Any, trial.state),
            actual_coordinates=actual,
            encoded_coordinates=encoded,
            coordinates_sha256=trial.coordinates_sha256,
            response_values=response,
            created_at=trial.created_at,
            closed_at=trial.closed_at,
            replicate_of_trial_id=UUID(trial.replicate_of_trial_id)
            if trial.replicate_of_trial_id
            else None,
        )
    except (ValueError, KeyError, TypeError):
        raise legacy._artifact_error() from None


def mixture_study_response(bundle: MixtureValidatedStudy) -> MixtureStudyResponse:
    counts = legacy._trial_counts(bundle.trials)
    minimum = max(2, len(bundle.design.keys))
    unique = {t.actual_coordinates_json for t in bundle.trials if t.state == "completed"}
    ready = counts["completed"] >= minimum and len(unique) >= minimum
    blockers = [] if ready else ["bayesian_optimization_history_incomplete"]
    if counts["pending"]:
        blockers.append("bayesian_optimization_pending_recommendation_exists")
    if bundle.study.status != "active":
        blockers.append("bayesian_study_not_active")
    if len(bundle.trials) >= 200:
        blockers.append("bayesian_optimization_budget_exhausted")
    return MixtureStudyResponse(
        study_id=UUID(bundle.study.study_id),
        study_version_id=UUID(bundle.version.study_version_id),
        method_version=bundle.study.method_version,
        name=bundle.study.name,
        status=cast(Any, bundle.study.status),
        created_at=bundle.study.created_at,
        updated_at=bundle.study.updated_at,
        app_version=bundle.study.app_version,
        definition_sha256=bundle.version.definition_sha256,
        mixture=bundle.definition.mixture,
        process_factors=bundle.definition.process_factors,
        factors=bundle.factors,
        design_domain=bundle.design.payload(),
        objective=bundle.objective,
        constraints=bundle.constraints,
        initial_design=json.loads(bundle.version.initial_design_json),
        trial_count=len(bundle.trials),
        pending_trial_count=counts["pending"],
        completed_trial_count=counts["completed"],
        abandoned_trial_count=counts["abandoned"],
        observation_history=legacy._history_response(bundle.current_history),
        trials=[mixture_trial_response(bundle, t) for t in bundle.trials],
        surrogate_available=ready,
        recommendation_available=not blockers,
        recommendation_minimum_completed_observations=minimum,
        recommendation_blockers=blockers,
        lifecycle_event=legacy._lifecycle_event_response(bundle.lifecycle_event).model_dump(
            mode="json"
        )
        if bundle.lifecycle_event
        else None,
    )


def get_mixture_study(settings: Settings, study_id: UUID) -> MixtureStudyResponse:
    return mixture_study_response(load_validated_mixture_study(settings, str(study_id)))


def mixture_initial_design_csv(settings: Settings, study_id: UUID) -> tuple[bytes, str]:
    bundle = load_validated_mixture_study(settings, str(study_id))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    factor_labels = [
        f"{f['name']} [{f['unit']}]" if f.get("unit") else str(f["name"]) for f in bundle.factors
    ]
    response_labels = [
        f"{r.name} [{r.unit}]" if r.unit else r.name for r in bundle.objective.responses
    ]
    writer.writerow(
        [
            "Trial",
            "Trial ID",
            "Origin",
            "State",
            *[legacy._csv_cell(v) for v in factor_labels],
            *[legacy._csv_cell(v) for v in response_labels],
            "Objective status",
        ]
    )
    for trial in bundle.trials:
        if trial.origin != "initial_design":
            continue
        row = mixture_trial_response(bundle, trial)
        actuals = [row.actual_coordinates[key] for key in bundle.design.keys]
        writer.writerow(
            [
                trial.trial_number,
                trial.trial_id,
                trial.origin,
                trial.state,
                *[legacy._csv_cell(v) if isinstance(v, str) else v for v in actuals],
                *[
                    (row.response_values or {}).get(r.response_id, "")
                    for r in bundle.objective.responses
                ],
                "recorded" if trial.state == "completed" else trial.state,
            ]
        )
    return output.getvalue().encode("utf-8-sig"), f"bayesian-initial-design-{study_id}.csv"
