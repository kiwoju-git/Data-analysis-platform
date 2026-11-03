import { useId, type ReactNode } from "react";
import "./ResultMetricCard.css";

interface ResultMetricCardProps {
  metricId: string;
  label: ReactNode;
  value: ReactNode;
  children?: ReactNode;
}

export function ResultMetricCard({ metricId, label, value, children }: ResultMetricCardProps) {
  const labelId = useId();
  return (
    <article className="result-metric-card" data-result-metric={metricId} aria-labelledby={labelId}>
      <h5 className="result-metric-card-label" id={labelId}>{label}</h5>
      <strong className="result-metric-card-value">{value}</strong>
      {children}
    </article>
  );
}
