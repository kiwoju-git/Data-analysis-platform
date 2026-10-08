import { useState } from "react";
import { AppChrome } from "../AppChrome";
import type { DatasetVersionResponse } from "../api";
import { useI18n } from "../i18n/LocaleProvider";
import { ScorePlot } from "./PrincipalComponentCharts";
import { LoadingPlot } from "./PlsResultCharts";
import { GpProfileChart, GpScatter } from "./GaussianProcessCharts";
import { gpFixture, pcaFixture, plsFixture } from "./resultChartFixtures";

const pca = pcaFixture();
const gp = gpFixture();
const pls = plsFixture();
pls.predictors = Array.from({ length: 25 }, (_, index) => ({
  ...pls.predictors[0], column_id: `predictor-${index}`,
  display_name: `Predictor ${index + 1} with a deliberately long synthetic name`,
}));
pls.latent_components.x_loadings = pls.predictors.map((_, index) => [index / 20 - 0.6, index / 40]);

function dataset(id: string): DatasetVersionResponse {
  return {
    version_id: id, dataset_id: "synthetic-dataset", version_number: id === "version-one" ? 1 : 2,
    row_count: 25, column_count: 2, schema_hash: "synthetic-schema", source_sha256: "synthetic-source",
    created_at: "2026-10-08T00:00:00Z", canonical_artifact: null, columns: [],
    parsing: { kind: "delimited_text", encoding: "utf-8", delimiter: ",", quote_char: "\"", decimal: ".",
      thousands: null, has_header: true, header_row: 1, data_start_row: 2, missing_tokens: [""], xlsx_sheet_name: null },
  };
}

const versions = ["version-one", "version-two"].map((id) => {
  const version = dataset(id);
  return { version_id: id, dataset_id: version.dataset_id, original_filename: "synthetic.csv",
    version_number: version.version_number, row_count: 25, column_count: 2, created_at: version.created_at,
    user_label: null, note: null, pinned: false, metadata_updated_at: null, archived: false, archived_at: null };
});
let mounts = 0;

// A browser-only shell fixture, not imported by application routes.
export function DesktopResizeFixture() {
  const { locale } = useI18n();
  const [instance] = useState(() => ++mounts);
  const [versionId, setVersionId] = useState("version-one");
  const [draft, setDraft] = useState("");
  const [component, setComponent] = useState(1);
  const [runs, setRuns] = useState(0);
  const [navigationCount, setNavigationCount] = useState(0);
  const navigate = () => setNavigationCount((value) => value + 1);
  const version = dataset(versionId);
  return <AppChrome activePage="analysis" canOpenAnalysis locale={locale}
    healthClassName="status-pill status-ready" healthLabel="Synthetic fixture" pageTitle="Desktop result layout"
    activeDatasetSelectorProps={{ version, isSwitching: false, pendingVersionId: null,
      onRetrySwitch: () => undefined, onSelect: setVersionId,
      catalogState: { activeItem: versions.find((item) => item.version_id === versionId)!,
        catalog: { offset: 0, limit: 20, total: 2, returned: 2, has_previous: false, has_next: false, versions },
        error: null, isLoading: false, isResolvingActiveItem: false, onPageChange: () => undefined, onRefresh: () => undefined } }}
    onOpenAnalysisPage={navigate} onOpenDatasetPage={navigate} onOpenGraphsPage={navigate}
    onOpenHelpPage={navigate} onOpenManagePage={navigate} onOpenProjectPage={navigate} onOpenReportsPage={navigate}>
    <section className="panel analysis-results-scope" data-testid="resize-content" data-instance={instance}>
      <div className="section-heading-row"><h2>Synthetic saved result</h2>
        <span data-testid="navigation-count">{navigationCount}</span></div>
      <div className="form-grid">
        <label>Draft value<input aria-label="Draft value" value={draft} onChange={(event) => setDraft(event.currentTarget.value)} /></label>
        <label>Loading component<select aria-label="Loading component" value={component} onChange={(event) => setComponent(Number(event.currentTarget.value))}>
          <option value="1">Component 1</option><option value="2">Component 2</option>
        </select></label>
      </div>
      <div className="action-bar"><button type="button" onClick={() => setRuns((value) => value + 1)}>Run fixture</button>
        <output data-testid="run-count">{runs}</output></div>
      <div className="analysis-result-grid" data-testid="result-grid">
        <div className="chart-panel"><h3>PCA scores</h3><ScorePlot result={pca} analysisId="desktop-fixture" xComponent={1} yComponent={2} /></div>
        <div className="chart-panel"><h3>PLS loadings</h3><LoadingPlot result={pls} analysisId="desktop-fixture" component={component} /></div>
        <div className="chart-panel"><h3>GPR fitted values</h3><GpScatter result={gp} mode="fitted" scope="desktop:selected" /></div>
        <div className="chart-panel"><h3>GPR profile</h3><GpProfileChart result={gp} profile={gp.conditional_profiles[0]} scope="desktop:selected" /></div>
      </div>
      <div className="table-wrap" data-testid="wide-table"><table className="result-table" style={{ minWidth: 1200 }}>
        <thead><tr><th>Stored identity</th><th>Long original variable name preserved in a scrollable table</th></tr></thead>
        <tbody><tr><td>Synthetic row</td><td>No user data</td></tr></tbody>
      </table></div>
      <button type="button" data-testid="after-results">After results</button>
    </section>
  </AppChrome>;
}
