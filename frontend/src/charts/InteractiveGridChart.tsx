import type { KeyboardEvent } from "react";
import { t } from "../i18n/translate";
import { ChartAxes } from "./ChartAxes";
import { ChartFrame } from "./ChartFrame";
import { ChartItemFeedback, type ChartDetailItem } from "./ChartItemFeedback";
import { STANDARD_CHART_LAYOUT, axisTitle, formatChartTick } from "./chartLayout";
import { expandNumericRange, paddedNumericRange, scaleChartValue, type NumericRange } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

export interface GridChartCell extends ChartDetailItem { x: number; y: number; value: number }

export function InteractiveGridChart({ chartId, title, description, cells, xLabel, yLabel, valueLabel,
  xUnit, yUnit, valueUnit, xRange, yRange, sourceKey }: {
  chartId: string; title: string; description: string; cells: readonly GridChartCell[];
  xLabel: string; yLabel: string; valueLabel: string;
  xUnit?: string | null; yUnit?: string | null; valueUnit?: string | null;
  xRange?: NumericRange; yRange?: NumericRange; sourceKey?: string;
}) {
  const identities = new Map<string, number>();
  const coordinates = new Map<string, number>();
  cells.forEach((cell) => {
    identities.set(cell.id, (identities.get(cell.id) ?? 0) + 1);
    const key = JSON.stringify([cell.x, cell.y]);
    coordinates.set(key, (coordinates.get(key) ?? 0) + 1);
  });
  const valid = cells.filter((cell) => [cell.x, cell.y, cell.value].every(Number.isFinite) &&
    identities.get(cell.id) === 1 && coordinates.get(JSON.stringify([cell.x, cell.y])) === 1);
  const interaction = useChartItemInteraction(valid.map((cell) => cell.id), { sourceKey });
  const xDomain = expandNumericRange(xRange ?? paddedNumericRange(valid.map((cell) => cell.x), 0), valid.map((cell) => cell.x));
  const yDomain = expandNumericRange(yRange ?? paddedNumericRange(valid.map((cell) => cell.y), 0), valid.map((cell) => cell.y));
  const xs = [...new Set(valid.map((cell) => cell.x))].sort((a, b) => a - b);
  const ys = [...new Set(valid.map((cell) => cell.y))].sort((a, b) => a - b);
  const boundaries = (values: number[], range: NumericRange) => [range.min, ...values.slice(1).map((value, index) => values[index] / 2 + value / 2), range.max];
  const xb = boundaries(xs, xDomain); const yb = boundaries(ys, yDomain);
  const values = valid.map((cell) => cell.value);
  const low = values.length ? Math.min(...values) : 0; const high = values.length ? Math.max(...values) : 0;
  const layout = STANDARD_CHART_LAYOUT; const { plot } = layout;
  const x = (value: number) => scaleChartValue(value, xDomain, plot.left, plot.left + plot.width);
  const y = (value: number) => scaleChartValue(value, yDomain, plot.top + plot.height, plot.top);
  function onKey(event: KeyboardEvent<SVGElement>, cell: GridChartCell) {
    const direction = event.key;
    if (!direction.startsWith("Arrow")) return interaction.handleKeyDown(event, cell.id);
    const candidates = valid.filter((other) => direction === "ArrowLeft" ? other.y === cell.y && other.x < cell.x
      : direction === "ArrowRight" ? other.y === cell.y && other.x > cell.x
        : direction === "ArrowUp" ? other.x === cell.x && other.y > cell.y
          : other.x === cell.x && other.y < cell.y);
    const nearest = candidates.sort((a, b) => Math.abs(a.x - cell.x) + Math.abs(a.y - cell.y) - Math.abs(b.x - cell.x) - Math.abs(b.y - cell.y))[0];
    event.preventDefault();
    if (nearest) {
      const index = valid.findIndex((item) => item.id === nearest.id);
      event.currentTarget.ownerSVGElement?.querySelectorAll<SVGElement>("[data-grid-cell]")[index]?.focus();
    }
  }
  if (valid.length === 0) return <div className="empty-state">{t("charts.noData")}
    {cells.length > 0 && <p>{t("charts.invalidData", { count: cells.length })}</p>}</div>;
  return <ChartFrame chartId={chartId} title={title} description={description} layout={layout}
    axes={<ChartAxes layout={layout} grid={false} x={{ label: xLabel, unit: xUnit, range: xDomain }} y={{ label: yLabel, unit: yUnit, range: yDomain }} />}
    footer={<>
      <div className="chart-color-scale"><strong>{axisTitle(valueLabel, valueUnit)}</strong>
        {low === high ? <span>{t("charts.constantGrid", { value: formatChartTick(low) })}</span>
          : <><span>{formatChartTick(low)}</span><span aria-hidden="true" className="chart-color-scale-ramp" /><span>{formatChartTick(high)}</span></>}
      </div>
      {valid.length !== cells.length && <p>{t("charts.invalidData", { count: cells.length - valid.length })}</p>}
      <ChartItemFeedback interaction={interaction} items={valid} />
    </>}>
    {valid.map((cell) => {
      const xi = xs.indexOf(cell.x); const yi = ys.indexOf(cell.y);
      const ratio = high === low ? 0.5 : (cell.value - low) / (high - low);
      const color = [230 - 212 * ratio, 241 - 141 * ratio, 248 - 85 * ratio].map(Math.round);
      return <rect key={cell.id} data-grid-cell={cell.id} role="img" aria-label={`${xLabel} ${cell.x}; ${yLabel} ${cell.y}; ${valueLabel} ${cell.value}`}
        aria-describedby={interaction.describedBy(cell.id)} className={interaction.stateClass(cell.id)}
        fill={`rgb(${color.join(",")})`} x={x(xb[xi])} y={y(yb[yi + 1])} width={x(xb[xi + 1]) - x(xb[xi])} height={y(yb[yi]) - y(yb[yi + 1])}
        tabIndex={interaction.tabIndexFor(cell.id)} ref={(element) => interaction.itemRef(cell.id, element)}
        onFocus={() => interaction.activateItem(cell.id, "focus")} onBlur={() => interaction.clearFocus(cell.id)}
        onPointerEnter={(event) => interaction.move(cell.id, event)} onPointerMove={(event) => interaction.move(cell.id, event)} onPointerLeave={() => interaction.clearHover(cell.id)}
        onClick={() => interaction.pin(cell.id)} onKeyDown={(event) => onKey(event, cell)}><title>{cell.title}</title></rect>;
    })}
  </ChartFrame>;
}
