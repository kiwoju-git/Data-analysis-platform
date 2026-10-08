import { useEffect, useMemo, useState } from "react";
import { Biplot, ComponentPairSelectors, LoadingPlot, OutlierPlot, ScorePlot, ScreePlot } from "./charts/PrincipalComponentCharts";
import { availablePcaComponents, validPcaPair } from "./charts/pcaChartModels";

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
      {analysisResult !== null && result !== null ? <PrincipalComponentsResults result={result} analysisId={analysisResult.analysis_id} /> : null}
    </section>
  );
}

function PrincipalComponentsResults({ result, analysisId }: { result: PrincipalComponentsResult; analysisId: string }) {
  const { t, formatNumber } = useI18n();
  const [requestedX, setXComponent] = useState(1);
  const [requestedY, setYComponent] = useState(2);
  const componentOptions = availablePcaComponents(result);
  const { x: xComponent, y: yComponent } = validPcaPair(componentOptions, requestedX, requestedY);
  useEffect(() => { setXComponent(xComponent); setYComponent(yComponent ?? xComponent); }, [xComponent, yComponent]);
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
        <section className="result-section"><h4>{t("pca.screePlot")}</h4><ScreePlot result={result} analysisId={analysisId} /></section>
        <section className="result-section">
          <div className="section-heading-row"><h4>{t("pca.scorePlot")}</h4><ComponentPairSelectors components={componentOptions} onX={setXComponent} onY={setYComponent} x={xComponent} y={yComponent} /></div>
          <ScorePlot result={result} analysisId={analysisId} xComponent={xComponent} yComponent={yComponent} />
        </section>
        <section className="result-section"><h4>{t("pca.loadingPlot")}</h4><LoadingPlot result={result} analysisId={analysisId} xComponent={xComponent} yComponent={yComponent} /></section>
        <section className="result-section"><h4>{t("pca.biplot")}</h4><Biplot result={result} analysisId={analysisId} xComponent={xComponent} yComponent={yComponent} /></section>
        <section className="result-section"><h4>{t("pca.outlierPlot")}</h4><OutlierPlot result={result} analysisId={analysisId} /></section>
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
