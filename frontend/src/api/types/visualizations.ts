import type { AnalysisFilterCondition } from "./analyses";
import type { GraphicalSummaryColumn } from "./analysisResultsExploration";
import type { IndividualsChartResult, RunChartResult } from "./analysisResultsQuality";

export type GraphPreviewType =
  | "box_plot"
  | "individual_value_plot"
  | "histogram"
  | "qq_plot"
  | "ecdf"
  | "scatter_plot"
  | "run_chart"
  | "imr_chart";

export type GraphPreviewLayout = "combined" | "overlay" | "small_multiples";

export interface GraphPreviewRequest {
  dataset_version_id: string;
  filter_snapshot: {
    expression_version: 1;
    conditions: AnalysisFilterCondition[];
  };
  graph_type: GraphPreviewType;
  value_column_ids?: string[];
  x_column_id?: string | null;
  y_column_ids?: string[];
  group_column_id?: string | null;
  order_column_id?: string | null;
  point_limit?: number;
  histogram_bin_count?: number | null;
  layout: GraphPreviewLayout;
}

export interface IndividualValuePreviewPoint {
  series_id: string;
  series_label: string;
  source_column_label: string;
  point_index: number;
  canonical_position: number;
  value: number;
}

export interface IndividualValuePreviewResult {
  point_count: number;
  point_limit: number;
  sampled: false;
  n_total: number;
  n_missing: number;
  n_non_numeric: number;
  points: IndividualValuePreviewPoint[];
}

export interface ScatterPreviewPoint {
  series_id: string;
  series_label: string;
  group: string | null;
  canonical_position: number;
  x: number;
  y: number;
}

export interface ScatterPreviewResult {
  point_count: number;
  point_limit: number;
  sampled: false;
  n_total: number;
  n_excluded: number;
  x_column: GraphPreviewColumnRef;
  y_column: GraphPreviewColumnRef;
  points: ScatterPreviewPoint[];
}

export interface GraphPreviewColumnRef {
  column_id: string;
  display_name: string;
  unit: string | null;
}

interface GraphPreviewPanelBase {
  panel_id: string;
  label: string;
  unit: string | null;
  status: "succeeded" | "failed";
  error_code: string | null;
}

export interface GraphicalSummaryPreviewPanel extends GraphPreviewPanelBase {
  kind: "graphical_summary";
  result: GraphicalSummaryColumn | null;
}

export interface IndividualValuePreviewPanel extends GraphPreviewPanelBase {
  kind: "individual_values";
  result: IndividualValuePreviewResult | null;
}

export interface ScatterPreviewPanel extends GraphPreviewPanelBase {
  kind: "scatter";
  result: ScatterPreviewResult | null;
}

export interface RunChartPreviewPanel extends GraphPreviewPanelBase {
  kind: "run_chart";
  result: RunChartResult | null;
}

export interface ImrChartPreviewPanel extends GraphPreviewPanelBase {
  kind: "imr_chart";
  result: IndividualsChartResult | null;
}

export type GraphPreviewPanel =
  | GraphicalSummaryPreviewPanel
  | IndividualValuePreviewPanel
  | ScatterPreviewPanel
  | RunChartPreviewPanel
  | ImrChartPreviewPanel;

export interface GraphPreviewResponse {
  visualization_schema_version: 1;
  graph_type: GraphPreviewType;
  dataset_version_id: string;
  source_schema_hash: string;
  filter_snapshot_sha256: string;
  preview_config_sha256: string;
  row_count_total: number;
  row_count_included: number;
  warnings: string[];
  layout: GraphPreviewLayout;
  panels: GraphPreviewPanel[];
}
