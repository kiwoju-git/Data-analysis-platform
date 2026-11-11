import type { AppLocale } from "./types";

const en = {
  title: "Saved-model LOO diagnostics", run: "Calculate LOO", busy: "Calculating LOO", download: "Download diagnostic JSON",
  meaning: "One observed trial is left out at a time. Kernel, noise, normalization and category parameters remain fixed from the full fit. This is not refitted cross-validation or independent external validation.",
  repeats: "Repeated measurements at the same setting remain separate trials; this does not evaluate generalization to new conditions or groups.",
  routing: "Diagnostic only: this score does not automatically switch the augmentation strategy. Exact JMP numerical parity has not been established.",
  snapshot: "Local diagnostic snapshot, not a managed Report Center artifact. The saved model and observations are unchanged.",
  current: "Selected saved model", historical: "Historical saved model; newer observations are not included",
  error: "LOO diagnostics could not be verified. The saved model is unchanged.",
  response: "Response", raw: "Observed trials", effective: "Fitted rows", scored: "Scored trials", r2: "LOO R²", rmse: "LOO RMSE",
  formula: "R² = 1 − PRESS / centered total sum of squares, across all observed trials. Negative R² is retained.",
  constant: "Unavailable: constant observed response", observed: "Observed", predicted: "LOO predicted", residual: "LOO residual",
  observation: "Observation", points: "Observed versus LOO predicted", identity: "Observed = predicted", rows: "All diagnostic rows", source: "Exact diagnostic source", none: "Unavailable",
};
const ko: typeof en = {
  title: "저장 모형 LOO 진단", run: "LOO 계산", busy: "LOO 계산 중", download: "진단 JSON 다운로드",
  meaning: "관측 실험을 한 건씩 제외합니다. 커널·노이즈·정규화·범주 파라미터는 전체 자료의 적합값으로 고정합니다. 매번 재적합하는 교차검증이나 독립 외부 검증이 아닙니다.",
  repeats: "같은 조건의 반복 측정도 개별 실험으로 평가합니다. 새 조건이나 새 그룹에 대한 일반화 성능을 평가하는 것은 아닙니다.",
  routing: "진단 전용이며 이 점수로 증강 전략을 자동 전환하지 않습니다. JMP와의 정확한 수치 일치는 확인되지 않았습니다.",
  snapshot: "Report Center 관리형 산출물이 아닌 로컬 진단 스냅샷입니다. 저장 모형과 관측값은 변경하지 않습니다.",
  current: "선택한 저장 모형", historical: "과거 저장 모형: 이후 관측값은 포함하지 않음",
  error: "LOO 진단을 검증하지 못했습니다. 저장 모형은 변경되지 않았습니다.",
  response: "반응", raw: "관측 실험 수", effective: "적합 행 수", scored: "평가 실험 수", r2: "LOO R²", rmse: "LOO RMSE",
  formula: "R² = 1 − PRESS / 전체 관측값의 평균 중심 총제곱합입니다. 음수 R²도 그대로 표시합니다.",
  constant: "제공 불가: 관측 반응이 상수", observed: "관측값", predicted: "LOO 예측값", residual: "LOO 잔차",
  observation: "관측", points: "관측값 대 LOO 예측값", identity: "관측값 = 예측값", rows: "전체 진단 행", source: "정확한 진단 출처", none: "제공 불가",
};
export const boLooMessages = (locale: AppLocale): typeof en => locale === "en" ? en : ko;
