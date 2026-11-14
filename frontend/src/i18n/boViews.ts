import type { AppLocale } from "./types";

const en = {
  save: "Save displayed view", saved: "Saved view", retry: "Retry save", error: "The view request failed. No automatic retry was made.",
  stored: "Saved diagnostic views", refresh: "Refresh saved views", choose: "Choose a saved view", open: "Open view", busy: "Processing view...",
  immutable: "This is a stored view of the identified model and observation history, not a new fit or candidate eligibility decision.",
  profiler: "All-factor Profiler", loo: "Conditional row-LOO", empty: "No saved views", source: "Applied source and settings",
  report: "Create HTML report", download: "Download HTML", reportError: "The report could not be created or downloaded.",
  expired: "Save uses the displayed server receipt. An expired receipt requires explicit regeneration; it is never recalculated during save.",
  sample: "Displayed executable levels / total levels", constraints: "Fixed constraints", passed: "Satisfied", failed: "Violated",
  warnings: "Stored model warnings", levels: "Displayed factor levels", warningMeaning: "These warnings belong to the exact fitted source, not a new fit during graph generation.",
  coVary: "Other mixture components co-vary to preserve the total; this is not an independent component effect.",
  excess: "Preserve ratios of excess above lower bounds", deficit: "Preserve ratios of deficits below upper bounds", process: "Hold composition fixed while changing the process factor",
  fixedComponent: "This component is fixed; no varying profile is available.", zeroMass: "No balancing mass is available at these applied holds.", noInterval: "No varying feasible interval is available at these applied holds.",
  pathUnavailable: "This conditional path is unavailable. The stored reason code is retained below.", actualCoordinates: "Applied actual coordinates",
};
const ko: typeof en = {
  save: "표시한 그래프 저장", saved: "저장된 그래프", retry: "저장 재시도", error: "그래프 요청을 처리하지 못했습니다. 자동 재시도하지 않았습니다.",
  stored: "저장된 진단 그래프", refresh: "저장 목록 새로고침", choose: "저장된 그래프 선택", open: "그래프 열기", busy: "그래프 처리 중...",
  immutable: "표시된 모델과 관측 이력의 저장 그래프입니다. 새 모형 적합이나 현재 후보의 추천 가능 여부를 뜻하지 않습니다.",
  profiler: "전체 요인 Profiler", loo: "조건부 행별 LOO", empty: "저장된 그래프 없음", source: "적용된 출처와 설정",
  report: "HTML 리포트 생성", download: "HTML 다운로드", reportError: "리포트를 생성하거나 다운로드하지 못했습니다.",
  expired: "화면에 표시된 서버 계산 결과를 저장합니다. 유효기간이 지나면 직접 다시 생성해야 하며 저장 중 재계산하지 않습니다.",
  sample: "표시 실행 수준 / 전체 수준", constraints: "고정 제약조건", passed: "충족", failed: "위반",
  warnings: "저장 모델 경고", levels: "표시된 요인 수준", warningMeaning: "해당 적합 모델에 저장된 경고입니다. 그래프 생성 중 새로 적합한 결과가 아닙니다.",
  coVary: "총량을 유지하도록 다른 혼합물 성분도 함께 변합니다. 독립 성분 효과가 아닙니다.",
  excess: "하한 초과량의 비율 유지", deficit: "상한 부족량의 비율 유지", process: "조성을 고정하고 공정 요인 변경",
  fixedComponent: "고정 성분이므로 변화 프로파일이 없습니다.", zeroMass: "적용한 기준 조건에서 균형을 맞출 나머지 성분량이 없습니다.", noInterval: "적용한 기준 조건에서 변화 가능한 구간이 없습니다.",
  pathUnavailable: "이 조건부 경로를 표시할 수 없습니다. 아래에 저장된 이유 코드를 표시합니다.", actualCoordinates: "적용된 실제 좌표",
};
export function boViewMessages(locale: AppLocale) { return locale === "en" ? en : ko; }
