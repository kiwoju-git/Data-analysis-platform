import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import status

from app.analyses.registry import METHOD_VERSION, get_analysis_method
from app.api.v1.schemas.doe import (
    DoeDesignResponseSeries,
    DoeDesignResponsesResponse,
    DoeDesignResponsesUpsertRequest,
    DoeDesignResponseValue,
    DoeFactorResponse,
    FactorialDesignCreateRequest,
    FactorialDesignOptionsResponse,
    FactorialDesignResponse,
    FactorialDesignRunResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.statistics.factorial_design import (
    FACTORIAL_DESIGN_FAMILY,
    FactorialDesignError,
    FactorialDesignOptions,
    FactorialDesignRun,
    FactorialFactor,
    canonical_factorial_design_payload,
    factor_to_payload,
    generate_two_level_full_factorial_design,
    options_to_payload,
)
from app.storage.metadata import (
    ExperimentDesignRecord,
    ExperimentDesignVersionRecord,
    ExperimentRunRecord,
    ExperimentRunResponseRecord,
    get_experiment_design_record,
    get_experiment_design_version_record,
    insert_experiment_design_records,
    list_experiment_run_records,
    list_experiment_run_response_records,
    replace_experiment_run_response_records,
)

APP_VERSION = "0.1.0"
DOE_FACTORIAL_METHOD_ID = "doe.factorial_design"


def create_factorial_design(
    settings: Settings,
    body: FactorialDesignCreateRequest,
) -> FactorialDesignResponse:
    method = get_analysis_method(DOE_FACTORIAL_METHOD_ID)
    if method is None or method.method_version != METHOD_VERSION:
        raise ApiError(
            code="doe_factorial_method_registry_mismatch",
            message="DOE factorial method registry 상태가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    factors = [
        FactorialFactor(
            name=factor.name.strip(),
            low=float(factor.low),
            high=float(factor.high),
            unit=None if factor.unit is None else factor.unit.strip() or None,
        )
        for factor in body.factors
    ]
    options = FactorialDesignOptions(
        replicates=body.replicates,
        center_points=body.center_points,
        randomize=body.randomize,
        randomization_seed=body.randomization_seed,
        block_count=body.block_count,
    )
    try:
        generated = generate_two_level_full_factorial_design(factors, options)
    except FactorialDesignError as exc:
        raise _doe_factorial_api_error(exc) from exc

    design_id = uuid4()
    design_version_id = uuid4()
    created_at = _utc_now()
    design_record = ExperimentDesignRecord(
        design_id=str(design_id),
        method_id=DOE_FACTORIAL_METHOD_ID,
        method_version=METHOD_VERSION,
        family=FACTORIAL_DESIGN_FAMILY,
        name=body.name.strip(),
        status="designed",
        current_version=1,
        created_at=created_at,
        updated_at=created_at,
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
            block_index=run.block_index,
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
    return _factorial_design_response(design_record, version_record, run_records)


def get_factorial_design(
    settings: Settings,
    design_id: UUID,
) -> FactorialDesignResponse:
    design, version, runs = _load_factorial_design_records(settings, design_id)
    return _factorial_design_response(design, version, runs)


def save_factorial_design_responses(
    settings: Settings,
    design_id: UUID,
    body: DoeDesignResponsesUpsertRequest,
) -> DoeDesignResponsesResponse:
    design, version, runs = _load_factorial_design_records(settings, design_id)
    _factorial_design_response(design, version, runs)
    if design.status == "analyzed":
        raise ApiError(
            code="doe_design_already_analyzed",
            message="이미 분석된 DOE 설계의 반응값은 이 API에서 수정할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    response_name = body.response_name.strip()
    if not response_name:
        raise ApiError(
            code="doe_response_name_required",
            message="반응 이름을 입력해야 합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    unit = None if body.unit is None else body.unit.strip() or None
    run_by_order = {run.run_order: run for run in runs}
    submitted: dict[int, float] = {}
    for value in body.values:
        if value.run_order in submitted:
            raise ApiError(
                code="doe_response_run_order_duplicate",
                message="같은 run_order에 반응값이 두 번 제출되었습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )
        submitted[value.run_order] = float(value.value)
    if set(submitted) != set(run_by_order):
        raise ApiError(
            code="doe_response_run_set_mismatch",
            message="반응값은 현재 DOE 설계의 모든 run_order와 정확히 일치해야 합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    now = _utc_now()
    records = [
        ExperimentRunResponseRecord(
            response_id=str(uuid4()),
            design_version_id=version.design_version_id,
            run_id=run_by_order[run_order].run_id,
            response_name=response_name,
            response_value=value,
            unit=unit,
            created_at=now,
            updated_at=now,
        )
        for run_order, value in sorted(submitted.items())
    ]
    replace_experiment_run_response_records(
        settings.workspace_root,
        design_id=design.design_id,
        design_version_id=version.design_version_id,
        response_name=response_name,
        records=records,
        design_status="completed",
        updated_at=now,
    )
    return list_factorial_design_responses(settings, design_id)


def list_factorial_design_responses(
    settings: Settings,
    design_id: UUID,
) -> DoeDesignResponsesResponse:
    design, version, runs = _load_factorial_design_records(settings, design_id)
    _factorial_design_response(design, version, runs)
    records = list_experiment_run_response_records(
        settings.workspace_root, version.design_version_id
    )
    return _factorial_design_responses_response(design, version, runs, records)


def _load_factorial_design_records(
    settings: Settings,
    design_id: UUID,
) -> tuple[ExperimentDesignRecord, ExperimentDesignVersionRecord, list[ExperimentRunRecord]]:
    design = get_experiment_design_record(settings.workspace_root, str(design_id))
    if design is None:
        raise ApiError(
            code="doe_design_not_found",
            message="요청한 DOE 설계를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if design.method_id != DOE_FACTORIAL_METHOD_ID:
        raise ApiError(
            code="doe_design_family_unsupported",
            message="현재 API는 2-level factorial DOE 설계만 조회합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    version = get_experiment_design_version_record(
        settings.workspace_root,
        design_id=str(design_id),
        version_number=design.current_version,
    )
    if version is None:
        raise ApiError(
            code="doe_design_version_missing",
            message="DOE 설계 version metadata를 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    runs = list_experiment_run_records(settings.workspace_root, version.design_version_id)
    if len(runs) != version.run_count:
        raise ApiError(
            code="doe_design_run_metadata_incomplete",
            message="DOE 설계 run metadata가 불완전합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return design, version, runs


def _factorial_design_response(
    design: ExperimentDesignRecord,
    version: ExperimentDesignVersionRecord,
    runs: list[ExperimentRunRecord],
) -> FactorialDesignResponse:
    factors = _json_list(version.factors_json, "doe_design_metadata_invalid")
    options = _json_dict(version.options_json, "doe_design_metadata_invalid")
    run_payloads: list[dict[str, Any]] = [
        {
            "standard_order": run.standard_order,
            "run_order": run.run_order,
            "replicate_index": run.replicate_index,
            "center_point": run.center_point,
            "block_index": run.block_index,
            "factor_levels": _json_dict(run.factor_levels_json, "doe_design_metadata_invalid"),
            "coded_levels": _json_dict(run.coded_levels_json, "doe_design_metadata_invalid"),
        }
        for run in runs
    ]
    _verify_design_sha256(
        expected_sha256=version.design_sha256,
        family=design.family,
        factors=factors,
        options=options,
        runs=run_payloads,
    )
    return FactorialDesignResponse(
        design_id=UUID(design.design_id),
        design_version_id=UUID(version.design_version_id),
        version_number=version.version_number,
        method_id=design.method_id,
        method_version=design.method_version,
        family=design.family,
        name=design.name,
        status=design.status,
        created_at=design.created_at,
        updated_at=design.updated_at,
        app_version=design.app_version,
        factors=[DoeFactorResponse.model_validate(factor) for factor in factors],
        options=FactorialDesignOptionsResponse.model_validate(options),
        run_count=version.run_count,
        design_sha256=version.design_sha256,
        runs=[FactorialDesignRunResponse.model_validate(run) for run in run_payloads],
    )


def _factorial_design_responses_response(
    design: ExperimentDesignRecord,
    version: ExperimentDesignVersionRecord,
    runs: list[ExperimentRunRecord],
    records: list[ExperimentRunResponseRecord],
) -> DoeDesignResponsesResponse:
    run_order_by_id = {run.run_id: run.run_order for run in runs}
    grouped: dict[str, list[DoeDesignResponseValue]] = {}
    units: dict[str, str | None] = {}
    for record in records:
        run_order = run_order_by_id.get(record.run_id)
        if run_order is None:
            raise ApiError(
                code="doe_response_metadata_invalid",
                message="저장된 DOE 반응 metadata가 현재 설계 run과 일치하지 않습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )
        grouped.setdefault(record.response_name, []).append(
            DoeDesignResponseValue(run_order=run_order, value=record.response_value),
        )
        units.setdefault(record.response_name, record.unit)

    responses = [
        DoeDesignResponseSeries(
            response_name=response_name,
            unit=units[response_name],
            response_count=len(values),
            values=sorted(values, key=lambda value: value.run_order),
        )
        for response_name, values in sorted(grouped.items())
    ]
    return DoeDesignResponsesResponse(
        design_id=UUID(design.design_id),
        design_version_id=UUID(version.design_version_id),
        version_number=version.version_number,
        status=design.status,
        responses=responses,
    )


def _verify_design_sha256(
    *,
    expected_sha256: str,
    family: str,
    factors: list[object],
    options: dict[str, Any],
    runs: list[dict[str, Any]],
) -> None:
    try:
        factor_specs: list[FactorialFactor] = []
        for factor in factors:
            if not isinstance(factor, dict):
                raise TypeError("DOE factor metadata must be a JSON object")
            factor_specs.append(
                FactorialFactor(
                    name=str(factor["name"]),
                    low=float(factor["low"]),
                    high=float(factor["high"]),
                    unit=None if factor.get("unit") is None else str(factor["unit"]),
                ),
            )
        option_spec = FactorialDesignOptions(
            replicates=int(options["replicates"]),
            center_points=int(options["center_points"]),
            randomize=bool(options["randomize"]),
            randomization_seed=int(options["randomization_seed"]),
            block_count=int(options["block_count"]),
        )
        run_specs = [FactorialDesignRunResponse.model_validate(run) for run in runs]
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(
            code="doe_design_metadata_invalid",
            message="저장된 DOE 설계 metadata 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc

    canonical_runs = tuple(
        _run_response_to_factorial_run(run)
        for run in sorted(run_specs, key=lambda run: run.run_order)
    )
    payload = canonical_factorial_design_payload(
        family=family,
        factors=factor_specs,
        options=option_spec,
        runs=canonical_runs,
    )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8",
    )
    if hashlib.sha256(encoded).hexdigest() != expected_sha256:
        raise ApiError(
            code="doe_design_checksum_mismatch",
            message="저장된 DOE 설계 metadata가 checksum과 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )


def _run_response_to_factorial_run(run: FactorialDesignRunResponse) -> FactorialDesignRun:
    return FactorialDesignRun(
        standard_order=run.standard_order,
        run_order=run.run_order,
        replicate_index=run.replicate_index,
        center_point=run.center_point,
        block_index=run.block_index,
        factor_levels=run.factor_levels,
        coded_levels=run.coded_levels,
    )


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_dict(payload: str, error_code: str) -> dict[str, Any]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ApiError(
            code=error_code,
            message="저장된 DOE 설계 metadata 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    if not isinstance(parsed, dict):
        raise ApiError(
            code=error_code,
            message="저장된 DOE 설계 metadata 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return parsed


def _json_list(payload: str, error_code: str) -> list[Any]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ApiError(
            code=error_code,
            message="저장된 DOE 설계 metadata 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    if not isinstance(parsed, list):
        raise ApiError(
            code=error_code,
            message="저장된 DOE 설계 metadata 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return parsed


def _doe_factorial_api_error(exc: FactorialDesignError) -> ApiError:
    return ApiError(
        code=exc.code,
        message=str(exc),
        status_code=status.HTTP_409_CONFLICT,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
