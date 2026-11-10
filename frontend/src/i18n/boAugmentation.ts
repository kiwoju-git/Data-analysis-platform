import type { AppLocale } from "./types";
import type { AugmentationPolicy } from "../api/types/boAugmentation";

const en = {
  title: "Experimental augmentation", candidates: "Independent candidate table", policy: "Augmentation strategy",
  maxpro: "Space filling: MaxPro (continuous factors)", maximin: "Space filling: mixed maximin",
  refine: "Refine model: EI, desirability SD and response SD", legacyRefine: "Earlier refine policy: desirability SD only",
  confirm: "Confirm optimum: expected desirability and competitive uncertainty",
  policyMeaning: "These are explicit product policies, not a verified numerical reproduction of JMP. Automatic order is stored without refitting or fantasy observations.",
  maxproMeaning: "MaxPro minimizes the incremental projection criterion. Equal projected coordinates can make a candidate unscorable; no arbitrary finite replacement is used.",
  maximinMeaning: "Mixed maximin maximizes the nearest normalized distance. It is a separate criterion, not MaxPro.",
  refineMeaning: "The first row maximizes Beta EI; later rows alternate desirability SD and importance-weighted, normalized response latent SD. These are different uncertainty criteria.",
  confirmMeaning: "The first row maximizes expected desirability. Later rows maximize desirability SD among candidates at or above the observed-location latent incumbent. This is not a probability or guarantee of optimality.",
  noModel: "No fitted model used", modelRequired: "A fitted model from the current observation history is required.",
  duplicate: "Novelty tolerance (normalized)", batch: "Batch size (1–8)", spacing: "Minimum batch distance (normalized)",
  evaluations: "Maximum acquisition evaluations", moments: "Maximum moment evaluations", seconds: "Time budget (seconds)",
  review: "Save automatic selection", saved: "Saved automatic selection", immutable: "The automatic trace is read-only. A separate manual selection has its own policy and result hash.",
  reviewId: "Saved automatic selection ID", openReview: "Open exact saved selection", invalid: "Check the strategy, current source, candidate count, budgets and finite numeric settings.",
  trace: "Automatic selection trace", criterion: "Criterion", score: "Criterion score", log: "Natural log", original: "Original scale", minimize: "Minimize", maximize: "Maximize",
  compared: "Candidates compared", threshold: "Competitive threshold", selectedDistance: "Nearest selected distance", referenceCount: "Reference conditions", collisions: "Projection collisions",
  savedBatch: "Saved augmentation batch", exactBatch: "This exact automatic selection and its original source are shown. No newer batch is substituted.",
  manual: "Start separate manual selection", manualModel: "A current fitted model is required for a separate manual selection.",
  unavailable: "Not evaluated", currentHistory: "Current history required for confirmation", defaults: "Augmentation candidates", displayLimit: "Only this page is displayed; automatic selection evaluates the complete saved candidate revision.",
  constraint: "Constraints", novelty: "Novelty", pending: "Pending experiments prevent another batch. Candidate tables do not create observations.",
  responseSd: "Normalized response latent SD", desirabilitySd: "Desirability SD", betaEi: "Beta EI", expected: "Expected desirability", warnings: "Saved policy warnings",
  reportMeaning: "The report reads this exact saved augmentation and its original observation history; model-free selections have no model predictions.",
  basePosterior: "Predictions use the completed-observation posterior; earlier selected candidates do not reduce its uncertainty.",
  legacySd: "This earlier refine policy does not use combined response-model uncertainty.",
  responseSchedule: "Response uncertainty uses this product's importance-weighted RMS normalization and alternating schedule.",
  projectionWarning: "Some fixed reference conditions share a projected coordinate. Unscorable candidate collisions are recorded separately.",
};
const ko: typeof en = {
  title: "실험 보강", candidates: "독립 후보표", policy: "실험 보강 전략",
  maxpro: "공간 충전: MaxPro (연속 요인)", maximin: "공간 충전: 혼합 maximin",
  refine: "모형 개선: EI · desirability SD · 반응 SD", legacyRefine: "이전 모형 개선 정책: desirability SD만 사용",
  confirm: "최적점 확인: 기대 desirability와 경쟁 후보 불확실성",
  policyMeaning: "명시된 제품 정책이며 JMP와 수치적으로 동일함을 검증한 것은 아닙니다. 재적합이나 가상 관측 없이 자동 선택 순서를 저장합니다.",
  maxproMeaning: "MaxPro는 추가 투영 기준을 최소화합니다. 동일한 투영 좌표로 점수를 계산할 수 없는 후보를 임의의 유한값으로 대체하지 않습니다.",
  maximinMeaning: "혼합 maximin은 정규화된 최소 거리를 최대화합니다. MaxPro와는 별개의 기준입니다.",
  refineMeaning: "첫 행은 Beta EI를 최대화하고, 이후는 desirability SD와 중요도 가중·정규화된 반응 잠재 SD를 번갈아 사용합니다. 서로 다른 불확실성 기준입니다.",
  confirmMeaning: "첫 행은 기대 desirability를 최대화합니다. 이후 관측 위치의 잠재 기준값 이상인 후보 중 desirability SD를 최대화합니다. 최적점일 확률이나 보장이 아닙니다.",
  noModel: "적합 모형을 사용하지 않음", modelRequired: "현재 관측 이력에 적합한 저장 모형이 필요합니다.",
  duplicate: "신규 조건 허용오차 (정규화)", batch: "배치 크기 (1–8)", spacing: "배치 최소 거리 (정규화)",
  evaluations: "최대 획득함수 평가 수", moments: "최대 모멘트 평가 수", seconds: "시간 예산 (초)",
  review: "자동 선택 저장", saved: "저장된 자동 선택", immutable: "자동 선택 이력은 읽기 전용입니다. 별도 수동 선택에는 독립적인 정책과 결과 해시가 적용됩니다.",
  reviewId: "저장된 자동 선택 ID", openReview: "정확한 저장 선택 열기", invalid: "전략, 현재 출처, 후보 수, 예산 및 유한한 숫자 설정을 확인하세요.",
  trace: "자동 선택 이력", criterion: "선택 기준", score: "기준 점수", log: "자연로그", original: "원래 척도", minimize: "최소화", maximize: "최대화",
  compared: "비교한 후보 수", threshold: "경쟁 후보 기준값", selectedDistance: "선택 조건까지 최소 거리", referenceCount: "기준 조건 수", collisions: "투영 좌표 충돌 수",
  savedBatch: "저장된 실험 보강 배치", exactBatch: "정확히 저장된 자동 선택과 원래 출처입니다. 다른 최신 배치로 대체하지 않습니다.",
  manual: "별도 수동 선택 시작", manualModel: "별도 수동 선택에는 현재 적합 모형이 필요합니다.",
  unavailable: "미평가", currentHistory: "확정에는 현재 이력이 필요합니다", defaults: "실험 보강 후보", displayLimit: "현재 페이지만 표시합니다. 자동 선택은 저장된 후보 revision 전체를 평가합니다.",
  constraint: "제약", novelty: "신규 조건", pending: "대기 실험이 있으면 새 배치를 만들 수 없습니다. 후보표는 관측값을 생성하지 않습니다.",
  responseSd: "정규화된 반응 잠재 SD", desirabilitySd: "Desirability SD", betaEi: "Beta EI", expected: "기대 desirability", warnings: "저장된 정책 경고",
  reportMeaning: "정확히 저장된 실험 보강과 원래 관측 이력으로 리포트를 만듭니다. 모형 없는 선택에는 모형 예측값이 없습니다.",
  basePosterior: "완료된 실제 관측의 사후분포를 사용합니다. 앞서 선택한 후보가 불확실성을 줄이지 않습니다.",
  legacySd: "이전 모형 개선 정책은 여러 반응 모형의 통합 불확실성을 사용하지 않습니다.",
  responseSchedule: "반응 불확실성에는 제품의 중요도 가중 RMS 정규화 및 교대 선택 정책을 사용합니다.",
  projectionWarning: "일부 기준 조건이 같은 투영 좌표를 가집니다. 점수를 계산할 수 없는 후보의 충돌은 별도로 기록됩니다.",
};
export const augmentationMessages = (locale: AppLocale) => locale === "ko" ? ko : en;
export function augmentationPolicyLabel(policy: AugmentationPolicy, locale: AppLocale): string {
  const text = augmentationMessages(locale);
  return { greedy_incremental_maxpro_v1: text.maxpro, greedy_mixed_maximin_v1: text.maximin,
    refine_ei_then_desirability_sd_v1: text.legacyRefine, confirm_mean_then_competitive_sd_v1: text.confirm,
    refine_ei_alternating_desirability_response_sd_v2: text.refine }[policy];
}
export function augmentationCriterionLabel(criterion: string, locale: AppLocale): string {
  const text = augmentationMessages(locale);
  const labels: Record<string, string> = { log_incremental_inverse_projection_distance: text.maxpro, minimum_explicit_mixed_distance: text.maximin,
    base_desirability_beta_ei: text.betaEi, base_desirability_standard_deviation: text.desirabilitySd,
    base_expected_desirability: text.expected, base_response_normalized_latent_standard_deviation: text.responseSd };
  return labels[criterion] ?? criterion;
}
export function augmentationWarningLabel(code: string, locale: AppLocale): string {
  const text = augmentationMessages(locale);
  const labels: Record<string, string> = { bayesian_augmentation_not_verified_jmp_parity: text.policyMeaning,
    bayesian_augmentation_base_posterior_not_conditioned_by_selection: text.basePosterior,
    bayesian_refine_multimodel_sd_not_implemented: text.legacySd,
    bayesian_refine_weighted_rms_schedule_product_policy: text.responseSchedule,
    bayesian_maxpro_fixed_reference_projection_collisions: text.projectionWarning };
  return labels[code] ?? code;
}
