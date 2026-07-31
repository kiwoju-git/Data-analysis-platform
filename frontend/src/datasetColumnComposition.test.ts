import { describe, expect, it } from "vitest";

import type { DatasetColumnResponse } from "./api";
import { summarizeDatasetColumnComposition } from "./datasetColumnComposition";

describe("dataset column composition", () => {
  it("classifies numeric, categorical, datetime, and ID columns without row data", () => {
    const result = summarizeDatasetColumnComposition([
      column("numeric", "decimal", "continuous", "feature"),
      column("count", "integer", "count", "feature"),
      column("category", "text", "nominal", "group"),
      column("flag", "boolean", "binary", "feature"),
      column("recorded_at", "datetime", "datetime", "time"),
      column("run_id", "text", "id", "id"),
    ]);

    expect(result).toEqual([
      { kind: "numeric", label: "수치형", count: 2 },
      { kind: "categorical", label: "범주·문자형", count: 2 },
      { kind: "datetime", label: "날짜시간형", count: 1 },
      { kind: "other", label: "ID·기타", count: 1 },
    ]);
    expect(result.reduce((sum, item) => sum + item.count, 0)).toBe(6);
  });
});

function column(
  id: string,
  dataType: DatasetColumnResponse["data_type"],
  measurementLevel: DatasetColumnResponse["measurement_level"],
  role: DatasetColumnResponse["role"],
): DatasetColumnResponse {
  return {
    column_id: id,
    version_id: "version-1",
    column_index: 0,
    original_name: id,
    display_name: id,
    data_type: dataType,
    measurement_level: measurementLevel,
    role,
    unit: null,
  };
}
