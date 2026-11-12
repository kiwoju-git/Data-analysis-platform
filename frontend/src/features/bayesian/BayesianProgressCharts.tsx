import { useId, useMemo, useState } from "react";
import type { AnyBayesianStudyResponse } from "../../api/types/boMixed";
import { InteractiveScatterChart, type ChartSeries, type InteractiveScatterPoint } from "../../charts/InteractiveScatterChart";
import { integerChartTicks } from "../../charts/chartLayout";
import { paddedNumericRange } from "../../charts/chartScale";
import { useI18n } from "../../i18n/LocaleProvider";
import { progressMessages } from "../../i18n/boProgress";
import { formatExactNumericValue } from "../../statisticalNumberFormat";
import { buildBayesianProgress, projectBayesianFactors, factorProgressSourceKey, categoryDisplayTicks, type ProgressRow } from "./bayesianProgress";
import "./bayesianProgress.css";

export function BayesianProgressCharts({ study }: { study: AnyBayesianStudyResponse }) {
  const { locale } = useI18n(), text = progressMessages(locale), id = useId();
  const [responseId, setResponseId] = useState("");
  const [distanceView, setDistanceView] = useState(false);
  const [xId, setXId] = useState(""), [yId, setYId] = useState("");
  const responses = study.objective.goal_type === "desirability" ? study.objective.responses : [];
  const activeResponse = responses.find(row => row.response_id === responseId)?.response_id ?? responses[0]?.response_id;
  const progress = useMemo(() => buildBayesianProgress(study, activeResponse), [study, activeResponse]);
  const xFactor = study.factors.find(factor => factor.factor_id === xId) ?? study.factors[0];
  const yFactor = study.factors.find(factor => factor.factor_id === yId && factor.factor_id !== xFactor?.factor_id)
    ?? study.factors.find(factor => factor.factor_id !== xFactor?.factor_id);
  const projection = useMemo(() => projectBayesianFactors(study, xFactor?.factor_id ?? "", yFactor?.factor_id ?? ""), [study, xFactor, yFactor]);
  const source = `${study.study_id}:${study.study_version_id}:${study.definition_sha256}:${study.observation_history.observation_history_sha256}`;
  const exact = (value: number) => formatExactNumericValue(value);
  const origin = (value: string) => value === "replicate" ? text.replicate : value === "initial_design" ? text.initial : text.recommendation;
  const stateLabel = (value: string) => value === "completed" ? text.completed : value === "pending" ? text.pending : text.abandoned;
  const isDistance = progress.goal === "match_target" && distanceView;
  const data = progress.rows.map(row => ({ ...row, value: isDistance ? row.distance! : row.value }));

  function progressPlot(rows: ProgressRow[], chartId: string, title: string, label: string, unit: string | null, composite = false) {
    const showBest = composite || progress.goal !== "match_target" || isDistance;
    const points: InteractiveScatterPoint[] = rows.flatMap(row => {
      const measured: InteractiveScatterPoint = { id: `${row.trialId}:measured`, x: row.trialNumber, y: row.value,
        title: `${text.trial} ${row.trialNumber}`, ariaLabel: `${text.trial} ${row.trialNumber}: ${exact(row.value)}`,
        className: "chart-interactive-item bo-progress-measured", marker: row.origin === "replicate" ? "diamond" : "circle", seriesId: "measured",
        details: [{ label: text.trial, value: String(row.trialNumber) }, { label, value: exact(row.value) },
          { label: text.origin, value: origin(row.origin) }] };
      return showBest ? [measured, { ...measured, id: `${row.trialId}:best`, y: row.best, seriesId: "best", marker: "square",
        className: "chart-interactive-item bo-progress-best", ariaLabel: `${text.trial} ${row.trialNumber}, ${text.best}: ${exact(row.best)}`,
        details: [{ label: text.trial, value: String(row.trialNumber) }, { label: text.best, value: exact(row.best) }] }] : [measured];
    });
    const series: ChartSeries[] = [{ id: "measured", label, className: "bo-progress-measured-line", pointIds: rows.map(row => `${row.trialId}:measured`), connect: "none" }];
    if (showBest) series.push({ id: "best", label: text.best, className: "bo-progress-best-line", pointIds: rows.map(row => `${row.trialId}:best`), connect: "step" });
    const range = paddedNumericRange(rows.map(row => row.trialNumber));
    const referenceLines = !composite && !isDistance && progress.target !== null
      ? [{ label: text.target, x1: range.min, x2: range.max, y1: progress.target, y2: progress.target }] : [];
    return <InteractiveScatterChart chartId={chartId} title={title} description={composite ? text.scoreMeaning : text.order}
      sourceKey={`${source}:${activeResponse ?? "scalar"}:${chartId}:${isDistance}`} points={points} series={series}
      xLabel={text.trial} xRange={range} xTicks={integerChartTicks(range)} yLabel={label} yUnit={unit}
      yRange={composite ? { min: 0, max: 1 } : paddedNumericRange(points.map(point => point.y))}
      referenceLines={referenceLines} annotations={[]} emptyLabel={text.empty} collapsibleDetails />;
  }

  const spacePoints: InteractiveScatterPoint[] = projection.points.map(row => ({ id: row.trialId, x: row.x, y: row.y,
    title: `${text.trial} ${row.trialNumber}`, ariaLabel: `${text.trial} ${row.trialNumber}, ${stateLabel(row.state)}, ${row.actualX}, ${row.actualY}`,
    className: `chart-interactive-item bo-progress-${row.state}`, marker: row.state === "completed" ? "circle" : row.state === "pending" ? "diamond" : "square",
    seriesId: row.state, details: [{ label: text.trial, value: String(row.trialNumber) }, { label: text.state, value: stateLabel(row.state) },
      { label: text.origin, value: origin(row.origin) },
      ...study.factors.map(factor => { const value = study.trials.find(trial => trial.trial_id === row.trialId)!.actual_coordinates[factor.factor_id];
        return { label: factor.unit ? `${factor.name} (${factor.unit})` : factor.name, value: typeof value === "number" ? exact(value) : value }; })] }));
  const spaceSeries: ChartSeries[] = ["completed", "pending", "abandoned"].map(state => ({ id: state, label: stateLabel(state),
    className: `bo-progress-${state}`, pointIds: spacePoints.filter(point => point.seriesId === state).map(point => point.id), connect: "none" }));

  return <section className="bo-progress" aria-labelledby={`${id}-title`}>
    <div className="panel-heading"><h4 id={`${id}-title`}>{text.title}</h4><span className="cell-subtext">{text.current}</span></div>
    <div className="bo-progress-controls">
      {responses.length > 0 && <label>{text.response}<select aria-label={text.response} value={activeResponse} onChange={event => setResponseId(event.currentTarget.value)}>
        {responses.map(response => <option key={response.response_id} value={response.response_id}>{response.name}</option>)}
      </select></label>}
      {progress.goal === "match_target" && <label>{text.view}<select aria-label={text.view} value={isDistance ? "distance" : "actual"} onChange={event => setDistanceView(event.currentTarget.value === "distance")}>
        <option value="actual">{text.actual}</option><option value="distance">{text.distance}</option></select></label>}
      <span>{text.n}: {progress.rows.length} / {study.completed_trial_count}</span>
    </div>
    <p className="cell-subtext">{text.order}</p>
    {(progress.invalidTrialCount > 0 || progress.invalidDesirabilityCount > 0) && <p className="warning-box">{text.invalid} ({progress.invalidTrialCount} / {progress.invalidDesirabilityCount})</p>}
    {progress.reason ? <p role="status">{text.unavailable} <code>{progress.reason}</code></p> : <div className="bo-progress-grid">
      <div><h5>{text.observed}</h5>{progressPlot(data, "bo-progress-observed", text.observed, isDistance ? text.distance : progress.name, progress.unit)}</div>
      <div>{progress.desirability === null ? <p className="cell-subtext">{text.noScore}</p>
        : <><h5>{text.scoreTitle}</h5>{progressPlot(progress.desirability, "bo-progress-desirability", text.scoreTitle, text.score, null, true)}</>}</div>
    </div>}
    {study.factors.length < 2 ? <p className="cell-subtext">{text.twoFactors}</p> : <>
      <div className="bo-progress-controls">{[{ label: text.x, factor: xFactor, other: yFactor, set: setXId }, { label: text.y, factor: yFactor, other: xFactor, set: setYId }].map((axis, index) =>
        <label key={index}>{axis.label}<select aria-label={axis.label} value={axis.factor?.factor_id} onChange={event => axis.set(event.currentTarget.value)}>
          {study.factors.map(factor => <option key={factor.factor_id} value={factor.factor_id} disabled={index === 1 && factor.factor_id === axis.other?.factor_id}>{factor.name}</option>)}
        </select></label>)}</div>
      <p className="cell-subtext">{text.projection}{projection.xTicks || projection.yTicks ? ` ${text.categories}` : ""}</p>
      {projection.invalidTrialCount > 0 && <p className="warning-box">{text.invalid} ({projection.invalidTrialCount})</p>}
      <div className="bo-progress-space"><h5>{text.space}</h5><InteractiveScatterChart chartId="bo-progress-space" title={text.space} description={text.projection}
        sourceKey={`${factorProgressSourceKey(study)}:space:${xFactor?.factor_id}:${yFactor?.factor_id}`} points={spacePoints} series={spaceSeries}
        xLabel={xFactor?.name ?? ""} yLabel={yFactor?.name ?? ""} xUnit={xFactor?.unit} yUnit={yFactor?.unit}
        xRange={projection.xTicks ? { min: -0.5, max: projection.xTicks.length - 0.5 } : paddedNumericRange(spacePoints.map(point => point.x))}
        yRange={projection.yTicks ? { min: -0.5, max: projection.yTicks.length - 0.5 } : paddedNumericRange(spacePoints.map(point => point.y))}
        xTicks={categoryDisplayTicks(projection.xTicks)} yTicks={categoryDisplayTicks(projection.yTicks)} annotations={[]} emptyLabel={text.empty} collapsibleDetails /></div>
      {(projection.xTicks || projection.yTicks) && <details className="bo-progress-levels"><summary>{text.levels}</summary>
        {[{ factor: xFactor, ticks: projection.xTicks }, { factor: yFactor, ticks: projection.yTicks }].filter(axis => axis.ticks).map(axis =>
          <div key={axis.factor!.factor_id}><strong>{axis.factor!.name}</strong><dl>{axis.ticks!.map(tick =>
            <div key={tick.value}><dt>#{tick.value + 1}</dt><dd>{tick.label}</dd></div>)}</dl></div>)}
      </details>}
    </>}
    <details><summary>{text.data}</summary><p className="cell-subtext">{text.history}: {study.observation_history.history_revision_id}</p>
      <div className="table-wrap"><table className="result-table"><thead><tr><th>{text.trial}</th><th>{progress.name}</th><th>{text.origin}</th></tr></thead>
        <tbody>{progress.rows.map(row => <tr key={row.trialId}><td>{row.trialNumber}</td><td>{exact(row.value)}{progress.unit ? ` ${progress.unit}` : ""}</td><td>{origin(row.origin)}</td></tr>)}</tbody></table></div>
    </details>
  </section>;
}
