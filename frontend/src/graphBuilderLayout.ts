import type { GraphPreviewPanel, GraphPreviewType } from "./api";

export function graphPreviewGridClassName(graphType: GraphPreviewType): string {
  const suffixByType: Record<GraphPreviewType, string> = {
    box_plot: "box-plot",
    individual_value_plot: "individual-value-plot",
    histogram: "histogram",
    qq_plot: "qq-plot",
    ecdf: "ecdf",
    scatter_plot: "scatter-plot",
    run_chart: "run-chart",
    imr_chart: "imr-chart",
  };
  return `graph-preview-grid graph-preview-grid-${suffixByType[graphType]}`;
}

export function graphPreviewPanelClassName(
  kind: GraphPreviewPanel["kind"],
): string {
  return kind === "individual_values" || kind === "imr_chart"
    ? "graph-preview-panel graph-preview-card-full-row"
    : "graph-preview-panel";
}
