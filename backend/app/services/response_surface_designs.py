import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS, get_analysis_method
from app.api.v1.schemas.doe import (
    DoeDesignResponseSeries,
    DoeDesignResponsesResponse,
    DoeDesignResponsesUpsertRequest,
    DoeDesignResponseValue,
    DoeFactorResponse,
    DoeResponseRevisionCreateRequest,
    ResponseSurfaceDesignCreateRequest,
    ResponseSurfaceDesignOptionsResponse,
    ResponseSurfaceDesignResponse,
    ResponseSurfaceDesignRunResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.doe_response_revisions import create_response_revision
from app.statistics.response_surface import (
    RESPONSE_SURFACE_DESIGN_SCHEMA_VERSION,
    RESPONSE_SURFACE_FAMILY,
    RESPONSE_SURFACE_LEGACY_DESIGN_SCHEMA_VERSION,
    RESPONSE_SURFACE_LEGACY_FAMILY,
    ResponseSurfaceDesignOptions,
    ResponseSurfaceDesignRun,
    ResponseSurfaceError,
    ResponseSurfaceFactor,
    canonical_response_surface_design_payload,
    generate_central_composite_design,
    response_surface_factor_payload,
    response_surface_options_payload,
)
from app.storage.metadata import (
    ExperimentDesignRecord,
    ExperimentDesignVersionRecord,
    ExperimentResponseRevisionRecord,
    ExperimentRunRecord,
    ExperimentRunResponseRecord,
    get_current_experiment_response_revision_record,
    get_experiment_design_record,
    get_experiment_design_version_record,
    insert_experiment_design_records,
    list_experiment_run_records,
    list_experiment_run_response_records,
)

APP_VERSION = "0.1.0"
DOE_RESPONSE_SURFACE_METHOD_ID = "doe.response_surface"


def create_response_surface_design(
    settings: Settings,
    body: ResponseSurfaceDesignCreateRequest,
) -> ResponseSurfaceDesignResponse:
    method = get_analysis_method(DOE_RESPONSE_SURFACE_METHOD_ID)
    method_version = METHOD_VERSIONS[DOE_RESPONSE_SURFACE_METHOD_ID]
    if method is None or method.method_version != method_version:
        raise _metadata_error("doe_rsm_method_registry_mismatch")
    factors = [
        ResponseSurfaceFactor(
            name=factor.name.strip(),
            low=float(factor.low),
            high=float(factor.high),
            unit=None if factor.unit is None else factor.unit.strip() or None,
        )
        for factor in body.factors
    ]
    options = ResponseSurfaceDesignOptions(
        alpha_mode=body.alpha_mode,
        factorial_replicates=body.factorial_replicates,
        axial_replicates=body.axial_replicates,
        center_points=body.center_points,
        randomize=body.randomize,
        randomization_seed=body.randomization_seed,
    )
    try:
        generated = generate_central_composite_design(factors, options)
    except ResponseSurfaceError as exc:
        raise _response_surface_api_error(exc.code) from exc

    design_id = uuid4()
    design_version_id = uuid4()
    created_at = _utc_now()
    design_record = ExperimentDesignRecord(
        design_id=str(design_id),
        method_id=DOE_RESPONSE_SURFACE_METHOD_ID,
        method_version=method_version,
        family=RESPONSE_SURFACE_FAMILY,
        name=body.name.strip(),
        status="designed",
        current_version=1,
        created_at=created_at,
        updated_at=created_at,
        app_version=APP_VERSION,
    )
    options_payload = response_surface_options_payload(generated.options)
    options_payload["design_schema_version"] = generated.schema_version
    options_payload["alpha"] = generated.alpha
    version_record = ExperimentDesignVersionRecord(
        design_version_id=str(design_version_id),
        design_id=str(design_id),
        version_number=1,
        factors_json=_json_dumps(
            [response_surface_factor_payload(factor) for factor in generated.factors]
        ),
        options_json=_json_dumps(options_payload),
        run_count=len(generated.runs),
        design_sha256=generated.design_sha256,
        created_at=created_at,
    )
    run_records = [
        ExperimentRunRecord(
            run_id=str(uuid4()),
            design_version_id=str(design_version_id),
            standard_order=run.standard_order,
            run_order=run.run_order,
            replicate_index=run.replicate_index,
            center_point=run.center_point,
            block_index=None,
            factor_levels_json=_json_dumps(run.factor_levels),
            coded_levels_json=_json_dumps(run.coded_levels),
        )
        for run in generated.runs
    ]
    insert_experiment_design_records(
        settings.workspace_root,
        design=design_record,
        version=version_record,
        runs=run_records,
    )
    return _design_response(design_record, version_record, run_records)


def get_response_surface_design(
    settings: Settings,
    design_id: UUID,
) -> ResponseSurfaceDesignResponse:
    design, version, runs = load_response_surface_design_records(settings, design_id)
    return _design_response(design, version, runs)


def save_response_surface_responses(
    settings: Settings,
    design_id: UUID,
    body: DoeDesignResponsesUpsertRequest,
) -> DoeDesignResponsesResponse:
    design, _version, _runs = load_response_surface_design_records(settings, design_id)
    if design.status == "analyzed":
        raise _metadata_error("doe_rsm_design_already_analyzed")
    create_response_revision(
        settings,
        design_id,
        DoeResponseRevisionCreateRequest(**body.model_dump()),
        allow_analyzed=False,
        require_explicit_supersedes=False,
        duplicate_run_error_code="doe_rsm_response_run_order_duplicate",
        run_set_error_code="doe_rsm_response_run_set_mismatch",
    )
    return list_response_surface_responses(settings, design_id)


def list_response_surface_responses(
    settings: Settings,
    design_id: UUID,
) -> DoeDesignResponsesResponse:
    design, version, runs = load_response_surface_design_records(settings, design_id)
    _design_response(design, version, runs)
    records = list_experiment_run_response_records(
        settings.workspace_root, version.design_version_id
    )
    revisions = {
        name: get_current_experiment_response_revision_record(
            settings.workspace_root, version.design_version_id, name
        )
        for name in {record.response_name for record in records}
    }
    return _responses_response(design, version, runs, records, revisions)


def load_response_surface_design_records(
    settings: Settings,
    design_id: UUID,
) -> tuple[ExperimentDesignRecord, ExperimentDesignVersionRecord, list[ExperimentRunRecord]]:
    design = get_experiment_design_record(settings.workspace_root, str(design_id))
    if design is None:
        raise ApiError(
            code="doe_rsm_design_not_found",
            message="요청한 반응표면 설계를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if design.method_id != DOE_RESPONSE_SURFACE_METHOD_ID or design.family not in {
        RESPONSE_SURFACE_FAMILY,
        RESPONSE_SURFACE_LEGACY_FAMILY,
    }:
        raise _metadata_error("doe_rsm_design_family_mismatch")
    version = get_experiment_design_version_record(
        settings.workspace_root,
        design_id=str(design_id),
        version_number=design.current_version,
    )
    if version is None:
        raise _metadata_error("doe_rsm_design_version_missing")
    runs = list_experiment_run_records(settings.workspace_root, version.design_version_id)
    if len(runs) != version.run_count:
        raise _metadata_error("doe_rsm_design_run_metadata_incomplete")
    return design, version, runs


def response_surface_point_type(
    coded_levels: dict[str, float], alpha: float
) -> Literal["factorial", "axial", "center"]:
    values = list(coded_levels.values())
    tolerance = 1e-10
    if all(abs(value) <= tolerance for value in values):
        return "center"
    nonzero = [value for value in values if abs(value) > tolerance]
    if len(nonzero) == 1 and abs(abs(nonzero[0]) - alpha) <= tolerance:
        return "axial"
    if len(nonzero) == len(values) and all(abs(abs(value) - 1.0) <= tolerance for value in values):
        return "factorial"
    raise _metadata_error("doe_rsm_coded_levels_invalid")


def _design_response(
    design: ExperimentDesignRecord,
    version: ExperimentDesignVersionRecord,
    runs: list[ExperimentRunRecord],
) -> ResponseSurfaceDesignResponse:
    factors_payload = _json_list(version.factors_json)
    options_payload = _json_dict(version.options_json)
    try:
        stored_schema_version = int(
            options_payload.get(
                "design_schema_version",
                RESPONSE_SURFACE_LEGACY_DESIGN_SCHEMA_VERSION,
            )
        )
        design_schema_version: Literal[1, 2]
        family: Literal["central_composite", "central_composite_inscribed"]
        if stored_schema_version == RESPONSE_SURFACE_LEGACY_DESIGN_SCHEMA_VERSION:
            design_schema_version = RESPONSE_SURFACE_LEGACY_DESIGN_SCHEMA_VERSION
            family = RESPONSE_SURFACE_LEGACY_FAMILY
        elif stored_schema_version == RESPONSE_SURFACE_DESIGN_SCHEMA_VERSION:
            design_schema_version = RESPONSE_SURFACE_DESIGN_SCHEMA_VERSION
            family = RESPONSE_SURFACE_FAMILY
        else:
            raise _metadata_error("doe_rsm_design_family_mismatch")
        if design.family != family:
            raise _metadata_error("doe_rsm_design_family_mismatch")
        alpha = float(options_payload["alpha"])
        options = ResponseSurfaceDesignOptions(
            alpha_mode=str(options_payload["alpha_mode"]),  # type: ignore[arg-type]
            factorial_replicates=int(options_payload["factorial_replicates"]),
            axial_replicates=int(options_payload["axial_replicates"]),
            center_points=int(options_payload["center_points"]),
            randomize=bool(options_payload["randomize"]),
            randomization_seed=int(options_payload["randomization_seed"]),
        )
        factors = [ResponseSurfaceFactor(**factor) for factor in factors_payload]
        run_specs: list[ResponseSurfaceDesignRun] = []
        run_responses: list[ResponseSurfaceDesignRunResponse] = []
        for run in runs:
            factor_levels = _numeric_json_dict(run.factor_levels_json)
            coded_levels = _numeric_json_dict(run.coded_levels_json)
            point_type = response_surface_point_type(coded_levels, alpha)
            spec = ResponseSurfaceDesignRun(
                standard_order=run.standard_order,
                run_order=run.run_order,
                replicate_index=run.replicate_index,
                point_type=point_type,
                center_point=run.center_point,
                factor_levels=factor_levels,
                coded_levels=coded_levels,
            )
            if run.center_point != (point_type == "center") or run.block_index is not None:
                raise _metadata_error("doe_rsm_design_run_metadata_invalid")
            run_specs.append(spec)
            run_responses.append(
                ResponseSurfaceDesignRunResponse.model_validate(
                    {
                        "standard_order": run.standard_order,
                        "run_order": run.run_order,
                        "replicate_index": run.replicate_index,
                        "point_type": point_type,
                        "center_point": run.center_point,
                        "factor_levels": factor_levels,
                        "coded_levels": coded_levels,
                    }
                )
            )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        if isinstance(exc, ApiError):
            raise
        raise _metadata_error("doe_rsm_design_metadata_invalid") from exc
    canonical = canonical_response_surface_design_payload(
        schema_version=design_schema_version,
        family=family,
        alpha=alpha,
        factors=factors,
        options=options,
        runs=run_specs,
    )
    actual_sha = hashlib.sha256(_json_dumps(canonical).encode("utf-8")).hexdigest()
    if actual_sha != version.design_sha256:
        raise _metadata_error("doe_rsm_design_checksum_mismatch")
    return ResponseSurfaceDesignResponse(
        design_id=UUID(design.design_id),
        design_version_id=UUID(version.design_version_id),
        version_number=version.version_number,
        method_id="doe.response_surface",
        method_version=design.method_version,
        design_schema_version=design_schema_version,
        family=family,
        name=design.name,
        status=design.status,
        created_at=design.created_at,
        updated_at=design.updated_at,
        app_version=design.app_version,
        factors=[DoeFactorResponse.model_validate(factor) for factor in factors_payload],
        options=ResponseSurfaceDesignOptionsResponse(
            **response_surface_options_payload(options), alpha=alpha
        ),
        run_count=version.run_count,
        design_sha256=version.design_sha256,
        runs=run_responses,
    )


def _responses_response(
    design: ExperimentDesignRecord,
    version: ExperimentDesignVersionRecord,
    runs: list[ExperimentRunRecord],
    records: list[ExperimentRunResponseRecord],
    revisions: dict[str, ExperimentResponseRevisionRecord | None],
) -> DoeDesignResponsesResponse:
    run_order_by_id = {run.run_id: run.run_order for run in runs}
    grouped: dict[str, list[DoeDesignResponseValue]] = {}
    units: dict[str, str | None] = {}
    for record in records:
        run_order = run_order_by_id.get(record.run_id)
        if run_order is None:
            raise _metadata_error("doe_rsm_response_metadata_invalid")
        grouped.setdefault(record.response_name, []).append(
            DoeDesignResponseValue(run_order=run_order, value=record.response_value)
        )
        units.setdefault(record.response_name, record.unit)
    responses = []
    for name, values in sorted(grouped.items()):
        revision = revisions.get(name)
        if (
            revision is None
            or revision.schema_version != 1
            or revision.state != "completed"
            or revision.value_count != len(values)
        ):
            raise _metadata_error("doe_response_revision_dependency_mismatch")
        responses.append(
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
                values=sorted(values, key=lambda value: value.run_order),
            )
        )
    return DoeDesignResponsesResponse(
        design_id=UUID(design.design_id),
        design_version_id=UUID(version.design_version_id),
        version_number=version.version_number,
        status=design.status,
        responses=responses,
    )


def _numeric_json_dict(payload: str) -> dict[str, float]:
    parsed = _json_dict(payload)
    if not all(
        isinstance(key, str) and isinstance(value, int | float) and not isinstance(value, bool)
        for key, value in parsed.items()
    ):
        raise _metadata_error("doe_rsm_design_metadata_invalid")
    return {key: float(value) for key, value in parsed.items()}


def _json_dict(payload: str) -> dict[str, Any]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise _metadata_error("doe_rsm_design_metadata_invalid") from exc
    if not isinstance(parsed, dict):
        raise _metadata_error("doe_rsm_design_metadata_invalid")
    return parsed


def _json_list(payload: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise _metadata_error("doe_rsm_design_metadata_invalid") from exc
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise _metadata_error("doe_rsm_design_metadata_invalid")
    return parsed


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _response_surface_api_error(code: str) -> ApiError:
    messages = {
        "doe_rsm_factor_count_out_of_range": "반응표면 설계는 2~5개 요인을 지원합니다.",
        "doe_rsm_factor_name_required": "반응표면 요인 이름이 필요합니다.",
        "doe_rsm_factor_names_not_unique": "반응표면 요인 이름은 중복될 수 없습니다.",
        "doe_rsm_factor_range_invalid": "각 요인의 low/high는 유한하며 low < high여야 합니다.",
        "doe_rsm_alpha_mode_invalid": "지원하지 않는 CCD alpha 정책입니다.",
        "doe_rsm_replicates_invalid": "factorial 및 axial 반복 수는 1 이상이어야 합니다.",
        "doe_rsm_center_points_invalid": "center point는 1개 이상이어야 합니다.",
        "doe_rsm_seed_invalid": "randomization seed는 0 이상의 정수여야 합니다.",
        "doe_rsm_run_count_exceeds_limit": "생성될 반응표면 run 수가 현재 제한을 초과합니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "반응표면 설계를 생성할 수 없습니다."),
        status_code=status.HTTP_409_CONFLICT,
    )


def _metadata_error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="저장된 반응표면 설계 또는 의존성 metadata가 올바르지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
