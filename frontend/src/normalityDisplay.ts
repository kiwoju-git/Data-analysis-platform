import type { NormalityResult } from "./api";
import { getCurrentLocale } from "./i18n/store";
import { translateSystemText } from "./i18n/translate";
import type { AppLocale } from "./i18n/types";

export interface NormalityDecisionDisplay {
  code:
    | "assumption_maintainable"
    | "normality_violation_signal"
    | "unavailable";
  shortLabel: string;
  detail: string;
  tone: "neutral" | "warning";
}

export function andersonPValueLabel(
  anderson: NormalityResult["columns"][number]["anderson_darling"],
  locale: AppLocale = getCurrentLocale(),
): string {
  if (anderson.p_value === undefined) return translateSystemText("제공되지 않음 (legacy result)", locale);
  if (anderson.p_value === null) return "-";
  return new Intl.NumberFormat(locale === "ko" ? "ko-KR" : "en-US", { maximumSignificantDigits: 6 }).format(
    anderson.p_value,
  );
}

export function andersonDecisionDisplay(
  decision: NormalityResult["columns"][number]["anderson_darling"]["decision_at_alpha"],
  locale?: AppLocale,
): NormalityDecisionDisplay {
  if (decision === null || decision.reject_normality === null) {
    return {
      code: "unavailable",
      shortLabel: translateSystemText("판정 불가", locale),
      detail:
        translateSystemText("현재 결과에서는 선택한 유의수준의 Anderson-Darling 판정을 제공하지 않습니다.", locale),
      tone: "neutral",
    };
  }
  if (decision.reject_normality) {
    return {
      code: "normality_violation_signal",
      shortLabel: translateSystemText("정규성 위배 신호", locale),
      detail:
        translateSystemText("유의수준 α에서 정규분포 가정에 반하는 통계적 근거가 있습니다. 분포 모양, 이상치와 분석 목적을 함께 검토하세요.", locale),
      tone: "warning",
    };
  }
  return {
    code: "assumption_maintainable",
    shortLabel: translateSystemText("정규성 가정 유지 가능", locale),
    detail:
      translateSystemText("유의수준 α에서 정규성 위배 근거가 충분하지 않습니다. 정규분포임을 증명한 것은 아니므로 Q-Q Plot, 이상치와 표본 수를 함께 확인하세요.", locale),
    tone: "neutral",
  };
}
