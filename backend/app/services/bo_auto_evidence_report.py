"""Render only the immutable Auto receipt shared by numeric and mixed batches."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.stored_report_primitives import report_table


def auto_evidence_markup(
    evidence: dict[str, Any], goals: dict[str, Any], locale: ReportLocale
) -> str:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    diagnostic, decision = evidence["diagnostic"], evidence["decision"]
    markup = (
        '<section data-auto-evidence="1"><h4>'
        + escape(text("Saved Auto decision evidence", "저장된 Auto 판단 근거"))
        + "</h4>"
    )
    markup += report_table(
        [text("Evidence", "판단 근거"), text("Stored value", "저장값")],
        [
            [text("Routing model ID", "판단용 모형 ID"), diagnostic["model_id"]],
            [text("Routing model SHA-256", "판단용 모형 SHA-256"), diagnostic["model_sha256"]],
            [text("History SHA-256", "관측 이력 SHA-256"), diagnostic["history_sha256"]],
            [text("Decision SHA-256", "판단 SHA-256"), evidence["decision_sha256"]],
            [text("Threshold", "임계값"), decision["threshold"]],
            [text("Comparison", "비교 규칙"), decision["comparison"]],
            [text("Decision policy", "판단 정책"), decision["policy"]],
            [text("Applied policy", "적용 정책"), decision["recommended_policy"]],
        ],
    )
    markup += report_table(
        [text("Response", "반응"), "LOO R²", "RMSE", "N"],
        [
            [goals[row["response_id"]]["name"], row["r_squared"], row["rmse"], row["n_scored"]]
            for row in diagnostic["calculation"]["responses"]
        ],
    )
    markup += (
        "<p>"
        + escape(
            text(
                "Conditional row-LOO keeps full-fit parameters fixed; "
                "this is not external validation. The routing model is separate from "
                "model-free candidate selection. Export does not rerun LOO.",
                "전체 적합 파라미터를 고정한 조건부 행 LOO이며 외부 검증이 아닙니다. "
                "판단용 모형과 모형 없는 후보 선택은 구분됩니다. "
                "내보내기에서 LOO를 재실행하지 않습니다.",
            )
        )
        + "</p></section>"
    )
    return markup
