"""Pure contracts for sections that were actually rendered from stored results."""

import re
from dataclasses import dataclass
from html import escape
from typing import Literal

ReportLevel = Literal["full", "summary", "unsupported"]
SectionStatus = Literal["rendered", "missing", "not_applicable"]
_CODE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class ReportSectionDefinition:
    section_id: str
    core: bool = False


@dataclass(frozen=True)
class ReportVariantDefinition:
    variant_id: str
    sections: tuple[ReportSectionDefinition, ...]


@dataclass(frozen=True)
class ReportDefinition:
    method_id: str
    summary_type: str
    accepted_schemas: tuple[int, ...]
    renderer_id: str
    renderer_version: str
    variants: tuple[ReportVariantDefinition, ...]


@dataclass(frozen=True)
class ReportSection:
    section_id: str
    title: str
    status: SectionStatus
    markup: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ReportBody:
    variant_id: str
    sections: tuple[ReportSection, ...]
    unsupported_reason: str | None = None

    @property
    def rendered_count(self) -> int:
        return sum(section.status == "rendered" for section in self.sections)

    def render(self) -> str:
        """Section content is trusted renderer output; titles and codes are text."""
        return "".join(
            f'<div data-report-section="{escape(section.section_id, quote=True)}" '
            f'data-report-section-status="{section.status}">'
            f"<h3>{escape(section.title)}</h3>{section.markup}</div>"
            for section in self.sections
            if section.status == "rendered"
        )


def assess_report_body(definition: ReportDefinition, body: ReportBody) -> ReportLevel:
    """Fail closed on renderer/definition drift, not merely on missing fields."""
    if body.unsupported_reason is not None:
        if not _CODE.fullmatch(body.unsupported_reason) or body.sections:
            raise ValueError("analysis_report_contract_invalid")
        return "unsupported"
    variant = next(
        (item for item in definition.variants if item.variant_id == body.variant_id), None
    )
    if variant is None:
        raise ValueError("analysis_report_contract_invalid")
    expected = {item.section_id: item for item in variant.sections}
    actual = {item.section_id: item for item in body.sections}
    if (
        not expected
        or len(expected) != len(variant.sections)
        or len(actual) != len(body.sections)
        or expected.keys() != actual.keys()
        or not any(item.core for item in variant.sections)
    ):
        raise ValueError("analysis_report_contract_invalid")
    core_missing = False
    missing = False
    for section in body.sections:
        if not _CODE.fullmatch(section.section_id) or not section.title.strip():
            raise ValueError("analysis_report_contract_invalid")
        if section.status == "rendered":
            if not section.markup or not section.markup.strip() or section.reason is not None:
                raise ValueError("analysis_report_contract_invalid")
            if expected[section.section_id].core and not re.search(
                r"<(?:table|svg|dl)\b", section.markup
            ):
                raise ValueError("analysis_report_payload_invalid")
        elif section.status in {"missing", "not_applicable"}:
            if (
                section.markup is not None
                or not section.reason
                or not _CODE.fullmatch(section.reason)
            ):
                raise ValueError("analysis_report_contract_invalid")
            if expected[section.section_id].core:
                core_missing = True
            if section.status == "missing":
                missing = True
        else:
            raise ValueError("analysis_report_contract_invalid")
    return "unsupported" if core_missing else "summary" if missing else "full"
