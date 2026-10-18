"""Shared immutable source boundary for dedicated report adapters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from app.api.v1.schemas.reports import ReportSourceRef
from app.services.report_contract import ReportBody, ReportDefinition


def canonical_report_source_json(source: ReportSourceRef) -> str:
    return json.dumps(
        source.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def report_source_sha256(source: ReportSourceRef) -> str:
    return hashlib.sha256(canonical_report_source_json(source).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VerifiedReportSource:
    source: ReportSourceRef
    payload: dict[str, Any]
    title: str
    created_at: str
    stale: bool
    open_target: str
    storage_kind: Literal["analysis", "doe", "managed"]
    owner_id: str
    definition: ReportDefinition | None
    body: ReportBody
