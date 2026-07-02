import hashlib
import json
from pathlib import Path
from uuid import UUID

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import get_analysis_method
from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisRunState,
    AnalysisRunStatusResponse,
    MethodAvailability,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_method_handlers import (
    MethodExecutionHandler,
    build_method_execution_handlers,
)
from app.services.analysis_run_execution import (
    utc_now as _utc_now,
)
from app.services.analysis_runners_categorical import (
    run_chi_square_association_analysis,
    run_one_proportion_analysis,
    run_two_proportion_analysis,
)
from app.services.analysis_runners_eda import (
    run_descriptive_analysis,
    run_equal_variances_analysis,
    run_graphical_summary_analysis,
    run_normality_analysis,
)
from app.services.analysis_runners_hypothesis import (
    run_equivalence_tost_analysis,
    run_kruskal_wallis_analysis,
    run_mann_whitney_analysis,
    run_one_sample_t_analysis,
    run_one_sample_wilcoxon_analysis,
    run_one_way_anova_analysis,
    run_paired_t_analysis,
    run_two_sample_t_analysis,
)
from app.services.analysis_runners_quality import (
    run_capability_analysis,
    run_gage_rr_analysis,
    run_gage_run_chart_analysis,
    run_individuals_chart_analysis,
    run_run_chart_analysis,
    run_subgroup_chart_analysis,
)
from app.services.analysis_runners_regression import (
    run_linear_model_analysis,
    run_pearson_analysis,
    run_xy_correlation_analysis,
)
from app.storage.metadata import (
    AnalysisRunRecord,
    count_analysis_artifact_records,
    get_analysis_run_record,
    update_analysis_run_status_record,
)

CANCELLABLE_STATES = {AnalysisRunState.QUEUED.value, AnalysisRunState.RUNNING.value}
TERMINAL_STATES = {
    AnalysisRunState.SUCCEEDED.value,
    AnalysisRunState.FAILED.value,
    AnalysisRunState.CANCELLED.value,
}


def create_analysis_run(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    method = get_analysis_method(request.method_id)
    if method is None:
        raise ApiError(
            code="analysis_method_not_found",
            message="요청한 분석 메서드를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if method.method_version != request.method_version:
        raise ApiError(
            code="analysis_method_version_mismatch",
            message="요청한 분석 메서드 버전이 현재 registry와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    if method.availability != MethodAvailability.AVAILABLE:
        raise ApiError(
            code="analysis_method_not_available",
            message="이 분석 메서드는 아직 실행할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=method.availability.value,
        )

    handler = _METHOD_EXECUTION_HANDLERS.get(request.method_id)
    if handler is not None:
        return handler.run(settings, request)

    if request.method_id == "doe.factorial_design":
        raise ApiError(
            code="analysis_method_uses_dedicated_api",
            message="이 메서드는 DOE 설계 자산 API를 통해 실행해야 합니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail="/api/v1/doe-designs/factorial",
        )

    raise ApiError(
        code="analysis_method_not_available",
        message="이 분석 메서드는 아직 실행할 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
        developer_detail=method.availability.value,
    )


def get_analysis_run_status(
    workspace_root: Path,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    record = get_analysis_run_record(workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _to_response(workspace_root, record)


def get_analysis_run_result(
    settings: Settings,
    analysis_id: UUID,
) -> AnalysisResultEnvelope:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if record.result_path is None or record.result_sha256 is None:
        raise ApiError(
            code="analysis_result_not_available",
            message="저장된 분석 결과가 아직 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    result_path = _safe_result_path(settings.workspace_root, record.result_path)
    if not result_path.exists():
        raise ApiError(
            code="analysis_result_file_missing",
            message="저장된 분석 결과 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    result_bytes = result_path.read_bytes()
    if hashlib.sha256(result_bytes).hexdigest() != record.result_sha256:
        raise ApiError(
            code="analysis_result_checksum_mismatch",
            message="저장된 분석 결과 파일이 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    try:
        return AnalysisResultEnvelope.model_validate_json(result_bytes)
    except ValidationError as exc:
        raise ApiError(
            code="analysis_result_envelope_invalid",
            message="저장된 분석 결과 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc


def request_analysis_run_cancellation(
    workspace_root: Path,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    record = get_analysis_run_record(workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if record.status in TERMINAL_STATES:
        raise ApiError(
            code="analysis_run_not_cancellable",
            message="이미 종료된 분석 실행은 취소 요청할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=record.status,
        )

    if record.status in CANCELLABLE_STATES:
        updated = update_analysis_run_status_record(
            workspace_root=workspace_root,
            analysis_id=str(analysis_id),
            status=AnalysisRunState.CANCEL_REQUESTED.value,
            updated_at=_utc_now(),
        )
        if updated is not None:
            record = updated

    return _to_response(workspace_root, record)


_METHOD_EXECUTION_HANDLERS: dict[str, MethodExecutionHandler] = build_method_execution_handlers(
    {
        "eda.descriptive": run_descriptive_analysis,
        "eda.graphical_summary": run_graphical_summary_analysis,
        "eda.normality": run_normality_analysis,
        "eda.equal_variances": run_equal_variances_analysis,
        "hypothesis.one_sample_t": run_one_sample_t_analysis,
        "hypothesis.paired_t": run_paired_t_analysis,
        "hypothesis.one_sample_wilcoxon": run_one_sample_wilcoxon_analysis,
        "hypothesis.two_sample_t": run_two_sample_t_analysis,
        "hypothesis.mann_whitney": run_mann_whitney_analysis,
        "hypothesis.kruskal_wallis": run_kruskal_wallis_analysis,
        "hypothesis.one_way_anova": run_one_way_anova_analysis,
        "hypothesis.equivalence_tost": run_equivalence_tost_analysis,
        "categorical.one_proportion": run_one_proportion_analysis,
        "categorical.two_proportion": run_two_proportion_analysis,
        "categorical.chi_square_association": run_chi_square_association_analysis,
        "regression.pearson": run_pearson_analysis,
        "regression.xy_correlation": run_xy_correlation_analysis,
        "regression.linear_model": run_linear_model_analysis,
        "quality.individuals_chart": run_individuals_chart_analysis,
        "quality.subgroup_chart": run_subgroup_chart_analysis,
        "quality.run_chart": run_run_chart_analysis,
        "quality.capability": run_capability_analysis,
        "quality.gage_rr": run_gage_rr_analysis,
        "quality.gage_run_chart": run_gage_run_chart_analysis,
    }
)


def _safe_result_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="analysis_result_path_invalid",
            message="저장된 분석 결과 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return workspace_root / relative_path


def _to_response(workspace_root: Path, record: AnalysisRunRecord) -> AnalysisRunStatusResponse:
    config_schema_version = _config_schema_version(record.config_json)
    artifact_count = count_analysis_artifact_records(workspace_root, record.analysis_id)
    return AnalysisRunStatusResponse(
        analysis_id=UUID(record.analysis_id),
        method_id=record.method_id,
        method_version=record.method_version,
        dataset_version_id=None
        if record.dataset_version_id is None
        else UUID(record.dataset_version_id),
        status=AnalysisRunState(record.status),
        config_schema_version=config_schema_version,
        result_available=record.result_path is not None and record.result_sha256 is not None,
        artifact_count=artifact_count,
        stale=record.stale,
        created_at=record.created_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
    )


def _config_schema_version(config_json: str) -> int:
    try:
        payload = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    if not isinstance(payload, dict):
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int) or schema_version < 1:
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return schema_version
