"""HTML view of an authoritative completed request and prediction response."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.report_contract import (
    ReportBody,
    ReportDefinition,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
)
from app.services.stored_report_primitives import report_column_label, report_table

COMPLETED_PREDICTION_REPORT_DEFINITION = ReportDefinition(
    "regression.completed_prediction",
    "completed_prediction",
    (1,),
    "completed_prediction_report",
    "1.1.0",
    (
        ReportVariantDefinition(
            "completed_prediction",
            (
                ReportSectionDefinition("provenance", True),
                ReportSectionDefinition("inputs", True),
                ReportSectionDefinition("predictions", True),
                ReportSectionDefinition("limitations", True),
            ),
        ),
    ),
)


def render_completed_prediction(payload: dict[str, Any], locale: ReportLocale) -> ReportBody:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    predictors = payload["predictors"]
    result = payload["result"]
    request_rows = payload["request"]["rows"]
    by_id = {row["client_row_id"]: row for row in result["rows"]}
    rows = [by_id[row["client_row_id"]] for row in request_rows]
    sections = [
        ReportSection(
            "provenance",
            text("Stored prediction identity", "저장 예측 식별 정보"),
            "rendered",
            report_table(
                [text("Field", "항목"), text("Value", "값")],
                [
                    ("Model ID", payload["model_id"]),
                    ("Model manifest SHA-256", payload["model_manifest_sha256"]),
                    ("Source analysis ID", payload["source_analysis_id"]),
                    ("Source result SHA-256", payload["source_result_sha256"]),
                    (text("Server completion time", "서버 완료 시각"), payload["created_at"]),
                    ("Request SHA-256", payload["request_sha256"]),
                    ("Response SHA-256", payload["result_sha256"]),
                    (
                        text("Response", "반응"),
                        report_column_label(payload["response"], "Response"),
                    ),
                ],
            ),
        ),
        ReportSection(
            "inputs",
            text("Exact prediction inputs", "정확한 예측 입력"),
            "rendered",
            report_table(
                [text("Input row ID", "입력 행 ID")]
                + [report_column_label(item, str(item["column_id"])) for item in predictors],
                [
                    [row["client_row_id"]]
                    + [row["values"][item["column_id"]] for item in predictors]
                    for row in request_rows
                ],
            ),
        ),
    ]
    if payload["family"] == "gaussian_process":
        headers = [
            text("Input row ID", "입력 행 ID"),
            text("Predicted mean", "예측 평균"),
            text("Latent SD", "잠재 반응 표준편차"),
            text("Latent 95% lower", "잠재 반응 95% 하한"),
            text("Latent 95% upper", "잠재 반응 95% 상한"),
            text("New-observation SD", "새 관측값 예측 표준편차"),
            text("New-observation 95% lower", "새 관측값 95% 하한"),
            text("New-observation 95% upper", "새 관측값 95% 상한"),
        ]
        values = [
            [
                row["client_row_id"],
                row["predicted_mean"],
                row["latent_standard_deviation"],
                row["latent_interval_95"]["lower"],
                row["latent_interval_95"]["upper"],
                row["predictive_standard_deviation"],
                row["predictive_interval_95"]["lower"],
                row["predictive_interval_95"]["upper"],
            ]
            for row in rows
        ]
        limitation = text(
            "Latent uncertainty and new-observation uncertainty are distinct. "
            "The stored 95% intervals are not recalculated during export.",
            "잠재 반응 불확실성과 새 관측값 불확실성은 다릅니다. "
            "저장된 95% 구간을 출력하며 내보내기 시 다시 계산하지 않습니다.",
        )
    else:
        headers = [text("Input row ID", "입력 행 ID"), text("Point prediction", "점예측")]
        values = [[row["client_row_id"], row["predicted_value"]] for row in rows]
        limitation = text(
            "PLS supplies point predictions only; "
            "no confidence or prediction interval is available.",
            "PLS는 점예측만 제공하며 신뢰구간이나 예측구간은 제공하지 않습니다.",
        )
    sections.append(
        ReportSection(
            "predictions",
            text("Stored predictions", "저장 예측값"),
            "rendered",
            report_table(
                headers,
                values,
                numeric_column_groups=((3, 4), (6, 7))
                if payload["family"] == "gaussian_process"
                else (),
            ),
        )
    )
    warnings = [(row["client_row_id"], code) for row in rows for code in row.get("warnings", [])]
    warning_text = text(
        "Extrapolation warnings identify inputs outside the model's training ranges. "
        "Historical results remain readable after model removal; "
        "they do not enable new predictions.",
        "외삽 경고는 모델 학습 범위를 벗어난 입력을 표시합니다. "
        "모델 삭제 후에도 과거 결과는 보존되지만 새 예측을 실행할 수는 없습니다.",
    )
    sections.append(
        ReportSection(
            "limitations",
            text("Warnings and limitations", "경고와 해석 제한"),
            "rendered",
            f"<p>{escape(limitation)}</p><p>{escape(warning_text)}</p>"
            + report_table(
                [text("Input row ID", "입력 행 ID"), text("Warning code", "경고 코드")], warnings
            ),
        )
    )
    return ReportBody("completed_prediction", tuple(sections))
