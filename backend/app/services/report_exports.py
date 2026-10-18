"""Source-bound standalone HTML artifacts across existing workflow owners."""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError

from app.api.v1.schemas.analyses import AnalysisResultExportDeleteRequest
from app.api.v1.schemas.reports import (
    BayesianHistoryReportSource,
    CreateManagedReportRequest,
    LhsDesignReportSource,
    ManagedReportActionRequest,
    ManagedReportDescriptor,
    ManagedReportList,
    ReportSourceQuery,
    ReportSourceRef,
)
from app.core.config import Settings
from app.i18n.report_text import ReportLocale, report_text
from app.services.analysis_run_exports import (
    delete_analysis_result_export,
    get_analysis_result_export_deletion_preflight,
)
from app.services.dedicated_report_sources import report_source_is_stale
from app.services.report_source_contract import (
    VerifiedReportSource,
    canonical_report_source_json,
    report_source_sha256,
)
from app.services.report_sources import prepare_report_source, report_capability, source_error
from app.services.stored_report_primitives import report_table
from app.storage.factorial_analysis_assets import (
    FactorialAnalysisAsset,
    delete_asset,
    get_asset,
    insert_asset,
    list_assets,
)
from app.storage.managed_report_artifacts import (
    ManagedReportArtifact,
    create_managed_report,
    delete_managed_report,
    get_managed_report,
    list_managed_reports,
    read_managed_report,
)
from app.storage.metadata import (
    AnalysisArtifactRecord,
    get_analysis_artifact_record,
    get_analysis_run_record,
    list_analysis_artifact_records,
    metadata_db_path,
)
from app.storage.source_bound_artifacts import (
    insert_source_bound_artifact,
    read_source_bound_artifact,
)

MANAGED_ANALYSIS_REPORT_KIND = "managed_source_html_report"
_SOURCE_ADAPTER: TypeAdapter[ReportSourceRef] = TypeAdapter(ReportSourceRef)
_META_NAME = "statistical-twin-stored-report"


def create_report(
    settings: Settings, request: CreateManagedReportRequest
) -> ManagedReportDescriptor:
    source_sha = report_source_sha256(request.source)
    if request.expected_source_ref_sha256 != source_sha:
        raise source_error("stored_report_source_changed")
    verified = prepare_report_source(settings, request.source, request.locale)
    if _source_owner(request.source) != (verified.storage_kind, verified.owner_id):
        raise source_error("stored_report_identity_mismatch")
    capability = report_capability(verified, request.locale)
    if capability.report_level == "unsupported" or verified.definition is None:
        raise source_error("stored_report_payload_unsupported", 422)
    export_id = uuid4()
    created_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        "schema_version": 1,
        "export_id": str(export_id),
        "source": request.source.model_dump(mode="json"),
        "source_ref_sha256": source_sha,
        "locale": request.locale,
        "report_level": capability.report_level,
        "renderer_version": verified.definition.renderer_version,
        "created_at": created_at,
        "stale_at_export": verified.stale,
    }
    content = _render_html(verified, capability.model_dump(mode="json"), metadata, request.locale)
    sha256 = hashlib.sha256(content).hexdigest()
    if verified.storage_kind == "analysis":
        owner = get_analysis_run_record(settings.workspace_root, verified.owner_id)
        if owner is None or owner.result_sha256 != _analysis_source_sha(request.source):
            raise source_error("stored_report_source_changed")
        record = AnalysisArtifactRecord(
            str(export_id),
            verified.owner_id,
            MANAGED_ANALYSIS_REPORT_KIND,
            _analysis_report_path(verified.owner_id, str(export_id)),
            sha256,
            "text/html",
            created_at,
        )
        dependency = None
        if (
            request.source.kind == "regression_prediction"
            and request.source.prediction.storage == "completed_prediction"
        ):
            dependency = (
                str(request.source.prediction.prediction_artifact_id),
                request.source.prediction.expected_source_sha256,
            )
        insert_source_bound_artifact(
            settings.workspace_root,
            record,
            content,
            expected_source_sha256=_analysis_source_sha(request.source),
            dependency_artifact=dependency,
        )
    elif verified.storage_kind == "doe":
        source_analysis_sha = _doe_source_sha(request.source)
        dependency_asset = None
        if (
            request.source.kind == "regression_prediction"
            and request.source.prediction.storage == "doe_prediction"
        ):
            dependency_asset = (
                str(request.source.prediction.prediction_id),
                request.source.prediction.expected_source_sha256,
            )
        insert_asset(
            settings.workspace_root,
            FactorialAnalysisAsset(
                str(export_id),
                verified.owner_id,
                "html_report",
                2,
                request.locale,
                source_analysis_sha,
                sha256,
                "text/html",
                len(content),
                created_at,
            ),
            content,
            dependency_asset=dependency_asset,
        )
    else:
        if not isinstance(request.source, LhsDesignReportSource | BayesianHistoryReportSource):
            raise source_error("stored_report_source_kind_mismatch")
        record_managed = create_managed_report(
            settings.workspace_root,
            source=request.source,
            expected_source_ref_sha256=source_sha,
            content=content,
            locale=request.locale,
            renderer_id=verified.definition.renderer_id,
            renderer_version=verified.definition.renderer_version,
            report_level=capability.report_level,
            section_manifest_json=json.dumps(
                capability.model_dump(mode="json")["sections"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            created_at=created_at,
            report_id=str(export_id),
        )
        if record_managed.report_id != str(export_id):
            raise source_error("stored_report_identity_mismatch")
    return _descriptor(content, str(export_id), sha256, created_at, verified.stale)


def list_reports(settings: Settings, request: ReportSourceQuery) -> ManagedReportList:
    verified = prepare_report_source(settings, request.source, request.locale)
    source_sha = report_source_sha256(request.source)
    candidates: list[ManagedReportDescriptor] = []
    if verified.storage_kind == "analysis":
        for artifact in list_analysis_artifact_records(settings.workspace_root, verified.owner_id):
            if artifact.kind == MANAGED_ANALYSIS_REPORT_KIND:
                candidates.append(_analysis_descriptor(settings, artifact))
    elif verified.storage_kind == "doe":
        for asset in list_assets(settings.workspace_root, verified.owner_id, "html_report"):
            if asset.schema_version != 2:
                continue  # Legacy factorial assets keep their existing reader/UI.
            loaded = get_asset(settings.workspace_root, verified.owner_id, asset.asset_id)
            if loaded is None:
                raise source_error("stored_report_not_found", 404)
            candidates.append(
                _descriptor(
                    loaded[1], asset.asset_id, asset.sha256, asset.created_at, verified.stale
                )
            )
    else:
        assert isinstance(request.source, LhsDesignReportSource | BayesianHistoryReportSource)
        candidates.extend(
            _managed_descriptor(settings, record)
            for record in list_managed_reports(
                settings.workspace_root,
                source=request.source,
                limit=100,
            )
        )
    return ManagedReportList(
        items=sorted(
            (
                item
                for item in candidates
                if item.source_ref_sha256 == source_sha and item.locale == request.locale
            ),
            key=lambda item: (item.created_at, str(item.export_id)),
            reverse=True,
        )
    )


def get_report(settings: Settings, export_id: UUID) -> ManagedReportDescriptor:
    descriptor, _ = _find_report(settings, str(export_id))
    return descriptor


def download_report(
    settings: Settings, export_id: UUID, request: ManagedReportActionRequest
) -> bytes:
    descriptor, content = _find_report(settings, str(export_id))
    _check_action(descriptor, request)
    return content


def delete_report(settings: Settings, export_id: UUID, request: ManagedReportActionRequest) -> None:
    descriptor, _ = _find_report(settings, str(export_id))
    _check_action(descriptor, request)
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        analysis_owner = connection.execute(
            "SELECT analysis_id FROM analysis_artifacts WHERE artifact_id=? AND kind=?",
            (str(export_id), MANAGED_ANALYSIS_REPORT_KIND),
        ).fetchone()
        doe_owner = connection.execute(
            "SELECT analysis_id FROM experiment_design_analysis_assets "
            "WHERE asset_id=? AND kind='html_report' AND schema_version=2",
            (str(export_id),),
        ).fetchone()
    if analysis_owner:
        owner_id = UUID(analysis_owner[0])
        preflight = get_analysis_result_export_deletion_preflight(settings, owner_id, export_id)
        if preflight.sha256 != request.expected_sha256:
            raise source_error("stored_report_deletion_conflict")
        delete_analysis_result_export(
            settings,
            owner_id,
            export_id,
            AnalysisResultExportDeleteRequest(
                confirmation_analysis_id=owner_id,
                confirmation_export_id=export_id,
                expected_deletion_manifest_sha256=preflight.deletion_manifest_sha256,
            ),
        )
    elif doe_owner:
        delete_asset(settings.workspace_root, doe_owner[0], str(export_id), request.expected_sha256)
    else:
        delete_managed_report(
            settings.workspace_root,
            report_id=str(export_id),
            expected_sha256=request.expected_sha256,
            expected_source_ref_sha256=descriptor.source_ref_sha256,
        )


def _check_action(descriptor: ManagedReportDescriptor, request: ManagedReportActionRequest) -> None:
    if (
        descriptor.sha256 != request.expected_sha256
        or descriptor.source_ref_sha256 != report_source_sha256(request.source)
    ):
        raise source_error("stored_report_source_changed")


def _find_report(settings: Settings, export_id: str) -> tuple[ManagedReportDescriptor, bytes]:
    managed = get_managed_report(settings.workspace_root, export_id)
    if managed is not None:
        content = read_managed_report(settings.workspace_root, managed)
        return _managed_descriptor(settings, managed, content), content
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        analysis = connection.execute(
            "SELECT analysis_id FROM analysis_artifacts WHERE artifact_id=? AND kind=?",
            (export_id, MANAGED_ANALYSIS_REPORT_KIND),
        ).fetchone()
        doe = connection.execute(
            "SELECT analysis_id FROM experiment_design_analysis_assets "
            "WHERE asset_id=? AND kind='html_report' AND schema_version=2",
            (export_id,),
        ).fetchone()
    if analysis:
        artifact = get_analysis_artifact_record(settings.workspace_root, analysis[0], export_id)
        if artifact is None:
            raise source_error("stored_report_not_found", 404)
        content = read_source_bound_artifact(settings.workspace_root, artifact)
        return _analysis_descriptor(settings, artifact, content), content
    if doe:
        loaded = get_asset(settings.workspace_root, doe[0], export_id)
        if loaded is None:
            raise source_error("stored_report_not_found", 404)
        record, content = loaded
        descriptor = _descriptor(content, export_id, record.sha256, record.created_at, False)
        if (
            _source_owner(descriptor.source) != ("doe", record.analysis_id)
            or _doe_source_sha(descriptor.source) != record.source_analysis_sha256
        ):
            raise source_error("stored_report_identity_mismatch")
        return descriptor.model_copy(
            update={"stale": report_source_is_stale(settings, descriptor.source)}
        ), content
    raise source_error("stored_report_not_found", 404)


def _analysis_descriptor(
    settings: Settings, artifact: AnalysisArtifactRecord, content: bytes | None = None
) -> ManagedReportDescriptor:
    if (
        artifact.path != _analysis_report_path(artifact.analysis_id, artifact.artifact_id)
        or artifact.media_type != "text/html"
    ):
        raise source_error("stored_report_identity_mismatch")
    owner = get_analysis_run_record(settings.workspace_root, artifact.analysis_id)
    if owner is None:
        raise source_error("stored_report_not_found", 404)
    descriptor = _descriptor(
        read_source_bound_artifact(settings.workspace_root, artifact)
        if content is None
        else content,
        artifact.artifact_id,
        artifact.sha256,
        artifact.created_at,
        owner.stale,
    )
    if _source_owner(descriptor.source) != ("analysis", artifact.analysis_id):
        raise source_error("stored_report_identity_mismatch")
    return descriptor.model_copy(
        update={"stale": report_source_is_stale(settings, descriptor.source)}
    )


def _managed_descriptor(
    settings: Settings, record: ManagedReportArtifact, content: bytes | None = None
) -> ManagedReportDescriptor:
    descriptor = _descriptor(
        read_managed_report(settings.workspace_root, record) if content is None else content,
        record.report_id,
        record.sha256,
        record.created_at,
        False,
    )
    if (
        descriptor.source_ref_sha256 != record.source_ref_sha256
        or canonical_report_source_json(descriptor.source) != record.source_ref_json
        or descriptor.locale != record.locale
        or descriptor.report_level != record.report_level
        or descriptor.renderer_version != record.renderer_version
        or descriptor.size_bytes != record.size_bytes
    ):
        raise source_error("stored_report_identity_mismatch")
    return descriptor.model_copy(
        update={"stale": report_source_is_stale(settings, descriptor.source)}
    )


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            attributes = dict(attrs)
            if attributes.get("name") == _META_NAME:
                self.values.append(attributes.get("content") or "")


def _descriptor(
    content: bytes, export_id: str, sha256: str, created_at: str, stale: bool
) -> ManagedReportDescriptor:
    if hashlib.sha256(content).hexdigest() != sha256 or len(content) > 16 * 1024 * 1024:
        raise source_error("stored_report_checksum_mismatch")
    try:
        parser = _MetadataParser()
        parser.feed(content.decode("utf-8"))
        if len(parser.values) != 1 or len(parser.values[0]) > 100000:
            raise ValueError("report metadata")
        metadata = json.loads(base64.b64decode(parser.values[0], validate=True))
        source = _SOURCE_ADAPTER.validate_python(metadata["source"])
        if (
            metadata["schema_version"] != 1
            or metadata["export_id"] != export_id
            or metadata["created_at"] != created_at
            or metadata["source_ref_sha256"] != report_source_sha256(source)
        ):
            raise ValueError("report metadata identity")
        return ManagedReportDescriptor(
            export_id=UUID(export_id),
            source=source,
            source_ref_sha256=metadata["source_ref_sha256"],
            locale=metadata["locale"],
            report_level=metadata["report_level"],
            renderer_version=metadata["renderer_version"],
            sha256=sha256,
            size_bytes=len(content),
            created_at=created_at,
            stale=stale,
        )
    except (ValueError, KeyError, TypeError, UnicodeError, ValidationError) as exc:
        raise source_error("stored_report_identity_mismatch") from exc


def _doe_source_sha(source: ReportSourceRef) -> str:
    if source.kind == "doe_analysis":
        return source.expected_source_sha256
    if source.kind == "doe_optimizer_result" and source.optimizer.workflow == "response_surface":
        return source.optimizer.expected_source_sha256
    if source.kind == "regression_prediction" and source.prediction.storage == "doe_prediction":
        return source.prediction.source.expected_source_sha256
    raise source_error("stored_report_source_kind_mismatch")


def _source_owner(source: ReportSourceRef) -> tuple[str, str]:
    if source.kind == "analysis_run":
        return "analysis", str(source.analysis_id)
    if source.kind == "doe_analysis":
        return "doe", str(source.analysis_id)
    if source.kind == "doe_optimizer_result":
        if source.optimizer.workflow == "regression":
            return "analysis", str(source.optimizer.analysis_id)
        return "doe", str(source.optimizer.optimization_id)
    if source.kind == "regression_prediction":
        if source.prediction.storage == "analysis_run":
            return "analysis", str(source.prediction.analysis_id)
        if source.prediction.storage == "completed_prediction":
            return "analysis", str(source.prediction.source_analysis_id)
        return "doe", str(source.prediction.source.analysis_id)
    if source.kind == "lhs_design_revision":
        return "managed", str(source.design_version_id)
    return "managed", str(source.study_version_id)


def _analysis_source_sha(source: ReportSourceRef) -> str:
    if source.kind == "analysis_run":
        return source.expected_source_sha256
    if source.kind == "doe_optimizer_result" and source.optimizer.workflow == "regression":
        return source.optimizer.expected_source_sha256
    if source.kind == "regression_prediction":
        if source.prediction.storage == "analysis_run":
            return source.prediction.expected_source_sha256
        if source.prediction.storage == "completed_prediction":
            return source.prediction.source_result_sha256
    raise source_error("stored_report_source_kind_mismatch")


def _analysis_report_path(owner_id: str, export_id: str) -> str:
    return (
        Path("workspaces") / "analyses" / owner_id / "exports" / f"{export_id}.managed-report.html"
    ).as_posix()


def _render_html(
    verified: VerifiedReportSource,
    capability: dict[str, Any],
    metadata: dict[str, Any],
    locale: ReportLocale,
) -> bytes:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    encoded = base64.b64encode(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).decode("ascii")
    sections = report_table(
        [text("Section", "섹션"), text("Status", "상태"), text("Reason", "사유")],
        [
            (section["title"], section["status"], section["reason"])
            for section in capability["sections"]
        ],
    )
    provenance = report_table(
        [text("Field", "항목"), text("Value", "값")],
        [
            (text("Source kind", "원본 종류"), verified.source.kind),
            (text("Owner ID", "소유 ID"), verified.owner_id),
            ("Source reference SHA-256", metadata["source_ref_sha256"]),
            (text("Source creation time", "원본 생성 시각"), verified.created_at),
            (text("Report creation time", "보고서 생성 시각"), metadata["created_at"]),
            (text("Report level", "보고서 수준"), capability["report_level"]),
            (text("Renderer version", "렌더러 버전"), capability["renderer_version"]),
            (text("Marked stale", "오래된 결과 표시"), str(verified.stale)),
        ],
    )
    description = text(
        "Stored-result report. No analysis, prediction, or source-data reread "
        "was performed during export.",
        "저장 결과 보고서입니다. 내보내기 시 분석, 예측 또는 "
        "원자료 읽기를 다시 수행하지 않았습니다.",
    )
    html = (
        '<!doctype html><html lang="' + locale + '"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'\">"
        f'<meta name="{_META_NAME}" content="{encoded}"><title>{escape(verified.title)}</title>'
        "<style>body{font:14px system-ui,sans-serif;color:#17212b;margin:24px;max-width:1200px}"
        "h1{font-size:24px}h2{font-size:20px}h3{font-size:17px;margin-top:28px}"
        ".table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:12px 0}"
        "td,th{border:1px solid #dce1e6;padding:7px;text-align:left;overflow-wrap:anywhere}"
        "th{background:#f0f3f6}svg{display:block;max-width:100%;height:auto}"
        "p{line-height:1.6}svg text{fill:#17212b;font:11px system-ui,sans-serif}"
        "@media print{body{margin:10mm}.table-wrap{overflow:visible}tr{break-inside:avoid}}"
        "</style></head><body>"
        f"<h1>{escape(verified.title)}</h1><p>{escape(description)}</p>"
        + provenance
        + f'<h2>{escape(text("Included and unavailable sections", "포함 및 미제공 섹션"))}</h2>'
        + sections
        + verified.body.render()
        + "</body></html>"
    )
    return html.encode("utf-8")
