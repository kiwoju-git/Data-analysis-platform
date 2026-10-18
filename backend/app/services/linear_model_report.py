"""OLS and penalized-regression views of stored results, without estimator calls."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.regularized_model_report import render_regularized_report
from app.services.report_contract import (
    ReportBody,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
)
from app.services.stored_report_primitives import (
    report_column_label,
    report_histogram,
    report_number,
    report_plot,
    report_table,
)

LINEAR_REPORT_VARIANTS = (
    ReportVariantDefinition(
        "ols",
        tuple(
            ReportSectionDefinition(key, core)
            for key, core in (
                ("model_summary", True),
                ("coefficients", True),
                ("anova", False),
                ("selection", False),
                ("diagnostics", False),
                ("residuals_raw", False),
                ("residuals_standardized", False),
            )
        ),
    ),
    *(
        ReportVariantDefinition(
            kind,
            (
                ReportSectionDefinition("regularized_results", True),
                ReportSectionDefinition("residual_distribution"),
            ),
        )
        for kind in ("ridge", "lasso", "elastic_net")
    ),
)


def linear_model_report_body(payload: dict[str, Any], locale: ReportLocale) -> ReportBody:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    def present(key: str, title: str, markup: str) -> ReportSection:
        if not markup:
            raise ValueError("analysis_report_payload_invalid")
        return ReportSection(key, title, "rendered", markup)

    def missing(key: str, title: str) -> ReportSection:
        return ReportSection(key, title, "missing", reason="section_not_stored")

    try:
        response_label = report_column_label(
            payload.get("response", {}), text("Response", "반응변수")
        )
        residual_label = text("Residual", "잔차")
        unit = payload.get("response", {}).get("unit")
        if unit:
            residual_label += f" ({unit})"
        if isinstance(payload.get("regularization"), dict):
            kind = payload["estimator"]["kind"]
            if kind not in {"ridge", "lasso", "elastic_net"}:
                raise ValueError("analysis_report_variant_unsupported")
            diagnostics = payload.get("diagnostics", {})
            distribution = _residual_distribution(
                diagnostics.get("histogram"), diagnostics.get("qq_plot"), residual_label, locale
            )
            title = text("Stored Residual Distribution", "저장된 잔차 분포")
            return ReportBody(
                kind,
                (
                    present(
                        "regularized_results",
                        text("Regularized Regression", "정규화 회귀"),
                        render_regularized_report(payload, locale),
                    ),
                    present("residual_distribution", title, distribution)
                    if distribution
                    else missing("residual_distribution", title),
                ),
            )

        fit, sample, coefficients = payload["fit"], payload["sample"], payload["coefficients"]
        if not isinstance(fit, dict) or not isinstance(sample, dict) or not coefficients:
            raise ValueError("analysis_report_payload_invalid")
        summary_rows = [
            [text("Response", "반응변수"), response_label],
            [
                text("Predictors", "예측변수"),
                ", ".join(str(p["display_name"]) for p in payload.get("predictors", [])),
            ],
            *[[name, value] for name, value in sample.items()],
            *[[name, value] for name, value in fit.items()],
        ]
        summary = report_table(
            [text("Setting / Metric", "설정 / 지표"), text("Stored Value", "저장값")], summary_rows
        )
        equation = payload.get("equation")
        if isinstance(equation, dict) and isinstance(equation.get("display_equation"), str):
            summary += f'<p>{escape(equation["display_equation"])}</p>'
        sections = [
            present("model_summary", text("OLS Model Summary", "OLS 모형 요약"), summary),
            present(
                "coefficients",
                text("Coefficients", "계수"),
                report_table(
                    [
                        text("Term", "항"),
                        "Coefficient",
                        "SE",
                        "T",
                        "P",
                        "CI lower",
                        "CI upper",
                        "VIF",
                    ],
                    [
                        [
                            row["term"],
                            row["estimate"],
                            row.get("standard_error"),
                            row.get("statistic"),
                            row.get("p_value"),
                            _bound(row.get("confidence_interval"), "lower"),
                            _bound(row.get("confidence_interval"), "upper"),
                            row.get("vif"),
                        ]
                        for row in coefficients
                    ],
                ),
            ),
        ]
        anova = payload.get("anova")
        title = "ANOVA"
        if isinstance(anova, dict) and anova.get("rows"):
            markup = report_table(
                [text("Source", "변동원"), "DF", "Adjusted SS", "Adjusted MS", "F", "P"],
                [
                    [
                        row.get(key)
                        for key in (
                            "source",
                            "df",
                            "adjusted_ss",
                            "adjusted_ms",
                            "f_statistic",
                            "p_value",
                        )
                    ]
                    for row in anova["rows"]
                ],
            )
            lack = anova.get("lack_of_fit")
            if isinstance(lack, dict) and lack.get("available") is False:
                reason = str(lack.get("reason", lack.get("reason_code", "not_available")))
                label = text("Lack of fit unavailable: ", "적합성 결여 검정 미제공: ")
                markup += f"<p>{escape(label)}{escape(reason)}</p>"
            sections.append(present("anova", title, markup))
        else:
            sections.append(missing("anova", title))
        selection = payload.get("model_selection")
        title = text("Model Selection", "모형 선택")
        if isinstance(selection, dict) and selection.get("method") == "none":
            sections.append(
                ReportSection(
                    "selection", title, "not_applicable", reason="selection_not_requested"
                )
            )
        elif isinstance(selection, dict) and selection.get("steps"):
            markup = report_table(
                [text("Policy", "정책"), text("Value", "값")],
                [[key, str(value)] for key, value in selection.items() if key != "steps"],
            )
            for step in selection["steps"]:
                markup += report_table(
                    [text("Step Metric", "단계 지표"), text("Stored Value", "저장값")],
                    [
                        [key, str(value) if isinstance(value, list) else value]
                        for key, value in step.items()
                        if key != "coefficients"
                    ],
                )
                markup += report_table(
                    [text("Term", "항"), "Coefficient"],
                    [[row["term"], row["estimate"]] for row in step["coefficients"]],
                )
            sections.append(present("selection", title, markup))
        else:
            sections.append(missing("selection", title))
        diagnostics = payload.get("diagnostics")
        title = text("Stored Diagnostics", "저장된 진단값")
        diagnostic_points = (
            diagnostics.get("diagnostic_points") if isinstance(diagnostics, dict) else None
        )
        if isinstance(diagnostic_points, dict) and diagnostic_points.get("points"):
            keys = (
                "row_index",
                "fitted",
                "residual",
                "standardized_residual",
                "leverage",
                "cooks_distance",
            )
            markup = report_table(
                list(keys), [[row.get(key) for key in keys] for row in diagnostic_points["points"]]
            )
            for name in ("residual_summary", "leverage", "influence"):
                details = diagnostics.get(name)
                if isinstance(details, dict):
                    markup += report_table(
                        [name, text("Stored Value", "저장값")],
                        [
                            [key, str(value) if isinstance(value, list) else value]
                            for key, value in details.items()
                        ],
                    )
            markup += _scope_note(
                {**diagnostic_points, "point_count_total": sample.get("n_used")}, locale
            )
            sections.append(present("diagnostics", title, markup))
        else:
            sections.append(missing("diagnostics", title))
        plots = payload.get("residual_plots")
        for kind in ("raw", "standardized"):
            title = text(
                f"{kind.title()} Residual Diagnostics",
                "원 잔차 진단" if kind == "raw" else "표준화 잔차 진단",
            )
            markup = ""
            if isinstance(plots, dict):
                y_label = (
                    residual_label
                    if kind == "raw"
                    else text("Standardized residual", "표준화 잔차")
                )
                markup = _residual_distribution(
                    plots.get("histograms", {}).get(kind),
                    plots.get("qq_plots", {}).get(kind),
                    y_label,
                    locale,
                )
                scatter_parts: list[str] = []
                for key, x_key, x_label in (
                    ("residuals_vs_fits", "fitted", text("Fitted ", "적합 ") + response_label),
                    ("residuals_vs_order", "order", text("Analysis row order", "분석 행 순서")),
                ):
                    saved = plots.get(key, {}).get(kind)
                    if not isinstance(saved, dict) or not saved.get("points"):
                        scatter_parts = []
                        break
                    scatter_parts.append(
                        report_plot(
                            title,
                            x_label,
                            y_label,
                            [
                                (
                                    y_label,
                                    [
                                        (
                                            report_number(p[x_key]),
                                            report_number(p["residual"]),
                                            f"row_index={p['row_index']}",
                                        )
                                        for p in saved["points"]
                                    ],
                                )
                            ],
                            zero=True,
                        )
                        + _scope_note(saved, locale)
                    )
                markup = (
                    markup + "".join(scatter_parts) if markup and len(scatter_parts) == 2 else ""
                )
            sections.append(
                present(f"residuals_{kind}", title, markup)
                if markup
                else missing(f"residuals_{kind}", title)
            )
        return ReportBody("ols", tuple(sections))
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise ValueError("analysis_report_payload_invalid") from exc


def _bound(value: object, key: str) -> object:
    return value.get(key) if isinstance(value, dict) else None


def _scope_note(payload: dict[str, Any], locale: ReportLocale) -> str:
    count = len(payload.get("points", []))
    total = payload.get("point_count_total", payload.get("n", "?"))
    title = report_text(
        locale, en="Stored plotted points / computation rows", ko="저장된 표시 점 / 계산 행"
    )
    return f"<p>{escape(title)}: {count} / {escape(str(total))}</p>"


def _residual_distribution(
    histogram: object, qq: object, residual_label: str, locale: ReportLocale
) -> str:
    if (
        not isinstance(histogram, dict)
        or not histogram.get("bins")
        or not isinstance(qq, dict)
        or not qq.get("points")
    ):
        return ""

    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    histogram_markup = report_histogram(
        text("Residual Histogram", "잔차 히스토그램"),
        residual_label,
        text("Frequency", "빈도"),
        [
            (report_number(b["lower"]), report_number(b["upper"]), report_number(b["count"]))
            for b in histogram["bins"]
        ],
    )
    points = [
        (
            report_number(p["theoretical_quantile"]),
            report_number(p["residual"]),
            f"row_index={p['row_index']}",
        )
        for p in qq["points"]
    ]
    reference_segments = []
    reference = qq.get("reference_line")
    if reference is not None:
        slope = report_number(reference["slope"])
        intercept = report_number(reference["intercept"])
        x1 = min(point[0] for point in points)
        x2 = max(point[0] for point in points)
        reference_segments.append(
            (
                text("Stored Q-Q reference", "저장된 Q-Q 기준선"),
                x1,
                slope * x1 + intercept,
                x2,
                slope * x2 + intercept,
            )
        )
    return (
        histogram_markup
        + report_plot(
            text("Residual Normal Q-Q Plot", "잔차 정규 Q-Q 도표"),
            text("Theoretical normal quantile", "이론적 정규 분위수"),
            residual_label,
            [(residual_label, points)],
            reference_segments=reference_segments,
        )
        + _scope_note(qq, locale)
    )
