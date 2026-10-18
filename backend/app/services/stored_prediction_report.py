"""Read saved regression prediction rows, not current dataset values."""

from __future__ import annotations

import hashlib
import json
from html import escape
from typing import Any
from uuid import UUID

from app.api.v1.schemas.analyses import (
    RegressionPastedPredictionResponse,
    RegressionPastedPredictionRow,
    RegressionPredictionResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.i18n.report_text import ReportLocale, report_text
from app.services.analysis_report_source import _safe_owned_path, load_analysis_report_source
from app.services.regression_models import (
    _iter_regression_prediction_rows,
    _load_prediction_rows_context,
    _prediction_rows_relative_path,
    _PredictionStoredConfig,
    _validate_prediction_rows_relationship,
)
from app.services.report_contract import (
    ReportBody,
    ReportDefinition,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
)
from app.services.stored_report_primitives import report_table
from app.storage.metadata import AnalysisArtifactRecord, list_analysis_artifact_records

PREDICTION_REPORT_DEFINITION = ReportDefinition(
    "regression.predict",
    "stored_regression_prediction",
    (1, 2, 3),
    "stored_regression_prediction",
    "1.0.0",
    (
        ReportVariantDefinition(
            "stored_prediction",
            (
                ReportSectionDefinition("provenance", True),
                ReportSectionDefinition("inputs"),
                ReportSectionDefinition("predictions", True),
                ReportSectionDefinition("warnings"),
            ),
        ),
    ),
)


def load_stored_prediction_report(
    settings: Settings, analysis_id: UUID, expected_sha256: str, locale: ReportLocale
) -> tuple[dict[str, Any], ReportBody, str, bool]:
    stored = load_analysis_report_source(settings, analysis_id)
    record = stored.record
    if record.result_sha256 != expected_sha256:
        raise _error("stored_report_source_changed")
    try:
        config = json.loads(record.config_json)
        if record.method_id == "regression.predict":
            saved = RegressionPredictionResponse.model_validate(stored.envelope.result)
            typed_config = _PredictionStoredConfig.model_validate(config)
            _safe_owned_path(
                settings.workspace_root, _prediction_rows_relative_path(str(analysis_id)).as_posix()
            )
            context = _load_prediction_rows_context(settings, analysis_id, typed_config)
            _safe_owned_path(
                settings.workspace_root, str(context.path.relative_to(settings.workspace_root))
            )
            _validate_prediction_rows_relationship(context.header, typed_config)
            rows = [
                row.model_dump(mode="json") for row in _iter_regression_prediction_rows(context)
            ]
            payload = saved.model_dump(mode="json")
            if (
                saved.prediction_id != analysis_id
                or typed_config.prediction_id != analysis_id
                or typed_config.analysis_id != analysis_id
                or typed_config.model_id != saved.model_id
                or typed_config.model_manifest_sha256 != saved.model_manifest_sha256
                or typed_config.source_analysis_id != saved.source_analysis_id
                or typed_config.target_dataset_version_id != saved.target_dataset_version_id
                or typed_config.target_schema_hash != saved.target_schema_hash
                or typed_config.confidence_level != saved.confidence_level
                or typed_config.method_version != record.method_version
                or len(rows) != saved.row_count_predicted
                or saved.row_count_total != saved.row_count_predicted + saved.row_count_excluded
                or rows[: len(saved.rows)] != payload["rows"]
                or payload["provenance"] != stored.envelope.provenance.model_dump(mode="json")
            ):
                raise ValueError("prediction relationships")
            payload["rows"] = rows
            input_section = ReportSection(
                "inputs",
                _text(locale, "Prediction inputs", "예측 입력"),
                "missing",
                reason="legacy_dataset_prediction_does_not_store_input_values",
            )
        elif record.method_id == "regression.predict_pasted":
            saved_pasted = RegressionPastedPredictionResponse.model_validate(stored.envelope.result)
            payload = saved_pasted.model_dump(mode="json")
            artifacts = list_analysis_artifact_records(settings.workspace_root, str(analysis_id))
            inputs = _json_artifact(
                settings,
                artifacts,
                analysis_id,
                "regression_pasted_prediction_input",
                "pasted_input.json",
            )
            stored_rows = _json_artifact(
                settings,
                artifacts,
                analysis_id,
                "regression_pasted_prediction_rows",
                "prediction_rows.json",
            )
            rows = [
                RegressionPastedPredictionRow.model_validate(row).model_dump(mode="json")
                for row in stored_rows["rows"]
            ]
            if (
                saved_pasted.prediction_id != analysis_id
                or config.get("model_id") != str(saved_pasted.model_id)
                or config.get("model_manifest_sha256") != saved_pasted.model_manifest_sha256
                or inputs.get("model_manifest_sha256") != saved_pasted.model_manifest_sha256
                or config.get("normalized_input_sha256") != saved_pasted.normalized_input_sha256
                or inputs.get("normalized_input_sha256") != saved_pasted.normalized_input_sha256
                or inputs.get("model_id") != str(saved_pasted.model_id)
                or stored_rows.get("model_id") != str(saved_pasted.model_id)
                or config.get("confidence_level") != saved_pasted.confidence_level
                or len(rows) != saved_pasted.row_count_predicted
                or rows[: len(saved_pasted.rows)] != payload["rows"]
                or len({row["row_index"] for row in rows}) != len(rows)
            ):
                raise ValueError("pasted relationships")
            payload["rows"] = rows
            mappings = inputs["mappings"]
            input_section = ReportSection(
                "inputs",
                _text(locale, "Exact prediction inputs", "정확한 예측 입력"),
                "rendered",
                report_table(
                    [_text(locale, "Row", "행")] + [str(item["display_name"]) for item in mappings],
                    [
                        [row["row_index"] + 1]
                        + [row["predictor_values"][item["source_column_id"]] for item in mappings]
                        for row in rows
                    ],
                ),
            )
        else:
            raise _error("stored_report_source_kind_mismatch")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise _error("stored_prediction_report_invalid") from exc
    return payload, _render(payload, input_section, locale), record.created_at, record.stale


def _json_artifact(
    settings: Settings,
    artifacts: list[AnalysisArtifactRecord],
    analysis_id: UUID,
    kind: str,
    filename: str,
) -> dict[str, Any]:
    matches = [item for item in artifacts if item.kind == kind]
    if len(matches) != 1:
        raise ValueError("prediction artifact")
    artifact = matches[0]
    if (
        artifact.path != f"workspaces/analyses/{analysis_id}/{filename}"
        or artifact.media_type != "application/json"
    ):
        raise ValueError("prediction artifact path")
    path = _safe_owned_path(settings.workspace_root, artifact.path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("prediction artifact bound")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != artifact.sha256:
        raise ValueError("prediction artifact hash")
    payload = json.loads(content)
    if (
        payload.get("artifact_schema_version") != 1
        or payload.get("artifact_kind") != kind
        or payload.get("prediction_id") != str(analysis_id)
    ):
        raise ValueError("prediction artifact owner")
    return payload


def _render(
    payload: dict[str, Any], input_section: ReportSection, locale: ReportLocale
) -> ReportBody:
    def text(en: str, ko: str) -> str:
        return _text(locale, en, ko)

    provenance = report_table(
        [text("Field", "항목"), text("Value", "값")],
        [
            ("Prediction ID", payload["prediction_id"]),
            ("Model ID", payload["model_id"]),
            ("Model manifest SHA-256", payload["model_manifest_sha256"]),
            (text("Source analysis ID", "원본 분석 ID"), payload.get("source_analysis_id")),
            (text("Confidence level", "신뢰수준"), payload["confidence_level"]),
            (text("Calculated rows", "계산 행 수"), payload["row_count_predicted"]),
            (text("Excluded rows", "제외 행 수"), payload["row_count_excluded"]),
            (text("Uncertainty", "불확실성"), payload.get("prediction_uncertainty_kind")),
            (
                text("Interval unavailability reason", "구간 미제공 사유"),
                payload.get("interval_unavailability_reason"),
            ),
        ],
    )
    table_rows = []
    warnings: list[tuple[int, str]] = []
    global_warnings = [
        (item.get("code"), item.get("message"), item.get("count"))
        for item in payload.get("warnings", [])
    ]
    for row in payload["rows"]:
        mean_ci = row.get("mean_confidence_interval")
        pi = row.get("prediction_interval")
        table_rows.append(
            [
                row["row_index"] + 1,
                row["predicted_mean"],
                None if mean_ci is None else mean_ci["lower"],
                None if mean_ci is None else mean_ci["upper"],
                None if pi is None else pi["lower"],
                None if pi is None else pi["upper"],
            ]
        )
        warnings.extend((row["row_index"] + 1, code) for code in row.get("warnings", []))
    return ReportBody(
        "stored_prediction",
        (
            ReportSection(
                "provenance",
                text("Model and prediction identity", "모델 및 예측 식별 정보"),
                "rendered",
                provenance,
            ),
            input_section,
            ReportSection(
                "predictions",
                text("Stored predictions", "저장 예측값"),
                "rendered",
                report_table(
                    [
                        text("Analysis row", "분석 행"),
                        text("Predicted mean", "예측 평균"),
                        text("Mean CI lower", "평균 신뢰구간 하한"),
                        text("Mean CI upper", "평균 신뢰구간 상한"),
                        text("New-observation PI lower", "새 관측값 예측구간 하한"),
                        text("New-observation PI upper", "새 관측값 예측구간 상한"),
                    ],
                    table_rows,
                ),
            ),
            ReportSection(
                "warnings",
                text("Warnings and limitations", "경고와 해석 제한"),
                "rendered",
                "<p>"
                + escape(
                    text(
                        "Missing intervals are unavailable, not zero-width intervals. "
                        "All saved prediction rows are included; no prediction is recalculated.",
                        "없는 구간은 미제공 값이며 길이가 0인 구간이 아닙니다. "
                        "저장된 전체 예측 행을 출력하며 예측을 다시 계산하지 않습니다.",
                    )
                )
                + "</p>"
                + report_table(
                    [
                        text("Warning code", "경고 코드"),
                        text("Original warning", "원문 경고"),
                        text("Count", "건수"),
                    ],
                    global_warnings,
                )
                + report_table(
                    [text("Analysis row", "분석 행"), text("Warning code", "경고 코드")], warnings
                ),
            ),
        ),
    )


def _text(locale: ReportLocale, en: str, ko: str) -> str:
    return report_text(locale, en=en, ko=ko)


def _error(code: str) -> ApiError:
    return ApiError(
        code=code, message="The saved prediction report source is inconsistent.", status_code=409
    )
