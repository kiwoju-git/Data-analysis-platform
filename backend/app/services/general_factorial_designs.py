from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.doe import (
    DoeDesignResponseSeries,
    DoeDesignResponsesResponse,
    DoeDesignResponsesUpsertRequest,
    DoeDesignResponseValue,
    DoeResponseRevisionCreateRequest,
    GeneralFactorialAnalysisCreateRequest,
    GeneralFactorialAnalysisResponse,
    GeneralFactorialDesignCreateRequest,
    GeneralFactorialDesignResponse,
    GeneralFactorialFactorResponse,
    GeneralFactorialOptionsResponse,
    GeneralFactorialRunResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import APP_VERSION, utc_now
from app.services.doe_response_revisions import (
    create_response_revision,
    load_response_revision_dependency,
)
from app.statistics.general_factorial_analysis import (
    GeneralFactorialAnalysisError,
    GeneralFactorialAnalysisRun,
    calculate_general_factorial_analysis,
)
from app.statistics.general_factorial_design import (
    GeneralFactorialDesignError,
    GeneralFactorialFactor,
    GeneralFactorialOptions,
    GeneralFactorialRun,
    canonical_general_factorial_payload,
    factor_to_payload,
    generate_general_full_factorial_design,
    options_to_payload,
)
from app.storage.metadata import (
    ExperimentDesignAnalysisRecord,
    ExperimentDesignRecord,
    ExperimentDesignVersionRecord,
    ExperimentRunRecord,
    get_current_experiment_response_revision_record,
    get_experiment_design_analysis_record,
    get_experiment_design_record,
    get_experiment_design_version_record,
    insert_experiment_design_analysis_record,
    insert_experiment_design_records,
    list_experiment_run_records,
    list_experiment_run_response_records,
)

DOE_GENERAL_FACTORIAL_METHOD_ID: Literal["doe.general_factorial_design"] = (
    "doe.general_factorial_design"
)
DOE_GENERAL_FACTORIAL_METHOD_VERSION = cast(
    Literal["0.1.0"], METHOD_VERSIONS[DOE_GENERAL_FACTORIAL_METHOD_ID]
)


def create_general_factorial_design(
    settings: Settings,
    body: GeneralFactorialDesignCreateRequest,
) -> GeneralFactorialDesignResponse:
    factors = [
        GeneralFactorialFactor(
            name=factor.name.strip(),
            levels=tuple(
                float(value) if isinstance(value, int | float) else value.strip()
                for value in factor.levels
            ),
            unit=None if factor.unit is None else factor.unit.strip() or None,
        )
        for factor in body.factors
    ]
    options = GeneralFactorialOptions(
        replicates=body.replicates,
        randomize=body.randomize,
        randomization_seed=body.randomization_seed,
        max_interaction_order=body.max_interaction_order,
    )
    try:
        generated = generate_general_full_factorial_design(factors, options)
    except GeneralFactorialDesignError as exc:
        raise ApiError(
            code=exc.code, message=str(exc), status_code=status.HTTP_409_CONFLICT
        ) from exc

    design_id = uuid4()
    design_version_id = uuid4()
    now = _utc_now()
    design_record = ExperimentDesignRecord(
        design_id=str(design_id),
        method_id=DOE_GENERAL_FACTORIAL_METHOD_ID,
        method_version=DOE_GENERAL_FACTORIAL_METHOD_VERSION,
        family=generated.family,
        name=body.name.strip(),
        status="designed",
        current_version=1,
        created_at=now,
        updated_at=now,
        app_version=APP_VERSION,
    )
    version_record = ExperimentDesignVersionRecord(
        design_version_id=str(design_version_id),
        design_id=str(design_id),
        version_number=1,
        factors_json=_json_dumps([factor_to_payload(factor) for factor in generated.factors]),
        options_json=_json_dumps(options_to_payload(generated.options)),
        run_count=len(generated.runs),
        design_sha256=generated.design_sha256,
        created_at=now,
    )
    run_records = [
        ExperimentRunRecord(
            run_id=str(uuid4()),
            design_version_id=str(design_version_id),
            standard_order=run.standard_order,
            run_order=run.run_order,
            replicate_index=run.replicate_index,
            center_point=False,
            block_index=None,
            factor_levels_json=_json_dumps(run.factor_levels),
            coded_levels_json=_json_dumps(run.level_indices),
        )
        for run in generated.runs
    ]
    insert_experiment_design_records(
        settings.workspace_root,
        design=design_record,
        version=version_record,
        runs=run_records,
    )
    return _response(design_record, version_record, run_records)


def get_general_factorial_design(
    settings: Settings, design_id: UUID
) -> GeneralFactorialDesignResponse:
    return _response(*_load(settings, design_id))


def save_general_factorial_responses(
    settings: Settings,
    design_id: UUID,
    body: DoeDesignResponsesUpsertRequest,
) -> DoeDesignResponsesResponse:
    create_response_revision(
        settings,
        design_id,
        DoeResponseRevisionCreateRequest(**body.model_dump()),
        allow_analyzed=False,
        require_explicit_supersedes=False,
    )
    return list_general_factorial_responses(settings, design_id)


def list_general_factorial_responses(
    settings: Settings, design_id: UUID
) -> DoeDesignResponsesResponse:
    design, version, runs = _load(settings, design_id)
    records = list_experiment_run_response_records(
        settings.workspace_root, version.design_version_id
    )
    run_order_by_id = {run.run_id: run.run_order for run in runs}
    grouped: dict[str, list[DoeDesignResponseValue]] = {}
    units: dict[str, str | None] = {}
    for record in records:
        grouped.setdefault(record.response_name, []).append(
            DoeDesignResponseValue(
                run_order=run_order_by_id[record.run_id], value=record.response_value
            )
        )
        units.setdefault(record.response_name, record.unit)
    series: list[DoeDesignResponseSeries] = []
    for name, values in sorted(grouped.items()):
        revision = get_current_experiment_response_revision_record(
            settings.workspace_root, version.design_version_id, name
        )
        if revision is None or revision.value_count != len(values):
            raise _metadata_error("doe_response_revision_dependency_mismatch")
        series.append(
            DoeDesignResponseSeries(
                response_name=name,
                unit=units[name],
                response_revision_id=UUID(revision.response_revision_id),
                response_revision_number=revision.revision_number,
                response_revision_schema_version=1,
                response_revision_sha256=revision.response_sha256,
                created_at=revision.created_at,
                closed_at=revision.closed_at,
                response_count=len(values),
                values=sorted(values, key=lambda item: item.run_order),
            )
        )
    return DoeDesignResponsesResponse(
        design_id=UUID(design.design_id),
        design_version_id=UUID(version.design_version_id),
        version_number=version.version_number,
        status=design.status,
        responses=series,
    )


def create_general_factorial_analysis(
    settings: Settings,
    design_id: UUID,
    body: GeneralFactorialAnalysisCreateRequest,
) -> GeneralFactorialAnalysisResponse:
    design = get_general_factorial_design(settings, design_id)
    dependency = load_response_revision_dependency(
        settings,
        design_version_id=design.design_version_id,
        response_name=body.response_name.strip(),
        response_revision_id=body.response_revision_id,
    )
    response_by_run = {record.run_id: record for record in dependency.response_records}
    calculation_runs = [
        GeneralFactorialAnalysisRun(
            run_order=run.run_order,
            level_indices=_json_int_dict(run.coded_levels_json),
            factor_levels=_json_dict(run.factor_levels_json),
            response=response_by_run[run.run_id].response_value,
        )
        for run in dependency.runs
    ]
    units = {record.unit for record in dependency.response_records}
    if len(units) != 1:
        raise _metadata_error("doe_general_factorial_response_metadata_invalid")
    try:
        result = calculate_general_factorial_analysis(
            calculation_runs,
            {factor.name: factor.levels for factor in design.factors},
            response_name=body.response_name.strip(),
            response_unit=next(iter(units)),
            max_interaction_order=body.max_interaction_order,
        )
    except GeneralFactorialAnalysisError as exc:
        raise ApiError(
            code=exc.code, message=str(exc), status_code=status.HTTP_409_CONFLICT
        ) from exc
    analysis_id = uuid4()
    now = utc_now()
    response = GeneralFactorialAnalysisResponse(
        analysis_id=analysis_id,
        design_id=design.design_id,
        design_version_id=design.design_version_id,
        design_version_number=design.version_number,
        method_id=DOE_GENERAL_FACTORIAL_METHOD_ID,
        method_version=DOE_GENERAL_FACTORIAL_METHOD_VERSION,
        analysis_schema_version=1,
        design_sha256=design.design_sha256,
        response_revision_id=UUID(dependency.revision.response_revision_id),
        response_revision_number=dependency.revision.revision_number,
        response_revision_sha256=dependency.revision.response_sha256,
        response_name=body.response_name.strip(),
        created_at=now,
        app_version=APP_VERSION,
        result=result,
    )
    result_json = _json_dumps(response.model_dump(mode="json"))
    record = ExperimentDesignAnalysisRecord(
        analysis_id=str(analysis_id),
        design_version_id=str(design.design_version_id),
        response_name=response.response_name,
        method_id=DOE_GENERAL_FACTORIAL_METHOD_ID,
        method_version=response.method_version,
        config_json=_json_dumps({"schema_version": 1, **body.model_dump(mode="json")}),
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
        response_sha256=dependency.revision.response_sha256,
        created_at=now,
        app_version=APP_VERSION,
        response_revision_id=dependency.revision.response_revision_id,
    )
    insert_experiment_design_analysis_record(
        settings.workspace_root, design_id=str(design_id), record=record, updated_at=now
    )
    return response


def get_general_factorial_analysis(
    settings: Settings, design_id: UUID, analysis_id: UUID
) -> GeneralFactorialAnalysisResponse:
    design = get_general_factorial_design(settings, design_id)
    record = get_experiment_design_analysis_record(settings.workspace_root, str(analysis_id))
    if record is None or record.design_version_id != str(design.design_version_id):
        raise ApiError(
            code="doe_general_factorial_analysis_not_found",
            message="The requested general factorial analysis was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if hashlib.sha256(record.result_json.encode("utf-8")).hexdigest() != record.result_sha256:
        raise _metadata_error("doe_general_factorial_analysis_checksum_mismatch")
    try:
        return GeneralFactorialAnalysisResponse.model_validate_json(record.result_json)
    except ValidationError as exc:
        raise _metadata_error("doe_general_factorial_analysis_metadata_invalid") from exc


def _load(
    settings: Settings, design_id: UUID
) -> tuple[ExperimentDesignRecord, ExperimentDesignVersionRecord, list[ExperimentRunRecord]]:
    design = get_experiment_design_record(settings.workspace_root, str(design_id))
    if design is None:
        raise ApiError(
            code="doe_design_not_found",
            message="The requested DOE design was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if design.method_id != DOE_GENERAL_FACTORIAL_METHOD_ID:
        raise _metadata_error("doe_general_factorial_design_family_mismatch")
    version = get_experiment_design_version_record(
        settings.workspace_root, design.design_id, design.current_version
    )
    if version is None:
        raise _metadata_error("doe_design_version_missing")
    runs = list_experiment_run_records(settings.workspace_root, version.design_version_id)
    if len(runs) != version.run_count:
        raise _metadata_error("doe_design_run_metadata_incomplete")
    return design, version, runs


def _response(
    design: ExperimentDesignRecord,
    version: ExperimentDesignVersionRecord,
    runs: list[ExperimentRunRecord],
) -> GeneralFactorialDesignResponse:
    factors_payload = _json_list(version.factors_json)
    options_payload = _json_dict(version.options_json)
    factors = [
        GeneralFactorialFactor(
            name=str(item["name"]),
            levels=tuple(item["levels"]),
            unit=None if item.get("unit") is None else str(item["unit"]),
        )
        for item in factors_payload
    ]
    options = GeneralFactorialOptions(**options_payload)
    run_payloads = [
        {
            "standard_order": run.standard_order,
            "run_order": run.run_order,
            "replicate_index": run.replicate_index,
            "factor_levels": _json_factor_level_dict(run.factor_levels_json),
            "level_indices": _json_int_dict(run.coded_levels_json),
        }
        for run in runs
    ]
    canonical_runs = tuple(
        GeneralFactorialRun(
            standard_order=run.standard_order,
            run_order=run.run_order,
            replicate_index=run.replicate_index,
            factor_levels=_json_factor_level_dict(run.factor_levels_json),
            level_indices=_json_int_dict(run.coded_levels_json),
        )
        for run in runs
    )
    payload = canonical_general_factorial_payload(
        factors=factors, options=options, runs=canonical_runs
    )
    actual = hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()
    if actual != version.design_sha256:
        raise _metadata_error("doe_general_factorial_design_checksum_mismatch")
    return GeneralFactorialDesignResponse(
        design_schema_version=1,
        design_id=UUID(design.design_id),
        design_version_id=UUID(version.design_version_id),
        version_number=1,
        method_id=DOE_GENERAL_FACTORIAL_METHOD_ID,
        method_version=DOE_GENERAL_FACTORIAL_METHOD_VERSION,
        family="general_full_factorial",
        name=design.name,
        status=design.status,
        created_at=design.created_at,
        updated_at=design.updated_at,
        app_version=design.app_version,
        factors=[GeneralFactorialFactorResponse.model_validate(item) for item in factors_payload],
        options=GeneralFactorialOptionsResponse.model_validate(options_payload),
        run_count=version.run_count,
        design_sha256=version.design_sha256,
        runs=[GeneralFactorialRunResponse.model_validate(item) for item in run_payloads],
    )


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_dict(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise _metadata_error("doe_general_factorial_metadata_invalid") from exc
    if not isinstance(payload, dict):
        raise _metadata_error("doe_general_factorial_metadata_invalid")
    return payload


def _json_int_dict(value: str) -> dict[str, int]:
    payload = _json_dict(value)
    if not all(isinstance(key, str) and isinstance(item, int) for key, item in payload.items()):
        raise _metadata_error("doe_general_factorial_metadata_invalid")
    return payload


def _json_factor_level_dict(value: str) -> dict[str, float | str]:
    payload = _json_dict(value)
    result: dict[str, float | str] = {}
    for key, item in payload.items():
        if not isinstance(key, str) or isinstance(item, bool):
            raise _metadata_error("doe_general_factorial_metadata_invalid")
        if isinstance(item, int | float):
            result[key] = float(item)
        elif isinstance(item, str):
            result[key] = item
        else:
            raise _metadata_error("doe_general_factorial_metadata_invalid")
    return result


def _json_list(value: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise _metadata_error("doe_general_factorial_metadata_invalid") from exc
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise _metadata_error("doe_general_factorial_metadata_invalid")
    return payload


def _metadata_error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="Stored general factorial metadata could not be verified.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
