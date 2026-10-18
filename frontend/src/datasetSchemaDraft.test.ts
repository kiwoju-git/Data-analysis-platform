import { describe, expect, it } from "vitest";
import type { DatasetVersionResponse } from "./api";
import { compareSchemaDraft, createSchemaDraftBase, datasetSchemaIsUnchanged, rebaseSchemaDraft, schemaDraftsFromColumns, validSchemaHash } from "./datasetSchemaDraft";

const version = {
  version_id: "version-a", dataset_id: "dataset-a", schema_hash: "a".repeat(64),
  columns: [1, 2].map((index) => ({
    column_id: `column-${index}`, version_id: "version-a", column_index: index - 1,
    original_name: "duplicate", display_name: "duplicate", data_type: "decimal",
    measurement_level: "continuous", role: "feature", unit: null,
  })),
} as DatasetVersionResponse;

describe("schema draft three-way comparison", () => {
  it("recognizes no-ops only with matching version/hash and every column field", () => {
    expect(datasetSchemaIsUnchanged(version, { ...version, columns: version.columns.map((column) => ({ ...column })) })).toBe(true);
    expect(datasetSchemaIsUnchanged(null, version)).toBe(false);
    for (const field of ["version_id", "dataset_id", "schema_hash"] as const) {
      expect(datasetSchemaIsUnchanged(version, { ...version, [field]: "different" })).toBe(false);
    }
    for (const field of ["column_id", "version_id", "column_index", "original_name", "display_name", "data_type", "measurement_level", "role", "unit"] as const) {
      const columns = [{ ...version.columns[0], [field]: field === "column_index" ? 99 : "different" }, version.columns[1]];
      expect(datasetSchemaIsUnchanged(version, { ...version, columns })).toBe(false);
    }
    expect(datasetSchemaIsUnchanged(version, { ...version, columns: [...version.columns].reverse() })).toBe(false);
  });

  it("retains an immutable original base and overlays only local changes by exact column ID", () => {
    const base = createSchemaDraftBase(version);
    const drafts = schemaDraftsFromColumns(version.columns);
    const literal = "name <b>\uE000user\uE001";
    drafts[0].display_name = literal;
    const latest = { ...version, schema_hash: "b".repeat(64), columns: [
      { ...version.columns[1], role: "target" as const },
      { ...version.columns[0], unit: "mg", display_name: "remote name" },
    ] };
    const changes = compareSchemaDraft(base, drafts, latest);
    expect(changes.find((item) => item.field === "display_name")).toMatchObject({ conflicting: true, draft: literal });
    const merged = rebaseSchemaDraft(base, drafts, latest);
    expect(merged[0]).toMatchObject({ column_id: "column-2", role: "target", display_name: "duplicate" });
    expect(merged[1]).toMatchObject({ column_id: "column-1", unit: "mg", display_name: literal });
    expect(base.schemaHash).toBe(version.schema_hash);
    expect(base.columns[0].display_name).toBe("duplicate");
    expect(Object.isFrozen(base.columns[0])).toBe(true);
    expect(latest.columns[1].display_name).toBe("remote name");
  });

  it.each(["duplicate", "missing", "extra", "wrong-version", "invalid-hash"])("rejects %s comparison identities", (kind) => {
    const latest = { ...version, columns: [...version.columns] };
    if (kind === "duplicate") latest.columns = [version.columns[0], version.columns[0]];
    if (kind === "missing") latest.columns = [version.columns[0]];
    if (kind === "extra") latest.columns.push({ ...version.columns[0], column_id: "other" });
    if (kind === "wrong-version") latest.version_id = "other";
    if (kind === "invalid-hash") latest.schema_hash = "old-hash";
    expect(() => compareSchemaDraft(createSchemaDraftBase(version), schemaDraftsFromColumns(version.columns), latest)).toThrow("dataset_schema_comparison_mismatch");
  });

  it("requires a lowercase 64-hex schema hash", () => {
    expect(validSchemaHash("0".repeat(64))).toBe(true);
    for (const value of ["", "A".repeat(64), "g".repeat(64), "a".repeat(63), "a".repeat(65)]) expect(validSchemaHash(value)).toBe(false);
  });
});
