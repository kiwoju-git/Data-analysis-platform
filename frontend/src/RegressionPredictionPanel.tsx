import type {
  DatasetVersionCatalogItem,
  DatasetVersionResponse,
  RegressionPredictionPreflightResponse,
  RegressionPredictionResponse,
  RegressionPredictionRowsPageResponse,
} from "./api";
import {
  groupPredictionPreflightIssues,
  predictionRangeRows,
} from "./predictionPreflightPresentation";
import type { RegressionPredictionExportState } from "./useRegressionPredictionExportState";
import type { RegressionPredictionTargetState } from "./useRegressionPredictionTargetState";

export interface RegressionPredictionRowsState {
  error: string | null;
  isLoading: boolean;
  page: RegressionPredictionRowsPageResponse | null;
  onPageChange: (offset: number) => void;
}

interface RegressionPredictionPanelProps {
  allowExportWithoutModel?: boolean;
  currentVersion: DatasetVersionResponse | null;
  expectedModelId: string | null;
  isRunningPrediction: boolean;
  isRunningPreflight: boolean;
  modelAvailable: boolean;
  modelManifestAvailable: boolean;
  prediction: RegressionPredictionResponse | null;
  predictionError: string | null;
  predictionExportState: RegressionPredictionExportState;
  predictionPreflight: RegressionPredictionPreflightResponse | null;
  predictionPreflightError: string | null;
  predictionRowsState: RegressionPredictionRowsState;
  predictionTargetState: RegressionPredictionTargetState;
  preflightButtonLabel?: string;
  onRunPrediction: () => void;
  onRunPreflight: () => void;
}

export function RegressionPredictionPanel({
  allowExportWithoutModel = false,
  currentVersion,
  expectedModelId,
  isRunningPrediction,
  isRunningPreflight,
  modelAvailable,
  modelManifestAvailable,
  prediction,
  predictionError,
  predictionExportState,
  predictionPreflight,
  predictionPreflightError,
  predictionRowsState,
  predictionTargetState,
  preflightButtonLabel = "사전점검 실행",
  onRunPrediction,
  onRunPreflight,
}: RegressionPredictionPanelProps) {
  const selectedTargetVersionId = predictionTargetState.selectedTargetVersionId;
  const canRunPreflight =
    expectedModelId !== null &&
    modelManifestAvailable &&
    modelAvailable &&
    selectedTargetVersionId !== null &&
    !isRunningPreflight;
  const canRunPrediction =
    canRunPreflight &&
    predictionPreflight?.prediction_ready === true &&
    predictionPreflight.model_id === expectedModelId &&
    predictionPreflight.target_dataset_version_id === selectedTargetVersionId &&
    !isRunningPrediction;
  const errorCount =
    predictionPreflight?.issues.filter((issue) => issue.severity === "error").length ?? 0;
  const warningCount =
    predictionPreflight?.issues.filter((issue) => issue.severity === "warning").length ?? 0;
  const groupedIssues = groupPredictionPreflightIssues(predictionPreflight?.issues ?? []);
  const extrapolationChecks = predictionRangeRows(predictionPreflight?.numeric_checks ?? []);
  const activePage =
    prediction !== null && predictionRowsState.page?.prediction_id === prediction.prediction_id
      ? predictionRowsState.page
      : null;
  const previewRows = activePage?.rows ?? prediction?.rows.slice(0, 25) ?? [];

  return (
    <section className="result-section" aria-labelledby="regression-prediction-title">
      <div className="panel-heading">
        <div>
          <h4 id="regression-prediction-title">예측 사전점검</h4>
          <p>선택한 데이터셋 버전을 checksum 검증된 모델 manifest와 대조합니다.</p>
        </div>
        <div className="button-row">
          <button
            className="secondary-button"
            disabled={!canRunPreflight}
            onClick={onRunPreflight}
            type="button"
          >
            {isRunningPreflight ? "점검 중" : preflightButtonLabel}
          </button>
          <button
            className="primary-button"
            disabled={!canRunPrediction}
            onClick={onRunPrediction}
            type="button"
          >
            {isRunningPrediction ? "예측 중" : "예측 실행"}
          </button>
        </div>
      </div>
      {!modelManifestAvailable ? (
        <div className="notice-box">저장된 model manifest가 없는 결과입니다.</div>
      ) : null}
      <div className="option-grid option-grid-wide">
        <label>
          <span>예측 대상 데이터셋 버전</span>
          <select
            aria-label="예측 대상 데이터셋 버전"
            disabled={
              selectedTargetVersionId === null ||
              !modelAvailable ||
              isRunningPreflight ||
              isRunningPrediction ||
              predictionExportState.isCreating ||
              predictionExportState.isDownloading
            }
            value={selectedTargetVersionId ?? ""}
            onChange={(event) => predictionTargetState.onSelect(event.currentTarget.value)}
          >
            {currentVersion !== null ? (
              <option value={currentVersion.version_id}>
                현재 데이터셋 · v{currentVersion.version_number} ·{" "}
                {currentVersion.row_count.toLocaleString()}행 ×{" "}
                {currentVersion.column_count.toLocaleString()}열
              </option>
            ) : null}
            {predictionTargetState.selectedTarget !== null &&
            predictionTargetState.selectedTarget.version_id !== currentVersion?.version_id &&
            !predictionTargetState.catalog?.versions.some(
              (candidate) =>
                candidate.version_id === predictionTargetState.selectedTarget?.version_id,
            ) ? (
              <option value={predictionTargetState.selectedTarget.version_id}>
                {targetLabel(predictionTargetState.selectedTarget)}
              </option>
            ) : null}
            {predictionTargetState.catalog?.versions
              .filter((candidate) => candidate.version_id !== currentVersion?.version_id)
              .map((candidate) => (
                <option key={candidate.version_id} value={candidate.version_id}>
                  {targetLabel(candidate)}
                </option>
              ))}
          </select>
        </label>
      </div>
      {predictionTargetState.error !== null ? (
        <div className="error-box" role="alert">
          데이터셋 버전 목록 조회 실패: {predictionTargetState.error}
        </div>
      ) : null}
      {predictionTargetState.catalog !== null &&
      predictionTargetState.catalog.total > predictionTargetState.catalog.limit ? (
        <div className="result-pagination" aria-label="예측 대상 데이터셋 목록 페이지 이동">
          <button
            disabled={
              predictionTargetState.isLoading ||
              !predictionTargetState.catalog.has_previous
            }
            onClick={() =>
              predictionTargetState.onPageChange(
                Math.max(
                  0,
                  predictionTargetState.catalog!.offset -
                    predictionTargetState.catalog!.limit,
                ),
              )
            }
            type="button"
          >이전</button>
          <span>
            {predictionTargetState.catalog.offset + 1}-
            {predictionTargetState.catalog.offset + predictionTargetState.catalog.returned} /{" "}
            {predictionTargetState.catalog.total}
          </span>
          <button
            disabled={
              predictionTargetState.isLoading || !predictionTargetState.catalog.has_next
            }
            onClick={() =>
              predictionTargetState.onPageChange(
                predictionTargetState.catalog!.offset + predictionTargetState.catalog!.limit,
              )
            }
            type="button"
          >다음</button>
        </div>
      ) : null}
      <div className="notice-box">
        예측은 저장된 OLS 모델이 선택한 데이터셋 버전에 적용한 추정값입니다. 원인·효과나
        확정값으로 해석하지 말고 학습 범위 밖 값과 OLS 가정을 확인해야 합니다.
      </div>
      {predictionPreflightError !== null ? (
        <div className="error-box" role="alert">오류 코드: {predictionPreflightError}</div>
      ) : null}
      {predictionError !== null ? (
        <div className="error-box" role="alert">오류 코드: {predictionError}</div>
      ) : null}
      {predictionPreflight !== null ? (
        <>
          <h4>예측 사전점검 결과</h4>
          <div className="metadata-grid" aria-label="예측 사전점검 요약">
            <span>상태</span>
            <strong>{predictionPreflight.prediction_ready ? "예측 준비 가능" : "확인 필요"}</strong>
            <span>대상 행</span>
            <strong>{predictionPreflight.row_count_usable.toLocaleString()} / {predictionPreflight.row_count_total.toLocaleString()}</strong>
            <span>Schema hash</span><strong>{predictionPreflight.schema_hash_match ? "일치" : "다름"}</strong>
            <span>Source model</span>
            <strong>{predictionPreflight.source_analysis_stale === true ? "stale · 재적합 필요" : predictionPreflight.source_analysis_stale === false ? "fresh" : "검증 불가"}</strong>
            <span>Source schema</span>
            <strong>
              {predictionPreflight.source_schema_hash_current === null
                ? "검증 불가"
                : predictionPreflight.source_schema_hash_current ===
                    predictionPreflight.source_schema_hash
                  ? "적합 시점과 일치"
                  : "변경됨 · 재적합 필요"}
            </strong>
            <span>문제</span><strong>오류 {errorCount}개 · 경고 {warningCount}개</strong>
          </div>
          {predictionPreflight.prediction_ready ? (
            <div className="success-box" role="status">
              {warningCount > 0 ? "경고는 있지만 실행 가능" : "예측 실행 가능"} · usable {predictionPreflight.row_count_usable.toLocaleString()} / {predictionPreflight.row_count_total.toLocaleString()}행
            </div>
          ) : (
            <div className="error-box" role="alert">
              예측 실행 차단 · source model과 target predictor 오류를 해결한 뒤 다시 점검하세요.
            </div>
          )}
          {groupedIssues.sourceBlockers.length > 0 ? (
            <div className="error-box prediction-source-blocker" role="alert">
              <strong>Source 회귀모형 재적합 필요</strong>
              <ul>
                {groupedIssues.sourceBlockers.map((issue, index) => (
                  <li key={`${issue.code}-${index}`}>{issue.message}<span className="cell-subtle">{issue.code}</span></li>
                ))}
              </ul>
            </div>
          ) : null}
          {!predictionPreflight.schema_hash_match ? (
            <div className="notice-box prediction-target-warning">
              <strong>Target schema가 source와 다릅니다.</strong>
              <span>별도 target dataset에서는 정상일 수 있습니다. 아래 predictor mapping과 type을 확인하세요.</span>
            </div>
          ) : null}
          {groupedIssues.mappingIssues.length > 0 ? (
            <details className="notice-box prediction-mapping-summary">
              <summary>
                Predictor ID가 달라 표시명으로 안전하게 매핑한 컬럼 {groupedIssues.mappingIssues.length.toLocaleString()}개
              </summary>
              <p>표시명이 target에서 하나뿐인 경우에만 매핑합니다. 중복되거나 누락되면 실행할 수 없습니다.</p>
              <PredictionMappingTable preflight={predictionPreflight} />
            </details>
          ) : (
            <PredictionMappingTable preflight={predictionPreflight} />
          )}
          {extrapolationChecks.length > 0 ? (
            <div className="notice-box prediction-range-warning">
              <strong>학습 범위 밖 target 값</strong>
              <span>예측은 실행할 수 있지만 외삽 결과의 불확실성과 적용 가능성을 별도로 검토하세요.</span>
              <div className="table-wrap">
                <table aria-label="학습 범위 밖 대상값 요약" className="result-table">
                  <thead><tr><th>Predictor</th><th>학습 min</th><th>학습 max</th><th>범위 아래</th><th>범위 위</th><th>합계</th></tr></thead>
                  <tbody>{extrapolationChecks.map((check) => (
                    <tr key={check.source_column_id}>
                      <td>{check.display_name}</td>
                      <td>{numberOrDash(check.training_min)}</td>
                      <td>{numberOrDash(check.training_max)}</td>
                      <td>{check.n_below_training_range.toLocaleString()}</td>
                      <td>{check.n_above_training_range.toLocaleString()}</td>
                      <td>{(check.n_below_training_range + check.n_above_training_range).toLocaleString()}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </div>
          ) : null}
          {groupedIssues.otherIssues.length > 0 ? (
            <ul className="warning-list" aria-label="예측 사전점검 문제">
              {groupedIssues.otherIssues.map((issue, index) => (
                <li key={`${issue.code}-${index}`}>[{issue.severity}] {issue.message}<span className="cell-subtle">{issue.display_name ?? issue.code}{issue.count !== null ? ` · ${issue.count.toLocaleString()}건` : ""}</span></li>
              ))}
            </ul>
          ) : null}
          {predictionPreflight.numeric_checks.length > 0 ? (
            <div className="table-wrap">
              <table className="result-table">
                <thead><tr><th>숫자형 컬럼</th><th>유효</th><th>결측</th><th>비숫자</th><th>학습범위 아래</th><th>학습범위 위</th></tr></thead>
                <tbody>{predictionPreflight.numeric_checks.map((check) => (
                  <tr key={check.source_column_id}><td>{check.display_name}</td><td>{check.n_valid.toLocaleString()}</td><td>{check.n_missing.toLocaleString()}</td><td>{check.n_non_numeric.toLocaleString()}</td><td>{check.n_below_training_range.toLocaleString()}</td><td>{check.n_above_training_range.toLocaleString()}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : null}
          {predictionPreflight.categorical_checks.length > 0 ? (
            <div className="table-wrap">
              <table className="result-table">
                <thead><tr><th>범주형 컬럼</th><th>학습 level</th><th>유효</th><th>결측</th><th>새 level</th></tr></thead>
                <tbody>{predictionPreflight.categorical_checks.map((check) => (
                  <tr key={check.source_column_id}><td>{check.display_name}</td><td>{check.training_level_count.toLocaleString()}</td><td>{check.n_valid.toLocaleString()}</td><td>{check.n_missing.toLocaleString()}</td><td>{check.n_unseen_level.toLocaleString()}</td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : null}
        </>
      ) : null}
      {prediction !== null ? (
        <>
          <h4>예측 결과</h4>
          <div className="metadata-grid" aria-label="예측 결과 요약">
            <span>Prediction ID</span><strong title={prediction.prediction_id}>{shortId(prediction.prediction_id)}</strong>
            <span>예측 행</span><strong>{prediction.row_count_predicted.toLocaleString()} / {prediction.row_count_total.toLocaleString()}</strong>
            <span>제외 행</span><strong>{prediction.row_count_excluded.toLocaleString()}개</strong>
            <span>응답 생략</span><strong>{prediction.row_count_omitted.toLocaleString()}개</strong>
            <span>신뢰수준</span><strong>{(prediction.confidence_level * 100).toFixed(1)}%</strong>
          </div>
          <div className="button-row" aria-label="전체 예측 CSV export">
            <button
              className="secondary-button"
              disabled={
                (!modelAvailable && !allowExportWithoutModel) ||
                predictionExportState.isCreating ||
                predictionExportState.isDownloading
              }
              onClick={predictionExportState.onCreate}
              type="button"
            >{predictionExportState.isCreating ? "전체 예측 CSV 생성 중" : "전체 예측 CSV 생성"}</button>
            {predictionExportState.csvExport !== null ? (
              <>
                <span className="cell-subtle">{predictionExportState.csvExport.row_count.toLocaleString()}행 · sha256: {shortId(predictionExportState.csvExport.sha256)}</span>
                <button className="secondary-button" disabled={predictionExportState.isDownloading} onClick={predictionExportState.onDownload} type="button">
                  {predictionExportState.isDownloading ? "CSV 다운로드 중" : "전체 예측 CSV 다운로드"}
                </button>
              </>
            ) : null}
          </div>
          {predictionExportState.error !== null ? <div className="error-box" role="alert">예측 CSV export 실패: {predictionExportState.error}</div> : null}
          {prediction.warnings.length > 0 ? (
            <ul className="warning-list" aria-label="예측 경고">{prediction.warnings.map((warning, index) => <li key={`${warning.code}-${index}`}>[{warning.severity}] {warning.message}<span className="cell-subtle">{warning.code}</span></li>)}</ul>
          ) : null}
          <div className="result-section" aria-label="예측 구간 차트 결과">
            <div className="panel-heading"><div><h4>예측 구간 차트</h4><p>Predicted mean · mean CI · prediction interval</p></div></div>
            <div className="chart-grid chart-grid-single"><PredictionIntervalChart rows={previewRows} /></div>
          </div>
          <div className="table-wrap">
            <table className="result-table">
              <thead><tr><th>행 index</th><th>예측 평균</th><th>Mean CI</th><th>Prediction interval</th><th>경고</th></tr></thead>
              <tbody>{previewRows.map((row) => <tr key={row.row_index}><td>{row.row_index.toLocaleString()}</td><td>{number(row.predicted_mean)}</td><td>{interval(row.mean_confidence_interval)}</td><td>{interval(row.prediction_interval)}</td><td>{row.warnings.length > 0 ? row.warnings.join(", ") : "없음"}</td></tr>)}</tbody>
            </table>
          </div>
          {predictionRowsState.error !== null ? <div className="error-box" role="alert">예측 행 조회 실패: {predictionRowsState.error}</div> : null}
          {activePage !== null ? (
            <div className="result-pagination" aria-label="예측 행 페이지 이동">
              <button disabled={predictionRowsState.isLoading || !activePage.has_previous} onClick={() => predictionRowsState.onPageChange(Math.max(0, activePage.offset - activePage.limit))} type="button">이전</button>
              <span>{activePage.total === 0 ? "0 / 0" : `${activePage.offset + 1}-${activePage.offset + activePage.returned} / ${activePage.total}`}</span>
              <button disabled={predictionRowsState.isLoading || !activePage.has_next} onClick={() => predictionRowsState.onPageChange(activePage.offset + activePage.limit)} type="button">다음</button>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function PredictionMappingTable({
  preflight,
}: {
  preflight: RegressionPredictionPreflightResponse;
}) {
  return (
    <div className="table-wrap">
      <table aria-label="Predictor source target mapping" className="result-table">
        <thead><tr><th>Predictor</th><th>종류</th><th>매핑</th><th>상태</th><th>Source ID</th><th>Target ID</th></tr></thead>
        <tbody>{preflight.required_columns.map((mapping) => (
          <tr key={mapping.source_column_id}>
            <td>{mapping.display_name}</td><td>{predictorKind(mapping.predictor_kind)}</td>
            <td>{matchType(mapping.match_type)}</td><td>{mapping.status}</td>
            <td>{shortId(mapping.source_column_id)}</td>
            <td>{shortId(mapping.target_column_id ?? "missing")}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function PredictionIntervalChart({ rows }: { rows: RegressionPredictionResponse["rows"] }) {
  const usable = rows.filter((row) => row.prediction_interval !== null);
  if (usable.length === 0) return <div className="empty-state">표시할 예측 구간이 없습니다.</div>;
  const width = 440;
  const height = 250;
  const values = usable.flatMap((row) => [
    row.prediction_interval!.lower,
    row.prediction_interval!.upper,
    row.mean_confidence_interval?.lower ?? row.predicted_mean,
    row.mean_confidence_interval?.upper ?? row.predicted_mean,
  ]);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const span = maximum === minimum ? 1 : maximum - minimum;
  const y = (value: number) => 18 + ((maximum - value) / span) * 190;
  const x = (index: number) => 48 + (index / Math.max(1, usable.length - 1)) * 374;
  return (
    <svg aria-label="예측 평균과 신뢰구간 및 개별 예측구간" className="chart-svg chart-svg-wide" role="img" viewBox={`0 0 ${width} ${height}`}>
      {usable.map((row, index) => {
        const xPosition = x(index);
        return <g key={row.row_index}>
          <line className="prediction-interval-line" x1={xPosition} x2={xPosition} y1={y(row.prediction_interval!.lower)} y2={y(row.prediction_interval!.upper)} />
          {row.mean_confidence_interval !== null ? <line className="prediction-ci-line" x1={xPosition - 3} x2={xPosition - 3} y1={y(row.mean_confidence_interval.lower)} y2={y(row.mean_confidence_interval.upper)} /> : null}
          <circle className="prediction-mean-point" cx={xPosition} cy={y(row.predicted_mean)} r="3" />
        </g>;
      })}
    </svg>
  );
}

function targetLabel(target: DatasetVersionCatalogItem) {
  return `${target.original_filename} · v${target.version_number} · ${target.row_count.toLocaleString()}행 × ${target.column_count.toLocaleString()}열 · ${shortId(target.version_id)}`;
}

function predictorKind(value: string) {
  return value === "numeric" ? "숫자형" : "범주형";
}

function matchType(value: string) {
  if (value === "column_id") return "컬럼 ID";
  if (value === "display_name") return "표시명";
  if (value === "ambiguous") return "표시명 중복";
  return "없음";
}

function shortId(value: string) {
  return value.length <= 16 ? value : `${value.slice(0, 8)}…${value.slice(-6)}`;
}

function number(value: number) {
  return Number.isFinite(value) ? value.toPrecision(6) : "-";
}

function numberOrDash(value: number | null) {
  return value === null || !Number.isFinite(value) ? "-" : number(value);
}

function interval(value: { level: number; lower: number; upper: number } | null) {
  return value === null ? "-" : `${(value.level * 100).toFixed(1)}% ${number(value.lower)} - ${number(value.upper)}`;
}
