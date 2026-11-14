import type { AppLocale } from "./types";

const en = {
  required: "This saved recommendation uses an earlier EI numerical policy. Review a new recommendation from the same saved model, candidates and options before confirmation. The original remains unchanged.",
  renew: "Renew saved recommendation", renewed: "Renewed review; not yet confirmed",
  original: "Open original recommendation", lineage: "Renewal source",
  deletionCount: "Recommendation renewal links",
  explanation: "Values and selected rows can differ under the current numerical policy. Check the new results before confirming.",
};
const ko: typeof en = {
  required: "이 저장 추천은 이전 EI 수치 정책을 사용합니다. 동일한 저장 모델·후보표·옵션으로 새 추천을 검토한 뒤 확정하세요. 원본은 변경하지 않습니다.",
  renew: "저장 추천 재검토", renewed: "재검토 완료 · 아직 확정하지 않음",
  original: "원본 추천 열기", lineage: "재검토 출처",
  deletionCount: "추천 재검토 연결",
  explanation: "현재 수치 정책에서 값과 선택 행이 달라질 수 있습니다. 새 결과를 확인한 뒤 확정하세요.",
};
export const renewalMessages = (locale: AppLocale) => locale === "ko" ? ko : en;
