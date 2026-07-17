import type { ConfirmedParsingOptions, DatasetUploadResponse } from "./api";
import { delimiterLabel } from "./datasetDisplay";

interface ParsingConfirmationPanelProps {
  canConfirm: boolean;
  delimiterOptions: string[];
  isConfirming: boolean;
  parsingOptions: ConfirmedParsingOptions;
  pastedHeaderPreference: boolean | null;
  upload: DatasetUploadResponse;
  onConfirmParsing: () => void;
  onParsingOptionsChange: (options: ConfirmedParsingOptions) => void;
}

export function ParsingConfirmationPanel({
  canConfirm,
  delimiterOptions,
  isConfirming,
  parsingOptions,
  pastedHeaderPreference,
  upload,
  onConfirmParsing,
  onParsingOptionsChange,
}: ParsingConfirmationPanelProps) {
  return (
    <section className="confirmation-panel" aria-labelledby="confirmation-title">
      <div className="panel-heading">
        <div>
          <h3 id="confirmation-title">파싱 옵션</h3>
          <p>{upload.original_filename}</p>
        </div>
        <span className="status-pill">SHA-256 기록됨</span>
      </div>
      <div className="metadata-grid">
        <span>형식</span>
        <strong>{upload.detected_format}</strong>
        <span>크기</span>
        <strong>{upload.size_bytes.toLocaleString()} bytes</strong>
        <span>다음 단계</span>
        <strong>{upload.next_step}</strong>
      </div>
      {upload.warnings.length > 0 ? (
        <ul className="warning-list" aria-label="업로드 경고">
          {upload.warnings.map((warning) => (
            <li key={warning.code}>{warning.message}</li>
          ))}
        </ul>
      ) : null}
      {pastedHeaderPreference !== null ? (
        <div
          className={
            pastedHeaderPreference === upload.parsing.has_header
              ? "notice-box"
              : "warning-box"
          }
          role="status"
        >
          붙여넣기 표시는 첫 행을 {pastedHeaderPreference ? "헤더처럼" : "데이터처럼"}
          보았습니다. 서버 제안은 {upload.parsing.has_header ? "헤더 있음" : "헤더 없음"}
          입니다. 아래 파싱 옵션이 최종 기준이며 자동 확정되지 않습니다.
        </div>
      ) : null}
      {parsingOptions.kind === "delimited_text" ? (
        <DelimitedParsingOptions
          delimiterOptions={delimiterOptions}
          parsingOptions={parsingOptions}
          upload={upload}
          onParsingOptionsChange={onParsingOptionsChange}
        />
      ) : (
        <XlsxParsingOptions
          parsingOptions={parsingOptions}
          onParsingOptionsChange={onParsingOptionsChange}
        />
      )}
      <button
        className="primary-button"
        disabled={!canConfirm}
        onClick={onConfirmParsing}
        type="button"
      >
        {isConfirming ? "확정 중" : "파싱 확정 및 버전 생성"}
      </button>
    </section>
  );
}

interface DelimitedParsingOptionsProps {
  delimiterOptions: string[];
  parsingOptions: ConfirmedParsingOptions;
  upload: DatasetUploadResponse;
  onParsingOptionsChange: (options: ConfirmedParsingOptions) => void;
}

function DelimitedParsingOptions({
  delimiterOptions,
  parsingOptions,
  upload,
  onParsingOptionsChange,
}: DelimitedParsingOptionsProps) {
  return (
    <div className="option-grid">
      <label>
        <span>인코딩</span>
        <select
          value={parsingOptions.encoding ?? ""}
          onChange={(event) => {
            onParsingOptionsChange({
              ...parsingOptions,
              encoding: event.currentTarget.value,
            });
          }}
        >
          {upload.parsing.encoding_candidates.map((encoding) => (
            <option key={encoding} value={encoding}>
              {encoding}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>구분자</span>
        <select
          value={parsingOptions.delimiter ?? ""}
          onChange={(event) => {
            onParsingOptionsChange({
              ...parsingOptions,
              delimiter: event.currentTarget.value,
            });
          }}
        >
          {delimiterOptions.map((delimiter) => (
            <option key={delimiter} value={delimiter}>
              {delimiterLabel(delimiter)}
            </option>
          ))}
        </select>
      </label>
      <HeaderAndMissingOptions
        parsingOptions={parsingOptions}
        onParsingOptionsChange={onParsingOptionsChange}
      />
    </div>
  );
}

interface XlsxParsingOptionsProps {
  parsingOptions: ConfirmedParsingOptions;
  onParsingOptionsChange: (options: ConfirmedParsingOptions) => void;
}

function XlsxParsingOptions({
  parsingOptions,
  onParsingOptionsChange,
}: XlsxParsingOptionsProps) {
  return (
    <div className="option-grid">
      <label>
        <span>시트명</span>
        <input
          placeholder="비우면 첫 시트"
          value={parsingOptions.xlsx_sheet_name ?? ""}
          onChange={(event) => {
            const value = event.currentTarget.value.trim();
            onParsingOptionsChange({
              ...parsingOptions,
              xlsx_sheet_name: value === "" ? null : value,
            });
          }}
        />
      </label>
      <HeaderAndMissingOptions
        parsingOptions={parsingOptions}
        onParsingOptionsChange={onParsingOptionsChange}
      />
    </div>
  );
}

interface HeaderAndMissingOptionsProps {
  parsingOptions: ConfirmedParsingOptions;
  onParsingOptionsChange: (options: ConfirmedParsingOptions) => void;
}

function HeaderAndMissingOptions({
  parsingOptions,
  onParsingOptionsChange,
}: HeaderAndMissingOptionsProps) {
  return (
    <>
      <label>
        <span>첫 데이터 행을 헤더로 사용</span>
        <input
          checked={parsingOptions.has_header}
          type="checkbox"
          onChange={(event) => {
            const hasHeader = event.currentTarget.checked;
            onParsingOptionsChange({
              ...parsingOptions,
              has_header: hasHeader,
              data_start_row: hasHeader
                ? parsingOptions.header_row + 1
                : (parsingOptions.data_start_row ?? parsingOptions.header_row),
            });
          }}
        />
      </label>
      <label>
        <span>{parsingOptions.has_header ? "헤더 행" : "데이터 시작 행"}</span>
        <input
          min={1}
          type="number"
          value={
            parsingOptions.has_header
              ? parsingOptions.header_row
              : (parsingOptions.data_start_row ?? parsingOptions.header_row)
          }
          onChange={(event) => {
            const rowNumber = Number(event.currentTarget.value);
            onParsingOptionsChange({
              ...parsingOptions,
              header_row: parsingOptions.has_header ? rowNumber : parsingOptions.header_row,
              data_start_row: parsingOptions.has_header ? rowNumber + 1 : rowNumber,
            });
          }}
        />
      </label>
      <label>
        <span>결측 토큰</span>
        <input
          value={parsingOptions.missing_tokens.join(",")}
          onChange={(event) => {
            onParsingOptionsChange({
              ...parsingOptions,
              missing_tokens: event.currentTarget.value.split(","),
            });
          }}
        />
      </label>
    </>
  );
}
