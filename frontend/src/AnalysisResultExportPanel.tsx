import type {
  AnalysisResultCsvExportResponse,
  AnalysisResultEnvelope,
  AnalysisResultExportListResponse,
  AnalysisResultHtmlReportResponse,
  AnalysisResultJsonExportResponse,
} from "./api";
import {
  exportKindLabel,
  formatBytes,
  formatDateTime,
  shortHash,
} from "./analysisWorkbenchUtils";

export function AnalysisResultExportPanel({
  analysisResult,
  csvExportError,
  csvExportResult,
  downloadError,
  exportError,
  exportList,
  exportListError,
  exportResult,
  htmlReportError,
  htmlReportResult,
  isExportingCsv,
  isExportingHtml,
  isExportingJson,
  isDownloadingExport,
  isLoadingExportList,
  onCreateCsvExport,
  onCreateExport,
  onCreateHtmlReport,
  onDownloadExport,
}: {
  analysisResult: AnalysisResultEnvelope | null;
  csvExportError: string | null;
  csvExportResult: AnalysisResultCsvExportResponse | null;
  downloadError: string | null;
  exportError: string | null;
  exportList: AnalysisResultExportListResponse | null;
  exportListError: string | null;
  exportResult: AnalysisResultJsonExportResponse | null;
  htmlReportError: string | null;
  htmlReportResult: AnalysisResultHtmlReportResponse | null;
  isExportingCsv: boolean;
  isExportingHtml: boolean;
  isExportingJson: boolean;
  isDownloadingExport: boolean;
  isLoadingExportList: boolean;
  onCreateCsvExport: (analysisId: string) => void;
  onCreateExport: (analysisId: string) => void;
  onCreateHtmlReport: (analysisId: string) => void;
  onDownloadExport: (analysisId: string, exportId: string) => void;
}) {
  if (analysisResult === null || analysisResult.status !== "succeeded") {
    return null;
  }

  const matchingExport =
    exportResult !== null && exportResult.analysis_id === analysisResult.analysis_id
      ? exportResult
      : null;
  const matchingCsvExport =
    csvExportResult !== null && csvExportResult.analysis_id === analysisResult.analysis_id
      ? csvExportResult
      : null;
  const matchingHtmlReport =
    htmlReportResult !== null && htmlReportResult.analysis_id === analysisResult.analysis_id
      ? htmlReportResult
      : null;
  const hasStaleExport =
    matchingExport?.stale === true ||
    matchingCsvExport?.stale === true ||
    matchingHtmlReport?.stale === true;

  return (
    <section className="analysis-export-panel" aria-labelledby="analysis-export-title">
      <div className="panel-heading">
        <div>
          <h4 id="analysis-export-title">결과 내보내기</h4>
          <p>{analysisResult.method_id}</p>
        </div>
      </div>
      <div className="export-format-grid" aria-label="export 형식 설명">
        <ExportFormatAction
          description="재현과 기계처리에 적합한 전체 result envelope입니다."
          disabled={isExportingJson}
          format="JSON"
          isBusy={isExportingJson}
          onCreate={() => {
            onCreateExport(analysisResult.analysis_id);
          }}
        />
        <ExportFormatAction
          description="표 형태로 검토하기 쉬운 long-form CSV입니다."
          disabled={isExportingCsv}
          format="CSV"
          isBusy={isExportingCsv}
          onCreate={() => {
            onCreateCsvExport(analysisResult.analysis_id);
          }}
        />
        <ExportFormatAction
          description="사람에게 공유하기 좋은 self-contained 정적 보고서입니다."
          disabled={isExportingHtml}
          format="HTML"
          isBusy={isExportingHtml}
          onCreate={() => {
            onCreateHtmlReport(analysisResult.analysis_id);
          }}
        />
      </div>
      {hasStaleExport ? (
        <div className="notice-box">
          stale result export입니다. 데이터셋 schema 또는 source가 바뀐 뒤 생성된 결과일 수 있으니
          공유 전 재실행 여부를 확인하세요.
        </div>
      ) : null}
      {matchingExport !== null ? (
        <ExportStatus
          exportId={matchingExport.export_id}
          format="JSON"
          isDownloading={isDownloadingExport}
          onDownload={(exportId) => {
            onDownloadExport(analysisResult.analysis_id, exportId);
          }}
          sha256={matchingExport.sha256}
          sizeText={formatBytes(matchingExport.size_bytes)}
          stale={matchingExport.stale}
        />
      ) : null}
      {matchingCsvExport !== null ? (
        <ExportStatus
          exportId={matchingCsvExport.export_id}
          format="CSV"
          isDownloading={isDownloadingExport}
          onDownload={(exportId) => {
            onDownloadExport(analysisResult.analysis_id, exportId);
          }}
          sha256={matchingCsvExport.sha256}
          sizeText={`${matchingCsvExport.row_count.toLocaleString()}행 · ${formatBytes(
            matchingCsvExport.size_bytes,
          )}`}
          stale={matchingCsvExport.stale}
        />
      ) : null}
      {matchingHtmlReport !== null ? (
        <ExportStatus
          exportId={matchingHtmlReport.export_id}
          format="HTML"
          isDownloading={isDownloadingExport}
          onDownload={(exportId) => {
            onDownloadExport(analysisResult.analysis_id, exportId);
          }}
          sha256={matchingHtmlReport.sha256}
          sizeText={`${matchingHtmlReport.section_count.toLocaleString()}개 항목 · ${formatBytes(
            matchingHtmlReport.size_bytes,
          )}`}
          stale={matchingHtmlReport.stale}
        />
      ) : null}
      {isLoadingExportList ? <div className="notice-box">export 목록 조회 중</div> : null}
      {exportListError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>export 목록 조회 실패</h4>
          <code>오류 코드: {exportListError}</code>
        </div>
      ) : null}
      {exportList !== null && exportList.analysis_id === analysisResult.analysis_id ? (
        <div className="export-list-box" aria-label="최근 export 목록">
          <strong>최근 export</strong>
          {exportList.exports.length === 0 ? (
            <span>생성된 export 없음</span>
          ) : (
            exportList.exports.map((item) => (
              <div className="export-list-item" key={item.export_id}>
                <span>{exportKindLabel(item.artifact_kind)}</span>
                <code>sha256:{shortHash(item.sha256)}</code>
                <span>{formatDateTime(item.created_at)}</span>
                <button
                  className="secondary-button compact-button"
                  disabled={isDownloadingExport}
                  onClick={() => {
                    onDownloadExport(analysisResult.analysis_id, item.export_id);
                  }}
                  type="button"
                >
                  다운로드
                </button>
              </div>
            ))
          )}
        </div>
      ) : null}
      {exportError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>JSON export 실패</h4>
          <code>오류 코드: {exportError}</code>
        </div>
      ) : null}
      {csvExportError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>CSV export 실패</h4>
          <code>오류 코드: {csvExportError}</code>
        </div>
      ) : null}
      {htmlReportError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>HTML report 실패</h4>
          <code>오류 코드: {htmlReportError}</code>
        </div>
      ) : null}
      {downloadError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>export 다운로드 실패</h4>
          <p>저장된 export 파일 또는 checksum이 맞지 않습니다. 목록을 새로고침하거나 export를 다시 생성하세요.</p>
          <code>오류 코드: {downloadError}</code>
        </div>
      ) : null}
    </section>
  );
}

function ExportFormatAction({
  description,
  disabled,
  format,
  isBusy,
  onCreate,
}: {
  description: string;
  disabled: boolean;
  format: "JSON" | "CSV" | "HTML";
  isBusy: boolean;
  onCreate: () => void;
}) {
  return (
    <div className="export-format-card">
      <strong>{format}</strong>
      <p>{description}</p>
      <button className="secondary-button compact-button" disabled={disabled} onClick={onCreate} type="button">
        {isBusy ? `${format} 생성 중` : `${format} 생성`}
      </button>
    </div>
  );
}

function ExportStatus({
  exportId,
  format,
  isDownloading,
  onDownload,
  sha256,
  sizeText,
  stale,
}: {
  exportId: string;
  format: "JSON" | "CSV" | "HTML";
  isDownloading: boolean;
  onDownload: (exportId: string) => void;
  sha256: string;
  sizeText: string;
  stale: boolean;
}) {
  return (
    <div className="export-status-box" role="status">
      <strong>생성됨</strong>
      <span>{format}</span>
      <span>{sizeText}</span>
      <code title={sha256}>sha256:{shortHash(sha256)}</code>
      {stale ? <span className="stale-badge">stale · 재검토 필요</span> : null}
      <button
        className="secondary-button compact-button"
        disabled={isDownloading}
        onClick={() => {
          onDownload(exportId);
        }}
        type="button"
      >
        {isDownloading ? "다운로드 중" : `${format} 다운로드`}
      </button>
    </div>
  );
}
