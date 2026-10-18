"""Additional reproducibility and diagnostic sections from saved GPR payloads."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.report_contract import ReportSection, ReportSectionDefinition
from app.services.stored_report_primitives import (
    report_column_label,
    report_grid,
    report_number,
    report_plot,
    report_table,
)

GP_SURFACE_DEFINITIONS = (
    ReportSectionDefinition("gp_surface_mean"),
    ReportSectionDefinition("gp_surface_sd"),
)


def validate_gp_report_core(payload: dict[str, Any]) -> None:
    for name in ("method", "response", "diagnostics", "optimization"):
        if name in payload and not isinstance(payload[name], dict):
            raise ValueError("analysis_report_payload_invalid")
    for name in ("predictors", "conditional_profiles"):
        if name in payload and (
            not isinstance(payload[name], list)
            or any(not isinstance(item, dict) for item in payload[name])
        ):
            raise ValueError("analysis_report_payload_invalid")
    summary = payload.get("model_summary")
    kernel = payload.get("kernel")
    if not isinstance(summary, dict) or not isinstance(kernel, dict):
        raise ValueError("analysis_report_payload_invalid")
    for key in ("training_r_squared", "training_rmse", "log_marginal_likelihood"):
        report_number(summary.get(key))
    for value in summary.values():
        if value is not None:
            report_number(value)
    if report_number(summary["training_rmse"]) < 0:
        raise ValueError("analysis_report_payload_invalid")
    if not isinstance(kernel.get("fitted_kernel"), str) or not kernel["fitted_kernel"].strip():
        raise ValueError("analysis_report_payload_invalid")
    parameters = kernel.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("analysis_report_payload_invalid")
    for parameter in parameters:
        if not isinstance(parameter, dict) or not parameter.get("parameter"):
            raise ValueError("analysis_report_payload_invalid")
        report_number(parameter.get("estimate"))
    method = payload.get("method", {})
    if method.get("length_scale") is not None and not isinstance(method["length_scale"], dict):
        raise ValueError("analysis_report_payload_invalid")
    evidence = payload.get("optimization", {})
    for key in ("final_runs", "cv_folds"):
        if key in evidence and (
            not isinstance(evidence[key], list)
            or any(not isinstance(item, dict) for item in evidence[key])
        ):
            raise ValueError("analysis_report_payload_invalid")


def gp_surface_sections(
    payload: dict[str, Any], locale: ReportLocale = "en"
) -> tuple[ReportSection, ...]:
    """Both stored surface modes, with the uncertainty definition kept explicit."""

    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    specs = (
        (
            "gp_surface_mean",
            "predicted_mean",
            text("Conditional Predicted Mean", "조건부 예측 평균"),
        ),
        (
            "gp_surface_sd",
            "predictive_standard_deviation",
            text("New Observation Predictive SD", "새 관측값 예측 표준편차"),
        ),
    )
    if "two_predictor_surface" not in payload:
        return tuple(
            ReportSection(section_id, title, "missing", reason="surface_configuration_not_stored")
            for section_id, _, title in specs
        )
    surface = payload.get("two_predictor_surface")
    if surface is None:
        return tuple(
            ReportSection(section_id, title, "not_applicable", reason="surface_not_requested")
            for section_id, _, title in specs
        )
    if (
        not isinstance(surface, dict)
        or not isinstance(surface.get("points"), list)
        or not surface["points"]
    ):
        return tuple(
            ReportSection(section_id, title, "missing", reason="surface_points_not_stored")
            for section_id, _, title in specs
        )
    predictors = {column["column_id"]: column for column in payload.get("predictors", [])}
    labels = []
    for axis in ("x", "y"):
        column_id = surface[f"{axis}_column_id"]
        column = {**predictors.get(column_id, {}), "display_name": surface[f"{axis}_display_name"]}
        labels.append(report_column_label(column, axis.upper()))
    response = payload.get("response", {})
    unit = response.get("unit")
    sections = []
    for section_id, key, title in specs:
        value_label = title + (f" ({unit})" if unit else "")
        cells = [
            (
                report_number(point["x"]),
                report_number(point["y"]),
                report_number(point[key]),
                f"{labels[0]}={point['x']}; {labels[1]}={point['y']}",
            )
            for point in surface["points"]
        ]
        if key == "predictive_standard_deviation" and any(value < 0 for _, _, value, _ in cells):
            raise ValueError("analysis_report_payload_invalid")
        markup = report_grid(title, labels[0], labels[1], value_label, cells)
        markup += report_table(
            [text("Fixed predictors (model order)", "고정 예측변수 (모형 순서)")],
            [[str(surface.get("fixed_values", []))]],
        )
        sections.append(ReportSection(section_id, title, "rendered", markup))
    return tuple(sections)


def gp_saved_details_report(payload: dict[str, Any], locale: ReportLocale) -> str:
    return "".join(section.markup or "" for section in gp_saved_sections(payload, locale))


def gp_saved_sections(payload: dict[str, Any], locale: ReportLocale) -> tuple[ReportSection, ...]:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    def heading(en: str, ko: str) -> str:
        return f"<h3>{escape(text(en, ko))}</h3>"

    method = payload.get("method", {})
    parts: list[str] = []
    sections: list[ReportSection] = []

    def take(section_id: str, en: str, ko: str) -> None:
        sections.append(ReportSection(section_id, text(en, ko), "rendered", "".join(parts)))
        parts.clear()

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
        take("gp_reproducibility", "Applied GPR Settings", "적용된 GPR 설정")
    else:
        sections.append(
            ReportSection(
                "gp_reproducibility",
                text("Applied GPR Settings", "적용된 GPR 설정"),
                "missing",
                reason="optimization_settings_not_stored",
            )
        )
    evidence = payload.get("optimization", {})
    if evidence.get("final_runs"):
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
        take(
            "gp_optimization",
            "Stored Optimization Evidence",
            "저장된 최적화 기록",
        )
    else:
        sections.append(
            ReportSection(
                "gp_optimization",
                text("Stored Optimization Evidence", "저장된 최적화 기록"),
                "missing",
                reason="optimization_evidence_not_stored",
            )
        )
    points = payload.get("diagnostics", {}).get("points", [])
    response = payload.get("response", {})
    response_label = response.get("display_name", text("Response", "반응"))
    if response.get("unit"):
        response_label += f' ({response["unit"]})'
    axis_labels = {
        "observed": text("Observed ", "관측 ") + response_label,
        "cross_validated_fitted": text("Predicted ", "예측 ") + response_label,
        "fitted": text("Fitted ", "적합 ") + response_label,
        "residual": text("Residual", "잔차")
        + (f' ({response["unit"]})' if response.get("unit") else ""),
        "row_index": text("Analysis row number", "분석 행 번호"),
        "predictive_standard_deviation": text(
            "New observation predictive SD", "새 관측값 예측 표준편차"
        )
        + (f' ({response["unit"]})' if response.get("unit") else ""),
    }
    for section_id, x, y, title in [
        (
            "gp_training_plot",
            "observed",
            "fitted",
            text("Observed vs Training Prediction", "관측값 대 학습 예측"),
        ),
        (
            "gp_cv_plot",
            "observed",
            "cross_validated_fitted",
            text("Observed vs CV Prediction", "관측값 대 CV 예측"),
        ),
        ("gp_residual_plot", "fitted", "residual", text("Residuals vs Fitted", "잔차 대 적합값")),
        (
            "gp_uncertainty_plot",
            "row_index",
            "predictive_standard_deviation",
            text("Predictive Uncertainty", "예측 불확실성"),
        ),
    ]:
        series = [
            (p[x] + 1 if x == "row_index" else p[x], p[y], str(p["row_index"] + 1))
            for p in points
            if p.get(x) is not None and p.get(y) is not None
        ]
        if not series:
            no_cv = section_id == "gp_cv_plot" and method.get("validation_method") == "none"
            sections.append(
                ReportSection(
                    section_id,
                    title,
                    "not_applicable" if no_cv else "missing",
                    reason="validation_not_requested" if no_cv else "diagnostic_points_not_stored",
                )
            )
            continue
        parts += [
            heading(title, title),
            report_plot(
                title,
                axis_labels[x],
                axis_labels[y],
                [(title, series)],
                identity=x == "observed",
                zero=y == "residual",
            ),
        ]
        take(section_id, title, title)
    predictor_units = {
        item["column_id"]: item.get("unit") for item in payload.get("predictors", [])
    }

    def predictor_label(column_id: str, name: str) -> str:
        unit = predictor_units.get(column_id)
        return name + (f" ({unit})" if unit else "")

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
                text("95% new-observation PI lower", "95% 새 관측값 예측구간 하한")
                if key == "lower"
                else text("95% new-observation PI upper", "95% 새 관측값 예측구간 상한"),
                [(p["value"], p["predictive_interval_95"][key], "") for p in profile["points"]],
            )
            for key in ("lower", "upper")
        ]
        parts += [
            heading(title, title),
            report_plot(
                title,
                predictor_label(profile["column_id"], profile["display_name"]),
                response_label,
                profile_series,
                lines=True,
            ),
            report_table(
                [text("Fixed predictors (model order)", "고정 예측변수 (모형 순서)")],
                [[str(profile["fixed_values"])]],
            ),
        ]
    if parts:
        take("gp_profiles", "Conditional Profiles", "조건부 예측 프로파일")
    else:
        stored_profiles = "conditional_profiles" in payload
        sections.append(
            ReportSection(
                "gp_profiles",
                text("Conditional Profiles", "조건부 예측 프로파일"),
                "not_applicable" if stored_profiles else "missing",
                reason="profiles_not_requested" if stored_profiles else "profiles_not_stored",
            )
        )
    surface = payload.get("two_predictor_surface")
    if surface:
        parts += [
            heading("Stored Two-Predictor Surface", "저장된 두 예측변수 곡면"),
            report_table(
                [
                    predictor_label(surface["x_column_id"], surface["x_display_name"]),
                    predictor_label(surface["y_column_id"], surface["y_display_name"]),
                    text("Predicted mean", "예측 평균")
                    + (f' ({response["unit"]})' if response.get("unit") else ""),
                    axis_labels["predictive_standard_deviation"],
                ],
                [
                    [p["x"], p["y"], p["predicted_mean"], p["predictive_standard_deviation"]]
                    for p in surface["points"]
                ],
            ),
        ]
        take("gp_surface_values", "Stored Surface Values", "저장된 곡면 값")
    else:
        stored_surface = "two_predictor_surface" in payload
        sections.append(
            ReportSection(
                "gp_surface_values",
                text("Stored Surface Values", "저장된 곡면 값"),
                "not_applicable" if stored_surface else "missing",
                reason="surface_not_requested" if stored_surface else "surface_not_stored",
            )
        )
    return tuple(sections)
