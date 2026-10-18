import { describe, expect, it } from "vitest";
import { formatExactNumericValue, formatInterval, formatMeasurement, formatProbability } from "./statisticalNumberFormat";

describe("semantic numeric display without stored-value rounding", () => {
  it.each(["ko", "en"] as const)("retains small values and narrow intervals in %s", (locale) => {
    for (const value of [1e-6, 2e-6, .0004, -1e-6, Number.MIN_VALUE]) expect(formatMeasurement(value, locale)).not.toMatch(/^-?0(?:\.0+)?$/);
    expect(formatMeasurement(0, locale)).toBe("0"); expect(formatMeasurement(-0, locale)).toBe("0");
    expect(formatInterval({ lower: 1e-6, upper: 2e-6 }, locale)).toBe("[1e-6, 2e-6]");
    expect(formatInterval({ lower: 1000.000001, upper: 1000.000002 }, locale)).toBe("[1,000.000001, 1,000.000002]");
    expect(formatInterval({ lower: 1, upper: 1 + Number.EPSILON }, locale)).toBe("[1, 1.0000000000000002]");
    expect(formatInterval({ lower: 2, upper: 2 }, locale)).toBe("[2, 2]");
    expect(formatProbability(1e-12, locale)).toBe("1e-12"); expect(formatProbability(0, locale)).toBe("0");
    expect(formatProbability(1.1, locale)).toBe("-");
    expect(formatProbability(NaN, locale)).toBe("-");
  });
  it("keeps exact roundtrip information and handles missing/nonfinite values", () => {
    for (const value of [Number.MIN_VALUE, 1e12 + 1, 1000.000001, Number.MAX_VALUE]) expect(Number(formatExactNumericValue(value))).toBe(value);
    for (const value of [null, undefined, NaN, Infinity]) {
      expect(formatMeasurement(value)).toBe("-"); expect(formatExactNumericValue(value)).toBe("-"); expect(formatProbability(value)).toBe("-");
    }
    expect(formatInterval(null)).toBe("-"); expect(formatInterval({ lower: 0, upper: Infinity })).toBe("-");
  });
});
