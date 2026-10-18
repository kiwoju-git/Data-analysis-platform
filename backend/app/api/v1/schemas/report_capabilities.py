"""Stored-result report support, separate from method execution availability."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportSectionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    core: bool


class ReportVariantContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: str
    sections: list[ReportSectionContract]


class MethodReportContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method_id: str
    summary_type: str
    accepted_schema_versions: list[int]
    renderer_id: str
    renderer_version: str
    variants: list[ReportVariantContract]


class ReportSectionCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    title: str
    status: Literal["rendered", "missing", "not_applicable"]
    reason: str | None = None


class AnalysisReportCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_schema_version: Literal[1] = 1
    analysis_id: UUID
    method_id: str
    summary_type: str | None
    result_schema_version: int | None
    source_result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stale: bool
    locale: Literal["en", "ko"]
    renderer_id: str | None
    renderer_version: str | None
    variant_id: str | None
    report_level: Literal["full", "summary", "unsupported"]
    sections: list[ReportSectionCapability]
    reason: str | None = None
    html_available: bool
    source_validation: Literal["stored_dependencies_only"] = "stored_dependencies_only"
