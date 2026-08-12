import csv
import hashlib
import io
import json
import os
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.analyses import (
    AnalysisResultCsvExportResponse,
    AnalysisResultEnvelope,
    AnalysisResultExportDeleteRequest,
    AnalysisResultExportDeleteResponse,
    AnalysisResultExportDeletionCounts,
    AnalysisResultExportDeletionPreflightResponse,
    AnalysisResultExportListItemResponse,
    AnalysisResultExportListResponse,
    AnalysisResultHtmlReportResponse,
    AnalysisResultJsonExportResponse,
    RegressionPredictionCsvExportResponse,
    RegressionPredictionResponse,
    RegressionPredictionRow,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.i18n.report_text import ReportLocale, report_text
from app.services.analysis_run_execution import canonical_json_bytes
from app.services.analysis_run_execution import utc_now as _utc_now
from app.services.analysis_run_results import get_analysis_run_result
from app.services.regression_models import (
    REGRESSION_PREDICTION_METHOD_ID,
    iter_regression_prediction_rows,
    validate_regression_prediction_consistency,
)
from app.storage.atomic import atomic_replace, atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisArtifactStorageConflict,
    delete_analysis_artifact_record,
    get_analysis_artifact_record,
    get_analysis_run_record,
    insert_analysis_artifact_record,
    list_analysis_artifact_records,
)

ANALYSIS_RESULT_JSON_EXPORT_SCHEMA_VERSION = 1
ANALYSIS_RESULT_JSON_EXPORT_KIND: Literal["analysis_result_json_export"] = (
    "analysis_result_json_export"
)
ANALYSIS_RESULT_JSON_EXPORT_FORMAT: Literal["analysis_result_json"] = "analysis_result_json"
ANALYSIS_RESULT_JSON_EXPORT_MEDIA_TYPE: Literal["application/json"] = "application/json"
ANALYSIS_RESULT_CSV_EXPORT_SCHEMA_VERSION = 1
ANALYSIS_RESULT_CSV_EXPORT_KIND: Literal["analysis_result_csv_export"] = (
    "analysis_result_csv_export"
)
ANALYSIS_RESULT_CSV_EXPORT_FORMAT: Literal["analysis_result_csv"] = "analysis_result_csv"
ANALYSIS_RESULT_CSV_EXPORT_MEDIA_TYPE: Literal["text/csv"] = "text/csv"
ANALYSIS_RESULT_CSV_COLUMNS = ("section", "path", "value")
ANALYSIS_RESULT_CSV_PREVIEW_ROW_LIMIT = 50
ANALYSIS_RESULT_HTML_REPORT_SCHEMA_VERSION = 3
ANALYSIS_RESULT_HTML_REPORT_KIND: Literal["analysis_result_html_report"] = (
    "analysis_result_html_report"
)
ANALYSIS_RESULT_HTML_REPORT_FORMAT: Literal["analysis_result_html_report"] = (
    "analysis_result_html_report"
)
ANALYSIS_RESULT_HTML_REPORT_MEDIA_TYPE: Literal["text/html"] = "text/html"
ANALYSIS_RESULT_HTML_REPORT_TITLE = "Statistical Twin Analysis Report"
REGRESSION_PREDICTION_CSV_EXPORT_SCHEMA_VERSION = 1
REGRESSION_PREDICTION_CSV_EXPORT_KIND: Literal["regression_prediction_csv_export"] = (
    "regression_prediction_csv_export"
)
REGRESSION_PREDICTION_CSV_EXPORT_FORMAT: Literal["regression_prediction_csv"] = (
    "regression_prediction_csv"
)
REGRESSION_PREDICTION_CSV_EXPORT_MEDIA_TYPE: Literal["text/csv"] = "text/csv"
REGRESSION_PREDICTION_CSV_COLUMNS = (
    "prediction_id",
    "model_id",
    "source_dataset_version_id",
    "target_dataset_version_id",
    "model_manifest_sha256",
    "target_schema_hash",
    "confidence_level",
    "row_index",
    "predicted_mean",
    "mean_ci_level",
    "mean_ci_lower",
    "mean_ci_upper",
    "prediction_interval_level",
    "prediction_interval_lower",
    "prediction_interval_upper",
    "warnings",
)

HYPOTHESIS_REPORT_SUMMARY_TYPES = {
    "one_sample_t_test",
    "paired_t_test",
    "one_sample_wilcoxon_signed_rank_test",
    "two_sample_t_test",
    "mann_whitney_u_test",
    "kruskal_wallis_test",
    "one_way_anova",
    "equivalence_tost",
}
CATEGORICAL_REPORT_SUMMARY_TYPES = {
    "one_proportion_test",
    "two_proportion_test",
    "chi_square_association",
}
REGRESSION_REPORT_SUMMARY_TYPES = {
    "pearson_correlation",
    "xy_correlation_matrix",
    "linear_model",
}
QUALITY_REPORT_SUMMARY_TYPES = {
    "attribute_control_chart",
    "individuals_chart",
    "subgroup_chart",
    "run_chart",
    "capability_analysis",
    "gage_rr",
    "gage_run_chart",
}
ANALYSIS_RESULT_EXPORT_DOWNLOAD_KINDS = {
    ANALYSIS_RESULT_JSON_EXPORT_KIND,
    ANALYSIS_RESULT_CSV_EXPORT_KIND,
    ANALYSIS_RESULT_HTML_REPORT_KIND,
    REGRESSION_PREDICTION_CSV_EXPORT_KIND,
}
ANALYSIS_RESULT_EXPORT_DELETION_PREFLIGHT_SCHEMA_VERSION: Literal[1] = 1
ANALYSIS_RESULT_EXPORT_DELETION_SCHEMA_VERSION: Literal[1] = 1
AnalysisResultExportKind = Literal[
    "analysis_result_json_export",
    "analysis_result_csv_export",
    "analysis_result_html_report",
    "regression_prediction_csv_export",
]
_ANALYSIS_EXPORT_QUARANTINE_PATTERN = re.compile(
    r"^\.delete-([0-9a-fA-F-]{36})-([0-9a-f]{32})\.quarantine$"
)


@dataclass(frozen=True)
class AnalysisResultExportDownload:
    content: bytes
    filename: str
    media_type: str
    sha256: str


@dataclass(frozen=True)
class AnalysisExportQuarantineRecovery:
    restored_file_count: int
    deleted_file_count: int
    pending_file_count: int


@dataclass(frozen=True)
class _AnalysisExportDeletionContext:
    artifact: AnalysisArtifactRecord
    analysis_updated_at: str
    analysis_stale: bool
    result_sha256: str | None
    export_path: Path
    file_bytes: int
    deletion_manifest_sha256: str


def analysis_export_expected_relative_path(
    analysis_id: str,
    export_id: str,
    artifact_kind: str,
) -> Path:
    return _analysis_export_relative_path(analysis_id, export_id, artifact_kind)


def analysis_export_expected_media_type(artifact_kind: str) -> str:
    return _analysis_export_expected_media_type(artifact_kind)


def get_analysis_result_export_deletion_preflight(
    settings: Settings,
    analysis_id: UUID,
    export_id: UUID,
) -> AnalysisResultExportDeletionPreflightResponse:
    context = _analysis_export_deletion_context(settings, analysis_id, export_id)
    return _analysis_export_deletion_preflight(analysis_id, export_id, context)


def delete_analysis_result_export(
    settings: Settings,
    analysis_id: UUID,
    export_id: UUID,
    body: AnalysisResultExportDeleteRequest,
) -> AnalysisResultExportDeleteResponse:
    if body.confirmation_analysis_id != analysis_id or body.confirmation_export_id != export_id:
        raise _analysis_export_deletion_confirmation_error()
    context = _analysis_export_deletion_context(settings, analysis_id, export_id)
    preflight = _analysis_export_deletion_preflight(analysis_id, export_id, context)
    if body.expected_deletion_manifest_sha256 != preflight.deletion_manifest_sha256:
        raise _analysis_export_deletion_confirmation_error()

    quarantine_path = context.export_path.with_name(f".delete-{export_id}-{uuid4().hex}.quarantine")
    try:
        os.replace(context.export_path, quarantine_path)
    except OSError as exc:
        raise ApiError(
            code="analysis_export_quarantine_failed",
            message="내보내기 파일을 안전한 삭제 대기 상태로 옮길 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc

    try:
        quarantined_file_matches = (
            not quarantine_path.is_symlink()
            and quarantine_path.is_file()
            and quarantine_path.stat().st_size == context.file_bytes
            and _file_sha256(quarantine_path) == context.artifact.sha256
        )
    except OSError:
        quarantined_file_matches = False
    if not quarantined_file_matches:
        _restore_quarantined_export(quarantine_path, context.export_path)
        raise ApiError(
            code="analysis_export_deletion_conflict",
            message="삭제 확인 이후 내보내기 파일이 변경되었습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    try:
        delete_analysis_artifact_record(
            settings.workspace_root,
            expected_artifact=context.artifact,
            expected_analysis_updated_at=context.analysis_updated_at,
            expected_analysis_stale=context.analysis_stale,
            expected_result_sha256=context.result_sha256,
        )
    except AnalysisArtifactStorageConflict as exc:
        _restore_quarantined_export(quarantine_path, context.export_path)
        code = (
            "analysis_export_not_found"
            if exc.code == "analysis_export_not_found"
            else "analysis_export_deletion_conflict"
        )
        raise ApiError(
            code=code,
            message="삭제 확인 이후 내보내기 소유 관계가 변경되었습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    except Exception:
        _restore_quarantined_export(quarantine_path, context.export_path)
        raise

    cleanup_status: Literal["deleted", "quarantined_pending_cleanup"] = "deleted"
    try:
        quarantine_path.unlink()
    except OSError:
        cleanup_status = "quarantined_pending_cleanup"

    return AnalysisResultExportDeleteResponse(
        deletion_schema_version=ANALYSIS_RESULT_EXPORT_DELETION_SCHEMA_VERSION,
        analysis_id=analysis_id,
        export_id=export_id,
        deletion_manifest_sha256=preflight.deletion_manifest_sha256,
        deleted_at=_utc_now(),
        deleted_counts=preflight.counts,
        cleanup_status=cleanup_status,
    )


def recover_analysis_export_quarantine_files(
    workspace_root: Path,
) -> AnalysisExportQuarantineRecovery:
    analyses_root = workspace_root / "workspaces" / "analyses"
    restored = 0
    deleted = 0
    pending = 0
    if not analyses_root.exists():
        return AnalysisExportQuarantineRecovery(0, 0, 0)
    for quarantine_path in analyses_root.glob("*/exports/.delete-*-*.quarantine"):
        match = _ANALYSIS_EXPORT_QUARANTINE_PATTERN.fullmatch(quarantine_path.name)
        try:
            analysis_id = UUID(quarantine_path.parent.parent.name)
            export_id = UUID(match.group(1)) if match is not None else None
        except ValueError:
            pending += 1
            continue
        if export_id is None or quarantine_path.is_symlink() or not quarantine_path.is_file():
            pending += 1
            continue
        artifact = get_analysis_artifact_record(
            workspace_root,
            str(analysis_id),
            str(export_id),
        )
        if artifact is None:
            try:
                quarantine_path.unlink()
                deleted += 1
            except OSError:
                pending += 1
            continue
        try:
            original_path = _safe_analysis_export_path(
                workspace_root,
                artifact.path,
                analysis_id=str(analysis_id),
                export_id=str(export_id),
                artifact_kind=artifact.kind,
            )
        except ApiError:
            pending += 1
            continue
        if original_path.exists():
            pending += 1
            continue
        try:
            if _file_sha256(quarantine_path) != artifact.sha256:
                pending += 1
                continue
        except OSError:
            pending += 1
            continue
        try:
            os.replace(quarantine_path, original_path)
            restored += 1
        except OSError:
            pending += 1
    return AnalysisExportQuarantineRecovery(restored, deleted, pending)


def list_analysis_result_exports(
    settings: Settings,
    analysis_id: UUID,
) -> AnalysisResultExportListResponse:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if record.method_id == REGRESSION_PREDICTION_METHOD_ID:
        validate_regression_prediction_consistency(
            settings,
            analysis_id,
            verify_rows=True,
        )

    artifacts = [
        artifact
        for artifact in list_analysis_artifact_records(settings.workspace_root, str(analysis_id))
        if artifact.kind in ANALYSIS_RESULT_EXPORT_DOWNLOAD_KINDS
    ]
    return AnalysisResultExportListResponse(
        analysis_id=analysis_id,
        exports=[
            AnalysisResultExportListItemResponse(
                export_id=UUID(artifact.artifact_id),
                analysis_id=analysis_id,
                artifact_kind=artifact.kind,
                media_type=artifact.media_type,
                sha256=artifact.sha256,
                created_at=artifact.created_at,
                download_url=(
                    f"/api/v1/analysis-runs/{analysis_id}/exports/"
                    f"{artifact.artifact_id}/download"
                ),
            )
            for artifact in artifacts
        ],
    )


def create_analysis_result_json_export(
    settings: Settings,
    analysis_id: UUID,
) -> AnalysisResultJsonExportResponse:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    result = get_analysis_run_result(settings, analysis_id)
    if record.result_sha256 is None:
        raise ApiError(
            code="analysis_result_not_available",
            message="저장된 분석 결과가 아직 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    export_id = uuid4()
    created_at = _utc_now()
    export_payload = {
        "schema_version": ANALYSIS_RESULT_JSON_EXPORT_SCHEMA_VERSION,
        "analysis_id": str(analysis_id),
        "format": ANALYSIS_RESULT_JSON_EXPORT_FORMAT,
        "media_type": ANALYSIS_RESULT_JSON_EXPORT_MEDIA_TYPE,
        "source_result_sha256": record.result_sha256,
        "stale": record.stale,
        "created_at": created_at,
        "result": result.model_dump(mode="json"),
    }
    export_bytes = canonical_json_bytes(export_payload)
    export_sha256 = hashlib.sha256(export_bytes).hexdigest()

    relative_path = _result_json_export_relative_path(str(analysis_id), str(export_id))
    export_path = settings.workspace_root / relative_path
    atomic_write_bytes(export_path, export_bytes)

    try:
        insert_analysis_artifact_record(
            settings.workspace_root,
            AnalysisArtifactRecord(
                artifact_id=str(export_id),
                analysis_id=str(analysis_id),
                kind=ANALYSIS_RESULT_JSON_EXPORT_KIND,
                path=relative_path.as_posix(),
                sha256=hashlib.sha256(export_bytes).hexdigest(),
                media_type=ANALYSIS_RESULT_JSON_EXPORT_MEDIA_TYPE,
                created_at=created_at,
            ),
        )
    except Exception:
        export_path.unlink(missing_ok=True)
        raise

    return AnalysisResultJsonExportResponse(
        schema_version=ANALYSIS_RESULT_JSON_EXPORT_SCHEMA_VERSION,
        export_id=export_id,
        analysis_id=analysis_id,
        format=ANALYSIS_RESULT_JSON_EXPORT_FORMAT,
        artifact_kind=ANALYSIS_RESULT_JSON_EXPORT_KIND,
        media_type=ANALYSIS_RESULT_JSON_EXPORT_MEDIA_TYPE,
        sha256=export_sha256,
        size_bytes=len(export_bytes),
        source_result_sha256=record.result_sha256,
        stale=record.stale,
        created_at=created_at,
        result=result,
    )


def create_analysis_result_csv_export(
    settings: Settings,
    analysis_id: UUID,
) -> AnalysisResultCsvExportResponse:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    result = get_analysis_run_result(settings, analysis_id)
    if record.result_sha256 is None:
        raise ApiError(
            code="analysis_result_not_available",
            message="저장된 분석 결과가 아직 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    export_id = uuid4()
    created_at = _utc_now()
    rows = _analysis_result_csv_rows(result)
    export_bytes = _analysis_result_csv_bytes(rows)
    export_sha256 = hashlib.sha256(export_bytes).hexdigest()

    relative_path = _result_csv_export_relative_path(str(analysis_id), str(export_id))
    export_path = settings.workspace_root / relative_path
    atomic_write_bytes(export_path, export_bytes)

    try:
        insert_analysis_artifact_record(
            settings.workspace_root,
            AnalysisArtifactRecord(
                artifact_id=str(export_id),
                analysis_id=str(analysis_id),
                kind=ANALYSIS_RESULT_CSV_EXPORT_KIND,
                path=relative_path.as_posix(),
                sha256=export_sha256,
                media_type=ANALYSIS_RESULT_CSV_EXPORT_MEDIA_TYPE,
                created_at=created_at,
            ),
        )
    except Exception:
        export_path.unlink(missing_ok=True)
        raise

    return AnalysisResultCsvExportResponse(
        schema_version=ANALYSIS_RESULT_CSV_EXPORT_SCHEMA_VERSION,
        export_id=export_id,
        analysis_id=analysis_id,
        format=ANALYSIS_RESULT_CSV_EXPORT_FORMAT,
        artifact_kind=ANALYSIS_RESULT_CSV_EXPORT_KIND,
        media_type=ANALYSIS_RESULT_CSV_EXPORT_MEDIA_TYPE,
        sha256=export_sha256,
        size_bytes=len(export_bytes),
        source_result_sha256=record.result_sha256,
        stale=record.stale,
        created_at=created_at,
        columns=list(ANALYSIS_RESULT_CSV_COLUMNS),
        row_count=len(rows),
        preview_rows=rows[:ANALYSIS_RESULT_CSV_PREVIEW_ROW_LIMIT],
    )


def create_regression_prediction_csv_export(
    settings: Settings,
    prediction_id: UUID,
) -> RegressionPredictionCsvExportResponse:
    record = get_analysis_run_record(settings.workspace_root, str(prediction_id))
    if record is None or record.method_id != REGRESSION_PREDICTION_METHOD_ID:
        raise ApiError(
            code="regression_prediction_not_found",
            message="요청한 회귀 예측 결과를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    consistency = validate_regression_prediction_consistency(
        settings,
        prediction_id,
        verify_rows=False,
    )
    if record.result_sha256 is None:
        raise ApiError(
            code="analysis_result_not_available",
            message="저장된 분석 결과가 아직 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    prediction = consistency.prediction

    export_id = uuid4()
    created_at = _utc_now()
    relative_path = _prediction_csv_export_relative_path(str(prediction_id), str(export_id))
    export_path = settings.workspace_root / relative_path
    preview_rows: list[list[str]] = []
    row_count = 0

    def write_export(temp_path: Path) -> None:
        nonlocal row_count
        with temp_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(
                [_sanitize_csv_cell(column) for column in REGRESSION_PREDICTION_CSV_COLUMNS],
            )
            for row in iter_regression_prediction_rows(
                settings,
                prediction_id,
                consistency=consistency,
            ):
                export_row = _regression_prediction_csv_row(prediction, row)
                writer.writerow(export_row)
                if len(preview_rows) < ANALYSIS_RESULT_CSV_PREVIEW_ROW_LIMIT:
                    preview_rows.append(export_row)
                row_count += 1
            handle.flush()
            os.fsync(handle.fileno())

    atomic_replace(export_path, write_export)
    export_sha256 = _file_sha256(export_path)
    size_bytes = export_path.stat().st_size
    try:
        insert_analysis_artifact_record(
            settings.workspace_root,
            AnalysisArtifactRecord(
                artifact_id=str(export_id),
                analysis_id=str(prediction_id),
                kind=REGRESSION_PREDICTION_CSV_EXPORT_KIND,
                path=relative_path.as_posix(),
                sha256=export_sha256,
                media_type=REGRESSION_PREDICTION_CSV_EXPORT_MEDIA_TYPE,
                created_at=created_at,
            ),
        )
    except Exception:
        export_path.unlink(missing_ok=True)
        raise

    return RegressionPredictionCsvExportResponse(
        schema_version=REGRESSION_PREDICTION_CSV_EXPORT_SCHEMA_VERSION,
        export_id=export_id,
        prediction_id=prediction_id,
        format=REGRESSION_PREDICTION_CSV_EXPORT_FORMAT,
        artifact_kind=REGRESSION_PREDICTION_CSV_EXPORT_KIND,
        media_type=REGRESSION_PREDICTION_CSV_EXPORT_MEDIA_TYPE,
        sha256=export_sha256,
        size_bytes=size_bytes,
        source_result_sha256=record.result_sha256,
        stale=record.stale,
        created_at=created_at,
        columns=list(REGRESSION_PREDICTION_CSV_COLUMNS),
        row_count=row_count,
        preview_rows=preview_rows,
    )


def create_analysis_result_html_report_export(
    settings: Settings,
    analysis_id: UUID,
    locale: Literal["en", "ko"] = "en",
) -> AnalysisResultHtmlReportResponse:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    result = get_analysis_run_result(settings, analysis_id)
    if record.result_sha256 is None:
        raise ApiError(
            code="analysis_result_not_available",
            message="저장된 분석 결과가 아직 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    export_id = uuid4()
    created_at = _utc_now()
    rows = _analysis_result_csv_rows(result)
    export_bytes = _analysis_result_html_report_bytes(
        result=result,
        analysis_id=analysis_id,
        source_result_sha256=record.result_sha256,
        stale=record.stale,
        created_at=created_at,
        rows=rows,
        locale=locale,
    )
    export_sha256 = hashlib.sha256(export_bytes).hexdigest()

    relative_path = _result_html_report_relative_path(str(analysis_id), str(export_id))
    export_path = settings.workspace_root / relative_path
    atomic_write_bytes(export_path, export_bytes)

    try:
        insert_analysis_artifact_record(
            settings.workspace_root,
            AnalysisArtifactRecord(
                artifact_id=str(export_id),
                analysis_id=str(analysis_id),
                kind=ANALYSIS_RESULT_HTML_REPORT_KIND,
                path=relative_path.as_posix(),
                sha256=export_sha256,
                media_type=ANALYSIS_RESULT_HTML_REPORT_MEDIA_TYPE,
                created_at=created_at,
            ),
        )
    except Exception:
        export_path.unlink(missing_ok=True)
        raise

    return AnalysisResultHtmlReportResponse(
        schema_version=ANALYSIS_RESULT_HTML_REPORT_SCHEMA_VERSION,
        export_id=export_id,
        analysis_id=analysis_id,
        format=ANALYSIS_RESULT_HTML_REPORT_FORMAT,
        artifact_kind=ANALYSIS_RESULT_HTML_REPORT_KIND,
        media_type=ANALYSIS_RESULT_HTML_REPORT_MEDIA_TYPE,
        sha256=export_sha256,
        size_bytes=len(export_bytes),
        source_result_sha256=record.result_sha256,
        stale=record.stale,
        created_at=created_at,
        title=report_text(
            locale,
            en=ANALYSIS_RESULT_HTML_REPORT_TITLE,
            ko="Statistical Twin 분석 보고서",
        ),
        section_count=len(rows),
        report_locale=locale,
    )


def get_analysis_result_export_download(
    settings: Settings,
    analysis_id: UUID,
    export_id: UUID,
) -> AnalysisResultExportDownload:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is not None and record.method_id == REGRESSION_PREDICTION_METHOD_ID:
        validate_regression_prediction_consistency(
            settings,
            analysis_id,
            verify_rows=True,
        )
    artifact = get_analysis_artifact_record(
        settings.workspace_root,
        str(analysis_id),
        str(export_id),
    )
    if artifact is None or artifact.kind not in ANALYSIS_RESULT_EXPORT_DOWNLOAD_KINDS:
        raise ApiError(
            code="analysis_export_not_found",
            message="요청한 분석 결과 내보내기 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if artifact.media_type != _analysis_export_expected_media_type(artifact.kind):
        raise ApiError(
            code="analysis_export_metadata_invalid",
            message="저장된 분석 결과 내보내기 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    export_path = _safe_analysis_export_path(
        settings.workspace_root,
        artifact.path,
        analysis_id=str(analysis_id),
        export_id=str(export_id),
        artifact_kind=artifact.kind,
    )
    if not export_path.exists() or not export_path.is_file():
        raise ApiError(
            code="analysis_export_file_missing",
            message="저장된 분석 결과 내보내기 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    export_bytes = export_path.read_bytes()
    if hashlib.sha256(export_bytes).hexdigest() != artifact.sha256:
        raise ApiError(
            code="analysis_export_checksum_mismatch",
            message="저장된 분석 결과 내보내기 파일이 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    return AnalysisResultExportDownload(
        content=export_bytes,
        filename=_analysis_export_download_filename(analysis_id, export_id, artifact.kind),
        media_type=artifact.media_type,
        sha256=artifact.sha256,
    )


def _safe_analysis_export_path(
    workspace_root: Path,
    stored_path: str,
    *,
    analysis_id: str,
    export_id: str,
    artifact_kind: str,
) -> Path:
    relative_path = Path(stored_path)
    expected_path = _analysis_export_relative_path(analysis_id, export_id, artifact_kind)
    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.as_posix() != expected_path.as_posix()
    ):
        raise ApiError(
            code="analysis_export_path_invalid",
            message="저장된 분석 결과 내보내기 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return workspace_root / relative_path


def _analysis_export_relative_path(
    analysis_id: str,
    export_id: str,
    artifact_kind: str,
) -> Path:
    if artifact_kind == ANALYSIS_RESULT_JSON_EXPORT_KIND:
        return _result_json_export_relative_path(analysis_id, export_id)
    if artifact_kind == ANALYSIS_RESULT_CSV_EXPORT_KIND:
        return _result_csv_export_relative_path(analysis_id, export_id)
    if artifact_kind == ANALYSIS_RESULT_HTML_REPORT_KIND:
        return _result_html_report_relative_path(analysis_id, export_id)
    if artifact_kind == REGRESSION_PREDICTION_CSV_EXPORT_KIND:
        return _prediction_csv_export_relative_path(analysis_id, export_id)
    raise ApiError(
        code="analysis_export_not_found",
        message="요청한 분석 결과 내보내기 파일을 찾을 수 없습니다.",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def _analysis_export_expected_media_type(artifact_kind: str) -> str:
    if artifact_kind == ANALYSIS_RESULT_JSON_EXPORT_KIND:
        return ANALYSIS_RESULT_JSON_EXPORT_MEDIA_TYPE
    if artifact_kind in {
        ANALYSIS_RESULT_CSV_EXPORT_KIND,
        REGRESSION_PREDICTION_CSV_EXPORT_KIND,
    }:
        return ANALYSIS_RESULT_CSV_EXPORT_MEDIA_TYPE
    if artifact_kind == ANALYSIS_RESULT_HTML_REPORT_KIND:
        return ANALYSIS_RESULT_HTML_REPORT_MEDIA_TYPE
    raise ApiError(
        code="analysis_export_not_found",
        message="요청한 분석 결과 내보내기 파일을 찾을 수 없습니다.",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def _analysis_export_deletion_context(
    settings: Settings,
    analysis_id: UUID,
    export_id: UUID,
) -> _AnalysisExportDeletionContext:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if record.method_id == REGRESSION_PREDICTION_METHOD_ID:
        validate_regression_prediction_consistency(settings, analysis_id, verify_rows=True)
    artifact = get_analysis_artifact_record(
        settings.workspace_root,
        str(analysis_id),
        str(export_id),
    )
    if artifact is None or artifact.kind not in ANALYSIS_RESULT_EXPORT_DOWNLOAD_KINDS:
        raise ApiError(
            code="analysis_export_not_found",
            message="요청한 분석 결과 내보내기 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if artifact.media_type != _analysis_export_expected_media_type(artifact.kind):
        raise ApiError(
            code="analysis_export_metadata_invalid",
            message="저장된 분석 결과 내보내기 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    export_path = _safe_analysis_export_path(
        settings.workspace_root,
        artifact.path,
        analysis_id=str(analysis_id),
        export_id=str(export_id),
        artifact_kind=artifact.kind,
    )
    if export_path.is_symlink():
        raise ApiError(
            code="analysis_export_path_invalid",
            message="저장된 분석 결과 내보내기 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    if not export_path.exists() or not export_path.is_file():
        raise ApiError(
            code="analysis_export_file_missing",
            message="저장된 분석 결과 내보내기 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    file_bytes = export_path.stat().st_size
    if _file_sha256(export_path) != artifact.sha256:
        raise ApiError(
            code="analysis_export_checksum_mismatch",
            message="저장된 분석 결과 내보내기 파일이 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    manifest_sha256 = hashlib.sha256(
        canonical_json_bytes(
            {
                "preflight_schema_version": (
                    ANALYSIS_RESULT_EXPORT_DELETION_PREFLIGHT_SCHEMA_VERSION
                ),
                "analysis_id": str(analysis_id),
                "analysis_method_id": record.method_id,
                "analysis_method_version": record.method_version,
                "analysis_updated_at": record.updated_at,
                "analysis_stale": record.stale,
                "analysis_result_sha256": record.result_sha256,
                "export_id": str(export_id),
                "artifact_kind": artifact.kind,
                "artifact_path": artifact.path,
                "artifact_sha256": artifact.sha256,
                "artifact_media_type": artifact.media_type,
                "artifact_created_at": artifact.created_at,
                "file_bytes": file_bytes,
            }
        )
    ).hexdigest()
    return _AnalysisExportDeletionContext(
        artifact=artifact,
        analysis_updated_at=record.updated_at,
        analysis_stale=record.stale,
        result_sha256=record.result_sha256,
        export_path=export_path,
        file_bytes=file_bytes,
        deletion_manifest_sha256=manifest_sha256,
    )


def _analysis_export_deletion_preflight(
    analysis_id: UUID,
    export_id: UUID,
    context: _AnalysisExportDeletionContext,
) -> AnalysisResultExportDeletionPreflightResponse:
    return AnalysisResultExportDeletionPreflightResponse(
        preflight_schema_version=ANALYSIS_RESULT_EXPORT_DELETION_PREFLIGHT_SCHEMA_VERSION,
        analysis_id=analysis_id,
        export_id=export_id,
        artifact_kind=cast(AnalysisResultExportKind, context.artifact.kind),
        media_type=context.artifact.media_type,
        sha256=context.artifact.sha256,
        counts=AnalysisResultExportDeletionCounts(
            metadata_record_count=1,
            file_count=1,
            file_bytes=context.file_bytes,
        ),
        deletion_manifest_sha256=context.deletion_manifest_sha256,
    )


def _analysis_export_deletion_confirmation_error() -> ApiError:
    return ApiError(
        code="analysis_export_deletion_confirmation_mismatch",
        message="내보내기 삭제 확인 대상 또는 영향 정보가 변경되었습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _restore_quarantined_export(
    quarantine_path: Path,
    export_path: Path,
) -> None:
    if export_path.exists():
        raise ApiError(
            code="analysis_export_restore_failed",
            message="삭제 실패 후 내보내기 파일을 안전하게 원위치로 복구하지 못했습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    try:
        os.replace(quarantine_path, export_path)
    except OSError as restore_error:
        raise ApiError(
            code="analysis_export_restore_failed",
            message="삭제 실패 후 내보내기 파일을 원위치로 복구하지 못했습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from restore_error


def _analysis_export_download_filename(
    analysis_id: UUID,
    export_id: UUID,
    artifact_kind: str,
) -> str:
    if artifact_kind == ANALYSIS_RESULT_JSON_EXPORT_KIND:
        suffix = "json"
    elif artifact_kind in {
        ANALYSIS_RESULT_CSV_EXPORT_KIND,
        REGRESSION_PREDICTION_CSV_EXPORT_KIND,
    }:
        suffix = "csv"
    else:
        return f"statistical-twin-analysis-{analysis_id}-export-{export_id}.html"
    return f"datalab-analysis-{analysis_id}-export-{export_id}.{suffix}"


def _result_json_export_relative_path(analysis_id: str, export_id: str) -> Path:
    return (
        Path("workspaces")
        / "analyses"
        / analysis_id
        / "exports"
        / f"{export_id}.analysis-result.json"
    )


def _result_csv_export_relative_path(analysis_id: str, export_id: str) -> Path:
    return (
        Path("workspaces")
        / "analyses"
        / analysis_id
        / "exports"
        / f"{export_id}.analysis-result.csv"
    )


def _result_html_report_relative_path(analysis_id: str, export_id: str) -> Path:
    return (
        Path("workspaces")
        / "analyses"
        / analysis_id
        / "exports"
        / f"{export_id}.analysis-result.html"
    )


def _prediction_csv_export_relative_path(prediction_id: str, export_id: str) -> Path:
    return (
        Path("workspaces")
        / "analyses"
        / prediction_id
        / "exports"
        / f"{export_id}.regression-prediction.csv"
    )


def _regression_prediction_csv_row(
    prediction: RegressionPredictionResponse,
    row: RegressionPredictionRow,
) -> list[str]:
    mean_interval = row.mean_confidence_interval
    prediction_interval = row.prediction_interval
    values = [
        str(prediction.prediction_id),
        str(prediction.model_id),
        str(prediction.source_dataset_version_id),
        str(prediction.target_dataset_version_id),
        prediction.model_manifest_sha256,
        prediction.target_schema_hash,
        str(prediction.confidence_level),
        str(row.row_index),
        str(row.predicted_mean),
        "" if mean_interval is None else str(mean_interval.level),
        "" if mean_interval is None else str(mean_interval.lower),
        "" if mean_interval is None else str(mean_interval.upper),
        "" if prediction_interval is None else str(prediction_interval.level),
        "" if prediction_interval is None else str(prediction_interval.lower),
        "" if prediction_interval is None else str(prediction_interval.upper),
        ";".join(row.warnings),
    ]
    return [_sanitize_csv_cell(value) for value in values]


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _analysis_result_csv_rows(result: AnalysisResultEnvelope) -> list[list[str]]:
    payload = result.model_dump(mode="json")
    rows: list[list[str]] = []
    for path, value in _flatten_csv_values(payload):
        section = _csv_section(path)
        rows.append(
            [
                _sanitize_csv_cell(section),
                _sanitize_csv_cell(path),
                _sanitize_csv_cell(_csv_value(value)),
            ],
        )
    return rows


def _analysis_result_csv_bytes(rows: list[list[str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([_sanitize_csv_cell(column) for column in ANALYSIS_RESULT_CSV_COLUMNS])
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def _flatten_csv_values(value: Any, path: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        if not value:
            return [(path, {})]
        rows: list[tuple[str, Any]] = []
        for key, child in value.items():
            child_path = key if not path else f"{path}.{key}"
            rows.extend(_flatten_csv_values(child, child_path))
        return rows
    if isinstance(value, list):
        if not value:
            return [(path, [])]
        rows = []
        for index, child in enumerate(value):
            rows.extend(_flatten_csv_values(child, f"{path}[{index}]"))
        return rows
    return [(path, value)]


def _csv_section(path: str) -> str:
    if not path:
        return "root"
    return path.split(".", maxsplit=1)[0].split("[", maxsplit=1)[0]


def _csv_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _sanitize_csv_cell(value: str) -> str:
    stripped = value.lstrip(" \t\r\n")
    if stripped.startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return f"'{value}"
    return value


def _analysis_result_html_report_bytes(
    result: AnalysisResultEnvelope,
    analysis_id: UUID,
    source_result_sha256: str,
    stale: bool,
    created_at: str,
    rows: list[list[str]],
    locale: ReportLocale = "en",
) -> bytes:
    del rows
    warning_markup = "\n".join(
        "<li>"
        f"<strong>{_html_text(warning.code)}</strong>: "
        f"{_html_text(warning.message if locale == 'ko' else 'Review this analysis warning.')} "
        f"<span>{_html_text(warning.severity)}</span>"
        "</li>"
        for warning in result.warnings
    )
    if not warning_markup:
        warning_markup = report_text(
            locale,
            en="<li>No saved warnings.</li>",
            ko="<li>저장된 경고가 없습니다.</li>",
        )
    method_specific_markup = _analysis_result_method_specific_report_section(result, locale)
    method_label = _analysis_method_report_label(result.method_id, locale)
    result_payload = result.result if isinstance(result.result, dict) else {}
    input_settings = _report_input_settings(result_payload, locale)
    raw_result = _html_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
    )
    row_count_included = _report_cell_value(result.provenance.row_count_included)
    row_count_total = _report_cell_value(result.provenance.row_count_total)
    stale_label = report_text(
        locale,
        en="Review required because the source changed" if stale else "Current source",
        ko="원본 변경으로 확인 필요" if stale else "현재 원본 기준",
    )
    report_heading = report_text(
        locale,
        en=f"{method_label} Results Report",
        ko=f"{method_label} 결과 보고서",
    )
    summary_heading = report_text(locale, en="Analysis Summary", ko="분석 요약")
    method_heading = report_text(locale, en="Analysis Method", ko="분석 방법")
    completed_heading = report_text(locale, en="Completed", ko="분석 완료")
    rows_heading = report_text(locale, en="Rows Used / Total Rows", ko="사용 행 / 전체 행")
    source_heading = report_text(locale, en="Source Status", ko="원본 상태")
    settings_heading = report_text(locale, en="Inputs and Settings", ko="입력 및 설정")
    results_heading = report_text(locale, en="Key Results", ko="핵심 결과")
    warning_heading = report_text(
        locale,
        en="Interpretation Notes and Warnings",
        ko="해석 시 주의사항과 경고",
    )
    note = report_text(
        locale,
        en=(
            "This report reconstructs the saved analysis result. "
            "It does not reread the source data or rerun the analysis."
        ),
        ko=(
            "이 보고서는 저장된 분석 결과를 재구성한 문서입니다. "
            "원자료를 다시 읽거나 분석을 재실행하지 않았습니다."
        ),
    )
    technical_heading = report_text(locale, en="Technical Information", ko="기술 정보")
    raw_heading = report_text(
        locale,
        en="Machine-readable Source Result JSON",
        ko="기계 판독용 원본 result JSON",
    )
    report_title = report_text(
        locale,
        en=ANALYSIS_RESULT_HTML_REPORT_TITLE,
        ko="Statistical Twin 분석 보고서",
    )

    html = f"""<!doctype html>
<html lang="{locale}">
<head>
  <meta charset="utf-8">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src 'unsafe-inline'"
  >
  <title>{_html_text(report_title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; color: #172033; line-height: 1.5; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px; }}
    h1, h2, h3 {{ margin: 0 0 12px; }}
    h2 {{ margin-top: 28px; padding-bottom: 6px; border-bottom: 2px solid #034da2; }}
    .report-kicker {{ color: #034da2; font-weight: 700; }}
    .report-summary {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .summary-item {{ border: 1px solid #cfd8e6; padding: 10px; }}
    .summary-item span {{ display: block; color: #52647a; font-size: 12px; }}
    .summary-item strong {{ display: block; margin-top: 3px; }}
    .meta {{
      display: grid;
      grid-template-columns: max-content 1fr;
      gap: 6px 12px;
      margin: 16px 0 24px;
    }}
    .meta dt {{ font-weight: 700; }}
    .meta dd {{ margin: 0; overflow-wrap: anywhere; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #d8dde5; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f2f5f9; }}
    code {{ font-family: Consolas, monospace; font-size: 12px; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f4f6f9; padding: 12px; }}
    .report-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .report-card {{ border: 1px solid #cfd8e6; padding: 12px; min-width: 0; break-inside: avoid; }}
    .report-card-full {{ grid-column: 1 / -1; }}
    svg {{ width: 100%; height: auto; }}
    .axis {{ stroke: #51647b; stroke-width: 1; }}
    .normal-fit {{ fill: none; stroke: #b42318; stroke-width: 2; stroke-dasharray: 6 3; }}
    .histogram-bar {{ fill: #79a7d8; stroke: #315d8c; }}
    .interval {{ stroke: #2166ac; stroke-width: 2; }}
    .estimate {{ fill: #034da2; }}
    details {{ margin-top: 18px; }}
    summary {{ cursor: pointer; font-weight: 700; }}
    .report-note {{ border-left: 4px solid #d99a00; background: #fff8e8; padding: 10px 12px; }}
    @media (max-width: 760px) {{
      main {{ padding: 18px; }}
      .report-summary, .report-grid {{ grid-template-columns: 1fr; }}
      .report-card-full {{ grid-column: auto; }}
      .table-wrap {{ overflow-x: auto; }}
      table {{ min-width: 620px; }}
    }}
    @media print {{
      body {{ color: #000; }} main {{ max-width: none; padding: 0; }}
      details:not([open]) {{ display: none; }}
      .report-card {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
<main>
  <p class="report-kicker">{_html_text(report_title)}</p>
  <h1>{_html_text(report_heading)}</h1>
  <h2>{_html_text(summary_heading)}</h2>
  <div class="report-summary">
    <div class="summary-item">
      <span>{_html_text(method_heading)}</span><strong>{_html_text(method_label)}</strong>
    </div>
    <div class="summary-item">
      <span>{_html_text(completed_heading)}</span><strong>{_html_text(created_at)}</strong>
    </div>
    <div class="summary-item">
      <span>{_html_text(rows_heading)}</span>
      <strong>{_html_text(row_count_included)} / {_html_text(row_count_total)}</strong>
    </div>
    <div class="summary-item">
      <span>{_html_text(source_heading)}</span><strong>{_html_text(stale_label)}</strong>
    </div>
  </div>
  <h2>{_html_text(settings_heading)}</h2>
  {input_settings}
  <h2>{_html_text(results_heading)}</h2>
{method_specific_markup}
  <h2>{_html_text(warning_heading)}</h2>
  <ul>{warning_markup}</ul>
  <p class="report-note">
    {_html_text(note)}
  </p>
  <details>
    <summary>{_html_text(technical_heading)}</summary>
    <dl class="meta">
      <dt>Analysis ID</dt><dd>{_html_text(str(analysis_id))}</dd>
      <dt>Method</dt><dd>{_html_text(result.method_id)} v{_html_text(result.method_version)}</dd>
      <dt>Dataset Version</dt><dd>{_html_text(str(result.dataset_version_id))}</dd>
      <dt>Source Result SHA-256</dt><dd><code>{_html_text(source_result_sha256)}</code></dd>
      <dt>Status</dt><dd>{_html_text(result.status)}</dd>
    </dl>
  </details>
  <details>
    <summary>{_html_text(raw_heading)}</summary>
    <pre>{raw_result}</pre>
  </details>
</main>
</body>
</html>
"""
    return html.encode("utf-8")


def _html_text(value: object) -> str:
    return escape(str(value), quote=True)


def _analysis_method_report_label(method_id: str, locale: ReportLocale = "en") -> str:
    labels = {
        "eda.descriptive": ("Descriptive Statistics", "기술통계"),
        "eda.graphical_summary": ("Graphical Summary", "그래프 요약"),
        "eda.normality": ("Normality Test", "정규성 검정"),
        "eda.equal_variances": ("Test for Equal Variances", "등분산 검정"),
        "regression.linear_model": ("Fit Regression Model", "회귀모형 적합"),
    }
    label = labels.get(method_id)
    if label is None:
        return method_id
    return label[1] if locale == "ko" else label[0]


def _report_input_settings(payload: dict[str, object], locale: ReportLocale = "en") -> str:
    settings = []
    for key, label_en, label_ko in (
        ("missing_policy", "Missing-data handling", "결측 처리"),
        ("confidence_level", "Confidence level", "신뢰수준"),
        ("alpha", "Significance level", "유의수준"),
        ("quartile_method", "Quartile method", "사분위수 방법"),
    ):
        if key in payload:
            label = label_ko if locale == "ko" else label_en
            settings.append(
                f"<div><dt>{_html_text(label)}</dt><dd>{_html_text(_report_cell_value(payload[key]))}</dd></div>"
            )
    if not settings:
        return report_text(
            locale,
            en="<p>No separate run-settings summary is stored with this result.</p>",
            ko="<p>저장된 결과에 별도 실행 설정 요약이 없습니다.</p>",
        )
    return f'<dl class="meta">{"".join(settings)}</dl>'


def _analysis_result_method_specific_report_section(
    result: AnalysisResultEnvelope, locale: ReportLocale = "en"
) -> str:
    payload = result.result
    if not isinstance(payload, dict):
        return ""
    summary_type = payload.get("summary_type")
    renderers = {
        "descriptive_statistics": _descriptive_statistics_report_section,
        "graphical_summary": _graphical_summary_report_section_v2,
        "normality_test": _normality_report_section,
        "equal_variances_test": _equal_variances_report_section_v2,
    }
    renderer = renderers.get(str(summary_type))
    if renderer is not None:
        return renderer(payload, locale)
    if summary_type in HYPOTHESIS_REPORT_SUMMARY_TYPES:
        return _hypothesis_report_section(payload, str(summary_type), locale)
    if summary_type in CATEGORICAL_REPORT_SUMMARY_TYPES:
        return _categorical_report_section(payload, str(summary_type), locale)
    if summary_type in REGRESSION_REPORT_SUMMARY_TYPES:
        return _regression_report_section(payload, str(summary_type), locale)
    if summary_type in QUALITY_REPORT_SUMMARY_TYPES:
        return _quality_report_section(payload, str(summary_type), locale)
    return ""


def _descriptive_statistics_report_section(
    payload: dict[str, object], locale: ReportLocale = "en"
) -> str:
    columns = payload.get("columns")
    if not isinstance(columns, list):
        return ""

    row_markup = "\n".join(
        _descriptive_statistics_report_row(column) for column in columns if isinstance(column, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Descriptive Statistics Summary", ko="기술통계 요약")
    description = report_text(
        locale,
        en="Values from the saved result are shown without recalculation.",
        ko="저장된 분석 결과의 기술통계 값을 재계산 없이 표시합니다.",
    )
    return f"""
  <h2>{_html_text(heading)}</h2>
  <p>{_html_text(description)}</p>
  <table>
    <thead>
      <tr>
        <th>Column</th>
        <th>N total</th>
        <th>N used</th>
        <th>Missing</th>
        <th>Non-numeric</th>
        <th>Mean</th>
        <th>Std</th>
        <th>Min</th>
        <th>Q1</th>
        <th>Median</th>
        <th>Q3</th>
        <th>Max</th>
        <th>Warnings</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _descriptive_statistics_report_row(column: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(column.get('display_name')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_total')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_used')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_missing')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_non_numeric')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('mean')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('std')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('min')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('q1')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('median')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('q3')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('max')))}</td>"
        f"<td>{_html_text(_report_warning_text(column.get('warnings')))}</td>"
        "</tr>"
    )


def _graphical_summary_report_section(payload: dict[str, object]) -> str:
    columns = payload.get("columns")
    if not isinstance(columns, list):
        return ""

    row_markup = "\n".join(
        _graphical_summary_report_row(column) for column in columns if isinstance(column, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>그래프 요약</h2>
  <p>저장된 그래프 요약 payload의 수치 요약과 시각화 포인트 수를 재계산 없이 표시합니다.</p>
  <table>
    <thead>
      <tr>
        <th>Column</th>
        <th>N total</th>
        <th>N used</th>
        <th>Missing</th>
        <th>Non-numeric</th>
        <th>Min</th>
        <th>Q1</th>
        <th>Median</th>
        <th>Q3</th>
        <th>Max</th>
        <th>Histogram bins</th>
        <th>Outliers</th>
        <th>Q-Q points</th>
        <th>ECDF points</th>
        <th>Warnings</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _graphical_summary_report_row(column: dict[object, object]) -> str:
    histogram = column.get("histogram")
    boxplot = column.get("boxplot")
    qq_plot = column.get("qq_plot")
    ecdf = column.get("ecdf")
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(column.get('display_name')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_total')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_used')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_missing')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_non_numeric')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('min')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('q1')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('median')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('q3')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('max')))}</td>"
        f"<td>{_html_text(_report_cell_value(_report_nested_value(histogram, 'bin_count')))}</td>"
        f"<td>{_html_text(_report_cell_value(_report_nested_value(boxplot, 'outlier_count')))}</td>"
        f"<td>{_html_text(_report_cell_value(_report_point_count(qq_plot)))}</td>"
        f"<td>{_html_text(_report_cell_value(_report_point_count(ecdf)))}</td>"
        f"<td>{_html_text(_report_warning_text(column.get('warnings')))}</td>"
        "</tr>"
    )


def _normality_report_section(payload: dict[str, object], locale: ReportLocale = "en") -> str:
    columns = payload.get("columns")
    if not isinstance(columns, list):
        return ""

    row_markup = "\n".join(
        _normality_report_row(column) for column in columns if isinstance(column, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Normality Test Summary", ko="정규성 검정 요약")
    description = report_text(
        locale,
        en="Shows stored Shapiro-Wilk, Anderson-Darling, and shape statistics.",
        ko="저장된 정규성 검정 결과의 Shapiro-Wilk, Anderson-Darling, 형상 통계량을 표시합니다.",
    )
    return f"""
  <h2>{_html_text(heading)}</h2>
  <p>{_html_text(description)}</p>
  <table>
    <thead>
      <tr>
        <th>Column</th>
        <th>N used</th>
        <th>Mean</th>
        <th>Std</th>
        <th>Skewness</th>
        <th>Kurtosis excess</th>
        <th>Shapiro W</th>
        <th>Shapiro p</th>
        <th>Anderson statistic</th>
        <th>Reject at alpha</th>
        <th>Q-Q points</th>
        <th>Warnings</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _normality_report_row(column: dict[object, object]) -> str:
    shapiro = column.get("shapiro_wilk")
    anderson = column.get("anderson_darling")
    decision = _report_nested_value(anderson, "decision_at_alpha")
    reject_normality = _report_nested_value(decision, "reject_normality")
    qq_plot = column.get("qq_plot")
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(column.get('display_name')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('n_used')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('mean')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('std')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('skewness')))}</td>"
        f"<td>{_html_text(_report_cell_value(column.get('kurtosis_excess')))}</td>"
        f"<td>{_html_text(_report_cell_value(_report_nested_value(shapiro, 'statistic')))}</td>"
        f"<td>{_html_text(_report_cell_value(_report_nested_value(shapiro, 'p_value')))}</td>"
        f"<td>{_html_text(_report_cell_value(_report_nested_value(anderson, 'statistic')))}</td>"
        f"<td>{_html_text(_report_cell_value(reject_normality))}</td>"
        f"<td>{_html_text(_report_cell_value(_report_point_count(qq_plot)))}</td>"
        f"<td>{_html_text(_report_warning_text(column.get('warnings')))}</td>"
        "</tr>"
    )


def _equal_variances_report_section(payload: dict[str, object], locale: ReportLocale = "en") -> str:
    tests = payload.get("tests")
    groups = payload.get("groups")
    test_markup = (
        "\n".join(
            _equal_variances_test_report_row(test) for test in tests if isinstance(test, dict)
        )
        if isinstance(tests, list)
        else ""
    )
    group_markup = (
        "\n".join(
            _equal_variances_group_report_row(group) for group in groups if isinstance(group, dict)
        )
        if isinstance(groups, list)
        else ""
    )
    if not test_markup and not group_markup:
        return ""

    response_name = _report_nested_value(payload.get("response"), "display_name")
    group_name = _report_nested_value(payload.get("group"), "display_name")
    response_label = _html_text(_report_cell_value(response_name))
    group_label = _html_text(_report_cell_value(group_name))
    summary_heading = report_text(
        locale, en="Test for Equal Variances Summary", ko="등분산 검정 요약"
    )
    group_heading = report_text(locale, en="Group Summary", ko="등분산 그룹 요약")

    return f"""
  <h2>{_html_text(summary_heading)}</h2>
  <p>Response: {response_label} / Group: {group_label}</p>
  <table>
    <thead>
      <tr>
        <th>Method</th>
        <th>Center</th>
        <th>Computed</th>
        <th>Statistic</th>
        <th>P value</th>
        <th>Alpha</th>
        <th>Reject equal variances</th>
        <th>Warnings</th>
      </tr>
    </thead>
    <tbody>
{test_markup}
    </tbody>
  </table>
  <h2>{_html_text(group_heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>Group</th>
        <th>N</th>
        <th>Mean</th>
        <th>Median</th>
        <th>Variance</th>
        <th>Std</th>
        <th>Min</th>
        <th>Max</th>
        <th>Warnings</th>
      </tr>
    </thead>
    <tbody>
{group_markup}
    </tbody>
  </table>
"""


def _equal_variances_test_report_row(test: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(test.get('method')))}</td>"
        f"<td>{_html_text(_report_cell_value(test.get('center')))}</td>"
        f"<td>{_html_text(_report_cell_value(test.get('computed')))}</td>"
        f"<td>{_html_text(_report_cell_value(test.get('statistic')))}</td>"
        f"<td>{_html_text(_report_cell_value(test.get('p_value')))}</td>"
        f"<td>{_html_text(_report_cell_value(test.get('alpha')))}</td>"
        f"<td>{_html_text(_report_cell_value(test.get('reject_equal_variances')))}</td>"
        f"<td>{_html_text(_report_warning_text(test.get('warnings')))}</td>"
        "</tr>"
    )


def _equal_variances_group_report_row(group: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(group.get('group_label')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('n')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('mean')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('median')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('variance')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('std')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('min')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('max')))}</td>"
        f"<td>{_html_text(_report_warning_text(group.get('warnings')))}</td>"
        "</tr>"
    )


def _hypothesis_report_section(
    payload: dict[str, object], summary_type: str, locale: ReportLocale = "en"
) -> str:
    metric_markup = "\n".join(_hypothesis_metric_report_rows(payload, summary_type))
    group_markup = _hypothesis_groups_report_markup(payload.get("groups"), locale)
    posthoc_markup = _hypothesis_posthoc_report_markup(payload.get("posthoc"), locale)
    if not metric_markup and not group_markup and not posthoc_markup:
        return ""

    heading = report_text(locale, en="Hypothesis Test Summary", ko="가설 검정 요약")
    description = report_text(
        locale,
        en="Shows stored test statistics, estimates, confidence intervals, and effect sizes.",
        ko="저장된 hypothesis 결과의 핵심 검정값, 추정치, 신뢰구간, 효과크기를 표시합니다.",
    )
    return f"""
  <h2>{_html_text(heading)}</h2>
  <p>{_html_text(description)}</p>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
{metric_markup}
    </tbody>
  </table>
{group_markup}
{posthoc_markup}
"""


def _hypothesis_metric_report_rows(
    payload: dict[str, object],
    summary_type: str,
) -> list[str]:
    rows = [
        _report_metric_row("Summary type", summary_type),
        _report_metric_row("Method", payload.get("method")),
        _report_metric_row("N total", payload.get("n_total")),
        _report_metric_row("N used", payload.get("n_used")),
        _report_metric_row("Alpha", payload.get("alpha")),
        _report_metric_row("Confidence level", payload.get("confidence_level")),
        _report_metric_row("Alternative", payload.get("alternative")),
        _report_metric_row("Missing policy", payload.get("missing_policy")),
    ]

    contrast = payload.get("contrast")
    if isinstance(contrast, dict):
        rows.extend(_hypothesis_contrast_metric_rows(contrast))

    test = payload.get("test")
    if isinstance(test, dict):
        rows.extend(_hypothesis_test_metric_rows(test))

    if summary_type == "equivalence_tost":
        rows.extend(_hypothesis_tost_metric_rows(payload))

    return [row for row in rows if row]


def _hypothesis_contrast_metric_rows(contrast: dict[object, object]) -> list[str]:
    confidence_interval = contrast.get("confidence_interval")
    return [
        _report_metric_row("Group 1", contrast.get("group_1_label")),
        _report_metric_row("Group 2", contrast.get("group_2_label")),
        _report_metric_row("Estimate", contrast.get("estimate")),
        _report_metric_row("Standard error", contrast.get("standard_error")),
        _report_metric_row("Degrees of freedom", contrast.get("df")),
        _report_metric_row("Statistic", contrast.get("statistic")),
        _report_metric_row("P value", contrast.get("p_value")),
        _report_metric_row("CI lower", _report_nested_value(confidence_interval, "lower")),
        _report_metric_row("CI upper", _report_nested_value(confidence_interval, "upper")),
        _report_metric_row("Effect size", _report_mapping_text(contrast.get("effect_size"))),
    ]


def _hypothesis_test_metric_rows(test: dict[object, object]) -> list[str]:
    statistic_value = _first_present_value(
        test,
        (
            "statistic",
            "t_statistic",
            "f_statistic",
            "h_statistic",
            "u_statistic",
            "w_statistic",
        ),
    )
    return [
        _report_metric_row("Test statistic", statistic_value),
        _report_metric_row("Statistic name", test.get("statistic_name")),
        _report_metric_row("Degrees of freedom", test.get("df")),
        _report_metric_row("P value", test.get("p_value")),
        _report_metric_row("Reject null", test.get("reject_null")),
        _report_metric_row("Effect size", _report_mapping_text(test.get("effect_size"))),
    ]


def _hypothesis_tost_metric_rows(payload: dict[str, object]) -> list[str]:
    estimate = payload.get("estimate")
    bounds = payload.get("equivalence_bounds")
    tests = payload.get("tests")
    lower_test = _report_nested_value(tests, "lower")
    upper_test = _report_nested_value(tests, "upper")
    tost = payload.get("tost")
    confidence_interval = payload.get("confidence_interval")
    return [
        _report_metric_row("Estimate", _report_nested_value(estimate, "value")),
        _report_metric_row("Lower bound", _report_nested_value(bounds, "lower")),
        _report_metric_row("Upper bound", _report_nested_value(bounds, "upper")),
        _report_metric_row("Lower one-sided p", _report_nested_value(lower_test, "p_value")),
        _report_metric_row("Upper one-sided p", _report_nested_value(upper_test, "p_value")),
        _report_metric_row("TOST p value", _report_nested_value(tost, "p_value")),
        _report_metric_row("Equivalent", _report_nested_value(tost, "equivalent")),
        _report_metric_row("CI lower", _report_nested_value(confidence_interval, "lower")),
        _report_metric_row("CI upper", _report_nested_value(confidence_interval, "upper")),
        _report_metric_row(
            "CI inside equivalence bounds",
            _report_nested_value(confidence_interval, "inside_equivalence_bounds"),
        ),
        _report_metric_row("Effect size", _report_mapping_text(payload.get("effect_size"))),
    ]


def _hypothesis_groups_report_markup(groups: object, locale: ReportLocale = "en") -> str:
    if not isinstance(groups, list):
        return ""
    row_markup = "\n".join(
        _hypothesis_group_report_row(group) for group in groups if isinstance(group, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Hypothesis-Test Group Summary", ko="가설 검정 그룹 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>Group</th>
        <th>N</th>
        <th>Mean</th>
        <th>Median</th>
        <th>Std</th>
        <th>Rank sum</th>
        <th>Warnings</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _hypothesis_group_report_row(group: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(group.get('group_label')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('n')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('mean')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('median')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('std')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('rank_sum')))}</td>"
        f"<td>{_html_text(_report_warning_text(group.get('warnings')))}</td>"
        "</tr>"
    )


def _hypothesis_posthoc_report_markup(posthoc: object, locale: ReportLocale = "en") -> str:
    if not isinstance(posthoc, dict):
        return ""
    comparisons = posthoc.get("comparisons")
    if not isinstance(comparisons, list):
        return ""
    row_markup = "\n".join(
        _hypothesis_posthoc_report_row(comparison)
        for comparison in comparisons
        if isinstance(comparison, dict)
    )
    if not row_markup:
        return ""

    performed = _report_cell_value(posthoc.get("performed"))
    method = _report_cell_value(posthoc.get("method") or posthoc.get("multiplicity_method"))
    heading = report_text(locale, en="Post-Hoc Comparisons", ko="가설 검정 사후 비교")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <p>Performed: {_html_text(performed)} / Method: {_html_text(method)}</p>
  <table>
    <thead>
      <tr>
        <th>Group 1</th>
        <th>Group 2</th>
        <th>Estimate</th>
        <th>P value</th>
        <th>Adjusted p</th>
        <th>Reject</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _hypothesis_posthoc_report_row(comparison: dict[object, object]) -> str:
    reject = _first_present_value(
        comparison,
        ("reject", "reject_null", "reject_holm", "reject_adjusted"),
    )
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(comparison.get('group_1_label')))}</td>"
        f"<td>{_html_text(_report_cell_value(comparison.get('group_2_label')))}</td>"
        f"<td>{_html_text(_report_cell_value(_posthoc_estimate_value(comparison)))}</td>"
        f"<td>{_html_text(_report_cell_value(comparison.get('p_value')))}</td>"
        f"<td>{_html_text(_report_cell_value(comparison.get('adjusted_p_value')))}</td>"
        f"<td>{_html_text(_report_cell_value(reject))}</td>"
        "</tr>"
    )


def _posthoc_estimate_value(comparison: dict[object, object]) -> object:
    return _first_present_value(
        comparison,
        ("estimate", "mean_difference", "median_difference", "rank_mean_difference"),
    )


def _categorical_report_section(
    payload: dict[str, object], summary_type: str, locale: ReportLocale = "en"
) -> str:
    metric_markup = "\n".join(_categorical_metric_report_rows(payload, summary_type))
    group_markup = _categorical_groups_report_markup(payload.get("groups"), locale)
    contingency_markup = _categorical_contingency_report_markup(
        payload.get("contingency_table"), locale
    )
    if not metric_markup and not group_markup and not contingency_markup:
        return ""

    heading = report_text(locale, en="Categorical Analysis Summary", ko="범주형 분석 요약")
    description = report_text(
        locale,
        en=(
            "Shows stored test statistics, proportions or differences, "
            "confidence intervals, and effect sizes."
        ),
        ko="저장된 categorical 결과의 검정값, 비율/차이, 신뢰구간, 효과크기를 표시합니다.",
    )
    return f"""
  <h2>{_html_text(heading)}</h2>
  <p>{_html_text(description)}</p>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
{metric_markup}
    </tbody>
  </table>
{group_markup}
{contingency_markup}
"""


def _categorical_metric_report_rows(
    payload: dict[str, object],
    summary_type: str,
) -> list[str]:
    rows = [
        _report_metric_row("Summary type", summary_type),
        _report_metric_row("Method", payload.get("method")),
        _report_metric_row("N total", payload.get("n_total")),
        _report_metric_row("N used", payload.get("n_used")),
        _report_metric_row("Alpha", payload.get("alpha")),
        _report_metric_row("Confidence level", payload.get("confidence_level")),
        _report_metric_row("Alternative", payload.get("alternative")),
        _report_metric_row("Event level", payload.get("event_level")),
        _report_metric_row("CI method", payload.get("ci_method")),
        _report_metric_row("Missing policy", payload.get("missing_policy")),
    ]

    sample = payload.get("sample")
    if isinstance(sample, dict):
        rows.extend(
            [
                _report_metric_row("Event count", sample.get("event_count")),
                _report_metric_row("Non-event count", sample.get("non_event_count")),
                _report_metric_row("Sample total", sample.get("total")),
                _report_metric_row("Sample proportion", sample.get("sample_proportion")),
                _report_metric_row("Difference from null", sample.get("difference_from_null")),
                _report_metric_row("Odds", sample.get("odds")),
            ],
        )

    difference = payload.get("difference")
    if isinstance(difference, dict):
        difference_ci = difference.get("confidence_interval")
        difference_ci_lower = _report_nested_value(difference_ci, "lower")
        difference_ci_upper = _report_nested_value(difference_ci, "upper")
        rows.extend(
            [
                _report_metric_row("Difference estimate", difference.get("estimate")),
                _report_metric_row("Difference CI lower", difference_ci_lower),
                _report_metric_row("Difference CI upper", difference_ci_upper),
            ],
        )

    test = payload.get("test")
    if isinstance(test, dict):
        rows.extend(_categorical_test_metric_rows(test))

    confidence_interval = payload.get("confidence_interval")
    rows.extend(
        [
            _report_metric_row("CI lower", _report_nested_value(confidence_interval, "lower")),
            _report_metric_row("CI upper", _report_nested_value(confidence_interval, "upper")),
            _report_metric_row("Effect size", _report_mapping_text(payload.get("effect_size"))),
            _report_metric_row("Effect sizes", _report_mapping_text(payload.get("effect_sizes"))),
            _report_metric_row(
                "Expected count diagnostics",
                _report_mapping_text(payload.get("expected_count_summary")),
            ),
            _report_metric_row(
                "Recommended alternatives",
                _report_cell_value(payload.get("recommended_alternative_tests")),
            ),
        ],
    )
    return [row for row in rows if row]


def _categorical_test_metric_rows(test: dict[object, object]) -> list[str]:
    return [
        _report_metric_row("Test statistic", test.get("statistic")),
        _report_metric_row("Statistic name", test.get("statistic_name")),
        _report_metric_row("Degrees of freedom", test.get("df")),
        _report_metric_row("P value", test.get("p_value")),
        _report_metric_row("Reject null", test.get("reject_null")),
        _report_metric_row("Exact test", test.get("exact")),
    ]


def _categorical_groups_report_markup(groups: object, locale: ReportLocale = "en") -> str:
    if not isinstance(groups, list):
        return ""
    row_markup = "\n".join(
        _categorical_group_report_row(group) for group in groups if isinstance(group, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Categorical Group Summary", ko="범주형 그룹 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>Group</th>
        <th>Total</th>
        <th>Events</th>
        <th>Non-events</th>
        <th>Proportion</th>
        <th>Warnings</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _categorical_group_report_row(group: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(group.get('group_label')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('total')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('event_count')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('non_event_count')))}</td>"
        f"<td>{_html_text(_report_cell_value(group.get('sample_proportion')))}</td>"
        f"<td>{_html_text(_report_warning_text(group.get('warnings')))}</td>"
        "</tr>"
    )


def _categorical_contingency_report_markup(
    contingency_table: object, locale: ReportLocale = "en"
) -> str:
    if not isinstance(contingency_table, dict):
        return ""
    rows = contingency_table.get("rows")
    if not isinstance(rows, list):
        return ""
    row_markup = "\n".join(
        _categorical_contingency_report_row(row) for row in rows if isinstance(row, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Contingency Table Summary", ko="범주형 교차표 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead><tr><th>Row level</th><th>Row total</th><th>Observed cells</th></tr></thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _categorical_contingency_report_row(row: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(row.get('row_level') or row.get('group_label')))}</td>"
        f"<td>{_html_text(_report_cell_value(row.get('row_total') or row.get('total')))}</td>"
        f"<td>{_html_text(_categorical_observed_cells_text(row.get('cells')))}</td>"
        "</tr>"
    )


def _categorical_observed_cells_text(cells: object) -> str:
    if not isinstance(cells, list):
        return ""
    parts: list[str] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            continue
        label = cell.get("column_level") or cell.get("level") or f"cell_{index + 1}"
        observed = cell.get("observed") if "observed" in cell else cell.get("count")
        parts.append(f"{_report_cell_value(label)}={_report_cell_value(observed)}")
    return "; ".join(parts)


def _regression_report_section(
    payload: dict[str, object], summary_type: str, locale: ReportLocale = "en"
) -> str:
    metric_markup = "\n".join(_regression_metric_report_rows(payload, summary_type))
    pairs_markup = _regression_pairs_report_markup(payload.get("pairs"), locale)
    coefficients_markup = _linear_model_coefficients_report_markup(
        payload.get("coefficients"), locale
    )
    if not metric_markup and not pairs_markup and not coefficients_markup:
        return ""

    heading = report_text(locale, en="Correlation and Regression Summary", ko="상관/회귀 분석 요약")
    description = report_text(
        locale,
        en="Shows stored association, model-fit, and coefficient results.",
        ko="저장된 correlation/regression 결과의 association, fit, coefficient 값을 표시합니다.",
    )
    return f"""
  <h2>{_html_text(heading)}</h2>
  <p>{_html_text(description)}</p>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
{metric_markup}
    </tbody>
  </table>
{pairs_markup}
{coefficients_markup}
"""


def _regression_metric_report_rows(
    payload: dict[str, object],
    summary_type: str,
) -> list[str]:
    association = payload.get("association")
    test = payload.get("test")
    confidence_interval = payload.get("confidence_interval")
    scatterplot = payload.get("scatterplot")
    sample = payload.get("sample")
    fit = payload.get("fit")
    diagnostics = payload.get("diagnostics")
    model_manifest = payload.get("model_manifest")
    return [
        row
        for row in [
            _report_metric_row("Summary type", summary_type),
            _report_metric_row("Method", payload.get("method")),
            _report_metric_row("N total", payload.get("n_total")),
            _report_metric_row("N used", payload.get("n_used")),
            _report_metric_row("Pair count", payload.get("pair_count")),
            _report_metric_row("Alpha", payload.get("alpha")),
            _report_metric_row("Confidence level", payload.get("confidence_level")),
            _report_metric_row("Missing policy", payload.get("missing_policy")),
            _report_metric_row("Correlation", _report_nested_value(association, "correlation")),
            _report_metric_row("R squared", _report_nested_value(association, "r_squared")),
            _report_metric_row("Covariance", _report_nested_value(association, "covariance")),
            _report_metric_row("P value", _report_nested_value(test, "p_value")),
            _report_metric_row("CI lower", _report_nested_value(confidence_interval, "lower")),
            _report_metric_row("CI upper", _report_nested_value(confidence_interval, "upper")),
            _report_metric_row("Scatter points", _report_nested_value(scatterplot, "point_count")),
            _report_metric_row("Sample N used", _report_nested_value(sample, "n_used")),
            _report_metric_row("DF model", _report_nested_value(sample, "df_model")),
            _report_metric_row("DF residual", _report_nested_value(sample, "df_residual")),
            _report_metric_row("Model R squared", _report_nested_value(fit, "r_squared")),
            _report_metric_row(
                "Adjusted R squared",
                _report_nested_value(fit, "adjusted_r_squared"),
            ),
            _report_metric_row(
                "Residual standard error",
                _report_nested_value(fit, "residual_standard_error"),
            ),
            _report_metric_row("F statistic", _report_nested_value(fit, "f_statistic")),
            _report_metric_row("F p value", _report_nested_value(fit, "f_p_value")),
            _report_metric_row("Rank", _report_nested_value(diagnostics, "rank")),
            _report_metric_row(
                "Condition number",
                _report_nested_value(diagnostics, "condition_number"),
            ),
            _report_metric_row("Max VIF", _report_nested_value(diagnostics, "max_vif")),
            _report_metric_row("Model ID", _report_nested_value(model_manifest, "model_id")),
        ]
        if row
    ]


def _regression_pairs_report_markup(pairs: object, locale: ReportLocale = "en") -> str:
    if not isinstance(pairs, list):
        return ""
    row_markup = "\n".join(
        _regression_pair_report_row(pair) for pair in pairs if isinstance(pair, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Correlation Pair Summary", ko="상관 쌍 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>X</th>
        <th>Y</th>
        <th>Status</th>
        <th>N used</th>
        <th>Correlation</th>
        <th>P value</th>
        <th>CI lower</th>
        <th>CI upper</th>
        <th>Warnings</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _regression_pair_report_row(pair: dict[object, object]) -> str:
    association = pair.get("association")
    test = pair.get("test")
    confidence_interval = pair.get("confidence_interval")
    x_name = _report_nested_value(pair.get("x"), "display_name")
    y_name = _report_nested_value(pair.get("y"), "display_name")
    correlation = _report_nested_value(association, "correlation")
    p_value = _report_nested_value(test, "p_value")
    ci_lower = _report_nested_value(confidence_interval, "lower")
    ci_upper = _report_nested_value(confidence_interval, "upper")
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(x_name))}</td>"
        f"<td>{_html_text(_report_cell_value(y_name))}</td>"
        f"<td>{_html_text(_report_cell_value(pair.get('status')))}</td>"
        f"<td>{_html_text(_report_cell_value(pair.get('n_used')))}</td>"
        f"<td>{_html_text(_report_cell_value(correlation))}</td>"
        f"<td>{_html_text(_report_cell_value(p_value))}</td>"
        f"<td>{_html_text(_report_cell_value(ci_lower))}</td>"
        f"<td>{_html_text(_report_cell_value(ci_upper))}</td>"
        f"<td>{_html_text(_report_warning_text(pair.get('warnings')))}</td>"
        "</tr>"
    )


def _linear_model_coefficients_report_markup(
    coefficients: object, locale: ReportLocale = "en"
) -> str:
    if not isinstance(coefficients, list):
        return ""
    row_markup = "\n".join(
        _linear_model_coefficient_report_row(coefficient)
        for coefficient in coefficients
        if isinstance(coefficient, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Linear-Model Coefficient Summary", ko="선형모델 계수 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>Term</th>
        <th>Kind</th>
        <th>Estimate</th>
        <th>Std error</th>
        <th>Statistic</th>
        <th>P value</th>
        <th>CI lower</th>
        <th>CI upper</th>
        <th>VIF</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _linear_model_coefficient_report_row(coefficient: dict[object, object]) -> str:
    confidence_interval = coefficient.get("confidence_interval")
    ci_lower = _report_nested_value(confidence_interval, "lower")
    ci_upper = _report_nested_value(confidence_interval, "upper")
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(coefficient.get('term')))}</td>"
        f"<td>{_html_text(_report_cell_value(coefficient.get('term_kind')))}</td>"
        f"<td>{_html_text(_report_cell_value(coefficient.get('estimate')))}</td>"
        f"<td>{_html_text(_report_cell_value(coefficient.get('standard_error')))}</td>"
        f"<td>{_html_text(_report_cell_value(coefficient.get('statistic')))}</td>"
        f"<td>{_html_text(_report_cell_value(coefficient.get('p_value')))}</td>"
        f"<td>{_html_text(_report_cell_value(ci_lower))}</td>"
        f"<td>{_html_text(_report_cell_value(ci_upper))}</td>"
        f"<td>{_html_text(_report_cell_value(coefficient.get('vif')))}</td>"
        "</tr>"
    )


def _quality_report_section(
    payload: dict[str, object], summary_type: str, locale: ReportLocale = "en"
) -> str:
    metric_markup = "\n".join(_quality_metric_report_rows(payload, summary_type))
    chart_markup = _quality_chart_summaries_report_markup(payload, locale)
    signal_markup = _quality_signals_report_markup(payload.get("signals"), locale)
    capability_markup = _quality_capability_report_markup(payload.get("capability"), locale)
    gage_markup = _gage_variance_components_report_markup(
        payload.get("variance_components"), locale
    )
    if not any((metric_markup, chart_markup, signal_markup, capability_markup, gage_markup)):
        return ""

    heading = report_text(locale, en="Quality Control Summary", ko="품질 관리 요약")
    description = report_text(
        locale,
        en="Shows stored chart, process-capability, and Gage diagnostic results.",
        ko="저장된 quality 결과의 핵심 차트, 공정능력, Gage 진단 값을 표시합니다.",
    )
    return f"""
  <h2>{_html_text(heading)}</h2>
  <p>{_html_text(description)}</p>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
{metric_markup}
    </tbody>
  </table>
{chart_markup}
{signal_markup}
{capability_markup}
{gage_markup}
"""


def _quality_metric_report_rows(
    payload: dict[str, object],
    summary_type: str,
) -> list[str]:
    sigma_estimator = payload.get("sigma_estimator")
    runs = payload.get("runs")
    runs_test = payload.get("runs_test")
    sample = payload.get("sample")
    spec_limits = payload.get("spec_limits")
    observed = payload.get("observed_nonconformance")
    expected = payload.get("expected_nonconformance_normal")
    histogram = payload.get("histogram")
    design = payload.get("design")
    summary = payload.get("summary")
    chart = payload.get("chart")
    signals = payload.get("signals")
    control_rules = payload.get("control_rules")
    observed_nonconformance_count = _report_nested_value(observed, "total_count")
    expected_nonconformance_ppm = _report_nested_value(expected, "total_ppm")
    return [
        row
        for row in [
            _report_metric_row("Summary type", summary_type),
            _report_metric_row("Method", payload.get("method")),
            _report_metric_row("N total", payload.get("n_total")),
            _report_metric_row("N used", payload.get("n_used")),
            _report_metric_row("Missing policy", payload.get("missing_policy")),
            _report_metric_row("Order source", payload.get("order_source")),
            _report_metric_row("Chart type", payload.get("chart_type")),
            _report_metric_row("Subgroup size", payload.get("subgroup_size")),
            _report_metric_row("Subgroup count", payload.get("subgroup_count")),
            _report_metric_row("Center line", payload.get("center_line")),
            _report_metric_row("Sigma", _report_nested_value(sigma_estimator, "sigma")),
            _report_metric_row("MR-bar", _report_nested_value(sigma_estimator, "mrbar")),
            _report_metric_row("Signal count", _sequence_count(signals)),
            _report_metric_row("Control rule count", _sequence_count(control_rules)),
            _report_metric_row("Run count", _report_nested_value(runs, "run_count")),
            _report_metric_row("Runs above center", _report_nested_value(runs, "n_above")),
            _report_metric_row("Runs below center", _report_nested_value(runs, "n_below")),
            _report_metric_row("Runs test p low", _report_nested_value(runs_test, "p_value_low")),
            _report_metric_row("Runs test p high", _report_nested_value(runs_test, "p_value_high")),
            _report_metric_row("Sample mean", _report_nested_value(sample, "mean")),
            _report_metric_row("Sample std overall", _report_nested_value(sample, "std_overall")),
            _report_metric_row("Sample std within", _report_nested_value(sample, "std_within")),
            _report_metric_row("Spec LSL", _report_nested_value(spec_limits, "lsl")),
            _report_metric_row("Spec USL", _report_nested_value(spec_limits, "usl")),
            _report_metric_row("Spec target", _report_nested_value(spec_limits, "target")),
            _report_metric_row("Observed nonconformance", observed_nonconformance_count),
            _report_metric_row("Expected nonconformance ppm", expected_nonconformance_ppm),
            _report_metric_row("Histogram bins", _quality_histogram_bin_count(histogram)),
            _report_metric_row("Part count", _report_nested_value(design, "part_count")),
            _report_metric_row("Operator count", _report_nested_value(design, "operator_count")),
            _report_metric_row("Replicate count", _report_nested_value(design, "replicate_count")),
            _report_metric_row("Measurement mean", _report_nested_value(summary, "mean")),
            _report_metric_row("Measurement range", _report_nested_value(summary, "range")),
            _report_metric_row("Chart point count", _report_nested_value(chart, "point_count")),
        ]
        if row
    ]


def _quality_chart_summaries_report_markup(
    payload: dict[str, object], locale: ReportLocale = "en"
) -> str:
    chart_specs = (
        ("individuals_chart", "Individuals"),
        ("moving_range_chart", "Moving range"),
        ("xbar_chart", "Xbar"),
        ("r_chart", "R"),
        ("s_chart", "S"),
        ("chart", "Chart"),
    )
    rows = [
        _quality_chart_summary_report_row(label, chart)
        for key, label in chart_specs
        if isinstance((chart := payload.get(key)), dict)
    ]
    row_markup = "\n".join(rows)
    if not row_markup:
        return ""

    heading = report_text(locale, en="Quality Chart Summary", ko="품질 차트 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>Chart</th>
        <th>Center</th>
        <th>LCL</th>
        <th>UCL</th>
        <th>Point count</th>
        <th>Truncated</th>
        <th>X axis</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _quality_chart_summary_report_row(label: str, chart: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(label)}</td>"
        f"<td>{_html_text(_report_cell_value(chart.get('center_line')))}</td>"
        f"<td>{_html_text(_report_cell_value(chart.get('lcl')))}</td>"
        f"<td>{_html_text(_report_cell_value(chart.get('ucl')))}</td>"
        f"<td>{_html_text(_report_cell_value(_chart_point_count(chart)))}</td>"
        f"<td>{_html_text(_report_cell_value(chart.get('points_truncated')))}</td>"
        f"<td>{_html_text(_report_cell_value(chart.get('x_axis')))}</td>"
        "</tr>"
    )


def _quality_signals_report_markup(signals: object, locale: ReportLocale = "en") -> str:
    if not isinstance(signals, list):
        return ""
    row_markup = "\n".join(
        _quality_signal_report_row(signal) for signal in signals if isinstance(signal, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Quality Signal Summary", ko="품질 신호 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>Code</th>
        <th>Severity</th>
        <th>Chart</th>
        <th>Position</th>
        <th>Range</th>
        <th>Direction</th>
        <th>Length</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _quality_signal_report_row(signal: dict[object, object]) -> str:
    signal_range = _quality_signal_range(signal)
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(signal.get('code')))}</td>"
        f"<td>{_html_text(_report_cell_value(signal.get('severity')))}</td>"
        f"<td>{_html_text(_report_cell_value(signal.get('chart')))}</td>"
        f"<td>{_html_text(_report_cell_value(signal.get('position')))}</td>"
        f"<td>{_html_text(signal_range)}</td>"
        f"<td>{_html_text(_report_cell_value(signal.get('direction')))}</td>"
        f"<td>{_html_text(_report_cell_value(signal.get('length')))}</td>"
        "</tr>"
    )


def _quality_signal_range(signal: dict[object, object]) -> str:
    start = signal.get("start_position")
    end = signal.get("end_position")
    if start is None and end is None:
        return ""
    return f"{_report_cell_value(start)}-{_report_cell_value(end)}"


def _quality_capability_report_markup(capability: object, locale: ReportLocale = "en") -> str:
    if not isinstance(capability, dict):
        return ""
    row_markup = "\n".join(
        _quality_capability_report_row(label, indices)
        for label, indices in capability.items()
        if isinstance(indices, dict)
    )
    if not row_markup:
        return ""

    heading = report_text(locale, en="Process Capability Summary", ko="공정능력 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>Estimator</th>
        <th>Two-sided</th>
        <th>Lower</th>
        <th>Upper</th>
        <th>Min side</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _quality_capability_report_row(label: object, indices: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(label))}</td>"
        f"<td>{_html_text(_report_cell_value(indices.get('two_sided')))}</td>"
        f"<td>{_html_text(_report_cell_value(indices.get('lower')))}</td>"
        f"<td>{_html_text(_report_cell_value(indices.get('upper')))}</td>"
        f"<td>{_html_text(_report_cell_value(indices.get('min_side')))}</td>"
        "</tr>"
    )


def _gage_variance_components_report_markup(components: object, locale: ReportLocale = "en") -> str:
    if not isinstance(components, dict):
        return ""
    component_rows = [
        _gage_component_report_row(label, component)
        for label, component in components.items()
        if isinstance(component, dict)
    ]
    row_markup = "\n".join(component_rows)
    if not row_markup:
        return ""

    heading = report_text(locale, en="Gage R&R Variance Summary", ko="Gage R&R 분산 요약")
    return f"""
  <h2>{_html_text(heading)}</h2>
  <table>
    <thead>
      <tr>
        <th>Component</th>
        <th>Raw variance</th>
        <th>Final variance</th>
        <th>Std dev</th>
        <th>Study variation</th>
        <th>% contribution</th>
        <th>% study variation</th>
      </tr>
    </thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
"""


def _gage_component_report_row(label: object, component: dict[object, object]) -> str:
    return (
        "<tr>"
        f"<td>{_html_text(_report_cell_value(label))}</td>"
        f"<td>{_html_text(_report_cell_value(component.get('raw_variance')))}</td>"
        f"<td>{_html_text(_report_cell_value(component.get('final_variance')))}</td>"
        f"<td>{_html_text(_report_cell_value(component.get('standard_deviation')))}</td>"
        f"<td>{_html_text(_report_cell_value(component.get('study_variation')))}</td>"
        f"<td>{_html_text(_report_cell_value(component.get('percent_contribution')))}</td>"
        f"<td>{_html_text(_report_cell_value(component.get('percent_study_variation')))}</td>"
        "</tr>"
    )


def _report_metric_row(label: str, value: object) -> str:
    if value is None or value == "":
        return ""
    return (
        "<tr>"
        f"<td>{_html_text(label)}</td>"
        f"<td>{_html_text(_report_cell_value(value))}</td>"
        "</tr>"
    )


def _report_warning_text(value: object) -> str:
    return ", ".join(str(item) for item in value) if isinstance(value, list) else ""


def _report_nested_value(value: object, key: str) -> object:
    return value.get(key) if isinstance(value, dict) else None


def _report_point_count(value: object) -> object:
    if isinstance(value, dict):
        point_count = value.get("point_count")
        if point_count is not None:
            return point_count
        points = value.get("points")
        return len(points) if isinstance(points, list) else None
    return len(value) if isinstance(value, list) else None


def _sequence_count(value: object) -> object:
    return len(value) if isinstance(value, list) else None


def _chart_point_count(chart: dict[object, object]) -> object:
    point_count = chart.get("point_count")
    if point_count is not None:
        return point_count
    points = chart.get("points")
    return len(points) if isinstance(points, list) else None


def _quality_histogram_bin_count(histogram: object) -> object:
    if not isinstance(histogram, dict):
        return None
    bin_count = histogram.get("bin_count")
    if bin_count is not None:
        return bin_count
    bins = histogram.get("bins")
    return len(bins) if isinstance(bins, list) else None


def _first_present_value(mapping: dict[object, object], keys: tuple[str, ...]) -> object:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _report_mapping_text(value: object) -> object:
    if not isinstance(value, dict):
        return value
    parts = [
        f"{key}={_report_cell_value(nested_value)}"
        for key, nested_value in value.items()
        if nested_value is not None
    ]
    return ", ".join(parts)


def _report_cell_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float | str):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _graphical_summary_report_section_v2(
    payload: dict[str, object], locale: ReportLocale = "en"
) -> str:
    columns = payload.get("columns")
    if not isinstance(columns, list):
        return report_text(
            locale,
            en="<p>No saved graphical-summary result is available.</p>",
            ko="<p>저장된 그래프 요약 결과가 없습니다.</p>",
        )
    cards = "".join(
        _graphical_summary_column_report_v2(column, locale)
        for column in columns
        if isinstance(column, dict)
    )
    return (
        report_text(
            locale,
            en="<p>The tables and charts below use only the saved result payload.</p>",
            ko="<p>아래 표와 그래프는 저장된 결과 payload만 사용해 재구성했습니다.</p>",
        )
        + f'<div class="report-grid">{cards}</div>'
    )


def _graphical_summary_column_report_v2(
    column: dict[object, object], locale: ReportLocale = "en"
) -> str:
    label = _report_cell_value(column.get("display_name"))
    ad = column.get("anderson_darling")
    metrics = (
        ("N", column.get("n_used")),
        (report_text(locale, en="Mean", ko="평균"), column.get("mean")),
        (
            report_text(locale, en="Standard deviation", ko="표준편차"),
            column.get("standard_deviation"),
        ),
        (report_text(locale, en="Variance", ko="분산"), column.get("variance")),
        (report_text(locale, en="Skewness", ko="왜도"), column.get("skewness")),
        (report_text(locale, en="Kurtosis", ko="첨도"), column.get("kurtosis_excess")),
        (report_text(locale, en="Minimum", ko="최소"), column.get("min")),
        ("Q1", column.get("q1")),
        (report_text(locale, en="Median", ko="중앙값"), column.get("median")),
        ("Q3", column.get("q3")),
        (report_text(locale, en="Maximum", ko="최대"), column.get("max")),
        ("AD A²", _report_nested_value(ad, "statistic")),
        ("AD p-value", _report_nested_value(ad, "p_value")),
    )
    table_rows = "".join(
        f"<tr><th>{_html_text(name)}</th><td>{_html_text(_report_cell_value(value))}</td></tr>"
        for name, value in metrics
    )
    qq_plot_markup = _report_point_svg(
        column.get("qq_plot"),
        label="Q-Q Plot",
        x_key="theoretical",
        y_key="sample",
        locale=locale,
    )
    ecdf_markup = _report_point_svg(
        column.get("ecdf"),
        label="ECDF",
        x_key="x",
        y_key="probability",
        locale=locale,
    )
    histogram_heading = report_text(
        locale, en="Histogram + Normal Fit", ko="히스토그램 + 적합 정규곡선"
    )
    statistics_heading = report_text(locale, en="Statistical Summary", ko="통계 요약")
    boxplot_heading = report_text(locale, en="Box Plot", ko="박스플롯")
    interval_heading = report_text(locale, en="Confidence Intervals", ko="신뢰구간")
    extra_heading = report_text(locale, en="Additional Chart: ECDF", ko="추가 그래프: ECDF")
    return f"""
<section class="report-card report-card-full">
  <h3>{_html_text(label)}</h3>
  <div class="report-grid">
    <div class="report-card">
      <h3>{_html_text(histogram_heading)}</h3>{_report_histogram_svg(column, locale)}
    </div>
    <div class="report-card">
      <h3>{_html_text(statistics_heading)}</h3><table><tbody>{table_rows}</tbody></table>
    </div>
    <div class="report-card">
      <h3>{_html_text(boxplot_heading)}</h3>{_report_boxplot_svg(column, locale)}
    </div>
    <div class="report-card"><h3>Q-Q Plot</h3>{qq_plot_markup}</div>
    <div class="report-card report-card-full">
      <h3>{_html_text(interval_heading)}</h3>{_report_confidence_interval_svg(column, locale)}
    </div>
  </div>
  <details><summary>{_html_text(extra_heading)}</summary>{ecdf_markup}</details>
</section>
"""


def _report_histogram_svg(column: dict[object, object], locale: ReportLocale = "en") -> str:
    histogram = column.get("histogram")
    bins_value = histogram.get("bins") if isinstance(histogram, dict) else None
    bins = (
        [item for item in bins_value if isinstance(item, dict)]
        if isinstance(bins_value, list)
        else []
    )
    parsed: list[tuple[float, float, float]] = []
    for item in bins:
        low = _report_float(item.get("lower"))
        high = _report_float(item.get("upper"))
        count = _report_float(item.get("count"))
        if low is not None and high is not None and count is not None:
            parsed.append((low, high, count))
    if not parsed:
        return report_text(
            locale, en="<p>Histogram unavailable.</p>", ko="<p>히스토그램을 표시할 수 없습니다.</p>"
        )
    normal_fit = column.get("normal_fit_curve")
    points_value = normal_fit.get("points") if isinstance(normal_fit, dict) else None
    curve = (
        [point for point in points_value if isinstance(point, dict)]
        if isinstance(points_value, list)
        else []
    )
    x_min = min(low for low, _, _ in parsed)
    x_max = max(high for _, high, _ in parsed)
    curve_values: list[tuple[float, float]] = []
    for point in curve:
        x = _report_float(point.get("x"))
        y = _report_float(point.get("expected_count"))
        if x is not None and y is not None:
            curve_values.append((x, y))
    y_max = max(1.0, *[count for _, _, count in parsed], *[y for _, y in curve_values])
    bars = "".join(
        _report_histogram_bar(low, high, count, x_min=x_min, x_max=x_max, y_max=y_max)
        for low, high, count in parsed
    )
    curve_markup = ""
    if len(curve_values) > 1:
        point_text = " ".join(
            f"{_report_scale(x,x_min,x_max,40,600):.3f},{_report_scale(y,0,y_max,210,20):.3f}"
            for x, y in curve_values
        )
        fit_label = _html_text(report_text(locale, en="Fitted normal curve", ko="적합 정규곡선"))
        curve_markup = (
            f'<polyline class="normal-fit" points="{point_text}"/>'
            f'<text x="455" y="16" font-size="10">-- {fit_label}</text>'
        )
    title = report_text(
        locale, en="Histogram and Fitted Normal Curve", ko="히스토그램과 적합 정규곡선"
    )
    description = report_text(
        locale,
        en="Bars show frequency; the dashed line is the stored fitted normal curve.",
        ko="막대는 빈도이고 점선은 저장된 적합 정규곡선입니다.",
    )
    return (
        f'<svg role="img" aria-label="{_html_text(title)}" '
        'viewBox="0 0 620 235">'
        f"<title>{_html_text(title)}</title>"
        f"<desc>{_html_text(description)}</desc>"
        '<line class="axis" x1="40" x2="600" y1="210" y2="210"/>'
        '<line class="axis" x1="40" x2="40" y1="20" y2="210"/>'
        f"{bars}{curve_markup}</svg>"
    )


def _report_histogram_bar(
    low: float, high: float, count: float, *, x_min: float, x_max: float, y_max: float
) -> str:
    x = _report_scale(low, x_min, x_max, 40, 600)
    x2 = _report_scale(high, x_min, x_max, 40, 600)
    y = _report_scale(count, 0, y_max, 210, 20)
    width = max(1, x2 - x - 1)
    return (
        f'<rect class="histogram-bar" x="{x:.3f}" y="{y:.3f}" '
        f'width="{width:.3f}" height="{210 - y:.3f}"/>'
    )


def _report_boxplot_svg(column: dict[object, object], locale: ReportLocale = "en") -> str:
    boxplot = column.get("boxplot")
    if not isinstance(boxplot, dict):
        return report_text(
            locale, en="<p>Box plot unavailable.</p>", ko="<p>박스플롯을 표시할 수 없습니다.</p>"
        )
    values = [
        _report_float(boxplot.get(key))
        for key in ("lower_whisker", "q1", "median", "q3", "upper_whisker")
    ]
    if any(value is None for value in values):
        return report_text(
            locale, en="<p>Box plot unavailable.</p>", ko="<p>박스플롯을 표시할 수 없습니다.</p>"
        )
    low, q1, median, q3, high = (float(value) for value in values if value is not None)

    def scale(value: float) -> float:
        return _report_scale(value, low, high, 40, 600)

    title = report_text(locale, en="Box Plot", ko="박스플롯")
    description = report_text(
        locale,
        en="Hyndman-Fan 6 quartiles with Tukey 1.5 IQR whiskers.",
        ko="Hyndman-Fan 6 사분위수와 Tukey 1.5 IQR whisker입니다.",
    )
    return (
        f'<svg role="img" aria-label="{_html_text(title)}" viewBox="0 0 620 145">'
        f"<title>{_html_text(title)}</title>"
        f"<desc>{_html_text(description)}</desc>"
        f'<line class="axis" x1="{scale(low):.3f}" x2="{scale(high):.3f}" '
        'y1="72" y2="72"/>'
        f'<rect x="{scale(q1):.3f}" y="46" width="{scale(q3)-scale(q1):.3f}" '
        'height="52" fill="#dbe9f7" stroke="#2166ac"/>'
        f'<line class="interval" x1="{scale(median):.3f}" '
        f'x2="{scale(median):.3f}" y1="46" y2="98"/></svg>'
    )


def _report_point_svg(
    series: object,
    *,
    label: str,
    x_key: str,
    y_key: str,
    locale: ReportLocale = "en",
) -> str:
    points_value = series.get("points") if isinstance(series, dict) else None
    points = (
        [point for point in points_value if isinstance(point, dict)]
        if isinstance(points_value, list)
        else []
    )
    values: list[tuple[float, float]] = []
    for point in points:
        x = _report_float(point.get(x_key))
        y = _report_float(point.get(y_key))
        if x is not None and y is not None:
            values.append((x, y))
    if not values:
        unavailable = report_text(
            locale, en=f"{label} points unavailable.", ko=f"{label} point를 표시할 수 없습니다."
        )
        return f"<p>{_html_text(unavailable)}</p>"
    x_min, x_max = min(x for x, _ in values), max(x for x, _ in values)
    y_min, y_max = min(y for _, y in values), max(y for _, y in values)
    circles = "".join(_report_point_circle(x, y, x_min, x_max, y_min, y_max) for x, y in values)
    escaped_label = _html_text(label)
    description = _html_text(
        report_text(
            locale,
            en="Bounded points from the saved payload.",
            ko="저장 payload의 bounded point입니다.",
        )
    )
    return (
        f'<svg role="img" aria-label="{escaped_label}" viewBox="0 0 620 235">'
        f"<title>{escaped_label}</title>"
        f"<desc>{description}</desc>"
        '<line class="axis" x1="40" x2="600" y1="210" y2="210"/>'
        '<line class="axis" x1="40" x2="40" y1="20" y2="210"/>'
        f"{circles}</svg>"
    )


def _report_point_circle(
    x: float,
    y: float,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> str:
    cx = _report_scale(x, x_min, x_max, 40, 600)
    cy = _report_scale(y, y_min, y_max, 210, 20)
    return f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="2.4" fill="#2166ac"/>'


def _report_confidence_interval_svg(
    column: dict[object, object], locale: ReportLocale = "en"
) -> str:
    intervals = column.get("confidence_intervals")
    if not isinstance(intervals, dict):
        return report_text(
            locale,
            en="<p>No confidence-interval payload is available.</p>",
            ko="<p>신뢰구간 payload가 없습니다.</p>",
        )
    rows = []
    for key, label, y in (
        ("mean", report_text(locale, en="Mean", ko="평균"), 42),
        ("median", report_text(locale, en="Median", ko="중앙값"), 88),
        (
            "standard_deviation",
            report_text(
                locale, en="Standard deviation (separate scale)", ko="표준편차 (별도 척도)"
            ),
            164,
        ),
    ):
        item = intervals.get(key)
        if not isinstance(item, dict):
            continue
        estimate = _report_float(item.get("estimate"))
        lower = _report_float(item.get("lower"))
        upper = _report_float(item.get("upper"))
        if estimate is not None and lower is not None and upper is not None:
            rows.append((label, y, estimate, lower, upper))
    if not rows:
        return report_text(
            locale,
            en="<p>Confidence intervals unavailable.</p>",
            ko="<p>신뢰구간을 계산할 수 없습니다.</p>",
        )
    markup = ""
    for label, y, estimate, lower, upper in rows:
        estimate_x = _report_scale(estimate, lower, upper, 190, 590)
        markup += (
            f'<text x="175" y="{y + 4}" text-anchor="end" font-size="12">'
            f"{_html_text(label)}</text>"
            f'<line class="interval" x1="190" x2="590" y1="{y}" y2="{y}"/>'
            f'<circle class="estimate" cx="{estimate_x:.3f}" cy="{y}" r="4"/>'
            f'<text x="190" y="{y + 18}" font-size="10">{lower:.6g}</text>'
            f'<text x="590" y="{y + 18}" text-anchor="end" '
            f'font-size="10">{upper:.6g}</text>'
        )
    title = report_text(locale, en="Confidence Intervals", ko="신뢰구간")
    aria = report_text(
        locale,
        en="Mean, median, and standard-deviation confidence intervals",
        ko="평균 중앙값 표준편차 신뢰구간",
    )
    description = report_text(
        locale,
        en="Mean and median use a location scale; standard deviation uses a separate scale.",
        ko="평균과 중앙값은 위치 척도이고 표준편차는 별도 척도입니다.",
    )
    return (
        f'<svg role="img" aria-label="{_html_text(aria)}" '
        'viewBox="0 0 620 205">'
        f"<title>{_html_text(title)}</title>"
        f"<desc>{_html_text(description)}</desc>"
        f"{markup}</svg>"
    )


def _report_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _report_scale(value: float, minimum: float, maximum: float, start: float, end: float) -> float:
    if maximum <= minimum:
        return (start + end) / 2
    return start + (value - minimum) / (maximum - minimum) * (end - start)


def _equal_variances_report_section_v2(
    payload: dict[str, object], locale: ReportLocale = "en"
) -> str:
    multiple = payload.get("multiple_comparisons")
    levene = payload.get("levene")
    if not isinstance(multiple, dict) or not isinstance(levene, dict):
        return _equal_variances_report_section(payload, locale)
    multiple_label = report_text(locale, en="Multiple Comparisons", ko="다중 비교")
    levene_label = report_text(
        locale, en="Levene's Test (Brown-Forsythe)", ko="Levene 검정 (Brown-Forsythe)"
    )
    method_rows = (
        f"<tr><td>{_html_text(multiple_label)}</td><td>-</td>"
        f"<td>{_html_text(_report_cell_value(multiple.get('p_value')))}</td>"
        f"<td>{_html_text(_report_cell_value(multiple.get('reject_equal_variances')))}</td></tr>"
        f"<tr><td>{_html_text(levene_label)}</td>"
        f"<td>{_html_text(_report_cell_value(levene.get('statistic')))}</td>"
        f"<td>{_html_text(_report_cell_value(levene.get('p_value')))}</td>"
        f"<td>{_html_text(_report_cell_value(levene.get('reject_equal_variances')))}</td></tr>"
    )
    heading = report_text(locale, en="Test for Equal Variances Summary", ko="등분산 검정 요약")
    method_header = report_text(locale, en="Method", ko="방법")
    statistic_header = report_text(locale, en="Test Statistic", ko="검정 통계량")
    reject_header = report_text(locale, en="Reject Equal Variances", ko="등분산 기각")
    interval_heading = report_text(
        locale,
        en="Multiple-Comparison Intervals for Standard Deviations",
        ko="표준편차 다중 비교구간",
    )
    note = report_text(
        locale,
        en=(
            "These multiple-comparison intervals compare group standard deviations; "
            "they are not ordinary confidence intervals for population standard deviations. "
            "Levene's test uses the median-centered Brown-Forsythe modification."
        ),
        ko=(
            "다중 비교구간은 그룹 표준편차 비교를 위한 구간이며 모집단 표준편차의 "
            "일반 신뢰구간이 아닙니다. Levene 검정은 중앙값 중심 Brown-Forsythe 수정법입니다."
        ),
    )
    return f"""
<h3>{_html_text(heading)}</h3>
<table>
  <thead><tr><th>{_html_text(method_header)}</th><th>{_html_text(statistic_header)}</th><th>p-value</th><th>{_html_text(reject_header)}</th></tr></thead>
  <tbody>{method_rows}</tbody>
</table>
<h3>{_html_text(interval_heading)}</h3>
{_variance_comparison_report_svg(multiple, locale)}
<p class="report-note">
  {_html_text(note)}
</p>
"""


def _variance_comparison_report_svg(
    multiple: dict[object, object], locale: ReportLocale = "en"
) -> str:
    groups_value = multiple.get("groups")
    groups = (
        [group for group in groups_value if isinstance(group, dict)]
        if isinstance(groups_value, list)
        else []
    )
    parsed = []
    for group in groups:
        interval = group.get("comparison_interval")
        if not isinstance(interval, dict):
            continue
        estimate = _report_float(group.get("sample_standard_deviation"))
        lower = _report_float(interval.get("lower"))
        upper = _report_float(interval.get("upper"))
        if estimate is not None and lower is not None and upper is not None:
            parsed.append((_report_cell_value(group.get("group_label")), estimate, lower, upper))
    if not parsed:
        return report_text(
            locale,
            en="<p>Multiple-comparison intervals unavailable.</p>",
            ko="<p>다중 비교구간을 계산할 수 없습니다.</p>",
        )
    minimum = min(lower for _, _, lower, _ in parsed)
    maximum = max(upper for _, _, _, upper in parsed)
    height = 50 + 44 * len(parsed)
    rows = ""
    for index, (label, estimate, lower, upper) in enumerate(parsed):
        y = 28 + 44 * index
        x1 = _report_scale(lower, minimum, maximum, 150, 600)
        x2 = _report_scale(upper, minimum, maximum, 150, 600)
        xe = _report_scale(estimate, minimum, maximum, 150, 600)
        rows += (
            f'<text x="138" y="{y + 4}" text-anchor="end" font-size="12">'
            f"{_html_text(label)}</text>"
            f'<line class="interval" x1="{x1:.3f}" x2="{x2:.3f}" y1="{y}" y2="{y}"/>'
            f'<line class="interval" x1="{x1:.3f}" x2="{x1:.3f}" '
            f'y1="{y - 7}" y2="{y + 7}"/>'
            f'<line class="interval" x1="{x2:.3f}" x2="{x2:.3f}" '
            f'y1="{y - 7}" y2="{y + 7}"/>'
            f'<circle class="estimate" cx="{xe:.3f}" cy="{y}" r="4"/>'
        )
    title = report_text(
        locale,
        en="Multiple-Comparison Intervals for Standard Deviations",
        ko="표준편차 다중 비교구간",
    )
    description = report_text(
        locale,
        en=(
            "Points are sample standard deviations; lines are Bonett-Nakayama "
            "multiple-comparison intervals."
        ),
        ko="점은 표본 표준편차, 선은 Bonett-Nakayama 다중 비교구간입니다.",
    )
    return (
        f'<svg role="img" aria-label="{_html_text(title)}" '
        f'viewBox="0 0 620 {height}">'
        f"<title>{_html_text(title)}</title>"
        f"<desc>{_html_text(description)}</desc>"
        f"{rows}</svg>"
    )
