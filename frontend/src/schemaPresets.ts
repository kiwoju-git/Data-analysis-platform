import type { DatasetColumnRole, DatasetMeasurementLevel } from "./api";

export interface SchemaDraft {
  column_id: string;
  display_name: string;
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string;
}

export function applyBayesianOptimizationPreset(drafts: SchemaDraft[]): SchemaDraft[] {
  return drafts.map((draft, index) => {
    if (index === 0) {
      return {
        ...draft,
        measurement_level: "id",
        role: "id",
      };
    }

    if (index >= 1 && index <= 24) {
      return {
        ...draft,
        measurement_level: isBayesianDayColumn(index) ? "count" : "continuous",
        role: "feature",
      };
    }

    if (index >= 25 && index <= 33) {
      return {
        ...draft,
        measurement_level: "continuous",
        role: "response",
      };
    }

    return draft;
  });
}

function isBayesianDayColumn(columnIndex: number): boolean {
  return columnIndex === 4 || columnIndex === 5 || columnIndex === 22;
}
