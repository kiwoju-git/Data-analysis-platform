import { useId } from "react";

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
  const selected = runs.find((run) => run.run_order === selectedRunOrder) ?? null;

  const moveSelection = (offset: number) => {
    if (runs.length === 0) return;
    const current = runs.findIndex((run) => run.run_order === selectedRunOrder);
    const next = current < 0
      ? offset < 0 ? runs.length - 1 : 0
      : Math.min(runs.length - 1, Math.max(0, current + offset));
    onSelectRun(runs[next].run_order);
  };

  return (
    <div className="lhs-parallel-chart-scroll">
      <div
        className="interactive-chart lhs-parallel-chart"
        onKeyDown={(event) => {
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
            event.preventDefault();
            moveSelection(-1);
          } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
            event.preventDefault();
            moveSelection(1);
          } else if (event.key === "Home" && runs.length > 0) {
            event.preventDefault();
            onSelectRun(runs[0].run_order);
          } else if (event.key === "End" && runs.length > 0) {
            event.preventDefault();
            onSelectRun(runs[runs.length - 1].run_order);
          } else if (event.key === "Escape") {
            onSelectRun(null);
          } else if ((event.key === "Enter" || event.key === " ") && runs.length > 0) {
            event.preventDefault();
            onSelectRun(selectedRunOrder ?? runs[0].run_order);
          }
        }}
        tabIndex={0}
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
                className={`lhs-parallel-run${isSelected ? " lhs-parallel-run-selected" : ""}`}
                data-run-order={run.run_order}
                key={run.run_order}
                onClick={() => onSelectRun(run.run_order)}
                onPointerEnter={() => onSelectRun(run.run_order)}
                points={points}
              >
                <title>{`Run ${run.run_order}`}</title>
              </polyline>
            );
          })}
        </svg>
        <div className="chart-selected-detail" aria-live="polite">
          {selected === null ? (
            <span>선을 가리키거나 차트에 초점을 둔 뒤 화살표 키로 실험을 확인하세요.</span>
          ) : (
            <>
              <strong>{`Run ${selected.run_order}`}</strong>
              {factors.map((factor) => (
                <span key={factor.name}>
                  {factor.name}: {format(selected.factor_levels[factor.name])}
                  {factor.unit ? ` ${factor.unit}` : ""}
                </span>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function format(value: number) {
  return Number.isFinite(value) ? value.toPrecision(6).replace(/\.?0+$/, "") : "-";
}
