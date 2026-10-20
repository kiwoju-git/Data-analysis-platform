from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.doe import (
    DoeResponseSurfaceAnalysisCreateRequest,
    DoeResponseSurfaceAnalysisResponse,
    DoeResponseSurfaceAnalysisResult,
)
from app.api.v1.schemas.doe_model_workflow import DoeAnalysisTermCatalog
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    APP_VERSION,
    runtime_build_provenance,
    utc_now,
)
from app.services.doe_response_revisions import load_response_revision_dependency
from app.services.response_surface_designs import (
    DOE_RESPONSE_SURFACE_METHOD_ID,
    get_response_surface_design,
    response_surface_point_type,
)
from app.services.rsm_plot_builder import (
    build_rsm_plot_bundle,
    default_rsm_overview_settings,
    default_rsm_plot_settings,
)
from app.statistics.response_surface import (
    ResponseSurfaceAnalysisRun,
    ResponseSurfaceError,
    ResponseSurfaceFactor,
    calculate_response_surface_analysis,
)
from app.statistics.rsm_coding import RsmFactorCoding, factor_coding, resolve_ccd_type
from app.statistics.rsm_model_basis import RsmTermPreset, rsm_basis_terms
from app.statistics.rsm_model_workflow import rsm_term_catalog
from app.statistics.term_block_model_selection import selection_options_from_payload
from app.storage.metadata import (
    ExperimentDesignAnalysisRecord,
    ExperimentRunRecord,
    ExperimentRunResponseRecord,
    get_experiment_design_analysis_record,
    get_latest_experiment_design_analysis_record,
    insert_experiment_design_analysis_record,
)

DOE_RESPONSE_SURFACE_ANALYSIS_SCHEMA_VERSION = 3
DOE_RESPONSE_SURFACE_CONFIG_SCHEMA_VERSION = 3
# These methods share the immutable revision-based envelope and config contract.
SUPPORTED_RSM_METHOD_SCHEMAS = {
    "0.3.0": (2, 1, 2),
    "0.3.1": (2, 1, 2),
    "0.4.0": (3, 2, 3),
}


def get_response_surface_term_catalog(
    settings: Settings,
    design_id: UUID,
    preset: RsmTermPreset,
) -> DoeAnalysisTermCatalog:
    design = get_response_surface_design(settings, design_id)
    return DoeAnalysisTermCatalog.model_validate(
        {
            "design_id": design_id,
            "max_interaction_order": 2,
            "terms": rsm_term_catalog(
                rsm_basis_terms([factor.name for factor in design.factors], preset)
            ),
            "selection_supported": True,
        }
    )


def create_response_surface_analysis(
    settings: Settings,
    design_id: UUID,
    body: DoeResponseSurfaceAnalysisCreateRequest,
) -> DoeResponseSurfaceAnalysisResponse:
    design = get_response_surface_design(settings, design_id)
    response_name = body.response_name.strip()
    dependency = load_response_revision_dependency(
        settings,
        design_version_id=design.design_version_id,
        response_name=response_name,
        response_revision_id=body.response_revision_id,
    )
    runs = dependency.runs
    response_records = dependency.response_records
    unit = _response_unit(response_records)
    response_sha256 = dependency.revision.response_sha256
    response_by_run_id = {record.run_id: record.response_value for record in response_records}
    alpha = design.options.alpha
    calculation_runs = []
    for run in runs:
        coded_levels = _coded_levels(run)
        calculation_runs.append(
            ResponseSurfaceAnalysisRun(
                run_order=run.run_order,
                standard_order=run.standard_order,
                point_type=response_surface_point_type(coded_levels, alpha),
                coded_levels=coded_levels,
                response=response_by_run_id[run.run_id],
            )
        )
    factors = [
        ResponseSurfaceFactor(
            factor.name,
            factor.low,
            factor.high,
            factor.unit,
            factor.domain_kind,
            factor.step,
            factor.display_decimals,
        )
        for factor in design.factors
    ]
    kind = resolve_ccd_type(design.options.alpha_mode, design.options.ccd_type)
    coding = {
        factor.name: (
            RsmFactorCoding(**design.coding[factor.name].model_dump())
            if design.coding is not None
            else factor_coding(factor.low, factor.high, alpha, kind)
        )
        for factor in factors
    }
    try:
        result_payload = calculate_response_surface_analysis(
            calculation_runs,
            factors,
            alpha=alpha,
            response_name=response_name,
            response_unit=unit,
            confidence_level=float(body.confidence_level),
            point_limit=body.point_limit,
            contour_grid_size=body.contour_grid_size,
            coding_by_name=coding,
            term_preset=body.term_preset,
            model_selection=selection_options_from_payload(
                body.model_selection.model_dump(exclude={"saturated_start_policy"}),
            ),
        )
        result = DoeResponseSurfaceAnalysisResult.model_validate(result_payload)
        if result.final_basis is not None:
            result.plot_bundle = build_rsm_plot_bundle(
                design,
                result.final_basis,
                default_rsm_plot_settings(design),
                response_name=response_name,
                response_unit=unit,
            )
            result.plot_overview = [
                build_rsm_plot_bundle(
                    design,
                    result.final_basis,
                    view,
                    response_name=response_name,
                    response_unit=unit,
                )
                for view in default_rsm_overview_settings(design)
            ]
    except ResponseSurfaceError as exc:
        raise _analysis_api_error(exc.code) from exc
    except ValidationError as exc:
        raise _metadata_error("doe_rsm_analysis_result_invalid") from exc

    analysis_id = uuid4()
    created_at = utc_now()
    method_version = METHOD_VERSIONS[DOE_RESPONSE_SURFACE_METHOD_ID]
    response = DoeResponseSurfaceAnalysisResponse(
        analysis_id=analysis_id,
        design_id=design.design_id,
        design_version_id=design.design_version_id,
        design_version_number=design.version_number,
        method_id="doe.response_surface",
        method_version=method_version,
        analysis_schema_version=DOE_RESPONSE_SURFACE_ANALYSIS_SCHEMA_VERSION,
        design_sha256=design.design_sha256,
        response_revision_id=UUID(dependency.revision.response_revision_id),
        response_revision_number=dependency.revision.revision_number,
        response_revision_sha256=response_sha256,
        response_sha256=response_sha256,
        response_name=response_name,
        created_at=created_at,
        app_version=APP_VERSION,
        result=result,
        **runtime_build_provenance(settings),
    )
    result_json = _json_dumps(response.model_dump(mode="json"))
    config_json = _json_dumps(
        {
            "schema_version": DOE_RESPONSE_SURFACE_CONFIG_SCHEMA_VERSION,
            "design_id": str(design.design_id),
            "design_version_id": str(design.design_version_id),
            "design_sha256": design.design_sha256,
            **body.model_dump(mode="json"),
            "response_revision_id": dependency.revision.response_revision_id,
            "response_revision_number": dependency.revision.revision_number,
            "response_revision_sha256": response_sha256,
            "response_sha256": response_sha256,
            "response_name": response_name,
        }
    )
    record = ExperimentDesignAnalysisRecord(
        analysis_id=str(analysis_id),
        design_version_id=str(design.design_version_id),
        response_name=response_name,
        method_id=DOE_RESPONSE_SURFACE_METHOD_ID,
        method_version=method_version,
        config_json=config_json,
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
        response_sha256=response_sha256,
        created_at=created_at,
        app_version=APP_VERSION,
        response_revision_id=dependency.revision.response_revision_id,
    )
    insert_experiment_design_analysis_record(
        settings.workspace_root,
        design_id=str(design.design_id),
        record=record,
        updated_at=created_at,
    )
    return response


def get_response_surface_analysis(
    settings: Settings,
    design_id: UUID,
    analysis_id: UUID,
) -> DoeResponseSurfaceAnalysisResponse:
    design = get_response_surface_design(settings, design_id)
    record = get_experiment_design_analysis_record(settings.workspace_root, str(analysis_id))
    if record is None or record.design_version_id != str(design.design_version_id):
        raise ApiError(
            code="doe_rsm_analysis_not_found",
            message="요청한 반응표면 분석을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _validated_analysis_response(settings, design_id, record)


def get_latest_response_surface_analysis(
    settings: Settings,
    design_id: UUID,
) -> DoeResponseSurfaceAnalysisResponse | None:
    design = get_response_surface_design(settings, design_id)
    record = get_latest_experiment_design_analysis_record(
        settings.workspace_root,
        str(design.design_version_id),
        method_id=DOE_RESPONSE_SURFACE_METHOD_ID,
    )
    return None if record is None else _validated_analysis_response(settings, design_id, record)


def _validated_analysis_response(
    settings: Settings,
    design_id: UUID,
    record: ExperimentDesignAnalysisRecord,
) -> DoeResponseSurfaceAnalysisResponse:
    design = get_response_surface_design(settings, design_id)
    if (
        record.method_id != DOE_RESPONSE_SURFACE_METHOD_ID
        or record.method_version not in SUPPORTED_RSM_METHOD_SCHEMAS
    ):
        raise _metadata_error("doe_rsm_analysis_method_mismatch")
    actual_result_sha = hashlib.sha256(record.result_json.encode("utf-8")).hexdigest()
    if actual_result_sha != record.result_sha256:
        raise _metadata_error("doe_rsm_analysis_checksum_mismatch")
    try:
        config = json.loads(record.config_json)
        response = DoeResponseSurfaceAnalysisResponse.model_validate_json(record.result_json)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise _metadata_error("doe_rsm_analysis_metadata_invalid") from exc
    if not isinstance(config, dict):
        raise _metadata_error("doe_rsm_analysis_metadata_invalid")
    envelope_schema, result_schema, config_schema = SUPPORTED_RSM_METHOD_SCHEMAS[
        record.method_version
    ]
    if (
        response.analysis_schema_version != envelope_schema
        or response.result.schema_version != result_schema
    ):
        raise _metadata_error("doe_rsm_analysis_metadata_invalid")
    if result_schema >= 2:
        kind = resolve_ccd_type(design.options.alpha_mode, design.options.ccd_type)
        expected_coding = {
            factor.name: factor_coding(
                factor.low,
                factor.high,
                design.options.alpha,
                kind,
            ).payload()
            for factor in design.factors
        }
        actual_coding = response.result.coding.factors
        if (
            actual_coding is None
            or {name: item.model_dump() for name, item in actual_coding.items()} != expected_coding
        ):
            raise _metadata_error("doe_rsm_analysis_coding_mismatch")
        basis = response.result.final_basis
        selection = response.result.model_selection
        if basis is None or selection is None or response.result.term_preset is None:
            raise _metadata_error("doe_rsm_analysis_basis_mismatch")
        terms_by_id = {
            term.term_id: term
            for term in rsm_basis_terms(response.result.factor_names, response.result.term_preset)
        }
        if (
            config.get("term_preset") != response.result.term_preset
            or config.get("model_selection")
            != {
                key: getattr(selection, key)
                for key in (
                    "method",
                    "alpha_to_remove",
                    "hierarchy_policy",
                    "saturated_start_policy",
                    "display_step_details",
                )
            }
            | {"term_policies": [policy.model_dump() for policy in selection.term_policies]}
            or any(
                term_id not in terms_by_id or list(terms_by_id[term_id].powers) != powers
                for term_id, powers in zip(basis.term_ids, basis.powers, strict=True)
            )
        ):
            raise _metadata_error("doe_rsm_analysis_basis_mismatch")
        default_plot = response.result.plot_bundle
        overview = response.result.plot_overview
        expected_views = default_rsm_overview_settings(design)
        if (
            default_plot is None
            or overview is None
            or default_plot.settings != default_rsm_plot_settings(design)
            or [item.settings for item in overview] != expected_views
            or any(
                item.final_term_ids != basis.term_ids
                or item.response_name != response.response_name
                or item.response_unit != response.result.response.unit
                for item in [default_plot, *overview]
            )
        ):
            raise _metadata_error("doe_rsm_analysis_plot_mismatch")
    expected_config = {
        "schema_version": config_schema,
        "design_id": str(design.design_id),
        "design_version_id": str(design.design_version_id),
        "design_sha256": design.design_sha256,
        "response_revision_id": record.response_revision_id,
        "response_revision_number": response.response_revision_number,
        "response_revision_sha256": record.response_sha256,
        "response_sha256": record.response_sha256,
        "response_name": record.response_name,
    }
    if any(config.get(key) != value for key, value in expected_config.items()):
        raise _metadata_error("doe_rsm_analysis_dependency_mismatch")
    if (
        response.analysis_id != UUID(record.analysis_id)
        or response.design_id != design.design_id
        or response.design_version_id != design.design_version_id
        or response.design_sha256 != design.design_sha256
        or str(response.response_revision_id) != record.response_revision_id
        or record.response_revision_sha256 != record.response_sha256
        or response.response_revision_number < 1
        or response.response_revision_sha256 != record.response_sha256
        or response.response_name != record.response_name
        or response.response_sha256 != record.response_sha256
        or response.method_id != record.method_id
        or response.method_version != record.method_version
    ):
        raise _metadata_error("doe_rsm_analysis_dependency_mismatch")
    if record.response_revision_id is None:
        raise _metadata_error("doe_rsm_analysis_dependency_mismatch")
    dependency = load_response_revision_dependency(
        settings,
        design_version_id=design.design_version_id,
        response_name=record.response_name,
        response_revision_id=UUID(record.response_revision_id),
    )
    if (
        dependency.revision.response_sha256 != record.response_sha256
        or dependency.revision.revision_number != response.response_revision_number
    ):
        raise _metadata_error("doe_rsm_analysis_response_mismatch")
    return response


def _response_unit(records: list[ExperimentRunResponseRecord]) -> str | None:
    units = {record.unit for record in records}
    if len(units) != 1:
        raise _metadata_error("doe_rsm_analysis_response_metadata_invalid")
    return next(iter(units))


def _coded_levels(run: ExperimentRunRecord) -> dict[str, float]:
    try:
        payload = json.loads(run.coded_levels_json)
    except json.JSONDecodeError as exc:
        raise _metadata_error("doe_rsm_analysis_coded_levels_invalid") from exc
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, int | float) and not isinstance(value, bool)
        for key, value in payload.items()
    ):
        raise _metadata_error("doe_rsm_analysis_coded_levels_invalid")
    return {key: float(value) for key, value in payload.items()}


def _analysis_api_error(code: str) -> ApiError:
    messages = {
        "doe_rsm_analysis_factors_invalid": "반응표면 요인 metadata가 올바르지 않습니다.",
        "doe_rsm_alpha_invalid": "CCD axial distance가 올바르지 않습니다.",
        "doe_rsm_confidence_level_invalid": "신뢰수준은 0과 1 사이여야 합니다.",
        "doe_rsm_point_limit_invalid": "진단 point limit이 올바르지 않습니다.",
        "doe_rsm_contour_grid_size_invalid": "contour grid는 11~51 범위의 홀수여야 합니다.",
        "doe_rsm_run_count_invalid": "반응표면 run 수가 허용 범위를 벗어났습니다.",
        "doe_rsm_run_order_duplicate": "반응표면 run_order가 중복되었습니다.",
        "doe_rsm_response_not_finite": "반응값은 유한한 숫자여야 합니다.",
        "doe_rsm_point_type_invalid": "CCD point type이 올바르지 않습니다.",
        "doe_rsm_coded_levels_invalid": "CCD coded level이 올바르지 않습니다.",
        "doe_rsm_response_variance_zero": "반응값 변동이 없어 모형을 적합할 수 없습니다.",
        "doe_rsm_model_rank_deficient": (
            "요청한 RSM 모형 행렬의 항을 독립적으로 추정할 수 없습니다."
        ),
        "doe_rsm_selection_requires_residual_df": (
            "RSM backward는 초기 잔차 자유도가 양수여야 합니다. " "항을 줄이거나 실험을 추가하세요."
        ),
        "doe_factorial_selection_hierarchy_invalid": (
            "제곱항과 교호작용에 필요한 주효과를 제외할 수 없습니다."
        ),
        "doe_factorial_term_policy_invalid": "현재 RSM preset에 없는 항 또는 중복된 항 정책입니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "반응표면 모형을 계산할 수 없습니다."),
        status_code=status.HTTP_409_CONFLICT,
    )


def _metadata_error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="저장된 반응표면 분석 dependency 또는 checksum이 일치하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
