import type { LinearModelResult } from "./api";

export interface ObservedDiagnosticPoint {
  fitted: number;
  observed: number;
  residual: number;
  rowIndex: number;
  standardizedResidual: number | null;
}

export function observedDiagnosticPoints(result: LinearModelResult): ObservedDiagnosticPoint[] {
  return result.diagnostics.diagnostic_points.points
    .filter((point) => Number.isFinite(point.fitted) && Number.isFinite(point.residual))
    .map((point) => ({
      fitted: point.fitted,
      observed: point.fitted + point.residual,
      residual: point.residual,
      rowIndex: point.row_index,
      standardizedResidual: point.standardized_residual,
    }))
    .filter((point) => Number.isFinite(point.observed));
}
