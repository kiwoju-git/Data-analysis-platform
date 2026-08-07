import { describe, expect, it } from "vitest";

import { resolveStatisticalTwinProfile } from "./productProfile";

describe("presentation product profile", () => {
  it("keeps full as the conservative default", () => {
    expect(resolveStatisticalTwinProfile(undefined)).toBe("full");
    expect(resolveStatisticalTwinProfile("unexpected")).toBe("full");
  });

  it("recognizes only the explicit presentation value", () => {
    expect(resolveStatisticalTwinProfile("presentation")).toBe("presentation");
    expect(resolveStatisticalTwinProfile("full")).toBe("full");
  });
});
