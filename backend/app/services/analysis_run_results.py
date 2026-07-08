import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import status
from pydantic import ValidationError

from app.api.v1.schemas.analyses import AnalysisResultEnvelope
from app.core.config import Settings
from app.core.errors import ApiError
from app.storage.metadata import AnalysisRunRecord, get_analysis_run_record


@dataclass(frozen=True)
class StoredAnalysisRunResult:
    record: AnalysisRunRecord
    envelope: AnalysisResultEnvelope


def get_analysis_run_result(
    settings: Settings,
    analysis_id: UUID,
) -> AnalysisResultEnvelope:
    return load_analysis_run_result(settings, analysis_id).envelope


def load_analysis_run_result(
    settings: Settings,
    analysis_id: UUID,
) -> StoredAnalysisRunResult:
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
        envelope = AnalysisResultEnvelope.model_validate_json(result_bytes)
    except ValidationError as exc:
        raise ApiError(
            code="analysis_result_envelope_invalid",
            message="저장된 분석 결과 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    return StoredAnalysisRunResult(record=record, envelope=envelope)


def _safe_result_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="analysis_result_path_invalid",
            message="저장된 분석 결과 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return workspace_root / relative_path


_load_analysis_run_result = load_analysis_run_result
