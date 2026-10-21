import { describe, expect, it } from "vitest";
import { buildGpExtensionOptions, defaultGpExtensionDraft } from "./gpExtensionOptions";

describe("GPR extension request settings", () => {
  it("keeps row validation metadata out of the payload", () => {
    const value = buildGpExtensionOptions(defaultGpExtensionDraft(), "k_fold", ["x"], "y");
    expect(value?.cv).toEqual({});
    expect(value?.lag_features).toBeNull();
  });
  it("requires an explicit group and never makes it a predictor", () => {
    expect(buildGpExtensionOptions(defaultGpExtensionDraft(), "group_k_fold", ["x"], "y")).toBeNull();
    const draft = { ...defaultGpExtensionDraft(), groupColumnId: "batch" };
    expect(buildGpExtensionOptions(draft, "group_k_fold", ["x"], "y")?.cv).toEqual({ group_column_id: "batch" });
    expect(buildGpExtensionOptions(draft, "group_k_fold", ["batch"], "y")).toBeNull();
  });
  it("rejects partial/zero lags and shuffled validation for lagged input", () => {
    const draft = { ...defaultGpExtensionDraft(), timeColumnId: "time", timeUnit: "s", lagEnabled: true, laggedColumnIds: ["y"], lagText: "1,2" };
    expect(buildGpExtensionOptions(draft, "k_fold", ["x"], "y")).toBeNull();
    expect(buildGpExtensionOptions(draft, "time_series_split", ["x"], "y")?.lag_features?.lags).toEqual([1, 2]);
    for (const lagText of ["0", "1abc", "1.5", "1,1", "NaN", ""]) expect(buildGpExtensionOptions({ ...draft, lagText }, "time_series_split", ["x"], "y")).toBeNull();
  });
  it("preserves custom initial pair and exact resource selection", () => {
    const draft = { ...defaultGpExtensionDraft(), initialX: "b", initialY: "a", resourceProfile: "extended_exact" as const };
    expect(buildGpExtensionOptions(draft, "none", ["a", "b"], "y")).toMatchObject({ initial_surface_x_column_id: "b", initial_surface_y_column_id: "a", resource_profile: "extended_exact" });
    expect(buildGpExtensionOptions({ ...draft, initialY: "b" }, "none", ["a", "b"], "y")).toBeNull();
  });
});
