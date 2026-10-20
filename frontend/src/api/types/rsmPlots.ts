export interface RsmPlotSettings {
  plot_kind: "contour" | "main_effect" | "interaction";
  x_factor_id: string;
  y_factor_id: string | null;
  held_actual_values: Record<string, number>;
  axis_scale: "actual" | "coded";
  grid_size: number;
  contour_levels: { count: number; thresholds: number[] | null };
  trace_actual_values: number[] | null;
  filled: boolean;
  lines: boolean;
  design_points: boolean;
}
export interface RsmPlotSource {
  expected_result_sha256: string;
  response_revision_id: string;
  response_revision_sha256: string;
}
export interface RsmPlotAxis {
  factor_id: string; name: string; unit: string | null; minimum: number; maximum: number;
}
export interface RsmPlotPoint {
  point_id: string; x: number; y: number; predicted: number; outside_design_hull: boolean;
}
export type RsmVertex = readonly [number, number];
export interface RsmContourGeometry {
  algorithm: "contourpy.serial"; algorithm_version: "1.3.2";
  grid_orientation: "z[y_index][x_index]";
  minimum: number; maximum: number; constant: boolean; levels: number[];
  lines: { level: number; paths: RsmVertex[][] }[];
  bands: { lower: number | null; upper: number | null; polygons: { rings: RsmVertex[][] }[] }[];
}
export interface RsmPlotBundle {
  schema_version: 1; settings: RsmPlotSettings;
  x_axis: RsmPlotAxis; y_axis: RsmPlotAxis | null;
  response_name: string; response_unit: string | null;
  held_actual_values: Record<string, number>;
  points: RsmPlotPoint[];
  curves: { series_id: string; trace_actual_value: number | null; points: RsmPlotPoint[] }[];
  geometry: RsmContourGeometry | null;
  design_points: { run_order: number; x: number; y: number; on_slice: boolean }[];
  hull_slice_polygon: RsmVertex[];
  hull_policy: "full_design_coded_convex_hull"; final_term_ids: string[];
}
export interface RsmPlotView extends RsmPlotSource {
  schema_version: 1; design_id: string; design_version_id: string; design_sha256: string;
  analysis_id: string; view_sha256: string; bundle: RsmPlotBundle;
}
export interface RsmPlotViewDescriptor {
  asset_id: string; sha256: string; created_at: string;
}
export interface RsmSavedPlotView extends RsmPlotViewDescriptor {
  view: RsmPlotView;
}
