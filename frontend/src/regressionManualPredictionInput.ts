import type { LinearModelResult } from "./api";
import { localizedErrorDisplay, type LocalizedErrorDisplay } from "./i18n/errorMessages";
import { translateSystemText } from "./i18n/translate";
import type { AppLocale } from "./i18n/types";

const validationMessages = {
  incomplete_preflight: "입력한 행 중 점검을 통과하지 못한 행이 있어 전체 예측을 차단했습니다.",
  incomplete_prediction: "일부 행만 예측된 응답은 저장 결과로 표시하지 않습니다.",
  header_without_data: "첫 행을 열 이름으로 사용하도록 설정되어 실제 예측 데이터 행이 없습니다. 첫 행에 열 이름 포함을 해제하세요.",
  no_values: "붙여넣은 값이 없습니다.",
  missing_predictor_header: "모든 predictor 열 이름을 찾을 수 없습니다.",
  row_limit: "예측 조건은 최대 10,000행입니다.",
  column_mapping: "붙여넣은 열 수와 predictor mapping을 확인하세요.",
  required: "필수 값",
  numeric: "숫자를 입력하세요",
  integer: "정수를 입력하세요",
  known_level: "학습된 수준을 선택하세요",
} as const;

type ValidationCode = keyof typeof validationMessages;
export type ManualPredictionError =
  | { kind: "validation"; code: ValidationCode }
  | { kind: "request"; cause: unknown };

export interface ManualRow {
  id: string;
  values: Record<string, string>;
}

export function validateRows(
  rows: ManualRow[],
  result: LinearModelResult,
  domains: Map<string, NonNullable<LinearModelResult["training_domain"]>["predictors"][number]>,
): Map<string, ValidationCode> {
  const issues = new Map<string, ValidationCode>();
  rows.forEach((row) => result.predictors.forEach((predictor) => {
    const value = (row.values[predictor.column_id] ?? "").trim();
    const key = `${row.id}:${predictor.column_id}`;
    const domain = domains.get(predictor.column_id);
    if (value === "") issues.set(key, "required");
    else if (domain?.kind !== "categorical") {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) issues.set(key, "numeric");
      else if (domain?.integer_only && !Number.isInteger(numeric)) issues.set(key, "integer");
    } else if (!(domain.levels ?? []).includes(value)) issues.set(key, "known_level");
  }));
  return issues;
}

export function serializeRows(rows: ManualRow[], result: LinearModelResult): string {
  const escape = (value: string) => value.replace(/\t|\r|\n/g, " ");
  return [
    result.predictors.map((predictor) => escape(predictor.column_id)).join("\t"),
    ...rows.map((row) => result.predictors.map((predictor) => escape(row.values[predictor.column_id] ?? "")).join("\t")),
  ].join("\n");
}

export function parseImportedRows(content: string, hasHeader: boolean, result: LinearModelResult): { rows: Array<Record<string, string>>; error: ValidationCode | null } {
  const lines = content.replace(/\r\n?/g, "\n").split("\n").filter((line) => line.trim() !== "");
  if (hasHeader && lines.length === 1) return { rows: [], error: "header_without_data" };
  if (lines.length === 0) return { rows: [], error: "no_values" };
  const separator = lines[0].includes("\t") ? "\t" : ",";
  let cells = lines.map((line) => line.split(separator).map((cell) => cell.trim()));
  let indexes = result.predictors.map((_, index) => index);
  if (hasHeader) {
    const header = cells[0];
    indexes = result.predictors.map((predictor) => header.findIndex((value) => value === predictor.column_id || value === predictor.display_name));
    if (indexes.some((index) => index < 0)) return { rows: [], error: "missing_predictor_header" };
    cells = cells.slice(1);
  } else if (cells.every((row) => row.length === 1) && cells.length === result.predictors.length) {
    cells = [cells.map((row) => row[0])];
  }
  if (cells.length > 10_000) return { rows: [], error: "row_limit" };
  if (cells.some((row) => indexes.some((index) => index >= row.length))) return { rows: [], error: "column_mapping" };
  return {
    rows: cells.map((row) => Object.fromEntries(result.predictors.map((predictor, index) => [predictor.column_id, row[indexes[index]] ?? ""]))),
    error: null,
  };
}

export function manualPredictionValidationMessage(code: ValidationCode, locale: AppLocale): string {
  return translateSystemText(validationMessages[code], locale);
}

export function manualPredictionErrorDisplay(error: ManualPredictionError, locale: AppLocale): LocalizedErrorDisplay {
  return error.kind === "request"
    ? localizedErrorDisplay(error.cause, locale)
    : { code: error.code, correlationId: null, message: manualPredictionValidationMessage(error.code, locale) };
}
