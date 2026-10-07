import { useState } from "react";
import { InteractiveScatterChart } from "./InteractiveScatterChart";

// Browser-only fixture: no application route or production entry imports this module.
export function ChartInteractionFixture() {
  const [source, setSource] = useState("analysis:1");
  const [remove, setRemove] = useState(false);
  const [locale, setLocale] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [selectCount, setSelectCount] = useState(0);
  const [shift, setShift] = useState(false);
  const points = [1, 2, 3].filter((value) => !remove || value !== 1).map((value) => ({
    id: `point:${value}`, x: value, y: shift ? 4 - value : value,
    title: `Point ${value}`, ariaLabel: `Point ${value}`, className: "scatter-point",
    details: [{ label: "Saved value", value: String(value) }],
  }));
  return <main>
    <button onClick={() => setLocale((value) => !value)}>Locale</button>
    <button onClick={() => setSource("analysis:2")}>Replace result</button>
    <button onClick={() => setRemove(true)}>Remove point</button>
    <button onClick={() => setSelected("point:3")}>External selection</button>
    <button onClick={() => setShift((value) => !value)}>Move coordinates</button>
    <output data-testid="selection-count">{selectCount}</output>
    <output data-testid="selection">{selected ?? "none"}</output>
    <div style={{ width: "min(660px, 100%)", marginTop: 80, overflow: "hidden" }}>
      <InteractiveScatterChart annotations={[]} chartId="fixture" description="Stored synthetic points"
        sourceKey={source} emptyLabel="Empty" formatValue={String} points={points}
        title={locale ? "Synthetic chart" : "Chart"} xLabel="X" yLabel="Y"
        xRange={{ min: 0, max: 3 }} yRange={{ min: 0, max: 3 }}
        selectedPointId={selected} onPointSelect={(id) => { setSelected(id); setSelectCount((value) => value + 1); }}
        onSelectionClear={() => setSelected(null)} />
    </div>
    <button>After chart</button>
    <div style={{ height: 1200 }} />
  </main>;
}
