import type { BayesianStudyResponse } from "../../api";
import { getCurrentLocale } from "../../i18n/store";
import { t, translateSystemText } from "../../i18n/translate";
import type { AppLocale } from "../../i18n/types";

export type ObservationPasteError =
  | { code: "empty" | "header_without_data" | "too_many_values" | "column_count" | "non_finite_value" }
  | { code: "trial_not_found" | "duplicate_trial"; params: { trialNumber: string } };

export function parseObservationPaste(
  content: string,
  pendingTrials: BayesianStudyResponse["trials"],
): { values: Record<string, string>; error: ObservationPasteError | null } {
  const lines = content.replace(/\r\n?/g, "\n").split("\n").filter((line) => line.trim() !== "");
  if (lines.length === 0) return { values: {}, error: { code: "empty" } };
  const separator = lines[0].includes("\t") ? "\t" : lines[0].includes(",") ? "," : null;
  let rows = lines.map((line) => separator === null ? [line.trim()] : line.split(separator).map((cell) => cell.trim()));
  if (rows[0].some((cell) => /trial|response|반응|관측/i.test(cell))) rows = rows.slice(1);
  if (rows.length === 0) return { values: {}, error: { code: "header_without_data" } };
  const values: Record<string, string> = {};
  if (rows.every((row) => row.length === 1)) {
    if (rows.length > pendingTrials.length) return { values: {}, error: { code: "too_many_values" } };
    rows.forEach((row, index) => { values[pendingTrials[index].trial_id] = row[0]; });
  } else if (rows.every((row) => row.length >= 2)) {
    const byNumber = new Map(pendingTrials.map((trial) => [String(trial.trial_number), trial]));
    for (const row of rows) {
      const trial = byNumber.get(row[0]);
      if (trial === undefined) return { values: {}, error: { code: "trial_not_found", params: { trialNumber: row[0] } } };
      if (trial.trial_id in values) return { values: {}, error: { code: "duplicate_trial", params: { trialNumber: row[0] } } };
      values[trial.trial_id] = row[1];
    }
  } else return { values: {}, error: { code: "column_count" } };
  if (Object.values(values).some((value) => value === "" || !Number.isFinite(Number(value)))) return { values: {}, error: { code: "non_finite_value" } };
  return { values, error: null };
}

export function observationPasteErrorMessage(error: ObservationPasteError, locale: AppLocale = getCurrentLocale()): string {
  if (error.code === "trial_not_found") {
    return t("bayesian.paste.trialNotFound", error.params, locale);
  }
  if (error.code === "duplicate_trial") {
    return t("bayesian.paste.duplicateTrial", error.params, locale);
  }
  const messages = {
    empty: "붙여넣은 관측값이 없습니다.",
    header_without_data: "header 아래에 관측 데이터가 없습니다.",
    too_many_values: "붙여넣은 값 수가 pending trial 수보다 많습니다.",
    column_count: "모든 행을 값 한 열 또는 trial/response 두 열로 맞추세요.",
    non_finite_value: "유한한 숫자가 아닌 관측값이 있습니다.",
  };
  return translateSystemText(messages[error.code], locale);
}
