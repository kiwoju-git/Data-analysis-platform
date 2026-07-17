import { useState, type FormEvent } from "react";

import { PastePreviewGrid } from "./PastePreviewGrid";
import {
  pastedDelimiterLabel,
  type PastedTablePreview,
} from "./pastedTablePreview";
import { usePastedDatasetDraft } from "./usePastedDatasetDraft";

interface PasteDatasetPanelProps {
  isSubmitting: boolean;
  onRegister: (content: string, previewHasHeader: boolean) => Promise<boolean>;
}

export function PasteDatasetPanel({ isSubmitting, onRegister }: PasteDatasetPanelProps) {
  const draft = usePastedDatasetDraft();
  const [isAwaitingSubmit, setIsAwaitingSubmit] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft.canSubmit || isSubmitting || isAwaitingSubmit) return;
    setIsAwaitingSubmit(true);
    try {
      const succeeded = await onRegister(draft.getRawText(), draft.hasHeaderPreview);
      if (succeeded) draft.clear();
    } finally {
      setIsAwaitingSubmit(false);
    }
  };

  return (
    <form className="paste-panel paste-staging-panel" onSubmit={(event) => void submit(event)}>
      <div className="paste-panel-heading">
        <div>
          <h3>복사한 표 붙여넣기</h3>
          <p>원문은 파싱 미리보기와 별도로 보존되며 등록할 때 변경 없이 전송됩니다.</p>
        </div>
        <div className="view-mode-control" aria-label="붙여넣기 보기 방식">
          <button
            aria-pressed={draft.mode === "grid"}
            className={draft.mode === "grid" ? "is-active" : undefined}
            disabled={draft.preview?.rawModeOnly === true}
            onClick={() => draft.setMode("grid")}
            type="button"
          >
            표 보기
          </button>
          <button
            aria-pressed={draft.mode === "raw"}
            className={draft.mode === "raw" ? "is-active" : undefined}
            onClick={() => draft.setMode("raw")}
            type="button"
          >
            원문 보기
          </button>
        </div>
      </div>

      <div
        aria-label="복사한 표 붙여넣기"
        aria-multiline="true"
        className={`paste-drop-surface${draft.characterCount > 0 ? " has-draft" : ""}`}
        ref={draft.pasteSurfaceRef}
        role="textbox"
        tabIndex={0}
        onPaste={draft.onDirectPaste}
      >
        <strong>Excel 또는 스프레드시트에서 셀 범위를 복사한 뒤 여기를 클릭하고 Ctrl+V 하세요.</strong>
        <span>클립보드의 text/plain만 읽으며 표는 항상 A1부터 미리 봅니다.</span>
      </div>

      <label className={`paste-control raw-paste-control${draft.mode === "raw" ? "" : " is-hidden"}`}>
        <span>원문 입력</span>
        <textarea
          aria-label="붙여넣기 원문"
          ref={draft.rawTextAreaRef}
          placeholder="모바일 또는 키보드 대체 입력이 필요하면 여기에 원문을 입력하세요."
          rows={8}
          onChange={draft.onRawTextChange}
        />
      </label>

      {draft.mode === "grid" && draft.preview !== null && !draft.preview.rawModeOnly ? (
        <>
          <PasteSummary
            byteCount={draft.byteCount}
            characterCount={draft.characterCount}
            preview={draft.preview}
          />
          <label className="inline-check-control">
            <input
              checked={draft.hasHeaderPreview}
              type="checkbox"
              onChange={(event) => draft.setHasHeaderPreview(event.currentTarget.checked)}
            />
            <span>첫 행을 헤더처럼 보기 (표시만 변경)</span>
          </label>
          <PastePreviewGrid
            hasHeaderPreview={draft.hasHeaderPreview}
            preview={draft.preview}
            selection={draft.selection}
            onCellSelect={draft.onCellSelect}
          />
        </>
      ) : null}

      {draft.preview !== null && draft.preview.warnings.length > 0 ? (
        <ul className="warning-list" aria-label="붙여넣기 미리보기 경고">
          {draft.preview.warnings.map((warning) => (
            <li key={warning.code}>{warning.message}</li>
          ))}
        </ul>
      ) : null}

      <div className="paste-actions">
        <span>
          {draft.characterCount.toLocaleString()}자 / {draft.byteCount.toLocaleString()} UTF-8 bytes
        </span>
        <div className="button-row">
          <button
            className="secondary-button"
            disabled={draft.characterCount === 0 || isSubmitting || isAwaitingSubmit}
            onClick={draft.replace}
            type="button"
          >
            다시 붙여넣기
          </button>
          <button
            className="secondary-button"
            disabled={draft.characterCount === 0 || isSubmitting || isAwaitingSubmit}
            onClick={draft.clear}
            type="button"
          >
            모두 지우기
          </button>
          <button
            className="primary-button"
            disabled={!draft.canSubmit || isSubmitting || isAwaitingSubmit}
            type="submit"
          >
            {isSubmitting || isAwaitingSubmit ? "등록 중" : "붙여넣기 데이터 등록"}
          </button>
        </div>
      </div>
    </form>
  );
}

function PasteSummary({
  byteCount,
  characterCount,
  preview,
}: {
  byteCount: number;
  characterCount: number;
  preview: PastedTablePreview;
}) {
  const countSuffix = preview.countsAreLowerBounds ? "+" : "";
  return (
    <dl className="paste-summary" aria-label="붙여넣기 표 요약">
      <div>
        <dt>미리보기</dt>
        <dd>{preview.previewRowCount}행 x {preview.previewColumnCount}열</dd>
      </div>
      <div>
        <dt>감지 범위</dt>
        <dd>{preview.detectedRowCount.toLocaleString()}{countSuffix}행 x {preview.detectedColumnCount.toLocaleString()}{countSuffix}열</dd>
      </div>
      <div>
        <dt>구분자</dt>
        <dd>{pastedDelimiterLabel(preview.delimiter)}</dd>
      </div>
      <div>
        <dt>줄바꿈</dt>
        <dd>{preview.lineEnding}</dd>
      </div>
      <div>
        <dt>빈 셀</dt>
        <dd>{preview.emptyCellCount.toLocaleString()}{countSuffix}</dd>
      </div>
      <div>
        <dt>열 수가 다른 행</dt>
        <dd>{preview.raggedRowCount.toLocaleString()}{countSuffix}</dd>
      </div>
      <div>
        <dt>원문</dt>
        <dd>{characterCount.toLocaleString()}자 / {byteCount.toLocaleString()} bytes</dd>
      </div>
      <div>
        <dt>표시 범위</dt>
        <dd>{preview.truncatedRows || preview.truncatedColumns ? "일부만 표시" : "전체 표시"}</dd>
      </div>
    </dl>
  );
}
