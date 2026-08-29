import { useEffect, useMemo, useState } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  PrincipalComponentsResult,
} from "./api";
import { CompactSettingsTable } from "./components/CompactSettingsTable";
import { NumericColumnPicker } from "./components/NumericColumnPicker";
import { useI18n } from "./i18n/LocaleProvider";

export interface PrincipalComponentsRunConfig {
  columnIds: string[];
  matrixType: "correlation" | "covariance";
  componentSelection: "all" | "fixed" | "cumulative_threshold";
  componentCount: number | null;
  cumulativeThreshold: number;
  outlierAlpha: number;
  plotPointLimit: number;
}

interface Props {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  onRun: (config: PrincipalComponentsRunConfig) => void;
  result: PrincipalComponentsResult | null;
  version: DatasetVersionResponse | null;
}

export function PrincipalComponentsPanel({
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  onRun,
  result,
  version,
}: Props) {
  const { t } = useI18n();
  const columns = useMemo(
    () => (version?.columns ?? []).filter(isNumericColumn),
    [version],
  );
  const [columnIds, setColumnIds] = useState<string[]>([]);
  const [matrixType, setMatrixType] = useState<"correlation" | "covariance">("correlation");
  const [componentSelection, setComponentSelection] =
    useState<PrincipalComponentsRunConfig["componentSelection"]>("all");
  const [componentCount, setComponentCount] = useState(2);
  const [cumulativeThreshold, setCumulativeThreshold] = useState(0.9);
  const [outlierAlpha, setOutlierAlpha] = useState(0.05);
  const [plotPointLimit, setPlotPointLimit] = useState(5000);

  useEffect(() => setColumnIds([]), [version?.version_id]);
  const maximumComponents = Math.max(
    1,
    Math.min(columnIds.length || 1, Math.max(1, (version?.row_count ?? 2) - 1)),
  );
  useEffect(() => {
    setComponentCount((current) => Math.max(1, Math.min(current, maximumComponents)));
  }, [maximumComponents]);

  const canRun =
    version !== null &&
    columnIds.length >= 2 &&
    filterValidationError === null &&
    !isRunningAnalysis;

  return (
    <section className="analysis-run-panel pca-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">{t("pca.datasetRequired")}</div>
      ) : (
        <>
          <div className="notice-box">
            <p>{t("pca.description")}</p>
            <p>{t("pca.plsDifference")}</p>
          </div>
          <NumericColumnPicker
            columns={columns}
            helpText={t("pca.variableHelp")}
            legend={t("pca.variables")}
            maximumSelection={50}
            minimumSelection={2}
            onClear={() => setColumnIds([])}
            onToggle={(columnId, checked) =>
              setColumnIds((current) =>
                checked
                  ? current.includes(columnId)
                    ? current
                    : [...current, columnId]
                  : current.filter((candidate) => candidate !== columnId),
              )
            }
            selectedColumnIds={columnIds}
          />
          <CompactSettingsTable
            ariaLabel={t("pca.settings")}
            fields={[
              {
                key: "matrix",
                label: t("pca.matrixType"),
                controlId: "pca-matrix-type",
                control: (
                  <select
                    id="pca-matrix-type"
                    value={matrixType}
                    onChange={(event) =>
                      setMatrixType(event.currentTarget.value as "correlation" | "covariance")
                    }
                  >
                    <option value="correlation">{t("pca.correlationMatrix")}</option>
                    <option value="covariance">{t("pca.covarianceMatrix")}</option>
                  </select>
                ),
                helper: matrixType === "correlation" ? t("pca.correlationHelp") : t("pca.covarianceHelp"),
              },
              {
                key: "selection",
                label: t("pca.componentSelection"),
                controlId: "pca-component-selection",
                control: (
                  <select
                    id="pca-component-selection"
                    value={componentSelection}
                    onChange={(event) =>
                      setComponentSelection(
                        event.currentTarget.value as PrincipalComponentsRunConfig["componentSelection"],
                      )
                    }
                  >
                    <option value="all">{t("pca.allComponents")}</option>
                    <option value="fixed">{t("pca.fixedComponents")}</option>
                    <option value="cumulative_threshold">{t("pca.cumulativeTarget")}</option>
                  </select>
                ),
              },
              {
                key: "value",
                label:
                  componentSelection === "fixed"
                    ? t("pca.componentCount")
                    : t("pca.cumulativeThreshold"),
                controlId: "pca-component-value",
                control:
                  componentSelection === "fixed" ? (
                    <input
                      id="pca-component-value"
                      max={maximumComponents}
                      min={1}
                      type="number"
                      value={componentCount}
                      onChange={(event) => setComponentCount(Number(event.currentTarget.value))}
                    />
                  ) : (
                    <input
                      id="pca-component-value"
                      disabled={componentSelection === "all"}
                      max={1}
                      min={0.01}
                      step={0.01}
                      type="number"
                      value={cumulativeThreshold}
                      onChange={(event) => setCumulativeThreshold(Number(event.currentTarget.value))}
                    />
                  ),
              },
              {
                key: "alpha",
                label: t("pca.outlierAlpha"),
                controlId: "pca-outlier-alpha",
                control: (
                  <input
                    id="pca-outlier-alpha"
                    max={0.5}
                    min={0.001}
                    step={0.001}
                    type="number"
                    value={outlierAlpha}
                    onChange={(event) => setOutlierAlpha(Number(event.currentTarget.value))}
                  />
                ),
              },
            ]}
          />
          <details className="advanced-settings">
            <summary>{t("pca.advanced")}</summary>
            <label>
              <span>{t("pca.plotPointLimit")}</span>
              <input
                max={5000}
                min={100}
                type="number"
                value={plotPointLimit}
                onChange={(event) => setPlotPointLimit(Number(event.currentTarget.value))}
              />
            </label>
          </details>
          <div className="button-row">
            <button
              className="primary-button"
              disabled={!canRun}
              type="button"
              onClick={() =>
                onRun({
                  columnIds,
                  matrixType,
                  componentSelection,
                  componentCount: componentSelection === "fixed" ? componentCount : null,
                  cumulativeThreshold,
                  outlierAlpha,
                  plotPointLimit,
                })
              }
            >
              {isRunningAnalysis ? t("pca.running") : t("pca.run")}
            </button>
          </div>
        </>
      )}
      {analysisResult !== null && result !== null ? <PrincipalComponentsResults result={result} /> : null}
    </section>
  );
}

function PrincipalComponentsResults({ result }: { result: PrincipalComponentsResult }) {
  const { t, formatNumber } = useI18n();
  const [xComponent, setXComponent] = useState(1);
  const [yComponent, setYComponent] = useState(Math.min(2, result.eigenanalysis.length));
  const componentOptions = result.eigenanalysis.map((row) => row.component);
  return (
    <div className="pca-results">
      <section className="result-section">
        <h4>{t("pca.methodSample")}</h4>
        <dl className="result-definition-grid">
          <div><dt>{t("pca.matrixType")}</dt><dd>{result.preprocessing.matrix_type === "correlation" ? t("pca.correlationMatrix") : t("pca.covarianceMatrix")}</dd></div>
          <div><dt>{t("pca.usedRows")}</dt><dd>{formatNumber(result.sample.n_used)}</dd></div>
          <div><dt>{t("pca.excludedRows")}</dt><dd>{formatNumber(result.sample.n_excluded)}</dd></div>
          <div><dt>{t("pca.variableCount")}</dt><dd>{formatNumber(result.sample.variable_count)}</dd></div>
          <div><dt>{t("pca.selectedComponents")}</dt><dd>{result.component_selection.selected_components}</dd></div>
          <div><dt>{t("pca.cumulativeProportion")}</dt><dd>{number(result.component_selection.selected_cumulative_proportion)}</dd></div>
        </dl>
      </section>
      <section className="result-section">
        <h4>{t("pca.eigenanalysis")}</h4>
        <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("pca.component")}</th><th>{t("pca.eigenvalue")}</th><th>{t("pca.proportion")}</th><th>{t("pca.cumulativeProportion")}</th><th>{t("pca.selected")}</th></tr></thead><tbody>{result.eigenanalysis.map((row) => <tr className={row.selected ? "is-selected" : undefined} key={row.component}><td>PC{row.component}</td><td>{number(row.eigenvalue)}</td><td>{number(row.proportion)}</td><td>{number(row.cumulative_proportion)}</td><td>{row.selected ? t("pca.yes") : ""}</td></tr>)}</tbody></table></div>
      </section>
      <section className="result-section">
        <h4>{t("pca.loadings")}</h4>
        <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("pca.variable")}</th>{componentOptions.map((component) => <th key={component}>PC{component}</th>)}</tr></thead><tbody>{result.loadings.map((row) => <tr key={row.column_id}><td>{row.display_name}</td>{row.values.map((value, index) => <td key={index}>{number(value)}</td>)}</tr>)}</tbody></table></div>
      </section>
      <div className="chart-grid pca-chart-grid">
        <section className="result-section"><h4>{t("pca.screePlot")}</h4><ScreePlot result={result} /></section>
        <section className="result-section">
          <div className="section-heading-row"><h4>{t("pca.scorePlot")}</h4><ComponentPairSelectors components={componentOptions} onX={setXComponent} onY={setYComponent} x={xComponent} y={yComponent} /></div>
          <PcaScatter ariaLabel={t("pca.scorePlotDesc")} points={result.plot.points.map((row) => ({ label: `${t("pca.row")} ${row.source_row_number}`, x: row.scores[xComponent - 1] ?? 0, y: row.scores[yComponent - 1] ?? 0, outlier: row.outlier }))} />
        </section>
        <section className="result-section"><h4>{t("pca.loadingPlot")}</h4><LoadingPlot result={result} xComponent={xComponent} yComponent={yComponent} /></section>
        <section className="result-section"><h4>{t("pca.biplot")}</h4><Biplot result={result} xComponent={xComponent} yComponent={yComponent} /></section>
        <section className="result-section"><h4>{t("pca.outlierPlot")}</h4><OutlierPlot result={result} /></section>
      </div>
      <section className="result-section">
        <h4>{t("pca.scores")}</h4>
        <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("pca.row")}</th>{componentOptions.map((component) => <th key={component}>PC{component}</th>)}<th>{t("pca.mahalanobis")}</th><th>{t("pca.outlier")}</th></tr></thead><tbody>{result.scores.slice(0, 500).map((row) => <tr key={row.source_row_number}><td>{row.source_row_number}</td>{row.scores.map((score, index) => <td key={index}>{number(score)}</td>)}<td>{number(row.mahalanobis_distance_squared)}</td><td>{row.outlier ? t("pca.yes") : t("pca.no")}</td></tr>)}</tbody></table></div>
        {result.scores.length > 500 ? <p className="cell-subtle">{t("pca.scorePreviewLimit", { count: 500 })}</p> : null}
      </section>
      {result.warnings.length > 0 ? <section className="result-section"><h4>{t("pca.warnings")}</h4><ul className="warning-list">{result.warnings.map((warning) => <li key={warning}>{pcaWarningText(warning, t)} <span className="cell-subtle">{warning}</span></li>)}</ul></section> : null}
    </div>
  );
}

function ComponentPairSelectors({ components, onX, onY, x, y }: { components: number[]; onX: (value: number) => void; onY: (value: number) => void; x: number; y: number }) {
  return <div className="pca-component-pair"><select aria-label="PC X" value={x} onChange={(event) => onX(Number(event.currentTarget.value))}>{components.map((component) => <option disabled={component === y} key={component} value={component}>PC{component}</option>)}</select><select aria-label="PC Y" value={y} onChange={(event) => onY(Number(event.currentTarget.value))}>{components.map((component) => <option disabled={component === x} key={component} value={component}>PC{component}</option>)}</select></div>;
}

function ScreePlot({ result }: { result: PrincipalComponentsResult }) {
  const { t } = useI18n();
  const max = Math.max(...result.eigenanalysis.map((row) => row.eigenvalue), 1e-12);
  const x = (index: number) => 48 + (index / Math.max(1, result.eigenanalysis.length - 1)) * 540;
  const y = (value: number) => 245 - (value / max) * 200;
  return <svg className="interactive-chart pca-chart" role="img" viewBox="0 0 620 280"><title>{t("pca.screePlot")}</title><desc>{t("pca.screePlotDesc")}</desc><line className="chart-axis" x1="48" x2="588" y1="245" y2="245"/><line className="chart-axis" x1="48" x2="48" y1="45" y2="245"/><polyline className="pca-scree-line" fill="none" points={result.eigenanalysis.map((row, index) => `${x(index)},${y(row.eigenvalue)}`).join(" ")}/>{result.eigenanalysis.map((row, index) => <g key={row.component}><circle aria-label={`PC${row.component}, ${number(row.eigenvalue)}`} className={row.selected ? "pca-point is-selected" : "pca-point"} cx={x(index)} cy={y(row.eigenvalue)} r="5" tabIndex={0}/><text className="chart-tick-label" textAnchor="middle" x={x(index)} y="266">{row.component}</text></g>)}</svg>;
}

function LoadingPlot({ result, xComponent, yComponent }: { result: PrincipalComponentsResult; xComponent: number; yComponent: number }) {
  const points = result.loadings.map((row) => ({ label: row.display_name, x: row.values[xComponent - 1] ?? 0, y: row.values[yComponent - 1] ?? 0, outlier: false }));
  return <PcaScatter ariaLabel={`PC${xComponent} / PC${yComponent}`} labels points={points} />;
}

function Biplot({ result, xComponent, yComponent }: { result: PrincipalComponentsResult; xComponent: number; yComponent: number }) {
  const scorePoints = result.plot.points.map((row) => ({ label: String(row.source_row_number), x: row.scores[xComponent - 1] ?? 0, y: row.scores[yComponent - 1] ?? 0, outlier: row.outlier }));
  const extent = symmetricExtent(scorePoints.flatMap((point) => [point.x, point.y]));
  const scale = Math.max(Math.abs(extent[0]), Math.abs(extent[1]));
  const loadingPoints = result.loadings.map((row) => ({ label: row.display_name, x: (row.values[xComponent - 1] ?? 0) * scale, y: (row.values[yComponent - 1] ?? 0) * scale, outlier: false }));
  return <PcaScatter ariaLabel="PCA biplot" labels loadingPoints={loadingPoints} points={scorePoints} />;
}

function OutlierPlot({ result }: { result: PrincipalComponentsResult }) {
  const { t } = useI18n();
  const points = result.plot.points;
  const max = Math.max(result.outliers.reference_value, ...points.map((row) => row.mahalanobis_distance_squared), 1e-12);
  const x = (index: number) => 48 + (index / Math.max(1, points.length - 1)) * 540;
  const y = (value: number) => 245 - (value / max) * 200;
  return <svg className="interactive-chart pca-chart" role="img" viewBox="0 0 620 280"><title>{t("pca.outlierPlot")}</title><desc>{t("pca.outlierPlotDesc")}</desc><line className="chart-axis" x1="48" x2="588" y1="245" y2="245"/><line className="chart-axis" x1="48" x2="48" y1="45" y2="245"/><line className="chart-reference-line" x1="48" x2="588" y1={y(result.outliers.reference_value)} y2={y(result.outliers.reference_value)}/>{points.map((row, index) => <circle aria-label={`${t("pca.row")} ${row.source_row_number}, ${number(row.mahalanobis_distance_squared)}`} className={row.outlier ? "pca-point is-outlier" : "pca-point"} cx={x(index)} cy={y(row.mahalanobis_distance_squared)} key={row.source_row_number} r="4" tabIndex={0}/>)}</svg>;
}

function PcaScatter({ ariaLabel, labels = false, loadingPoints = [], points }: { ariaLabel: string; labels?: boolean; loadingPoints?: Array<ChartPoint>; points: Array<ChartPoint> }) {
  const [selected, setSelected] = useState<string | null>(null);
  const all = [...points, ...loadingPoints];
  const bounds = symmetricExtent(all.flatMap((point) => [point.x, point.y]));
  const x = (value: number) => 310 + (value / Math.max(Math.abs(bounds[0]), Math.abs(bounds[1]))) * 250;
  const y = (value: number) => 145 - (value / Math.max(Math.abs(bounds[0]), Math.abs(bounds[1]))) * 105;
  return <><svg aria-label={ariaLabel} className="interactive-chart pca-chart" role="img" viewBox="0 0 620 290"><title>{ariaLabel}</title><desc>{ariaLabel}</desc><line className="chart-axis" x1="45" x2="575" y1="145" y2="145"/><line className="chart-axis" x1="310" x2="310" y1="35" y2="255"/>{points.map((point, index) => { const key = `score-${index}`; return <circle aria-label={`${point.label}, ${number(point.x)}, ${number(point.y)}`} className={`pca-point${point.outlier ? " is-outlier" : ""}${selected === key ? " is-selected" : ""}`} cx={x(point.x)} cy={y(point.y)} key={key} onClick={() => setSelected(key)} onFocus={() => setSelected(key)} r="4.5" tabIndex={0}/>; })}{loadingPoints.map((point, index) => <g key={`loading-${index}`}><line className="pca-loading-vector" x1="310" x2={x(point.x)} y1="145" y2={y(point.y)}/><text className="chart-tick-label" x={x(point.x)} y={y(point.y)}>{point.label}</text></g>)}{labels ? points.map((point, index) => <text className="chart-tick-label" key={`label-${index}`} x={x(point.x) + 5} y={y(point.y) - 5}>{point.label}</text>) : null}</svg>{selected === null ? null : <p className="chart-detail">{points[Number(selected.split("-")[1])]?.label}</p>}</>;
}

interface ChartPoint { label: string; x: number; y: number; outlier: boolean }

function symmetricExtent(values: number[]): [number, number] {
  const maximum = Math.max(1e-12, ...values.filter(Number.isFinite).map(Math.abs));
  return [-maximum * 1.08, maximum * 1.08];
}

function isNumericColumn(column: DatasetColumnResponse): boolean {
  return column.role !== "id" && (column.data_type === "integer" || column.data_type === "decimal");
}

function number(value: number): string {
  return Number.isFinite(value) ? Number(value.toPrecision(6)).toString() : "-";
}

function pcaWarningText(
  warning: string,
  t: (key: "pca.warning.pca_complete_case_rows_excluded" | "pca.warning.pca_chart_points_limited" | "pca.warning.pca_variables_not_less_than_rows") => string,
): string {
  if (warning === "pca_chart_points_limited") return t("pca.warning.pca_chart_points_limited");
  if (warning === "pca_variables_not_less_than_rows") return t("pca.warning.pca_variables_not_less_than_rows");
  return t("pca.warning.pca_complete_case_rows_excluded");
}
