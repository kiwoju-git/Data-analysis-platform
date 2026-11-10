import type { AppLocale } from "./types";
import type { MixedCorrelationPolicy } from "../api/types/boMixed";
const en = {
  studyMode: "Study factor type", parameterValue: "Fitted parameter value",
  numericMode: "Numeric factors", mixedMode: "Nominal / ordinal factors", title: "Mixed-factor Bayesian study", create: "Create mixed-factor study", name: "Study name",
  factors: "Factors", factor: "Factor", factorId: "Factor ID", factorName: "Factor name", kind: "Factor kind", unit: "Unit", continuous: "Continuous", discrete: "Discrete numeric", nominal: "Nominal", ordinal: "Ordinal",
  low: "Lower bound", high: "Upper bound", step: "Executable step", decimals: "Display decimals", levels: "Declared levels", addLevel: "Add level", removeLevel: "Remove level", up: "Move level earlier", down: "Move level later",
  correlation: "Category correlation policy", equal: "Equal positive correlation", unequal: "Unequal: flexible PSD correlations", latent: "Ordinal: learned monotone latent gaps",
  categoryMeaning: "Category labels retain their complete identity. Integer codes are equality/lookup indices, not numeric distances.",
  ordinalMeaning: "The listed order is the declared ordinal order. Equal/unequal policies do not impose rank spacing; the latent policy learns positive gaps with fixed scale.",
  parity: "These explicit product parameterizations are not verified numerical reproductions of JMP Equal, Unequal or Latent.",
  parameterLimits: "Up to 10 factors, 32 levels per category, 8 levels for unequal correlation, and 64 total category parameters.",
  addFactor: "Add factor", removeFactor: "Remove factor", objective: "Objective name", seed: "Initial design seed", modelSeed: "Model fit seed", size: "Initial conditions (2–64)",
  initialPolicy: "Seeded feasible uniform mixed design; not a Latin hypercube or a balanced categorical design.", constraints: "Actual-unit numeric constraints", constraintName: "Constraint name", addConstraint: "Add constraint", removeConstraint: "Remove constraint", coefficient: "Coefficient", relation: "Relation", bound: "Bound",
  constraintMeaning: "Constraint coefficients apply only to numeric factors. Categorical levels cannot be assigned arbitrary numeric coefficients.",
  invalid: "Check complete numeric values, bounds, exact level identities, declared order, correlation limits, response goals and constraints.", cancel: "Cancel", working: "Working...", error: "The operation did not complete. The saved source was not replaced.",
  uncertainCreate: "The server may already have created the study. Refresh the study catalog before starting another creation; this POST is not automatically retried.", refresh: "Refresh source", initial: "Initial design", uncovered: "Declared levels not present in the initial design", prior: "Predictions for unobserved levels depend on the declared correlation prior; initial coverage is not guaranteed.",
  observations: "Actual response observations", history: "Observation history", state: "State", trial: "Trial", pending: "Pending", completed: "Completed", abandoned: "Abandoned", response: "Response",
  review: "Review complete observations", confirmObservations: "Save actual observations", retry: "Retry identical observation request", uncertain: "The server may already have committed this operation. Explicit retry uses the same ID and payload.",
  partial: "Each entered trial requires every response. Blank trials remain pending; predictions are never inserted as observations.",
  reviewed: "Observation confirmation", stale: "The study or history changed. Review the current source before saving.",
  replicate: "Create explicit replicates", replicateCount: "Replicate count (1–8)", replicateIntent: "I intend to repeat this completed experiment", replicateMeaning: "New pending trials keep the same executed settings. Each repeat requires its own actual measured response vector.",
  abandon: "Abandon pending trial", close: "Close study", closeTarget: "Closing status", closeReason: "Closing reason", note: "Closing note", confirmClose: "Confirm close", confirmAbandon: "Confirm abandon", closePending: "All pending trials must be completed or explicitly abandoned before closing.",
  source: "Source details", definition: "Definition hash", coordinate: "Coordinate encoding", ordinalDistance: "Use declared ordinal rank for distance (explicit equal-gap assumption)",
  model: "Mixed-factor saved model", fit: "Fit and save mixed model", hold: "Actual factor settings / fixed holds", numericCurve: "Conditional numeric curve", levelProfile: "Declared category levels", profile: "Mixed-factor profiler",
  planning: "Mixed-factor candidates and planning", savedBatch: "Saved mixed-factor batch", fitSettings: "Mixed model fit settings", kernel: "Numeric kernel", noise: "Measurement noise", estimate: "Estimate variance", fixed: "Fixed measured SD", nearNoiseless: "Near noiseless", fixedSd: "Measured SD (response units)", initialNoise: "Initial scaled variance", lowerNoise: "Lower scaled variance", upperNoise: "Upper scaled variance", aggregation: "Exact-repeat training view", retainRaw: "Retain raw observations", exactReplicates: "Exact sufficient-statistic compression", xi: "Desirability exploration xi", seconds: "Time budget (seconds)", evaluations: "Model evaluations", starts: "Typed deterministic starts", restarts: "Random restarts", moments: "Moment evaluations", samples: "Joint posterior samples", tolerance: "Novelty tolerance", manual: "Manual ordered selection", automatic: "Automatic augmentation", selectionKind: "Selection mode", profileDraft: "Changing holds requires explicit evaluation. Display switches reuse the applied predictions.", fitApplied: "Predictions below use the opened saved model, not uncommitted fit settings.", coverage: "Training category coverage", parameters: "Typed kernel parameters", sigmaNoise: "Measurement noise SD", fitStatus: "Fit termination", minimumDistance: "Minimum batch distance", previewRows: "Validated rows", automaticMeaning: "Automatic order and its trace are immutable. Switch to manual selection to create a separate reviewed selection.", rawCode: "Stored code",
  objectiveSatisfied: "Objective satisfied", budgetReached: "Budget reached", confirmationComplete: "Confirmation complete", unsafe: "Unsafe or infeasible", resources: "Resources unavailable", cancelled: "Study cancelled", closingIntent: "Pending trials are being abandoned to close the study", totalBudget: "Total trial budget", previous: "Previous page", next: "Next page", confirm: "Confirm reviewed operation",
};
const ko: typeof en = {
  studyMode: "연구 요인 유형", parameterValue: "적합 파라미터 값",
  numericMode: "숫자 요인", mixedMode: "명목형 · 순서형 요인", title: "혼합 요인 Bayesian 연구", create: "혼합 요인 연구 생성", name: "연구 이름",
  factors: "요인", factor: "요인", factorId: "요인 ID", factorName: "요인 이름", kind: "요인 종류", unit: "단위", continuous: "연속형", discrete: "이산 숫자형", nominal: "명목형", ordinal: "순서형",
  low: "하한", high: "상한", step: "실행 간격", decimals: "표시 소수 자릿수", levels: "선언된 수준", addLevel: "수준 추가", removeLevel: "수준 삭제", up: "수준 앞으로 이동", down: "수준 뒤로 이동",
  correlation: "범주 상관 정책", equal: "동일한 양의 상관", unequal: "비동일: 유연한 PSD 상관", latent: "순서형: 단조 잠재 간격 학습",
  categoryMeaning: "범주 이름의 전체 식별자를 보존합니다. 정수 코드는 동일성 확인용 인덱스이며 숫자 거리가 아닙니다.",
  ordinalMeaning: "목록 순서가 선언된 순서형 수준 순서입니다. 동일·비동일 정책은 순위 간격을 강제하지 않으며, 잠재 정책은 고정 척도에서 양의 간격을 학습합니다.",
  parity: "명시된 제품 파라미터화이며 JMP의 Equal · Unequal · Latent와 수치적으로 동일함을 검증한 것은 아닙니다.",
  parameterLimits: "최대 10요인, 범주당 32수준, 비동일 상관은 8수준, 전체 범주 파라미터는 64개입니다.",
  addFactor: "요인 추가", removeFactor: "요인 삭제", objective: "목적 이름", seed: "초기 설계 시드", modelSeed: "모형 적합 시드", size: "초기 조건 수 (2–64)",
  initialPolicy: "시드 기반 실행 가능 균등 혼합 설계입니다. LHS 또는 범주 균형 설계가 아닙니다.", constraints: "실제 단위 숫자 요인 제약", constraintName: "제약 이름", addConstraint: "제약 추가", removeConstraint: "제약 삭제", coefficient: "계수", relation: "관계", bound: "우변",
  constraintMeaning: "제약 계수는 숫자 요인에만 적용합니다. 범주 수준에 임의 숫자 계수를 부여하지 않습니다.",
  invalid: "전체 숫자, 범위, 정확한 수준 식별자, 선언 순서, 상관 제한, 반응 목표 및 제약을 확인하세요.", cancel: "취소", working: "처리 중...", error: "작업을 완료하지 못했습니다. 저장된 출처를 대체하지 않았습니다.",
  uncertainCreate: "서버에서 이미 연구를 생성했을 수 있습니다. 새로 생성하기 전에 연구 목록을 확인하세요. 이 POST는 자동 재시도하지 않습니다.", refresh: "출처 새로고침", initial: "초기 설계", uncovered: "초기 설계에 포함되지 않은 선언 수준", prior: "관측하지 않은 수준의 예측은 선언된 상관 사전 가정에 의존하며, 초기 수준 포함을 보장하지 않습니다.",
  observations: "실제 반응 관측값", history: "관측 이력", state: "상태", trial: "실험", pending: "대기", completed: "완료", abandoned: "중단", response: "반응",
  review: "전체 반응 관측 검토", confirmObservations: "실제 관측값 저장", retry: "동일 관측 요청 재시도", uncertain: "서버에서 이미 저장했을 수 있습니다. 명시적 재시도는 동일 ID와 입력을 사용합니다.",
  partial: "입력한 실험에는 모든 반응이 필요합니다. 빈 실험은 대기 상태이며, 예측값을 관측값으로 넣지 않습니다.",
  reviewed: "관측값 저장 확인", stale: "연구 또는 이력이 변경되었습니다. 현재 출처를 검토한 뒤 저장하세요.",
  replicate: "명시적 반복 실험 생성", replicateCount: "반복 수 (1–8)", replicateIntent: "완료된 이 실험을 반복하려는 의도입니다", replicateMeaning: "동일한 실행 조건으로 새 대기 실험을 만듭니다. 반복마다 실제로 측정한 전체 반응값을 입력해야 합니다.",
  abandon: "대기 실험 중단", close: "연구 종료", closeTarget: "종료 상태", closeReason: "종료 사유", note: "종료 메모", confirmClose: "종료 확정", confirmAbandon: "중단 확정", closePending: "종료 전에 모든 대기 실험을 완료하거나 명시적으로 중단해야 합니다.",
  source: "출처 상세", definition: "정의 해시", coordinate: "좌표 인코딩", ordinalDistance: "거리 계산에 선언 순위를 사용 (명시적 등간격 가정)",
  model: "혼합 요인 저장 모형", fit: "혼합 모형 적합 및 저장", hold: "실제 요인 설정 / 고정값", numericCurve: "조건부 숫자 곡선", levelProfile: "선언된 범주 수준", profile: "혼합 요인 Profiler",
  planning: "혼합 요인 후보 및 계획", savedBatch: "저장된 혼합 요인 배치", fitSettings: "혼합 모형 적합 설정", kernel: "숫자 요인 커널", noise: "측정 노이즈", estimate: "분산 추정", fixed: "고정 측정 SD", nearNoiseless: "거의 무잡음", fixedSd: "측정 SD (반응 단위)", initialNoise: "초기 표준화 분산", lowerNoise: "표준화 분산 하한", upperNoise: "표준화 분산 상한", aggregation: "정확한 반복 학습 뷰", retainRaw: "원래 관측 유지", exactReplicates: "정확한 충분통계 압축", xi: "Desirability 탐색 xi", seconds: "시간 예산 (초)", evaluations: "모형 평가 횟수", starts: "요인 종류별 결정적 시작점", restarts: "무작위 재시작", moments: "모멘트 평가 횟수", samples: "결합 사후표본 수", tolerance: "신규 조건 허용 거리", manual: "수동 순서 선택", automatic: "자동 추가 실험 선택", selectionKind: "선택 방식", profileDraft: "고정값을 변경하면 명시적으로 다시 예측해야 합니다. 표시 전환은 적용된 예측값을 재사용합니다.", fitApplied: "아래 예측은 열린 저장 모형을 사용하며, 아직 적용하지 않은 적합 설정을 사용하지 않습니다.", coverage: "학습 범주 수준 포함 수", parameters: "종류별 커널 파라미터", sigmaNoise: "측정 노이즈 SD", fitStatus: "적합 종료 상태", minimumDistance: "배치 최소 거리", previewRows: "검증된 행", automaticMeaning: "자동 선택 순서와 이력은 변경하지 않습니다. 수동 방식으로 전환하면 별도의 검토 선택을 생성합니다.", rawCode: "저장 코드",
  objectiveSatisfied: "목표 달성", budgetReached: "예산 도달", confirmationComplete: "확인 완료", unsafe: "안전 또는 실행 불가", resources: "자원 부족", cancelled: "연구 취소", closingIntent: "연구를 종료하기 위해 대기 실험을 중단합니다", totalBudget: "전체 실험 예산", previous: "이전 페이지", next: "다음 페이지", confirm: "검토한 작업 확정",
};
export const mixedMessages = (locale: AppLocale) => locale === "ko" ? ko : en;
export function mixedCorrelationLabel(policy: MixedCorrelationPolicy, locale: AppLocale) {
  const text = mixedMessages(locale);
  return { equal_positive_correlation_v1: text.equal, unequal_hyperspherical_correlation_v1: text.unequal, ordinal_monotone_latent_rbf_v1: text.latent }[policy];
}
