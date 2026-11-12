import type { AppLocale } from "./types";

const en = {
  title: "Imported measured observations", dataset: "Source dataset", version: "Source dataset version",
  total: "Source rows", filtered: "Filter exclusions", missing: "Missing exclusions", used: "Imported observations",
  unique: "Unique conditions", repeats: "Repeated observations", conflicts: "Conditions with differing responses",
  missingPolicy: "Missing-data policy", reject: "Reject missing values", completeCase: "Explicit complete cases",
  provenance: "Import provenance", x: "Factor columns", y: "Response columns", rows: "Source row indices (zero-based)",
  invalid: "The stored dataset import receipt is invalid. Source details are unavailable.",
  successorUnavailable: "Imported observations have no generation seed. Start a new study to choose a new initial design or import measured data again.",
  study: "Bayesian study", dependency: "This dataset is the source of imported Bayesian observations. Delete the dependent study before deleting this dataset.",
};
const ko: typeof en = {
  title: "데이터셋에서 가져온 실측 관측", dataset: "원본 데이터셋", version: "원본 데이터셋 버전",
  total: "원본 행", filtered: "필터 제외", missing: "결측 제외", used: "가져온 관측",
  unique: "고유 조건", repeats: "반복 관측", conflicts: "반응값이 다른 반복 조건",
  missingPolicy: "결측 처리 정책", reject: "결측값 거부", completeCase: "명시적 완전 사례",
  provenance: "가져오기 출처 정보", x: "요인 열", y: "반응 열", rows: "원본 행 인덱스 (0부터 시작)",
  invalid: "저장된 데이터셋 가져오기 기록이 유효하지 않아 출처 정보를 표시할 수 없습니다.",
  successorUnavailable: "가져온 관측에는 생성 seed가 없습니다. 새 Study에서 초기 설계를 선택하거나 실측 데이터를 다시 가져오세요.",
  study: "Bayesian Study", dependency: "이 데이터셋은 Bayesian 실측 관측의 출처입니다. 연결된 Study를 먼저 삭제한 뒤 데이터셋을 삭제하세요.",
};
export const datasetSourceMessages = (locale: AppLocale) => locale === "en" ? en : ko;
