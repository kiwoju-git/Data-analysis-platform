import { InteractiveScatterChart } from "./charts/InteractiveScatterChart";
import { ChartFrame } from "./charts/ChartFrame";
import { useState } from "react";
import type { DoeFinalModelWorkflow } from "./api/types/doeModelWorkflow";
import { ChartItemFeedback } from "./charts/ChartItemFeedback";
import { paddedNumericRange } from "./charts/chartScale";
import { useChartItemInteraction } from "./charts/useChartItemInteraction";
import { factorialViewFactors, isGeneralFactorial, type FactorialViewDesign, type FactorialViewFactor } from "./doe/factorialView";
import { factorialNumber } from "./doe/factorialWorkflowPresentation";
import { t } from "./i18n/translate";

type Cell = DoeFinalModelWorkflow["factorial_plots"]["cells"][number];
type Means = "fitted_mean" | "data_mean";
import { factorialMarginalMean } from "./doe/factorialWorkflowPresentation";

export function FactorialPlotsPanel({ model, design }: { model: DoeFinalModelWorkflow; design: FactorialViewDesign }) {
  const factors = factorialViewFactors(design);
  const [means, setMeans] = useState<Means>("fitted_mean");
  const [xName, setXName] = useState(factors[0].name);
  const [traceName, setTraceName] = useState(factors[1].name);
  const [allPairs, setAllPairs] = useState(false);
  const [modelPairsOnly, setModelPairsOnly] = useState(false);
  const [cubeNames, setCubeNames] = useState(factors.slice(0, 3).map((factor) => factor.name));
  const [fixed, setFixed] = useState<Record<string, number>>({});
  const cells = model.factorial_plots.cells;
  const xFactor = factors.find((factor) => factor.name === xName) ?? factors[0];
  const traceFactor = factors.find((factor) => factor.name === traceName && factor.name !== xFactor.name) ?? factors.find((factor) => factor.name !== xFactor.name)!;
  const candidates = allPairs ? factors.flatMap((factor, index) => factors.slice(index + 1).map((trace) => [factor, trace] as const)) : [[xFactor, traceFactor] as const];
  const pairs = candidates.filter(([factor, trace]) => !modelPairsOnly || model.coded_coefficients.some((term) => term.kind === "interaction" && term.factor_names.includes(factor.name) && term.factor_names.includes(trace.name))).slice(0, 15);
  const cubeAllowed = !isGeneralFactorial(design) && !design.fractional && !design.screening;
  return <section className="result-section factorial-plots"><h3>{t("doe.plots.title")}</h3>
    <label className="factorial-inline-select"><span>{t("doe.plots.mean")}</span><select value={means} onChange={(event) => setMeans(event.currentTarget.value as Means)}>
      <option value="fitted_mean">{t("doe.plots.fitted")}</option><option value="data_mean">{t("doe.plots.data")}</option>
    </select></label><p className="field-help">{t("doe.plots.policy")}</p>
    {!model.factorial_plots.available ? <p className="notice-box">{t("doe.model.unavailable")}</p> : <>
      <h4>{t("doe.plots.main")}</h4><div className="chart-grid analysis-result-grid">{factors.map((factor) => <FactorialMeanChart key={factor.name} xFactor={factor} cells={cells} means={means} />)}</div>
      <h4>{t("doe.plots.interaction")}</h4><div className="option-grid">
        <label><span>{t("doe.plots.x")}</span><select value={xFactor.name} onChange={(event) => setXName(event.currentTarget.value)}>{factors.map((factor) => <option key={factor.name}>{factor.name}</option>)}</select></label>
        <label><span>{t("doe.plots.trace")}</span><select value={traceFactor.name} onChange={(event) => setTraceName(event.currentTarget.value)}>{factors.filter((factor) => factor.name !== xFactor.name).map((factor) => <option key={factor.name}>{factor.name}</option>)}</select></label>
      </div><label className="doe-table-toggle"><input type="checkbox" checked={allPairs} onChange={(event) => setAllPairs(event.currentTarget.checked)} /><span>{t("doe.plots.allPairs")}</span></label>
      <label className="doe-table-toggle"><input type="checkbox" checked={modelPairsOnly} onChange={(event) => setModelPairsOnly(event.currentTarget.checked)} /><span>{t("doe.plots.modelPairs")}</span></label>
      <p className="field-help">{t("doe.plots.parallel")}</p>
      <div className="chart-grid analysis-result-grid">{pairs.map(([factor, trace]) => <FactorialMeanChart key={`${factor.name}:${trace.name}`} xFactor={factor} traceFactor={trace} cells={cells} means={means} />)}</div>
      <h4>{t("doe.plots.cube")}</h4>{!cubeAllowed ? <p className="field-help">{t("doe.plots.cubeUnavailable")}</p> : <>
        <div className="option-grid"><label><span>{t("doe.plots.count")}</span><select aria-label={t("doe.plots.count")} value={cubeNames.length} onChange={(event) => {
          const count = Number(event.currentTarget.value); setCubeNames([...cubeNames.slice(0, count), ...factors.filter((factor) => !cubeNames.includes(factor.name)).map((factor) => factor.name)].slice(0, count));
        }}><option value={2}>2</option>{factors.length >= 3 ? <option value={3}>3</option> : null}</select></label>
        {cubeNames.map((name, index) => <label key={index}><span>{t("doe.plots.cube")} {index + 1}</span><select value={name} onChange={(event) => setCubeNames((current) => current.map((value, at) => at === index ? event.currentTarget.value : value))}>
          {factors.filter((factor) => factor.name === name || !cubeNames.includes(factor.name)).map((factor) => <option key={factor.name}>{factor.name}</option>)}
        </select></label>)}</div>
        {factors.length > cubeNames.length ? <fieldset><legend>{t("doe.plots.fixed")}</legend><div className="option-grid">{factors.filter((factor) => !cubeNames.includes(factor.name)).map((factor) => <label key={factor.name}>
          <span>{factor.name}</span><select value={fixed[factor.name] ?? factor.levels[0].code} onChange={(event) => setFixed((current) => ({ ...current, [factor.name]: Number(event.currentTarget.value) }))}>
            {factor.levels.map((level) => <option value={level.code} key={level.code}>{String(level.actual)}</option>)}
          </select></label>)}</div></fieldset> : null}
        <FactorialCubeChart factors={factors.filter((factor) => cubeNames.includes(factor.name)).sort((a, b) => cubeNames.indexOf(a.name) - cubeNames.indexOf(b.name))}
          cells={cells} means={means} fixed={Object.fromEntries(factors.filter((factor) => !cubeNames.includes(factor.name)).map((factor) => [factor.name, fixed[factor.name] ?? factor.levels[0].code]))} />
      </>}
    </>}
  </section>;
}

function FactorialMeanChart({ xFactor, traceFactor, cells, means }: { xFactor: FactorialViewFactor; traceFactor?: FactorialViewFactor; cells: Cell[]; means: Means }) {
  const traces = traceFactor?.levels ?? [{ code: 0, actual: "" }];
  const points = traces.flatMap((trace, series) => xFactor.levels.map((level, index) => {
    const value = factorialMarginalMean(cells, { [xFactor.name]: level.code, ...(traceFactor ? { [traceFactor.name]: trace.code } : {}) }, means);
    const label = `${xFactor.name} = ${level.actual}${traceFactor ? `; ${traceFactor.name} = ${trace.actual}` : ""}`;
    return { id: JSON.stringify([xFactor.name, level.code, traceFactor?.name, trace.code]), seriesId: String(trace.code), x: index, y: value ?? NaN,
      title: label, ariaLabel: `${label}: ${factorialNumber(value)}`, className: `factorial-series-${series}`,
      marker: series % 2 ? "diamond" as const : "circle" as const,
      details: [{ label: t(means === "fitted_mean" ? "doe.plots.fitted" : "doe.plots.data"), value: factorialNumber(value) }] };
  }));
  const title = `${t(traceFactor ? "doe.plots.interaction" : "doe.plots.main")}: ${xFactor.name}${traceFactor ? ` / ${traceFactor.name}` : ""}`;
  const overall = factorialMarginalMean(cells, {}, means);
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <div className="chart-panel"><h4>{title}</h4><InteractiveScatterChart chartId="factorial-means"
    sourceKey={JSON.stringify([means, xFactor.name, traceFactor?.name])} title={title} description={t("doe.plots.policy")} annotations={[]}
    points={points} formatValue={factorialNumber} emptyLabel={t("charts.noData")} xLabel={xFactor.name} xUnit={xFactor.unit}
    yLabel={t(means === "fitted_mean" ? "doe.plots.fitted" : "doe.plots.data")} xRange={xRange} yRange={paddedNumericRange(points.map((point) => point.y))}
    xTicks={xFactor.levels.map((level, index) => ({ value: index, label: String(level.actual) }))}
    series={traces.map((trace, index) => ({ id: String(trace.code), label: traceFactor ? `${traceFactor.name}: ${trace.actual}` : xFactor.name,
      className: `factorial-series-${index}`, pointIds: points.filter((point) => point.seriesId === String(trace.code)).map((point) => point.id), connect: "line" }))}
    referenceLines={!traceFactor && overall !== null ? [{ label: t("doe.plots.mean"), x1: xRange.min, x2: xRange.max, y1: overall, y2: overall }] : []} />
  </div>;
}

function FactorialCubeChart({ factors, cells, means, fixed }: { factors: FactorialViewFactor[]; cells: Cell[]; means: Means; fixed: Record<string, number> }) {
  const vertices = Array.from({ length: 2 ** factors.length }, (_, index) => {
    const bits = factors.map((_, bit) => (index >> bit) & 1);
    const settings = { ...fixed, ...Object.fromEntries(factors.map((factor, at) => [factor.name, factor.levels[bits[at]].code])) };
    return { id: JSON.stringify(Object.entries(settings)), bits, x: 100 + bits[0] * 235 + (bits[2] ?? 0) * 80, y: 275 - bits[1] * 165 - (bits[2] ?? 0) * 70,
      value: factorialMarginalMean(cells, settings, means), label: factors.map((factor, at) => `${factor.name} = ${factor.levels[bits[at]].actual}`).join("; ") };
  });
  const interaction = useChartItemInteraction(vertices.filter((point) => point.value !== null).map((point) => point.id), { sourceKey: JSON.stringify([means, factors.map((factor) => factor.name), fixed]) });
  return <div className="chart-panel factorial-cube-chart"><ChartFrame chartId="factorial-cube" title={t("doe.plots.cube")} description={factors.map((factor) => factor.name).join(", ")} layout={{ width: 520, height: 360, maxWidth: 640, plot: { left: 0, top: 0, width: 520, height: 360 } }}>
    {vertices.flatMap((point, index) => factors.map((_, bit) => {
      const other = index ^ (1 << bit); return other > index ? <line className="chart-axis" key={`${index}-${bit}`} x1={point.x} y1={point.y} x2={vertices[other].x} y2={vertices[other].y} /> : null;
    }))}
    {vertices.map((point) => <g key={point.id}>{point.value !== null && <circle className={`scatter-point chart-interactive-item ${interaction.stateClass(point.id)}`} aria-describedby={interaction.describedBy(point.id)} onBlur={() => interaction.clearFocus(point.id)} cx={point.x} cy={point.y} r={6} role="img" aria-label={`${point.label}: ${factorialNumber(point.value)}`}
      tabIndex={interaction.tabIndexFor(point.id)} ref={(element) => interaction.itemRef(point.id, element)} onFocus={() => interaction.activate(point.id, point.x, point.y, "focus")}
      onKeyDown={(event) => interaction.handleKeyDown(event, point.id)} onClick={() => interaction.activate(point.id, point.x, point.y, "selection")}
      onPointerMove={(event) => interaction.move(point.id, event)} onPointerEnter={(event) => interaction.move(point.id, event)} onPointerLeave={() => interaction.clearHover(point.id)}><title>{point.label}: {factorialNumber(point.value)}</title></circle>}
      <text x={point.x} y={point.y - 12} className="chart-axis-label" textAnchor="middle">{factorialNumber(point.value)}</text></g>)}
    <text x={255} y={322} className="chart-axis-label" textAnchor="middle">{factors[0].name}</text>
    <text x={20} y={180} className="chart-axis-label" transform="rotate(-90 20 180)" textAnchor="middle">{factors[1].name}</text>
    {factors[2] ? <text x={425} y={245} className="chart-axis-label" textAnchor="middle">{factors[2].name}</text> : null}
  </ChartFrame><ChartItemFeedback interaction={interaction} items={vertices.map((point) => ({ id: point.id, title: point.label, details: [{ label: t("doe.plots.mean"), value: factorialNumber(point.value) }] }))} />
  <ul className="factorial-plot-legend">{factors.map((factor) => <li key={factor.name}>{factor.name}: {factor.levels.map((level) => String(level.actual)).join(" / ")}</li>)}</ul></div>;
}
