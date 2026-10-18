import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { findInitializer, readFrontendMetadata, readGuidanceIds, readLiteralExpression } from "./read_frontend_capability_metadata.mjs";

const literal = (value) => readLiteralExpression(findInitializer(`export const data = ${value};`, "data"));

test("reads literal TS metadata without executing expressions", () => {
  const result = literal(`([{ id: "한글 name", order: 1, enabled: true, missing: null, nested: [false] }] as const) satisfies readonly unknown[]`);
  assert.equal(result[0].id, "한글 name");
  assert.equal(result[0].enabled, true);
  assert.equal(result[0].missing, null);
  assert.deepEqual(result[0].nested, [false]);
});

for (const expression of ["makeData()", "[...other]", "({ ...other })", "({ [key]: 1 })", "({ value })", "({ value: `dynamic` })"]) {
  test(`rejects executable or ambiguous metadata: ${expression}`, () => {
    assert.throws(() => literal(expression), /capability_frontend_/);
  });
}

test("rejects duplicates and malformed source", () => {
  assert.throws(() => literal('({ a: 1, "a": 2 })'), /duplicate_key/);
  assert.throws(() => findInitializer("const data = [", "data"), /parse_error/);
  assert.throws(() => findInitializer("const other = []", "data"), /missing_or_duplicate/);
  assert.throws(() => findInitializer("const data = []; const data = [];", "data"), /missing_or_duplicate/);
});

test("guidance coverage reads keys, never translates or executes values", () => {
  assert.deepEqual(readGuidanceIds('export const analysisMethodGuidance = { "eda.a": translationToken("known") } as const satisfies Record<string, unknown>;'), ["eda.a"]);
  assert.throws(() => readGuidanceIds('const analysisMethodGuidance = { "eda.a": {}, "eda.a": {} };'), /duplicate_guidance/);
  assert.throws(() => readGuidanceIds('const analysisMethodGuidance = { ...other };'), /guidance_property/);
});

test("actual domain source is literal and contains eight unique domains", () => {
  const metadata = readFrontendMetadata();
  assert.equal(metadata.domains.length, 8);
  assert.equal(new Set(metadata.domains.map((domain) => domain.id)).size, 8);
  assert.ok(metadata.guidance_method_ids.includes("regression.gaussian_process"));
});

test("CLI reads a Korean space source archive from a different cwd without Git", () => {
  const root = mkdtempSync(join(tmpdir(), "capability 한글 "));
  try {
    const source = join(root, "frontend/src");
    mkdirSync(source, { recursive: true });
    writeFileSync(join(source, "analysisDomains.ts"), 'export const ANALYSIS_DOMAINS = [{id:"synthetic", order:1, families:[]}];', "utf8");
    writeFileSync(join(source, "analysisMethodGuidance.ts"), 'export const analysisMethodGuidance = { "synthetic.method": translate("not executed") };', "utf8");
    const child = spawnSync(process.execPath, [fileURLToPath(new URL("./read_frontend_capability_metadata.mjs", import.meta.url)), root], { cwd: tmpdir(), encoding: "utf8", timeout: 30_000 });
    assert.equal(child.status, 0, child.stderr);
    assert.equal(JSON.parse(child.stdout).domains[0].id, "synthetic");
    assert.deepEqual(JSON.parse(child.stdout).guidance_method_ids, ["synthetic.method"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
