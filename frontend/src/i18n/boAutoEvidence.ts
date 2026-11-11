const en = {
  title: "Saved Auto decision evidence", threshold: "Saved threshold", routing: "Routing model ID",
  response: "Response", source: "Saved provenance", policy: "Decision policy",
  attached: "Auto evidence attached · threshold",
  limitation: "Conditional row-LOO keeps full-fit parameters fixed; this is not external validation. A routing model is not a prediction model for model-free selection.",
};
const ko: typeof en = {
  title: "저장된 Auto 판단 근거", threshold: "당시 임계값", routing: "판단용 모형 ID",
  response: "반응", source: "저장 출처", policy: "판단 정책",
  attached: "Auto 근거 연결됨 · 임계값",
  limitation: "전체 적합 파라미터를 고정한 조건부 행 LOO이며 외부 검증이 아닙니다. 판단용 모형은 모형 없는 후보 선택의 예측 모형이 아닙니다.",
};
export const autoEvidenceMessages = (locale: string) => locale === "ko" ? ko : en;
