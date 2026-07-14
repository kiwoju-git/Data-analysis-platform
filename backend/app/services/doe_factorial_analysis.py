from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.doe import (
    DoeFactorialAnalysisCreateRequest,
    DoeFactorialAnalysisResponse,
    DoeFactorialAnalysisResult,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    APP_VERSION,
    canonical_json_bytes,
    runtime_build_provenance,
    utc_now,
)
from app.services.doe_designs import DOE_FACTORIAL_METHOD_ID, get_factorial_design
from app.statistics.factorial_analysis import (
    FactorialAnalysisError,
    FactorialAnalysisRun,
    calculate_factorial_analysis,
)
from app.storage.metadata import (
    ExperimentDesignAnalysisRecord,
    ExperimentRunRecord,
    ExperimentRunResponseRecord,
    get_experiment_design_analysis_record,
    get_latest_experiment_design_analysis_record,
    insert_experiment_design_analysis_record,
    list_experiment_run_records,
    list_experiment_run_response_records,
)

DOE_FACTORIAL_ANALYSIS_SCHEMA_VERSION = 1
DOE_FACTORIAL_ANALYSIS_CONFIG_SCHEMA_VERSION = 1


def create_factorial_analysis(
    settings: Settings,
    design_id: UUID,
    body: DoeFactorialAnalysisCreateRequest,
) -> DoeFactorialAnalysisResponse:
    design = get_factorial_design(settings, design_id)
    response_name = body.response_name.strip()
    runs, response_records = _analysis_dependency_records(
        settings,
        design.design_version_id,
        response_name,
    )
    unit = _response_unit(response_records)
    response_sha256 = _response_sha256(
        design_version_id=design.design_version_id,
        response_name=response_name,
        unit=unit,
        runs=runs,
        response_records=response_records,
    )
    response_by_run_id = {record.run_id: record for record in response_records}
    calculation_runs = [
        FactorialAnalysisRun(
            run_order=run.run_order,
            standard_order=run.standard_order,
            center_point=run.center_point,
            block_index=run.block_index,
            coded_levels=_coded_levels(run),
            response=response_by_run_id[run.run_id].response_value,
        )
        for run in runs
    ]
    try:
        result_payload = calculate_factorial_analysis(
            calculation_runs,
            [factor.name for factor in design.factors],
            response_name=response_name,
            response_unit=unit,
            max_interaction_order=body.max_interaction_order,
            confidence_level=float(body.confidence_level),
            point_limit=body.point_limit,
        )
        result = DoeFactorialAnalysisResult.model_validate(result_payload)
    except FactorialAnalysisError as exc:
        raise _factorial_analysis_api_error(exc.code) from exc
    except ValidationError as exc:
        raise ApiError(
            code="doe_factorial_analysis_result_invalid",
            message="DOE factorial 분석 결과 계약을 검증할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc

    analysis_id = uuid4()
    created_at = utc_now()
    method_version = METHOD_VERSIONS[DOE_FACTORIAL_METHOD_ID]
    response = DoeFactorialAnalysisResponse(
        analysis_id=analysis_id,
        design_id=design.design_id,
        design_version_id=design.design_version_id,
        design_version_number=design.version_number,
        method_id=DOE_FACTORIAL_METHOD_ID,
        method_version=method_version,
        analysis_schema_version=DOE_FACTORIAL_ANALYSIS_SCHEMA_VERSION,
        design_sha256=design.design_sha256,
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
            "schema_version": DOE_FACTORIAL_ANALYSIS_CONFIG_SCHEMA_VERSION,
            "design_id": str(design.design_id),
            "design_version_id": str(design.design_version_id),
            "design_sha256": design.design_sha256,
            "response_sha256": response_sha256,
            **body.model_dump(mode="json"),
            "response_name": response_name,
        }
    )
    record = ExperimentDesignAnalysisRecord(
        analysis_id=str(analysis_id),
        design_version_id=str(design.design_version_id),
        response_name=response_name,
        method_id=DOE_FACTORIAL_METHOD_ID,
        method_version=method_version,
        config_json=config_json,
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
        response_sha256=response_sha256,
        created_at=created_at,
        app_version=APP_VERSION,
    )
    insert_experiment_design_analysis_record(
        settings.workspace_root,
        design_id=str(design.design_id),
        record=record,
        updated_at=created_at,
    )
    return response


def get_factorial_analysis(
    settings: Settings,
    design_id: UUID,
    analysis_id: UUID,
) -> DoeFactorialAnalysisResponse:
    design = get_factorial_design(settings, design_id)
    record = get_experiment_design_analysis_record(settings.workspace_root, str(analysis_id))
    if record is None or record.design_version_id != str(design.design_version_id):
        raise ApiError(
            code="doe_factorial_analysis_not_found",
            message="요청한 DOE factorial 분석을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _validated_analysis_response(settings, design_id, record)


def get_latest_factorial_analysis(
    settings: Settings,
    design_id: UUID,
) -> DoeFactorialAnalysisResponse | None:
    design = get_factorial_design(settings, design_id)
    record = get_latest_experiment_design_analysis_record(
        settings.workspace_root,
        str(design.design_version_id),
        method_id=DOE_FACTORIAL_METHOD_ID,
    )
    return None if record is None else _validated_analysis_response(settings, design_id, record)


def _validated_analysis_response(
    settings: Settings,
    design_id: UUID,
    record: ExperimentDesignAnalysisRecord,
) -> DoeFactorialAnalysisResponse:
    design = get_factorial_design(settings, design_id)
    if (
        record.method_id != DOE_FACTORIAL_METHOD_ID
        or record.method_version != METHOD_VERSIONS[DOE_FACTORIAL_METHOD_ID]
    ):
        raise _metadata_error("doe_factorial_analysis_method_mismatch")
    actual_result_sha256 = hashlib.sha256(record.result_json.encode("utf-8")).hexdigest()
    if actual_result_sha256 != record.result_sha256:
        raise _metadata_error("doe_factorial_analysis_checksum_mismatch")
    try:
        config = json.loads(record.config_json)
        response = DoeFactorialAnalysisResponse.model_validate_json(record.result_json)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise _metadata_error("doe_factorial_analysis_metadata_invalid") from exc
    if not isinstance(config, dict):
        raise _metadata_error("doe_factorial_analysis_metadata_invalid")
    expected_config = {
        "schema_version": DOE_FACTORIAL_ANALYSIS_CONFIG_SCHEMA_VERSION,
        "design_id": str(design.design_id),
        "design_version_id": str(design.design_version_id),
        "design_sha256": design.design_sha256,
        "response_sha256": record.response_sha256,
        "response_name": record.response_name,
    }
    if any(config.get(key) != value for key, value in expected_config.items()):
        raise _metadata_error("doe_factorial_analysis_dependency_mismatch")
    if (
        response.analysis_id != UUID(record.analysis_id)
        or response.design_id != design.design_id
        or response.design_version_id != design.design_version_id
        or response.design_sha256 != design.design_sha256
        or response.response_name != record.response_name
        or response.response_sha256 != record.response_sha256
        or response.method_id != record.method_id
        or response.method_version != record.method_version
    ):
        raise _metadata_error("doe_factorial_analysis_dependency_mismatch")
    runs, response_records = _analysis_dependency_records(
        settings,
        design.design_version_id,
        record.response_name,
    )
    current_response_sha256 = _response_sha256(
        design_version_id=design.design_version_id,
        response_name=record.response_name,
        unit=_response_unit(response_records),
        runs=runs,
        response_records=response_records,
    )
    if current_response_sha256 != record.response_sha256:
        raise _metadata_error("doe_factorial_analysis_response_mismatch")
    return response


def _analysis_dependency_records(
    settings: Settings,
    design_version_id: UUID,
    response_name: str,
) -> tuple[list[ExperimentRunRecord], list[ExperimentRunResponseRecord]]:
    runs = list_experiment_run_records(settings.workspace_root, str(design_version_id))
    all_responses = list_experiment_run_response_records(
        settings.workspace_root,
        str(design_version_id),
    )
    responses = [record for record in all_responses if record.response_name == response_name]
    if not responses:
        raise ApiError(
            code="doe_factorial_analysis_response_not_found",
            message="분석할 저장 반응 series를 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    run_ids = {run.run_id for run in runs}
    if len(responses) != len(runs) or {record.run_id for record in responses} != run_ids:
        raise _metadata_error("doe_factorial_analysis_response_incomplete")
    return runs, responses


def _response_unit(records: list[ExperimentRunResponseRecord]) -> str | None:
    units = {record.unit for record in records}
    if len(units) != 1:
        raise _metadata_error("doe_factorial_analysis_response_metadata_invalid")
    return next(iter(units))


def _response_sha256(
    *,
    design_version_id: UUID,
    response_name: str,
    unit: str | None,
    runs: list[ExperimentRunRecord],
    response_records: list[ExperimentRunResponseRecord],
) -> str:
    run_order_by_id = {run.run_id: run.run_order for run in runs}
    payload = {
        "schema_version": 1,
        "design_version_id": str(design_version_id),
        "response_name": response_name,
        "unit": unit,
        "values": [
            {
                "run_order": run_order_by_id[record.run_id],
                "value": record.response_value,
            }
            for record in sorted(
                response_records,
                key=lambda item: run_order_by_id[item.run_id],
            )
        ],
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _coded_levels(run: ExperimentRunRecord) -> dict[str, int]:
    try:
        payload = json.loads(run.coded_levels_json)
    except json.JSONDecodeError as exc:
        raise _metadata_error("doe_factorial_analysis_coded_levels_invalid") from exc
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, int) and not isinstance(value, bool)
        for key, value in payload.items()
    ):
        raise _metadata_error("doe_factorial_analysis_coded_levels_invalid")
    return payload


def _factorial_analysis_api_error(code: str) -> ApiError:
    messages = {
        "doe_factorial_analysis_factors_invalid": (
            "DOE factorial 요인 metadata가 올바르지 않습니다."
        ),
        "doe_factorial_interaction_order_invalid": (
            "상호작용 차수는 요인 수 범위에서 1~3이어야 합니다."
        ),
        "doe_factorial_confidence_level_invalid": "신뢰수준은 0과 1 사이여야 합니다.",
        "doe_factorial_analysis_point_limit_invalid": "DOE 진단 point limit이 올바르지 않습니다.",
        "doe_factorial_analysis_run_count_invalid": "DOE 분석 run 수가 허용 범위를 벗어났습니다.",
        "doe_factorial_analysis_run_order_duplicate": "DOE run_order가 중복되었습니다.",
        "doe_factorial_response_not_finite": "DOE 반응값은 유한한 숫자여야 합니다.",
        "doe_factorial_coded_levels_invalid": "DOE coded factor level이 올바르지 않습니다.",
        "doe_factorial_center_coding_invalid": (
            "DOE center point는 모든 coded level이 0이어야 합니다."
        ),
        "doe_factorial_response_variance_zero": "DOE 반응값 변동이 없어 효과를 추정할 수 없습니다.",
        "doe_factorial_model_rank_deficient": "DOE 모형 행렬이 rank deficient입니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "DOE factorial 분석을 계산할 수 없습니다."),
        status_code=status.HTTP_409_CONFLICT,
    )


def _metadata_error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="저장된 DOE 분석 dependency 또는 checksum이 일치하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
