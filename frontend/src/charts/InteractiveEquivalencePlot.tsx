import type { EquivalenceTostResult } from "../api";

export function InteractiveEquivalencePlot({ result }: { result: EquivalenceTostResult }) {
  const values = [
    result.equivalence_bounds.lower,
    result.equivalence_bounds.upper,
    result.confidence_interval.lower,
    result.confidence_interval.upper,
    result.estimate.value,
    0,
  ];
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const padding = Math.max((maximum - minimum) * 0.12, 0.1);
  const domainMinimum = minimum - padding;
  const domainMaximum = maximum + padding;
  const x = (value: number) => 54 + ((value - domainMinimum) / (domainMaximum - domainMinimum)) * 532;
  const decision = result.tost.equivalent ? "동등성 근거 있음" : "동등성 근거 부족";
  const description = `${estimateDefinition(result)}. 점 추정치 ${formatNumber(result.estimate.value)}, ${formatPercent(result.confidence_interval.level)} 신뢰구간 ${formatNumber(result.confidence_interval.lower)}에서 ${formatNumber(result.confidence_interval.upper)}, 동등성 한계 ${formatNumber(result.equivalence_bounds.lower)}에서 ${formatNumber(result.equivalence_bounds.upper)}. ${decision}.`;

  return (
    <div className="interactive-chart equivalence-plot">
      <svg
        aria-label={description}
        className="chart-svg chart-svg-wide interactive-chart-svg"
        role="img"
        viewBox="0 0 640 150"
      >
        <title>동등성 신뢰구간</title>
        <desc>{description}</desc>
        <line className="equivalence-axis" x1="54" x2="586" y1="88" y2="88" />
        <line className="equivalence-zero" x1={x(0)} x2={x(0)} y1="40" y2="112" />
        <line className="equivalence-bound" x1={x(result.equivalence_bounds.lower)} x2={x(result.equivalence_bounds.lower)} y1="50" y2="106" />
        <line className="equivalence-bound" x1={x(result.equivalence_bounds.upper)} x2={x(result.equivalence_bounds.upper)} y1="50" y2="106" />
        <line className="equivalence-ci" x1={x(result.confidence_interval.lower)} x2={x(result.confidence_interval.upper)} y1="72" y2="72" />
        <line className="equivalence-ci-cap" x1={x(result.confidence_interval.lower)} x2={x(result.confidence_interval.lower)} y1="64" y2="80" />
        <line className="equivalence-ci-cap" x1={x(result.confidence_interval.upper)} x2={x(result.confidence_interval.upper)} y1="64" y2="80" />
        <circle
          aria-label={`점 추정치 ${formatNumber(result.estimate.value)}`}
          className="equivalence-estimate"
          cx={x(result.estimate.value)}
          cy="72"
          r="6"
          tabIndex={0}
        />
        <text x={x(result.equivalence_bounds.lower)} y="130" textAnchor="middle">하한 {formatNumber(result.equivalence_bounds.lower)}</text>
        <text x={x(result.equivalence_bounds.upper)} y="130" textAnchor="middle">상한 {formatNumber(result.equivalence_bounds.upper)}</text>
      </svg>
      <p className="chart-description">{description}</p>
    </div>
  );
}

function estimateDefinition(result: EquivalenceTostResult): string {
  if (result.design === "two_sample_independent_mean_difference") return "평균 차이 = 시험군 - 기준군";
  if (result.design === "paired_mean_difference") return "평균 차이 = 시험 측정 - 기준 측정";
  return "평균 차이 = 표본 평균 - 기준 평균";
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1, style: "percent" }).format(value);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 6 }).format(value);
}
