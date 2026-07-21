export interface ChartTooltipProps {
  details: Array<{ label: string; value: string }>;
  left: number;
  title: string;
  top: number;
}

export function ChartTooltip({ details, left, title, top }: ChartTooltipProps) {
  return (
    <div
      className="chart-tooltip"
      role="status"
      style={{ left: `${left}px`, top: `${top}px` }}
    >
      <strong>{title}</strong>
      <dl>
        {details.map((detail) => (
          <div key={detail.label}>
            <dt>{detail.label}</dt>
            <dd>{detail.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
