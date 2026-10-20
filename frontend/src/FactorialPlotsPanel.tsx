import { InteractiveScatterChart } from "./charts/InteractiveScatterChart";
import { ChartFrame } from "./charts/ChartFrame";
import { useState } from "react";
import type { DoeFinalModelWorkflow, DoeFractionalEstimability, DoeModelSelectionResult } from "./api/types/doeModelWorkflow";
import { ChartItemFeedback } from "./charts/ChartItemFeedback";
import { paddedNumericRange, type NumericRange } from "./charts/chartScale";
import { useChartItemInteraction } from "./charts/useChartItemInteraction";
import { factorialViewFactors, isGeneralFactorial, type FactorialViewDesign, type FactorialViewFactor } from "./doe/factorialView";
import { factorialNumber } from "./doe/factorialWorkflowPresentation";
import { t } from "./i18n/translate";
import { DoeCompactPlotCard, DoeCompactPlotGrid } from "./doe/DoeCompactPlotGrid";
import { doePlotStatus, type DoePlotStatus } from "./doe/doePlotStatus";

type Cell = DoeFinalModelWorkflow["factorial_plots"]["cells"][number];
type Means = "fitted_mean" | "data_mean";
import { factorialMarginalMean } from "./doe/factorialWorkflowPresentation";

export function FactorialPlotsPanel({ model, design, selection, estimability, responseUnit }: {
  model: DoeFinalModelWorkflow; design: FactorialViewDesign;
  selection?: DoeModelSelectionResult | null; estimability?: DoeFractionalEstimability | null;
  responseUnit?: string | null;
}) {
  const factors = factorialViewFactors(design);
  const [means, setMeans] = useState<Means | "auto">("auto");
  const [xName, setXName] = useState(factors[0].name);
  const [traceName, setTraceName] = useState(factors[1].name);
  const [allPairs, setAllPairs] = useState(true);
  const [modelPairsOnly, setModelPairsOnly] = useState(false);
  const [sharedScale, setSharedScale] = useState(true);
  const [pairPage, setPairPage] = useState(0);
  const [cubeNames, setCubeNames] = useState(factors.slice(0, 3).map((factor) => factor.name));
  const [fixed, setFixed] = useState<Record<string, number>>({});
  const cells = model.factorial_plots.cells;
  const xFactor = factors.find((factor) => factor.name === xName) ?? factors[0];
  const traceFactor = factors.find((factor) => factor.name === traceName && factor.name !== xFactor.name) ?? factors.find((factor) => factor.name !== xFactor.name)!;
  const candidates = allPairs ? factors.flatMap((factor, index) => factors.slice(index + 1).map((trace) => [factor, trace] as const)) : [[xFactor, traceFactor] as const];
  const pairs = candidates.filter(([factor, trace]) => !modelPairsOnly || model.coded_coefficients.some((term) => term.kind === "interaction" && term.factor_names.includes(factor.name) && term.factor_names.includes(trace.name)));
  function card(factor: FactorialViewFactor, trace?: FactorialViewFactor) {
    const names = [factor.name, ...(trace ? [trace.name] : [])];
    const termId = factors.filter((item) => names.includes(item.name)).map((item) => item.id).join(":");
    const status = doePlotStatus(termId, selection, estimability);
    const retained = model.coded_coefficients.some((term) => term.factor_names.length === names.length && names.every((name) => term.factor_names.includes(name)));
    const actualMeans: Means = means === "auto" ? retained ? "fitted_mean" : "data_mean" : means;
    return { id: termId, factor, trace, status, means: actualMeans, points: meanPoints(factor, trace, cells, actualMeans) };
  }
  const mainCards = factors.map((factor) => card(factor));
  const pairCards = pairs.map(([factor, trace]) => card(factor, trace));
  const mainRange = paddedNumericRange(mainCards.flatMap((item) => item.points.map((point) => point.y)));
  const pairRange = paddedNumericRange(pairCards.flatMap((item) => item.points.map((point) => point.y)));
  const page = Math.min(pairPage, Math.max(0, Math.ceil(pairCards.length / 12) - 1));
  const visiblePairs = pairCards.slice(page * 12, (page + 1) * 12);
  const renderCard = (item: ReturnType<typeof card>, range: NumericRange) => <FactorialMeanChart
    key={item.id} xFactor={item.factor} traceFactor={item.trace} cells={cells} means={item.means}
    status={item.status} yRange={sharedScale ? range : undefined} responseUnit={responseUnit} />;
  const cubeAllowed = !isGeneralFactorial(design) && !design.fractional && !design.screening;
  return <section className="result-section factorial-plots"><h3>{t("doe.plots.title")}</h3>
    <label className="factorial-inline-select"><span>{t("doe.plots.mean")}</span><select value={means} onChange={(event) => setMeans(event.currentTarget.value as Means | "auto")}>
      <option value="auto">{t("doe.plots.auto")}</option>
      <option value="fitted_mean">{t("doe.plots.fitted")}</option><option value="data_mean">{t("doe.plots.data")}</option>
    </select></label><p className="field-help">{t("doe.plots.autoPolicy")} {t("doe.plots.policy")}</p>
    <p className="field-help">{model.equation.response_name}{responseUnit ? ` (${responseUnit})` : ""}</p>
    <label className="doe-table-toggle"><input type="checkbox" checked={sharedScale} onChange={(event) => setSharedScale(event.currentTarget.checked)} /><span>{t("doe.plots.sharedScale")}</span></label>
    <details><summary>{t("doe.alias.symbolMap")}</summary><ul>{factors.map((factor) => <li key={factor.id}><strong>{factor.symbol}</strong>: {factor.name}{factor.unit ? ` (${factor.unit})` : ""}</li>)}</ul></details>
    {!isGeneralFactorial(design) && design.fractional ? <p className="field-help">{t("doe.plots.fractionPolicy")}</p> : null}
    {!model.factorial_plots.available ? <p className="notice-box">{t("doe.model.unavailable")}</p> : <>
      <h4>{t("doe.plots.main")}</h4><DoeCompactPlotGrid>{mainCards.map((item) => renderCard(item, mainRange))}</DoeCompactPlotGrid>
      <h4>{t("doe.plots.interaction")}</h4><div className="option-grid">
        <label><span>{t("doe.plots.x")}</span><select value={xFactor.name} onChange={(event) => setXName(event.currentTarget.value)}>{factors.map((factor) => <option key={factor.name}>{factor.name}</option>)}</select></label>
        <label><span>{t("doe.plots.trace")}</span><select value={traceFactor.name} onChange={(event) => setTraceName(event.currentTarget.value)}>{factors.filter((factor) => factor.name !== xFactor.name).map((factor) => <option key={factor.name}>{factor.name}</option>)}</select></label>
      </div><label className="doe-table-toggle"><input type="checkbox" checked={allPairs} onChange={(event) => setAllPairs(event.currentTarget.checked)} /><span>{t("doe.plots.allPairs")}</span></label>
      <label className="doe-table-toggle"><input type="checkbox" checked={modelPairsOnly} onChange={(event) => setModelPairsOnly(event.currentTarget.checked)} /><span>{t("doe.plots.modelPairs")}</span></label>
      <p className="field-help">{t("doe.plots.parallel")}</p>
      <p>{t("doe.plots.pageRange", { start: pairCards.length ? page * 12 + 1 : 0, end: Math.min((page + 1) * 12, pairCards.length), total: pairCards.length })}</p>
      {pairCards.length > 12 ? <div className="button-row">
        <button type="button" className="secondary-button" disabled={page === 0} onClick={() => setPairPage(page - 1)}>{t("doe.plots.previous")}</button>
        <button type="button" className="secondary-button" disabled={(page + 1) * 12 >= pairCards.length} onClick={() => setPairPage(page + 1)}>{t("doe.plots.next")}</button>
      </div> : null}
      <DoeCompactPlotGrid>{visiblePairs.map((item) => renderCard(item, pairRange))}</DoeCompactPlotGrid>
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
          cells={cells} means={means === "auto" ? "fitted_mean" : means} fixed={Object.fromEntries(factors.filter((factor) => !cubeNames.includes(factor.name)).map((factor) => [factor.name, fixed[factor.name] ?? factor.levels[0].code]))} />
      </>}
    </>}
  </section>;
}

function meanPoints(xFactor: FactorialViewFactor, traceFactor: FactorialViewFactor | undefined, cells: Cell[], means: Means) {
  const traces = traceFactor?.levels ?? [{ code: 0, actual: "" }];
  return traces.flatMap((trace, series) => xFactor.levels.map((level, index) => {
    const value = factorialMarginalMean(cells, { [xFactor.name]: level.code, ...(traceFactor ? { [traceFactor.name]: trace.code } : {}) }, means);
    const label = `${xFactor.name} = ${level.actual}${traceFactor ? `; ${traceFactor.name} = ${trace.actual}` : ""}`;
    return { id: JSON.stringify([xFactor.name, level.code, traceFactor?.name, trace.code]), seriesId: String(trace.code), x: index, y: value ?? NaN,
      title: label, ariaLabel: `${label}: ${factorialNumber(value)}`, className: `factorial-series-${series}`,
      marker: series % 2 ? "diamond" as const : "circle" as const,
      details: [{ label: t(means === "fitted_mean" ? "doe.plots.fitted" : "doe.plots.data"), value: factorialNumber(value) }] };
  }));
}

function FactorialMeanChart({ xFactor, traceFactor, cells, means, status, yRange, responseUnit }: {
  xFactor: FactorialViewFactor; traceFactor?: FactorialViewFactor; cells: Cell[]; means: Means;
  status: DoePlotStatus; yRange?: NumericRange; responseUnit?: string | null;
}) {
  const traces = traceFactor?.levels ?? [{ code: 0, actual: "" }];
  const points = meanPoints(xFactor, traceFactor, cells, means);
  const title = `${xFactor.symbol}${traceFactor ? ` × ${traceFactor.symbol}` : ""}`;
  const overall = factorialMarginalMean(cells, {}, means);
  const missingCount = points.filter((point) => !Number.isFinite(point.y)).length;
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <DoeCompactPlotCard title={title} status={status} meanLabel={t(means === "fitted_mean" ? "doe.plots.fitted" : "doe.plots.data")}>{(layout) => <InteractiveScatterChart chartId="factorial-means"
    sourceKey={JSON.stringify([means, xFactor.name, traceFactor?.name])} title={title} description={t("doe.plots.policy")}
    annotations={missingCount ? [t("doe.plots.missingCells", { count: missingCount })] : []}
    layout={layout} axisTickCount={3} collapsibleDetails
    points={points.filter((point) => Number.isFinite(point.y))} emptyLabel={t("charts.noData")} xLabel={xFactor.symbol} xUnit={xFactor.unit}
    yLabel="Y" yUnit={responseUnit} xRange={xRange} yRange={yRange ?? paddedNumericRange(points.map((point) => point.y))}
    xTicks={xFactor.levels.map((level, index) => ({ value: index, label: String(level.actual) })).filter((_, index, values) => index % Math.ceil(values.length / 4) === 0 || index === values.length - 1)}
    series={traces.map((trace, index) => ({ id: String(trace.code), label: traceFactor ? `${traceFactor.symbol}: ${trace.actual}` : xFactor.symbol,
      className: `factorial-series-${index}`, pointIds: points.filter((point) => point.seriesId === String(trace.code)).map((point) => point.id), connect: "line" }))}
    referenceLines={!traceFactor && overall !== null ? [{ label: t("doe.plots.mean"), x1: xRange.min, x2: xRange.max, y1: overall, y2: overall }] : []} />}</DoeCompactPlotCard>;
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
