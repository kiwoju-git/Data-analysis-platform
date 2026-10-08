import type { PlsRegressionResult } from "../api";

export function plsSelectionModel(result: Pick<PlsRegressionResult, "component_selection">) {
  return result.component_selection.rows.flatMap((row) => [
    { id: `training:${row.components}`, seriesId: "training", x: row.components, y: row.training_r_squared, row },
    { id: `cv:${row.components}`, seriesId: "cv", x: row.components, y: row.predicted_r_squared, row },
  ]);
}

export function plsResponseModel(result: Pick<PlsRegressionResult, "diagnostics">) {
  return result.diagnostics.points.flatMap((row) => [
    { id: `fitted:${row.row_index}`, seriesId: "fitted", x: row.observed, y: row.fitted, residual: row.residual, rowIndex: row.row_index },
    ...(row.cross_validated_fitted == null ? [] : [{ id: `cv:${row.row_index}`, seriesId: "cv", x: row.observed, y: row.cross_validated_fitted, residual: row.cross_validated_residual, rowIndex: row.row_index }]),
  ]);
}

export function plsScoreModel(result: Pick<PlsRegressionResult, "latent_components">) {
  const source = result.latent_components;
  const dimensions = source.x_scores.length > 0 ? Math.min(...source.x_scores.map((row) => row.length)) : 0;
  return { dimensions, points: source.x_scores.map((row, index) => {
    const rowIndex = source.score_row_indices[index];
    const validRow = Number.isInteger(rowIndex) && rowIndex >= 0;
    return { id: `row:${rowIndex}`, rowIndex, x: validRow ? dimensions >= 2 ? row[0] : rowIndex + 1 : NaN,
      y: validRow ? dimensions >= 2 ? row[1] : row[0] : NaN };
  }) };
}

export function plsLoadingModel(result: Pick<PlsRegressionResult, "predictors" | "latent_components">, component: number) {
  return result.predictors.map((predictor, index) => ({ id: predictor.column_id, label: predictor.display_name,
    value: result.latent_components.x_loadings[index]?.[component - 1] ?? NaN }));
}
