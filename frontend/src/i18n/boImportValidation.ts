import type { AppLocale } from "./types";
import type { ImportFieldIssueCode } from "../features/bayesian/boDatasetImportValidation";

const en: Record<ImportFieldIssueCode, string> = {
  required: "Enter a value.",
  studyName: "Use a Study name of 1 to 120 characters.",
  finiteNumber: "Enter a complete, finite number, for example 0, -1.25 or 1e-3.",
  positiveNumber: "Enter a number greater than zero.",
  boundOrder: "The lower bound must be less than the upper bound.",
  mixtureBoundOrder: "Mixture component bounds must satisfy 0 <= lower <= upper. A fixed component may use equal bounds.",
  finiteSpan: "The distance between these values is too large. Use a narrower range.",
  selectColumn: "Select a column from the current dataset.",
  duplicateColumn: "This column is selected more than once. Use different columns for X and Y.",
  lowerTargetOrder: "The lower threshold must be less than the target.",
  targetUpperOrder: "The target must be less than the upper threshold.",
  stepLattice: "The upper bound must lie on the step grid starting at the lower bound.",
  categoryLevels: "Enter 2 to 32 distinct, nonempty levels, one per line (up to 1,024 characters each).",
  vectorRequired: "Select Desirability response goals for categorical or mixture factors.",
  displayName: "Enter a BO display name of 1 to 80 characters. The dataset name is not changed.",
};
const ko: typeof en = {
  required: "값을 입력하세요.",
  studyName: "Study 이름은 1~120자로 입력하세요.",
  finiteNumber: "0, -1.25, 1e-3처럼 완전한 유한 숫자를 입력하세요.",
  positiveNumber: "0보다 큰 숫자를 입력하세요.",
  boundOrder: "하한은 상한보다 작아야 합니다.",
  mixtureBoundOrder: "혼합물 성분은 0 ≤ 하한 ≤ 상한이어야 합니다. 고정 성분은 같은 하한·상한을 사용할 수 있습니다.",
  finiteSpan: "두 값의 간격이 너무 큽니다. 더 좁은 범위를 입력하세요.",
  selectColumn: "현재 데이터셋에서 열을 선택하세요.",
  duplicateColumn: "같은 열을 중복 선택했습니다. X와 Y에는 서로 다른 열을 선택하세요.",
  lowerTargetOrder: "하한은 목표값보다 작아야 합니다.",
  targetUpperOrder: "목표값은 상한보다 작아야 합니다.",
  stepLattice: "상한이 하한에서 시작하는 간격의 격자에 맞도록 범위 또는 간격을 수정하세요.",
  categoryLevels: "서로 다른 수준 2~32개를 한 줄에 하나씩 입력하세요. 빈 줄은 허용하지 않으며 수준당 최대 1,024자입니다.",
  vectorRequired: "범주형 또는 혼합물 요인은 Desirability 반응 목표를 선택하세요.",
  displayName: "BO 표시 이름을 1~80자로 입력하세요. 원본 데이터셋 이름은 바뀌지 않습니다.",
};
export const importFieldMessage = (locale: AppLocale, code: ImportFieldIssueCode) => (locale === "en" ? en : ko)[code];
export const importFieldSummary = (locale: AppLocale, count: number) => locale === "en"
  ? `Check ${count} highlighted fields. Your inputs have been preserved.`
  : `표시된 입력란 ${count}곳을 확인하세요. 입력한 값은 그대로 유지됩니다.`;
