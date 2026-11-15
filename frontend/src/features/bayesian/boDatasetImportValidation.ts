import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { isRsmOnLattice } from "../../doe/rsmRegion";
import type { DatasetImportDraft, ImportVersion } from "./boDatasetImportDraft";

export type ImportFieldIssueCode = "required" | "studyName" | "finiteNumber" | "positiveNumber" |
  "boundOrder" | "finiteSpan" | "selectColumn" | "duplicateColumn" | "lowerTargetOrder" |
  "targetUpperOrder" | "stepLattice" | "categoryLevels" | "vectorRequired" | "displayName" | "mixtureBoundOrder";
export interface ImportFieldIssue { field: string; code: ImportFieldIssueCode }

/** Presentation-only checks. The request builder and server remain authoritative. */
export function datasetImportFieldIssues(version: ImportVersion, draft: DatasetImportDraft): ImportFieldIssue[] {
  const issues = new Map<string, ImportFieldIssueCode>();
  const add = (field: string, code: ImportFieldIssueCode) => { if (!issues.has(field)) issues.set(field, code); };
  const number = (field: string, raw: string, positive = false) => {
    const value = parseDoeResponseNumber(raw);
    if (value === null) add(field, raw.trim() ? "finiteNumber" : "required");
    else if (positive && value <= 0) add(field, "positiveNumber");
    return value;
  };
  const ordered = (leftField: string, rightField: string, left: number | null, right: number | null, code: ImportFieldIssueCode) => {
    if (left === null || right === null) return;
    if (left >= right) { add(leftField, code); add(rightField, code); }
    else if (!Number.isFinite(right - left)) { add(leftField, "finiteSpan"); add(rightField, "finiteSpan"); }
  };
  if (!draft.name.trim()) add("name", "required");
  else if (draft.name.trim().length > 120) add("name", "studyName");
  const mappings = [
    ...draft.factors.map(row => ({ field: `factor.${row.key}.column`, id: row.columnId })),
    ...(draft.responseMode === "scalar" ? [{ field: "scalarColumn", id: draft.scalarColumnId }] :
      draft.responses.map(row => ({ field: `response.${row.key}.column`, id: draft.responseColumns[row.responseId] ?? "" }))),
  ];
  for (const { field, id } of mappings) {
    const column = version.columns.find(item => item.column_id === id);
    if (!column) add(field, "selectColumn");
    else {
      if (mappings.filter(item => item.id === id).length > 1) add(field, "duplicateColumn");
      const name = draft.displayNames?.[id] ?? column.display_name;
      if (!name.trim() || name.trim().length > 80) add(`display.${id}`, "displayName");
    }
  }
  for (const row of draft.factors) {
    const key = `factor.${row.key}`;
    if (row.kind === "nominal" || row.kind === "ordinal") {
      if (row.levels.length < 2 || row.levels.length > 32 || row.levels.some(value => !value.trim() || value.length > 1024 || value.includes("\0")) || new Set(row.levels).size !== row.levels.length) add(`${key}.levels`, "categoryLevels");
    } else {
      const low = number(`${key}.low`, row.low), high = number(`${key}.high`, row.high);
      if (draft.mixture?.componentKeys.includes(row.key)) {
        if (low !== null && high !== null && (low < 0 || high < low)) {
          add(`${key}.low`, "mixtureBoundOrder"); add(`${key}.high`, "mixtureBoundOrder");
        }
      } else ordered(`${key}.low`, `${key}.high`, low, high, "boundOrder");
      if (row.kind === "discrete_numeric") {
        const step = number(`${key}.step`, row.step, true);
        if (step !== null && step > 0 && low !== null && high !== null && high > low && !isRsmOnLattice(high, low, step)) add(`${key}.step`, "stepLattice");
      }
    }
  }
  if (draft.responseMode === "scalar") {
    if (draft.mixture || draft.factors.some(row => row.kind === "nominal" || row.kind === "ordinal")) add("responseMode", "vectorRequired");
    if (draft.goal === "match_target") {
      number("target", draft.target);
      if (draft.tolerance.trim()) number("tolerance", draft.tolerance, true);
    }
  } else {
    for (const row of draft.responses) {
      const key = `response.${row.key}`;
      const lower = row.goal === "minimize" ? null : number(`${key}.lower`, row.lower);
      const target = number(`${key}.target`, row.target);
      const upper = row.goal === "maximize" ? null : number(`${key}.upper`, row.upper);
      ordered(`${key}.lower`, `${key}.target`, lower, target, "lowerTargetOrder");
      ordered(`${key}.target`, `${key}.upper`, target, upper, "targetUpperOrder");
      number(`${key}.importance`, row.importance, true);
    }
  }
  return [...issues].map(([field, code]) => ({ field, code }));
}
