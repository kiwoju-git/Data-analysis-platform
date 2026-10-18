"""Stored Pearson scatter and X/Y correlation matrix, without source-row access."""

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
    report_grid,
    report_number,
    report_plot,
    report_table,
)

CORRELATION_REPORT_VARIANTS = {
    "pearson_correlation": (
        ReportVariantDefinition(
            "default",
            (
                ReportSectionDefinition("correlation_summary", core=True),
                ReportSectionDefinition("scatter_plot"),
            ),
        ),
    ),
    "xy_correlation_matrix": (
        ReportVariantDefinition(
            "default",
            (
                ReportSectionDefinition("correlation_pairs", core=True),
                ReportSectionDefinition("correlation_heatmap"),
            ),
        ),
    ),
}


def correlation_report_body(payload: dict[str, Any], locale: ReportLocale = "en") -> ReportBody:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    matrix = payload.get("summary_type") == "xy_correlation_matrix"
    pairs = payload.get("pairs") if matrix else [payload]
    if (
        not isinstance(pairs, list)
        or not pairs
        or any(
            not isinstance(pair, dict)
            or not isinstance(pair.get("x"), dict)
            or not isinstance(pair.get("y"), dict)
            for pair in pairs
        )
    ):
        return ReportBody("default", (), "correlation_core_not_stored")
    rows = []
    for pair in pairs:
        association, test = pair.get("association") or {}, pair.get("test") or {}
        interval = pair.get("confidence_interval") or {}
        if not association and pair.get("status") != "failed":
            return ReportBody("default", (), "correlation_core_not_stored")
        rows.append(
            [
                report_column_label(pair["x"], "X"),
                report_column_label(pair["y"], "Y"),
                pair.get("n_total"),
                pair.get("n_used"),
                pair.get("n_excluded_missing_x"),
                pair.get("n_excluded_missing_y"),
                pair.get("n_excluded_non_numeric_x"),
                pair.get("n_excluded_non_numeric_y"),
                association.get("correlation"),
                association.get("r_squared"),
                association.get("covariance"),
                test.get("statistic"),
                test.get("p_value"),
                test.get("alternative"),
                interval.get("level"),
                interval.get("lower"),
                interval.get("upper"),
                pair.get("status", "ok"),
                pair.get("error_code"),
                ", ".join(pair.get("warnings", [])),
            ]
        )
    table = report_table(
        [
            "X",
            "Y",
            text("Total N", "전체 N"),
            text("Used N", "사용 N"),
            text("Missing X", "X 결측"),
            text("Missing Y", "Y 결측"),
            text("Non-numeric X", "X 비수치"),
            text("Non-numeric Y", "Y 비수치"),
            "Pearson r",
            "R²",
            text("Covariance", "공분산"),
            text("Statistic", "검정 통계량"),
            "p",
            text("Alternative", "대립가설"),
            text("CI level", "신뢰수준"),
            text("CI lower", "신뢰구간 하한"),
            text("CI upper", "신뢰구간 상한"),
            text("Status", "상태"),
            text("Error code", "오류 코드"),
            text("Warning codes", "경고 코드"),
        ],
        rows,
    )
    if not matrix:
        scatter = payload.get("scatterplot")
        plot_section = ReportSection(
            "scatter_plot",
            text("Pearson Scatter Plot", "Pearson 산점도"),
            "missing",
            reason="scatter_points_not_stored",
        )
        if (
            isinstance(scatter, dict)
            and isinstance(scatter.get("points"), list)
            and scatter["points"]
        ):
            label = text("Observations", "관측값")
            markup = report_plot(
                text("Pearson Scatter Plot", "Pearson 산점도"),
                report_column_label(payload["x"], "X"),
                report_column_label(payload["y"], "Y"),
                [
                    (
                        label,
                        [
                            (report_number(point["x"]), report_number(point["y"]), label)
                            for point in scatter["points"]
                        ],
                    )
                ],
            )
            markup += (
                "<p>"
                + escape(text("Stored / used points", "저장 / 사용 점 수"))
                + f": {len(scatter['points'])} / {payload.get('n_used')}; "
                + escape(text("Truncated", "표시 제한"))
                + f": {scatter.get('points_truncated')}</p>"
            )
            plot_section = ReportSection("scatter_plot", plot_section.title, "rendered", markup)
        return ReportBody(
            "default",
            (
                ReportSection(
                    "correlation_summary",
                    text("Pearson Correlation", "Pearson 상관분석"),
                    "rendered",
                    table,
                ),
                plot_section,
            ),
        )
    xs, ys = payload.get("x_columns"), payload.get("y_columns")
    plot_section = ReportSection(
        "correlation_heatmap",
        text("Correlation Matrix", "상관 행렬"),
        "missing",
        reason="matrix_axes_not_stored",
    )
    if isinstance(xs, list) and xs and isinstance(ys, list) and ys:
        x_index = {column["column_id"]: index for index, column in enumerate(xs)}
        y_index = {column["column_id"]: index for index, column in enumerate(ys)}
        cells = []
        for pair in pairs:
            if pair.get("status") == "failed":
                continue
            if pair["x"]["column_id"] not in x_index or pair["y"]["column_id"] not in y_index:
                raise ValueError("analysis_report_payload_invalid")
            cells.append(
                (
                    float(x_index[pair["x"]["column_id"]]),
                    float(y_index[pair["y"]["column_id"]]),
                    report_number(pair["association"]["correlation"]),
                    pair["x"]["display_name"] + " / " + pair["y"]["display_name"],
                )
            )
        if cells:
            markup = report_grid(
                plot_section.title,
                text("X variables", "X 변수"),
                text("Y variables", "Y 변수"),
                "Pearson r",
                cells,
                value_range=(-1.0, 1.0),
                categorical=True,
                x_ticks=[(float(i), column["display_name"]) for i, column in enumerate(xs)],
                y_ticks=[(float(i), column["display_name"]) for i, column in enumerate(ys)],
            )
            markup += (
                "<p>"
                + escape(
                    text(
                        "Failed pairs are omitted, not assigned zero; "
                        "exact values and pair-specific N are in the table.",
                        "실패한 변수 쌍은 0으로 대체하지 않고 표시에서 제외합니다. "
                        "정확한 값과 쌍별 N은 표에 있습니다.",
                    )
                )
                + "</p>"
            )
            plot_section = ReportSection(
                "correlation_heatmap", plot_section.title, "rendered", markup
            )
        else:
            plot_section = ReportSection(
                "correlation_heatmap",
                plot_section.title,
                "not_applicable",
                reason="no_successful_pairs",
            )
    return ReportBody(
        "default",
        (
            ReportSection(
                "correlation_pairs", text("Correlation Pairs", "상관 변수 쌍"), "rendered", table
            ),
            plot_section,
        ),
    )
