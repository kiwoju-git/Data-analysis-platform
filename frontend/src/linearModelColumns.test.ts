import { describe, expect, it } from "vitest";

import type { DatasetColumnResponse } from "./api";
import {
  isNumericLinearModelPredictor,
  isSupportedLinearModelPredictor,
  isSupportedLinearModelResponse,
  linearModelPredictorKind,
} from "./linearModelColumns";

function column(
  overrides: Partial<DatasetColumnResponse> = {},
): DatasetColumnResponse {
  return {
    column_id: "column-1",
    version_id: "version-1",
    column_index: 0,
    original_name: "afucose",
    display_name: "afucose",
    data_type: "decimal",
    measurement_level: "continuous",
    role: "factor",
    unit: null,
    ...overrides,
  };
}

describe("linear-model column semantics", () => {
  it("keeps continuous and count factors numeric", () => {
    expect(linearModelPredictorKind(column())).toBe("numeric");
    expect(
      linearModelPredictorKind(
        column({ data_type: "integer", measurement_level: "count" }),
      ),
    ).toBe("numeric");
    expect(isNumericLinearModelPredictor(column())).toBe(true);
  });

  it("uses measurement level for numeric-coded categorical factors", () => {
    expect(linearModelPredictorKind(column({ measurement_level: "nominal" }))).toBe(
      "categorical",
    );
    expect(
      linearModelPredictorKind(
        column({ data_type: "text", measurement_level: "nominal" }),
      ),
    ).toBe("categorical");
  });

  it("rejects datetime and ID columns", () => {
    expect(
      isSupportedLinearModelPredictor(
        column({ data_type: "datetime", measurement_level: "datetime" }),
      ),
    ).toBe(false);
    expect(isSupportedLinearModelPredictor(column({ role: "id" }))).toBe(false);
  });

  it("accepts numeric responses independently from their suggested role", () => {
    expect(isSupportedLinearModelResponse(column({ role: "factor" }))).toBe(true);
    expect(isSupportedLinearModelResponse(column({ measurement_level: "nominal" }))).toBe(
      false,
    );
  });
});
