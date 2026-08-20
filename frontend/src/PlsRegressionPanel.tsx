import { useEffect, useMemo, useRef, useState } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  PlsPointPredictionResponse,
  PlsRegressionResult,
} from "./api";
import { createPlsPointPredictions } from "./api/regression";
import { CompactSettingsTable } from "./components/CompactSettingsTable";
import { localizedErrorDisplay } from "./i18n/errorMessages";
import { useI18n } from "./i18n/LocaleProvider";

export interface PlsRunConfig {
  responseColumnId: string;
  predictorColumnIds: string[];
  scale: boolean;
  componentSelection: "automatic_cv" | "fixed";
  nComponents: number | null;
  maxComponents: number;
  cvMethod: "k_fold" | "leave_one_out";
  cvFolds: number;
  cvShuffle: boolean;
  cvSeed: number;
  maxIter: number;
  tolerance: number;
  plotPointLimit: number;
}

interface Props {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: PlsRegressionResult | null;
  version: DatasetVersionResponse | null;
  onRun: (config: PlsRunConfig) => void;
}

interface PredictionRowDraft {
  id: string;
  values: Record<string, string>;
}

const PLS_WARNING_KEYS = {
  missing_values_excluded: "pls.warning.missingValuesExcluded",
  pls_model_not_converged: "pls.warning.notConverged",
  pls_negative_predicted_r_squared: "pls.warning.negativePredictedR",
  pls_no_classical_coefficient_p_values: "pls.warning.noClassicalPValues",
  pls_predictive_not_causal: "pls.warning.notCausal",
  pls_selected_maximum_component: "pls.warning.selectedMaximum",
  pls_training_r_squared_much_higher_than_cv: "pls.warning.trainingCvGap",
} as const;

export function PlsRegressionPanel({
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  result,
  version,
  onRun,
}: Props) {
  const { t } = useI18n();
  const numericColumns = useMemo(
    () => (version?.columns ?? []).filter(isNumericColumn),
    [version],
  );
  const [responseColumnId, setResponseColumnId] = useState("");
  const [predictorColumnIds, setPredictorColumnIds] = useState<string[]>([]);
  const [scale, setScale] = useState(true);
  const [componentSelection, setComponentSelection] = useState<"automatic_cv" | "fixed">(
    "automatic_cv",
  );
  const [nComponents, setNComponents] = useState(1);
  const [maxComponents, setMaxComponents] = useState(1);
  const [cvMethod, setCvMethod] = useState<"k_fold" | "leave_one_out">("k_fold");
  const [cvFolds, setCvFolds] = useState(5);
  const [cvShuffle, setCvShuffle] = useState(true);
  const [cvSeed, setCvSeed] = useState(20260820);
  const [maxIter, setMaxIter] = useState(500);
  const [tolerance, setTolerance] = useState(1e-6);
  const [plotPointLimit, setPlotPointLimit] = useState(2000);

  useEffect(() => {
    setResponseColumnId("");
    setPredictorColumnIds([]);
  }, [version?.version_id]);

  const componentCeiling = Math.max(
    1,
    Math.min(
      30,
      predictorColumnIds.length || 1,
      Math.max(1, (version?.row_count ?? 2) - 1),
    ),
  );
  useEffect(() => {
    setMaxComponents(componentCeiling);
    setNComponents((current) => Math.max(1, Math.min(current, componentCeiling)));
  }, [componentCeiling]);
  const canRun =
    version !== null &&
    responseColumnId.length > 0 &&
    predictorColumnIds.length >= 2 &&
    !predictorColumnIds.includes(responseColumnId) &&
    filterValidationError === null &&
    !isRunningAnalysis;

  function togglePredictor(columnId: string, checked: boolean): void {
    setPredictorColumnIds((current) =>
      checked
        ? current.includes(columnId)
          ? current
          : [...current, columnId]
        : current.filter((candidate) => candidate !== columnId),
    );
  }

  return (
    <section className="analysis-run-panel pls-regression-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">{t("pls.datasetRequired")}</div>
      ) : (
        <>
          <div className="notice-box">
            <p>{t("pls.description")}</p>
            <p>{t("pls.pcaDifference")}</p>
          </div>
          <div className="option-grid option-grid-wide">
            <label>
              <span>{t("pls.response")}</span>
              <select
                value={responseColumnId}
                onChange={(event) => setResponseColumnId(event.currentTarget.value)}
              >
                <option value="">{t("pls.select")}</option>
                {numericColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <fieldset className="checkbox-field pls-predictor-field">
              <legend>{t("pls.predictors")}</legend>
              <small>{t("pls.predictorsHelp")}</small>
              <div className="checkbox-grid">
                {numericColumns
                  .filter((column) => column.column_id !== responseColumnId)
                  .map((column) => (
                    <label key={column.column_id}>
                      <input
                        checked={predictorColumnIds.includes(column.column_id)}
                        onChange={(event) =>
                          togglePredictor(column.column_id, event.currentTarget.checked)
                        }
                        type="checkbox"
                      />
                      <span>{column.display_name}</span>
                    </label>
                  ))}
              </div>
            </fieldset>
          </div>

          <CompactSettingsTable
            ariaLabel={t("pls.componentSettings")}
            className="pls-settings-table"
            fields={[
              {
                key: "selection",
                label: t("pls.componentSelection"),
                control: (
                  <select
                    value={componentSelection}
                    onChange={(event) =>
                      setComponentSelection(
                        event.currentTarget.value as "automatic_cv" | "fixed",
                      )
                    }
                  >
                    <option value="automatic_cv">{t("pls.automatic")}</option>
                    <option value="fixed">{t("pls.fixed")}</option>
                  </select>
                ),
              },
              {
                key: "maximum",
                label: t("pls.maxComponents"),
                control: (
                  <input
                    max={componentCeiling}
                    min={1}
                    onChange={(event) => setMaxComponents(Number(event.currentTarget.value))}
                    type="number"
                    value={maxComponents}
                  />
                ),
              },
              {
                key: "fixed",
                label: t("pls.componentCount"),
                control: (
                  <input
                    disabled={componentSelection !== "fixed"}
                    max={maxComponents}
                    min={1}
                    onChange={(event) => setNComponents(Number(event.currentTarget.value))}
                    type="number"
                    value={nComponents}
                  />
                ),
              },
              {
                key: "scale",
                label: t("pls.standardize"),
                control: (
                  <label className="doe-table-toggle">
                    <input
                      checked={scale}
                      onChange={(event) => setScale(event.currentTarget.checked)}
                      type="checkbox"
                    />
                    <span>{t("pls.standardizeHelp")}</span>
                  </label>
                ),
              },
            ]}
          />

          <div className="option-grid option-grid-wide">
            <label>
              <span>{t("pls.cvMethod")}</span>
              <select
                value={cvMethod}
                onChange={(event) =>
                  setCvMethod(event.currentTarget.value as "k_fold" | "leave_one_out")
                }
              >
                <option value="k_fold">{t("pls.kFold")}</option>
                <option value="leave_one_out">{t("pls.leaveOneOut")}</option>
              </select>
            </label>
            <label>
              <span>{t("pls.folds")}</span>
              <input
                disabled={cvMethod !== "k_fold"}
                max={10}
                min={2}
                onChange={(event) => setCvFolds(Number(event.currentTarget.value))}
                type="number"
                value={cvFolds}
              />
            </label>
            <label className="checkbox-field">
              <span>{t("pls.shuffle")}</span>
              <input
                checked={cvShuffle}
                disabled={cvMethod !== "k_fold"}
                onChange={(event) => setCvShuffle(event.currentTarget.checked)}
                type="checkbox"
              />
            </label>
            <label>
              <span>{t("pls.seed")}</span>
              <input
                disabled={cvMethod !== "k_fold" || !cvShuffle}
                onChange={(event) => setCvSeed(Number(event.currentTarget.value))}
                type="number"
                value={cvSeed}
              />
            </label>
          </div>

          <details>
            <summary>{t("pls.advanced")}</summary>
            <div className="option-grid option-grid-wide">
              <label>
                <span>{t("pls.maxIter")}</span>
                <input
                  max={10000}
                  min={1}
                  onChange={(event) => setMaxIter(Number(event.currentTarget.value))}
                  type="number"
                  value={maxIter}
                />
              </label>
              <label>
                <span>{t("pls.tolerance")}</span>
                <input
                  max={0.1}
                  min={1e-12}
                  onChange={(event) => setTolerance(Number(event.currentTarget.value))}
                  step="any"
                  type="number"
                  value={tolerance}
                />
              </label>
              <label>
                <span>{t("pls.plotLimit")}</span>
                <input
                  max={5000}
                  min={100}
                  onChange={(event) => setPlotPointLimit(Number(event.currentTarget.value))}
                  type="number"
                  value={plotPointLimit}
                />
              </label>
            </div>
          </details>

          <div className="button-row">
            <button
              className="primary-button"
              disabled={!canRun}
              onClick={() =>
                onRun({
                  responseColumnId,
                  predictorColumnIds,
                  scale,
                  componentSelection,
                  nComponents: componentSelection === "fixed" ? nComponents : null,
                  maxComponents,
                  cvMethod,
                  cvFolds,
                  cvShuffle,
                  cvSeed,
                  maxIter,
                  tolerance,
                  plotPointLimit,
                })
              }
              type="button"
            >
              {isRunningAnalysis ? t("pls.running") : t("pls.run")}
            </button>
          </div>
        </>
      )}
      {analysisResult !== null && result !== null ? <PlsResults result={result} /> : null}
    </section>
  );
}

function PlsResults({ result }: { result: PlsRegressionResult }) {
  const { t, formatNumber } = useI18n();
  const [loadingComponent, setLoadingComponent] = useState(1);
  const maxLoadingComponent = result.model_summary.selected_components;
  return (
    <div className="pls-results">
      <section className="result-section">
        <h4>{t("pls.method")}</h4>
        <dl className="result-definition-grid">
          <div><dt>{t("pls.componentSelection")}</dt><dd>{result.method.component_selection === "automatic_cv" ? t("pls.automatic") : t("pls.fixed")}</dd></div>
          <div><dt>{t("pls.cvMethod")}</dt><dd>{result.method.cv_method === "k_fold" ? `${result.method.cv_folds} ${t("pls.kFold")}` : t("pls.leaveOneOut")}</dd></div>
          <div><dt>{t("pls.standardize")}</dt><dd>{result.method.scale ? t("pls.yes") : t("pls.no")}</dd></div>
          <div><dt>{t("pls.usedRows")}</dt><dd>{formatNumber(result.sample.n_used)}</dd></div>
        </dl>
      </section>

      <section className="result-section">
        <h4>{t("pls.modelSelection")}</h4>
        <div className="table-wrap pls-selection-table-wrap">
          <table className="result-table">
            <thead><tr><th>{t("pls.components")}</th><th>{t("pls.xVariance")}</th><th>{t("pls.error")}</th><th>{t("pls.trainingR")}</th><th>{t("pls.press")}</th><th>{t("pls.predictedR")}</th><th>{t("pls.cvRmse")}</th><th>{t("pls.selected")}</th></tr></thead>
            <tbody>
              {result.component_selection.rows.map((row) => (
                <tr key={row.components} className={row.components === result.model_summary.selected_components ? "is-selected" : undefined}>
                  <td>{row.components}</td><td>{number(row.x_variance)}</td><td>{number(row.training_sse)}</td><td>{number(row.training_r_squared)}</td><td>{number(row.press)}</td><td>{number(row.predicted_r_squared)}</td><td>{number(row.cv_rmse)}</td><td>{row.components === result.model_summary.selected_components ? "✓" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="result-section">
        <h4>{t("pls.modelSelectionPlot")}</h4>
        <LineMetricChart result={result} />
      </section>

      <section className="result-section">
        <h4>{t("pls.modelSummary")}</h4>
        <dl className="result-definition-grid">
          <div><dt>{t("pls.components")}</dt><dd>{result.model_summary.selected_components}</dd></div>
          <div><dt>{t("pls.usedRows")}</dt><dd>{formatNumber(result.sample.n_used)}</dd></div>
          <div><dt>{t("pls.predictorCount")}</dt><dd>{result.sample.predictor_count}</dd></div>
          <div><dt>{t("pls.trainingR")}</dt><dd>{number(result.model_summary.training_r_squared)}</dd></div>
          <div><dt>{t("pls.predictedR")}</dt><dd>{number(result.model_summary.predicted_r_squared)}</dd></div>
          <div><dt>{t("pls.press")}</dt><dd>{number(result.model_summary.press)}</dd></div>
          <div><dt>{t("pls.cvRmse")}</dt><dd>{number(result.model_summary.cv_rmse)}</dd></div>
          <div><dt>{t("pls.xVariance")}</dt><dd>{number(result.model_summary.cumulative_x_variance)}</dd></div>
        </dl>
      </section>

      <section className="result-section">
        <h4>{t("pls.coefficients")}</h4>
        <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("pls.predictor")}</th><th>{t("pls.rawCoefficient")}</th><th>{t("pls.standardizedCoefficient")}</th><th>{t("pls.direction")}</th></tr></thead><tbody>{result.coefficients.map((coefficient) => <tr key={coefficient.column_id}><td>{coefficient.display_name}</td><td>{number(coefficient.coefficient)}</td><td>{number(coefficient.standardized_coefficient)}</td><td>{t(`pls.direction.${coefficient.direction}`)}</td></tr>)}</tbody></table></div>
      </section>

      <div className="chart-grid pls-chart-grid">
        <section className="result-section"><h4>{t("pls.responsePlot")}</h4><ResponsePlot result={result} /></section>
        <section className="result-section"><h4>{t("pls.scores")}</h4><ScorePlot result={result} /></section>
      </div>

      <section className="result-section">
        <div className="section-heading-row"><h4>{t("pls.loadings")}</h4><label><span>{t("pls.loadingComponent")}</span><select value={loadingComponent} onChange={(event) => setLoadingComponent(Number(event.currentTarget.value))}>{Array.from({ length: maxLoadingComponent }, (_value, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}</select></label></div>
        <LoadingPlot component={loadingComponent} result={result} />
      </section>

      <section className="result-section">
        <h4>{t("pls.residualDiagnostics")}</h4>
        <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("pls.row")}</th><th>{t("pls.fitted")}</th><th>{t("pls.residual")}</th><th>{t("pls.cvResidual")}</th></tr></thead><tbody>{result.diagnostics.points.slice(0, 100).map((point) => <tr key={point.row_index}><td>{point.row_index + 1}</td><td>{number(point.fitted)}</td><td>{number(point.residual)}</td><td>{number(point.cross_validated_residual)}</td></tr>)}</tbody></table></div>
      </section>

      {result.warnings.length > 0 ? (
        <section className="result-section">
          <h4>{t("pls.warnings")}</h4>
          <ul className="warning-list">
            {result.warnings.map((warning) => {
              const warningKey = PLS_WARNING_KEYS[warning as keyof typeof PLS_WARNING_KEYS];
              return (
                <li key={warning}>
                  {warningKey === undefined ? t("pls.warning.generic") : t(warningKey)}
                  <span className="cell-subtle">{warning}</span>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {result.model_manifest !== undefined ? <PlsPointPrediction result={result} /> : null}
    </div>
  );
}

function LineMetricChart({ result }: { result: PlsRegressionResult }) {
  const { t } = useI18n();
  const points = result.component_selection.rows;
  const values = points.flatMap((row) => [row.training_r_squared, row.predicted_r_squared]);
  const bounds = extent(values);
  const x = (component: number) => 54 + ((component - 1) / Math.max(1, points.length - 1)) * 540;
  const y = (value: number) => 254 - ((value - bounds[0]) / Math.max(1e-12, bounds[1] - bounds[0])) * 210;
  return <svg aria-label={t("pls.modelSelectionPlotDesc")} className="interactive-chart pls-selection-chart" role="img" viewBox="0 0 640 290"><title>{t("pls.modelSelectionPlot")}</title><desc>{t("pls.modelSelectionPlotDesc")}</desc><line className="chart-axis" x1="54" x2="594" y1="254" y2="254"/><line className="chart-axis" x1="54" x2="54" y1="44" y2="254"/><line className="pls-selected-component-line" x1={x(result.model_summary.selected_components)} x2={x(result.model_summary.selected_components)} y1="36" y2="254"/><polyline className="pls-training-line" fill="none" points={points.map((row) => `${x(row.components)},${y(row.training_r_squared)}`).join(" ")}/><polyline className="pls-cv-line" fill="none" points={points.map((row) => `${x(row.components)},${y(row.predicted_r_squared)}`).join(" ")}/>{points.map((row) => <g key={row.components}><circle aria-label={`${t("pls.components")} ${row.components}, ${t("pls.trainingR")} ${number(row.training_r_squared)}`} className="pls-training-point" cx={x(row.components)} cy={y(row.training_r_squared)} r="5" tabIndex={0}/><circle aria-label={`${t("pls.components")} ${row.components}, ${t("pls.predictedR")} ${number(row.predicted_r_squared)}`} className="pls-cv-point" cx={x(row.components)} cy={y(row.predicted_r_squared)} r="5" tabIndex={0}/><text className="chart-tick-label" textAnchor="middle" x={x(row.components)} y="275">{row.components}</text></g>)}</svg>;
}

function ResponsePlot({ result }: { result: PlsRegressionResult }) {
  const { t } = useI18n();
  const points = result.diagnostics.points;
  const values = points.flatMap((point) => [point.observed, point.fitted, point.cross_validated_fitted]);
  const bounds = extent(values);
  return <ScatterSvg ariaLabel={t("pls.responsePlotDesc")} bounds={bounds} series={[{ className: "pls-training-point", label: t("pls.fitted"), points: points.map((point) => ({ x: point.observed, y: point.fitted, label: `${t("pls.row")} ${point.row_index + 1}` })) }, { className: "pls-cv-point", label: t("pls.cvFitted"), points: points.map((point) => ({ x: point.observed, y: point.cross_validated_fitted, label: `${t("pls.row")} ${point.row_index + 1}` })) }]} showReferenceLine />;
}

function ScorePlot({ result }: { result: PlsRegressionResult }) {
  const { t } = useI18n();
  const scores = result.latent_components.x_scores;
  const points = scores.map((row, index) => ({ x: row[0] ?? 0, y: row[1] ?? 0, label: `${t("pls.row")} ${(result.latent_components.score_row_indices[index] ?? index) + 1}` }));
  return <ScatterSvg ariaLabel={t("pls.scoresPlotDesc")} bounds={extent(points.flatMap((point) => [point.x, point.y]))} series={[{ className: "pls-score-point", label: t("pls.scores"), points }]} />;
}

function LoadingPlot({ component, result }: { component: number; result: PlsRegressionResult }) {
  const { t } = useI18n();
  const values = result.predictors.map((predictor, index) => ({ label: predictor.display_name, value: result.latent_components.x_loadings[index]?.[component - 1] ?? 0 }));
  const maximum = Math.max(1e-12, ...values.map((item) => Math.abs(item.value)));
  const height = Math.max(180, values.length * 32 + 30);
  return <svg aria-label={t("pls.loadingPlotTitle", { component })} className="interactive-chart pls-loading-chart" role="img" viewBox={`0 0 640 ${height}`}><title>{t("pls.loadingPlotTitle", { component })}</title><desc>{t("pls.loadingPlotDesc")}</desc><line className="chart-axis" x1="320" x2="320" y1="10" y2={height - 10}/>{values.map((item, index) => { const width = (Math.abs(item.value) / maximum) * 230; const x = item.value >= 0 ? 320 : 320 - width; const y = 18 + index * 32; return <g key={item.label} tabIndex={0}><text className="chart-tick-label" textAnchor="end" x="80" y={y + 13}>{item.label}</text><rect aria-label={`${item.label} ${number(item.value)}`} className={item.value >= 0 ? "pls-loading-positive" : "pls-loading-negative"} height="18" width={width} x={x} y={y}/></g>; })}</svg>;
}

function ScatterSvg({ ariaLabel, bounds, series, showReferenceLine = false }: { ariaLabel: string; bounds: [number, number]; series: Array<{ className: string; label: string; points: Array<{ x: number; y: number; label: string }> }>; showReferenceLine?: boolean }) {
  const [selected, setSelected] = useState<string | null>(null);
  const x = (value: number) => 54 + ((value - bounds[0]) / Math.max(1e-12, bounds[1] - bounds[0])) * 540;
  const y = (value: number) => 254 - ((value - bounds[0]) / Math.max(1e-12, bounds[1] - bounds[0])) * 210;
  return <><svg aria-label={ariaLabel} className="interactive-chart pls-scatter-chart" role="img" viewBox="0 0 640 290"><title>{ariaLabel}</title><desc>{ariaLabel}</desc><line className="chart-axis" x1="54" x2="594" y1="254" y2="254"/><line className="chart-axis" x1="54" x2="54" y1="44" y2="254"/>{showReferenceLine ? <line className="chart-reference-line" x1="54" x2="594" y1="254" y2="44"/> : null}{series.flatMap((item) => item.points.map((point, index) => { const key = `${item.label}-${index}`; return <circle aria-label={`${item.label}, ${point.label}, ${number(point.x)}, ${number(point.y)}`} className={`${item.className}${selected === key ? " is-selected" : ""}`} cx={x(point.x)} cy={y(point.y)} key={key} onClick={() => setSelected(key)} onFocus={() => setSelected(key)} r="5" tabIndex={0}/>; }))}</svg><div className="chart-legend">{series.map((item) => <span key={item.label} className={item.className}>{item.label}</span>)}</div></>;
}

function PlsPointPrediction({ result }: { result: PlsRegressionResult }) {
  const { t, locale } = useI18n();
  const nextId = useRef(2);
  const [rows, setRows] = useState<PredictionRowDraft[]>([emptyPredictionRow("pls-row-1", result)]);
  const [prediction, setPrediction] = useState<PlsPointPredictionResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const manifest = result.model_manifest;
  const valid = rows.every((row) => result.predictors.every((predictor) => finiteInput(row.values[predictor.column_id])));

  useEffect(() => {
    setRows([emptyPredictionRow("pls-row-1", result)]);
    setPrediction(null);
    setError(null);
  }, [manifest?.model_id, result]);

  async function run(): Promise<void> {
    if (manifest === undefined || !valid) return;
    setIsRunning(true); setError(null); setPrediction(null);
    try {
      setPrediction(await createPlsPointPredictions(manifest.model_id, { expected_model_manifest_sha256: manifest.manifest_sha256, rows: rows.map((row) => ({ client_row_id: row.id, values: Object.fromEntries(result.predictors.map((predictor) => [predictor.column_id, Number(row.values[predictor.column_id])])) })) }));
    } catch (caught) {
      const display = localizedErrorDisplay(caught, locale);
      setError(`${display.message} (${display.code})`);
    } finally { setIsRunning(false); }
  }

  return <section className="result-section pls-point-prediction"><h4>{t("pls.pointPrediction")}</h4><p>{t("pls.pointPredictionHelp")}</p>{!valid ? <div className="notice-box warning">{t("pls.inputRequired")}</div> : null}{error !== null ? <div className="notice-box error">{error}</div> : null}<div className="table-wrap"><table className="result-table pls-prediction-grid"><thead><tr><th>{t("pls.row")}</th>{result.predictors.map((predictor) => <th key={predictor.column_id}>{predictor.display_name}</th>)}<th>{t("pls.predictedValue")}</th><th>{t("pls.status")}</th><th /></tr></thead><tbody>{rows.map((row, index) => { const predicted = prediction?.rows.find((item) => item.client_row_id === row.id); return <tr key={row.id}><td>{index + 1}</td>{result.predictors.map((predictor) => <td key={predictor.column_id}><input aria-label={`${predictor.display_name} ${index + 1}`} inputMode="decimal" onChange={(event) => { const value = event.currentTarget.value; setRows((current) => current.map((item) => item.id === row.id ? { ...item, values: { ...item.values, [predictor.column_id]: value } } : item)); setPrediction(null); }} type="text" value={row.values[predictor.column_id] ?? ""}/></td>)}<td>{predicted === undefined ? "-" : number(predicted.predicted_value)}</td><td>{predicted?.warnings.includes("prediction_extrapolation_risk") ? t("pls.extrapolation") : predicted === undefined ? "-" : t("pls.ready")}</td><td><button aria-label={`${t("pls.deleteRow")} ${index + 1}`} onClick={() => setRows((current) => current.length === 1 ? [emptyPredictionRow(`pls-row-${nextId.current++}`, result)] : current.filter((item) => item.id !== row.id))} type="button">{t("pls.deleteRow")}</button></td></tr>; })}</tbody></table></div><div className="button-row"><button onClick={() => setRows((current) => [...current, emptyPredictionRow(`pls-row-${nextId.current++}`, result)])} type="button">{t("pls.addRow")}</button><button className="primary-button" disabled={!valid || isRunning || manifest === undefined} onClick={() => void run()} type="button">{isRunning ? t("pls.predicting") : t("pls.runPrediction")}</button></div></section>;
}

function emptyPredictionRow(id: string, result: PlsRegressionResult): PredictionRowDraft {
  return { id, values: Object.fromEntries(result.predictors.map((predictor) => [predictor.column_id, ""])) };
}

function finiteInput(value: string | undefined): boolean {
  return value !== undefined && value.trim().length > 0 && Number.isFinite(Number(value));
}

function isNumericColumn(column: DatasetColumnResponse): boolean {
  return column.role !== "id" && (column.data_type === "integer" || column.data_type === "decimal");
}

function extent(values: number[]): [number, number] {
  const finite = values.filter(Number.isFinite);
  if (finite.length === 0) return [0, 1];
  const low = Math.min(...finite); const high = Math.max(...finite);
  if (low === high) return [low - 1, high + 1];
  const padding = (high - low) * 0.05;
  return [low - padding, high + padding];
}

function number(value: number): string {
  return Number.isFinite(value) ? Number(value.toPrecision(6)).toString() : "-";
}
