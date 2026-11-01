import { describe, expect, it } from "vitest";

import { parseRsmResponseDraft, validateRsmPasteApplication } from "./rsmResponseDraft";

describe("complete RSM response draft", () => {
  it.each(["", " ", "\t", "NaN", "Infinity", "1x", "0x10", "1,2"])(
    "rejects %j instead of silently coercing a response",
    (value) => {
      expect(parseRsmResponseDraft([1, 2], { 1: "2", 2: value }).ok).toBe(false);
    },
  );

  it.each(["0", "0.0", "-0", " 0 ", "1e-6", "-2.5E+2"])(
    "accepts finite decimal syntax %j",
    (value) => {
      expect(parseRsmResponseDraft([1, 2], { 1: value, 2: "3" })).toEqual({
        ok: true, values: [{ run_order: 1, value: Number(value) }, { run_order: 2, value: 3 }],
      });
    },
  );

  it("requires the exact complete run set without merging duplicate run identities", () => {
    expect(parseRsmResponseDraft([1, 2], { 1: "0" }).ok).toBe(false);
    expect(parseRsmResponseDraft([1, 1], { 1: "0" }).ok).toBe(false);
    expect(parseRsmResponseDraft([1, 2], { 1: "0", 2: "1", 3: "2" }).ok).toBe(false);
    expect(parseRsmResponseDraft([], {}).ok).toBe(false);
  });

  it("uses the full design order, independently of visible table order", () => {
    expect(parseRsmResponseDraft([3, 1, 2], { 1: "1", 2: "2", 3: "3" })).toEqual({
      ok: true,
      values: [{ run_order: 3, value: 3 }, { run_order: 1, value: 1 }, { run_order: 2, value: 2 }],
    });
  });

  it("atomically rejects stale or locked paste without changing the existing draft", () => {
    const values = { 1: "0", 2: "-1e-6" };
    const before = JSON.stringify(values);
    expect(validateRsmPasteApplication("designA:r1:edit1", "designB:r1:edit1", true, [1, 2], values)).toBe(false);
    expect(validateRsmPasteApplication("same", "same", false, [1, 2], values)).toBe(false);
    expect(validateRsmPasteApplication("same", "same", true, [1, 2, 3], values)).toBe(false);
    expect(validateRsmPasteApplication("same", "same", true, [1, 2], values)).toBe(true);
    expect(JSON.stringify(values)).toBe(before);
  });
});
