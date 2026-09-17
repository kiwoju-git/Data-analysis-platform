"""Additional reproducibility and diagnostic sections from saved GPR payloads."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.stored_report_primitives import report_plot, report_table


def gp_saved_details_report(payload: dict[str, Any], locale: ReportLocale) -> str:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    def heading(en: str, ko: str) -> str:
        return f"<h3>{escape(text(en, ko))}</h3>"

    method = payload.get("method", {})
    parts: list[str] = []
    settings = method.get("length_scale")
    if settings:
        parts += [
            heading("Applied GPR Settings", "적용된 GPR 설정"),
            report_table(
                [text("Setting", "설정"), text("Value", "값")],
                [
                    [text("Optimizer", "최적화 알고리즘"), method["optimizer"]],
                    [
                        text("Length lower / initial / upper", "길이 척도 하한 / 초기값 / 상한"),
                        f'{settings["lower"]} / {settings["initial"]} / {settings["upper"]}',
                    ],
                    [
                        text("Coordinates / SD ddof", "좌표 / 표준편차 ddof"),
                        f'{settings["coordinate_system"]} / {method["scaling_ddof"]}',
                    ],
                    [
                        text("Final / CV restarts", "최종 / CV 재시작"),
                        f'{method["optimizer_restarts"]} / {method["cv_optimizer_restarts"]}',
                    ],
                    [text("Seed", "Seed"), method["random_seed"]],
                    [
                        text(
                            "Noise mode / fixed SD / jitter", "Noise 설정 / 고정 표준편차 / jitter"
                        ),
                        f'{method["noise_mode"]} / {method["fixed_noise_standard_deviation"]} / '
                        f'{method["jitter"]}',
                    ],
                    *[[name, value] for name, value in method["package_versions"].items()],
                ],
            ),
        ]
        evidence = payload.get("optimization", {})
        parts += [
            heading("Optimizer Convergence", "최적화 수렴 기록"),
            report_table(
                [
                    text("Start", "시작"),
                    "Optimizer",
                    text("Status", "상태"),
                    text("Iterations", "반복"),
                    text("Evaluations", "평가"),
                    text("Original gradient", "원래 gradient"),
                    text("Optimizer gradient", "최적화 gradient"),
                ],
                [
                    [
                        i + 1,
                        r["scipy_method"],
                        r["termination"],
                        r["iterations"],
                        r["evaluations"],
                        r["theta_gradient_inf_norm"],
                        r["optimizer_gradient_inf_norm"],
                    ]
                    for i, r in enumerate(evidence.get("final_runs", []))
                ],
            ),
            report_table(
                [
                    "CV fold",
                    "Seed",
                    text("Converged", "수렴"),
                    text("Training / validation N", "학습 / 검증 N"),
                ],
                [
                    [
                        f["fold"],
                        f["seed"],
                        f["converged"],
                        f'{len(f["training_row_indices"])} / {len(f["validation_row_indices"])}',
                    ]
                    for f in evidence.get("cv_folds", [])
                ],
            ),
        ]
    points = payload.get("diagnostics", {}).get("points", [])
    for x, y, title in [
        (
            "cross_validated_fitted",
            "observed",
            text("Observed vs CV Prediction", "관측값 대 CV 예측"),
        ),
        ("fitted", "residual", text("Residuals vs Fitted", "잔차 대 적합값")),
        (
            "fitted",
            "predictive_standard_deviation",
            text("Predictive Uncertainty", "예측 불확실성"),
        ),
    ]:
        series = [
            (p[x], p[y], str(p["row_index"] + 1))
            for p in points
            if p.get(x) is not None and p.get(y) is not None
        ]
        parts += [
            heading(title, title),
            report_plot(
                title, x, y, [(title, series)], identity=y == "observed", zero=y == "residual"
            ),
        ]
    for profile in payload.get("conditional_profiles", []):
        title = text("Conditional Profile", "조건부 profile") + ": " + profile["display_name"]
        profile_series = [
            (
                text("Mean", "평균"),
                [(p["value"], p["predicted_mean"], "") for p in profile["points"]],
            )
        ]
        profile_series += [
            (
                text("95% lower", "95% 하한") if key == "lower" else text("95% upper", "95% 상한"),
                [(p["value"], p["predictive_interval_95"][key], "") for p in profile["points"]],
            )
            for key in ("lower", "upper")
        ]
        parts += [
            heading(title, title),
            report_plot(
                title, profile["display_name"], text("Response", "반응"), profile_series, lines=True
            ),
            report_table(
                [text("Fixed predictors (model order)", "고정 예측변수 (모형 순서)")],
                [[str(profile["fixed_values"])]],
            ),
        ]
    surface = payload.get("two_predictor_surface")
    if surface:
        parts += [
            heading("Stored Two-Predictor Surface", "저장된 두 예측변수 곡면"),
            report_table(
                [
                    surface["x_display_name"],
                    surface["y_display_name"],
                    text("Predicted mean", "예측 평균"),
                    text("Observation predictive SD", "관측 예측 표준편차"),
                ],
                [
                    [p["x"], p["y"], p["predicted_mean"], p["predictive_standard_deviation"]]
                    for p in surface["points"]
                ],
            ),
        ]
    return "".join(parts)
