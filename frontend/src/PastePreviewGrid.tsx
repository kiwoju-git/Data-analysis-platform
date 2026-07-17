import type { KeyboardEvent } from "react";

import {
  spreadsheetColumnLabel,
  type PastedTablePreview,
} from "./pastedTablePreview";
import type { PastedCellSelection } from "./usePastedDatasetDraft";

interface PastePreviewGridProps {
  hasHeaderPreview: boolean;
  preview: PastedTablePreview;
  selection: PastedCellSelection | null;
  onCellSelect: (rowIndex: number, columnIndex: number) => void;
}

export function PastePreviewGrid({
  hasHeaderPreview,
  preview,
  selection,
  onCellSelect,
}: PastePreviewGridProps) {
  const raggedRows = new Set(preview.raggedRowIndices);

  return (
    <div className="paste-grid-layout">
      <div className="paste-grid-scroll" aria-label="붙여넣기 표 미리보기">
        <table className="paste-preview-grid" role="grid">
          <thead>
            <tr>
              <th className="paste-grid-corner" scope="col" aria-label="행 번호" />
              {Array.from({ length: preview.previewColumnCount }, (_, columnIndex) => (
                <th key={columnIndex} scope="col">
                  {spreadsheetColumnLabel(columnIndex)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row, rowIndex) => (
              <tr className={hasHeaderPreview && rowIndex === 0 ? "is-header-preview" : undefined} key={rowIndex}>
                <th className="paste-grid-row-header" scope="row">
                  <span>{rowIndex + 1}</span>
                  {raggedRows.has(rowIndex + 1) ? (
                    <span className="ragged-row-marker" title="행마다 열 수가 다름">
                      <span aria-hidden="true">!</span>
                      <span className="sr-only">열 수 다름</span>
                    </span>
                  ) : null}
                </th>
                {Array.from({ length: preview.previewColumnCount }, (_, columnIndex) => {
                  const value = row[columnIndex];
                  const structuralGap = value === undefined;
                  const selected =
                    selection?.rowIndex === rowIndex &&
                    selection.columnIndex === columnIndex;
                  return (
                    <td
                      aria-colindex={columnIndex + 2}
                      aria-rowindex={rowIndex + 2}
                      aria-selected={selected}
                      className={selected ? "is-selected" : undefined}
                      data-paste-cell={`${rowIndex}-${columnIndex}`}
                      key={`${rowIndex}-${columnIndex}`}
                      tabIndex={selected || (selection === null && rowIndex === 0 && columnIndex === 0) ? 0 : -1}
                      title={structuralGap ? "행에 해당 열이 없음" : value}
                      onClick={() => {
                        if (!structuralGap) onCellSelect(rowIndex, columnIndex);
                      }}
                      onFocus={() => {
                        if (!structuralGap) onCellSelect(rowIndex, columnIndex);
                      }}
                      onKeyDown={(event) => {
                        handleGridKeyDown(
                          event,
                          rowIndex,
                          columnIndex,
                          preview,
                          onCellSelect,
                        );
                      }}
                    >
                      {structuralGap ? (
                        <span className="structural-empty-cell">구조상 없음</span>
                      ) : value === "" ? (
                        <span className="empty-cell">빈 셀</span>
                      ) : (
                        <span className="paste-cell-text">{value}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <CellInspector selection={selection} />
    </div>
  );
}

function CellInspector({ selection }: { selection: PastedCellSelection | null }) {
  return (
    <section className="cell-inspector" aria-labelledby="paste-cell-inspector-title">
      <div className="panel-heading compact-heading">
        <div>
          <h4 id="paste-cell-inspector-title">선택 셀</h4>
          <p>{selection === null ? "셀을 선택하면 전체 값을 확인합니다." : selection.address}</p>
        </div>
        {selection !== null ? (
          <span className="status-pill">행 {selection.rowIndex + 1} / 열 {selection.columnIndex + 1}</span>
        ) : null}
      </div>
      <output className="cell-inspector-value">
        {selection === null ? "선택된 셀 없음" : selection.value === "" ? "(빈 셀)" : selection.value}
      </output>
    </section>
  );
}

function handleGridKeyDown(
  event: KeyboardEvent<HTMLTableCellElement>,
  rowIndex: number,
  columnIndex: number,
  preview: PastedTablePreview,
  onCellSelect: (rowIndex: number, columnIndex: number) => void,
) {
  const keyOffsets: Record<string, [number, number]> = {
    ArrowDown: [1, 0],
    ArrowLeft: [0, -1],
    ArrowRight: [0, 1],
    ArrowUp: [-1, 0],
  };
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onCellSelect(rowIndex, columnIndex);
    return;
  }
  const offset = keyOffsets[event.key];
  if (offset === undefined) return;
  event.preventDefault();
  const nextRow = Math.max(0, Math.min(preview.previewRowCount - 1, rowIndex + offset[0]));
  const nextColumn = Math.max(
    0,
    Math.min(preview.previewColumnCount - 1, columnIndex + offset[1]),
  );
  const nextValue = preview.rows[nextRow]?.[nextColumn];
  if (nextValue === undefined) return;
  onCellSelect(nextRow, nextColumn);
  const table = event.currentTarget.closest("table");
  const nextCell = table?.querySelector<HTMLElement>(
    `[data-paste-cell="${nextRow}-${nextColumn}"]`,
  );
  nextCell?.focus();
}
