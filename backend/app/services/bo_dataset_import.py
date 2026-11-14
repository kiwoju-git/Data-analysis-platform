"""Bounded, source-verified import of measured rows into the existing BO store."""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, replace
from typing import Any, cast
from uuid import UUID, uuid4

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.bayesian import (
    BayesianFactorRequest,
    BayesianFactorResponse,
    BayesianLinearConstraintResponse,
    BayesianObjectiveRequest,
    BayesianObjectiveResponse,
    BayesianStudyCreateRequest,
    BayesianStudyResponse,
)
from app.api.v1.schemas.bo_curve_policy import (
    AnyDesirabilityObjective,
    BayesianVersionedCurveObjective,
)
from app.api.v1.schemas.bo_dataset_import import (
    DatasetFactorMapping,
    DatasetImportCreateRequest,
    DatasetImportPreflightRequest,
)
from app.api.v1.schemas.bo_dataset_source import (
    DatasetImportedInitialDesign,
    DatasetImportPreflightResponse,
    DatasetImportSource,
)
from app.api.v1.schemas.bo_mixed_studies import (
    MixedCategoricalFactorRequest,
    MixedCategoricalFactorResponse,
    MixedFactorResponse,
    MixedStudyResponse,
    mixed_constraint_definitions,
    mixed_factor_domains,
)
from app.api.v1.schemas.bo_mixture import MixtureStudyDefinition, MixtureStudyResponse
from app.api.v1.schemas.bo_mixture_dataset_import import (
    MixtureDatasetImportCreateRequest,
    MixtureDatasetImportedInitialDesign,
    MixtureDatasetImportPreflightRequest,
    MixtureDatasetImportPreflightResponse,
    MixtureImportComponent,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services import bayesian_studies as legacy
from app.services.analysis_run_execution import (
    APP_VERSION,
    parse_filter_conditions,
    parse_filter_decimal,
    row_matches_condition,
    runtime_build_provenance,
    utc_now,
)
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
)
from app.statistics.bo_factor_domains import BoFactorDomain, BoFactorValue, encode_bo_point
from app.statistics.bo_mixed_initial_design import (
    mixed_constraints_satisfied,
    validate_mixed_constraints,
)
from app.statistics.doe_factor_domain import DoeFactorDomain
from app.storage.bayesian_studies import (
    BayesianStorageConflict,
    BayesianStudyRecord,
    BayesianStudyVersionRecord,
    BayesianTrialRecord,
    insert_bayesian_study_bundle,
)
from app.storage.bo_dataset_import import commit_dataset_import, validate_import_reference


@dataclass(frozen=True)
class _Prepared:
    preview: DatasetImportPreflightResponse | MixtureDatasetImportPreflightResponse
    context: DatasetRowsContext
    factors: list[MixedFactorResponse]
    objective: BayesianObjectiveResponse | AnyDesirabilityObjective
    constraints: list[BayesianLinearConstraintResponse]
    actual: list[dict[str, BoFactorValue]]
    encoded: list[dict[str, float]]
    observations: list[float | dict[str, float]]
    indices: list[int]
    mixed: bool
    mixture: MixtureStudyDefinition | None = None


def _error(code: str) -> ApiError:
    return ApiError(
        code=code, message="측정 데이터 가져오기 조건 또는 원본 상태를 확인하세요.", status_code=409
    )


def preflight_dataset_import(
    settings: Settings, body: DatasetImportPreflightRequest | MixtureDatasetImportPreflightRequest
) -> DatasetImportPreflightResponse | MixtureDatasetImportPreflightResponse:
    return _prepare(settings, body).preview


def _prepare(
    settings: Settings, body: DatasetImportPreflightRequest | MixtureDatasetImportPreflightRequest
) -> _Prepared:
    try:
        return _prepare_source(settings, body)
    except OSError as exc:
        raise _error("bayesian_import_source_stale") from exc


def _prepare_source(
    settings: Settings, body: DatasetImportPreflightRequest | MixtureDatasetImportPreflightRequest
) -> _Prepared:
    context = get_dataset_rows_context(settings, body.dataset_version_id)
    if context.version.schema_hash != body.expected_schema_hash:
        raise _error("bayesian_import_source_stale")
    columns = {item.column_id: item for item in context.columns}
    mappings: list[Any] = [
        *body.factor_mappings,
        *body.response_mappings,
    ]
    if any(item.column_id not in columns for item in mappings):
        raise _error("bayesian_import_column_missing")
    numeric_ids = [item.column_id for item in body.response_mappings] + [
        item.column_id
        for item in body.factor_mappings
        if isinstance(item.factor, BayesianFactorRequest | MixtureImportComponent)
    ]
    if any(columns[item].data_type not in {"integer", "decimal"} for item in numeric_ids):
        raise _error("bayesian_import_numeric_column_required")
    mixed = any(
        isinstance(item.factor, MixedCategoricalFactorRequest) for item in body.factor_mappings
    )
    factors: list[MixedFactorResponse]
    objective: BayesianObjectiveResponse | AnyDesirabilityObjective
    domains: tuple[BoFactorDomain, ...]
    mixture = body.definition() if isinstance(body, MixtureDatasetImportPreflightRequest) else None
    mixture_domain = mixture.domain() if mixture is not None else None
    if mixture is not None:
        factors = []
        objective = mixture.objective
        constraints = [
            BayesianLinearConstraintResponse.model_validate(c.model_dump())
            for c in body.constraints
        ]
        domains = ()
    elif not mixed:
        validated = BayesianStudyCreateRequest(
            name=body.name,
            factors=[cast(BayesianFactorRequest, item.factor) for item in body.factor_mappings],
            objective=body.objective,
            constraints=body.constraints,
            initial_design_seed=0,
            initial_design_size=2,
        )
        numeric_factors = legacy._validated_factor_payload(validated)
        factors = list(numeric_factors)
        objective = legacy._validated_objective_payload(validated)
        constraints = legacy._validated_constraint_payload(validated, numeric_factors)
        domains = ()
    else:
        factors = []
        for index, item in enumerate(cast(list[DatasetFactorMapping], body.factor_mappings)):
            factor = item.factor
            if isinstance(factor, MixedCategoricalFactorRequest):
                factors.append(
                    MixedCategoricalFactorResponse(**factor.model_dump(), order=index + 1)
                )
            else:
                domain = DoeFactorDomain(
                    factor.low,
                    factor.high,
                    factor.domain_kind,
                    factor.step,
                    factor.display_decimals,
                )
                factors.append(
                    BayesianFactorResponse(
                        **factor.model_dump(),
                        order=index + 1,
                        scaling_rule="linear_0_1",
                        level_count=domain.level_count,
                    )
                )
        try:
            domains = mixed_factor_domains(factors)
        except ValueError as exc:
            raise _error("bayesian_import_factor_space_invalid") from exc
        constraints = [
            BayesianLinearConstraintResponse.model_validate(item.model_dump())
            for item in body.constraints
        ]
        try:
            validate_mixed_constraints(domains, mixed_constraint_definitions(constraints))
        except ValueError as exc:
            raise _error("bayesian_study_constraint_invalid") from exc
        objective = cast(AnyDesirabilityObjective, body.objective)
    conditions = parse_filter_conditions(context, body.filter_snapshot)
    actual_rows: list[dict[str, BoFactorValue]] = []
    encoded_rows: list[dict[str, float]] = []
    observations: list[float | dict[str, float]] = []
    indices: list[int] = []
    filtered = missing = used = 0
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if not all(row_matches_condition(row, item, context) for item in conditions):
            filtered += 1
            continue
        values = {item.column_id: row[columns[item.column_id].column_index] for item in mappings}
        if any(value is None or value.strip() == "" for value in values.values()):
            missing += 1
            continue
        numbers: dict[str, float] = {}
        for column_id in numeric_ids:
            value = parse_filter_decimal(
                cast(str, values[column_id]),
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
            )
            if value is None or not math.isfinite(float(value)):
                raise _error("bayesian_import_nonfinite_value")
            numbers[column_id] = float(value)
        actual: dict[str, BoFactorValue] = {
            item.factor.factor_id: numbers[item.column_id]
            if isinstance(item.factor, BayesianFactorRequest | MixtureImportComponent)
            else cast(str, values[item.column_id])
            for item in body.factor_mappings
        }
        encoded: dict[str, float] = {}
        try:
            if mixture_domain is not None:
                # Imported actual amounts remain untouched. The explicit domain
                # validates every component and closure before any commit.
                validated_actual, vector = mixture_domain.canonical(actual)
                if validated_actual != actual:
                    raise ValueError("import would coerce actual coordinates")
                encoded = dict(zip(mixture_domain.keys, vector, strict=True))
            elif mixed:
                encoded = dict(
                    zip(
                        (item.factor_id for item in domains),
                        encode_bo_point(domains, actual),
                        strict=True,
                    )
                )
            else:
                for numeric_factor in cast(list[BayesianFactorResponse], factors):
                    numeric = float(actual[numeric_factor.factor_id])
                    domain = DoeFactorDomain(
                        numeric_factor.low,
                        numeric_factor.high,
                        numeric_factor.domain_kind,
                        numeric_factor.step,
                        numeric_factor.display_decimals,
                    )
                    if not domain.is_executable(numeric):
                        raise ValueError("domain")
                    encoded[numeric_factor.factor_id] = (numeric - numeric_factor.low) / (
                        numeric_factor.high - numeric_factor.low
                    )
        except ValueError as exc:
            raise _error("bayesian_import_factor_out_of_domain") from exc
        feasible = (
            mixed_constraints_satisfied(actual, mixed_constraint_definitions(constraints))
            if mixed or mixture is not None
            else legacy._constraints_satisfied(cast(dict[str, float], actual), constraints)
        )
        if not feasible:
            raise _error("bayesian_import_infeasible_row")
        observation: float | dict[str, float] = (
            numbers[body.response_mappings[0].column_id]
            if isinstance(body.objective, BayesianObjectiveRequest)
            else {
                cast(str, item.response_id): numbers[item.column_id]
                for item in body.response_mappings
            }
        )
        used += 1
        # Always exhaust and hash the canonical stream; never materialize more than the budget.
        if used <= 200:
            actual_rows.append(actual)
            encoded_rows.append(encoded)
            observations.append(observation)
            indices.append(row_index)
    if missing and body.missing_policy == "reject":
        raise _error("bayesian_import_missing_values")
    if used > 200:
        raise _error("bayesian_import_trial_limit")
    if not used:
        raise _error("bayesian_import_no_observations")
    groups: dict[str, set[str]] = {}
    for point, observation in zip(actual_rows, observations, strict=True):
        groups.setdefault(legacy._sha256(point), set()).add(legacy._json_dumps(observation))
    warnings = []
    if used != len(groups):
        warnings.append("bayesian_import_repeated_coordinates_retained")
    if missing:
        warnings.append("bayesian_import_complete_case_exclusions")
    if len(groups) < (
        max(2, len(mixture.domain().keys)) if mixture is not None else max(2, len(factors) + 1)
    ):
        warnings.append("bayesian_optimization_history_incomplete")
    source = DatasetImportSource(
        dataset_id=UUID(context.dataset.dataset_id),
        dataset_version_id=body.dataset_version_id,
        schema_hash=context.version.schema_hash,
        canonical_sha256=context.canonical_rows_artifact.sha256,
        raw_sha256=context.dataset.sha256,
        filter_sha256=legacy._sha256(body.filter_snapshot.model_dump(mode="json")),
    )
    counts: dict[str, Any] = dict(
        n_total=context.version.row_count,
        n_filtered=filtered,
        n_missing=missing,
        n_used=used,
        unique_coordinate_count=len(groups),
        repeated_coordinate_count=used - len(groups),
        conflicting_coordinate_count=sum(len(values) > 1 for values in groups.values()),
        warnings=warnings,
    )
    digest = legacy._sha256(
        {
            "request": body.model_dump(mode="json"),
            "source": source.model_dump(mode="json"),
            "counts": counts,
            "source_row_indices": indices,
            "observations": _observation_payload(actual_rows, encoded_rows, observations),
        }
    )
    preview_type = (
        MixtureDatasetImportPreflightResponse
        if mixture is not None
        else DatasetImportPreflightResponse
    )
    preview = preview_type(source=source, preflight_sha256=digest, **counts)
    return _Prepared(
        preview,
        context,
        factors,
        objective,
        constraints,
        actual_rows,
        encoded_rows,
        observations,
        indices,
        mixed,
        mixture,
    )


def _observation_payload(
    actual: list[dict[str, BoFactorValue]],
    encoded: list[dict[str, float]],
    observations: list[float | dict[str, float]],
) -> dict[str, Any]:
    return {
        "rows": [
            {"actual": point, "encoded": normalized, "observation": observation}
            for point, normalized, observation in zip(actual, encoded, observations, strict=True)
        ]
    }


def create_dataset_import(
    settings: Settings, body: DatasetImportCreateRequest | MixtureDatasetImportCreateRequest
) -> BayesianStudyResponse | MixedStudyResponse | MixtureStudyResponse:
    request_hash = legacy._sha256(body.model_dump(mode="json"))
    request_type = (
        MixtureDatasetImportPreflightRequest
        if isinstance(body, MixtureDatasetImportCreateRequest)
        else DatasetImportPreflightRequest
    )
    request = request_type.model_validate(
        body.model_dump(exclude={"request_id", "expected_preflight_sha256"})
    )

    def create(connection: sqlite3.Connection) -> str:
        prepared = _prepare(settings, request)
        if prepared.preview.preflight_sha256 != body.expected_preflight_sha256:
            raise _error("bayesian_import_preflight_stale")
        return _insert(settings, body, request_hash, prepared, connection)

    try:
        study_id = commit_dataset_import(
            settings.workspace_root, str(body.request_id), request_hash, create
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    from app.services.bo_mixed_studies import get_any_bayesian_study

    return get_any_bayesian_study(settings, UUID(study_id))


def _insert(
    settings: Settings,
    body: DatasetImportCreateRequest | MixtureDatasetImportCreateRequest,
    request_hash: str,
    prepared: _Prepared,
    connection: sqlite3.Connection,
) -> str:
    from app.services.bo_mixed_studies import mixed_coordinate_payload, mixed_definition_payload

    preview = prepared.preview
    initial_type = (
        MixtureDatasetImportedInitialDesign
        if prepared.mixture is not None
        else DatasetImportedInitialDesign
    )
    initial = initial_type(
        **preview.model_dump(exclude={"schema_version"}),
        requested_size=preview.n_used,
        generated_size=preview.n_used,
        source_row_indices=prepared.indices,
        factor_columns={item.factor.factor_id: item.column_id for item in body.factor_mappings},
        response_columns={
            item.response_id or "objective": item.column_id for item in body.response_mappings
        },
        missing_policy=body.missing_policy,
        filter_snapshot=body.filter_snapshot,
        observations_sha256=legacy._sha256(
            _observation_payload(prepared.actual, prepared.encoded, prepared.observations)
        ),
        request_id=body.request_id,
        request_sha256=request_hash,
        runtime_provenance=runtime_build_provenance(settings),
    )
    if prepared.mixture is not None:
        return _insert_mixture(
            settings,
            cast(MixtureDatasetImportCreateRequest, body),
            request_hash,
            prepared,
            initial,
            connection,
        )
    method_version = METHOD_VERSIONS[legacy.BAYESIAN_METHOD_ID]
    schema = (
        7
        if prepared.mixed
        else 6
        if isinstance(prepared.objective, BayesianVersionedCurveObjective)
        else 4
        if isinstance(prepared.objective, BayesianObjectiveResponse)
        else 5
    )
    if prepared.mixed:
        definition = mixed_definition_payload(
            method_version=method_version,
            factors=prepared.factors,
            objective=cast(AnyDesirabilityObjective, prepared.objective),
            constraints=prepared.constraints,
            initial_design=initial,
        )
    else:
        definition = legacy._definition_payload(
            method_version=method_version,
            factors=cast(list[BayesianFactorResponse], prepared.factors),
            objective=prepared.objective,
            constraints=prepared.constraints,
            initial_design=initial,
            study_schema_version=schema,
        )
    definition_hash, now = legacy._sha256(definition), utc_now()
    study_id, version_id = str(uuid4()), str(uuid4())
    study = BayesianStudyRecord(
        study_id,
        legacy.BAYESIAN_METHOD_ID,
        method_version,
        body.name.strip(),
        "active",
        1,
        now,
        now,
        APP_VERSION,
    )
    version = BayesianStudyVersionRecord(
        version_id,
        study_id,
        1,
        schema,
        legacy._json_dumps([item.model_dump(mode="json") for item in prepared.factors]),
        legacy._json_dumps(prepared.objective.model_dump(mode="json")),
        legacy._json_dumps([item.model_dump(mode="json") for item in prepared.constraints]),
        legacy._json_dumps(initial.model_dump(mode="json")),
        definition_hash,
        now,
    )
    trials = []
    for index, (actual, encoded, observation) in enumerate(
        zip(prepared.actual, prepared.encoded, prepared.observations, strict=True)
    ):
        trial = legacy._new_trial_record(
            study_version_id=version_id,
            definition_sha256=definition_hash,
            trial_number=index + 1,
            actual=cast(dict[str, float], actual),
            normalized=encoded,
            created_at=now,
        )
        if prepared.mixed:
            trial = replace(
                trial,
                coordinates_sha256=legacy._sha256(
                    mixed_coordinate_payload(
                        definition_sha256=definition_hash,
                        trial_number=index + 1,
                        origin="initial_design",
                        actual=actual,
                        encoded=encoded,
                    )
                ),
            )
        trials.append(
            replace(
                trial,
                state="completed",
                closed_at=now,
                objective_value=observation if isinstance(observation, float) else None,
                response_values_json=legacy._json_dumps(observation)
                if isinstance(observation, dict)
                else None,
            )
        )
    history = legacy._new_history_record(
        study_version_id=version_id,
        definition_sha256=definition_hash,
        revision_number=1,
        completed_trials=trials,
        previous_history_sha256=None,
        created_at=now,
        schema_version=1 if schema == 4 else 2,
    )
    insert_bayesian_study_bundle(
        settings.workspace_root,
        study=study,
        version=version,
        trials=trials,
        initial_history=history,
        transaction=connection,
    )
    connection.execute(
        "INSERT INTO bayesian_dataset_imports VALUES (?,?,?,?,?,?,?,?)",
        (
            version_id,
            str(body.dataset_version_id),
            str(body.request_id),
            request_hash,
            preview.preflight_sha256,
            preview.source.schema_hash,
            preview.source.canonical_sha256,
            1,
        ),
    )
    return study_id


def _insert_mixture(
    settings: Settings,
    body: MixtureDatasetImportCreateRequest,
    request_hash: str,
    prepared: _Prepared,
    initial: DatasetImportedInitialDesign | MixtureDatasetImportedInitialDesign,
    connection: sqlite3.Connection,
) -> str:
    from app.services.bo_mixture_studies import METHOD_VERSION, new_mixture_trial_record

    definition_request = prepared.mixture
    if definition_request is None:
        raise _error("bayesian_import_factor_space_invalid")
    design = definition_request.domain()
    definition = {
        "schema_version": 8,
        "method_version": METHOD_VERSION,
        "request": definition_request.model_dump(mode="json"),
        "design_domain": design.payload(),
        "initial_design": initial.model_dump(mode="json"),
    }
    digest, now = legacy._sha256(definition), utc_now()
    study_id, version_id = str(uuid4()), str(uuid4())
    owner = BayesianStudyRecord(
        study_id,
        legacy.BAYESIAN_METHOD_ID,
        METHOD_VERSION,
        body.name.strip(),
        "active",
        1,
        now,
        now,
        APP_VERSION,
    )
    version = BayesianStudyVersionRecord(
        version_id,
        study_id,
        1,
        8,
        legacy._json_dumps(
            {
                "request": definition_request.model_dump(mode="json"),
                "design_domain": design.payload(),
            }
        ),
        legacy._json_dumps(definition_request.objective.model_dump(mode="json")),
        legacy._json_dumps([c.model_dump(mode="json") for c in definition_request.constraints]),
        legacy._json_dumps(initial.model_dump(mode="json")),
        digest,
        now,
    )
    trials = []
    for index, (point, observation) in enumerate(
        zip(prepared.actual, prepared.observations, strict=True)
    ):
        if not isinstance(observation, dict):
            raise _error("bayesian_import_response_mapping_invalid")
        trial = new_mixture_trial_record(
            study_version_id=version_id,
            definition_sha256=digest,
            design=design,
            trial_number=index + 1,
            actual=point,
            created_at=now,
        )
        trials.append(
            replace(
                trial,
                state="completed",
                closed_at=now,
                response_values_json=legacy._json_dumps(observation),
            )
        )
    history = legacy._new_history_record(
        study_version_id=version_id,
        definition_sha256=digest,
        revision_number=1,
        completed_trials=trials,
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
        transaction=connection,
    )
    connection.execute(
        "INSERT INTO bayesian_dataset_imports VALUES (?,?,?,?,?,?,?,?)",
        (
            version_id,
            str(body.dataset_version_id),
            str(body.request_id),
            request_hash,
            prepared.preview.preflight_sha256,
            prepared.preview.source.schema_hash,
            prepared.preview.source.canonical_sha256,
            2,
        ),
    )
    return study_id


def validate_imported_trials(
    settings: Settings,
    version: BayesianStudyVersionRecord,
    initial: DatasetImportedInitialDesign | MixtureDatasetImportedInitialDesign,
    trials: list[BayesianTrialRecord],
) -> None:
    imported = trials[: initial.generated_size]
    if (
        initial.generated_size != initial.requested_size
        or initial.n_used != initial.generated_size
        or len(imported) != initial.generated_size
        or len(initial.source_row_indices) != len(imported)
        or initial.source_row_indices != sorted(set(initial.source_row_indices))
        or any(index < 0 or index >= initial.n_total for index in initial.source_row_indices)
        or initial.n_total != initial.n_filtered + initial.n_missing + initial.n_used
        or any(item.origin != "initial_design" or item.state != "completed" for item in imported)
        or not validate_import_reference(
            settings.workspace_root,
            version.study_version_id,
            (
                str(initial.source.dataset_version_id),
                str(initial.request_id),
                initial.request_sha256,
                initial.preflight_sha256,
                initial.source.schema_hash,
                initial.source.canonical_sha256,
                initial.import_schema_version,
            ),
        )
    ):
        raise legacy._artifact_error()
    payload = _observation_payload(
        [legacy._json_dict(item.actual_coordinates_json) for item in imported],
        [legacy._numeric_json_dict(item.normalized_coordinates_json) for item in imported],
        [cast(float | dict[str, float], legacy._trial_observation(item)) for item in imported],
    )
    if legacy._sha256(payload) != initial.observations_sha256:
        raise legacy._artifact_error()
