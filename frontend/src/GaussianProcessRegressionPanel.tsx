import { useEffect, useMemo, useRef, useState } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  GaussianProcessPointPredictionResponse,
  GaussianProcessRegressionResult,
} from "./api";
import { createGaussianProcessPointPredictions } from "./api/regression";
import { CompactSettingsTable } from "./components/CompactSettingsTable";
import { localizedErrorDisplay } from "./i18n/errorMessages";
import { useI18n } from "./i18n/LocaleProvider";

export interface GaussianProcessRunConfig {
  responseColumnId: string;
  predictorColumnIds: string[];
  kernelPreset: "matern_5_2_ard" | "matern_3_2_ard" | "rbf_ard" | "rational_quadratic";
  noiseMode: "estimate" | "fixed" | "near_noiseless";
  fixedNoiseStandardDeviation: number | null;
  standardizePredictors: boolean;
  normalizeResponse: boolean;
  validationMethod: "k_fold" | "leave_one_out" | "none";
  cvFolds: number;
  cvShuffle: boolean;
  randomSeed: number;
  jitter: number;
  optimizerRestarts: number;
  cvOptimizerRestarts: number;
  plotPointLimit: number;
  profilePoints: number;
  surfaceGridSize: number;
  timeBudgetSeconds: number;
}

interface Props {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: GaussianProcessRegressionResult | null;
  version: DatasetVersionResponse | null;
  onRun: (config: GaussianProcessRunConfig) => void;
}

interface PredictionRowDraft {
  id: string;
  values: Record<string, string>;
}

const warningKeys = {
  missing_values_excluded: "gp.warning.missing",
  gp_hyperparameter_near_bound: "gp.warning.bound",
  gp_length_scale_near_bound: "gp.warning.bound",
  gp_noise_level_near_bound: "gp.warning.bound",
  gp_amplitude_near_bound: "gp.warning.bound",
  gp_negative_cv_r_squared: "gp.warning.negativeR",
  gp_interval_undercoverage: "gp.warning.coverage",
  gp_training_cv_gap: "gp.warning.gap",
  gp_uncertainty_conditional_on_kernel: "gp.warning.conditional",
  gp_predictive_not_causal: "gp.warning.notCausal",
} as const;

export function GaussianProcessRegressionPanel({
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
  const [kernelPreset, setKernelPreset] = useState<GaussianProcessRunConfig["kernelPreset"]>(
    "matern_5_2_ard",
  );
  const [noiseMode, setNoiseMode] = useState<GaussianProcessRunConfig["noiseMode"]>("estimate");
  const [fixedNoiseStandardDeviation, setFixedNoiseStandardDeviation] = useState(0.1);
  const [standardizePredictors, setStandardizePredictors] = useState(true);
  const [normalizeResponse, setNormalizeResponse] = useState(true);
  const [validationMethod, setValidationMethod] =
    useState<GaussianProcessRunConfig["validationMethod"]>("k_fold");
  const [cvFolds, setCvFolds] = useState(5);
  const [cvShuffle, setCvShuffle] = useState(true);
  const [randomSeed, setRandomSeed] = useState(20260829);
  const [jitter, setJitter] = useState(1e-8);
  const [optimizerRestarts, setOptimizerRestarts] = useState(3);
  const [cvOptimizerRestarts, setCvOptimizerRestarts] = useState(0);
  const [plotPointLimit, setPlotPointLimit] = useState(1000);
  const [profilePoints, setProfilePoints] = useState(50);
  const [surfaceGridSize, setSurfaceGridSize] = useState(25);
  const [timeBudgetSeconds, setTimeBudgetSeconds] = useState(120);

  useEffect(() => {
    setResponseColumnId("");
    setPredictorColumnIds([]);
  }, [version?.version_id]);

  const canRun =
    version !== null &&
    responseColumnId.length > 0 &&
    predictorColumnIds.length >= 1 &&
    predictorColumnIds.length <= 12 &&
    !predictorColumnIds.includes(responseColumnId) &&
    (noiseMode !== "fixed" || fixedNoiseStandardDeviation > 0) &&
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
    <section className="analysis-run-panel gp-regression-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">{t("gp.datasetRequired")}</div>
      ) : (
        <>
          <div className="notice-box">
            <p>{t("gp.description")}</p>
            <p>{t("gp.assumptionNotice")}</p>
          </div>
          <div className="option-grid option-grid-wide">
            <label>
              <span>{t("gp.response")}</span>
              <select
                value={responseColumnId}
                onChange={(event) => setResponseColumnId(event.currentTarget.value)}
              >
                <option value="">{t("gp.select")}</option>
                {numericColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <fieldset className="checkbox-field gp-predictor-field">
              <legend>{t("gp.predictors")}</legend>
              <small>{t("gp.predictorsHelp")}</small>
              <div className="checkbox-grid">
                {numericColumns
                  .filter((column) => column.column_id !== responseColumnId)
                  .map((column) => (
                    <label key={column.column_id}>
                      <input
                        checked={predictorColumnIds.includes(column.column_id)}
                        disabled={
                          !predictorColumnIds.includes(column.column_id) &&
                          predictorColumnIds.length >= 12
                        }
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
            ariaLabel={t("gp.basicSettings")}
            className="gp-settings-table"
            fields={[
              {
                key: "kernel",
                label: t("gp.kernel"),
                control: (
                  <select
                    value={kernelPreset}
                    onChange={(event) =>
                      setKernelPreset(event.currentTarget.value as GaussianProcessRunConfig["kernelPreset"])
                    }
                  >
                    <option value="matern_5_2_ard">{t("gp.kernel.matern52")}</option>
                    <option value="matern_3_2_ard">{t("gp.kernel.matern32")}</option>
                    <option value="rbf_ard">{t("gp.kernel.rbf")}</option>
                    <option value="rational_quadratic">{t("gp.kernel.rq")}</option>
                  </select>
                ),
              },
              {
                key: "noise",
                label: t("gp.noiseMode"),
                control: (
                  <select
                    value={noiseMode}
                    onChange={(event) =>
                      setNoiseMode(event.currentTarget.value as GaussianProcessRunConfig["noiseMode"])
                    }
                  >
                    <option value="estimate">{t("gp.noise.estimate")}</option>
                    <option value="fixed">{t("gp.noise.fixed")}</option>
                    <option value="near_noiseless">{t("gp.noise.nearNoiseless")}</option>
                  </select>
                ),
              },
              {
                key: "standardize",
                label: t("gp.standardize"),
                control: (
                  <label className="doe-table-toggle">
                    <input
                      checked={standardizePredictors}
                      onChange={(event) => setStandardizePredictors(event.currentTarget.checked)}
                      type="checkbox"
                    />
                    <span>{t("gp.standardize")}</span>
                  </label>
                ),
              },
              {
                key: "normalize",
                label: t("gp.normalizeResponse"),
                control: (
                  <label className="doe-table-toggle">
                    <input
                      checked={normalizeResponse}
                      onChange={(event) => setNormalizeResponse(event.currentTarget.checked)}
                      type="checkbox"
                    />
                    <span>{t("gp.normalizeResponse")}</span>
                  </label>
                ),
              },
            ]}
          />

          {noiseMode === "fixed" ? (
            <label className="gp-fixed-noise-field">
              <span>{t("gp.fixedNoise")}</span>
              <input
                min="0.000000000001"
                onChange={(event) =>
                  setFixedNoiseStandardDeviation(Number(event.currentTarget.value))
                }
                step="any"
                type="number"
                value={fixedNoiseStandardDeviation}
              />
            </label>
          ) : null}

          <div className="option-grid option-grid-wide">
            <label>
              <span>{t("gp.validation")}</span>
              <select
                value={validationMethod}
                onChange={(event) =>
                  setValidationMethod(
                    event.currentTarget.value as GaussianProcessRunConfig["validationMethod"],
                  )
                }
              >
                <option value="k_fold">{t("gp.validation.kFold")}</option>
                <option value="leave_one_out">{t("gp.validation.loo")}</option>
                <option value="none">{t("gp.validation.none")}</option>
              </select>
            </label>
            <label>
              <span>{t("gp.folds")}</span>
              <input
                disabled={validationMethod !== "k_fold"}
                max={10}
                min={2}
                onChange={(event) => setCvFolds(Number(event.currentTarget.value))}
                type="number"
                value={cvFolds}
              />
            </label>
            <label className="checkbox-field">
              <span>{t("gp.shuffle")}</span>
              <input
                checked={cvShuffle}
                disabled={validationMethod !== "k_fold"}
                onChange={(event) => setCvShuffle(event.currentTarget.checked)}
                type="checkbox"
              />
            </label>
            <label>
              <span>{t("gp.seed")}</span>
              <input
                onChange={(event) => setRandomSeed(Number(event.currentTarget.value))}
                type="number"
                value={randomSeed}
              />
            </label>
          </div>

          <details>
            <summary>{t("gp.advanced")}</summary>
            <div className="option-grid option-grid-wide gp-advanced-grid">
              <NumberField label={t("gp.jitter")} min={1e-12} step="any" value={jitter} onChange={setJitter} />
              <NumberField label={t("gp.finalRestarts")} max={10} min={0} value={optimizerRestarts} onChange={setOptimizerRestarts} />
              <NumberField label={t("gp.cvRestarts")} max={1} min={0} value={cvOptimizerRestarts} onChange={setCvOptimizerRestarts} />
              <NumberField label={t("gp.plotLimit")} max={2000} min={100} value={plotPointLimit} onChange={setPlotPointLimit} />
              <NumberField label={t("gp.profilePoints")} max={80} min={10} value={profilePoints} onChange={setProfilePoints} />
              <NumberField label={t("gp.surfaceGrid")} max={40} min={10} value={surfaceGridSize} onChange={setSurfaceGridSize} />
              <NumberField label={t("gp.timeBudget")} max={600} min={5} value={timeBudgetSeconds} onChange={setTimeBudgetSeconds} />
            </div>
          </details>

          {filterValidationError !== null ? (
            <div className="notice-box error">{filterValidationError}</div>
          ) : null}
          <div className="button-row">
            <button
              className="primary-button"
              disabled={!canRun}
              onClick={() =>
                onRun({
                  responseColumnId,
                  predictorColumnIds,
                  kernelPreset,
                  noiseMode,
                  fixedNoiseStandardDeviation:
                    noiseMode === "fixed" ? fixedNoiseStandardDeviation : null,
                  standardizePredictors,
                  normalizeResponse,
                  validationMethod,
                  cvFolds,
                  cvShuffle,
                  randomSeed,
                  jitter,
                  optimizerRestarts,
                  cvOptimizerRestarts,
                  plotPointLimit,
                  profilePoints,
                  surfaceGridSize,
                  timeBudgetSeconds,
                })
              }
              type="button"
            >
              {isRunningAnalysis ? t("gp.running") : t("gp.run")}
            </button>
          </div>
        </>
      )}

      {analysisResult !== null && result !== null ? <GaussianProcessResults result={result} /> : null}
    </section>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max?: number;
  step?: string;
  onChange: (value: number) => void;
}) {
  return (
    <label>
      <span>{label}</span>
      <input
        max={max}
        min={min}
        onChange={(event) => onChange(Number(event.currentTarget.value))}
        step={step}
        type="number"
        value={value}
      />
    </label>
  );
}

function GaussianProcessResults({ result }: { result: GaussianProcessRegressionResult }) {
  const { t, formatNumber, formatPercent } = useI18n();
  const metric = (value: number | null) =>
    value === null ? "-" : formatNumber(value, { maximumSignificantDigits: 7 });
  return (
    <div className="gp-results">
      <section className="result-section">
        <h4>{t("gp.method")}</h4>
        <dl className="result-definition-grid">
          <Metric label={t("gp.kernel")} value={kernelLabel(result.method.kernel_preset, t)} />
          <Metric label={t("gp.noiseMode")} value={t(`gp.noise.${noiseKey(result.method.noise_mode)}`)} />
          <Metric label={t("gp.validation")} value={validationLabel(result.method.validation_method, t)} />
          <Metric label={t("gp.usedRows")} value={String(result.sample.n_used)} />
          <Metric label={t("gp.excludedRows")} value={String(result.sample.n_excluded)} />
          <Metric label={t("gp.predictorCount")} value={String(result.sample.predictor_count)} />
          <Metric label={t("gp.elapsed")} value={`${metric(result.method.elapsed_seconds)} s`} />
        </dl>
      </section>

      <section className="result-section">
        <h4>{t("gp.modelSummary")}</h4>
        <dl className="result-definition-grid">
          <Metric label={t("gp.trainingR")} value={metric(result.model_summary.training_r_squared)} />
          <Metric label={t("gp.rmse")} value={metric(result.model_summary.training_rmse)} />
          <Metric label={t("gp.mae")} value={metric(result.model_summary.training_mae)} />
          <Metric label={t("gp.predictedR")} value={metric(result.model_summary.predicted_r_squared)} />
          <Metric label={t("gp.press")} value={metric(result.model_summary.press)} />
          <Metric label={t("gp.cvRmse")} value={metric(result.model_summary.cv_rmse)} />
          <Metric label={t("gp.cvMae")} value={metric(result.model_summary.cv_mae)} />
          <Metric label={t("gp.nlpd")} value={metric(result.model_summary.negative_log_predictive_density)} />
          <Metric
            label={t("gp.coverage")}
            value={
              result.model_summary.interval_coverage_95 === null
                ? "-"
                : formatPercent(result.model_summary.interval_coverage_95, 1)
            }
          />
          <Metric label={t("gp.intervalWidth")} value={metric(result.model_summary.mean_predictive_interval_width)} />
          <Metric label={t("gp.lml")} value={metric(result.model_summary.log_marginal_likelihood)} />
          <Metric label={t("gp.noiseSd")} value={metric(result.model_summary.fitted_noise_standard_deviation)} />
        </dl>
      </section>

      <section className="result-section">
        <h4>{t("gp.kernelSummary")}</h4>
        <p className="cell-subtle">{result.kernel.fitted_kernel}</p>
        <div className="table-wrap">
          <table className="result-table gp-hyperparameter-table">
            <thead><tr><th>{t("gp.parameter")}</th><th>{t("gp.estimate")}</th><th>{t("gp.lowerBound")}</th><th>{t("gp.upperBound")}</th><th>{t("gp.status")}</th></tr></thead>
            <tbody>
              {result.kernel.parameters.map((parameter) => (
                <tr key={`${parameter.parameter}-${parameter.column_id ?? "model"}`}>
                  <td>{parameter.column_id === null ? parameter.parameter : `${parameter.column_id} ${parameter.parameter}`}</td>
                  <td>{metric(parameter.estimate)}</td>
                  <td>{metric(parameter.lower_bound)}</td>
                  <td>{metric(parameter.upper_bound)}</td>
                  <td>{parameter.near_bound ? t("gp.nearBound") : t("gp.inRange")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="chart-grid gp-chart-grid">
        <section className="result-section"><h4>{t("gp.observedFitted")}</h4><GpScatter result={result} mode="fitted" /></section>
        {result.method.validation_method !== "none" ? <section className="result-section"><h4>{t("gp.observedCv")}</h4><GpScatter result={result} mode="cv" /></section> : null}
        <section className="result-section"><h4>{t("gp.residualDiagnostics")}</h4><GpResidualChart result={result} /></section>
        <section className="result-section"><h4>{t("gp.uncertaintyDiagnostics")}</h4><GpUncertaintyChart result={result} /></section>
      </div>

      <section className="result-section">
        <h4>{t("gp.conditionalProfiles")}</h4>
        <p>{t("gp.profileNotice")}</p>
        <div className="chart-grid gp-chart-grid">
          {result.conditional_profiles.map((profile) => <GpProfileChart key={profile.column_id} profile={profile} />)}
        </div>
      </section>

      {result.two_predictor_surface !== null ? <GpSurfaceChart result={result} /> : null}

      {result.warnings.length > 0 ? (
        <section className="result-section">
          <h4>{t("gp.warnings")}</h4>
          <ul className="warning-list">
            {result.warnings.map((warning) => (
              <li key={warning}>
                {t(warningKeys[warning as keyof typeof warningKeys] ?? "gp.warning.generic")}
                <span className="cell-subtle">{warning}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {result.model_manifest !== undefined ? <GaussianProcessPrediction result={result} /> : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function GpScatter({ result, mode }: { result: GaussianProcessRegressionResult; mode: "fitted" | "cv" }) {
  const { t, formatNumber } = useI18n();
  const points = result.diagnostics.points
    .map((point) => ({ x: point.observed, y: mode === "fitted" ? point.fitted : point.cross_validated_fitted, row: point.row_index }))
    .filter((point): point is { x: number; y: number; row: number } => point.y !== null);
  const bounds = extent(points.flatMap((point) => [point.x, point.y]));
  const x = scale(bounds, 54, 594);
  const y = scale(bounds, 254, 44);
  const title = mode === "fitted" ? t("gp.observedFitted") : t("gp.observedCv");
  return <svg aria-label={title} className="interactive-chart gp-scatter-chart" role="img" viewBox="0 0 640 290"><title>{title}</title><desc>{title}</desc><line className="chart-axis" x1="54" x2="594" y1="254" y2="254"/><line className="chart-axis" x1="54" x2="54" y1="44" y2="254"/><line className="chart-reference-line" x1="54" x2="594" y1="254" y2="44"/>{points.map((point) => <circle aria-label={`${t("gp.row")} ${point.row + 1}, ${t("gp.observed")} ${formatNumber(point.x)}, ${mode === "fitted" ? t("gp.fitted") : t("gp.cvFitted")} ${formatNumber(point.y)}`} className="gp-chart-point" cx={x(point.x)} cy={y(point.y)} key={point.row} r="5" tabIndex={0}/>)}</svg>;
}

function GpResidualChart({ result }: { result: GaussianProcessRegressionResult }) {
  const { t, formatNumber } = useI18n();
  const xBounds = extent(result.diagnostics.points.map((point) => point.fitted));
  const yBounds = extent(result.diagnostics.points.map((point) => point.residual).concat(0));
  const x = scale(xBounds, 54, 594); const y = scale(yBounds, 254, 44);
  return <svg aria-label={t("gp.residualDiagnostics")} className="interactive-chart gp-scatter-chart" role="img" viewBox="0 0 640 290"><title>{t("gp.residualDiagnostics")}</title><desc>{t("gp.residualDiagnostics")}</desc><line className="chart-axis" x1="54" x2="594" y1="254" y2="254"/><line className="chart-axis" x1="54" x2="54" y1="44" y2="254"/><line className="chart-reference-line" x1="54" x2="594" y1={y(0)} y2={y(0)}/>{result.diagnostics.points.map((point) => <circle aria-label={`${t("gp.row")} ${point.row_index + 1}, ${t("gp.fitted")} ${formatNumber(point.fitted)}, ${t("gp.residual")} ${formatNumber(point.residual)}`} className="gp-chart-point" cx={x(point.fitted)} cy={y(point.residual)} key={point.row_index} r="5" tabIndex={0}/>)}</svg>;
}

function GpUncertaintyChart({ result }: { result: GaussianProcessRegressionResult }) {
  const { t, formatNumber } = useI18n();
  const maximum = Math.max(1e-12, ...result.diagnostics.points.map((point) => point.predictive_standard_deviation));
  const x = (index: number) => 54 + (index / Math.max(1, result.diagnostics.points.length - 1)) * 540;
  const y = (value: number) => 254 - (value / maximum) * 210;
  return <svg aria-label={t("gp.uncertaintyDiagnostics")} className="interactive-chart gp-scatter-chart" role="img" viewBox="0 0 640 290"><title>{t("gp.uncertaintyDiagnostics")}</title><desc>{t("gp.uncertaintyDiagnostics")}</desc><line className="chart-axis" x1="54" x2="594" y1="254" y2="254"/><line className="chart-axis" x1="54" x2="54" y1="44" y2="254"/>{result.diagnostics.points.map((point, index) => <circle aria-label={`${t("gp.row")} ${point.row_index + 1}, ${t("gp.predictiveSd")} ${formatNumber(point.predictive_standard_deviation)}`} className="gp-uncertainty-point" cx={x(index)} cy={y(point.predictive_standard_deviation)} key={point.row_index} r="5" tabIndex={0}/>)}</svg>;
}

function GpProfileChart({ profile }: { profile: GaussianProcessRegressionResult["conditional_profiles"][number] }) {
  const { t, formatNumber } = useI18n();
  const xBounds = extent(profile.points.map((point) => point.value));
  const yBounds = extent(profile.points.flatMap((point) => [point.predictive_interval_95.lower, point.predictive_interval_95.upper]));
  const x = scale(xBounds, 54, 594); const y = scale(yBounds, 254, 44);
  const band = [...profile.points.map((point) => `${x(point.value)},${y(point.predictive_interval_95.lower)}`), ...profile.points.slice().reverse().map((point) => `${x(point.value)},${y(point.predictive_interval_95.upper)}`)].join(" ");
  return <figure className="gp-profile-chart"><figcaption>{profile.display_name}</figcaption><svg aria-label={`${t("gp.conditionalProfiles")}: ${profile.display_name}`} className="interactive-chart" role="img" viewBox="0 0 640 290"><title>{profile.display_name}</title><desc>{t("gp.profileNotice")}</desc><line className="chart-axis" x1="54" x2="594" y1="254" y2="254"/><line className="chart-axis" x1="54" x2="54" y1="44" y2="254"/><polygon className="gp-profile-band" points={band}/><polyline className="gp-profile-line" fill="none" points={profile.points.map((point) => `${x(point.value)},${y(point.predicted_mean)}`).join(" ")}/>{profile.points.filter((_point, index) => index % Math.max(1, Math.floor(profile.points.length / 12)) === 0).map((point) => <circle aria-label={`${profile.display_name} ${formatNumber(point.value)}, ${t("gp.predictedMean")} ${formatNumber(point.predicted_mean)}`} className="gp-profile-point" cx={x(point.value)} cy={y(point.predicted_mean)} key={point.value} r="4" tabIndex={0}/>)}</svg></figure>;
}

function GpSurfaceChart({ result }: { result: GaussianProcessRegressionResult }) {
  const { t, locale, formatNumber } = useI18n();
  const [view, setView] = useState<"mean" | "uncertainty">("mean");
  const initialSurface = result.two_predictor_surface;
  const [xColumnId, setXColumnId] = useState(initialSurface?.x_column_id ?? "");
  const [yColumnId, setYColumnId] = useState(initialSurface?.y_column_id ?? "");
  const [surface, setSurface] = useState(initialSurface);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const manifest = result.model_manifest;

  useEffect(() => {
    setXColumnId(initialSurface?.x_column_id ?? "");
    setYColumnId(initialSurface?.y_column_id ?? "");
    setSurface(initialSurface);
    setError(null);
  }, [initialSurface, manifest?.model_id]);

  if (surface === null || initialSurface === null) return null;
  const requestedGridSize = initialSurface.grid_size;

  async function generateSurface(): Promise<void> {
    if (manifest === undefined || xColumnId === yColumnId) return;
    const gridSize = Math.min(40, requestedGridSize);
    const xRange = result.training_ranges.find((item) => item.column_id === xColumnId);
    const yRange = result.training_ranges.find((item) => item.column_id === yColumnId);
    if (xRange === undefined || yRange === undefined) return;
    const rows: Array<{ client_row_id: string; values: Record<string, number> }> = [];
    for (let yIndex = 0; yIndex < gridSize; yIndex += 1) {
      const y = interpolate(yRange.minimum, yRange.maximum, yIndex, gridSize);
      for (let xIndex = 0; xIndex < gridSize; xIndex += 1) {
        const x = interpolate(xRange.minimum, xRange.maximum, xIndex, gridSize);
        rows.push({
          client_row_id: `surface-${yIndex}-${xIndex}`,
          values: Object.fromEntries(
            result.training_ranges.map((item) => [
              item.column_id,
              item.column_id === xColumnId ? x : item.column_id === yColumnId ? y : item.median,
            ]),
          ),
        });
      }
    }
    setIsGenerating(true);
    setError(null);
    try {
      const response = await createGaussianProcessPointPredictions(manifest.model_id, {
        expected_model_manifest_sha256: manifest.manifest_sha256,
        rows,
      });
      setSurface({
        x_column_id: xColumnId,
        x_display_name: xRange.display_name,
        y_column_id: yColumnId,
        y_display_name: yRange.display_name,
        grid_size: gridSize,
        fixed_values: result.training_ranges.map((item) => item.median),
        points: response.rows.map((row, index) => ({
          x: rows[index].values[xColumnId],
          y: rows[index].values[yColumnId],
          predicted_mean: row.predicted_mean,
          predictive_standard_deviation: row.predictive_standard_deviation,
        })),
      });
    } catch (caught) {
      const display = localizedErrorDisplay(caught, locale);
      setError(`${display.message} (${display.code})`);
    } finally {
      setIsGenerating(false);
    }
  }

  const values = surface.points.map((point) => view === "mean" ? point.predicted_mean : point.predictive_standard_deviation);
  const bounds = extent(values);
  const cell = 500 / surface.grid_size;
  return <section className="result-section"><div className="section-heading-row"><h4>{t("gp.surface")}</h4><div className="segmented-control"><button aria-pressed={view === "mean"} onClick={() => setView("mean")} type="button">{t("gp.surfaceMean")}</button><button aria-pressed={view === "uncertainty"} onClick={() => setView("uncertainty")} type="button">{t("gp.surfaceUncertainty")}</button></div></div><p>{t("gp.surfaceNotice")}</p><div className="gp-surface-controls"><label><span>{t("gp.surfaceX")}</span><select onChange={(event) => setXColumnId(event.currentTarget.value)} value={xColumnId}>{result.predictors.map((predictor) => <option disabled={predictor.column_id === yColumnId} key={predictor.column_id} value={predictor.column_id}>{predictor.display_name}</option>)}</select></label><label><span>{t("gp.surfaceY")}</span><select onChange={(event) => setYColumnId(event.currentTarget.value)} value={yColumnId}>{result.predictors.map((predictor) => <option disabled={predictor.column_id === xColumnId} key={predictor.column_id} value={predictor.column_id}>{predictor.display_name}</option>)}</select></label><button disabled={manifest === undefined || xColumnId === yColumnId || isGenerating} onClick={() => void generateSurface()} type="button">{isGenerating ? t("gp.generatingSurface") : t("gp.generateSurface")}</button></div>{error !== null ? <div className="notice-box error" role="alert">{error}</div> : null}<p>{surface.y_display_name} vs {surface.x_display_name}</p><svg aria-label={t(view === "mean" ? "gp.surfaceMean" : "gp.surfaceUncertainty")} className="interactive-chart gp-surface-chart" role="img" viewBox="0 0 620 560"><title>{t("gp.surface")}</title><desc>{t("gp.surfaceNotice")}</desc>{surface.points.map((point, index) => { const normalized = (values[index] - bounds[0]) / Math.max(1e-12, bounds[1] - bounds[0]); const row = Math.floor(index / surface.grid_size); const column = index % surface.grid_size; return <rect aria-label={`${surface.x_display_name} ${formatNumber(point.x)}, ${surface.y_display_name} ${formatNumber(point.y)}, ${formatNumber(values[index])}`} className="gp-surface-cell" fill={`hsl(${220 - normalized * 190} 70% ${82 - normalized * 35}%)`} height={cell + 0.5} key={`${point.x}-${point.y}`} tabIndex={0} width={cell + 0.5} x={70 + column * cell} y={20 + (surface.grid_size - row - 1) * cell}/>; })}<text className="chart-axis-label" textAnchor="middle" x="320" y="545">{surface.x_display_name}</text><text className="chart-axis-label" textAnchor="middle" transform="rotate(-90 18 270)" x="18" y="270">{surface.y_display_name}</text></svg></section>;
}

function GaussianProcessPrediction({ result }: { result: GaussianProcessRegressionResult }) {
  const { t, locale, formatNumber } = useI18n();
  const nextId = useRef(2);
  const [rows, setRows] = useState<PredictionRowDraft[]>([emptyPredictionRow("gp-row-1", result)]);
  const [prediction, setPrediction] = useState<GaussianProcessPointPredictionResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const manifest = result.model_manifest;
  const valid = rows.every((row) => result.predictors.every((predictor) => finiteInput(row.values[predictor.column_id])));
  useEffect(() => { setRows([emptyPredictionRow("gp-row-1", result)]); setPrediction(null); setError(null); }, [manifest?.model_id, result]);
  async function run(): Promise<void> {
    if (manifest === undefined || !valid) return;
    setIsRunning(true); setError(null); setPrediction(null);
    try {
      setPrediction(await createGaussianProcessPointPredictions(manifest.model_id, { expected_model_manifest_sha256: manifest.manifest_sha256, rows: rows.map((row) => ({ client_row_id: row.id, values: Object.fromEntries(result.predictors.map((predictor) => [predictor.column_id, Number(row.values[predictor.column_id])])) })) }));
    } catch (caught) {
      const display = localizedErrorDisplay(caught, locale); setError(`${display.message} (${display.code})`);
    } finally { setIsRunning(false); }
  }
  const interval = (value: { lower: number; upper: number } | undefined) => value === undefined ? "-" : `[${formatNumber(value.lower)}, ${formatNumber(value.upper)}]`;
  return <section className="result-section gp-point-prediction"><h4>{t("gp.pointPrediction")}</h4><p>{t("gp.pointPredictionHelp")}</p>{!valid ? <div className="notice-box warning">{t("gp.inputRequired")}</div> : null}{error !== null ? <div className="notice-box error">{error}</div> : null}<div className="table-wrap"><table className="result-table gp-prediction-grid"><thead><tr><th>{t("gp.row")}</th>{result.predictors.map((predictor) => <th key={predictor.column_id}>{predictor.display_name}</th>)}<th>{t("gp.predictedMean")}</th><th>{t("gp.latentSd")}</th><th>{t("gp.latentInterval")}</th><th>{t("gp.predictiveSd")}</th><th>{t("gp.predictiveInterval")}</th><th>{t("gp.status")}</th><th /></tr></thead><tbody>{rows.map((row, index) => { const predicted = prediction?.rows.find((item) => item.client_row_id === row.id); return <tr key={row.id}><td>{index + 1}</td>{result.predictors.map((predictor) => <td key={predictor.column_id}><input aria-label={`${predictor.display_name} ${index + 1}`} inputMode="decimal" onChange={(event) => { const value = event.currentTarget.value; setRows((current) => current.map((item) => item.id === row.id ? { ...item, values: { ...item.values, [predictor.column_id]: value } } : item)); setPrediction(null); }} type="text" value={row.values[predictor.column_id] ?? ""}/></td>)}<td>{predicted === undefined ? "-" : formatNumber(predicted.predicted_mean)}</td><td>{predicted === undefined ? "-" : formatNumber(predicted.latent_standard_deviation)}</td><td>{interval(predicted?.latent_interval_95)}</td><td>{predicted === undefined ? "-" : formatNumber(predicted.predictive_standard_deviation)}</td><td>{interval(predicted?.predictive_interval_95)}</td><td>{predicted?.warnings.includes("gp_extrapolation") ? t("gp.extrapolation") : predicted === undefined ? "-" : t("gp.ready")}</td><td><button aria-label={`${t("gp.deleteRow")} ${index + 1}`} onClick={() => setRows((current) => current.length === 1 ? [emptyPredictionRow(`gp-row-${nextId.current++}`, result)] : current.filter((item) => item.id !== row.id))} type="button">{t("gp.deleteRow")}</button></td></tr>; })}</tbody></table></div><div className="button-row"><button onClick={() => setRows((current) => [...current, emptyPredictionRow(`gp-row-${nextId.current++}`, result)])} type="button">{t("gp.addRow")}</button><button className="primary-button" disabled={!valid || isRunning || manifest === undefined} onClick={() => void run()} type="button">{isRunning ? t("gp.predicting") : t("gp.runPrediction")}</button></div></section>;
}

function emptyPredictionRow(id: string, result: GaussianProcessRegressionResult): PredictionRowDraft { return { id, values: Object.fromEntries(result.predictors.map((predictor) => [predictor.column_id, ""])) }; }
function finiteInput(value: string | undefined): boolean { return value !== undefined && value.trim().length > 0 && Number.isFinite(Number(value)); }
function isNumericColumn(column: DatasetColumnResponse): boolean { return column.role !== "id" && (column.data_type === "integer" || column.data_type === "decimal"); }
function extent(values: number[]): [number, number] { const finite = values.filter(Number.isFinite); if (finite.length === 0) return [0, 1]; const low = Math.min(...finite); const high = Math.max(...finite); if (low === high) return [low - 1, high + 1]; const padding = (high - low) * 0.05; return [low - padding, high + padding]; }
function scale(bounds: [number, number], start: number, end: number): (value: number) => number { return (value) => start + ((value - bounds[0]) / Math.max(1e-12, bounds[1] - bounds[0])) * (end - start); }
function interpolate(minimum: number, maximum: number, index: number, count: number): number { return count <= 1 ? minimum : minimum + (index / (count - 1)) * (maximum - minimum); }
function kernelLabel(value: GaussianProcessRegressionResult["method"]["kernel_preset"], t: ReturnType<typeof useI18n>["t"]): string { return t(value === "matern_5_2_ard" ? "gp.kernel.matern52" : value === "matern_3_2_ard" ? "gp.kernel.matern32" : value === "rbf_ard" ? "gp.kernel.rbf" : "gp.kernel.rq"); }
function noiseKey(value: GaussianProcessRegressionResult["method"]["noise_mode"]): "estimate" | "fixed" | "nearNoiseless" { return value === "near_noiseless" ? "nearNoiseless" : value; }
function validationLabel(value: GaussianProcessRegressionResult["method"]["validation_method"], t: ReturnType<typeof useI18n>["t"]): string { return t(value === "k_fold" ? "gp.validation.kFold" : value === "leave_one_out" ? "gp.validation.loo" : "gp.validation.none"); }
