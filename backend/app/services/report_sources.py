"""Dispatch exact stored-source references without running an analysis."""

from __future__ import annotations

import json
import sqlite3
from uuid import UUID

from app.api.v1.schemas.report_capabilities import ReportSectionCapability
from app.api.v1.schemas.reports import (
    AnalysisPredictionRef,
    AnalysisRunReportSource,
    CompletedPredictionRef,
    RegressionPredictionReportSource,
    ReportSourceDescriptor,
    ReportSourceKind,
    ReportSourceList,
    ReportSourceRef,
    StoredReportCapability,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.i18n.report_text import ReportLocale
from app.services.analysis_report_source import load_analysis_report_source
from app.services.analysis_run_exports import prepare_analysis_report
from app.services.completed_prediction_report import (
    COMPLETED_PREDICTION_REPORT_DEFINITION,
    render_completed_prediction,
)
from app.services.completed_predictions import load_completed_prediction
from app.services.report_contract import assess_report_body
from app.services.report_source_contract import VerifiedReportSource, report_source_sha256
from app.services.stored_prediction_report import (
    PREDICTION_REPORT_DEFINITION,
    load_stored_prediction_report,
)
from app.storage.metadata import get_analysis_run_record, metadata_db_path


def prepare_report_source(
    settings: Settings, source: ReportSourceRef, locale: ReportLocale
) -> VerifiedReportSource:
    if source.kind == "analysis_run":
        stored = load_analysis_report_source(settings, source.analysis_id)
        if stored.record.result_sha256 != source.expected_source_sha256:
            raise source_error("stored_report_source_changed")
        if stored.record.method_id in {
            "regression.predict",
            "regression.predict_pasted",
            "regression.linear_model_optimizer",
        }:
            raise source_error("stored_report_source_kind_mismatch")
        prepared = prepare_analysis_report(stored.envelope, locale)
        return VerifiedReportSource(
            source,
            stored.envelope.model_dump(mode="json"),
            stored.record.method_id,
            stored.record.created_at,
            stored.record.stale,
            f"/reports?analysis_id={source.analysis_id}",
            "analysis",
            str(source.analysis_id),
            prepared.definition,
            prepared.body,
        )
    if source.kind == "regression_prediction":
        prediction = source.prediction
        if prediction.storage == "completed_prediction":
            try:
                payload, record = load_completed_prediction(settings, prediction)
            except ApiError as exc:
                if exc.code == "completed_prediction_not_found":
                    raise source_error("stored_report_source_changed") from exc
                raise
            source_run = get_analysis_run_record(settings.workspace_root, record.analysis_id)
            if source_run is None or source_run.result_sha256 != prediction.source_result_sha256:
                raise source_error("stored_report_source_changed")
            return VerifiedReportSource(
                source,
                payload,
                f"{prediction.family} prediction",
                record.created_at,
                source_run.stale,
                "/analysis/regression/"
                + source_run.method_id
                + f"?analysis_id={record.analysis_id}&section=prediction",
                "analysis",
                record.analysis_id,
                COMPLETED_PREDICTION_REPORT_DEFINITION,
                render_completed_prediction(payload, locale),
            )
        if prediction.storage == "analysis_run":
            payload, body, created, stale = load_stored_prediction_report(
                settings,
                prediction.analysis_id,
                prediction.expected_source_sha256,
                locale,
            )
            return VerifiedReportSource(
                source,
                payload,
                "Regression prediction",
                created,
                stale,
                f"/analysis/regression/regression.predict?prediction_id={prediction.analysis_id}",
                "analysis",
                str(prediction.analysis_id),
                PREDICTION_REPORT_DEFINITION,
                body,
            )
    from app.services.dedicated_report_sources import prepare_dedicated_report_source

    return prepare_dedicated_report_source(settings, source, locale)


def report_capability(
    verified: VerifiedReportSource, locale: ReportLocale
) -> StoredReportCapability:
    definition = verified.definition
    level = "unsupported" if definition is None else assess_report_body(definition, verified.body)
    return StoredReportCapability(
        source=verified.source,
        source_ref_sha256=report_source_sha256(verified.source),
        title=verified.title,
        locale=locale,
        stale=verified.stale,
        report_level=level,
        renderer_id=None if definition is None else definition.renderer_id,
        renderer_version=None if definition is None else definition.renderer_version,
        sections=[
            ReportSectionCapability(
                section_id=item.section_id,
                title=item.title,
                status=item.status,
                reason=item.reason,
            )
            for item in verified.body.sections
        ],
        reason=verified.body.unsupported_reason,
        html_available=level != "unsupported",
    )


def list_report_sources(
    settings: Settings,
    *,
    source_kind: ReportSourceKind,
    limit: int = 50,
    offset: int = 0,
) -> ReportSourceList:
    if source_kind not in {"analysis_run", "regression_prediction"}:
        from app.services.dedicated_report_sources import list_dedicated_report_sources

        return list_dedicated_report_sources(settings, source_kind, limit, offset)
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        if source_kind == "analysis_run":
            rows = connection.execute(
                "SELECT 'analysis',analysis_id,analysis_id,created_at FROM analysis_runs "
                "WHERE status='succeeded' AND result_sha256 IS NOT NULL "
                "AND method_id NOT IN ('regression.predict','regression.predict_pasted',"
                "'regression.linear_model_optimizer') "
                "ORDER BY created_at DESC,analysis_id DESC LIMIT ? OFFSET ?",
                (limit + 1, offset),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM (SELECT 'prediction_run' AS storage,analysis_id AS item_id,"
                "analysis_id AS owner_id,created_at FROM analysis_runs WHERE status='succeeded' "
                "AND result_sha256 IS NOT NULL "
                "AND method_id IN ('regression.predict','regression.predict_pasted') "
                "UNION ALL SELECT 'completed',a.artifact_id,a.analysis_id,a.created_at "
                "FROM analysis_artifacts a JOIN analysis_runs r USING(analysis_id) "
                "WHERE a.kind IN ('gp_completed_prediction','pls_completed_prediction') "
                "AND r.status='succeeded' AND r.result_sha256 IS NOT NULL "
                "UNION ALL SELECT 'doe_prediction',asset_id,analysis_id,created_at "
                "FROM experiment_design_analysis_assets WHERE kind='prediction') "
                "ORDER BY created_at DESC,item_id DESC LIMIT ? OFFSET ?",
                (limit + 1, offset),
            ).fetchall()
    items = []
    for storage, item_id, owner_id, created_at in rows[:limit]:
        if storage == "doe_prediction":
            from app.services.dedicated_report_sources import doe_prediction_source_descriptor

            items.append(doe_prediction_source_descriptor(settings, item_id))
            continue
        record = get_analysis_run_record(settings.workspace_root, owner_id)
        if record is None or record.result_sha256 is None:
            raise source_error("stored_report_source_changed")
        source: ReportSourceRef
        if storage == "analysis":
            source = AnalysisRunReportSource(
                analysis_id=UUID(item_id), expected_source_sha256=record.result_sha256
            )
        elif storage == "prediction_run":
            source = RegressionPredictionReportSource(
                prediction=AnalysisPredictionRef(
                    analysis_id=UUID(item_id),
                    expected_source_sha256=record.result_sha256,
                )
            )
        else:
            source = completed_prediction_source(settings, owner_id, item_id)
        items.append(
            ReportSourceDescriptor(
                source=source,
                source_ref_sha256=report_source_sha256(source),
                title=record.method_id + (" prediction" if storage == "completed" else ""),
                created_at=created_at,
                stale=record.stale,
                open_target=f"/reports?analysis_id={record.analysis_id}",
            )
        )
    return ReportSourceList(items=items, limit=limit, offset=offset, has_more=len(rows) > limit)


def completed_prediction_source(
    settings: Settings, owner_id: str, artifact_id: str
) -> RegressionPredictionReportSource:
    from app.storage.metadata import get_analysis_artifact_record
    from app.storage.source_bound_artifacts import read_source_bound_artifact

    artifact = get_analysis_artifact_record(settings.workspace_root, owner_id, artifact_id)
    if artifact is None or artifact.kind not in {
        "gp_completed_prediction",
        "pls_completed_prediction",
    }:
        raise source_error("completed_prediction_not_found", 404)
    try:
        payload = json.loads(read_source_bound_artifact(settings.workspace_root, artifact))
        prediction = CompletedPredictionRef(
            family=payload["family"],
            source_analysis_id=payload["source_analysis_id"],
            source_result_sha256=payload["source_result_sha256"],
            model_id=payload["model_id"],
            model_manifest_sha256=payload["model_manifest_sha256"],
            prediction_artifact_id=UUID(artifact_id),
            expected_source_sha256=artifact.sha256,
        )
        load_completed_prediction(settings, prediction)
    except (ValueError, KeyError, TypeError) as exc:
        raise source_error("completed_prediction_corrupt") from exc
    return RegressionPredictionReportSource(prediction=prediction)


def source_error(code: str, status_code: int = 409) -> ApiError:
    return ApiError(
        code=code,
        message="The exact saved report source could not be verified.",
        status_code=status_code,
    )
