"""Human-readable, escaped report sections from immutable regression results."""

from html import escape
from math import isfinite, log10
from typing import Any

from app.i18n.report_text import ReportLocale, report_text


def regularized_warning_text(code: str, locale: ReportLocale) -> str:
    messages = {
        "regularized_model_predictive_not_causal": (
            "Coefficients and CV metrics do not establish causality or significance.",
            "계수와 교차검증 지표는 인과관계나 통계적 유의성을 입증하지 않습니다.",
        ),
        "regularized_model_categorical_levelwise_penalty": (
            "Category dummy coefficients are penalized separately, not as a factor block.",
            "범주형 더미 계수는 요인 전체가 아닌 수준별로 독립적으로 정규화됩니다.",
        ),
        "regularized_model_hierarchy_not_enforced": (
            "Lasso and Elastic Net do not enforce main-effect and interaction hierarchy.",
            "Lasso와 Elastic Net은 주효과·2차항·상호작용의 계층구조를 보장하지 않습니다.",
        ),
        "lasso_correlated_predictor_instability": (
            "Lasso selection can be unstable among correlated predictors.",
            "상관된 예측변수 사이에서 Lasso의 계수 선택은 불안정할 수 있습니다.",
        ),
        "lasso_all_or_most_coefficients_zero": (
            "At least half of the coefficients are zero; an intercept-only fit is possible.",
            "계수의 절반 이상이 0이며 절편만 남는 모형도 가능합니다.",
        ),
        "regularized_model_convergence_warning": (
            "Some solver fits did not converge. Review iterations, tolerance and alpha.",
            "일부 적합이 수렴하지 않았습니다. 반복 수·허용오차·alpha를 확인하세요.",
        ),
        "regularized_model_constant_fold_feature": (
            "Constant training-fold features use a scaling divisor of one.",
            "학습 fold 안의 상수 특성은 표준화 나눗값으로 1을 사용했습니다.",
        ),
        "regularized_model_negative_predicted_r_squared": (
            "CV predicted R-squared is negative and has not been truncated.",
            "교차검증 예측 R 제곱이 음수이며 0으로 절단하지 않았습니다.",
        ),
        "regularized_model_training_cv_gap": (
            "Training R-squared substantially exceeds cross-validation performance.",
            "학습 R 제곱이 교차검증 성능보다 상당히 높습니다.",
        ),
        "missing_values_excluded": (
            "Required missing values were excluded using complete-case analysis.",
            "필수 변수의 결측값을 완전 사례 정책에 따라 제외했습니다.",
        ),
        "non_numeric_values_excluded": (
            "Invalid required numeric values were excluded.",
            "필수 수치 변수의 유효하지 않은 값을 제외했습니다.",
        ),
    }
    en, ko = messages.get(code, ("Review this analysis warning.", "분석 경고를 확인하세요."))
    return report_text(locale, en=en, ko=ko)


def render_regularized_report(payload: dict[str, Any], locale: ReportLocale) -> str:
    def label(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    config = payload["regularization"]
    sample = payload["sample"]
    validation = payload.get("validation")
    training = payload["fit"]
    headings = [label("Metric", "지표"), label("Value", "값")]
    method_rows = [
        [label("Regression Method", "회귀 방법"), payload["estimator"]["kind"]],
        [label("Selected Alpha", "선택된 alpha"), config["selected_alpha"]],
        [label("Selected L1 Ratio", "선택된 L1 혼합 비율"), config["selected_l1_ratio"]],
        [label("Total Rows", "전체 행"), sample["n_total"]],
        [label("Used Rows", "사용 행"), sample["n_used"]],
        [label("Excluded Missing", "결측 제외"), sample["n_excluded_missing"]],
        [
            label("Excluded Invalid Numeric", "유효하지 않은 수치 제외"),
            sample["n_excluded_non_numeric"],
        ],
        [label("Design Features", "설계 특성"), sample["feature_count"]],
        [label("Converged", "수렴 여부"), config["converged"]],
        [label("Elapsed Seconds", "실행 시간(초)"), config["elapsed_seconds"]],
        [
            label("Nested Cross-Validation", "중첩 교차검증"),
            validation["nested"] if validation else None,
        ],
        [label("Outer Folds", "외부 fold"), validation["outer_folds"] if validation else None],
        [label("Inner Folds", "내부 fold"), validation["inner_folds"] if validation else None],
    ]
    metrics = [
        [label("Training R-squared", "학습 R 제곱"), training["r_squared"]],
        ["Training RMSE", training["rmse"]],
        ["Training MAE", training["mae"]],
    ]
    if validation:
        metrics += [
            [
                label("CV Predicted R-squared", "교차검증 예측 R 제곱"),
                validation["predicted_r_squared"],
            ],
            ["PRESS", validation["press"]],
            ["CV RMSE", validation["rmse"]],
            ["CV MAE", validation["mae"]],
        ]
    scaling_text = label(
        "Features are standardized inside each training fold; "
        "the response remains on its original scale.",
        "특성은 각 학습 fold 안에서 표준화하며 반응변수는 원척도를 유지합니다.",
    )
    parts = [
        f'<h2>{escape(label("Regularized Regression", "정규화 회귀"))}</h2>',
        _table(headings, method_rows),
        f"<p>{escape(scaling_text)}</p>",
        f'<h3>{escape(label("Model Performance", "모델 성능"))}</h3>',
        _table(headings, metrics),
        f'<h3>{escape(label("Coefficients", "계수"))}</h3>',
        _table(
            [
                label("Term", "항"),
                label("Original Scale", "원척도"),
                label("Standardized", "표준화"),
                label("Zero", "0 여부"),
            ],
            [
                [row["term"], row["estimate"], row["standardized_estimate"], row["is_zero"]]
                for row in payload["coefficients"]
            ],
        ),
    ]
    curve = config["cv_curve"]
    if curve:
        title = label("Cross-Validation Error", "교차검증 오차")
        parts += [
            f"<h3>{escape(title)}</h3>",
            _table(
                ["alpha", "l1_ratio", "MSE", label("Fold Error SD", "fold 오차 표준편차")],
                [
                    [r["alpha"], r["l1_ratio"], r["mean_squared_error"], r["fold_error_sd"]]
                    for r in curve
                ],
            ),
            _scatter(
                title,
                [
                    (log10(r["alpha"]), r["mean_squared_error"])
                    for r in curve
                    if r["l1_ratio"] == config["selected_l1_ratio"]
                ],
                "log10(alpha)",
                "MSE",
            ),
        ]
    title = label("Coefficient Path", "계수 경로")
    path = config["coefficient_path"]
    parts += [
        f"<h3>{escape(title)}</h3>",
        _table(
            ["alpha", *config["feature_order"]],
            [[r["alpha"], *r["standardized_coefficients"]] for r in path],
        ),
    ]
    for index, feature in enumerate(config["feature_order"][:20]):
        parts.append(
            _scatter(
                f"{title}: {feature}",
                [(log10(r["alpha"]), r["standardized_coefficients"][index]) for r in path],
                "log10(alpha)",
                label("Standardized Coefficient", "표준화 계수"),
            )
        )
    points = payload["diagnostics"]["points"]
    for title, x, y, x_title, y_title in [
        (
            label("Observed vs Fitted", "관측값과 적합값"),
            "observed",
            "fitted",
            label("Observed", "관측값"),
            label("Fitted", "적합값"),
        ),
        (
            label("Observed vs Cross-Validated Prediction", "관측값과 교차검증 예측값"),
            "observed",
            "oof_predicted",
            label("Observed", "관측값"),
            label("Prediction", "예측값"),
        ),
        (
            label("Residuals vs Fitted", "적합값과 잔차"),
            "fitted",
            "residual",
            label("Fitted", "적합값"),
            label("Residual", "잔차"),
        ),
        (
            label("Residuals vs Row Order", "행 순서와 잔차"),
            "row_index",
            "residual",
            label("Row", "행"),
            label("Residual", "잔차"),
        ),
    ]:
        xy = [(p[x], p[y]) for p in points if p.get(y) is not None]
        if xy:
            parts.append(_scatter(title, xy, x_title, y_title))
    limitations = label(
        "Point prediction only. Classical OLS inference and prediction intervals do not apply. "
        "Diagnostics use saved, bounded plot points; fitting uses all usable rows.",
        "점 예측만 제공합니다. 고전적 OLS 추론과 예측구간을 적용하지 않습니다. "
        "그래프는 저장된 제한된 점을 사용하며 적합에는 모든 사용 행을 사용합니다.",
    )
    parts.append(f"<p>{escape(limitations)}</p>")
    return "\n".join(parts)


def _text(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return escape(format(value, ".8g")) if isfinite(value) else "-"
    return escape(str(value))


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    return (
        "<table><thead><tr>"
        + "".join(f"<th>{escape(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{_text(v)}</td>" for v in row) + "</tr>" for row in rows)
        + "</tbody></table>"
    )


def _scatter(title: str, points: list[tuple[float, float]], x_title: str, y_title: str) -> str:
    if not points:
        return ""
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    dx, dy = max(xmax - xmin, 1e-12), max(ymax - ymin, 1e-12)
    circles = "".join(
        f'<circle cx="{65 + 490 * (x - xmin) / dx:.3f}" '
        f'cy="{225 - 185 * (y - ymin) / dy:.3f}" r="3" fill="#1667a6">'
        f"<title>{_text(x)}, {_text(y)}</title></circle>"
        for x, y in points
    )
    return (
        f"<figure><figcaption>{escape(title)}</figcaption>"
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 285" role="img">'
        f"<title>{escape(title)}</title><desc>{escape(x_title)}; {escape(y_title)}</desc>"
        '<path d="M60 30V230H560" fill="none" stroke="#555"/>'
        f'{circles}<text x="280" y="280">{escape(x_title)}</text>'
        f'<text x="15" y="150" transform="rotate(-90 15 150)">{escape(y_title)}</text>'
        f'<text x="60" y="250">{_text(xmin)}</text>'
        f'<text x="560" y="250" text-anchor="end">{_text(xmax)}</text>'
        f'<text x="55" y="40" text-anchor="end">{_text(ymax)}</text>'
        f'<text x="55" y="230" text-anchor="end">{_text(ymin)}</text></svg></figure>'
    )
