import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  EquivalenceTostResult,
} from "./api";
import { EquivalenceResultView } from "./EquivalenceResultView";

interface EquivalenceTostPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  lowerBound: number;
  methodId: string;
  referenceMean: number;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: EquivalenceTostResult | null;
  upperBound: number;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onLowerBoundChange: (lowerBound: number) => void;
  onReferenceMeanChange: (referenceMean: number) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
  onUpperBoundChange: (upperBound: number) => void;
}

export function EquivalenceTostPanel({
  alpha,
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  lowerBound,
  methodId,
  referenceMean,
  responseColumnId,
  responseColumns,
  result,
  upperBound,
  version,
  onAlphaChange,
  onLowerBoundChange,
  onReferenceMeanChange,
  onResponseColumnChange,
  onRun,
  onUpperBoundChange,
}: EquivalenceTostPanelProps) {
  const confidenceLevel = 1 - 2 * alpha;
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    Number.isFinite(referenceMean) &&
    Number.isFinite(lowerBound) &&
    Number.isFinite(upperBound) &&
    lowerBound < upperBound &&
    alpha > 0 &&
    alpha < 0.5 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <label>
              <span>반응 변수</span>
              <select
                value={responseColumnId ?? ""}
                onChange={(event) => {
                  onResponseColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {responseColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>기준 평균</span>
              <input
                step="any"
                type="number"
                value={referenceMean}
                onChange={(event) => {
                  onReferenceMeanChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>동등성 하한</span>
              <input
                step="any"
                type="number"
                value={lowerBound}
                onChange={(event) => {
                  onLowerBoundChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>동등성 상한</span>
              <input
                step="any"
                type="number"
                value={upperBound}
                onChange={(event) => {
                  onUpperBoundChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>유의수준 alpha</span>
              <input
                max="0.499"
                min="0.001"
                step="0.001"
                type="number"
                value={alpha}
                onChange={(event) => {
                  onAlphaChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <div className="readonly-field">
              <span>TOST CI 수준</span>
              <strong>{formatPercent(confidenceLevel)}</strong>
            </div>
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "동등성 검정 실행"}
          </button>
          <EquivalenceResultView analysisResult={analysisResult} result={result} />
        </>
      )}
    </section>
  );
}

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 1,
    style: "percent",
  }).format(value);
}
