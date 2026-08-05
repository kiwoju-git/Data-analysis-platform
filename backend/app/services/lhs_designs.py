import csv
import hashlib
import io
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

import numpy as np
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
    LatinHypercubeDesignCreateRequest,
    LatinHypercubeDesignOptionsResponse,
    LatinHypercubeDesignQualityResponse,
    LatinHypercubeDesignResponse,
    LatinHypercubeRunResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.doe_response_revisions import create_response_revision
from app.statistics.latin_hypercube import (
    LATIN_HYPERCUBE_FAMILY,
    LATIN_HYPERCUBE_POLICY,
    MIXED_LATIN_HYPERCUBE_POLICY,
    LatinHypercubeError,
    LatinHypercubeFactor,
    LatinHypercubeOptions,
    LatinHypercubeRun,
    calculate_latin_hypercube_quality,
    canonical_latin_hypercube_payload,
    generate_latin_hypercube_design,
)
from app.storage.metadata import (
    ExperimentDesignRecord,
    ExperimentDesignVersionRecord,
    ExperimentResponseRevisionRecord,
    ExperimentRunRecord,
    get_current_experiment_response_revision_record,
    get_experiment_design_record,
    get_experiment_design_version_record,
    insert_experiment_design_records,
    list_experiment_run_records,
    list_experiment_run_response_records,
)

LHS_METHOD_ID = "doe.latin_hypercube"
APP_VERSION = "0.1.0"


def create_latin_hypercube_design(
    settings: Settings,
    body: LatinHypercubeDesignCreateRequest,
) -> LatinHypercubeDesignResponse:
    method = get_analysis_method(LHS_METHOD_ID)
    method_version = METHOD_VERSIONS[LHS_METHOD_ID]
    if method is None or method.method_version != method_version:
        raise _error(
            "lhs_method_registry_mismatch",
            "LHS method registry 상태가 올바르지 않습니다.",
            status.HTTP_409_CONFLICT,
        )
    factors = [
        LatinHypercubeFactor(
            name=item.name.strip(),
            low=float(item.low),
            high=float(item.high),
            unit=None if item.unit is None else item.unit.strip() or None,
            domain_kind=item.domain_kind,
            step=None if item.step is None else float(item.step),
            display_decimals=item.display_decimals,
        )
        for item in body.factors
    ]
    options = LatinHypercubeOptions(
        run_count=body.run_count,
        seed=body.seed,
        randomize_run_order=body.randomize_run_order,
        run_order_seed=body.run_order_seed,
        optimization=body.optimization,
    )
    try:
        generated = generate_latin_hypercube_design(factors, options)
    except LatinHypercubeError as exc:
        raise _error(exc.code, _lhs_error_message(exc.code)) from exc

    now = datetime.now(timezone.utc).isoformat()
    design_id = str(uuid4())
    design_version_id = str(uuid4())
    design = ExperimentDesignRecord(
        design_id=design_id,
        method_id=LHS_METHOD_ID,
        method_version=method_version,
        family=LATIN_HYPERCUBE_FAMILY,
        name=body.name.strip(),
        status="designed",
        current_version=1,
        created_at=now,
        updated_at=now,
        app_version=APP_VERSION,
    )
    stored_options = {
        "policy": (
            MIXED_LATIN_HYPERCUBE_POLICY
            if any(item.domain_kind == "discrete_numeric" for item in generated.factors)
            else LATIN_HYPERCUBE_POLICY
        ),
        "run_count": options.run_count,
        "seed": options.seed,
        "scramble": True,
        "strength": 1,
        "optimization": options.optimization,
        "randomize_run_order": options.randomize_run_order,
        "run_order_seed": options.run_order_seed,
        "quality": asdict(generated.quality),
        "numpy_version": generated.numpy_version,
        "scipy_version": generated.scipy_version,
    }
    version = ExperimentDesignVersionRecord(
        design_version_id=design_version_id,
        design_id=design_id,
        version_number=1,
        factors_json=_json([asdict(item) for item in generated.factors]),
        options_json=_json(stored_options),
        run_count=len(generated.runs),
        design_sha256=generated.design_sha256,
        created_at=now,
    )
    runs = [
        ExperimentRunRecord(
            run_id=str(uuid4()),
            design_version_id=design_version_id,
            standard_order=item.standard_order,
            run_order=item.run_order,
            replicate_index=1,
            center_point=False,
            block_index=None,
            factor_levels_json=_json(item.factor_levels),
            coded_levels_json=_json(item.normalized_levels),
        )
        for item in generated.runs
    ]
    insert_experiment_design_records(
        settings.workspace_root,
        design=design,
        version=version,
        runs=runs,
    )
    return _response(design, version, runs)


def get_latin_hypercube_design(
    settings: Settings,
    design_id: UUID,
) -> LatinHypercubeDesignResponse:
    design, version, runs = _load(settings, design_id)
    return _response(design, version, runs)


def save_latin_hypercube_responses(
    settings: Settings,
    design_id: UUID,
    body: DoeDesignResponsesUpsertRequest,
) -> DoeDesignResponsesResponse:
    _load(settings, design_id)
    create_response_revision(
        settings,
        design_id,
        DoeResponseRevisionCreateRequest(**body.model_dump()),
        allow_analyzed=True,
        require_explicit_supersedes=False,
    )
    return list_latin_hypercube_responses(settings, design_id)


def list_latin_hypercube_responses(
    settings: Settings,
    design_id: UUID,
) -> DoeDesignResponsesResponse:
    design, version, runs = _load(settings, design_id)
    records = list_experiment_run_response_records(
        settings.workspace_root,
        version.design_version_id,
    )
    run_order_by_id = {item.run_id: item.run_order for item in runs}
    grouped: dict[str, list[DoeDesignResponseValue]] = {}
    units: dict[str, str | None] = {}
    for item in records:
        run_order = run_order_by_id.get(item.run_id)
        if run_order is None:
            raise _error(
                "lhs_response_metadata_invalid",
                "저장된 LHS 반응 metadata가 설계표와 일치하지 않습니다.",
                status.HTTP_409_CONFLICT,
            )
        grouped.setdefault(item.response_name, []).append(
            DoeDesignResponseValue(run_order=run_order, value=item.response_value)
        )
        units.setdefault(item.response_name, item.unit)
    responses: list[DoeDesignResponseSeries] = []
    for name, values in sorted(grouped.items()):
        revision = get_current_experiment_response_revision_record(
            settings.workspace_root,
            version.design_version_id,
            name,
        )
        _validate_revision(revision, len(values))
        assert revision is not None
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
        design_id=design_id,
        design_version_id=UUID(version.design_version_id),
        version_number=version.version_number,
        status=design.status,
        responses=responses,
    )


def latin_hypercube_csv(
    settings: Settings,
    design_id: UUID,
) -> tuple[bytes, str]:
    design = get_latin_hypercube_design(settings, design_id)
    responses = list_latin_hypercube_responses(settings, design_id)
    by_response = {
        item.response_name: {value.run_order: value.value for value in item.values}
        for item in responses.responses
    }
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    factor_names = [item.name for item in design.factors]
    response_names = sorted(by_response)
    writer.writerow(
        ["Standard order", "Run order"]
        + [_csv_text(name) for name in factor_names]
        + [_csv_text(f"{name} normalized") for name in factor_names]
        + [_csv_text(name) for name in response_names]
    )
    for run in sorted(design.runs, key=lambda item: item.run_order):
        writer.writerow(
            [run.standard_order, run.run_order]
            + [
                _display_factor_value(
                    run.factor_levels[factor.name],
                    factor.display_decimals,
                )
                for factor in design.factors
            ]
            + [run.normalized_levels[name] for name in factor_names]
            + [by_response[name].get(run.run_order, "") for name in response_names]
        )
    return output.getvalue().encode("utf-8-sig"), f"datalab-lhs-{design_id}.csv"


def _load(
    settings: Settings,
    design_id: UUID,
) -> tuple[ExperimentDesignRecord, ExperimentDesignVersionRecord, list[ExperimentRunRecord]]:
    design = get_experiment_design_record(settings.workspace_root, str(design_id))
    if design is None:
        raise _error("lhs_design_not_found", "요청한 LHS 설계를 찾을 수 없습니다.", 404)
    if design.method_id != LHS_METHOD_ID or design.family != LATIN_HYPERCUBE_FAMILY:
        raise _error(
            "lhs_design_family_unsupported",
            "요청한 설계는 LHS 공간충전 설계가 아닙니다.",
            status.HTTP_409_CONFLICT,
        )
    version = get_experiment_design_version_record(
        settings.workspace_root,
        design.design_id,
        design.current_version,
    )
    if version is None:
        raise _error(
            "lhs_design_version_missing",
            "LHS 설계 version metadata를 찾을 수 없습니다.",
            status.HTTP_409_CONFLICT,
        )
    runs = list_experiment_run_records(settings.workspace_root, version.design_version_id)
    if len(runs) != version.run_count:
        raise _metadata_error()
    return design, version, runs


def _response(
    design: ExperimentDesignRecord,
    version: ExperimentDesignVersionRecord,
    records: list[ExperimentRunRecord],
) -> LatinHypercubeDesignResponse:
    method_version: Literal["0.1.0", "0.2.0"]
    if design.method_version == "0.1.0":
        method_version = "0.1.0"
    elif design.method_version == "0.2.0":
        method_version = "0.2.0"
    else:
        raise _metadata_error()
    factors_payload = _list(version.factors_json)
    options_payload = _dict(version.options_json)
    quality_payload = options_payload.get("quality")
    if not isinstance(quality_payload, dict):
        raise _metadata_error()
    try:
        factor_responses = [DoeFactorResponse.model_validate(item) for item in factors_payload]
        options_response = LatinHypercubeDesignOptionsResponse.model_validate(
            {key: value for key, value in options_payload.items() if key != "quality"}
        )
    except ValidationError as exc:
        raise _metadata_error() from exc
    if options_response.run_count != version.run_count:
        raise _metadata_error()
    factors = [
        LatinHypercubeFactor(
            name=item.name,
            low=item.low,
            high=item.high,
            unit=item.unit,
            domain_kind=item.domain_kind,
            step=item.step,
            display_decimals=item.display_decimals,
        )
        for item in factor_responses
    ]
    points_by_standard: list[list[float] | None] = [None] * version.run_count
    run_payloads: list[LatinHypercubeRun] = []
    for record in records:
        actual = _float_dict(record.factor_levels_json)
        normalized = _float_dict(record.coded_levels_json)
        if set(actual) != {item.name for item in factors} or set(normalized) != set(actual):
            raise _metadata_error()
        point = [normalized[item.name] for item in factors]
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in point):
            raise _metadata_error()
        if not 1 <= record.standard_order <= version.run_count:
            raise _metadata_error()
        points_by_standard[record.standard_order - 1] = point
        run_payloads.append(
            LatinHypercubeRun(
                standard_order=record.standard_order,
                run_order=record.run_order,
                factor_levels=actual,
                normalized_levels=normalized,
            )
        )
    if any(point is None for point in points_by_standard):
        raise _metadata_error()
    points = np.asarray(points_by_standard, dtype=float)
    recalculated = calculate_latin_hypercube_quality(points, factors=factors)
    mixed = any(item.domain_kind == "discrete_numeric" for item in factors)
    if (not mixed and not recalculated.strata_valid) or (
        mixed
        and (
            recalculated.continuous_strata_valid is not True
            or recalculated.duplicate_count != 0
            or any(
                max(counts) - min(counts) > 1
                for counts in (recalculated.discrete_level_balance or {}).values()
            )
        )
    ):
        raise _metadata_error()
    for field in (
        "centered_discrepancy",
        "minimum_pairwise_distance",
        "maximum_absolute_factor_correlation",
    ):
        if not math.isclose(
            _finite_number(quality_payload.get(field)),
            float(getattr(recalculated, field)),
            rel_tol=1e-10,
            abs_tol=1e-12,
        ):
            raise _metadata_error()
    if sorted(item.run_order for item in run_payloads) != list(range(1, version.run_count + 1)):
        raise _metadata_error()
    stat_options = LatinHypercubeOptions(
        run_count=options_response.run_count,
        seed=options_response.seed,
        randomize_run_order=options_response.randomize_run_order,
        run_order_seed=options_response.run_order_seed,
        optimization=options_response.optimization,
    )
    payload = canonical_latin_hypercube_payload(
        factors=factors,
        options=stat_options,
        quality=recalculated,
        runs=tuple(sorted(run_payloads, key=lambda item: item.standard_order)),
    )
    package_versions = payload["package_versions"]
    assert isinstance(package_versions, dict)
    package_versions["numpy"] = str(options_payload["numpy_version"])
    package_versions["scipy"] = str(options_payload["scipy_version"])
    calculated_hash = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if calculated_hash != version.design_sha256:
        raise _metadata_error()
    return LatinHypercubeDesignResponse(
        design_schema_version=2 if mixed else 1,
        design_id=UUID(design.design_id),
        design_version_id=UUID(version.design_version_id),
        version_number=1,
        method_id="doe.latin_hypercube",
        method_version=method_version,
        family="latin_hypercube_space_filling",
        name=design.name,
        status=design.status,
        created_at=design.created_at,
        updated_at=design.updated_at,
        app_version=design.app_version,
        factors=factor_responses,
        options=options_response,
        quality=LatinHypercubeDesignQualityResponse(
            centered_discrepancy=recalculated.centered_discrepancy,
            minimum_pairwise_distance=recalculated.minimum_pairwise_distance,
            maximum_absolute_factor_correlation=(recalculated.maximum_absolute_factor_correlation),
            per_factor_strata_occupancy=[
                list(item) for item in recalculated.per_factor_strata_occupancy
            ],
            strata_valid=recalculated.strata_valid,
            continuous_strata_valid=recalculated.continuous_strata_valid,
            discrete_level_balance={
                key: list(value)
                for key, value in (recalculated.discrete_level_balance or {}).items()
            },
            duplicate_count=recalculated.duplicate_count,
            executable_point_count=recalculated.executable_point_count,
        ),
        run_count=version.run_count,
        design_sha256=version.design_sha256,
        runs=[
            LatinHypercubeRunResponse(
                standard_order=item.standard_order,
                run_order=item.run_order,
                replicate_index=1,
                center_point=False,
                block_index=None,
                factor_levels=item.factor_levels,
                normalized_levels=item.normalized_levels,
            )
            for item in sorted(run_payloads, key=lambda item: item.run_order)
        ],
    )


def _float_dict(value: str) -> dict[str, float]:
    payload = _dict(value)
    result: dict[str, float] = {}
    for key, item in payload.items():
        result[key] = _finite_number(item)
    return result


def _finite_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _metadata_error()
    number = float(value)
    if not math.isfinite(number):
        raise _metadata_error()
    return number


def _validate_revision(
    revision: ExperimentResponseRevisionRecord | None,
    value_count: int,
) -> None:
    if (
        revision is None
        or revision.schema_version != 1
        or revision.state != "completed"
        or revision.value_count != value_count
    ):
        raise _error(
            "lhs_response_revision_dependency_mismatch",
            "현재 LHS response revision metadata를 검증할 수 없습니다.",
            status.HTTP_409_CONFLICT,
        )


def _csv_text(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def _display_factor_value(value: float, decimals: int | None) -> float | str:
    if decimals is None:
        return value
    return f"{value:.{decimals}f}"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _dict(value: str) -> dict[str, object]:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise _metadata_error()
    return payload


def _list(value: str) -> list[dict[str, object]]:
    payload = json.loads(value)
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise _metadata_error()
    return payload


def _metadata_error() -> ApiError:
    return _error(
        "lhs_design_metadata_invalid",
        "저장된 LHS 설계 metadata를 검증할 수 없습니다.",
        status.HTTP_409_CONFLICT,
    )


def _lhs_error_message(code: str) -> str:
    return {
        "lhs_factor_count_invalid": "연속형 요인은 1개부터 6개까지 지원합니다.",
        "lhs_factor_name_invalid": "요인 이름은 비어 있거나 중복될 수 없습니다.",
        "lhs_factor_bounds_invalid": "각 요인의 범위는 유한한 low < high여야 합니다.",
        "lhs_run_count_invalid": "실험 수는 2개부터 200개까지 지원합니다.",
    }.get(code, "LHS 공간충전 설계를 생성할 수 없습니다.")


def _error(code: str, message: str, status_code: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status_code)
