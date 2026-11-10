import type { AppLocale } from "./types";
const en = {
  underflow: "Some Gaussian tail values are below floating-point range and display as 0; they are not exact zero preferences. Point count",
  tail: "Normal tail bound", integrationError: "Quadrature error estimate",
  title: "Target curve comparison", preview: "Preview only: not saved or applied to recommendations.",
  response: "Target response", select: "Choose a match-target response", lower: "Desirability at lower control", upper: "Desirability at upper control",
  meaning: "Peak desirability is fixed at 1. Side controls must be between 0 and 1. Gaussian tails continue beyond the controls; these are preferences, not specification probabilities. This comparison never changes a saved recommendation's curve policy.",
  assumed: "Compare an explicitly assumed Gaussian distribution", mean: "Assumed mean (response unit)", sd: "Assumed SD (response unit)",
  incumbent: "Assumed incumbent (desirability)", xi: "Improvement margin xi (desirability)",
  assumedMeaning: "These assumptions are not fitted GP predictions. Beta EI uses moment matching, not exact transformed-Gaussian EI or JMP numerical equivalence.",
  run: "Compare curves", running: "Comparing...", invalid: "Check ordered lower < target < upper, side desirability in (0,1), and complete finite assumption values. SD and xi must be nonnegative; incumbent and xi must not exceed 1.",
  failure: "Comparison did not complete. No study or experiment was changed. Retry explicitly.", gaussian: "Two-sided Gaussian target", linear: "Existing DS-linear target",
  value: "Response value", desirability: "Desirability", moments: "Assumed-distribution comparison", policy: "Curve policy", expected: "Expected desirability", variance: "Desirability variance", ei: "Moment-matched Beta EI",
  unavailable: "Unavailable at this numerical precision", controls: "Control point comparison", details: "Numerical details", empty: "Choose a target response to compare curves.",
};
const ko: typeof en = {
  underflow: "일부 Gaussian 꼬리값은 부동소수점 범위보다 작아 0으로 표시됩니다. 정확히 0인 선호도라는 뜻은 아닙니다. 해당 점 수",
  tail: "정규분포 꼬리 상한", integrationError: "적분 오차 추정",
  title: "목표값 곡선 비교", preview: "미리보기 전용: 저장하거나 추천에 적용하지 않습니다.",
  response: "목표값 반응", select: "목표값 맞추기 반응 선택", lower: "하한 제어점 desirability", upper: "상한 제어점 desirability",
  meaning: "목표점 desirability는 1입니다. 좌우 제어점 값은 0과 1 사이여야 합니다. Gaussian 꼬리는 제어점 밖에서도 이어지며, 이는 선호도이지 규격 만족확률이 아닙니다. 이 비교는 저장된 추천의 곡선 정책을 변경하지 않습니다.",
  assumed: "명시적으로 가정한 Gaussian 분포 비교", mean: "가정 평균 (반응 단위)", sd: "가정 표준편차 (반응 단위)",
  incumbent: "가정 기준값 (desirability)", xi: "개선 여유 xi (desirability)",
  assumedMeaning: "이 가정값은 GP 적합 예측이 아닙니다. Beta EI는 모멘트 일치 근사이며, 변환 Gaussian의 정확한 EI나 JMP 수치 일치를 의미하지 않습니다.",
  run: "곡선 비교", running: "비교 중...", invalid: "하한 < 목표값 < 상한, 좌우 desirability (0,1), 유한한 가정 입력값을 확인하세요. 표준편차와 xi는 음수가 아니어야 하며 기준값과 xi는 1 이하여야 합니다.",
  failure: "비교를 완료하지 못했습니다. 연구나 실험은 변경되지 않았습니다. 명시적으로 다시 실행하세요.", gaussian: "양측 Gaussian 목표 곡선", linear: "기존 DS 선형 목표 곡선",
  value: "반응값", desirability: "Desirability", moments: "가정 분포 비교", policy: "곡선 정책", expected: "기대 desirability", variance: "Desirability 분산", ei: "모멘트 일치 Beta EI",
  unavailable: "현재 수치 정밀도에서 제공 불가", controls: "제어점 비교", details: "수치 상세", empty: "목표값 맞추기 반응을 선택하면 곡선을 비교할 수 있습니다.",
};
export const curvePreviewMessages = (locale: AppLocale) => locale === "ko" ? ko : en;
