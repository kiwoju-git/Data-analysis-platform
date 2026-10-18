import { describe, expect, it } from "vitest";

import type { DatasetColumnResponse, NormalityResult } from "./api";
import { filterOperatorOptions } from "./analysisFilters";
import { summarizeDatasetColumnComposition } from "./datasetColumnComposition";
import { andersonDecisionDisplay, andersonPValueLabel } from "./normalityDisplay";

const column = {
  column_id: "column-a", display_name: "\uE000doe.interactionOrder.mainEffectsOnly\uE001",
  original_name: "raw value", data_type: "decimal", measurement_level: "continuous", role: "response",
} as DatasetColumnResponse;

describe("schema display boundaries", () => {
  it("localizes composition labels without modifying column metadata or classifications", () => {
    const before = JSON.stringify(column);
    const korean = summarizeDatasetColumnComposition([column], "ko");
    const english = summarizeDatasetColumnComposition([column], "en");
    expect(korean[0].label).toBe("수치형");
    expect(english[0].label).toBe("Numeric type");
    expect(english.map(({ kind, count }) => ({ kind, count }))).toEqual(korean.map(({ kind, count }) => ({ kind, count })));
    expect(JSON.stringify(column)).toBe(before);
  });

  it("localizes operator labels without changing operator values", () => {
    const korean = filterOperatorOptions(column, "ko");
    const english = filterOperatorOptions(column, "en");
    expect(korean.find((option) => option.value === "is_not_missing")?.label).toBe("결측 아님");
    expect(english.find((option) => option.value === "is_not_missing")?.label).toBe("Not missing");
    expect(english.map((option) => option.value)).toEqual(korean.map((option) => option.value));
    expect(column.column_id).toBe("column-a");
    expect(column.display_name).toBe("\uE000doe.interactionOrder.mainEffectsOnly\uE001");
  });

  it("localizes normality interpretation while retaining decision code and numeric output", () => {
    const decision = { reject_normality: true } as NonNullable<NormalityResult["columns"][number]["anderson_darling"]["decision_at_alpha"]>;
    expect(andersonDecisionDisplay(decision, "ko").shortLabel).toBe("정규성 위배 신호");
    expect(andersonDecisionDisplay(decision, "en")).toMatchObject({
      code: "normality_violation_signal", tone: "warning", shortLabel: "Normality violation signal",
    });
    const anderson = {} as NormalityResult["columns"][number]["anderson_darling"];
    expect(andersonPValueLabel(anderson, "en")).toBe("Not provided (legacy result)");
    expect(andersonPValueLabel({ ...anderson, p_value: 0.12345678 }, "en")).toBe("0.123457");
    expect(andersonPValueLabel({ ...anderson, p_value: null }, "ko")).toBe("-");
    expect(decision).toEqual({ reject_normality: true });
  });
});
