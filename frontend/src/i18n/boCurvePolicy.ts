import type { AppLocale } from "./types";
const en = {
  goals: "Desirability goals · 1–4 responses",
  title: "Recommendation curve", linear: "DS linear", gaussian: "Two-sided Gaussian target",
  lower: "Desirability at lower control", upper: "Desirability at upper control",
  meaning: "The selected curve is saved with this new study and used by its recommendations. Target peak = 1; side controls are preferences, not specification probabilities. Maximize and minimize retain DS-linear curves. JMP numerical equivalence is not established.",
  invalid: "Side desirability must be a finite number strictly between 0 and 1.",
  stored: "Stored recommendation curves", response: "Response", policy: "Curve", peak: "Peak",
};
const ko: typeof en = {
  goals: "Desirability 목표 · 반응 1~4개",
  title: "추천에 사용할 곡선", linear: "DS 선형", gaussian: "양측 Gaussian 목표 곡선",
  lower: "하한 제어점 desirability", upper: "상한 제어점 desirability",
  meaning: "선택한 곡선은 새 연구에 저장되어 해당 연구의 추천에 사용됩니다. 목표점은 1이며 좌우 제어점은 선호도이지 규격 만족확률이 아닙니다. 최대화·최소화는 DS 선형을 유지합니다. JMP와의 수치 일치는 검증되지 않았습니다.",
  invalid: "좌우 desirability에는 0보다 크고 1보다 작은 유한한 숫자가 필요합니다.",
  stored: "저장된 추천 곡선", response: "반응", policy: "곡선", peak: "최댓값",
};
export const curvePolicyMessages = (locale: AppLocale) => locale === "ko" ? ko : en;
