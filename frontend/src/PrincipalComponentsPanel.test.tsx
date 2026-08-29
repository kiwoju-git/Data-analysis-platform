import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";

import type {
  AnalysisResultEnvelope,
  DatasetVersionResponse,
  PrincipalComponentsResult,
} from "./api";
import { PrincipalComponentsPanel } from "./PrincipalComponentsPanel";
import { setCurrentLocale } from "./i18n/store";

describe("PrincipalComponentsPanel", () => {
  beforeEach(() => setCurrentLocale("en"));
  it("renders the shared numeric picker and correlation/covariance settings", () => {
    const html = renderToString(
      <PrincipalComponentsPanel
        analysisResult={null}
        filterValidationError={null}
        isRunningAnalysis={false}
        methodId="eda.principal_components"
        onRun={() => undefined}
        result={null}
        version={versionFixture()}
      />,
    );

    expect(html).toContain("numeric-column-picker");
    expect(html).toContain("Correlation matrix");
    expect(html).toContain("Covariance matrix");
    expect(html).toContain("temperature_c");
    expect(html).toContain("pressure_bar");
    expect(html).not.toContain("Response variable");
  });

  it("renders eigenanalysis, scores, loadings, biplot, and outlier diagnostics", () => {
    const result = resultFixture();
    const html = renderToString(
      <PrincipalComponentsPanel
        analysisResult={{ result } as AnalysisResultEnvelope}
        filterValidationError={null}
        isRunningAnalysis={false}
        methodId="eda.principal_components"
        onRun={() => undefined}
        result={result}
        version={versionFixture()}
      />,
    );

    expect(html).toContain("Eigenanalysis");
    expect(html).toContain("Scree Plot");
    expect(html).toContain("Score Plot");
    expect(html).toContain("Loading Plot");
    expect(html).toContain("Biplot");
    expect(html).toContain("Outlier Plot");
    expect(html).toContain("Squared Mahalanobis distance");
  });
});

function versionFixture(): DatasetVersionResponse {
  return {
    version_id: "pca-version",
    dataset_id: "pca-dataset",
    row_count: 6,
    column_count: 3,
    created_at: "2026-08-29T00:00:00Z",
    columns: [
      column("x1", "temperature_c", 0),
      column("x2", "pressure_bar", 1),
      column("id", "run_id", 2, "id"),
    ],
  } as unknown as DatasetVersionResponse;
}

function column(id: string, name: string, index: number, role: "feature" | "id" = "feature") {
  return {
    column_id: id,
    display_name: name,
    source_name: name,
    column_index: index,
    data_type: role === "id" ? "string" as const : "decimal" as const,
    measurement_level: role === "id" ? "id" as const : "continuous" as const,
    role,
    unit: null,
  };
}

function resultFixture(): PrincipalComponentsResult {
  const scoreRows = [
    { source_row_number: 1, scores: [-1, 0.2], mahalanobis_distance_squared: 1.1, outlier: false },
    { source_row_number: 2, scores: [1, -0.2], mahalanobis_distance_squared: 7.1, outlier: true },
  ];
  return {
    schema_version: 1,
    summary_type: "principal_components_analysis",
    method: "sample_correlation_eigendecomposition",
    missing_policy: "complete_case",
    sample: { n_total: 2, n_used: 2, n_excluded: 0, n_excluded_missing: 0, n_excluded_non_numeric: 0, variable_count: 2 },
    variables: [
      { column_id: "x1", display_name: "temperature_c", unit: null, mean: 2, sample_standard_deviation: 1 },
      { column_id: "x2", display_name: "pressure_bar", unit: null, mean: 4, sample_standard_deviation: 2 },
    ],
    preprocessing: { matrix_type: "correlation", centered: true, standardized: true, degrees_of_freedom: 1 },
    matrix: [[1, 0.8], [0.8, 1]],
    component_selection: { mode: "all", requested_component_count: null, cumulative_threshold: 0.9, maximum_components: 2, selected_components: 2, selected_cumulative_proportion: 1 },
    eigenanalysis: [
      { component: 1, eigenvalue: 1.8, proportion: 0.9, cumulative_proportion: 0.9, selected: true },
      { component: 2, eigenvalue: 0.2, proportion: 0.1, cumulative_proportion: 1, selected: true },
    ],
    eigenvectors: [
      { column_id: "x1", display_name: "temperature_c", values: [0.707, 0.707] },
      { column_id: "x2", display_name: "pressure_bar", values: [0.707, -0.707] },
    ],
    loadings: [
      { column_id: "x1", display_name: "temperature_c", values: [0.95, 0.32] },
      { column_id: "x2", display_name: "pressure_bar", values: [0.95, -0.32] },
    ],
    scores: scoreRows,
    plot: { point_limit: 5000, point_count: 2, sampled: false, sampling_policy: "outliers_then_evenly_spaced", points: scoreRows },
    outliers: { alpha: 0.05, method: "chi_square_squared_mahalanobis_selected_components", degrees_of_freedom: 2, reference_value: 5.99, count: 1 },
    warnings: [],
    provenance: { algorithm: "numpy.linalg.eigh", sign_policy: "largest_absolute_eigenvector_entry_positive_first_on_tie", score_equation: "transformed_X @ eigenvectors" },
  };
}
