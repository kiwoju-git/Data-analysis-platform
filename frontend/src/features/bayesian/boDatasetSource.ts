import type { DatasetImportedInitialDesign } from "../../api/types/boDatasetSource";
import { planningHash, planningId } from "./boPlanningDraft";

const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value);
const count = (value: unknown, min = 0, max = Number.MAX_SAFE_INTEGER): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= min && value <= max;

export function validDatasetImportedInitialDesign(value: unknown, factorIds?: readonly string[], responseIds?: readonly string[], expectedVersion: 1 | 2 = 1): value is DatasetImportedInitialDesign {
  if (!record(value) || value.policy !== "dataset_observations_v1" || value.import_schema_version !== expectedVersion ||
    !count(value.n_total) || !count(value.n_filtered) || !count(value.n_missing) || !count(value.n_used, 1, 200) ||
    value.n_total !== value.n_filtered + value.n_missing + value.n_used ||
    value.requested_size !== value.n_used || value.generated_size !== value.n_used ||
    !count(value.unique_coordinate_count, 1, value.n_used) ||
    value.repeated_coordinate_count !== value.n_used - value.unique_coordinate_count ||
    !count(value.conflicting_coordinate_count, 0, Math.min(value.unique_coordinate_count, value.repeated_coordinate_count)) ||
    !Array.isArray(value.warnings) || !value.warnings.every(item => typeof item === "string") ||
    !record(value.source) || !planningId(value.source.dataset_id) || !planningId(value.source.dataset_version_id) ||
    ![value.source.schema_hash, value.source.canonical_sha256, value.source.raw_sha256, value.source.filter_sha256,
      value.preflight_sha256, value.observations_sha256, value.request_sha256].every(planningHash) || !planningId(value.request_id) ||
    !record(value.runtime_provenance) || (value.missing_policy !== "reject" && value.missing_policy !== "complete_case") ||
    (value.missing_policy === "reject" && value.n_missing !== 0)) return false;
  const rows = value.source_row_indices;
  if (!Array.isArray(rows) || rows.length !== value.n_used || !rows.every((row, index) =>
    count(row, 0, (value.n_total as number) - 1) && (index === 0 || row > rows[index - 1]))) return false;
  const columns = (mapping: unknown, ids: readonly string[] | undefined) => record(mapping) && Object.keys(mapping).length > 0 &&
    Object.entries(mapping).every(([id, column]) => id.length > 0 && typeof column === "string" && column.length > 0) &&
    (ids === undefined || Object.keys(mapping).length === ids.length && ids.every(id => Object.prototype.hasOwnProperty.call(mapping, id)));
  if (!columns(value.factor_columns, factorIds) || !columns(value.response_columns, responseIds)) return false;
  const filter = value.filter_snapshot;
  return record(filter) && filter.expression_version === 1 && Array.isArray(filter.conditions) && filter.conditions.every(condition =>
    record(condition) && typeof condition.column_id === "string" && condition.column_id.length > 0 &&
    ["is_missing", "is_not_missing", "eq", "ne", "gt", "gte", "lt", "lte"].includes(String(condition.operator)) &&
    (condition.value === undefined || condition.value === null || typeof condition.value === "string" ||
      typeof condition.value === "number" && Number.isFinite(condition.value)));
}
