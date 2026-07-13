import csv
import hashlib
import io
import json
import os
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.api.v1.schemas.analyses import (
    AnalysisResultCsvExportResponse,
    AnalysisResultEnvelope,
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
from app.services.analysis_run_execution import canonical_json_bytes
from app.services.analysis_run_execution import utc_now as _utc_now
from app.services.analysis_run_results import get_analysis_run_result
from app.services.regression_models import (
    REGRESSION_PREDICTION_METHOD_ID,
    iter_regression_prediction_rows,
)
from app.storage.atomic import atomic_replace, atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
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
ANALYSIS_RESULT_HTML_REPORT_SCHEMA_VERSION = 1
ANALYSIS_RESULT_HTML_REPORT_KIND: Literal["analysis_result_html_report"] = (
    "analysis_result_html_report"
)
ANALYSIS_RESULT_HTML_REPORT_FORMAT: Literal["analysis_result_html_report"] = (
    "analysis_result_html_report"
)
ANALYSIS_RESULT_HTML_REPORT_MEDIA_TYPE: Literal["text/html"] = "text/html"
ANALYSIS_RESULT_HTML_REPORT_TITLE = "DataLab Studio Analysis Report"
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


@dataclass(frozen=True)
class AnalysisResultExportDownload:
    content: bytes
    filename: str
    media_type: str
    sha256: str


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
    result = get_analysis_run_result(settings, prediction_id)
    if record.result_sha256 is None:
        raise ApiError(
            code="analysis_result_not_available",
            message="저장된 분석 결과가 아직 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    try:
        prediction = RegressionPredictionResponse.model_validate(result.result)
    except ValidationError as exc:
        raise ApiError(
            code="regression_prediction_result_invalid",
            message="저장된 회귀 예측 결과 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc

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
            for row in iter_regression_prediction_rows(settings, prediction_id):
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
        title=ANALYSIS_RESULT_HTML_REPORT_TITLE,
        section_count=len(rows),
    )


def get_analysis_result_export_download(
    settings: Settings,
    analysis_id: UUID,
    export_id: UUID,
) -> AnalysisResultExportDownload:
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

    export_path = _safe_analysis_export_path(settings.workspace_root, artifact.path)
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


def _safe_analysis_export_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="analysis_export_path_invalid",
            message="저장된 분석 결과 내보내기 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return workspace_root / relative_path


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
        suffix = "html"
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
) -> bytes:
    row_markup = "\n".join(
        "<tr>"
        f"<td>{_html_text(section)}</td>"
        f"<td><code>{_html_text(path)}</code></td>"
        f"<td>{_html_text(value)}</td>"
        "</tr>"
        for section, path, value in rows
    )
    warning_markup = "\n".join(
        "<li>"
        f"<strong>{_html_text(warning.code)}</strong>: "
        f"{_html_text(warning.message)} "
        f"<span>{_html_text(warning.severity)}</span>"
        "</li>"
        for warning in result.warnings
    )
    if not warning_markup:
        warning_markup = "<li>None</li>"
    method_specific_markup = _analysis_result_method_specific_report_section(result)

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src 'unsafe-inline'"
  >
  <title>{_html_text(ANALYSIS_RESULT_HTML_REPORT_TITLE)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; }}
    h1, h2 {{ margin: 0 0 12px; }}
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
  </style>
</head>
<body>
  <h1>{_html_text(ANALYSIS_RESULT_HTML_REPORT_TITLE)}</h1>
  <dl class="meta">
    <dt>Analysis ID</dt><dd>{_html_text(str(analysis_id))}</dd>
    <dt>Method</dt><dd>{_html_text(result.method_id)} v{_html_text(result.method_version)}</dd>
    <dt>Status</dt><dd>{_html_text(result.status)}</dd>
    <dt>Dataset Version</dt><dd>{_html_text(str(result.dataset_version_id))}</dd>
    <dt>Source Result SHA-256</dt><dd><code>{_html_text(source_result_sha256)}</code></dd>
    <dt>Created At</dt><dd>{_html_text(created_at)}</dd>
    <dt>Stale</dt><dd>{_html_text(str(stale).lower())}</dd>
  </dl>
  <h2>Warnings</h2>
  <ul>{warning_markup}</ul>
{method_specific_markup}
  <h2>Result Envelope</h2>
  <table>
    <thead><tr><th>Section</th><th>Path</th><th>Value</th></tr></thead>
    <tbody>
{row_markup}
    </tbody>
  </table>
</body>
</html>
"""
    return html.encode("utf-8")


def _html_text(value: object) -> str:
    return escape(str(value), quote=True)


def _analysis_result_method_specific_report_section(result: AnalysisResultEnvelope) -> str:
    payload = result.result
    if not isinstance(payload, dict):
        return ""
    summary_type = payload.get("summary_type")
    if summary_type == "descriptive_statistics":
        return _descriptive_statistics_report_section(payload)
    if summary_type == "graphical_summary":
        return _graphical_summary_report_section(payload)
    if summary_type == "normality_test":
        return _normality_report_section(payload)
    if summary_type == "equal_variances_test":
        return _equal_variances_report_section(payload)
    if summary_type in HYPOTHESIS_REPORT_SUMMARY_TYPES:
        return _hypothesis_report_section(payload, str(summary_type))
    if summary_type in CATEGORICAL_REPORT_SUMMARY_TYPES:
        return _categorical_report_section(payload, str(summary_type))
    if summary_type in REGRESSION_REPORT_SUMMARY_TYPES:
        return _regression_report_section(payload, str(summary_type))
    if summary_type in QUALITY_REPORT_SUMMARY_TYPES:
        return _quality_report_section(payload, str(summary_type))
    return ""


def _descriptive_statistics_report_section(payload: dict[str, object]) -> str:
    columns = payload.get("columns")
    if not isinstance(columns, list):
        return ""

    row_markup = "\n".join(
        _descriptive_statistics_report_row(column) for column in columns if isinstance(column, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>기술통계 요약</h2>
  <p>저장된 분석 결과의 기술통계 값을 재계산 없이 표시합니다.</p>
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


def _normality_report_section(payload: dict[str, object]) -> str:
    columns = payload.get("columns")
    if not isinstance(columns, list):
        return ""

    row_markup = "\n".join(
        _normality_report_row(column) for column in columns if isinstance(column, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>정규성 검정 요약</h2>
  <p>저장된 정규성 검정 결과의 Shapiro-Wilk, Anderson-Darling, 형상 통계량을 표시합니다.</p>
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


def _equal_variances_report_section(payload: dict[str, object]) -> str:
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

    return f"""
  <h2>등분산 검정 요약</h2>
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
  <h2>등분산 그룹 요약</h2>
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


def _hypothesis_report_section(payload: dict[str, object], summary_type: str) -> str:
    metric_markup = "\n".join(_hypothesis_metric_report_rows(payload, summary_type))
    group_markup = _hypothesis_groups_report_markup(payload.get("groups"))
    posthoc_markup = _hypothesis_posthoc_report_markup(payload.get("posthoc"))
    if not metric_markup and not group_markup and not posthoc_markup:
        return ""

    return f"""
  <h2>가설 검정 요약</h2>
  <p>저장된 hypothesis 결과의 핵심 검정값, 추정치, 신뢰구간, 효과크기를 표시합니다.</p>
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


def _hypothesis_groups_report_markup(groups: object) -> str:
    if not isinstance(groups, list):
        return ""
    row_markup = "\n".join(
        _hypothesis_group_report_row(group) for group in groups if isinstance(group, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>가설 검정 그룹 요약</h2>
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


def _hypothesis_posthoc_report_markup(posthoc: object) -> str:
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
    return f"""
  <h2>가설 검정 사후 비교</h2>
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


def _categorical_report_section(payload: dict[str, object], summary_type: str) -> str:
    metric_markup = "\n".join(_categorical_metric_report_rows(payload, summary_type))
    group_markup = _categorical_groups_report_markup(payload.get("groups"))
    contingency_markup = _categorical_contingency_report_markup(payload.get("contingency_table"))
    if not metric_markup and not group_markup and not contingency_markup:
        return ""

    return f"""
  <h2>범주형 분석 요약</h2>
  <p>저장된 categorical 결과의 검정값, 비율/차이, 신뢰구간, 효과크기를 표시합니다.</p>
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


def _categorical_groups_report_markup(groups: object) -> str:
    if not isinstance(groups, list):
        return ""
    row_markup = "\n".join(
        _categorical_group_report_row(group) for group in groups if isinstance(group, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>범주형 그룹 요약</h2>
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


def _categorical_contingency_report_markup(contingency_table: object) -> str:
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

    return f"""
  <h2>범주형 교차표 요약</h2>
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


def _regression_report_section(payload: dict[str, object], summary_type: str) -> str:
    metric_markup = "\n".join(_regression_metric_report_rows(payload, summary_type))
    pairs_markup = _regression_pairs_report_markup(payload.get("pairs"))
    coefficients_markup = _linear_model_coefficients_report_markup(payload.get("coefficients"))
    if not metric_markup and not pairs_markup and not coefficients_markup:
        return ""

    return f"""
  <h2>상관/회귀 분석 요약</h2>
  <p>저장된 correlation/regression 결과의 association, fit, coefficient 값을 표시합니다.</p>
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


def _regression_pairs_report_markup(pairs: object) -> str:
    if not isinstance(pairs, list):
        return ""
    row_markup = "\n".join(
        _regression_pair_report_row(pair) for pair in pairs if isinstance(pair, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>상관 쌍 요약</h2>
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


def _linear_model_coefficients_report_markup(coefficients: object) -> str:
    if not isinstance(coefficients, list):
        return ""
    row_markup = "\n".join(
        _linear_model_coefficient_report_row(coefficient)
        for coefficient in coefficients
        if isinstance(coefficient, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>선형모델 계수 요약</h2>
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


def _quality_report_section(payload: dict[str, object], summary_type: str) -> str:
    metric_markup = "\n".join(_quality_metric_report_rows(payload, summary_type))
    chart_markup = _quality_chart_summaries_report_markup(payload)
    signal_markup = _quality_signals_report_markup(payload.get("signals"))
    capability_markup = _quality_capability_report_markup(payload.get("capability"))
    gage_markup = _gage_variance_components_report_markup(payload.get("variance_components"))
    if not any((metric_markup, chart_markup, signal_markup, capability_markup, gage_markup)):
        return ""

    return f"""
  <h2>품질 관리 요약</h2>
  <p>저장된 quality 결과의 핵심 차트, 공정능력, Gage 진단 값을 표시합니다.</p>
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


def _quality_chart_summaries_report_markup(payload: dict[str, object]) -> str:
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

    return f"""
  <h2>품질 차트 요약</h2>
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


def _quality_signals_report_markup(signals: object) -> str:
    if not isinstance(signals, list):
        return ""
    row_markup = "\n".join(
        _quality_signal_report_row(signal) for signal in signals if isinstance(signal, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>품질 신호 요약</h2>
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


def _quality_capability_report_markup(capability: object) -> str:
    if not isinstance(capability, dict):
        return ""
    row_markup = "\n".join(
        _quality_capability_report_row(label, indices)
        for label, indices in capability.items()
        if isinstance(indices, dict)
    )
    if not row_markup:
        return ""

    return f"""
  <h2>공정능력 요약</h2>
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


def _gage_variance_components_report_markup(components: object) -> str:
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

    return f"""
  <h2>Gage R&amp;R 분산 요약</h2>
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
