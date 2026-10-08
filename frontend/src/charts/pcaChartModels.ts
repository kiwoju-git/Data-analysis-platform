import type { PrincipalComponentsResult } from "../api";
import type { NumericRange } from "./chartScale";
type PcaChartSource = Pick<PrincipalComponentsResult, "eigenanalysis" | "plot" | "loadings" | "outliers">;

export function availablePcaComponents(result: PcaChartSource): number[] {
  const dimensions = [...result.plot.points.map((row) => row.scores.length), ...result.loadings.map((row) => row.values.length)];
  const maximum = dimensions.length === 0 ? 0 : Math.min(...dimensions);
  return result.eigenanalysis.map((row) => row.component).filter((component) => component > 0 && component <= maximum);
}

export function validPcaPair(components: readonly number[], x: number, y: number): { x: number; y: number | null } {
  const validX = components.includes(x) ? x : components[0] ?? 1;
  return { x: validX, y: components.includes(y) && y !== validX ? y : components.find((component) => component !== validX) ?? null };
}

export function pcaScoreModel(result: PcaChartSource, x: number, y: number | null) {
  return result.plot.points.map((row) => ({
    id: `row:${row.source_row_number}`, rowNumber: row.source_row_number,
    x: y === null ? row.source_row_number : row.scores[x - 1],
    y: y === null ? row.scores[x - 1] : row.scores[y - 1],
    distanceSquared: row.mahalanobis_distance_squared, outlier: row.outlier,
  }));
}

export function pcaLoadingModel(result: PcaChartSource, x: number, y: number) {
  return result.loadings.map((row) => ({ id: `variable:${row.column_id}`, label: row.display_name,
    x: row.values[x - 1], y: row.values[y - 1] }));
}

export function pcaSymmetricRange(values: readonly number[]): NumericRange {
  const maximum = Math.max(1e-12, ...values.filter(Number.isFinite).map(Math.abs));
  return { min: -maximum * 1.08, max: maximum * 1.08 };
}

export function pcaBiplotModel(result: PcaChartSource, x: number, y: number) {
  const rawScorePoints = pcaScoreModel(result, x, y);
  const rawLoadingVectors = pcaLoadingModel(result, x, y);
  // Preserve the established display-only scale, not a new SVD biplot definition.
  const loadingDisplayScale = pcaSymmetricRange(rawScorePoints.flatMap((point) => [point.x, point.y])).max;
  return { rawScorePoints, rawLoadingVectors, loadingDisplayScale,
    displayedLoadingVectors: rawLoadingVectors.map((point) => ({ ...point, x: point.x * loadingDisplayScale, y: point.y * loadingDisplayScale })) };
}

export function pcaOutlierModel(result: PcaChartSource) {
  return result.plot.points.map((row) => ({ id: `row:${row.source_row_number}`, x: row.source_row_number,
    y: row.mahalanobis_distance_squared, outlier: row.outlier }));
}
