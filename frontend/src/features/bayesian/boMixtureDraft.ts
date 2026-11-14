import type { MixtureComponent, MixtureDatasetImportRequest, MixtureGroup, MixtureModel, MixturePage, MixtureRow, MixtureSelection, MixtureStudy, MixtureStudyRequest } from "../../api/boMixture";
import type { AnalysisFilterSnapshot, DatasetVersionResponse } from "../../api";
import type { DatasetImportDraft } from "./boDatasetImportDraft";
import type { BayesianDesirabilityObjective } from "../../api/types/bayesian";
import type { MixedActualPoint, MixedFactorRequest, MixedFitOptions, MixedSourceRequest } from "../../api/types/boMixed";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { isRsmOnLattice } from "../../doe/rsmRegion";
import { parsePastedTablePreview } from "../../pastedTablePreview";
import { parseMixedConstraintDefinitions, parseMixedFactorDefinitions, type MixedConstraintDraft, type MixedFactorDraft } from "./boMixedDraft";
import { planningHash, planningId, planningInteger } from "./boPlanningDraft";
import { defaultDesirabilitySearch } from "./bayesianDesirabilityDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";
import { buildVectorObjective } from "./bayesianVectorDraft";

export interface MixtureComponentDraft { key: number; factorId: string; name: string; low: string; high: string }
export const newMixtureComponent = (key: number): MixtureComponentDraft => ({ key, factorId: `component_${key}`, name: `Component ${key}`, low: "0", high: "1" });
function sum(values: number[]): number {
  let result = 0, correction = 0;
  for (const value of values) { const next = result + value; correction += Math.abs(result) >= Math.abs(value) ? result - next + value : value - next + result; result = next; }
  return result + correction;
}
// Match the server's documented 16-ULP closure comparison, never rescale input.
function tolerance(a: number, b: number): number {
  const data = new DataView(new ArrayBuffer(8));
  data.setFloat64(0, Math.max(Math.abs(a), Math.abs(b)), false);
  const exponent = (data.getUint32(0, false) >>> 20) & 0x7ff;
  return 16 * 2 ** (exponent === 0 ? -1074 : exponent - 1075);
}
export function buildMixtureGroup(totalText: string, unitText: string, coding: MixtureGroup["coding"], drafts: MixtureComponentDraft[]): MixtureGroup | string {
  const total = parseDoeResponseNumber(totalText), unit = unitText.trim();
  if (total === null || total <= 0 || !unit || unit.length > 40 || !["auto", "lower", "upper"].includes(coding) || drafts.length < 2 || drafts.length > 8) return "bayesian_mixture_definition_invalid";
  const ids = new Set<string>(), components: MixtureComponent[] = [];
  for (const row of drafts) {
    const low = parseDoeResponseNumber(row.low), high = parseDoeResponseNumber(row.high);
    if (!/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(row.factorId) || ids.has(row.factorId) || !row.name.trim() || row.name.trim().length > 80 || low === null || high === null || low < 0 || high < low) return "bayesian_mixture_definition_invalid";
    ids.add(row.factorId); components.push({ factor_id: row.factorId, name: row.name.trim(), low, high, unit });
  }
  const lower = sum(components.map(c => c.low)), upper = sum(components.map(c => c.high));
  if (!Number.isFinite(lower) || !Number.isFinite(upper) || components.filter(c => c.low < c.high).length < 2 || sum([total, ...components.map(c => -c.low)]) <= tolerance(total, lower) || sum([...components.map(c => c.high), -total]) <= tolerance(upper, total)) return "bayesian_mixture_region_invalid";
  return { total, coding, components };
}
export function validMixtureCoordinates(point: MixedActualPoint, mixture: MixtureGroup, process: MixedFactorRequest[] = []): boolean {
  if (!point || !Number.isFinite(mixture.total) || mixture.total <= 0 || Object.keys(point).length !== mixture.components.length + process.length) return false;
  const values: number[] = [];
  for (const component of mixture.components) { const value = point[component.factor_id]; if (![component.low, component.high].every(Number.isFinite) || component.low < 0 || component.high < component.low || typeof value !== "number" || !Number.isFinite(value) || value < component.low || value > component.high) return false; values.push(value); }
  const actual = sum(values);
  if (!Number.isFinite(actual) || Math.abs(actual - mixture.total) > tolerance(actual, mixture.total)) return false;
  return process.every(factor => { const value = point[factor.factor_id];
    if ("levels" in factor) return typeof value === "string" && factor.levels.includes(value);
    return typeof value === "number" && Number.isFinite(value) && value >= factor.low && value <= factor.high && (factor.domain_kind !== "discrete_numeric" || factor.step !== null && factor.step !== undefined && isRsmOnLattice(value, factor.low, factor.step));
  });
}
export function buildMixtureStudyRequest(draft: { name: string; total: string; unit: string; coding: MixtureGroup["coding"]; components: MixtureComponentDraft[]; process: MixedFactorDraft[]; constraints: MixedConstraintDraft[]; objective: BayesianDesirabilityObjective; seed: string; size: string }): MixtureStudyRequest | string {
  const mixture = buildMixtureGroup(draft.total, draft.unit, draft.coding, draft.components);
  if (typeof mixture === "string") return mixture;
  const process = draft.process.length ? parseMixedFactorDefinitions(draft.process) : [];
  if (typeof process === "string") return process;
  const ids = [...mixture.components.map(c => c.factor_id), ...process.map(f => f.factor_id)];
  const seed = planningInteger(draft.seed, 0, 2147483647), size = planningInteger(draft.size, Math.max(2, ids.length), 64);
  if (!draft.name.trim() || draft.name.trim().length > 120 || ids.length > 10 || process.length > 8 || new Set(ids).size !== ids.length || seed === null || size === null) return "bayesian_mixture_study_input_invalid";
  const constraintFactors: MixedFactorRequest[] = [...mixture.components.map(c => ({ ...c, domain_kind: "continuous" as const })), ...process];
  const constraints = parseMixedConstraintDefinitions(draft.constraints, constraintFactors);
  return typeof constraints === "string" ? constraints : { schema_version: 8, name: draft.name.trim(), mixture, process_factors: process, objective: draft.objective, constraints, initial_design_seed: seed, initial_design_size: size };
}
export function validMixtureStudy(value: MixtureStudy, expectedId?: string): boolean {
  return !!value && value.study_schema_version === 8 && planningId(value.study_id) && (!expectedId || value.study_id === expectedId) && planningId(value.study_version_id) && planningHash(value.definition_sha256) && value.objective?.goal_type === "desirability" && Array.isArray(value.objective.responses) && value.objective.responses.length >= 1 && value.objective.responses.length <= 4 && planningId(value.observation_history?.history_revision_id) && planningHash(value.observation_history?.observation_history_sha256) && value.observation_history.study_version_id === value.study_version_id && !!value.mixture && Array.isArray(value.mixture.components) && Array.isArray(value.process_factors) && Array.isArray(value.factors) && value.factors.length === value.mixture.components.length + value.process_factors.length && Array.isArray(value.trials) && value.trial_count === value.trials.length && value.trials.every(trial => planningId(trial.trial_id) && trial.study_version_id === value.study_version_id && validMixtureCoordinates(trial.actual_coordinates, value.mixture, value.process_factors));
}
export const mixtureSource = (study: MixtureStudy): MixedSourceRequest => ({ expected_study_version_id: study.study_version_id, expected_definition_sha256: study.definition_sha256, expected_history_revision_id: study.observation_history.history_revision_id, expected_history_sha256: study.observation_history.observation_history_sha256, expected_trial_count: study.trial_count });
export const mixtureSourceKey = (study: MixtureStudy) => JSON.stringify([study.study_id, study.study_version_id, study.definition_sha256, study.status, study.observation_history.history_revision_id, study.observation_history.observation_history_sha256, study.trial_count]);
export function mixtureReviewDraftKey(draft: { seed: string; budget: string; distance: string; batch: string; manual: boolean; selected: string[] }): string {
  return JSON.stringify([draft.seed, draft.budget, draft.distance, draft.batch, draft.manual, draft.selected]);
}
export function mixtureFit(study: MixtureStudy, kernel: MixedFitOptions["response_models"][number]["kernel"]["kind"], seconds: string, seedText: string): MixedFitOptions | null {
  const duration = planningInteger(seconds, 1, 60), seed = planningInteger(seedText, 0, 2147483647);
  if (duration === null || seed === null) return null;
  return { response_models: study.objective.responses.map(r => ({ response_id: r.response_id, kernel: { kind: kernel }, surrogate: { noise_mode: "estimate", fixed_noise_sd: null, initial_noise_variance_scaled: .01, lower_noise_variance_scaled: .000001, upper_noise_variance_scaled: 1 } })), observation_policy: { mode: "retain_raw", nearby_tolerances: null, nearby_units: "normalized" }, xi_desirability: .01, search: { ...defaultDesirabilitySearch, random_seed: seed, time_budget_ms: duration * 1000, model_max_evaluations: 1000, hyperparameter_restart_count: 0 }, fit_policy: { policy: "bounded_typed_factor_starts_v1", deterministic_start_count: 3 }, max_moment_evaluations: 8192 };
}
export function validMixtureModel(model: MixtureModel, study: MixtureStudy): boolean {
  return !!model && model.schema_version === 3 && model.study_id === study.study_id && model.study_version_id === study.study_version_id && model.definition_sha256 === study.definition_sha256 && planningId(model.model_id) && planningId(model.source_history_revision_id) && [model.snapshot_sha256, model.config_sha256, model.history_sha256].every(planningHash) && model.model_reusable_without_refit === true && sameDesirabilityJson(model.objective, study.objective) && Array.isArray(model.warnings);
}
export const currentMixtureModel = (model: MixtureModel, study: MixtureStudy) => validMixtureModel(model, study) && model.source_is_current && model.source_history_revision_id === study.observation_history.history_revision_id && model.history_sha256 === study.observation_history.observation_history_sha256;
export function validMixtureRow(row: MixtureRow, study: MixtureStudy): boolean {
  return !!row && planningHash(row.row_id) && validMixtureCoordinates(row.actual_coordinates, study.mixture, study.process_factors) && typeof row.constraints_satisfied === "boolean" && typeof row.eligible === "boolean" && row.eligible === (row.constraints_satisfied && row.novel) && Array.isArray(row.response_predictions) && sameDesirabilityJson(row.response_predictions.map(r => r.response_id), study.objective.responses.map(r => r.response_id)) && row.response_predictions.every(r => [r.mean_raw, r.latent_standard_deviation_raw, r.predictive_standard_deviation_raw].every(Number.isFinite) && r.latent_standard_deviation_raw >= 0 && r.predictive_standard_deviation_raw >= r.latent_standard_deviation_raw) && Number.isFinite(row.desirability_moments?.mean) && row.desirability_moments.mean >= 0 && row.desirability_moments.mean <= 1;
}
export function validMixturePage(page: MixturePage, study: MixtureStudy, model: MixtureModel): boolean {
  const revision = page?.revision;
  return !!revision && planningId(revision.revision_id) && planningHash(revision.rows_sha256) && revision.model_id === model.model_id && revision.study_version_id === study.study_version_id && revision.definition_sha256 === study.definition_sha256 && revision.history_sha256 === model.history_sha256 && Number.isInteger(revision.row_count) && revision.row_count >= 1 && revision.row_count <= 10000 && Array.isArray(page.items) && page.items.length === Math.min(page.limit, revision.row_count - page.offset) && page.items.every(row => validMixtureRow(row, study));
}
export function validMixtureSelection(selection: MixtureSelection, study: MixtureStudy, model: MixtureModel): boolean {
  return !!selection && planningId(selection.selection_id) && planningHash(selection.config_sha256) && planningHash(selection.result_sha256) && selection.config?.expected_study_version_id === study.study_version_id && selection.config.expected_definition_sha256 === study.definition_sha256 && selection.config.model_id === model.model_id && selection.config.expected_model_sha256 === model.snapshot_sha256 && selection.config.expected_history_sha256 === model.history_sha256 && selection.config.expected_history_revision_id === model.source_history_revision_id && planningId(selection.config.candidate_revision_id) && planningHash(selection.config.expected_rows_sha256) && selection.result?.schema_version === 13 && selection.result.model_refit === false && selection.result.joint_improvement_claimed === false && Array.isArray(selection.result.items) && selection.result.items.length >= 1 && selection.result.items.length <= 8 && new Set(selection.result.items.map(row => row.row_id)).size === selection.result.items.length && selection.result.items.every(row => validMixtureRow(row, study) && row.eligible);
}
export function parseMixturePoints(text: string, study: MixtureStudy): MixedActualPoint[] | string {
  const preview = parsePastedTablePreview(text), ids = study.factors.map(f => f.factor_id);
  if (preview.warnings.length || preview.rows.length < 2 || !sameDesirabilityJson(preview.rows[0], ids)) return "bayesian_mixture_candidate_input_invalid";
  const points: MixedActualPoint[] = [];
  for (const cells of preview.rows.slice(1)) {
    if (cells.length !== ids.length) return "bayesian_mixture_candidate_input_invalid";
    const point: MixedActualPoint = {};
    for (let i = 0; i < ids.length; i++) { const factor = study.factors[i]; const value = factor.domain_kind === "nominal" || factor.domain_kind === "ordinal" ? cells[i] : parseDoeResponseNumber(cells[i]); if (value === null) return "bayesian_mixture_candidate_input_invalid"; point[ids[i]] = value; }
    if (!validMixtureCoordinates(point, study.mixture, study.process_factors)) return "bayesian_mixture_closure_invalid";
    points.push(point);
  }
  return points;
}

export function buildMixtureDatasetRequest(version: Pick<DatasetVersionResponse, "version_id" | "schema_hash"> & { columns: Pick<DatasetVersionResponse["columns"][number], "column_id" | "display_name" | "unit">[] }, filter: AnalysisFilterSnapshot, draft: DatasetImportDraft): MixtureDatasetImportRequest | string {
  const invalid = "bayesian_import_mapping_invalid", setup = draft.mixture;
  if (!setup || draft.responseMode !== "vector" || !draft.name.trim() || draft.name.trim().length > 120) return invalid;
  const columns = (id: string) => version.columns.find(c => c.column_id === id);
  if (draft.factors.some(row => !columns(row.columnId)) || draft.responses.some(row => !columns(draft.responseColumns[row.responseId]))) return invalid;
  const label = (id: string) => draft.displayNames?.[id] ?? columns(id)!.display_name;
  const componentRows = draft.factors.filter(row => setup.componentKeys.includes(row.key));
  const mixture = buildMixtureGroup(setup.total, setup.unit, setup.coding, componentRows.map(row => ({ ...row, name: label(row.columnId) })));
  if (typeof mixture === "string") return mixture;
  const processRows = draft.factors.filter(row => !setup.componentKeys.includes(row.key));
  const process = processRows.length ? parseMixedFactorDefinitions(processRows.map(row => ({ ...row, name: label(row.columnId), unit: columns(row.columnId)!.unit ?? "" }))) : [];
  if (typeof process === "string") return process;
  const factors: MixtureDatasetImportRequest["factor_mappings"] = [...mixture.components.map((component, i) => ({ column_id: componentRows[i].columnId, factor: { ...component, domain_kind: "mixture_component" as const } })), ...process.map((factor, i) => ({ column_id: processRows[i].columnId, factor }))];
  const ids = factors.map(row => row.factor.factor_id), columnIds = [...factors.map(row => row.column_id), ...draft.responses.map(row => draft.responseColumns[row.responseId])];
  if (ids.length > 10 || new Set(ids).size !== ids.length || new Set(columnIds).size !== columnIds.length) return invalid;
  const objective = buildVectorObjective("Desirability", draft.responses.map(row => ({ ...row, name: label(draft.responseColumns[row.responseId]), unit: columns(draft.responseColumns[row.responseId])!.unit ?? "" })));
  if (typeof objective === "string") return objective;
  const constraints = parseMixedConstraintDefinitions(draft.constraints, [...mixture.components.map(c => ({ ...c, domain_kind: "continuous" as const })), ...process]);
  if (typeof constraints === "string") return constraints;
  return { schema_version: 2, name: draft.name.trim(), dataset_version_id: version.version_id, expected_schema_hash: version.schema_hash, mixture, factor_mappings: factors, objective, constraints, response_mappings: draft.responses.map(row => ({ column_id: draft.responseColumns[row.responseId], response_id: row.responseId })), filter_snapshot: filter, missing_policy: draft.missingPolicy };
}
