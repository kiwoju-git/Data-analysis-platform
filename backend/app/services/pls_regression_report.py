"""PLS report from immutable schema-1 results; no estimator or dataset access."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.stored_report_primitives import report_plot, report_table


def pls_warning_text(code: str, locale: ReportLocale) -> str:
    messages = {
        "pls_predictive_not_causal": (
            "PLS predicts associations, not causal effects.",
            "PLS는 예측 관계를 나타내며 인과효과를 입증하지 않습니다.",
        ),
        "pls_no_classical_coefficient_p_values": (
            "Classical OLS coefficient p-values and prediction intervals are not available.",
            "고전적 OLS 계수 p-value와 예측구간은 제공하지 않습니다.",
        ),
        "pls_negative_predicted_r_squared": (
            "CV predicted R-squared is negative; it has not been clipped.",
            "CV 예측 R 제곱이 음수이며 0으로 절단하지 않았습니다.",
        ),
        "pls_selected_maximum_component": (
            "The selected count is the maximum evaluated component count.",
            "평가한 최대 성분 수가 선택되었습니다.",
        ),
        "pls_training_r_squared_much_higher_than_cv": (
            "Training performance exceeds cross-validation performance substantially.",
            "학습 성능이 교차검증 성능보다 상당히 높습니다.",
        ),
        "pls_model_not_converged": (
            "One or more PLS fits did not converge.",
            "하나 이상의 PLS 적합이 수렴하지 않았습니다.",
        ),
        "missing_values_excluded": (
            "Missing or invalid numeric rows were excluded by complete-case policy.",
            "결측 또는 비수치 행을 완전 사례 정책으로 제외했습니다.",
        ),
    }
    en, ko = messages.get(
        code, ("Review the saved warning code.", "저장된 경고 코드를 확인하세요.")
    )
    return report_text(locale, en=en, ko=ko)


def render_pls_report(payload: dict[str, Any], locale: ReportLocale) -> str:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    def heading(en: str, ko: str) -> str:
        return f"<h3>{escape(text(en, ko))}</h3>"

    def paragraph(en: str, ko: str) -> str:
        return f"<p>{escape(text(en, ko))}</p>"

    if payload.get("schema_version") != 1:
        raise ValueError("analysis_report_schema_unsupported")
    try:
        method, sample, selection, summary = (
            payload[key] for key in ("method", "sample", "component_selection", "model_summary")
        )
        predictors, latent = payload["predictors"], payload["latent_components"]
        selected = int(summary["selected_components"])
        points, total = (
            payload["diagnostics"]["points"],
            payload["diagnostics"]["point_count_total"],
        )
        if not selection["rows"] or not points or not predictors or selected < 1:
            raise ValueError("analysis_report_payload_invalid")
        metric_headers = [text("Setting", "설정"), text("Value", "값")]
        settings = [
            [text("Response", "반응변수"), payload["response"]["display_name"]],
            [text("Predictors", "예측변수"), ", ".join(p["display_name"] for p in predictors)],
            [
                text("Used / excluded / total rows", "사용 / 제외 / 전체 행"),
                f'{sample["n_used"]} / {sample["n_excluded"]} / {sample["n_total"]}',
            ],
            [
                text("Missing / nonnumeric exclusions", "결측 / 비수치 제외"),
                f'{sample["n_excluded_missing"]} / {sample["n_excluded_non_numeric"]}',
            ],
            [text("Standardization (sample SD)", "표준화 (표본 표준편차)"), method["scale"]],
            [
                text("Component selection", "성분 선택"),
                text("Automatic CV", "CV 자동 선택")
                if method["component_selection"] == "automatic_cv"
                else text("Fixed", "직접 지정"),
            ],
            [
                text("CV method / folds", "CV 방법 / fold"),
                f'{method["cv_method"]} / {method["cv_folds"]}',
            ],
            [
                text("Shuffle / seed", "무작위 섞기 / seed"),
                f'{method["cv_shuffle"]} / {method["cv_seed"]}',
            ],
            [
                text("Maximum iterations / tolerance", "최대 반복 / 허용오차"),
                f'{method["max_iter"]} / {method["tol"]}',
            ],
            [text("Missing policy", "결측 정책"), method["missing_policy"]],
        ]
        parts = [
            f'<section data-pls-report="1" data-selected-components="{selected}">',
            heading("PLS Method and Sample", "PLS 분석 방법과 표본"),
            report_table(metric_headers, settings),
        ]
        headers = [
            text("Components", "성분 수"),
            text("X variance ratio", "X 설명 비율"),
            "Training SSE",
            "Training R-squared",
            "PRESS",
            "Predicted R-squared",
            "CV RMSE",
            text("Selected", "선택"),
        ]
        keys = (
            "components",
            "x_variance",
            "training_sse",
            "training_r_squared",
            "press",
            "predicted_r_squared",
            "cv_rmse",
        )
        parts += [
            heading("Component Selection", "성분 선택"),
            report_table(
                headers,
                [
                    [
                        *(row[key] for key in keys),
                        text("Selected", "선택") if row["components"] == selected else "-",
                    ]
                    for row in selection["rows"]
                ],
            ),
        ]
        series = [
            (
                label,
                [
                    (float(r["components"]), float(r[key]), str(r["components"]))
                    for r in selection["rows"]
                ],
            )
            for key, label in [
                ("training_r_squared", "Training R-squared"),
                ("predicted_r_squared", "CV R-squared"),
                ("x_variance", text("X variance ratio", "X 설명 비율")),
            ]
        ]
        parts += [
            '<div data-pls-selection-plot="1">',
            report_plot(
                text("PLS Model Selection", "PLS 모형 선택"),
                headers[0],
                text("Ratio", "비율"),
                series,
                lines=True,
                selected_x=selected,
            ),
            "</div>",
        ]
        parts += [
            heading("Selected Model Summary", "선택 모형 요약"),
            report_table(
                metric_headers,
                [
                    [label, summary[key]]
                    for key, label in [
                        ("selected_components", text("Selected components", "선택 성분 수")),
                        ("training_r_squared", text("Training R-squared", "학습 R 제곱")),
                        ("predicted_r_squared", text("CV predicted R-squared", "CV 예측 R 제곱")),
                        ("press", "PRESS"),
                        ("cv_rmse", "CV RMSE"),
                        (
                            "cumulative_x_variance",
                            text("Cumulative X variance ratio", "누적 X 설명 비율"),
                        ),
                    ]
                ],
            ),
        ]
        parts += [
            heading("Regression Coefficients", "회귀계수"),
            report_table(
                [
                    text("Predictor", "예측변수"),
                    text("Original scale", "원래 단위"),
                    text("Standardized", "표준화"),
                ],
                [
                    [row["display_name"], row["coefficient"], row["standardized_coefficient"]]
                    for row in payload["coefficients"]
                ],
            ),
            paragraph(
                "Standardized coefficients express sample-SD response changes per sample-SD "
                "predictor change. They are not significance tests.",
                "표준화 계수는 예측변수 표본 표준편차 변화에 대한 반응 표본 표준편차 변화를 "
                "나타내며 유의성 검정이 아닙니다.",
            ),
        ]
        parts += [
            heading("Stored Diagnostic Coverage", "저장된 진단 범위"),
            f'<p>{len(points)} / {total}; '
            f'{escape(text("saved point limit", "저장 점 수 상한"))}: '
            f'{payload["diagnostics"]["point_limit"]}.</p>',
            paragraph(
                "Only stored points are shown; no source rows are reread.",
                "저장된 점만 표시하며 원자료를 다시 읽지 않습니다.",
            ),
        ]
        observed = text("Observed response", "관측 반응")
        for key, label in [
            ("fitted", text("Training prediction", "학습 예측")),
            ("cross_validated_fitted", text("Cross-validated prediction", "교차검증 예측")),
        ]:
            parts += [
                heading(label, label),
                report_plot(
                    label,
                    label,
                    observed,
                    [(label, [(p[key], p["observed"], str(p["row_index"] + 1)) for p in points])],
                    identity=True,
                ),
            ]
        row_label = text("Observation", "관측 행")
        score_title = text("Score Plot", "Score Plot")
        score_points = [
            (
                row[0] if selected > 1 else latent["score_row_indices"][i] + 1,
                row[1] if selected > 1 else row[0],
                str(latent["score_row_indices"][i] + 1),
            )
            for i, row in enumerate(latent["x_scores"])
        ]
        parts += [
            heading(score_title, score_title),
            '<div data-pls-score-plot="1">',
            report_plot(
                score_title,
                "Component 1" if selected > 1 else row_label,
                "Component 2" if selected > 1 else "Component 1",
                [(score_title, score_points)],
                zero=True,
            ),
            "</div>",
            report_table(
                [row_label, *[f"X Score {i+1}" for i in range(selected)]],
                [
                    [latent["score_row_indices"][i] + 1, *row]
                    for i, row in enumerate(latent["x_scores"])
                ],
            ),
        ]
        for component in range(selected):
            label = text(f"Loading Component {component+1}", f"Loading 성분 {component+1}")
            parts += [
                f'<div data-loading-component="{component+1}">',
                heading(label, label),
                report_plot(
                    label,
                    text("Predictor index", "예측변수 순서"),
                    "X Loading",
                    [
                        (
                            label,
                            [
                                (i + 1, row[component], predictors[i]["display_name"])
                                for i, row in enumerate(latent["x_loadings"])
                            ],
                        )
                    ],
                    zero=True,
                ),
                report_table(
                    [text("Predictor", "예측변수"), "X Loading", "X Weight", "X Rotation"],
                    [
                        [
                            p["display_name"],
                            latent["x_loadings"][i][component],
                            latent["x_weights"][i][component],
                            latent["x_rotations"][i][component],
                        ]
                        for i, p in enumerate(predictors)
                    ],
                ),
                "</div>",
            ]
        parts += [
            report_table(
                [headers[0], "Y Loading", "Y Weight"],
                [
                    [i + 1, latent["y_loadings"][0][i], latent["y_weights"][0][i]]
                    for i in range(selected)
                ],
            )
        ]
        residual = text("Residual", "잔차")
        parts += [
            heading("Residual Diagnostics", "잔차 진단"),
            '<div data-pls-residual-plot="1">',
            report_plot(
                residual,
                text("Fitted value", "적합값"),
                residual,
                [
                    (
                        residual,
                        [(p["fitted"], p["residual"], str(p["row_index"] + 1)) for p in points],
                    )
                ],
                zero=True,
            ),
            report_plot(
                residual,
                row_label,
                residual,
                [
                    (
                        residual,
                        [
                            (p["row_index"] + 1, p["residual"], str(p["row_index"] + 1))
                            for p in points
                        ],
                    )
                ],
                zero=True,
            ),
            "</div>",
            report_table(
                [
                    row_label,
                    observed,
                    text("Fitted", "적합값"),
                    "OOF",
                    residual,
                    text("CV residual", "CV 잔차"),
                ],
                [
                    [
                        p["row_index"] + 1,
                        p["observed"],
                        p["fitted"],
                        p["cross_validated_fitted"],
                        p["residual"],
                        p["cross_validated_residual"],
                    ]
                    for p in points
                ],
            ),
        ]
        parts += [
            heading("Warnings and Limitations", "경고와 해석 제한"),
            "<ul>",
            *(
                f"<li>{escape(pls_warning_text(code, locale))} <code>{escape(code)}</code></li>"
                for code in payload["warnings"]
            ),
            "</ul>",
            paragraph(
                "Component-selection CV is not independent external validation. Separate point "
                "predictions are not part of this saved analysis; "
                "export completed predictions separately.",
                "성분 선택에 사용한 CV는 독립적인 외부 검증이 아닙니다. "
                "별도 점 예측은 이 저장 분석에 "
                "포함되지 않으며 완료된 예측을 별도로 내보내세요.",
            ),
            "</section>",
        ]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("analysis_report_payload_invalid") from exc
    return "".join(parts)
