import { useState } from "react";
import { LocaleProvider, useI18n } from "../i18n/LocaleProvider";
import { InteractiveScatterChart, type InteractiveScatterChartProps } from "./InteractiveScatterChart";
import numericCases from "../../../tests/fixtures/numeric_display_cases.json";

const points = [
  { id: "row:7", x: 1, y: 0.25, title: "User \ue000name & <stored>", ariaLabel: "Row 7", className: "scatter-point", details: [{ label: "Saved Y", value: "0.25" }] },
  { id: "row:9", x: 2, y: 0.75, title: "Row 9", ariaLabel: "Row 9", className: "scatter-point", details: [{ label: "Saved Y", value: "0.75" }] },
];

// Browser-only synthetic fixture, never imported by the application route graph.
export function ChartFormattingFixture() {
  return <LocaleProvider><FormatterControls /></LocaleProvider>;
}

function FormatterControls() {
  const { locale, setLocale, formatPercent } = useI18n();
  const [mode, setMode] = useState("axis");
  const [source, setSource] = useState(1);
  const [selectionCount, setSelectionCount] = useState(0);
  const formatting: Partial<InteractiveScatterChartProps> = mode === "common" ? {} : {
    formatValue: (value) => `legacy:${value}`,
    ...(mode === "legacy" ? {} : {
      xFormatValue: (value: number) => `${locale}:${value.toFixed(1)}`,
      yFormatValue: (value: number) => formatPercent(value),
    }),
    ...(mode === "explicit" ? { xTicks: [0, 1, 2].map((value) => ({ value, label: `PC${value} \ue000 & <stored>` })) } : {}),
  };
  return <main style={{ padding: 16, maxWidth: 1000, margin: "auto" }}>
    <h1>Axis formatter fixture</h1>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      <button onClick={() => setLocale("ko")}>KOR</button>
      <button onClick={() => setLocale("en")}>ENG</button>
      <label>Formatter policy<select value={mode} onChange={(event) => setMode(event.currentTarget.value)}>
        <option value="axis">Per axis</option><option value="legacy">Legacy</option>
        <option value="common">Common locale</option><option value="explicit">Explicit labels</option>
      </select></label>
      <button onClick={() => setSource((value) => value + 1)}>Replace source</button>
      <output data-testid="select-count">{selectionCount}</output>
      <output data-testid="source">{source}</output>
    </div>
    <InteractiveScatterChart chartId="formatter" sourceKey={`saved:${source}`} title="Mixed numeric axes"
      description="Stored fractions, display-only percent labels" annotations={[]} emptyLabel="Empty"
      points={points} xLabel={"X \ue000 & <stored>"} xUnit="s" yLabel="Saved fraction" yUnit="ratio"
      xRange={{ min: 0, max: 2 }} yRange={{ min: -0.5, max: 1 }}
      referenceLines={[{ label: "Zero", x1: 0, x2: 2, y1: 0, y2: 0 }]}
      onPointSelect={() => setSelectionCount((value) => value + 1)} {...formatting} />
    <InteractiveScatterChart chartId="common-formatter" sourceKey="common:1" title="Common numeric fallback"
      description="Finite saved values only" annotations={[]} emptyLabel="Empty"
      points={[{ ...points[0], x: 2000, y: 2e-8 }]} xLabel="Count" yLabel="Small value"
      xRange={{ min: 1000, max: 5000 }} yRange={{ min: 0, max: 8e-8 }} />
    {numericCases.filter((item) => ["narrow-positive", "large-origin", "narrow-negative"].includes(item.id)).map((item) =>
      <InteractiveScatterChart key={item.id} chartId={`numeric-${item.id}`} sourceKey={`numeric:${item.id}`} title={item.id}
        description="Stored numeric coordinates; adaptive display only" annotations={[]} emptyLabel="Empty"
        points={[item.min, item.max].map((value, index) => ({ ...points[0], id: `${item.id}:${index}`, x: value, y: index, ariaLabel: `${item.id} ${value}`, details: [{ label: "Saved X", value: String(value) }] }))}
        xLabel="Stored X" xUnit="mg/L" yLabel="Count" xRange={{ min: item.min, max: item.max }} yRange={{ min: 0, max: 1 }} />)}
  </main>;
}
