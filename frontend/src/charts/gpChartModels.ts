import type { GaussianProcessPointPredictionResponse, GaussianProcessRegressionResult } from "../api";

type DiagnosticsSource = Pick<GaussianProcessRegressionResult, "diagnostics">;
export type GpSurface = NonNullable<GaussianProcessRegressionResult["two_predictor_surface"]>;
export type GpSurfaceRequestSnapshot = {
  modelId: string; manifestHash: string; responseId: string;
  xColumnId: string; yColumnId: string; xName: string; yName: string;
  gridSize: number; fixedValues: number[];
  rows: Array<{ client_row_id: string; values: Record<string, number> }>;
};

export function gpScatterModel(result: DiagnosticsSource, mode: "fitted" | "cv") {
  return result.diagnostics.points.flatMap((row) => {
    const value = mode === "fitted" ? row.fitted : row.cross_validated_fitted;
    return value === null ? [] : [{ id: `row:${row.row_index}`, rowIndex: row.row_index, x: row.observed, y: value,
      residual: mode === "fitted" ? row.residual : row.cross_validated_residual }];
  });
}
export function gpResidualModel(result: DiagnosticsSource) {
  return result.diagnostics.points.map((row) => ({ id: `row:${row.row_index}`, rowIndex: row.row_index,
    x: row.fitted, y: row.residual, standardizedResidual: row.standardized_predictive_residual }));
}
export function gpUncertaintyModel(result: DiagnosticsSource) {
  return result.diagnostics.points.map((row) => ({ id: `row:${row.row_index}`, x: row.row_index + 1,
    y: row.predictive_standard_deviation }));
}

export function gpSurfaceRequest(result: GaussianProcessRegressionResult, xColumnId: string, yColumnId: string): GpSurfaceRequestSnapshot | null {
  const manifest = result.model_manifest;
  const gridSize = result.two_predictor_surface?.grid_size;
  const xRange = result.training_ranges.find((range) => range.column_id === xColumnId);
  const yRange = result.training_ranges.find((range) => range.column_id === yColumnId);
  if (!manifest || !xRange || !yRange || gridSize === undefined || !Number.isInteger(gridSize) || gridSize < 2 || gridSize > 40 || xColumnId === yColumnId) return null;
  const rows: GpSurfaceRequestSnapshot["rows"] = [];
  for (let yi = 0; yi < gridSize; yi += 1) {
    for (let xi = 0; xi < gridSize; xi += 1) {
      const x = xRange.minimum + xi / (gridSize - 1) * (xRange.maximum - xRange.minimum);
      const y = yRange.minimum + yi / (gridSize - 1) * (yRange.maximum - yRange.minimum);
      rows.push({ client_row_id: `surface-${yi}-${xi}`, values: Object.fromEntries(result.training_ranges.map((range) =>
        [range.column_id, range.column_id === xColumnId ? x : range.column_id === yColumnId ? y : range.median])) });
    }
  }
  return { modelId: manifest.model_id, manifestHash: manifest.manifest_sha256, responseId: result.response.column_id,
    xColumnId, yColumnId, xName: xRange.display_name, yName: yRange.display_name, gridSize,
    fixedValues: result.training_ranges.map((range) => range.median), rows };
}

export function joinGpSurfaceRows(snapshot: GpSurfaceRequestSnapshot, response: GaussianProcessPointPredictionResponse): GpSurface {
  const byId = new Map(response.rows.map((row) => [row.client_row_id, row]));
  const requestedIds = new Set(snapshot.rows.map((row) => row.client_row_id));
  if (response.model_id !== snapshot.modelId || response.model_manifest_sha256 !== snapshot.manifestHash || response.response_column_id !== snapshot.responseId ||
      response.row_count !== snapshot.rows.length || response.rows.length !== snapshot.rows.length || byId.size !== response.rows.length ||
      requestedIds.size !== snapshot.rows.length || response.rows.some((row) => !requestedIds.has(row.client_row_id)) ||
      response.rows.some((row) => !Number.isFinite(row.predicted_mean) || !Number.isFinite(row.predictive_standard_deviation) || row.predictive_standard_deviation < 0)) {
    throw new Error("gp_surface_response_invalid");
  }
  return { x_column_id: snapshot.xColumnId, y_column_id: snapshot.yColumnId,
    x_display_name: snapshot.xName, y_display_name: snapshot.yName, grid_size: snapshot.gridSize,
    fixed_values: [...snapshot.fixedValues], points: snapshot.rows.map((requestRow) => {
      const row = byId.get(requestRow.client_row_id)!;
      return { x: requestRow.values[snapshot.xColumnId], y: requestRow.values[snapshot.yColumnId],
        predicted_mean: row.predicted_mean, predictive_standard_deviation: row.predictive_standard_deviation };
    }) };
}
