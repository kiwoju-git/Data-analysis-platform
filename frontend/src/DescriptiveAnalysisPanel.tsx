import { Fragment, useEffect, useRef } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  DescriptiveStatisticsResult,
  GraphicalSummaryResult,
} from "./api";
import { GraphicalSummaryColumnVisuals } from "./GraphicalSummaryColumnVisuals";

export interface DescriptiveQuickGraphState {
  columnId: string | null;
  error: string | null;
  result: GraphicalSummaryResult | null;
  status: "idle" | "loading" | "ready" | "error";
}

interface DescriptiveAnalysisPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  descriptiveColumns: DatasetColumnResponse[];
  descriptiveResult: DescriptiveStatisticsResult | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  quickGraphState?: DescriptiveQuickGraphState;
  selectedColumnIds: string[];
  version: DatasetVersionResponse | null;
  onOpenFullGraphicalSummary?: (columnId: string) => void;
  onRetryQuickGraph?: () => void;
  onRun: () => void;
  onToggleColumn: (columnId: string, checked: boolean) => void;
  onToggleQuickGraph?: (columnId: string) => void;
}

const idleQuickGraphState: DescriptiveQuickGraphState = {
  columnId: null,
  error: null,
  result: null,
  status: "idle",
};

export function DescriptiveAnalysisPanel({
  analysisResult,
  descriptiveColumns,
  descriptiveResult,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  quickGraphState = idleQuickGraphState,
  selectedColumnIds,
  version,
  onOpenFullGraphicalSummary = () => undefined,
  onRetryQuickGraph = () => undefined,
  onRun,
  onToggleColumn,
  onToggleQuickGraph = () => undefined,
}: DescriptiveAnalysisPanelProps) {
  const quickResultRef = useRef<HTMLDivElement | null>(null);
  const focusQuickResultRef = useRef(false);

  useEffect(() => {
    if (quickGraphState.status === "ready" && focusQuickResultRef.current) {
      quickResultRef.current?.focus();
      focusQuickResultRef.current = false;
    }
  }, [quickGraphState.status, quickGraphState.columnId]);

  return (
    <section className="analysis-run-panel" aria-labelledby="descriptive-title">
      <div className="panel-heading">
        <div>
          <h3 id="descriptive-title">기술통계 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="column-picker" aria-label="기술통계 컬럼 선택">
            {descriptiveColumns.map((column) => (
              <label key={column.column_id}>
                <input
                  checked={selectedColumnIds.includes(column.column_id)}
                  type="checkbox"
                  onChange={(event) => {
                    onToggleColumn(column.column_id, event.currentTarget.checked);
                  }}
                />
                <span>{column.display_name}</span>
              </label>
            ))}
          </div>
          <button
            className="primary-button"
            disabled={
              isRunningAnalysis ||
              selectedColumnIds.length === 0 ||
              filterValidationError !== null
            }
            onClick={onRun}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "기술통계 실행"}
          </button>
          {analysisResult?.provenance.row_count_included !== undefined &&
          analysisResult.provenance.row_count_included !== null ? (
            <div className="metadata-grid" aria-label="분석 사용 행">
              <span>사용 행</span>
              <strong>
                {analysisResult.provenance.row_count_included.toLocaleString()} /{" "}
                {(
                  analysisResult.provenance.row_count_total ??
                  analysisResult.provenance.row_count_included
                ).toLocaleString()}
              </strong>
            </div>
          ) : null}
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {descriptiveResult !== null ? (
            <div className="table-wrap">
              <table className="result-table descriptive-result-table">
                <thead>
                  <tr>
                    <th>컬럼</th>
                    <th>N</th>
                    <th>결측</th>
                    <th>평균</th>
                    <th>표준편차</th>
                    <th>최소</th>
                    <th>Q1</th>
                    <th>중앙값</th>
                    <th>Q3</th>
                    <th>최대</th>
                  </tr>
                </thead>
                <tbody>
                  {descriptiveResult.columns.map((column) => {
                    const expanded = quickGraphState.columnId === column.column_id;
                    const quickColumn = quickGraphState.result?.columns.find(
                      (candidate) => candidate.column_id === column.column_id,
                    );
                    const panelId = `descriptive-quick-graph-${column.column_id}`;
                    return (
                      <Fragment key={column.column_id}>
                        <tr>
                          <td>
                            <button
                              aria-controls={panelId}
                              aria-expanded={expanded}
                              className="table-link-button"
                              onClick={(event) => {
                                focusQuickResultRef.current = event.detail === 0;
                                onToggleQuickGraph(column.column_id);
                              }}
                              type="button"
                            >
                              {column.display_name} 그래프 보기
                            </button>
                          </td>
                          <td>{column.n_used}</td>
                          <td>{column.n_missing}</td>
                          <td>{formatAnalysisNumber(column.mean)}</td>
                          <td>{formatAnalysisNumber(column.std)}</td>
                          <td>{formatAnalysisNumber(column.min)}</td>
                          <td>{formatAnalysisNumber(column.q1)}</td>
                          <td>{formatAnalysisNumber(column.median)}</td>
                          <td>{formatAnalysisNumber(column.q3)}</td>
                          <td>{formatAnalysisNumber(column.max)}</td>
                        </tr>
                        {expanded ? (
                          <tr className="descriptive-quick-graph-row">
                            <td colSpan={10}>
                              <div
                                aria-busy={quickGraphState.status === "loading"}
                                className="descriptive-quick-graph"
                                id={panelId}
                                ref={quickResultRef}
                                tabIndex={-1}
                              >
                                {quickGraphState.status === "loading" ? (
                                  <div role="status">그래프 요약 분석 실행 중</div>
                                ) : null}
                                {quickGraphState.status === "error" ? (
                                  <div className="error-box" role="alert">
                                    빠른 그래프를 불러오지 못했습니다. 오류 코드:{" "}
                                    {quickGraphState.error}
                                    <button
                                      className="secondary-button"
                                      onClick={onRetryQuickGraph}
                                      type="button"
                                    >
                                      다시 시도
                                    </button>
                                  </div>
                                ) : null}
                                {quickGraphState.status === "ready" && quickColumn !== undefined ? (
                                  <>
                                    <GraphicalSummaryColumnVisuals
                                      column={quickColumn}
                                      mode="quick"
                                    />
                                    <div className="inline-actions">
                                      <span className="cell-subtle">
                                        현재 데이터셋과 필터 조건의 그래프 요약 분석으로
                                        저장되었습니다.
                                      </span>
                                      <button
                                        className="secondary-button"
                                        onClick={() =>
                                          onOpenFullGraphicalSummary(column.column_id)
                                        }
                                        type="button"
                                      >
                                        그래프 요약에서 전체 보기
                                      </button>
                                    </div>
                                  </>
                                ) : null}
                              </div>
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
