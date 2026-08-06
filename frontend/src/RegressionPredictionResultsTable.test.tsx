import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RegressionPredictionResultsTable } from "./RegressionPredictionResultsTable";

describe("RegressionPredictionResultsTable", () => {
  it("defaults to a readable summary and retains predictor details", () => {
    const mappings = [
      {
        input_column_index: 0,
        input_column_name: "temperature_c",
        source_column_id: "temperature",
        display_name: "temperature_c",
        predictor_kind: "numeric" as const,
      },
      {
        input_column_index: 1,
        input_column_name: "production_line",
        source_column_id: "line",
        display_name: "production_line",
        predictor_kind: "categorical" as const,
      },
    ];
    const html = renderToString(
      <RegressionPredictionResultsTable
        mappings={mappings}
        rows={[
          {
            mean_confidence_interval: {
              level: 0.95,
              lower: 84.8088,
              method: "t",
              upper: 85.8053,
            },
            predicted_mean: 85.30705,
            prediction_interval: {
              level: 0.95,
              lower: 80.4325,
              method: "t",
              upper: 89.1351,
            },
            predictor_values: { line: "Line-A", temperature: 88 },
            row_index: 0,
            warnings: [],
          },
        ]}
      />,
    );

    expect(html).toContain("요약 보기");
    expect(html).toContain("입력값 포함");
    expect(html).toContain("예측 평균");
    expect(html).toContain("평균 신뢰구간");
    expect(html).toContain("개별 예측구간");
    expect(html).toContain("[84.8088, 85.8053]");
    expect(html).toContain("조건 보기");
    expect(html).toContain("regression-prediction-results-wrap");
    expect(html).not.toContain("temperature_c</th>");
  });
});
