import { describe, expect, it } from "vitest";
import { restoredGageRrOptions } from "./gageRrRestore";

describe("stored Gage R&R input options", () => {
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
