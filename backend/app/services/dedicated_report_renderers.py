"""Static projections of verified DOE/LHS/BO snapshots, without model execution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale
from app.services.inference_report_primitives import missing, paragraph, section, text
from app.services.report_contract import (
    ReportBody,
    ReportDefinition,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
)
from app.services.stored_report_primitives import (
    report_grid,
    report_number,
    report_plot,
    report_table,
)


def _definition(
    method: str,
    summary: str,
    variant: str,
    core: tuple[str, ...],
    optional: tuple[str, ...],
    schemas: tuple[int, ...] = (1, 2, 3),
) -> ReportDefinition:
    return ReportDefinition(
        method,
        summary,
        schemas,
        "dedicated_" + variant,
        "1",
        (
            ReportVariantDefinition(
                variant,
                tuple(ReportSectionDefinition(key, key in core) for key in (*core, *optional)),
            ),
        ),
    )


DEFINITIONS = {
    "factorial": _definition(
        "doe.factorial_design",
        "factorial_analysis",
        "factorial",
        ("source", "model_summary", "terms", "anova"),
        (
            "selection",
            "equation",
            "coded_coefficients",
            "diagnostics",
            "residual_plots",
            "factorial_plots",
            "warnings",
        ),
    ),
    "general_factorial": _definition(
        "doe.general_factorial_design",
        "general_factorial_analysis",
        "general_factorial",
        ("source", "model_summary", "terms", "anova"),
        (
            "selection",
            "equation",
            "coded_coefficients",
            "diagnostics",
            "residual_plots",
            "factorial_plots",
            "warnings",
        ),
    ),
    "response_surface": _definition(
        "doe.response_surface",
        "response_surface_analysis",
        "response_surface",
        ("source", "model_summary", "terms", "anova"),
        ("diagnostics", "stationary_point", "surface_grid", "warnings"),
        (1,),
    ),
    "response_optimizer": _definition(
        "doe.response_optimizer",
        "response_optimizer",
        "response_optimizer",
        ("source", "objectives", "recommendation"),
        ("factor_region", "search", "source_eligibility", "warnings"),
        (2,),
    ),
    "lhs": _definition(
        "doe.latin_hypercube",
        "latin_hypercube_design",
        "lhs",
        ("source", "factors", "runs"),
        ("quality", "responses", "warnings"),
        (1, 2),
    ),
    "bayesian": _definition(
        "doe.bayesian_optimization",
        "bayesian_history",
        "bayesian",
        ("source", "definition", "history"),
        ("observations", "history_plot", "attachment", "warnings"),
        (1,),
    ),
    "doe_prediction": _definition(
        "doe.factorial_prediction",
        "factorial_prediction",
        "doe_prediction",
        ("source", "prediction_rows"),
        ("warnings",),
        (1,),
    ),
    "regression_optimizer": _definition(
        "regression.linear_model_optimizer",
        "regression_response_optimizer",
        "regression_optimizer",
        ("source", "goal", "recommendation"),
        ("factor_region", "profiles", "search", "warnings"),
        (1, 2),
    ),
}


def stored_table(value: object, locale: ReportLocale) -> str:
    """Render explicit saved sections as escaped leaf tables, not a raw JSON appendix."""
    rows: list[tuple[str, object]] = []

    def visit(item: object, path: str, depth: int) -> None:
        if depth > 12 or len(rows) > 50000:
            raise ValueError("report_source_size_exceeded")
        if isinstance(item, Mapping):
            if not item:
                rows.append((path, text(locale, "없음", "None")))
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("report_source_invalid")
                visit(child, f"{path}.{key}" if path else key, depth + 1)
        elif isinstance(item, list | tuple):
            if not item:
                rows.append((path, text(locale, "저장 항목 없음", "No stored entries")))
            for index, child in enumerate(item):
                visit(child, f"{path}[{index + 1}]", depth + 1)
        else:
            if isinstance(item, float | int) and not isinstance(item, bool):
                report_number(item)
            if item is not None and not isinstance(item, str | float | int | bool):
                raise ValueError("report_source_invalid")
            rows.append((path, item))

    visit(value, "", 0)
    return report_table(
        [text(locale, "항목", "Item"), text(locale, "저장값", "Stored value")], rows
    )


def _saved(section_id: str, ko: str, en: str, value: object, locale: ReportLocale) -> ReportSection:
    return section(
        section_id, ko, en, stored_table(value, locale) if value is not None else "", locale
    )


def _warning_section(
    payload: dict[str, Any], result: dict[str, Any], locale: ReportLocale
) -> ReportSection:
    warnings = result.get("warnings", [])
    source_warnings = payload.get("source_warnings", [])
    if not isinstance(warnings, list) or not isinstance(source_warnings, list):
        raise ValueError("report_source_invalid")
    # Dedicated workflows contain both codes and contextual text; never erase either.
    return _saved(
        "warnings",
        "경고와 해석 제한",
        "Warnings and limitations",
        {
            "warnings": warnings,
            "source_warnings": source_warnings,
            "scope": text(
                locale,
                "저장된 결과만 표시하며 분석, 예측, 탐색을 다시 실행하지 않았습니다.",
                "Only stored results are displayed; analysis, prediction "
                "and search were not rerun.",
            ),
        },
        locale,
    )


def _source(payload: dict[str, Any], locale: ReportLocale) -> ReportSection:
    return _saved("source", "출처와 설정", "Source and settings", payload.get("provenance"), locale)


def _ordered(variant: str, sections: Sequence[ReportSection]) -> ReportBody:
    indexed = {item.section_id: item for item in sections}
    definition = DEFINITIONS[variant].variants[0]
    return ReportBody(
        definition.variant_id, tuple(indexed[item.section_id] for item in definition.sections)
    )


def _diagnostics(result: dict[str, Any], locale: ReportLocale) -> ReportSection:
    diagnostics = result.get("diagnostics")
    if not isinstance(diagnostics, dict) or not isinstance(diagnostics.get("points"), list):
        return missing("diagnostics", "저장 잔차 진단", "Stored residual diagnostics", locale)
    points = diagnostics["points"]
    response = result.get("response", {})
    response_label = str(response.get("name", "Response")) + (
        f" ({response['unit']})" if response.get("unit") else ""
    )
    markup = stored_table(diagnostics, locale)
    if points:
        values = [
            (report_number(row["fitted"]), report_number(row["residual"]), str(row["run_order"]))
            for row in points
        ]
        markup += report_plot(
            text(locale, "잔차 대 적합값", "Residual versus fitted"),
            text(locale, "적합 ", "Fitted ") + response_label,
            text(locale, "잔차", "Residual"),
            [(text(locale, "실행", "Run"), values)],
            zero=True,
        )
        markup += report_plot(
            text(locale, "잔차 대 실행순서", "Residual versus run order"),
            text(locale, "실행순서", "Run order"),
            text(locale, "잔차", "Residual"),
            [
                (
                    text(locale, "실행", "Run"),
                    [
                        (
                            report_number(row["run_order"]),
                            report_number(row["residual"]),
                            str(row["run_order"]),
                        )
                        for row in points
                    ],
                )
            ],
            zero=True,
        )
    return section("diagnostics", "저장 잔차 진단", "Stored residual diagnostics", markup, locale)


def _residual_views(final: dict[str, Any], locale: ReportLocale) -> ReportSection:
    views = final.get("residual_plots")
    if not isinstance(views, dict):
        return missing(
            "residual_plots", "최종 모형 잔차 그래프", "Final-model residual plots", locale
        )
    markup = stored_table(
        {key: views[key] for key in ("n_total", "point_limit", "truncated") if key in views}, locale
    )
    for name in ("raw", "standardized"):
        view = views.get(name)
        if not isinstance(view, dict) or not all(
            isinstance(view.get(key), list) for key in ("histogram", "qq_points", "points")
        ):
            return missing(
                "residual_plots", "최종 모형 잔차 그래프", "Final-model residual plots", locale
            )
        label = (
            text(locale, "원시 잔차", "Raw residual")
            if name == "raw"
            else text(locale, "표준화 잔차", "Standardized residual")
        )
        markup += "<h4>" + escape(label) + "</h4>"
        markup += stored_table(view, locale)
        qq = view["qq_points"]
        points = view["points"]
        bins = view["histogram"]
        markup += report_plot(
            label + " Q-Q",
            text(locale, "이론 분위수", "Theoretical quantile"),
            label,
            [
                (
                    label,
                    [
                        (
                            report_number(row["theoretical_quantile"]),
                            report_number(row["residual"]),
                            str(row["run_order"]),
                        )
                        for row in qq
                    ],
                )
            ],
        )
        markup += report_plot(
            label,
            label,
            text(locale, "빈도", "Frequency"),
            [],
            histogram_bins=[
                (
                    report_number(row["lower"]),
                    report_number(row["upper"]),
                    report_number(row["count"]),
                    str(index + 1),
                )
                for index, row in enumerate(bins)
            ],
        )
        for x_key, x_label in (
            ("fitted", text(locale, "적합값", "Fitted")),
            ("run_order", text(locale, "실행순서", "Run order")),
        ):
            markup += report_plot(
                label,
                x_label,
                label,
                [
                    (
                        label,
                        [
                            (
                                report_number(row[x_key]),
                                report_number(row["residual"]),
                                str(row["run_order"]),
                            )
                            for row in points
                        ],
                    )
                ],
                zero=True,
            )
    return section(
        "residual_plots", "최종 모형 잔차 그래프", "Final-model residual plots", markup, locale
    )


def render_doe_analysis_body(
    payload: dict[str, Any], family: str, locale: ReportLocale
) -> ReportBody:
    result = payload.get("result")
    if family not in {"factorial", "general_factorial", "response_surface"} or not isinstance(
        result, dict
    ):
        return ReportBody("unsupported", (), "unsupported_result_schema")
    schemas = (1,) if family == "response_surface" else (1, 2, 3)
    if (
        type(result.get("schema_version")) is not int
        or result["schema_version"] not in schemas
        or result.get("summary_type") != DEFINITIONS[family].summary_type
    ):
        return ReportBody("unsupported", (), "unsupported_result_schema")
    if (
        not isinstance(result.get("fit"), dict)
        or not result["fit"]
        or not isinstance(result.get("sample"), dict)
        or not result["sample"]
        or not isinstance(result.get("anova"), dict)
        or not result["anova"]
        or not result.get("terms" if family != "general_factorial" else "coefficients")
    ):
        return ReportBody("unsupported", (), "required_result_section_missing")
    final = result.get("final_model") or {}
    terms = result.get("terms") if family != "general_factorial" else result.get("coefficients")
    sections = [
        _source(payload, locale),
        _saved(
            "model_summary",
            "모형 요약",
            "Model summary",
            {
                key: result[key]
                for key in ("response", "method", "coding", "model_policy", "sample", "fit")
                if key in result
            },
            locale,
        ),
        _saved("terms", "모형 항과 계수", "Model terms and coefficients", terms, locale),
        _saved("anova", "분산분석", "ANOVA", result.get("anova"), locale),
        _diagnostics(result, locale),
        _warning_section(payload, result, locale),
    ]
    if family == "response_surface":
        sections.append(
            _saved(
                "stationary_point",
                "정류점",
                "Stationary point",
                result.get("stationary_point"),
                locale,
            )
        )
        contour = result.get("contour")
        if isinstance(contour, dict) and isinstance(contour.get("points"), list):
            response = result.get("response", {})
            label = str(response.get("name", "Response")) + (
                f" ({response['unit']})" if response.get("unit") else ""
            )
            factor_units = {
                item["name"]: item.get("unit")
                for item in payload.get("provenance", {}).get("design_factors", [])
            }

            def factor_label(name: str) -> str:
                return name + (f" ({factor_units[name]})" if factor_units.get(name) else "")

            markup = stored_table(contour, locale) + report_grid(
                text(locale, "저장 반응표면 격자", "Stored response-surface grid"),
                factor_label(str(contour["x_factor"])),
                factor_label(str(contour["y_factor"])),
                label,
                [
                    (
                        report_number(row["x_actual"]),
                        report_number(row["y_actual"]),
                        report_number(row["predicted"]),
                        label,
                    )
                    for row in contour["points"]
                ],
            )
        else:
            markup = ""
        sections.append(
            section(
                "surface_grid", "저장 반응표면 격자", "Stored response-surface grid", markup, locale
            )
        )
    else:
        sections += [
            _saved(
                "selection",
                "모형 선택 단계",
                "Model-selection steps",
                result.get("model_selection"),
                locale,
            ),
            _saved("equation", "회귀식", "Regression equation", final.get("equation"), locale),
            _saved(
                "coded_coefficients",
                "코딩 계수와 VIF",
                "Coded coefficients and VIF",
                final.get("coded_coefficients"),
                locale,
            ),
            _residual_views(final, locale),
            _saved(
                "factorial_plots",
                "저장 요인 수준별 평균",
                "Stored factorial level means",
                {
                    "fitted_cells": final.get("factorial_plots"),
                    "observed_plots": result.get("plots"),
                    "group_means": result.get("group_means"),
                }
                if any(key in result for key in ("plots", "group_means"))
                or final.get("factorial_plots")
                else None,
                locale,
            ),
        ]
    return _ordered(family, sections)


def render_optimizer_body(payload: dict[str, Any], locale: ReportLocale) -> ReportBody:
    result = payload.get("result", {})
    if result.get("schema_version") != 2 or result.get("summary_type") != "response_optimizer":
        return ReportBody("unsupported", (), "unsupported_result_schema")
    if not result.get("objectives") or not result.get("recommendation"):
        return ReportBody("unsupported", (), "required_result_section_missing")
    return _ordered(
        "response_optimizer",
        [
            _source(payload, locale),
            *[
                _saved(key, ko, en, result.get(source), locale)
                for key, source, ko, en in (
                    ("objectives", "objectives", "반응별 목표", "Response objectives"),
                    (
                        "recommendation",
                        "recommendation",
                        "저장 최적 조건",
                        "Stored recommended conditions",
                    ),
                    (
                        "factor_region",
                        "factor_region",
                        "요인 영역과 제약",
                        "Factor region and constraints",
                    ),
                    ("search", "search", "탐색 예산과 종료", "Search budget and termination"),
                    (
                        "source_eligibility",
                        "source_model_eligibility",
                        "원본 모형 적격성",
                        "Source-model eligibility",
                    ),
                )
            ],
            _warning_section(payload, result, locale),
        ],
    )


def render_lhs_body(payload: dict[str, Any], locale: ReportLocale) -> ReportBody:
    design = payload["design"]
    if not design.get("factors") or not design.get("runs"):
        return ReportBody("unsupported", (), "required_result_section_missing")
    return _ordered(
        "lhs",
        [
            _source(payload, locale),
            _saved(
                "factors",
                "요인과 실행 설정",
                "Factors and execution settings",
                {"factors": design["factors"], "options": design["options"]},
                locale,
            ),
            _saved("runs", "저장 실행순서", "Stored runs", design.get("runs"), locale),
            _saved(
                "quality", "저장 설계 품질", "Stored design quality", design.get("quality"), locale
            ),
            _saved(
                "responses",
                "선택 반응 revision",
                "Selected response revisions",
                payload.get("responses", []),
                locale,
            ),
            _warning_section(payload, {}, locale),
        ],
    )


def render_bayesian_body(payload: dict[str, Any], locale: ReportLocale) -> ReportBody:
    observations = payload["observations"]
    objective = payload["definition"]["objective"]
    label = str(objective["name"]) + (f" ({objective['unit']})" if objective.get("unit") else "")
    plot = (
        report_plot(
            text(locale, "선택 이력의 완료 관측", "Completed observations in selected history"),
            text(locale, "실험 번호", "Trial number"),
            label,
            [
                (
                    label,
                    [
                        (
                            report_number(item["trial_number"]),
                            report_number(item["objective_value"]),
                            str(item["trial_id"]),
                        )
                        for item in observations
                    ],
                )
            ],
        )
        if observations
        else paragraph(
            "선택한 이력에는 완료 관측이 없습니다. 추천이나 학습을 실행하지 않았습니다.",
            "The selected history has no completed observations. "
            "No recommendation or fitting was run.",
            locale,
        )
    )
    attachment = payload.get("attachment")
    return _ordered(
        "bayesian",
        [
            _source(payload, locale),
            _saved(
                "definition",
                "저장 study 정의",
                "Stored study definition",
                payload.get("definition"),
                locale,
            ),
            _saved(
                "history",
                "선택 관측 이력",
                "Selected observation history",
                payload.get("history"),
                locale,
            ),
            _saved(
                "observations", "이력의 관측값", "Historical observations", observations, locale
            ),
            section("history_plot", "관측 이력 그래프", "Observation history plot", plot, locale),
            _saved(
                "attachment",
                "명시적으로 선택한 추천",
                "Explicitly selected recommendation",
                attachment,
                locale,
            )
            if attachment is not None
            else missing(
                "attachment",
                "명시적으로 선택한 추천",
                "Explicitly selected recommendation",
                locale,
                reason="not_requested",
                applicable=False,
            ),
            _warning_section(
                payload,
                attachment.get("result", attachment) if isinstance(attachment, dict) else {},
                locale,
            ),
        ],
    )


def render_doe_prediction_body(payload: dict[str, Any], locale: ReportLocale) -> ReportBody:
    result = payload["prediction"]
    if not result.get("rows"):
        return ReportBody("unsupported", (), "required_result_section_missing")
    return _ordered(
        "doe_prediction",
        [
            _source(payload, locale),
            _saved(
                "prediction_rows",
                "저장 예측과 구간",
                "Stored predictions and intervals",
                result,
                locale,
            ),
            _warning_section(payload, result, locale),
        ],
    )


def render_regression_optimizer_body(payload: dict[str, Any], locale: ReportLocale) -> ReportBody:
    result = payload["result"]
    if result.get("summary_type") != "regression_response_optimizer" or result.get(
        "schema_version"
    ) not in {1, 2}:
        return ReportBody("unsupported", (), "unsupported_result_schema")
    if not result.get("goal") or not result.get("recommendation"):
        return ReportBody("unsupported", (), "required_result_section_missing")
    return _ordered(
        "regression_optimizer",
        [
            _source(payload, locale),
            *[
                _saved(key, ko, en, result.get(key), locale)
                for key, ko, en in (
                    ("goal", "반응 목표", "Response objective"),
                    ("recommendation", "저장 최적 조건", "Stored recommended conditions"),
                    ("factor_region", "요인 영역과 제약", "Factor region and constraints"),
                    ("profiles", "저장 조건부 프로파일", "Stored conditional profiles"),
                    ("search", "탐색 예산과 종료", "Search budget and termination"),
                )
            ],
            _warning_section(payload, result, locale),
        ],
    )
