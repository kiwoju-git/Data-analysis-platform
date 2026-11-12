import type { AppLocale } from "./types";

const en = {
  title: "Experiment progress", observed: "Measured response and best so far", scoreTitle: "Observed desirability progress",
  space: "Experiment locations", trial: "Trial number", response: "Response", measured: "Measured value", best: "Best so far",
  distance: "Absolute target distance", target: "Target", score: "Observed desirability", state: "State", origin: "Origin",
  completed: "Completed", pending: "Pending", abandoned: "Abandoned", replicate: "Replicate", initial: "Initial design", recommendation: "Recommendation",
  order: "Trial numbers show registration order, not measurement time. Best-so-far follows this order among completed trials.",
  current: "Current study history", scoreMeaning: "Derived from actual response vectors and stored goal curves, not predicted desirability or success probability.",
  noScore: "No desirability limits are defined for this scalar goal. No limits or scores are inferred.",
  projection: "Projection of actual factor settings, not a fitted surface or a fixed-value slice. Overlapping trials remain separate.",
  categories: "Category positions identify declared levels; spacing is not a physical distance.",
  levels: "Declared level labels (# uses the declared level order)",
  twoFactors: "Two factors are required for a factor-space plot.", empty: "No completed measurements yet.",
  invalid: "Some stored values cannot be displayed. They are not replaced with zero.", unavailable: "This view is unavailable for the stored source.",
  x: "X factor", y: "Y factor", data: "Displayed values", n: "Completed measurements", view: "Response view",
  actual: "Actual response", history: "History revision", direction: "Response goal", maximize: "Maximize", minimize: "Minimize", match_target: "Match target",
};
const ko: typeof en = {
  title: "실험 진행 그래프", observed: "실측 반응과 누적 최선값", scoreTitle: "관측 desirability 추이",
  space: "실험 위치", trial: "실험 번호", response: "반응", measured: "실측값", best: "누적 최선값",
  distance: "목표와의 절대 거리", target: "목표값", score: "관측 desirability", state: "상태", origin: "출처",
  completed: "완료", pending: "실험 대기", abandoned: "포기", replicate: "반복 실험", initial: "초기 설계", recommendation: "추천 실험",
  order: "실험 번호는 등록 순서이며 실제 측정 시간순이 아닙니다. 누적 최선값은 이 번호순의 완료 실험을 기준으로 합니다.",
  current: "현재 Study 관측 이력", scoreMeaning: "실제 반응 벡터와 저장된 목표 곡선으로 계산한 적합도이며 예측 desirability나 성공확률이 아닙니다.",
  noScore: "이 단일 반응 목표에는 desirability 한계가 정의되어 있지 않습니다. 한계나 점수를 임의로 만들지 않습니다.",
  projection: "실제 요인 설정의 투영이며 적합 곡면이나 고정값 단면이 아닙니다. 겹치는 실험도 각각 유지합니다.",
  categories: "범주 위치는 선언된 수준을 구분하며 간격이 물리적 거리를 뜻하지 않습니다.",
  levels: "범주 전체 이름 (#은 선언된 수준 순서)",
  twoFactors: "요인 공간 그래프에는 요인이 두 개 이상 필요합니다.", empty: "아직 완료된 측정값이 없습니다.",
  invalid: "일부 저장값을 표시할 수 없습니다. 0으로 대체하지 않습니다.", unavailable: "이 저장 source에서는 해당 보기를 제공할 수 없습니다.",
  x: "X 요인", y: "Y 요인", data: "표시값", n: "완료 측정 수", view: "반응 보기",
  actual: "실제 반응", history: "이력 revision", direction: "반응 목표", maximize: "최대화", minimize: "최소화", match_target: "목표값 맞추기",
};
export const progressMessages = (locale: AppLocale) => locale === "en" ? en : ko;
