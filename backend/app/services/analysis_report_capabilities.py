"""One report contract for catalog, preflight and HTML output."""

from uuid import UUID

from app.api.v1.schemas.report_capabilities import AnalysisReportCapability, ReportSectionCapability
from app.core.config import Settings
from app.i18n.report_text import ReportLocale
from app.services.analysis_report_source import load_analysis_report_source
from app.services.analysis_run_exports import prepare_analysis_report


def get_analysis_report_capability(
    settings: Settings, analysis_id: UUID, locale: ReportLocale = "en"
) -> AnalysisReportCapability:
    stored = load_analysis_report_source(settings, analysis_id)
    prepared = prepare_analysis_report(stored.envelope, locale)
    payload = stored.envelope.result or {}
    summary = payload.get("summary_type")
    schema = payload.get("schema_version")
    definition = prepared.definition
    assert stored.record.result_sha256 is not None
    return AnalysisReportCapability(
        analysis_id=analysis_id,
        method_id=stored.record.method_id,
        summary_type=summary if isinstance(summary, str) else None,
        result_schema_version=schema if type(schema) is int else None,
        source_result_sha256=stored.record.result_sha256,
        stale=stored.record.stale,
        locale=locale,
        renderer_id=None if definition is None else definition.renderer_id,
        renderer_version=None if definition is None else definition.renderer_version,
        variant_id=prepared.body.variant_id if prepared.body.variant_id != "unsupported" else None,
        report_level=prepared.level,
        sections=[
            ReportSectionCapability(
                section_id=section.section_id,
                title=section.title,
                status=section.status,
                reason=section.reason,
            )
            for section in prepared.body.sections
        ],
        reason=prepared.body.unsupported_reason,
        html_available=prepared.level != "unsupported",
    )
