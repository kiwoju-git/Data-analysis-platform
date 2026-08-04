from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Literal
from uuid import UUID, uuid4

from fastapi import status

from app.analyses.registry import get_method_version
from app.api.v1.schemas.analyses import (
    AnalysisProvenance,
    AnalysisResultEnvelope,
    AnalysisRunState,
    AnalysisWarning,
    RegressionResponseOptimizationListResponse,
    RegressionResponseOptimizationRequest,
    RegressionResponseOptimizationResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import runtime_build_provenance
from app.services.analysis_run_results import load_analysis_run_result_base
from app.services.regression_models import get_regression_model_manifest
from app.statistics.regression_response_optimizer import (
    RegressionResponseOptimizerError,
    calculate_regression_response_optimizer,
)
from app.storage.atomic import atomic_write_bytes
from app.storage.metadata import (
    AnalysisRunRecord,
    get_analysis_run_record,
    insert_analysis_run_record,
    list_analysis_run_records,
)

APP_VERSION = "0.1.0"
METHOD_ID: Final[Literal["regression.linear_model_optimizer"]] = "regression.linear_model_optimizer"
METHOD_VERSION = get_method_version(METHOD_ID)
CONFIG_SCHEMA_VERSION = 1


def create_regression_response_optimization(
    settings: Settings,
    *,
    model_id: UUID,
    body: RegressionResponseOptimizationRequest,
) -> RegressionResponseOptimizationResponse:
    model = get_regression_model_manifest(settings, model_id)
    if model.manifest_sha256 != body.expected_model_manifest_sha256:
        raise _error(
            "regression_optimizer_model_manifest_mismatch",
            "회귀모델 manifest가 사전 확인 시점과 달라졌습니다.",
            status.HTTP_409_CONFLICT,
        )
    source_analysis = get_analysis_run_record(settings.workspace_root, str(model.analysis_id))
    if source_analysis is None or source_analysis.method_id != "regression.linear_model":
        raise _error(
            "regression_optimizer_source_model_invalid",
            "회귀모델 source analysis를 검증할 수 없습니다.",
            status.HTTP_409_CONFLICT,
        )
    if source_analysis.stale:
        raise _error(
            "regression_optimizer_source_model_stale",
            "현재 데이터 schema와 일치하는 회귀모델을 다시 적합하세요.",
            status.HTTP_409_CONFLICT,
        )
    factor_bounds = _unique_mapping(
        [(item.column_id, (item.lower, item.upper)) for item in body.factor_bounds],
        "regression_optimizer_factor_bound_duplicate",
    )
    categorical_levels = _unique_mapping(
        [(item.column_id, item.level) for item in body.fixed_categorical_levels],
        "regression_optimizer_categorical_setting_duplicate",
    )
    try:
        result = calculate_regression_response_optimizer(
            model.manifest,
            goal=body.goal.kind,
            lower=body.goal.lower,
            target=body.goal.target,
            upper=body.goal.upper,
            numeric_bounds=factor_bounds,
            fixed_categorical_levels=categorical_levels,
            linear_constraints=[item.model_dump(mode="json") for item in body.linear_constraints],
            random_seed=body.search.random_seed,
            random_candidate_count=body.search.random_candidate_count,
            multi_start_count=body.search.multi_start_count,
            max_iterations=body.search.max_iterations,
            max_evaluations=body.search.max_evaluations,
            profile_point_count=body.search.profile_point_count,
        )
    except RegressionResponseOptimizerError as exc:
        raise _calculation_error(exc.code) from exc

    optimization_id = uuid4()
    created_at = _utc_now()
    result.update(
        {
            "optimization_id": str(optimization_id),
            "model_id": str(model_id),
            "source_analysis_id": str(model.analysis_id),
            "source_dataset_version_id": str(model.dataset_version_id),
            "model_manifest_sha256": model.manifest_sha256,
        }
    )
    config_payload: dict[str, Any] = {
        "config_schema_version": CONFIG_SCHEMA_VERSION,
        "optimization_id": str(optimization_id),
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "model_id": str(model_id),
        "source_analysis_id": str(model.analysis_id),
        "source_dataset_version_id": str(model.dataset_version_id),
        "model_manifest_sha256": model.manifest_sha256,
        "request": body.model_dump(mode="json"),
    }
    config_bytes = _canonical_bytes(config_payload)
    result_bytes = _canonical_bytes(result)
    response = RegressionResponseOptimizationResponse(
        optimization_id=optimization_id,
        model_id=model_id,
        source_analysis_id=model.analysis_id,
        source_dataset_version_id=model.dataset_version_id,
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        model_manifest_sha256=model.manifest_sha256,
        config_sha256=hashlib.sha256(config_bytes).hexdigest(),
        result_sha256=hashlib.sha256(result_bytes).hexdigest(),
        result=result,
        created_at=created_at,
    )
    _persist(settings, response, config_payload)
    return response


def get_regression_response_optimization(
    settings: Settings,
    *,
    model_id: UUID,
    optimization_id: UUID,
) -> RegressionResponseOptimizationResponse:
    stored = load_analysis_run_result_base(settings, optimization_id)
    if stored.record.method_id != METHOD_ID:
        raise _error(
            "regression_optimizer_not_found",
            "요청한 회귀 최적화 결과를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    try:
        config = json.loads(stored.record.config_json)
        response = RegressionResponseOptimizationResponse.model_validate(stored.envelope.result)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _error(
            "regression_optimizer_metadata_invalid",
            "저장된 회귀 최적화 metadata 형식이 올바르지 않습니다.",
            status.HTTP_409_CONFLICT,
        ) from exc
    _validate_restore_relationship(model_id, optimization_id, config, response)
    try:
        model = get_regression_model_manifest(settings, model_id)
    except ApiError as exc:
        raise _error(
            "regression_optimizer_source_model_missing",
            "회귀 최적화 source model을 찾을 수 없습니다.",
            status.HTTP_409_CONFLICT,
        ) from exc
    if model.manifest_sha256 != response.model_manifest_sha256:
        raise _error(
            "regression_optimizer_model_manifest_mismatch",
            "회귀 최적화 결과와 source model manifest가 일치하지 않습니다.",
            status.HTTP_409_CONFLICT,
        )
    return response


def list_regression_response_optimizations(
    settings: Settings,
    *,
    model_id: UUID,
) -> RegressionResponseOptimizationListResponse:
    records = list_analysis_run_records(
        settings.workspace_root,
        dataset_version_id=None,
        method_id=METHOD_ID,
        status=AnalysisRunState.SUCCEEDED.value,
        stale=None,
        result_available=True,
        limit=1_000,
        offset=0,
    )
    items: list[RegressionResponseOptimizationResponse] = []
    for record in records:
        try:
            config = json.loads(record.config_json)
        except json.JSONDecodeError:
            continue
        if config.get("model_id") != str(model_id):
            continue
        items.append(
            get_regression_response_optimization(
                settings,
                model_id=model_id,
                optimization_id=UUID(record.analysis_id),
            )
        )
    return RegressionResponseOptimizationListResponse(
        model_id=model_id,
        optimizations=items,
        total=len(items),
    )


def _persist(
    settings: Settings,
    response: RegressionResponseOptimizationResponse,
    config_payload: dict[str, Any],
) -> None:
    envelope = AnalysisResultEnvelope(
        analysis_id=response.optimization_id,
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        dataset_version_id=response.source_dataset_version_id,
        status="succeeded",
        warnings=[
            AnalysisWarning(code=str(code), severity="warning", message=_warning_message(str(code)))
            for code in response.result.get("warnings", [])
        ],
        provenance=AnalysisProvenance(
            method_id=METHOD_ID,
            method_version=METHOD_VERSION,
            dataset_version_id=response.source_dataset_version_id,
            source_schema_hash=None,
            app_version=APP_VERSION,
            **runtime_build_provenance(settings),
        ),
        result=response.model_dump(mode="json"),
    )
    envelope_bytes = _canonical_bytes(envelope.model_dump(mode="json"))
    relative_path = _result_relative_path(response.optimization_id)
    path = settings.workspace_root / relative_path
    try:
        atomic_write_bytes(path, envelope_bytes)
        insert_analysis_run_record(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(response.optimization_id),
                method_id=METHOD_ID,
                method_version=METHOD_VERSION,
                dataset_version_id=str(response.source_dataset_version_id),
                config_json=_canonical_bytes(config_payload).decode("utf-8"),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=relative_path.as_posix(),
                result_sha256=hashlib.sha256(envelope_bytes).hexdigest(),
                stale=False,
                created_at=response.created_at,
                updated_at=response.created_at,
                completed_at=response.created_at,
                app_version=APP_VERSION,
            ),
        )
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def _validate_restore_relationship(
    model_id: UUID,
    optimization_id: UUID,
    config: object,
    response: RegressionResponseOptimizationResponse,
) -> None:
    if not isinstance(config, dict):
        raise _restore_error()
    config_copy = dict(config)
    request = config_copy.get("request")
    if not isinstance(request, dict):
        raise _restore_error()
    try:
        RegressionResponseOptimizationRequest.model_validate(request)
    except ValueError as exc:
        raise _restore_error() from exc
    config_sha = hashlib.sha256(_canonical_bytes(config_copy)).hexdigest()
    result_sha = hashlib.sha256(_canonical_bytes(response.result)).hexdigest()
    if not (
        config_copy.get("config_schema_version") == CONFIG_SCHEMA_VERSION
        and config_copy.get("optimization_id") == str(optimization_id)
        and config_copy.get("model_id") == str(model_id)
        and config_copy.get("method_id") == METHOD_ID
        and config_copy.get("method_version") == METHOD_VERSION
        and response.optimization_id == optimization_id
        and response.model_id == model_id
        and response.method_id == METHOD_ID
        and response.method_version == METHOD_VERSION
        and response.config_sha256 == config_sha
        and response.result_sha256 == result_sha
        and response.result.get("optimization_id") == str(optimization_id)
        and response.result.get("model_id") == str(model_id)
        and response.result.get("model_manifest_sha256") == response.model_manifest_sha256
    ):
        raise _restore_error()


def _unique_mapping(items: list[tuple[str, Any]], duplicate_code: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise _error(duplicate_code, "같은 predictor 설정이 중복되었습니다.")
        result[key] = value
    return result


def _calculation_error(code: str) -> ApiError:
    messages = {
        "regression_optimizer_goal_invalid": "반응 최적화 목표와 한계가 올바르지 않습니다.",
        "regression_optimizer_factor_bound_invalid": (
            "검색 범위는 회귀 학습 범위 안에서 지정해야 합니다."
        ),
        "regression_optimizer_categorical_combination_limit": (
            "범주 수준 조합이 256개를 초과합니다. 일부 수준을 고정하세요."
        ),
        "regression_optimizer_no_feasible_point": (
            "지정한 범위와 제약을 만족하는 후보를 찾지 못했습니다."
        ),
        "regression_optimizer_search_budget_invalid": "회귀 최적화 탐색 예산이 올바르지 않습니다.",
    }
    return _error(code, messages.get(code, "회귀모형 기반 반응 최적화를 계산할 수 없습니다."))


def _restore_error() -> ApiError:
    return _error(
        "regression_optimizer_metadata_invalid",
        "저장된 회귀 최적화 result와 config 관계가 올바르지 않습니다.",
        status.HTTP_409_CONFLICT,
    )


def _warning_message(code: str) -> str:
    return {
        "regression_optimizer_global_optimum_not_guaranteed": (
            "탐색 결과는 전역 최적점을 보장하지 않습니다."
        ),
        "regression_optimizer_confirmation_experiment_required": (
            "모델 예측이므로 실제 확인 실험이 필요합니다."
        ),
        "regression_optimizer_associational_model_not_causal": (
            "회귀 관계를 인과관계로 해석하지 마세요."
        ),
        "regression_optimizer_profiles_are_conditional_slices": (
            "프로파일은 다른 predictor를 최적 설정에 고정한 조건부 단면입니다."
        ),
    }.get(code, code)


def _error(
    code: str, message: str, status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
) -> ApiError:
    return ApiError(code=code, message=message, status_code=status_code)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _result_relative_path(optimization_id: UUID) -> Path:
    return Path("workspaces") / "analyses" / str(optimization_id) / "result.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
