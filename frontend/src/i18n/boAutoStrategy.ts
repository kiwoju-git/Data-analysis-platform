import type { AppLocale } from "./types";

const en = {
  title: "Auto strategy advice", threshold: "LOO R² threshold", run: "Suggest strategy", apply: "Apply suggested strategy",
  meaning: "Any response below the threshold suggests exploration. All responses meeting it suggest Refine; this latter rule is our product policy. Confirm remains a manual choice, not an inferred final iteration.",
  conditional: "Conditional row LOO freezes full-fit parameters. This is not independent external validation or verified JMP numerical parity.",
  mixed: "Exploration uses MaxPro only for continuous factors. Discrete or categorical factors use our explicit mixed maximin policy; ordinal distance still requires consent.",
  snapshot: "Advice changes only the strategy draft. Review and confirmation are still required. The saved selection records the effective strategy, not this Auto receipt; download it separately if needed.",
  invalid: "Enter a finite threshold between 0 and 1.", busy: "Checking saved source", error: "The advice or current source could not be verified. No strategy was applied.",
  stale: "Historical or unavailable source: advice cannot be applied.", unavailable: "R² is unavailable for at least one response. Choose a strategy explicitly.",
  below: "At least one response is below the threshold.", all: "Every response meets the threshold; Refine is suggested.",
  response: "Response", r2: "Conditional LOO R²", scoreUnavailable: "Unavailable", proposed: "Suggested strategy", download: "Download Auto advice JSON", source: "Exact advice source",
};
const ko: typeof en = {
  title: "Auto 전략 제안", threshold: "LOO R² 임계값", run: "전략 제안 계산", apply: "제안 전략 적용",
  meaning: "반응 중 하나라도 임계값 미만이면 탐색을 제안합니다. 모두 통과하면 Refine을 제안하는 것은 제품 정책입니다. Confirm은 최종 회차를 추측하지 않고 사용자가 선택합니다.",
  conditional: "조건부 행 LOO는 전체 적합 파라미터를 고정합니다. 독립 외부 검증이나 JMP 수치 일치 검증이 아닙니다.",
  mixed: "연속 인자만 있으면 MaxPro 탐색을 사용합니다. 이산·범주 인자는 명시적인 mixed maximin 제품 정책을 사용하며 순서형 거리 동의는 여전히 필요합니다.",
  snapshot: "제안은 전략 입력만 바꿉니다. 후보 검토와 확정은 별도로 필요합니다. 저장된 선택에는 적용 전략만 기록되고 Auto 근거는 포함되지 않으므로 필요한 경우 따로 다운로드하세요.",
  invalid: "0 이상 1 이하의 유한한 임계값을 입력하세요.", busy: "저장 출처 확인 중", error: "제안 또는 현재 출처를 검증하지 못했습니다. 전략을 적용하지 않았습니다.",
  stale: "과거 또는 사용할 수 없는 출처: 제안을 적용할 수 없습니다.", unavailable: "하나 이상의 반응에서 R²를 제공할 수 없습니다. 전략을 직접 선택하세요.",
  below: "하나 이상의 반응이 임계값 미만입니다.", all: "모든 반응이 임계값을 통과하여 Refine을 제안합니다.",
  response: "반응", r2: "조건부 LOO R²", scoreUnavailable: "제공 불가", proposed: "제안 전략", download: "Auto 제안 JSON 다운로드", source: "정확한 제안 출처",
};
export const autoStrategyMessages = (locale: AppLocale): typeof en => locale === "en" ? en : ko;
