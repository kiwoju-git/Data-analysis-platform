"""Normality tables and Q-Q coordinates projected from the saved result only."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.report_contract import (
    ReportBody,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
)
from app.services.stored_report_primitives import (
    report_column_label,
    report_number,
    report_plot,
    report_table,
)

NORMALITY_REPORT_VARIANTS = (
    ReportVariantDefinition(
        "default",
        (
            ReportSectionDefinition("normality_tests", core=True),
            ReportSectionDefinition("qq_plots"),
        ),
    ),
)


def normality_report_body(payload: dict[str, Any], locale: ReportLocale = "en") -> ReportBody:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    columns = payload.get("columns")
    if (
        not isinstance(columns, list)
        or not columns
        or any(
            not isinstance(column, dict)
            or not {"column_id", "n_used", "shapiro_wilk", "anderson_darling"} <= column.keys()
            for column in columns
        )
    ):
        return ReportBody("default", (), "normality_core_not_stored")
    rows = []
    plots: list[str] = []
    missing_plot = False
    for column in columns:
        shapiro, anderson = column["shapiro_wilk"], column["anderson_darling"]
        if not isinstance(shapiro, dict) or not isinstance(anderson, dict):
            return ReportBody("default", (), "normality_core_not_stored")
        label = report_column_label(column, column["column_id"])
        decision = anderson.get("decision_at_alpha") or {}
        rows.append(
            [
                label,
                column.get("n_total"),
                column["n_used"],
                column.get("n_missing"),
                column.get("n_non_numeric"),
                column.get("mean"),
                column.get("std"),
                column.get("skewness"),
                column.get("kurtosis_excess"),
                shapiro.get("computed"),
                shapiro.get("statistic"),
                shapiro.get("p_value"),
                anderson.get("statistic"),
                anderson.get("adjusted_statistic"),
                anderson.get("p_value"),
                decision.get("reject_normality"),
                ", ".join(column.get("warnings", [])),
            ]
        )
        qq = column.get("qq_plot")
        if not isinstance(qq, dict) or not isinstance(qq.get("points"), list):
            missing_plot = True
            continue
        points = [
            (report_number(point["theoretical"]), report_number(point["sample"]), label)
            for point in qq["points"]
        ]
        if points:
            title = text("Normal Q-Q Plot", "정규 Q-Q 그림") + ": " + label
            plots += [
                report_plot(
                    title,
                    text("Theoretical normal quantile", "이론 정규 분위수"),
                    text("Sample quantile", "표본 분위수") + ": " + label,
                    [(label, points)],
                ),
                "<p>"
                + escape(text("Stored / used points", "저장 / 사용 점 수"))
                + f": {len(points)} / {column['n_used']}; "
                + escape(text("Truncated", "표시 제한"))
                + f": {qq.get('points_truncated')}</p>",
            ]
    headers = [
        text("Variable", "변수"),
        text("Total N", "전체 N"),
        text("Used N", "사용 N"),
        text("Missing", "결측"),
        text("Non-numeric", "비수치"),
        text("Mean", "평균"),
        text("Sample SD", "표본 표준편차"),
        text("Skewness", "왜도"),
        text("Excess kurtosis", "초과 첨도"),
        text("Shapiro computed", "Shapiro 계산 여부"),
        "Shapiro W",
        "Shapiro p",
        "Anderson-Darling A²",
        text("Adjusted A²", "조정 A²"),
        "Anderson-Darling p",
        text("Reject at alpha", "유의수준에서 기각"),
        text("Warning codes", "경고 코드"),
    ]
    summary = report_table(headers, rows) + report_table(
        [text("Setting", "설정"), text("Value", "값")],
        [
            ["Alpha", payload.get("alpha")],
            [text("Missing policy", "결측 처리"), payload.get("missing_policy")],
            [text("Q-Q distribution", "Q-Q 분포"), payload.get("qq_plot_distribution")],
            [text("Plotting position", "분위수 위치"), payload.get("qq_plotting_position")],
        ],
    )
    sections = [
        ReportSection(
            "normality_tests", text("Normality Tests", "정규성 검정"), "rendered", summary
        )
    ]
    sections.append(
        ReportSection(
            "qq_plots",
            text("Normal Q-Q Plots", "정규 Q-Q 그림"),
            "missing" if missing_plot else "rendered" if plots else "not_applicable",
            "".join(plots) if plots and not missing_plot else None,
            "qq_points_not_stored" if missing_plot else None if plots else "no_usable_qq_points",
        )
    )
    return ReportBody("default", tuple(sections))
