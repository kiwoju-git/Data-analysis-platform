import { describe, expect, it } from "vitest";

import { formatDoeFactorValue, parseDoeFactorDomainDraft } from "./factorDomain";

describe("DOE factor domain UI contract", () => {
  it("separates executable step validation from display formatting", () => {
    expect(
      parseDoeFactorDomainDraft(
        { domainKind: "discrete_numeric", step: "1", displayDecimals: "0" },
        1,
        10,
      ),
    ).toEqual({
      domain_kind: "discrete_numeric",
      step: 1,
      display_decimals: 0,
      level_count: 10,
    });
    expect(formatDoeFactorValue(5, 0)).toBe("5");
    expect(formatDoeFactorValue(5, 2)).toBe("5.00");
  });

  it("rejects bounds that are not representable by the requested step", () => {
    expect(
      parseDoeFactorDomainDraft(
        { domainKind: "discrete_numeric", step: "1", displayDecimals: "0" },
        1,
        10.5,
      ),
    ).toBeNull();
  });
});
