import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  XyCorrelationPairResult,
  XyCorrelationResult,
} from "./api";

interface XyCorrelationPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: XyCorrelationResult | null;
  version: DatasetVersionResponse | null;
  xColumnIds: string[];
  xColumns: DatasetColumnResponse[];
  yColumnIds: string[];
  yColumns: DatasetColumnResponse[];
  onAlphaChange: (alpha: number) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onRun: () => void;
  onToggleXColumn: (columnId: string, checked: boolean) => void;
  onToggleYColumn: (columnId: string, checked: boolean) => void;
}

export function XyCorrelationPanel({
  alpha,
  analysisResult,
  confidenceLevel,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  result,
  version,
  xColumnIds,
  xColumns,
  yColumnIds,
  yColumns,
  onAlphaChange,
  onConfidenceLevelChange,
  onRun,
  onToggleXColumn,
  onToggleYColumn,
}: XyCorrelationPanelProps) {
  const canRun =
    version !== null &&
    xColumnIds.length > 0 &&
    yColumnIds.length > 0 &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="xy-correlation-title">
      <div className="panel-heading">
        <div>
          <h3 id="xy-correlation-title">X-Y 상관행렬 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid option-grid-wide">
            <div className="checkbox-field">
              <span>X 변수 집합</span>
              <div className="checkbox-list" aria-label="X 변수 집합">
                {xColumns.map((column) => (
                  <label key={column.column_id}>
                    <input
                      checked={xColumnIds.includes(column.column_id)}
                      type="checkbox"
                      onChange={(event) => {
                        onToggleXColumn(column.column_id, event.currentTarget.checked);
                      }}
                    />
                    <span>{column.display_name}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="checkbox-field">
              <span>Y 변수 집합</span>
              <div className="checkbox-list" aria-label="Y 변수 집합">
                {yColumns.map((column) => (
                  <label key={column.column_id}>
                    <input
                      checked={yColumnIds.includes(column.column_id)}
                      type="checkbox"
                      onChange={(event) => {
                        onToggleYColumn(column.column_id, event.currentTarget.checked);
                      }}
                    />
                    <span>{column.display_name}</span>
                  </label>
                ))}
              </div>
            </div>
            <label>
              <span>유의수준 alpha</span>
              <input
                max="0.5"
                min="0.001"
                step="0.001"
                type="number"
                value={alpha}
                onChange={(event) => {
                  onAlphaChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>신뢰수준</span>
              <input
                max="0.999"
                min="0.5"
                step="0.001"
                type="number"
                value={confidenceLevel}
                onChange={(event) => {
                  onConfidenceLevelChange(Number(event.currentTarget.value));
                }}
              />
            </label>
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "X-Y 상관행렬 실행"}
          </button>
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {result !== null ? (
            <>
              <div className="metadata-grid" aria-label="X-Y 상관행렬 요약">
                <span>X 변수</span>
                <strong>{result.x_column_count.toLocaleString()}개</strong>
                <span>Y 변수</span>
                <strong>{result.y_column_count.toLocaleString()}개</strong>
                <span>조합</span>
                <strong>{result.pair_count.toLocaleString()}개</strong>
                <span>결측 처리</span>
                <strong>{result.missing_policy}</strong>
              </div>
              <div className="result-section" aria-label="X-Y 상관 Heatmap 결과">
                <div className="panel-heading">
                  <div>
                    <h4>상관 Heatmap</h4>
                    <p>Pearson r · complete-case by pair</p>
                  </div>
                </div>
                <XyCorrelationHeatmap result={result} />
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>X</th>
                      <th>Y</th>
                      <th>N</th>
                      <th>r</th>
                      <th>CI</th>
                      <th>p-value</th>
                      <th>r²</th>
                      <th>상태</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.pairs.map((pair) => (
                      <tr key={`${pair.x.column_id}-${pair.y.column_id}`}>
                        <td>{pair.x.display_name}</td>
                        <td>{pair.y.display_name}</td>
                        <td>
                          {pair.n_used.toLocaleString()} / {pair.n_total.toLocaleString()}
                          <span className="cell-subtle">
                            제외{" "}
                            {(
                              pair.n_excluded_missing_x +
                              pair.n_excluded_missing_y +
                              pair.n_excluded_non_numeric_x +
                              pair.n_excluded_non_numeric_y
                            ).toLocaleString()}
                          </span>
                        </td>
                        <td>{formatPairNumber(pair.association?.correlation ?? null)}</td>
                        <td>{confidenceIntervalLabel(pair)}</td>
                        <td>{formatPairNumber(pair.test?.p_value ?? null)}</td>
                        <td>{formatPairNumber(pair.association?.r_squared ?? null)}</td>
                        <td>
                          {pair.status === "ok" ? "계산됨" : "계산 불가"}
                          {pair.error_code !== null ? (
                            <span className="cell-subtle">{pair.error_code}</span>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function XyCorrelationHeatmap({ result }: { result: XyCorrelationResult }) {
  const pairByColumn = new Map(
    result.pairs.map((pair) => [`${pair.x.column_id}::${pair.y.column_id}`, pair]),
  );
  const gridTemplateColumns = `minmax(112px, 1.1fr) repeat(${result.x_columns.length}, minmax(96px, 1fr))`;

  return (
    <div
      className="heatmap-grid"
      role="grid"
      style={{ gridTemplateColumns }}
      aria-label="X-Y Pearson 상관 heatmap"
    >
      <div className="heatmap-axis-label heatmap-corner" role="columnheader">
        Y \\ X
      </div>
      {result.x_columns.map((column) => (
        <div key={column.column_id} className="heatmap-axis-label" role="columnheader">
          {column.display_name}
        </div>
      ))}
      {result.y_columns.flatMap((yColumn) => [
        <div key={`${yColumn.column_id}-label`} className="heatmap-axis-label" role="rowheader">
          {yColumn.display_name}
        </div>,
        ...result.x_columns.map((xColumn) => {
          const pair = pairByColumn.get(`${xColumn.column_id}::${yColumn.column_id}`);
          return (
            <HeatmapCell
              key={`${xColumn.column_id}-${yColumn.column_id}`}
              pair={pair}
              xLabel={xColumn.display_name}
              yLabel={yColumn.display_name}
            />
          );
        }),
      ])}
    </div>
  );
}

function HeatmapCell({
  pair,
  xLabel,
  yLabel,
}: {
  pair: XyCorrelationPairResult | undefined;
  xLabel: string;
  yLabel: string;
}) {
  const correlation = pair?.association?.correlation ?? null;
  const statusLabel = pair === undefined ? "missing" : pair.status === "ok" ? "ok" : pair.error_code;
  return (
    <div
      className="heatmap-cell"
      role="gridcell"
      style={heatmapCellStyle(correlation)}
      title={`${xLabel} / ${yLabel}: ${formatPairNumber(correlation)}`}
    >
      <strong>{formatPairNumber(correlation)}</strong>
      <span>
        N {pair?.n_used.toLocaleString() ?? "NA"} · {statusLabel ?? "failed"}
      </span>
    </div>
  );
}

function heatmapCellStyle(value: number | null): { backgroundColor?: string; color?: string } {
  if (value === null || !Number.isFinite(value)) {
    return {};
  }
  const magnitude = Math.min(1, Math.abs(value));
  const alpha = 0.16 + magnitude * 0.58;
  if (value >= 0) {
    return {
      backgroundColor: `rgba(29, 127, 95, ${alpha})`,
      color: magnitude >= 0.74 ? "#ffffff" : "#172033",
    };
  }
  return {
    backgroundColor: `rgba(47, 111, 159, ${alpha})`,
    color: magnitude >= 0.74 ? "#ffffff" : "#172033",
  };
}

function confidenceIntervalLabel(pair: XyCorrelationPairResult): string {
  if (pair.confidence_interval === null) {
    return "NA";
  }
  const { lower, upper, level } = pair.confidence_interval;
  if (lower === null || upper === null) {
    return "계산 불가";
  }
  return `${formatPercent(level)} CI ${formatPairNumber(lower)} - ${formatPairNumber(upper)}`;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}

function formatPairNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "NA";
  }
  return value.toLocaleString("ko-KR", {
    maximumFractionDigits: 6,
    minimumFractionDigits: 0,
  });
}
