import { useId } from "react";
import { useChartItemInteraction } from "./useChartItemInteraction";
import { ChartItemFeedback } from "./ChartItemFeedback";

interface ParallelFactor {
  name: string;
  low: number;
  high: number;
  unit?: string | null;
  domain_kind?: "continuous" | "discrete_numeric";
  level_count?: number | null;
}

interface ParallelRun {
  run_order: number;
  standard_order: number;
  factor_levels: Record<string, number>;
  normalized_levels: Record<string, number>;
}

export function InteractiveParallelCoordinatesChart({
  factors,
  mode,
  onSelectRun,
  runs,
  selectedRunOrder,
}: {
  factors: ParallelFactor[];
  mode: "actual" | "normalized";
  onSelectRun: (runOrder: number | null) => void;
  runs: ParallelRun[];
  selectedRunOrder: number | null;
}) {
  const id = useId().replace(/:/g, "");
  const width = Math.max(640, 120 + factors.length * 130);
  const height = 330;
  const left = 54;
  const right = 36;
  const top = 34;
  const bottom = 62;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const xAt = (index: number) =>
    factors.length === 1 ? left + plotWidth / 2 : left + index * (plotWidth / (factors.length - 1));
  const yAt = (factor: ParallelFactor, run: ParallelRun) => {
    const normalized = mode === "normalized"
      ? run.normalized_levels[factor.name]
      : (run.factor_levels[factor.name] - factor.low) / (factor.high - factor.low);
    return top + (1 - normalized) * plotHeight;
  };
  const interaction = useChartItemInteraction(runs.map((run) => `run:${run.run_order}`), {
    selectedId: selectedRunOrder === null ? null : `run:${selectedRunOrder}`,
    onSelect: (runId) => onSelectRun(Number(runId.slice(4))),
    onClear: () => onSelectRun(null),
  });

  return (
    <div className="lhs-parallel-chart-scroll">
      <div
        className="interactive-chart lhs-parallel-chart"
        onKeyDown={(event) => interaction.handleKeyDown(event)}
      >
        <svg
          aria-labelledby={`${id}-title ${id}-description`}
          className="chart-svg lhs-parallel-svg"
          role="img"
          viewBox={`0 0 ${width} ${height}`}
        >
          <title id={`${id}-title`}>LHS 평행좌표 그림</title>
          <desc id={`${id}-description`}>
            {`${runs.length}개 실험을 ${factors.length}개 요인 축에 연결합니다. 화살표 키로 실험을 선택할 수 있습니다.`}
          </desc>
          {factors.map((factor, index) => {
            const x = xAt(index);
            const high = mode === "normalized" ? "1" : format(factor.high);
            const low = mode === "normalized" ? "0" : format(factor.low);
            return (
              <g key={factor.name}>
                <line className="chart-axis" x1={x} x2={x} y1={top} y2={top + plotHeight} />
                <text className="chart-axis-title" textAnchor="middle" x={x} y={height - 24}>
                  {factor.name}
                </text>
                <text className="chart-axis-label" textAnchor="middle" x={x} y={top - 10}>
                  {high}{mode === "actual" && factor.unit ? ` ${factor.unit}` : ""}
                </text>
                <text className="chart-axis-label" textAnchor="middle" x={x} y={top + plotHeight + 18}>
                  {low}
                </text>
                {factor.domain_kind === "discrete_numeric" ? (
                  <text className="chart-axis-label" textAnchor="middle" x={x} y={height - 8}>
                    {factor.level_count ?? "-"}개 실행 수준
                  </text>
                ) : null}
              </g>
            );
          })}
          {runs.map((run) => {
            const isSelected = run.run_order === selectedRunOrder;
            const points = factors
              .map((factor, index) => `${xAt(index)},${yAt(factor, run)}`)
              .join(" ");
            return (
              <polyline
                aria-label={`Run ${run.run_order}`}
                className={`lhs-parallel-run ${interaction.stateClass(`run:${run.run_order}`)}${isSelected ? " lhs-parallel-run-selected" : ""}`}
                data-run-order={run.run_order}
                key={run.run_order}
                onClick={() => interaction.pin(`run:${run.run_order}`)}
                onFocus={() => interaction.activateItem(`run:${run.run_order}`, "focus")}
                onBlur={() => interaction.clearFocus(`run:${run.run_order}`)}
                onPointerEnter={(event) => interaction.move(`run:${run.run_order}`, event)}
                onPointerMove={(event) => interaction.move(`run:${run.run_order}`, event)}
                onPointerLeave={() => interaction.clearHover(`run:${run.run_order}`)}
                onKeyDown={(event) => interaction.handleKeyDown(event, `run:${run.run_order}`)}
                ref={(element) => interaction.itemRef(`run:${run.run_order}`, element)}
                tabIndex={interaction.tabIndexFor(`run:${run.run_order}`)}
                aria-describedby={interaction.describedBy(`run:${run.run_order}`)}
                role="img"
                points={points}
              >
                <title>{`Run ${run.run_order}`}</title>
              </polyline>
            );
          })}
        </svg>
        <ChartItemFeedback interaction={interaction} items={runs.map((run) => ({
          id: `run:${run.run_order}`, title: `Run ${run.run_order}`,
          details: factors.map((factor) => ({ label: factor.name,
            value: `${format(run.factor_levels[factor.name])}${factor.unit ? ` ${factor.unit}` : ""}` })),
        }))} />
      </div>
    </div>
  );
}

function format(value: number) {
  return Number.isFinite(value) ? value.toPrecision(6).replace(/\.?0+$/, "") : "-";
}
