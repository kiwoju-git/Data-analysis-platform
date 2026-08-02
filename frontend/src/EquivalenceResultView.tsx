import type { AnalysisResultEnvelope, EquivalenceTostResult } from "./api";
import { InteractiveEquivalencePlot } from "./charts/InteractiveEquivalencePlot";

export function EquivalenceResultView({
  analysisResult,
  result,
}: {
  analysisResult: AnalysisResultEnvelope | null;
  result: EquivalenceTostResult | null;
}) {
  if (result === null) return null;
  return (
    <>
      {analysisResult?.warnings.length ? (
        <ul className="warning-list" aria-label="분석 경고">
          {analysisResult.warnings.map((warning, index) => <li key={`${warning.code}-${index}`}>{warning.message}</li>)}
        </ul>
      ) : null}
      <div className="metadata-grid" aria-label="동등성 검정 요약">
        <span>설계</span><strong>{designLabel(result)}</strong>
        <span>추정량 정의</span><strong>{estimateDefinition(result)}</strong>
        <span>사용 N</span><strong>{sampleSize(result)}</strong>
        <span>평균 차이</span><strong>{formatNumber(result.estimate.value)}</strong>
        <span>판정</span><strong>{result.tost.equivalent ? "동등성 근거 있음" : "동등성 근거 부족"}</strong>
      </div>
      <InteractiveEquivalencePlot result={result} />
      <div className="table-wrap">
        <table className="result-table">
          <thead><tr><th>검정</th><th>한계</th><th>t</th><th>df</th><th>p-value</th><th>결정</th></tr></thead>
          <tbody>
            <TestRow label="하한 단측" test={result.tests.lower} />
            <TestRow label="상한 단측" test={result.tests.upper} />
          </tbody>
        </table>
      </div>
      <div className="metadata-grid" aria-label="동등성 한계와 신뢰구간">
        <span>동등성 구간</span><strong>{formatNumber(result.equivalence_bounds.lower)} ~ {formatNumber(result.equivalence_bounds.upper)}</strong>
        <span>{formatPercent(result.confidence_interval.level)} CI</span><strong>{formatNumber(result.confidence_interval.lower)} ~ {formatNumber(result.confidence_interval.upper)}</strong>
        <span>TOST p-value</span><strong>{formatNumber(result.tost.p_value)}</strong>
        {result.variance_assumption ? <><span>분산 가정</span><strong>{result.variance_assumption === "welch" ? "등분산 가정 안 함 (Welch)" : "등분산 가정 (pooled)"}</strong></> : null}
        {result.n_complete_pairs !== undefined ? <><span>완전한 쌍</span><strong>{result.n_complete_pairs.toLocaleString()}</strong><span>불완전한 쌍</span><strong>{(result.n_incomplete_pairs ?? 0).toLocaleString()}</strong></> : null}
      </div>
      <div className="notice-box">
        동등성 근거 부족은 두 모집단이 다르다는 뜻이 아닙니다. 현재 표본과 사전 지정 한계로 동등성을 입증하기에 근거가 부족하다는 뜻입니다. 일반 t-검정에서 차이가 유의하지 않았다는 사실만으로 동등하다고 결론낼 수 없습니다.
      </div>
    </>
  );
}

function TestRow({ label, test }: { label: string; test: EquivalenceTostResult["tests"]["lower"] }) {
  return <tr><td>{label}</td><td>{formatNumber(test.bound)}</td><td>{formatNumber(test.statistic)}</td><td>{formatNumber(test.df)}</td><td>{formatNumber(test.p_value)}</td><td>{test.reject_null ? "기각" : "기각 안 함"}</td></tr>;
}

function designLabel(result: EquivalenceTostResult): string {
  if (result.design === "two_sample_independent_mean_difference") return "독립 2-표본 평균 차이";
  if (result.design === "paired_mean_difference") return "대응표본 평균 차이";
  return "1-표본 평균";
}

function estimateDefinition(result: EquivalenceTostResult): string {
  if (result.design === "two_sample_independent_mean_difference") return `${result.test_group_label ?? "시험군"} - ${result.reference_group_label ?? "기준군"}`;
  if (result.design === "paired_mean_difference") return `${result.test_column?.display_name ?? "시험 측정"} - ${result.reference_column?.display_name ?? "기준 측정"}`;
  return `${result.response.display_name} 평균 - 기준 평균`;
}

function sampleSize(result: EquivalenceTostResult): string {
  if (result.design === "paired_mean_difference") return `${result.n_complete_pairs ?? result.n_used}쌍 / ${result.n_total.toLocaleString()}행`;
  return `${result.n_used.toLocaleString()} / ${result.n_total.toLocaleString()}`;
}

function formatPercent(value: number): string { return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1, style: "percent" }).format(value); }
function formatNumber(value: number | null): string { return value === null || !Number.isFinite(value) ? "-" : new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 6 }).format(value); }
