import { useId, useState } from "react";
import type { DoeFinalModelWorkflow } from "./api/types/doeModelWorkflow";
import { paddedNumericRange, scaleChartValue } from "./charts/chartScale";
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
      <h4>{t("doe.plots.main")}</h4><div className="chart-grid">{factors.map((factor) => <FactorialMeanChart key={factor.name} xFactor={factor} cells={cells} means={means} />)}</div>
      <h4>{t("doe.plots.interaction")}</h4><div className="option-grid">
        <label><span>{t("doe.plots.x")}</span><select value={xFactor.name} onChange={(event) => setXName(event.currentTarget.value)}>{factors.map((factor) => <option key={factor.name}>{factor.name}</option>)}</select></label>
        <label><span>{t("doe.plots.trace")}</span><select value={traceFactor.name} onChange={(event) => setTraceName(event.currentTarget.value)}>{factors.filter((factor) => factor.name !== xFactor.name).map((factor) => <option key={factor.name}>{factor.name}</option>)}</select></label>
      </div><label className="doe-table-toggle"><input type="checkbox" checked={allPairs} onChange={(event) => setAllPairs(event.currentTarget.checked)} /><span>{t("doe.plots.allPairs")}</span></label>
      <label className="doe-table-toggle"><input type="checkbox" checked={modelPairsOnly} onChange={(event) => setModelPairsOnly(event.currentTarget.checked)} /><span>{t("doe.plots.modelPairs")}</span></label>
      <p className="field-help">{t("doe.plots.parallel")}</p>
      <div className="chart-grid">{pairs.map(([factor, trace]) => <FactorialMeanChart key={`${factor.name}:${trace.name}`} xFactor={factor} traceFactor={trace} cells={cells} means={means} />)}</div>
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

const seriesColors = ["#2563a6", "#ad3e64", "#187762", "#8a651b", "#6852a1", "#a04c23", "#237e91", "#735c68", "#4e6f29", "#94662f"];

function FactorialMeanChart({ xFactor, traceFactor, cells, means }: { xFactor: FactorialViewFactor; traceFactor?: FactorialViewFactor; cells: Cell[]; means: Means }) {
  const id = useId().replace(/:/g, "");
  const traces = traceFactor?.levels ?? [{ code: 0, actual: "" }];
  const points = traces.flatMap((trace, series) => xFactor.levels.map((level, index) => ({ id: `${id}-${series}-${index}`, series, index,
    label: `${xFactor.name} = ${level.actual}${traceFactor ? `; ${traceFactor.name} = ${trace.actual}` : ""}`,
    value: factorialMarginalMean(cells, { [xFactor.name]: level.code, ...(traceFactor ? { [traceFactor.name]: trace.code } : {}) }, means) })));
  const interaction = useChartItemInteraction(points.filter((point) => point.value !== null).map((point) => point.id));
  const range = paddedNumericRange(points.flatMap((point) => point.value === null ? [] : [point.value]), 0.1);
  const x = (index: number) => 62 + index * 316 / Math.max(1, xFactor.levels.length - 1);
  const y = (value: number) => scaleChartValue(value, range, 190, 25);
  const selected = points.find((point) => point.id === interaction.activeItem?.id);
  const title = `${t(traceFactor ? "doe.plots.interaction" : "doe.plots.main")}: ${xFactor.name}${traceFactor ? ` / ${traceFactor.name}` : ""}`;
  const overall = factorialMarginalMean(cells, {}, means);
  return <div className="chart-panel"><h4>{title}</h4><div className="interactive-chart">
    <svg className="chart-svg chart-svg-wide" viewBox="0 0 440 265" role="img" aria-labelledby={`${id}-title ${id}-desc`}>
      <title id={`${id}-title`}>{title}</title><desc id={`${id}-desc`}>{t("doe.plots.policy")}</desc>
      <line className="chart-axis" x1={62} x2={378} y1={190} y2={190} /><line className="chart-axis" x1={62} x2={62} y1={25} y2={190} />
      {[range.min, (range.min + range.max) / 2, range.max].map((value) => <text key={value} className="chart-axis-label" textAnchor="end" x={55} y={y(value) + 4}>{factorialNumber(value)}</text>)}
      {!traceFactor && overall !== null ? <line className="reference-line" x1={62} x2={378} y1={y(overall)} y2={y(overall)} /> : null}
      {traces.map((trace, series) => <polyline key={trace.code} fill="none" stroke={seriesColors[series]} strokeWidth={2} strokeDasharray={series % 2 ? "6 3" : undefined}
        points={points.filter((point) => point.series === series && point.value !== null).map((point) => `${x(point.index)},${y(point.value!)}`).join(" ")} />)}
      {points.filter((point) => point.value !== null).map((point) => <circle key={point.id} cx={x(point.index)} cy={y(point.value!)} r={5} fill={seriesColors[point.series]}
        className="chart-interactive-item" tabIndex={interaction.tabIndexFor(point.id)} aria-label={`${point.label}: ${factorialNumber(point.value)}`} role="img"
        ref={(element) => interaction.itemRef(point.id, element)} onFocus={() => interaction.activate(point.id, x(point.index), y(point.value!), "focus")}
        onClick={() => interaction.activate(point.id, x(point.index), y(point.value!), "selection")} onKeyDown={(event) => interaction.handleKeyDown(event, point.id)}
        onPointerEnter={(event) => interaction.move(point.id, event)} onPointerLeave={() => interaction.clear(point.id)}><title>{point.label}: {factorialNumber(point.value)}</title></circle>)}
      {xFactor.levels.map((level, index) => <text className="chart-axis-label" key={level.code} x={x(index)} y={210} textAnchor="middle"><title>{String(level.actual)}</title>{String(level.actual).length > 12 ? `${String(level.actual).slice(0, 10)}...` : String(level.actual)}</text>)}
      <text className="chart-axis-label" x={220} y={246} textAnchor="middle">{xFactor.name}{xFactor.unit ? ` (${xFactor.unit})` : ""}</text>
    </svg>
    {traceFactor ? <ul className="factorial-plot-legend">{traces.map((trace, index) => <li key={trace.code}><span aria-hidden="true" style={{ backgroundColor: seriesColors[index] }} />{traceFactor.name}: {String(trace.actual)}</li>)}</ul> : null}
    <p className="factorial-point-detail" aria-live="polite">{selected ? `${selected.label}: ${factorialNumber(selected.value)}` : "\u00a0"}</p>
  </div></div>;
}

function FactorialCubeChart({ factors, cells, means, fixed }: { factors: FactorialViewFactor[]; cells: Cell[]; means: Means; fixed: Record<string, number> }) {
  const id = useId().replace(/:/g, "");
  const vertices = Array.from({ length: 2 ** factors.length }, (_, index) => {
    const bits = factors.map((_, bit) => (index >> bit) & 1);
    const settings = { ...fixed, ...Object.fromEntries(factors.map((factor, at) => [factor.name, factor.levels[bits[at]].code])) };
    return { id: `${id}-${index}`, bits, x: 100 + bits[0] * 235 + (bits[2] ?? 0) * 80, y: 275 - bits[1] * 165 - (bits[2] ?? 0) * 70,
      value: factorialMarginalMean(cells, settings, means), label: factors.map((factor, at) => `${factor.name} = ${factor.levels[bits[at]].actual}`).join("; ") };
  });
  const interaction = useChartItemInteraction(vertices.map((point) => point.id));
  const selected = vertices.find((point) => point.id === interaction.activeItem?.id);
  return <div className="chart-panel factorial-cube-chart"><svg className="chart-svg" viewBox="0 0 520 360" role="img" aria-labelledby={`${id}-title ${id}-desc`}>
    <title id={`${id}-title`}>{t("doe.plots.cube")}</title><desc id={`${id}-desc`}>{factors.map((factor) => factor.name).join(", ")}; {t("doe.plots.fixed")}: {Object.entries(fixed).map(([key, value]) => `${key}=${value}`).join(", ")}</desc>
    {vertices.flatMap((point, index) => factors.map((_, bit) => {
      const other = index ^ (1 << bit); return other > index ? <line className="chart-axis" key={`${index}-${bit}`} x1={point.x} y1={point.y} x2={vertices[other].x} y2={vertices[other].y} /> : null;
    }))}
    {vertices.map((point) => <g key={point.id}><circle className="scatter-point chart-interactive-item" cx={point.x} cy={point.y} r={6} role="img" aria-label={`${point.label}: ${factorialNumber(point.value)}`}
      tabIndex={interaction.tabIndexFor(point.id)} ref={(element) => interaction.itemRef(point.id, element)} onFocus={() => interaction.activate(point.id, point.x, point.y, "focus")}
      onKeyDown={(event) => interaction.handleKeyDown(event, point.id)} onClick={() => interaction.activate(point.id, point.x, point.y, "selection")}
      onPointerEnter={(event) => interaction.move(point.id, event)}><title>{point.label}: {factorialNumber(point.value)}</title></circle>
      <text x={point.x} y={point.y - 12} className="chart-axis-label" textAnchor="middle">{factorialNumber(point.value)}</text></g>)}
    <text x={255} y={322} className="chart-axis-label" textAnchor="middle">{factors[0].name}</text>
    <text x={20} y={180} className="chart-axis-label" transform="rotate(-90 20 180)" textAnchor="middle">{factors[1].name}</text>
    {factors[2] ? <text x={425} y={245} className="chart-axis-label" textAnchor="middle">{factors[2].name}</text> : null}
  </svg><p className="factorial-point-detail" aria-live="polite">{selected ? `${selected.label}: ${factorialNumber(selected.value)}` : "\u00a0"}</p>
  <ul className="factorial-plot-legend">{factors.map((factor) => <li key={factor.name}>{factor.name}: {factor.levels.map((level) => String(level.actual)).join(" / ")}</li>)}</ul></div>;
}
