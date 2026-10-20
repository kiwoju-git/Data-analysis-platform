"""Compact and complete alias display from verified catalogue metadata only."""

from html import escape

from app.api.v1.schemas.doe import FactorialDesignResponse
from app.i18n.report_text import ReportLocale, report_text
from app.services.regularized_model_report import _table as report_table


def fractional_alias_report(design: FactorialDesignResponse, locale: ReportLocale) -> str:
    metadata = design.fractional
    if metadata is None:
        return ""

    def label(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    mapping = report_table(
        [label("Symbol", "기호"), label("Full factor name", "전체 요인명"), label("Unit", "단위")],
        [
            [chr(65 + index), factor.name, factor.unit]
            for index, factor in enumerate(design.factors)
        ],
    )
    if metadata.alias_classes is None:
        aliases = report_table(
            [label("Stored alias labels", "저장된 Alias 이름")],
            [[" = ".join(group)] for group in metadata.alias_groups],
        )
    else:
        aliases = report_table(
            [label("Alias class", "Alias 그룹"), label("Full factor names", "전체 요인명")],
            [
                [
                    " = ".join(
                        ("-" if term.sign < 0 else "") + term.compact_label for term in group
                    ),
                    " = ".join(("-" if term.sign < 0 else "") + term.full_label for term in group),
                ]
                for group in metadata.alias_classes
            ],
        )
    explanation = label(
        "I is the identity, not a factor. All alias orders are preserved. "
        "Corner alias membership does not establish independent estimability "
        "of the requested model with centers and blocks.",
        "I는 요인이 아니라 항등원입니다. 모든 차수의 Alias를 보존합니다. "
        "코너 Alias 관계와 중심점·블록을 포함한 요청 모형의 독립 추정 가능성은 다릅니다.",
    )
    title = escape(label("Alias structure", "Alias 구조"))
    return (
        f'<section class="fractional-alias"><h2>{title}</h2>'
        f"{mapping}{aliases}<p>{escape(explanation)}</p></section>"
    )
