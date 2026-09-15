"""Script-free reports rendered exclusively from verified, saved analyses."""

from __future__ import annotations

import json
from html import escape
from itertools import combinations, product
from statistics import mean
from typing import Any

from app.api.v1.schemas.doe import GeneralFactorialDesignResponse
from app.api.v1.schemas.doe_model_workflow import DoePredictionResponse
from app.i18n.report_text import ReportLocale, report_text
from app.services.factorial_prediction import FactorialModelSource
from app.services.regularized_model_report import _table as report_table


def factorial_warning_text(code: str, locale: ReportLocale) -> str:
    messages = {
        "doe_factorial_post_selection_inference_exploratory": (
            "Inference after selection on the same data is exploratory. "
            "Confirm the model with independent data or experiments.",
            "같은 데이터로 모형을 선택한 뒤의 추론은 탐색적입니다. "
            "독립 데이터나 확인 실험으로 검증하세요.",
        ),
        "doe_factorial_initial_pooling_assumption": (
            "Pooled effects are assumed negligible, not proven zero. "
            "Subsequent inference depends on this assumption.",
            "풀링된 효과가 0임을 증명한 것이 아닙니다. "
            "이후 추론은 풀링된 효과를 무시할 수 있다는 가정에 의존합니다.",
        ),
        "doe_factorial_press_unavailable_high_leverage": (
            "PRESS is unavailable because one or more leverage values are too close to one.",
            "일부 레버리지가 1에 가까워 PRESS를 계산할 수 없습니다.",
        ),
        "doe_factorial_randomization_and_independence_not_proven": (
            "Randomization and independence must be established by the experimental design.",
            "무작위화와 독립성은 실험 설계를 통해 확보해야 합니다.",
        ),
        "doe_factorial_effects_are_associations_within_experiment": (
            "Effects describe associations within this experiment, "
            "not automatic causal conclusions.",
            "효과는 이 실험 범위의 관계를 나타내며 자동으로 인과관계를 입증하지 않습니다.",
        ),
        "doe_factorial_higher_order_interactions_excluded_by_policy": (
            "Higher-order interactions were excluded by the specified model order.",
            "지정한 모형 차수보다 높은 상호작용은 제외되었습니다.",
        ),
        "doe_factorial_model_saturated_no_inference": (
            "The saturated model has no residual degrees of freedom for inference.",
            "포화모형에는 추론에 필요한 잔차 자유도가 없습니다.",
        ),
        "doe_factorial_residual_df_small": (
            "Residual degrees of freedom are small.",
            "잔차 자유도가 작습니다.",
        ),
        "doe_factorial_residual_variance_zero": (
            "Residual variance is zero or numerically negligible.",
            "잔차 분산이 0이거나 수치적으로 매우 작습니다.",
        ),
        "doe_factorial_pure_error_unavailable_without_replication": (
            "Pure error cannot be estimated without replicated settings.",
            "동일 조건의 반복이 없어 순수오차를 추정할 수 없습니다.",
        ),
        "doe_factorial_lack_of_fit_df_unavailable": (
            "Lack-of-fit degrees of freedom are unavailable.",
            "적합성 결여의 자유도를 확보할 수 없습니다.",
        ),
        "doe_factorial_block_fixed_effects_included": (
            "Fixed block effects are retained in the model.",
            "블록 고정효과를 모형에 유지했습니다.",
        ),
        "doe_factorial_large_standardized_residual": (
            "Some standardized residuals are large.",
            "일부 표준화 잔차가 큽니다.",
        ),
        "doe_factorial_influential_run_detected": (
            "Some runs have high influence; inspect Cook's distance.",
            "영향력이 큰 실행 행이 있습니다. Cook 거리를 확인하세요.",
        ),
        "doe_factorial_vif_unavailable": (
            "VIF is unavailable for a constant or non-identifiable feature.",
            "상수 또는 식별 불가능한 항의 VIF는 제공하지 않습니다.",
        ),
    }
    if code in messages:
        en, ko = messages[code]
        return report_text(locale, en=en, ko=ko)
    general = {
        "Numeric factor levels are analyzed as categorical levels in a general factorial model.": (
            "Numeric levels use categorical treatment coding; "
            "interpolation between levels is not supported.",
            "숫자 수준도 범주형 treatment coding을 사용하며 수준 간 보간을 지원하지 않습니다.",
        ),
        "Residual degrees of freedom are zero; inferential statistics are unavailable.": messages[
            "doe_factorial_model_saturated_no_inference"
        ],
        "Repeated factor combinations are insufficient to separate pure error and lack of fit.": (
            "Replicated settings are insufficient to separate pure error and lack of fit.",
            "순수오차와 적합성 결여를 분리할 반복 조건이 부족합니다.",
        ),
    }
    if code in general:
        en, ko = general[code]
        return report_text(locale, en=en, ko=ko)
    return report_text(
        locale,
        en="Review the stored analysis warning in technical information.",
        ko="기술 정보의 저장된 분석 경고를 확인하세요.",
    )


def render_factorial_analysis_report(
    source: FactorialModelSource,
    locale: ReportLocale,
    latest_prediction: DoePredictionResponse | None = None,
) -> bytes:
    def label(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    def heading(en: str, ko: str) -> str:
        return f"<h2>{escape(label(en, ko))}</h2>"

    def paragraph(en: str, ko: str) -> str:
        return f"<p>{escape(label(en, ko))}</p>"

    design, analysis, result = source.design, source.analysis, source.result
    titles = [label("Item", "항목"), label("Value", "값")]
    parts = [
        "<h1>"
        + escape(
            label(
                "Statistical Twin Factorial Analysis Report",
                "Statistical Twin 요인배치 분석 보고서",
            )
        )
        + "</h1>",
        heading("Design and response", "설계와 반응"),
        report_table(
            titles,
            [
                [label("Design", "설계"), design.name],
                [label("Response", "반응"), analysis.response_name],
                [label("Response revision", "반응 revision"), analysis.response_revision_number],
                [label("Runs", "실행 수"), result["sample"]["n_observations"]],
                [label("Method version", "방법 버전"), analysis.method_version],
            ],
        ),
        heading("Analysis settings", "분석 설정"),
        report_table(
            titles,
            [
                [
                    label("Maximum interaction order", "최대 상호작용 차수"),
                    result["model_policy"]["max_interaction_order"],
                ],
                [
                    label("Sum of squares", "제곱합"),
                    label(
                        "Partial drop-one term/block SS",
                        "항 또는 항 블록을 제외해 계산한 조정제곱합",
                    ),
                ],
            ],
        ),
    ]
    selection = result.get("model_selection")
    if selection is not None:
        parts += [
            heading("Model selection", "모형 선택"),
            report_table(
                titles,
                [
                    [
                        label("Method", "방법"),
                        label("Backward elimination", "후진 제거")
                        if selection["method"] != "none"
                        else label("Full specified model", "지정한 전체 모형"),
                    ],
                    ["Alpha to remove", selection["alpha_to_remove"]],
                    [label("Initial terms", "초기 항 수"), len(selection["initial_term_ids"])],
                    [label("Pooled terms", "풀링 항 수"), len(selection["pooled_term_ids"])],
                    [label("Removed terms", "제거 항 수"), len(selection["removed_term_ids"])],
                    [label("Final terms", "최종 항 수"), len(selection["final_term_ids"])],
                    [
                        label("Initial parameter count", "초기 모수 수"),
                        selection["initial_parameter_count"],
                    ],
                    [label("Pooling target", "풀링 목표 항 수"), selection["target_pool_count"]],
                    [
                        label("Final residual DF", "최종 잔차 자유도"),
                        result["sample"]["df_residual"],
                    ],
                    [
                        label("Initial residual DF", "초기 잔차 자유도"),
                        selection["initial_residual_df"],
                    ],
                ],
            ),
            report_table(
                [
                    label("Step", "단계"),
                    label("Phase", "단계 종류"),
                    label("Removed term", "제거 항"),
                    "Adj SS",
                    "P",
                    "S",
                    "R-sq",
                    "Adj R-sq",
                    "Pred R-sq",
                    "PRESS",
                ],
                [
                    [
                        step["step"] + 1,
                        label("Initial pooling", "초기 오차 풀링")
                        if step["phase"] == "initial_pooling"
                        else label("Initial model", "초기 모형")
                        if step["phase"] == "initial_full_model"
                        else label("Backward elimination", "후진 제거"),
                        step["removed_term_id"],
                        step["removal_adjusted_ss"],
                        step["removal_p_value"],
                        step["residual_standard_error"],
                        step["r_squared"],
                        step["adjusted_r_squared"],
                        step["predicted_r_squared"],
                        step["press"],
                    ]
                    for step in selection["steps"]
                ],
            ),
        ]
        if selection.get("term_catalog"):
            term_labels = {term["term_id"]: term["label"] for term in selection["term_catalog"]}
            parts.append(
                report_table(
                    titles,
                    [
                        [
                            label(en, ko),
                            ", ".join(
                                term_labels.get(term, term) for term in selection.get(key, [])
                            )
                            or "-",
                        ]
                        for en, ko, key in [
                            ("Candidate terms", "후보 항", "candidate_term_ids"),
                            (
                                "Excluded before analysis",
                                "분석 전 제외 항",
                                "initially_excluded_term_ids",
                            ),
                            ("Forced terms", "강제 유지 항", "fixed_term_ids"),
                        ]
                    ],
                )
            )
            for step in selection["steps"]:
                if not step.get("term_statistics"):
                    continue
                parts += [
                    f"<h3>{escape(label('Step', '단계'))} {step['step'] + 1}</h3>",
                    report_table(
                        [label("Term", "항"), "DF", "Coef", "P"],
                        [
                            [term["label"], term["df"], term["coefficient"], term["p_value"]]
                            for term in step["term_statistics"]
                            if term["status"] != "removed_this_step"
                        ],
                    ),
                    report_table(
                        titles,
                        [
                            ["Mallows Cp", step.get("mallows_cp")],
                            [label("Residual DF", "잔차 자유도"), step["residual_df"]],
                        ],
                    ),
                ]
                if step.get("mallows_cp_unavailable_reason"):
                    parts.append(
                        paragraph(
                            "The initial model has no residual MSE for Mallows Cp.",
                            "초기 모형에 잔차 MSE가 없어 Mallows Cp를 계산하지 않습니다.",
                        )
                    )
                if source.final_model and source.final_model.equation.scale == "treatment":
                    parts.append(
                        report_table(
                            [label("Level coefficient", "수준 계수"), "Coef", "P"],
                            [
                                [
                                    coef.get("label", term["label"]),
                                    coef["coefficient"],
                                    coef.get("p_value"),
                                ]
                                for term in step["term_statistics"]
                                for coef in term["coefficients"]
                            ],
                        )
                    )
    workflow = source.final_model
    if workflow is not None:
        parts += [
            heading("Regression equation", "회귀식"),
            f'<p class="equation">{escape(workflow.equation.display_equation)}</p>',
            paragraph(
                "Coded low = -1, high = +1. General full designs use treatment coding "
                "with the first level as reference.",
                "Coded low = -1, high = +1입니다. "
                "일반 완전요인은 첫 수준을 기준으로 treatment coding을 사용합니다.",
            ),
        ]
    parts += [
        heading("Model summary", "모형 요약"),
        report_table(
            titles,
            [
                ["S", result["fit"]["residual_standard_error"]],
                ["R-sq", result["fit"]["r_squared"]],
                ["Adjusted R-sq", result["fit"]["adjusted_r_squared"]],
                ["Predicted R-sq", workflow.predicted_r_squared if workflow else None],
                ["PRESS", workflow.press if workflow else None],
                [label("Residual DF", "잔차 자유도"), result["sample"]["df_residual"]],
            ],
        ),
    ]
    if workflow is not None:
        parts += [
            heading("Coded / treatment coefficients", "Coded / treatment 계수"),
            report_table(
                [label("Term", "항"), "Effect", "Coef", "SE Coef", "T", "P", "VIF"],
                [
                    [
                        row.label,
                        row.effect,
                        row.coefficient,
                        row.standard_error,
                        row.t_statistic,
                        row.p_value,
                        row.vif,
                    ]
                    for row in workflow.coded_coefficients
                ],
            ),
        ]
    elif result.get("terms"):
        parts += [
            heading("Stored legacy coefficients", "저장된 기존 계수"),
            report_table(
                [label("Term", "항"), "Coef", "Effect", "SE", "P"],
                [
                    [
                        term["label"],
                        term["coefficient"],
                        term.get("effect"),
                        term.get("standard_error"),
                        term.get("p_value"),
                    ]
                    for term in result["terms"]
                ],
            ),
        ]
    anova = result["anova"]
    rows = [
        [
            label("Model", "모형"),
            anova["model"]["df"],
            anova["model"]["sum_squares"],
            anova["model"]["mean_square"],
            anova["model"]["f_statistic"],
            anova["model"]["p_value"],
        ]
    ]
    for term in anova.get("rows", []):
        rows.append(
            [
                term["source"],
                term["df"],
                term["adjusted_sum_squares"],
                term["adjusted_mean_square"],
                term["f_statistic"],
                term["p_value"],
            ]
        )
    for term in result.get("terms", [])[1:]:
        rows.append(
            [
                term["label"],
                1,
                term["partial_sum_squares"],
                term["partial_sum_squares"],
                term["f_statistic"],
                term["f_p_value"],
            ]
        )
    for key, name in [("residual", label("Error", "오차")), ("total", label("Total", "전체"))]:
        row = anova[key]
        rows.append([name, row["df"], row["sum_squares"], row.get("mean_square"), None, None])
    lack = anova.get("lack_of_fit", {})
    lack_rows = (
        [
            (label("Curvature in error", "오차에 포함된 곡률"), lack["curvature_in_error"]),
            (label("Other lack of fit", "나머지 적합성 결여"), lack["non_curvature_lack_of_fit"]),
        ]
        if lack.get("curvature_in_error")
        else [(label("Lack of fit", "적합성 결여"), lack.get("lack_of_fit", lack))]
    )
    for name, row in [
        *lack_rows,
        (label("Pure error", "순수오차"), lack.get("pure_error", anova.get("pure_error", {}))),
    ]:
        if "df" in row:
            rows.append(
                [
                    name,
                    row["df"],
                    row.get("sum_squares"),
                    row.get("mean_square"),
                    row.get("f_statistic"),
                    row.get("p_value"),
                ]
            )
    parts += [
        heading("Analysis of variance", "분산분석"),
        report_table([label("Source", "변동원"), "DF", "Adj SS", "Adj MS", "F", "P"], rows),
    ]
    if workflow is not None:
        group_labels = {
            "main_effect": label("Linear", "주효과"),
            "interaction_2": label("2-way interactions", "2차 상호작용"),
            "interaction_3": label("3-way interactions", "3차 상호작용"),
            "block": label("Blocks", "블록"),
            "center_curvature": label("Curvature", "곡률"),
        }
        parts += [
            paragraph(
                "Joint group partial SS need not add to model SS.",
                "항 묶음의 부분제곱합은 모형 제곱합과 가산적이지 않을 수 있습니다.",
            ),
            report_table(
                [label("Group", "항 묶음"), "DF", "Adj SS", "Adj MS", "F", "P"],
                [
                    [
                        group_labels.get(group.kind, group.kind),
                        group.df,
                        group.adjusted_ss,
                        group.mean_square,
                        group.f_statistic,
                        group.p_value,
                    ]
                    for group in workflow.anova_groups
                ],
            ),
        ]
    diagnostics = result.get("diagnostics", {})
    parts += [
        heading("Influence diagnostics", "영향력 진단"),
        report_table(
            titles,
            [
                ["Durbin-Watson", diagnostics.get("durbin_watson")],
                ["Shapiro-Wilk P", diagnostics.get("shapiro_wilk", {}).get("p_value")],
                [
                    label("High leverage count", "높은 leverage 수"),
                    diagnostics.get("high_leverage_count"),
                ],
                [
                    label("High Cook's distance count", "높은 Cook 거리 수"),
                    diagnostics.get("high_cooks_distance_count"),
                ],
            ],
        ),
    ]
    if workflow is not None:
        effects = sorted(
            [row for row in workflow.coded_coefficients if row.effect is not None],
            key=lambda row: abs(row.effect or 0),
            reverse=True,
        )
        if effects:
            parts += [
                heading("Pareto plot of absolute effects", "절대 효과 Pareto 그림"),
                _effect_svg(
                    [(row.label, float(row.effect)) for row in effects if row.effect is not None],
                    label("Absolute effect", "절대 효과"),
                ),
            ]
        parts += [heading("Residual diagnostics", "잔차 진단"), '<div class="chart-grid">']
        for kind, view in [
            ("raw", workflow.residual_plots.raw),
            ("standardized", workflow.residual_plots.standardized),
        ]:
            residual_label = (
                label("Residual", "잔차")
                if kind == "raw"
                else label("Standardized residual", "표준화 잔차")
            )
            parts += [
                _residual_scatter(
                    label("Normal probability plot", "정규 확률 그림") + ": " + residual_label,
                    [(point.theoretical_quantile, point.residual) for point in view.qq_points],
                    label("Normal quantile", "정규 분위수"),
                    residual_label,
                    reference=(view.reference_line.slope, view.reference_line.intercept)
                    if view.reference_line
                    else None,
                ),
                _histogram(
                    view.histogram, label("Histogram", "히스토그램") + ": " + residual_label
                ),
                _residual_scatter(
                    label("Residuals versus fits", "잔차 대 적합값"),
                    [(point.fitted, point.residual) for point in view.points],
                    label("Fitted mean", "적합 평균"),
                    residual_label,
                    reference=(0.0, 0.0),
                ),
                _residual_scatter(
                    label("Residuals versus run order", "잔차 대 실행 순서"),
                    [(float(point.run_order), point.residual) for point in view.points],
                    label("Run order", "실행 순서"),
                    residual_label,
                    reference=(0.0, 0.0),
                ),
            ]
        parts += [
            "</div>",
            heading("Factorial plots: fitted means", "요인배치 그림: 적합 평균"),
            paragraph(
                "Other factor levels and blocks receive equal weights. "
                "Curvature points are excluded from corner marginal means.",
                "다른 요인의 수준과 블록을 균등 평균합니다. "
                "Corner 주변평균에는 곡률점을 포함하지 않습니다.",
            ),
            _factorial_svgs(source, locale),
        ]
    if latest_prediction is not None:
        parts += [
            heading(
                "Latest saved prediction at report creation", "보고서 생성 시점의 최근 저장 예측"
            ),
            f"<p>{escape(str(latest_prediction.prediction_id))}</p>",
            report_table(
                [
                    label("Row", "행"),
                    label("Settings", "조건"),
                    label("Fitted mean", "적합 평균"),
                    label("SE fit", "적합 표준오차"),
                    label("Mean CI", "평균 신뢰구간"),
                    label("Prediction interval", "개별 예측구간"),
                ],
                [
                    [
                        row.row_id,
                        "; ".join(f"{key}={value}" for key, value in row.factor_settings.items()),
                        row.fitted_mean,
                        row.standard_error_fit,
                        (
                            f"{row.mean_confidence_interval.lower:.7g} ... "
                            f"{row.mean_confidence_interval.upper:.7g}"
                        )
                        if row.mean_confidence_interval
                        else None,
                        (
                            f"{row.individual_prediction_interval.lower:.7g} ... "
                            f"{row.individual_prediction_interval.upper:.7g}"
                        )
                        if row.individual_prediction_interval
                        else None,
                    ]
                    for row in latest_prediction.rows
                ],
            ),
            paragraph(
                "Intervals require estimable residual variance and degrees of freedom; "
                "otherwise they are unavailable.",
                "잔차 분산과 자유도를 추정할 수 있을 때만 구간을 제공하며, "
                "그렇지 않으면 제공하지 않습니다.",
            ),
        ]
    parts += [
        heading("Warnings", "경고"),
        "<ul>"
        + "".join(
            f"<li>{escape(factorial_warning_text(str(code), locale))}</li>"
            for code in result["warnings"]
        )
        + "</ul>",
    ]
    technical = {
        "analysis_id": str(analysis.analysis_id),
        "design_id": str(design.design_id),
        "design_sha256": design.design_sha256,
        "analysis_sha256": source.sha256,
        "response_revision_sha256": analysis.response_revision_sha256,
        "method_version": analysis.method_version,
        "model_policy": result["model_policy"],
        "model_selection": selection,
        "warnings": result["warnings"],
        "created_at": analysis.created_at,
        "software": {
            key: value
            for key, value in analysis.model_dump(mode="json").items()
            if key in {"app_version", "python_version", "package_versions", "build_commit"}
        },
        "prediction_basis_schema": workflow.prediction_basis.schema_version if workflow else None,
        "included_prediction_id": str(latest_prediction.prediction_id)
        if latest_prediction
        else None,
    }
    parts += [
        f"<details><summary>{escape(label('Technical information', '기술 정보'))}</summary>"
        f"<pre>{escape(json.dumps(technical, ensure_ascii=False, indent=2))}</pre></details>"
    ]
    style = (
        "body{font:14px Arial,sans-serif;color:#202d39;max-width:1100px;"
        "margin:24px auto;padding:0 20px}h1{font-size:24px}h2{font-size:19px;margin-top:28px}"
        "table{border-collapse:collapse;width:100%;font-size:12px;overflow-wrap:anywhere}"
        "th,td{border-bottom:1px solid #dce3eb;padding:7px;text-align:left}th{background:#edf3f9}"
        "figure{margin:0;break-inside:avoid;min-width:0}svg{width:100%;height:auto}"
        "svg text{font:12px Arial,sans-serif}.chart-grid{display:grid;"
        "grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}"
        ".equation,pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin-top:24px}"
        "@media(max-width:600px){.chart-grid{grid-template-columns:1fr}}"
        "@media print{body{margin:0}h2{break-after:avoid}details{font-size:10px}}"
    )
    return (
        f'<!doctype html><html lang="{locale}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Statistical Twin Factorial Analysis</title><style>{style}</style></head><body>"
        + "".join(parts)
        + "</body></html>"
    ).encode("utf-8")


def _histogram(bins: list[Any], title: str) -> str:
    if not bins:
        return ""
    maximum = max(item.count for item in bins) or 1
    width = 490 / len(bins)
    bars = "".join(
        f'<rect x="{60+i*width:.3f}" y="{220-180*item.count/maximum:.3f}" '
        f'width="{width:.3f}" height="{180*item.count/maximum:.3f}" fill="#246ba3">'
        f"<title>{item.lower:.6g} - {item.upper:.6g}: {item.count}</title></rect>"
        for i, item in enumerate(bins)
    )
    return (
        f'<figure><figcaption>{escape(title)}</figcaption><svg viewBox="0 0 600 260" role="img">'
        f"<title>{escape(title)}</title><desc>{escape(title)}</desc>{bars}"
        f'<text x="60" y="245">{bins[0].lower:.6g}</text>'
        f'<text x="550" y="245" text-anchor="end">{bins[-1].upper:.6g}</text></svg></figure>'
    )


def _effect_svg(effects: list[tuple[str, float]], title: str) -> str:
    maximum = max(abs(value) for _, value in effects) or 1.0
    bars = []
    for index, (name, value) in enumerate(effects):
        y = 15 + index * 25
        bars.append(
            f'<text x="175" y="{y+13}" text-anchor="end">{escape(name)}</text>'
            f'<rect x="185" y="{y}" width="{330*abs(value)/maximum:.4f}" height="17" '
            f'fill="#246ba3"><title>{escape(name)}: {value:.8g}</title></rect>'
            f'<text x="525" y="{y+13}">{value:.6g}</text>'
        )
    return (
        f'<figure><svg viewBox="0 0 620 {max(90, 35+len(effects)*25)}" role="img">'
        f"<title>{escape(title)}</title><desc>{escape(title)}</desc>"
        + "".join(bars)
        + "</svg></figure>"
    )


def _residual_scatter(
    title: str,
    points: list[tuple[float, float]],
    x_title: str,
    y_title: str,
    *,
    reference: tuple[float, float] | None,
) -> str:
    if not points:
        return ""
    xmin, xmax = min(x for x, _ in points), max(x for x, _ in points)
    ref = [(x, reference[0] * x + reference[1]) for x in (xmin, xmax)] if reference else []
    ymin, ymax = min(y for _, y in points + ref), max(y for _, y in points + ref)
    dx, dy = max(xmax - xmin, 1e-12), max(ymax - ymin, 1e-12)

    def xy(x: float, y: float) -> tuple[float, float]:
        return 65 + 490 * (x - xmin) / dx, 220 - 180 * (y - ymin) / dy

    marks = []
    if ref:
        (x1, y1), (x2, y2) = [xy(x, y) for x, y in ref]
        marks.append(
            f'<line class="reference-line" x1="{x1:.3f}" y1="{y1:.3f}" '
            f'x2="{x2:.3f}" y2="{y2:.3f}" stroke="#8e5267" stroke-dasharray="5 3"/>'
        )
    for x, y in points:
        px, py = xy(x, y)
        marks.append(
            f'<circle cx="{px:.3f}" cy="{py:.3f}" r="3" fill="#246ba3">'
            f"<title>{x:.7g}, {y:.7g}</title></circle>"
        )
    return (
        f'<figure><figcaption>{escape(title)}</figcaption><svg viewBox="0 0 600 285" role="img">'
        f'<title>{escape(title)}</title><desc>{escape(x_title)}; {escape(y_title)}</desc>'
        '<path d="M60 30V225H565" fill="none" stroke="#555"/>'
        f'{"".join(marks)}<text x="280" y="280" text-anchor="middle">{escape(x_title)}</text>'
        f'<text x="15" y="150" transform="rotate(-90 15 150)">{escape(y_title)}</text>'
        f'<text x="60" y="245">{xmin:.5g}</text>'
        f'<text x="560" y="245" text-anchor="end">{xmax:.5g}</text>'
        f'<text x="55" y="40" text-anchor="end">{ymax:.5g}</text>'
        f'<text x="55" y="225" text-anchor="end">{ymin:.5g}</text></svg></figure>'
    )


def _factorial_svgs(source: FactorialModelSource, locale: ReportLocale) -> str:
    assert source.final_model is not None
    cells = source.final_model.factorial_plots.cells
    if not cells:
        return ""
    names = [factor.name for factor in source.design.factors]
    levels = {name: sorted({cell.settings[name] for cell in cells}) for name in names}
    actual: dict[str, dict[float, str]] = {}
    units: dict[str, str] = {}
    if isinstance(source.design, GeneralFactorialDesignResponse):
        for factor in source.design.factors:
            actual[factor.name] = {
                float(index): str(value) for index, value in enumerate(factor.levels)
            }
            units[factor.name] = factor.unit or ""
    else:
        for two_factor in source.design.factors:
            actual[two_factor.name] = {
                -1.0: str(
                    two_factor.low_label
                    if two_factor.factor_kind == "categorical"
                    else two_factor.low
                ),
                1.0: str(
                    two_factor.high_label
                    if two_factor.factor_kind == "categorical"
                    else two_factor.high
                ),
            }
            units[two_factor.name] = two_factor.unit or ""
    parts = ['<div class="chart-grid">']
    fitted_label = report_text(locale, en="Fitted mean", ko="적합 평균")
    for name in names:
        points = [
            (level, mean(cell.fitted_mean for cell in cells if cell.settings[name] == level))
            for level in levels[name]
        ]
        title = name + (f" ({units[name]})" if units[name] else "")
        parts.append(_line_plot(title, [(name, points)], fitted_label, actual[name]))
    for first, second in list(combinations(names, 2))[:15]:
        traces = [
            (
                f"{second}: {actual[second][trace]}",
                [
                    (
                        level,
                        mean(
                            cell.fitted_mean
                            for cell in cells
                            if cell.settings[first] == level and cell.settings[second] == trace
                        ),
                    )
                    for level in levels[first]
                ],
            )
            for trace in levels[second]
        ]
        parts.append(_line_plot(first + " * " + second, traces, fitted_label, actual[first]))
    parts.append("</div>")
    if (
        not isinstance(source.design, GeneralFactorialDesignResponse)
        and source.design.fractional is None
        and source.design.screening is None
    ):
        selected = names[:3]
        vertices = []
        for signs in product((-1.0, 1.0), repeat=len(selected)):
            settings = {name: -1.0 for name in names}
            settings.update(dict(zip(selected, signs, strict=True)))
            cell = next(item for item in cells if item.settings == settings)
            vertices.append((signs, cell.fitted_mean))
        parts.append(
            cube_svg(
                selected,
                vertices,
                report_text(
                    locale,
                    en="Cube plot: remaining factors at low",
                    ko="Cube Plot: 나머지 요인은 낮은 수준",
                ),
            )
        )
        parts.append(
            "<p>"
            + escape(
                "; ".join(
                    f"{name}: -1 = {actual[name][-1.0]}, +1 = {actual[name][1.0]}"
                    for name in selected
                )
            )
            + "</p>"
        )
    return "".join(parts)


def _line_plot(
    title: str,
    traces: list[tuple[str, list[tuple[float, float]]]],
    y_label: str,
    actual: dict[float, str],
) -> str:
    points = [point for _, values in traces for point in values]
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    colors = ["#246ba3", "#a24663", "#268074", "#9a6700"]
    lines = []
    for i, (name, values) in enumerate(traces):
        coords = " ".join(
            f"{65+490*(x-xmin)/max(xmax-xmin,1e-12):.3f},{220-170*(y-ymin)/max(ymax-ymin,1e-12):.3f}"
            for x, y in values
        )
        lines.append(
            f'<polyline points="{coords}" fill="none" stroke="{colors[i%4]}" stroke-width="2">'
            f"<title>{escape(name)}</title></polyline>"
        )
    legend = " | ".join(name for name, _ in traces)
    return (
        f'<figure><figcaption>{escape(title)}</figcaption><svg viewBox="0 0 600 270" role="img">'
        f'<title>{escape(title)}</title><desc>{escape(y_label)}; {escape(legend)}</desc>'
        f'<path d="M60 30V225H565" fill="none" stroke="#555"/>{"".join(lines)}'
        f'<text x="60" y="250">{escape(actual[xmin])}</text>'
        f'<text x="550" y="250" text-anchor="end">{escape(actual[xmax])}</text>'
        f'<text x="5" y="40">{ymax:.5g}</text><text x="5" y="220">{ymin:.5g}</text>'
        f'</svg><p>{escape(legend)}</p></figure>'
    )


def cube_svg(names: list[str], vertices: list[tuple[tuple[float, ...], float]], title: str) -> str:
    def location(signs: tuple[float, ...]) -> tuple[float, float]:
        return 80 + (signs[0] + 1) * 150 + ((signs[2] + 1) * 50 if len(signs) == 3 else 0), 260 - (
            signs[1] + 1
        ) * 85 - ((signs[2] + 1) * 30 if len(signs) == 3 else 0)

    lines = []
    for first, _ in vertices:
        x1, y1 = location(first)
        for second, _ in vertices:
            if first < second and sum(a != b for a, b in zip(first, second, strict=True)) == 1:
                x2, y2 = location(second)
                lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#7e91a4"/>')
    for signs, value in vertices:
        x, y = location(signs)
        detail = ", ".join(f"{name}={sign:g}" for name, sign in zip(names, signs, strict=True))
        lines.append(
            f'<g><title>{escape(detail)}</title><circle cx="{x}" cy="{y}" r="4" fill="#246ba3"/>'
            f'<text x="{x+7}" y="{y-7}">{value:.6g}</text></g>'
        )
    return (
        f'<figure><figcaption>{escape(title)}: {escape(", ".join(names))}</figcaption>'
        f'<svg viewBox="0 0 600 300" role="img"><title>{escape(title)}</title>'
        f'<desc>{escape(", ".join(names))}</desc>{"".join(lines)}</svg></figure>'
    )
