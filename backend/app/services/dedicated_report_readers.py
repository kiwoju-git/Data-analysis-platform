"""Stored-only LHS/BO report snapshots. No design generation or model execution."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import asdict
from typing import Any

from app.api.v1.schemas.bayesian import (
    BayesianFactorResponse,
    BayesianInitialDesignResponse,
    BayesianLinearConstraintResponse,
    BayesianObjectiveResponse,
    BayesianRecommendationBatchCreateRequest,
    BayesianRecommendationBatchResponse,
)
from app.api.v1.schemas.doe import (
    DoeFactorResponse,
    LatinHypercubeDesignOptionsResponse,
    LatinHypercubeDesignQualityResponse,
)
from app.api.v1.schemas.reports import BayesianHistoryReportSource, LhsDesignReportSource
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.bayesian_recommendation_consistency import validate_bayesian_recommendation_record
from app.services.bayesian_studies import (
    SUPPORTED_BAYESIAN_STUDY_METHOD_VERSIONS,
    _definition_payload,
    _trial_response,
    canonical_bayesian_observation_history_sha256,
)
from app.services.doe_response_revisions import _validated_revision_values
from app.statistics.latin_hypercube import (
    LatinHypercubeFactor,
    LatinHypercubeOptions,
    LatinHypercubeQuality,
    LatinHypercubeRun,
    canonical_latin_hypercube_payload,
)
from app.storage.bayesian_studies import (
    get_bayesian_history_revision_record,
    get_bayesian_recommendation_batch_record,
    get_bayesian_recommendation_record,
    get_bayesian_study_record,
    get_bayesian_study_version_record,
    get_bayesian_trial_record,
    list_bayesian_recommendation_batch_item_records,
)
from app.storage.metadata import (
    get_experiment_design_record,
    get_experiment_design_version_record,
    get_experiment_response_revision_record,
    list_experiment_run_records,
    metadata_db_path,
)


def invalid(code: str = "report_source_invalid") -> ApiError:
    return ApiError(
        code=code,
        message="The stored report source could not be verified.",
        status_code=404 if code == "report_source_not_found" else 409,
    )


def canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def parsed(value: str) -> Any:
    if len(value.encode("utf-8")) > 16 * 1024 * 1024:
        raise invalid("report_source_size_exceeded")

    def reject(_: str) -> None:
        raise invalid()

    return json.loads(value, parse_constant=reject)


def finite(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise invalid()
    return float(value)


def exact_design_version(settings: Settings, design_version_id: str) -> Any:
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        row = connection.execute(
            "SELECT design_id,version_number FROM experiment_design_versions "
            "WHERE design_version_id=?",
            (design_version_id,),
        ).fetchone()
    if row is None:
        return None
    return get_experiment_design_version_record(settings.workspace_root, row[0], row[1])


def read_lhs(settings: Settings, source: LhsDesignReportSource) -> tuple[dict[str, Any], str, str]:
    root = settings.workspace_root
    design = get_experiment_design_record(root, str(source.design_id))
    version = exact_design_version(settings, str(source.design_version_id))
    if design is None or version is None:
        raise invalid("report_source_not_found")
    if (
        design.method_id != "doe.latin_hypercube"
        or version.design_id != design.design_id
        or design.method_version not in {"0.1.0", "0.2.0", "0.3.0"}
        or version.design_sha256 != source.expected_source_sha256
    ):
        raise invalid("report_source_changed")
    factors = [DoeFactorResponse.model_validate(item) for item in parsed(version.factors_json)]
    options_raw = parsed(version.options_json)
    quality_raw = options_raw["quality"]
    quality = LatinHypercubeDesignQualityResponse.model_validate(quality_raw)
    options = LatinHypercubeDesignOptionsResponse.model_validate(
        {key: value for key, value in options_raw.items() if key != "quality"}
    )
    runs = list_experiment_run_records(root, version.design_version_id)
    if (
        len(runs) != version.run_count
        or options.run_count != version.run_count
        or sorted(item.standard_order for item in runs) != list(range(1, version.run_count + 1))
        or sorted(item.run_order for item in runs) != list(range(1, version.run_count + 1))
    ):
        raise invalid()
    names = {item.name for item in factors}
    saved_runs = []
    for run in sorted(runs, key=lambda item: item.standard_order):
        actual, normalized = parsed(run.factor_levels_json), parsed(run.coded_levels_json)
        if set(actual) != names or set(normalized) != names:
            raise invalid()
        for factor in factors:
            value, coordinate = finite(actual[factor.name]), finite(normalized[factor.name])
            if not factor.low <= value <= factor.high or not 0 <= coordinate <= 1:
                raise invalid()
            expected = (value - factor.low) / (factor.high - factor.low)
            if not math.isclose(expected, coordinate, rel_tol=1e-10, abs_tol=1e-12):
                raise invalid()
        saved_runs.append(LatinHypercubeRun(run.standard_order, run.run_order, actual, normalized))
    # Reconstruct only the canonical stored payload. Quality is never recalculated.
    payload = canonical_latin_hypercube_payload(
        factors=[
            LatinHypercubeFactor(
                item.name,
                item.low,
                item.high,
                item.unit,
                item.domain_kind,
                item.step,
                item.display_decimals,
            )
            for item in factors
        ],
        options=LatinHypercubeOptions(
            options.run_count,
            options.seed,
            options.randomize_run_order,
            options.run_order_seed,
            options.optimization,
        ),
        quality=LatinHypercubeQuality(**quality.model_dump()),
        runs=tuple(saved_runs),
    )
    payload["package_versions"] = {
        "numpy": options_raw["numpy_version"],
        "scipy": options_raw["scipy_version"],
    }
    if digest(payload) != version.design_sha256:
        raise invalid("report_source_changed")
    responses, warnings = [], []
    for ref in source.response_revisions:
        revision = get_experiment_response_revision_record(root, str(ref.response_revision_id))
        if (
            revision is None
            or revision.design_version_id != version.design_version_id
            or revision.response_sha256 != ref.response_revision_sha256
        ):
            raise invalid("report_source_changed")
        values = _validated_revision_values(
            settings, revision, expected_run_count=version.run_count
        )
        responses.append(
            {"revision": asdict(revision), "values": [asdict(item) for item in values]}
        )
        if revision.state == "abandoned":
            warnings.append("historical_abandoned_response_revision")
    return (
        {
            "design": payload,
            "responses": responses,
            "source_warnings": warnings,
            "owner": {
                "method_id": design.method_id,
                "method_version": design.method_version,
                "app_version": design.app_version,
                "created_at": design.created_at,
            },
        },
        design.name,
        version.created_at,
    )


def read_bayesian(
    settings: Settings, source: BayesianHistoryReportSource
) -> tuple[dict[str, Any], str, str]:
    root = settings.workspace_root
    study = get_bayesian_study_record(root, str(source.study_id))
    with sqlite3.connect(metadata_db_path(root)) as connection:
        version_row = connection.execute(
            "SELECT study_id,version_number FROM bayesian_study_versions WHERE study_version_id=?",
            (str(source.study_version_id),),
        ).fetchone()
    version = (
        None
        if version_row is None
        else get_bayesian_study_version_record(
            root, study_id=version_row[0], version_number=version_row[1]
        )
    )
    history = get_bayesian_history_revision_record(root, str(source.history_revision_id))
    if study is None or version is None or history is None:
        raise invalid("report_source_not_found")
    if (
        study.method_id != "doe.bayesian_optimization"
        or study.method_version not in SUPPORTED_BAYESIAN_STUDY_METHOD_VERSIONS
        or version.study_id != study.study_id
        or history.study_version_id != version.study_version_id
        or version.schema_version not in {1, 2, 3, 4}
        or history.schema_version != 1
        or version.definition_sha256 != source.definition_sha256
        or history.observation_history_sha256 != source.expected_source_sha256
    ):
        raise invalid("report_source_changed")
    factors = [BayesianFactorResponse.model_validate(item) for item in parsed(version.factors_json)]
    objective = BayesianObjectiveResponse.model_validate(parsed(version.objective_json))
    constraints = [
        BayesianLinearConstraintResponse.model_validate(item)
        for item in parsed(version.constraints_json)
    ]
    initial = BayesianInitialDesignResponse.model_validate(parsed(version.initial_design_json))
    definition = _definition_payload(
        method_version=study.method_version,
        factors=factors,
        objective=objective,
        constraints=constraints,
        initial_design=initial,
        study_schema_version=version.schema_version,
    )
    if digest(definition) != version.definition_sha256:
        raise invalid("report_source_changed")
    identifiers = parsed(history.completed_trial_ids_json)
    if (
        not isinstance(identifiers, list)
        or len(identifiers) != history.completed_trial_count
        or len(set(identifiers)) != len(identifiers)
    ):
        raise invalid()
    observations = []
    observation_records = []
    for identifier in identifiers:
        trial = get_bayesian_trial_record(root, identifier)
        if (
            trial is None
            or trial.study_version_id != version.study_version_id
            or trial.state != "completed"
        ):
            raise invalid()
        validated = _verified_trial(trial, version.definition_sha256, factors)
        finite(validated.objective_value)
        observations.append(validated)
        observation_records.append(trial)
    if (
        len({item.trial_number for item in observations}) != len(observations)
        or [item.trial_number for item in observations]
        != sorted(item.trial_number for item in observations)
        or canonical_bayesian_observation_history_sha256(
            definition_sha256=version.definition_sha256, completed_trials=observation_records
        )
        != history.observation_history_sha256
    ):
        raise invalid("report_source_changed")
    attachment: dict[str, Any] | None = None
    if source.attachment.kind == "recommendation":
        ref = source.attachment
        record = get_bayesian_recommendation_record(root, str(ref.recommendation_id))
        if (
            record is None
            or record.result_sha256 != ref.result_json_sha256
            or record.source_history_revision_id != history.history_revision_id
        ):
            raise invalid("report_source_changed")
        trial = get_bayesian_trial_record(root, record.trial_id)
        if trial is None or trial.study_version_id != version.study_version_id:
            raise invalid()
        response = validate_bayesian_recommendation_record(
            record=record,
            study_id=study.study_id,
            study_version_id=version.study_version_id,
            definition_sha256=version.definition_sha256,
            source_history_revision_id=history.history_revision_id,
            source_history_sha256=history.observation_history_sha256,
            source_observation_values=[finite(item.objective_value) for item in observations],
            factors=factors,
            constraints=constraints,
            objective_direction=str(objective.goal_type or objective.direction),
            current_trial=_verified_trial(trial, version.definition_sha256, factors),
        )
        if response.result_payload_sha256 != ref.result_payload_sha256:
            raise invalid("report_source_changed")
        attachment = response.model_dump(mode="json", exclude={"is_latest", "current_trial"})
    elif source.attachment.kind == "batch":
        attachment = _batch_snapshot(
            settings,
            source,
            factors,
            len(observations),
            str(objective.goal_type or objective.direction),
        )
    return (
        {
            "definition": definition,
            "history": asdict(history),
            "observations": [item.model_dump(mode="json") for item in observations],
            "attachment": attachment,
            "source_warnings": ["historical_snapshot_without_current_trial_overlay"],
            "owner": {
                "method_id": study.method_id,
                "method_version": study.method_version,
                "app_version": study.app_version,
                "created_at": study.created_at,
            },
        },
        study.name,
        history.created_at,
    )


def _verified_trial(
    trial: Any, definition_sha256: str, factors: list[BayesianFactorResponse]
) -> Any:
    response = _trial_response(trial)
    identifiers = {item.factor_id for item in factors}
    actual, normalized = response.actual_coordinates, response.normalized_coordinates
    if set(actual) != identifiers or set(normalized) != identifiers:
        raise invalid()
    for factor in factors:
        value, coordinate = finite(actual[factor.factor_id]), finite(normalized[factor.factor_id])
        if (
            not factor.low <= value <= factor.high
            or not 0 <= coordinate <= 1
            or not math.isclose(
                (value - factor.low) / (factor.high - factor.low),
                coordinate,
                rel_tol=1e-10,
                abs_tol=1e-12,
            )
        ):
            raise invalid()
    coordinate_payload = {
        "definition_sha256": definition_sha256,
        "trial_number": trial.trial_number,
        "origin": trial.origin,
        "actual_coordinates": actual,
        "normalized_coordinates": normalized,
    }
    if trial.origin == "replicate":
        coordinate_payload["replicate_of_trial_id"] = trial.replicate_of_trial_id
    if digest(coordinate_payload) != trial.coordinates_sha256:
        raise invalid("report_source_changed")
    return response


def _batch_snapshot(
    settings: Settings,
    source: BayesianHistoryReportSource,
    factors: list[BayesianFactorResponse],
    observation_count: int,
    objective_goal: str,
) -> dict[str, Any]:
    ref = source.attachment
    assert ref.kind == "batch"
    record = get_bayesian_recommendation_batch_record(settings.workspace_root, str(ref.batch_id))
    if (
        record is None
        or record.study_version_id != str(source.study_version_id)
        or record.source_history_revision_id != str(source.history_revision_id)
        or record.source_observation_history_sha256 != source.expected_source_sha256
        or record.result_sha256 != ref.result_json_sha256
    ):
        raise invalid("report_source_changed")
    if (
        hashlib.sha256(record.config_json.encode("utf-8")).hexdigest() != record.config_sha256
        or hashlib.sha256(record.result_json.encode("utf-8")).hexdigest() != record.result_sha256
    ):
        raise invalid("report_source_changed")
    config = parsed(record.config_json)
    request: Any
    response: Any
    if record.result_schema_version == 2:
        from app.api.v1.schemas.bayesian_noise import (
            BayesianNoiseBatchCreateRequest,
            BayesianNoiseBatchResponse,
        )
        from app.services.bayesian_studies import get_bayesian_study

        # Validate the saved graph, never regenerate the recommendation for export.
        get_bayesian_study(settings, source.study_id)
        request = BayesianNoiseBatchCreateRequest.model_validate(config["request"])
        response = BayesianNoiseBatchResponse.model_validate(parsed(record.result_json))
        completed_count = response.shared_model.raw_observation_count
    else:
        request = BayesianRecommendationBatchCreateRequest.model_validate(config["request"])
        response = BayesianRecommendationBatchResponse.model_validate(parsed(record.result_json))
        completed_count = response.shared_model.completed_observation_count
    expected_context = {
        "study_id": str(source.study_id),
        "study_version_id": str(source.study_version_id),
        "definition_sha256": source.definition_sha256,
        "source_history_revision_id": str(source.history_revision_id),
        "source_observation_history_sha256": source.expected_source_sha256,
    }
    provenance = response.provenance.model_dump(mode="json")
    if (
        any(
            config.get(key) != value or provenance.get(key) != value
            for key, value in expected_context.items()
        )
        or config.get("schema_version") != record.config_schema_version
        or record.method_id != "doe.bayesian_optimization"
        or response.created_at != record.created_at
        or provenance.get("batch_id") != record.batch_id
        or provenance.get("method_id") != record.method_id
        or provenance.get("method_version") != record.method_version
        or str(request.expected_history_revision_id) != str(source.history_revision_id)
        or completed_count != observation_count
        or response.shared_model.objective_goal_type != objective_goal
    ):
        raise invalid()
    payload = response.model_dump(mode="json", exclude={"is_latest", "batch_state"})
    if (
        digest({**payload, "result_sha256": "0" * 64}) != response.result_sha256
        or response.result_sha256 != ref.result_payload_sha256
        or str(response.batch_id) != record.batch_id
        or str(response.study_id) != str(source.study_id)
        or str(response.study_version_id) != record.study_version_id
        or str(response.source_history_revision_id) != record.source_history_revision_id
        or response.source_observation_history_sha256 != source.expected_source_sha256
        or response.definition_sha256 != source.definition_sha256
        or response.method_version != record.method_version
        or response.config_sha256 != record.config_sha256
        or response.batch_size != record.batch_size
        or request.batch_size != record.batch_size
        or response.batch_policy != record.batch_policy
    ):
        raise invalid()
    items = list_bayesian_recommendation_batch_item_records(
        settings.workspace_root, record.batch_id
    )
    if len(items) != record.batch_size or len(response.items) != len(items):
        raise invalid()
    for rank, (stored, item) in enumerate(zip(items, response.items, strict=True), 1):
        trial = get_bayesian_trial_record(settings.workspace_root, stored.trial_id)
        if trial is None or trial.study_version_id != record.study_version_id:
            raise invalid()
        validated = _verified_trial(trial, source.definition_sha256, factors)
        item_json = canonical(item.model_dump(mode="json"))
        if (
            stored.rank != rank
            or item.rank != rank
            or stored.item_id != str(item.item_id)
            or stored.batch_id != record.batch_id
            or stored.item_result_json != item_json
            or hashlib.sha256(item_json.encode("utf-8")).hexdigest() != stored.item_result_sha256
            or item.trial.trial_id != validated.trial_id
            or item.trial.coordinates_sha256 != validated.coordinates_sha256
            or item.actual_coordinates != validated.actual_coordinates
            or item.normalized_coordinates != validated.normalized_coordinates
        ):
            raise invalid()
    for payload_item in payload["items"]:
        payload_item.pop("current_trial", None)
    return payload
