import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import type { GageRrResult } from "./api/types/analysisResultsQuality";
import { isGageRrResult, restoredGageRrOptions } from "./gageRrRestore";

describe("stored Gage R&R input options", () => {
  it.each([1, 2, 3])("admits schema %s at the actual app result/restore boundary", (schema) => {
    const fixture = (JSON.parse(readFileSync(new URL("../../tests/fixtures/gage_rr_six_panel.json", import.meta.url), "utf8")) as { auto_pool: GageRrResult }).auto_pool;
    fixture.schema_version = schema;
    if (schema < 3) delete fixture.plot_bundle;
    const before = JSON.stringify(fixture);
    expect(isGageRrResult(fixture)).toBe(true);
    expect(JSON.stringify(fixture)).toBe(before);
    expect(isGageRrResult({ ...fixture, schema_version: 4 })).toBe(false);
    expect(isGageRrResult({ ...fixture, variance_components: null })).toBe(false);
  });

  it("restores a nondefault interaction alpha without adopting the current UI default", () => {
    expect(restoredGageRrOptions({
      replicate_mode: "infer_from_rows",
      interaction_selection: {
        requested_policy: "auto_pool", effective_policy: "pooled",
        alpha_to_remove_interaction: 0.1, interaction_p_value: 0.8,
        pooled: true, reason: "interaction_p_at_or_above_alpha",
      },
    })).toEqual({
      replicateMode: "infer_from_rows", interactionPolicy: "auto_pool", interactionAlpha: "0.1",
    });
  });

  it("preserves schema1 explicit-column and retain semantics without changing the payload", () => {
    const legacy = {};
    expect(restoredGageRrOptions(legacy)).toEqual({
      replicateMode: "explicit_column", interactionPolicy: "retain", interactionAlpha: "0.05",
    });
    expect(legacy).toEqual({});
  });
});
