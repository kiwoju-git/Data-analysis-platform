import type { DatasetColumnResponse, DatasetVersionResponse } from "./api";
import type { SchemaDraft } from "./schemaPresets";

export const schemaEditableFields = ["display_name", "measurement_level", "role", "unit"] as const;
export type SchemaEditableField = typeof schemaEditableFields[number];
export type SchemaDraftBase = Readonly<{
  versionId: string;
  datasetId: string;
  schemaHash: string;
  columns: readonly Readonly<SchemaDraft>[];
}>;
export interface SchemaFieldComparison {
  columnId: string;
  field: SchemaEditableField;
  base: string;
  draft: string;
  latest: string;
  localChanged: boolean;
  remoteChanged: boolean;
  conflicting: boolean;
}
export type SchemaConflictState = {
  status: "loading" | "ready" | "failed";
  baseHash: string;
  latest: DatasetVersionResponse | null;
  errorCode: string | null;
};
export interface SchemaConflictProps {
  schemaConflict?: SchemaConflictState | null;
  schemaComparison?: readonly SchemaFieldComparison[];
  schemaStaged?: boolean;
  onSchemaConflictApply?: () => void;
  onSchemaConflictDiscard?: () => void;
  onSchemaConflictEdit?: () => void;
  onSchemaConflictRetry?: () => void;
}

export function schemaDraftsFromColumns(columns: readonly DatasetColumnResponse[]): SchemaDraft[] {
  return columns.map((column) => ({
    column_id: column.column_id,
    display_name: column.display_name,
    measurement_level: column.measurement_level,
    role: column.role,
    unit: column.unit ?? "",
  }));
}

export function createSchemaDraftBase(version: DatasetVersionResponse): SchemaDraftBase {
  return Object.freeze({
    versionId: version.version_id,
    datasetId: version.dataset_id,
    schemaHash: version.schema_hash,
    columns: Object.freeze(schemaDraftsFromColumns(version.columns).map((column) => Object.freeze(column))),
  });
}

export function validSchemaHash(value: string): boolean {
  return /^[a-f0-9]{64}$/.test(value);
}

const schemaColumnFields = [
  "column_id", "version_id", "column_index", "original_name", "display_name",
  "data_type", "measurement_level", "role", "unit",
] as const satisfies readonly (keyof DatasetColumnResponse)[];

export function datasetSchemaIsUnchanged(current: DatasetVersionResponse | null, next: DatasetVersionResponse): boolean {
  return current !== null && current.version_id === next.version_id && current.dataset_id === next.dataset_id &&
    current.schema_hash === next.schema_hash && current.columns.length === next.columns.length &&
    current.columns.every((column, index) => schemaColumnFields.every((field) => column[field] === next.columns[index][field]));
}

function indexedColumns(columns: readonly Readonly<SchemaDraft>[]): Map<string, Readonly<SchemaDraft>> {
  const indexed = new Map(columns.map((column) => [column.column_id, column]));
  if (indexed.size !== columns.length) throw comparisonMismatch();
  return indexed;
}

function comparisonMismatch(): Error {
  return Object.assign(new Error("dataset_schema_comparison_mismatch"), { code: "dataset_schema_comparison_mismatch" });
}

export function compareSchemaDraft(
  base: SchemaDraftBase, drafts: readonly SchemaDraft[], latest: DatasetVersionResponse,
): SchemaFieldComparison[] {
  const initial = indexedColumns(base.columns);
  const local = indexedColumns(drafts);
  const remote = indexedColumns(schemaDraftsFromColumns(latest.columns));
  if (latest.version_id !== base.versionId || latest.dataset_id !== base.datasetId ||
      !validSchemaHash(latest.schema_hash) || initial.size !== local.size || initial.size !== remote.size ||
      [...initial.keys()].some((id) => !local.has(id) || !remote.has(id))) {
    throw comparisonMismatch();
  }
  return base.columns.flatMap((column) => schemaEditableFields.flatMap((field) => {
    const draft = local.get(column.column_id)![field];
    const latestValue = remote.get(column.column_id)![field];
    const localChanged = draft !== column[field];
    const remoteChanged = latestValue !== column[field];
    return localChanged || remoteChanged ? [{
      columnId: column.column_id, field, base: column[field], draft, latest: latestValue,
      localChanged, remoteChanged, conflicting: localChanged && remoteChanged && draft !== latestValue,
    }] : [];
  }));
}

export function rebaseSchemaDraft(
  base: SchemaDraftBase, drafts: readonly SchemaDraft[], latest: DatasetVersionResponse,
): SchemaDraft[] {
  const changes = compareSchemaDraft(base, drafts, latest).filter((change) => change.localChanged);
  return schemaDraftsFromColumns(latest.columns).map((column) => {
    const updates = Object.fromEntries(changes.filter((change) => change.columnId === column.column_id)
      .map((change) => [change.field, change.draft]));
    return { ...column, ...updates };
  });
}
