from __future__ import annotations

import hashlib
import json
from math import isfinite
from typing import Any, Final, Literal
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.doe import (
    DoeResponseSurfaceAnalysisResponse,
    ResponseOptimizerCreateRequest,
    ResponseOptimizerResponse,
    ResponseOptimizerResult,
    ResponseSurfaceDesignResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    APP_VERSION,
    canonical_json_bytes,
    runtime_build_provenance,
    utc_now,
)
from app.services.doe_response_surface_analysis import get_response_surface_analysis
from app.services.response_surface_designs import get_response_surface_design
from app.statistics.response_optimizer import (
    RESPONSE_OPTIMIZER_RESULT_SCHEMA_VERSION,
    OptimizerEligibilityIssue,
    OptimizerFactor,
    OptimizerFactorBound,
    OptimizerLinearConstraint,
    OptimizerModel,
    OptimizerObjective,
    OptimizerSearchOptions,
    OptimizerSourceEligibility,
    OptimizerTerm,
    ResponseOptimizerError,
    calculate_response_optimizer,
)
from app.storage.metadata import (
    ExperimentDesignAnalysisRecord,
    get_experiment_design_analysis_record,
    insert_experiment_design_analysis_record,
)

RESPONSE_OPTIMIZER_METHOD_ID: Final[Literal["regression.response_optimizer"]] = (
    "regression.response_optimizer"
)
RESPONSE_OPTIMIZER_CONFIG_SCHEMA_VERSION: Final[Literal[2]] = 2
RESPONSE_OPTIMIZER_RECORD_RESPONSE_NAME = "response_optimizer"


def create_response_optimizer(
    settings: Settings,
    design_id: UUID,
    body: ResponseOptimizerCreateRequest,
) -> ResponseOptimizerResponse:
    design = get_response_surface_design(settings, design_id)
    objectives, source_dependencies, source_eligibility = _load_source_objectives(
        settings,
        design_id,
        body,
    )
    source_bundle_sha256 = hashlib.sha256(
        canonical_json_bytes(
            {
                "schema_version": 2,
                "design_id": str(design.design_id),
                "design_version_id": str(design.design_version_id),
                "design_sha256": design.design_sha256,
                "sources": source_dependencies,
            }
        )
    ).hexdigest()
    try:
        result_payload = calculate_response_optimizer(
            objectives,
            factor_bounds=[
                OptimizerFactorBound(item.factor_name, float(item.lower), float(item.upper))
                for item in body.factor_bounds
            ],
            linear_constraints=[
                OptimizerLinearConstraint(
                    name=item.name,
                    coefficients={key: float(value) for key, value in item.coefficients.items()},
                    relation=item.relation,
                    bound=float(item.bound),
                )
                for item in body.linear_constraints
            ],
            search_options=OptimizerSearchOptions(**body.search.model_dump()),
            source_model_eligibility=source_eligibility,
        )
        result = ResponseOptimizerResult.model_validate(result_payload)
    except ResponseOptimizerError as exc:
        raise _optimizer_api_error(exc.code) from exc
    except ValidationError as exc:
        raise _metadata_error("response_optimizer_result_invalid") from exc

    optimization_id = uuid4()
    created_at = utc_now()
    method_version = METHOD_VERSIONS[RESPONSE_OPTIMIZER_METHOD_ID]
    config_payload = {
        "schema_version": RESPONSE_OPTIMIZER_CONFIG_SCHEMA_VERSION,
        "design_id": str(design.design_id),
        "design_version_id": str(design.design_version_id),
        "design_sha256": design.design_sha256,
        "source_bundle_sha256": source_bundle_sha256,
        "request": body.model_dump(mode="json"),
    }
    config_json = _json_dumps(config_payload)
    config_sha256 = hashlib.sha256(config_json.encode("utf-8")).hexdigest()
    response = ResponseOptimizerResponse(
        optimization_id=optimization_id,
        design_id=design.design_id,
        design_version_id=design.design_version_id,
        design_version_number=design.version_number,
        method_id=RESPONSE_OPTIMIZER_METHOD_ID,
        method_version=method_version,
        config_schema_version=RESPONSE_OPTIMIZER_CONFIG_SCHEMA_VERSION,
        result_schema_version=RESPONSE_OPTIMIZER_RESULT_SCHEMA_VERSION,
        config_sha256=config_sha256,
        design_sha256=design.design_sha256,
        source_analysis_ids=[item.source_analysis_id for item in body.objectives],
        source_bundle_sha256=source_bundle_sha256,
        acknowledged_source_warning_codes=list(
            source_eligibility.acknowledged_source_warning_codes
        ),
        created_at=created_at,
        app_version=APP_VERSION,
        result=result,
        **runtime_build_provenance(settings),
    )
    result_json = _json_dumps(response.model_dump(mode="json"))
    record = ExperimentDesignAnalysisRecord(
        analysis_id=str(optimization_id),
        design_version_id=str(design.design_version_id),
        response_name=RESPONSE_OPTIMIZER_RECORD_RESPONSE_NAME,
        method_id=RESPONSE_OPTIMIZER_METHOD_ID,
        method_version=method_version,
        config_json=config_json,
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
        response_sha256=source_bundle_sha256,
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


def get_response_optimizer(
    settings: Settings,
    design_id: UUID,
    optimization_id: UUID,
) -> ResponseOptimizerResponse:
    design = get_response_surface_design(settings, design_id)
    record = get_experiment_design_analysis_record(settings.workspace_root, str(optimization_id))
    if record is None or record.design_version_id != str(design.design_version_id):
        raise ApiError(
            code="response_optimizer_not_found",
            message="요청한 Response Optimizer 결과를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _validated_optimizer_response(settings, design_id, record)


def _validated_optimizer_response(
    settings: Settings,
    design_id: UUID,
    record: ExperimentDesignAnalysisRecord,
) -> ResponseOptimizerResponse:
    design = get_response_surface_design(settings, design_id)
    if (
        record.method_id != RESPONSE_OPTIMIZER_METHOD_ID
        or record.method_version != METHOD_VERSIONS[RESPONSE_OPTIMIZER_METHOD_ID]
        or record.response_name != RESPONSE_OPTIMIZER_RECORD_RESPONSE_NAME
    ):
        raise _metadata_error("response_optimizer_method_mismatch")
    if hashlib.sha256(record.result_json.encode("utf-8")).hexdigest() != record.result_sha256:
        raise _metadata_error("response_optimizer_checksum_mismatch")
    try:
        config = json.loads(record.config_json)
        response = ResponseOptimizerResponse.model_validate_json(record.result_json)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise _metadata_error("response_optimizer_metadata_invalid") from exc
    if not isinstance(config, dict):
        raise _metadata_error("response_optimizer_metadata_invalid")
    config_sha256 = hashlib.sha256(record.config_json.encode("utf-8")).hexdigest()
    if (
        config.get("schema_version") != RESPONSE_OPTIMIZER_CONFIG_SCHEMA_VERSION
        or config.get("design_id") != str(design.design_id)
        or config.get("design_version_id") != str(design.design_version_id)
        or config.get("design_sha256") != design.design_sha256
        or response.optimization_id != UUID(record.analysis_id)
        or response.design_id != design.design_id
        or response.design_version_id != design.design_version_id
        or response.design_sha256 != design.design_sha256
        or response.method_id != record.method_id
        or response.method_version != record.method_version
        or response.config_schema_version != RESPONSE_OPTIMIZER_CONFIG_SCHEMA_VERSION
        or response.result_schema_version != RESPONSE_OPTIMIZER_RESULT_SCHEMA_VERSION
        or response.result.schema_version != RESPONSE_OPTIMIZER_RESULT_SCHEMA_VERSION
        or response.config_sha256 != config_sha256
        or response.source_bundle_sha256 != record.response_sha256
    ):
        raise _metadata_error("response_optimizer_dependency_mismatch")
    try:
        request = ResponseOptimizerCreateRequest.model_validate(config.get("request"))
    except ValidationError as exc:
        raise _metadata_error("response_optimizer_config_invalid") from exc
    objectives, source_dependencies, source_eligibility = _load_source_objectives(
        settings, design_id, request
    )
    current_source_bundle_sha256 = hashlib.sha256(
        canonical_json_bytes(
            {
                "schema_version": 2,
                "design_id": str(design.design_id),
                "design_version_id": str(design.design_version_id),
                "design_sha256": design.design_sha256,
                "sources": source_dependencies,
            }
        )
    ).hexdigest()
    if (
        config.get("source_bundle_sha256") != current_source_bundle_sha256
        or record.response_sha256 != current_source_bundle_sha256
        or response.source_bundle_sha256 != current_source_bundle_sha256
        or response.source_analysis_ids != [item.source_analysis_id for item in request.objectives]
    ):
        raise _metadata_error("response_optimizer_source_bundle_mismatch")
    _validate_result_config_relationship(response, request, objectives, source_eligibility, design)
    return response


def _load_source_objectives(
    settings: Settings,
    design_id: UUID,
    body: ResponseOptimizerCreateRequest,
) -> tuple[
    list[OptimizerObjective],
    list[dict[str, object]],
    OptimizerSourceEligibility,
]:
    design = get_response_surface_design(settings, design_id)
    factors = tuple(
        OptimizerFactor(
            name=factor.name,
            low=factor.low,
            high=factor.high,
            alpha=design.options.alpha,
            unit=factor.unit,
        )
        for factor in design.factors
    )
    objectives: list[OptimizerObjective] = []
    dependencies: list[dict[str, object]] = []
    eligibility_issues: list[OptimizerEligibilityIssue] = []
    for requested in body.objectives:
        try:
            source = get_response_surface_analysis(
                settings,
                design_id,
                requested.source_analysis_id,
            )
        except ApiError as exc:
            code = "response_optimizer_source_analysis_missing"
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                code = "response_optimizer_source_model_ineligible"
            raise ApiError(
                code=code,
                message="검증 가능한 source response-surface 분석이 필요합니다.",
                status_code=status.HTTP_409_CONFLICT,
            ) from exc
        source_record = get_experiment_design_analysis_record(
            settings.workspace_root,
            str(requested.source_analysis_id),
        )
        if source_record is None:
            raise _metadata_error("response_optimizer_source_analysis_missing")
        confidence_level = _source_confidence_level(source_record.config_json)
        source_issues = _source_model_eligibility_issues(source, confidence_level)
        eligibility_issues.extend(source_issues)
        model = OptimizerModel(
            analysis_id=str(source.analysis_id),
            response_name=source.response_name,
            response_unit=source.result.response.unit,
            factors=factors,
            terms=tuple(
                OptimizerTerm(
                    kind=term.kind,
                    factor_names=tuple(term.factor_names),
                    coefficient=term.coefficient,
                )
                for term in source.result.terms
            ),
            source_warnings=tuple(source.result.warnings),
        )
        objectives.append(
            OptimizerObjective(
                model=model,
                goal=requested.goal,
                lower=None if requested.lower is None else float(requested.lower),
                target=None if requested.target is None else float(requested.target),
                upper=None if requested.upper is None else float(requested.upper),
                lower_weight=float(requested.lower_weight),
                upper_weight=float(requested.upper_weight),
                importance=float(requested.importance),
            )
        )
        dependencies.append(
            {
                "analysis_id": str(source.analysis_id),
                "method_id": source.method_id,
                "method_version": source.method_version,
                "result_sha256": source_record.result_sha256,
                "response_sha256": source.response_sha256,
                "response_revision_id": str(source.response_revision_id),
                "response_revision_number": source.response_revision_number,
                "response_revision_sha256": source.response_revision_sha256,
                "response_name": source.response_name,
                "design_version_id": str(source.design_version_id),
                "eligibility_issue_codes": [item.code for item in source_issues],
            }
        )
    eligibility_issues.extend(
        [
            OptimizerEligibilityIssue(
                source_analysis_id=None,
                code="response_optimizer_global_optimum_not_guaranteed",
                severity="informational",
            ),
            OptimizerEligibilityIssue(
                source_analysis_id=None,
                code="response_optimizer_confirmation_run_required",
                severity="informational",
            ),
        ]
    )
    eligibility = _validated_source_eligibility(eligibility_issues, body)
    return objectives, dependencies, eligibility


def _validate_result_config_relationship(
    response: ResponseOptimizerResponse,
    request: ResponseOptimizerCreateRequest,
    objectives: list[OptimizerObjective],
    source_eligibility: OptimizerSourceEligibility,
    design: ResponseSurfaceDesignResponse,
) -> None:
    expected_objectives = [
        {
            "source_analysis_id": objective.model.analysis_id,
            "response_name": objective.model.response_name,
            "response_unit": objective.model.response_unit,
            "goal": objective.goal,
            "lower": objective.lower,
            "target": objective.target,
            "upper": objective.upper,
            "lower_weight": objective.lower_weight,
            "upper_weight": objective.upper_weight,
            "importance": objective.importance,
        }
        for objective in objectives
    ]
    if [item.model_dump(mode="json") for item in response.result.objectives] != expected_objectives:
        raise _metadata_error("response_optimizer_result_config_mismatch")
    search = response.result.search
    if any(
        getattr(search, name) != getattr(request.search, name)
        for name in (
            "random_seed",
            "random_candidate_count",
            "multi_start_count",
            "max_iterations",
            "max_evaluations",
            "time_budget_ms",
        )
    ):
        raise _metadata_error("response_optimizer_result_config_mismatch")
    requested_bounds = {item.factor_name: item for item in request.factor_bounds}
    expected_bounds = []
    for factor in design.factors:
        requested = requested_bounds.get(factor.name)
        expected_bounds.append(
            {
                "factor_name": factor.name,
                "lower": factor.low if requested is None else float(requested.lower),
                "upper": factor.high if requested is None else float(requested.upper),
            }
        )
    if [
        item.model_dump() for item in response.result.factor_region.search_bounds
    ] != expected_bounds:
        raise _metadata_error("response_optimizer_result_config_mismatch")
    if [item.model_dump() for item in response.result.factor_region.linear_constraints] != [
        item.model_dump() for item in request.linear_constraints
    ]:
        raise _metadata_error("response_optimizer_result_config_mismatch")
    recommendation_ids = [
        item.source_analysis_id for item in response.result.recommendation.objectives
    ]
    if recommendation_ids != response.source_analysis_ids:
        raise _metadata_error("response_optimizer_result_config_mismatch")

    acknowledged = list(source_eligibility.acknowledged_source_warning_codes)
    if (
        response.acknowledged_source_warning_codes != acknowledged
        or response.result.acknowledged_source_warning_codes != acknowledged
        or response.result.source_model_eligibility.model_dump(mode="json")
        != _eligibility_payload(source_eligibility)
    ):
        raise _metadata_error("response_optimizer_result_config_mismatch")


def _source_confidence_level(config_json: str) -> float:
    try:
        config = json.loads(config_json)
        confidence_level = float(config["confidence_level"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise _metadata_error("response_optimizer_source_analysis_invalid") from exc
    if not isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise _metadata_error("response_optimizer_source_analysis_invalid")
    return confidence_level


def _source_model_eligibility_issues(
    source: DoeResponseSurfaceAnalysisResponse,
    confidence_level: float,
) -> list[OptimizerEligibilityIssue]:
    analysis_id = str(source.analysis_id)
    result = source.result
    issues: list[OptimizerEligibilityIssue] = []

    def add(
        code: str,
        severity: Literal["blocking", "acknowledgment_required", "informational"],
        source_warning_code: str | None = None,
    ) -> None:
        issues.append(
            OptimizerEligibilityIssue(
                source_analysis_id=analysis_id,
                code=code,
                severity=severity,
                source_warning_code=source_warning_code,
            )
        )

    sample = result.sample
    fit = result.fit
    diagnostics = result.diagnostics
    if sample.rank != sample.parameter_count:
        add("response_optimizer_source_model_rank_invalid", "blocking")
    if sample.df_residual <= 0:
        add(
            "response_optimizer_source_model_saturated",
            "blocking",
            "doe_rsm_model_saturated_no_inference",
        )
    else:
        residual_variance = fit.residual_mean_square
        residual_standard_error = fit.residual_standard_error
        if (
            residual_variance is None
            or not isfinite(residual_variance)
            or residual_variance <= 0
            or residual_standard_error is None
            or not isfinite(residual_standard_error)
            or residual_standard_error <= 0
        ):
            add(
                "response_optimizer_source_residual_variance_unusable",
                "blocking",
                "doe_rsm_residual_variance_zero",
            )
        if sample.df_residual < 5:
            add(
                "response_optimizer_source_residual_df_small",
                "acknowledgment_required",
                "doe_rsm_residual_df_small",
            )

    lack_of_fit = result.anova.lack_of_fit
    lack_of_fit_p = lack_of_fit.lack_of_fit.p_value
    if (
        lack_of_fit.available
        and lack_of_fit_p is not None
        and isfinite(lack_of_fit_p)
        and lack_of_fit_p < 1.0 - confidence_level
    ):
        add("response_optimizer_source_lack_of_fit_significant", "blocking")
    if diagnostics.high_cooks_distance_count > 0:
        add(
            "response_optimizer_source_influential_run",
            "acknowledgment_required",
            "doe_rsm_influential_run_detected",
        )
    if diagnostics.high_leverage_count > 0:
        add("response_optimizer_source_high_leverage", "acknowledgment_required")
    if diagnostics.high_standardized_residual_count > 0:
        add(
            "response_optimizer_source_large_standardized_residual",
            "acknowledgment_required",
            "doe_rsm_large_standardized_residual",
        )
    normality_p = diagnostics.shapiro_wilk.p_value
    if normality_p is not None and isfinite(normality_p) and normality_p < 0.01:
        add(
            "response_optimizer_source_residual_normality_severe",
            "acknowledgment_required",
        )
    add(
        "response_optimizer_source_model_associational",
        "informational",
        "doe_rsm_model_is_associational_not_causal",
    )
    if len(result.factor_names) > 2:
        add(
            "response_optimizer_source_contour_slice_limited",
            "informational",
            "doe_rsm_contour_holds_other_factors_at_center",
        )
    return issues


def _validated_source_eligibility(
    issues: list[OptimizerEligibilityIssue],
    body: ResponseOptimizerCreateRequest,
) -> OptimizerSourceEligibility:
    blocking = [item for item in issues if item.severity == "blocking"]
    required_codes = {item.code for item in issues if item.severity == "acknowledgment_required"}
    acknowledged = body.acknowledged_source_warning_codes
    if blocking:
        raise _optimizer_api_error("response_optimizer_source_model_ineligible")
    if len(acknowledged) != len(set(acknowledged)) or any(
        code not in required_codes for code in acknowledged
    ):
        raise _optimizer_api_error("response_optimizer_source_acknowledgment_invalid")
    if required_codes - set(acknowledged):
        raise _optimizer_api_error("response_optimizer_source_model_acknowledgment_required")
    return OptimizerSourceEligibility(
        eligible=True,
        acknowledgment_required=bool(required_codes),
        issues=tuple(issues),
        acknowledged_source_warning_codes=tuple(acknowledged),
    )


def _eligibility_payload(eligibility: OptimizerSourceEligibility) -> dict[str, object]:
    return {
        "eligible": eligibility.eligible,
        "acknowledgment_required": eligibility.acknowledgment_required,
        "issues": [
            {
                "source_analysis_id": item.source_analysis_id,
                "code": item.code,
                "severity": item.severity,
                "source_warning_code": item.source_warning_code,
            }
            for item in eligibility.issues
        ],
        "acknowledged_source_warning_codes": list(eligibility.acknowledged_source_warning_codes),
    }


def _optimizer_api_error(code: str) -> ApiError:
    messages = {
        "response_optimizer_source_model_ineligible": (
            "source 반응표면 모형이 Response Optimizer 실행 기준을 충족하지 않습니다."
        ),
        "response_optimizer_source_model_acknowledgment_required": (
            "source 모형 진단 경고를 확인한 뒤 명시적으로 승인해야 합니다."
        ),
        "response_optimizer_source_acknowledgment_invalid": (
            "현재 source 모형에 필요한 warning code만 승인할 수 있습니다."
        ),
        "response_optimizer_objective_count_invalid": "최적화 목표는 1~8개여야 합니다.",
        "response_optimizer_objective_thresholds_invalid": (
            "목표 유형의 lower/target/upper 순서가 올바르지 않습니다."
        ),
        "response_optimizer_factor_space_mismatch": "source 모형의 요인 공간이 서로 다릅니다.",
        "response_optimizer_factor_bound_invalid": (
            "요인 탐색 경계는 선언된 설계영역 안이어야 합니다."
        ),
        "response_optimizer_linear_constraint_invalid": "선형 제약조건이 올바르지 않습니다.",
        "response_optimizer_no_feasible_point": (
            "요인 경계와 제약조건을 만족하는 점을 찾을 수 없습니다."
        ),
        "response_optimizer_search_budget_invalid": "최적화 탐색 예산이 허용 범위를 벗어났습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Response Optimizer 요청을 계산할 수 없습니다."),
        status_code=status.HTTP_409_CONFLICT,
    )


def _metadata_error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="저장된 Response Optimizer source/config/result dependency가 일치하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
