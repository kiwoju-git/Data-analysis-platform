import type { AnalysisFilterSnapshot, DatasetColumnResponse, DatasetVersionResponse } from "../../api";
import type { DatasetImportRequest } from "../../api/types/boDatasetImport";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { buildVectorObjective, type ResponseGoalDraft } from "./bayesianVectorDraft";
import { parseMixedConstraintDefinitions, parseMixedFactorDefinitions, type MixedConstraintDraft, type MixedFactorDraft } from "./boMixedDraft";

export interface DatasetImportFactorDraft extends MixedFactorDraft { columnId: string }
export interface DatasetImportDraft {
  name: string; factors: DatasetImportFactorDraft[]; responseMode: "scalar" | "vector";
  scalarColumnId: string; goal: "maximize" | "minimize" | "match_target"; target: string; tolerance: string;
  responses: ResponseGoalDraft[]; responseColumns: Record<string, string>;
  constraints: MixedConstraintDraft[]; missingPolicy: "reject" | "complete_case";
  displayNames?: Record<string, string>;
}
type ImportVersion = Pick<DatasetVersionResponse, "version_id" | "schema_hash"> & {
  columns: Pick<DatasetColumnResponse, "column_id" | "display_name" | "unit">[];
};
export function buildDatasetImportRequest(version: ImportVersion, filter: AnalysisFilterSnapshot, draft: DatasetImportDraft): DatasetImportRequest | string {
  const invalid = "bayesian_import_mapping_invalid";
  if (!draft.name.trim() || draft.name.trim().length > 120) return invalid;
  const column = (id: string) => version.columns.find(item => item.column_id === id);
  const name = (id: string) => draft.displayNames?.[id] ?? column(id)!.display_name;
  if (draft.factors.some(row => !column(row.columnId))) return invalid;
  const factors = parseMixedFactorDefinitions(draft.factors.map(row => ({ ...row,
    name: name(row.columnId), unit: column(row.columnId)!.unit ?? "" })));
  if (typeof factors === "string") return factors;
  const constraints = parseMixedConstraintDefinitions(draft.constraints, factors);
  if (typeof constraints === "string") return constraints;
  let objective: DatasetImportRequest["objective"];
  let responses: DatasetImportRequest["response_mappings"];
  if (draft.responseMode === "scalar") {
    const selected = column(draft.scalarColumnId);
    if (!selected) return invalid;
    if (factors.some(row => row.domain_kind === "nominal" || row.domain_kind === "ordinal")) return "bayesian_mixed_requires_response_vector";
    const target = draft.goal === "match_target" ? parseDoeResponseNumber(draft.target) : null;
    const tolerance = draft.goal === "match_target" && draft.tolerance.trim() ? parseDoeResponseNumber(draft.tolerance) : null;
    if (draft.goal === "match_target" && (target === null || (draft.tolerance.trim() && (tolerance === null || tolerance <= 0)))) return "bayesian_study_input_invalid";
    if (!name(selected.column_id).trim() || name(selected.column_id).trim().length > 80) return "bayesian_import_display_name_invalid";
    objective = { name: name(selected.column_id).trim(), unit: selected.unit, goal_type: draft.goal,
      target_value: target, target_tolerance: tolerance, observation_policy: "manual_single_observation" };
    responses = [{ column_id: selected.column_id, response_id: null }];
  } else {
    if (draft.responses.some(row => !column(draft.responseColumns[row.responseId]))) return invalid;
    const parsed = buildVectorObjective("Desirability", draft.responses.map(row => {
      const selected = column(draft.responseColumns[row.responseId])!;
      return { ...row, name: name(selected.column_id), unit: selected.unit ?? "" };
    }));
    if (typeof parsed === "string") return parsed;
    objective = parsed;
    responses = draft.responses.map(row => ({ column_id: draft.responseColumns[row.responseId], response_id: row.responseId }));
  }
  const ids = [...draft.factors.map(row => row.columnId), ...responses.map(row => row.column_id)];
  if (new Set(ids).size !== ids.length) return invalid;
  return { schema_version: 1, name: draft.name.trim(), dataset_version_id: version.version_id,
    expected_schema_hash: version.schema_hash, factor_mappings: factors.map((factor, i) => ({ column_id: draft.factors[i].columnId, factor })),
    response_mappings: responses, objective, constraints, filter_snapshot: filter, missing_policy: draft.missingPolicy };
}
