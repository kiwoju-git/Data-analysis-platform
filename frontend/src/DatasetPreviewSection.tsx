import { useEffect, useState, type FormEvent, type KeyboardEvent } from "react";

import type { DatasetRowsPreviewResponse, DatasetVersionResponse } from "./api";
import { spreadsheetColumnLabel } from "./pastedTablePreview";

interface DatasetPreviewSectionProps {
  isLoadingPreview: boolean;
  preview: DatasetRowsPreviewResponse | null;
  previewLimit: number;
  previewOffset: number;
  version: DatasetVersionResponse;
  onLoadRowsPreview: (versionId: string, offset: number) => void;
  onPreviewLimitChange: (limit: number) => void;
}

interface CanonicalCellSelection {
  address: string;
  columnName: string;
  rowNumber: number;
  value: string | null;
}

const previewPageSizes = [10, 25, 50, 100] as const;

export function DatasetPreviewSection({
  isLoadingPreview,
  preview,
  previewLimit,
  previewOffset,
  version,
  onLoadRowsPreview,
  onPreviewLimitChange,
}: DatasetPreviewSectionProps) {
  const [jumpRow, setJumpRow] = useState("1");
  const [selection, setSelection] = useState<CanonicalCellSelection | null>(null);

  useEffect(() => {
    setSelection(null);
  }, [preview?.offset, preview?.limit, version.version_id]);

  const submitJump = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const requested = Number(jumpRow);
    if (!Number.isInteger(requested) || requested < 1 || requested > version.row_count) return;
    const maximumOffset = Math.max(0, version.row_count - previewLimit);
    onLoadRowsPreview(version.version_id, Math.min(requested - 1, maximumOffset));
  };

  const visibleStart = version.row_count === 0 ? 0 : previewOffset + 1;
  const visibleEnd = Math.min(previewOffset + previewLimit, version.row_count);

  return (
    <section className="canonical-preview-section" aria-labelledby="canonical-preview-title">
      <div className="panel-heading">
        <div>
          <h4 id="canonical-preview-title">Canonical 행 미리보기</h4>
          <p>
            {visibleStart.toLocaleString()}-{visibleEnd.toLocaleString()} / 전체 {version.row_count.toLocaleString()}행
          </p>
        </div>
        <div className="canonical-preview-controls">
          <label>
            <span>페이지 크기</span>
            <select
              aria-label="미리보기 페이지 크기"
              disabled={isLoadingPreview}
              value={previewLimit}
              onChange={(event) => onPreviewLimitChange(Number(event.currentTarget.value))}
            >
              {previewPageSizes.map((size) => (
                <option key={size} value={size}>{size}</option>
              ))}
            </select>
          </label>
          <form className="row-jump-control" onSubmit={submitJump}>
            <label>
              <span>행으로 이동</span>
              <input
                aria-label="이동할 행 번호"
                max={version.row_count}
                min={1}
                type="number"
                value={jumpRow}
                onChange={(event) => setJumpRow(event.currentTarget.value)}
              />
            </label>
            <button
              className="secondary-button"
              disabled={isLoadingPreview || version.row_count === 0}
              type="submit"
            >
              이동
            </button>
          </form>
          <div className="button-row">
            <button
              className="secondary-button"
              disabled={isLoadingPreview || previewOffset === 0}
              onClick={() => {
                onLoadRowsPreview(version.version_id, Math.max(0, previewOffset - previewLimit));
              }}
              type="button"
            >
              이전
            </button>
            <button
              className="secondary-button"
              disabled={isLoadingPreview || previewOffset + previewLimit >= version.row_count}
              onClick={() => {
                onLoadRowsPreview(version.version_id, previewOffset + previewLimit);
              }}
              type="button"
            >
              다음
            </button>
          </div>
        </div>
      </div>
      {preview !== null ? (
        <>
          <div className="table-wrap canonical-preview-scroll">
            <table className="preview-table canonical-preview-grid" role="grid">
              <thead>
                <tr>
                  <th className="canonical-row-header" scope="col">행</th>
                  {preview.columns.map((column) => (
                    <th key={column.column_id} scope="col">{column.display_name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, rowIndex) => (
                  <tr key={row.row_index}>
                    <th className="canonical-row-header" scope="row">{row.row_index + 1}</th>
                    {row.values.map((value, columnIndex) => {
                      const address = `${spreadsheetColumnLabel(columnIndex)}${row.row_index + 1}`;
                      const selected = selection?.address === address;
                      return (
                        <td
                          aria-selected={selected}
                          className={selected ? "is-selected" : undefined}
                          data-canonical-cell={`${rowIndex}-${columnIndex}`}
                          key={`${row.row_index}-${columnIndex}`}
                          tabIndex={selected || (selection === null && rowIndex === 0 && columnIndex === 0) ? 0 : -1}
                          title={value ?? "결측"}
                          onClick={() => setSelection({
                            address,
                            columnName: preview.columns[columnIndex]?.display_name ?? address,
                            rowNumber: row.row_index + 1,
                            value,
                          })}
                          onFocus={() => setSelection({
                            address,
                            columnName: preview.columns[columnIndex]?.display_name ?? address,
                            rowNumber: row.row_index + 1,
                            value,
                          })}
                          onKeyDown={(event) => handleCanonicalGridKeyDown(
                            event,
                            rowIndex,
                            columnIndex,
                            preview,
                          )}
                        >
                          {value === null ? (
                            <span className="missing-cell">결측</span>
                          ) : value === "" ? (
                            <span className="empty-cell">빈 문자열</span>
                          ) : (
                            <span className="canonical-cell-text">{value}</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <section className="cell-inspector" aria-labelledby="canonical-cell-inspector-title">
            <div className="panel-heading compact-heading">
              <div>
                <h4 id="canonical-cell-inspector-title">선택 셀</h4>
                <p>{selection === null ? "셀을 선택하면 전체 값을 확인합니다." : `${selection.address} · ${selection.columnName}`}</p>
              </div>
              {selection !== null ? <span className="status-pill">행 {selection.rowNumber}</span> : null}
            </div>
            <output className="cell-inspector-value">
              {selection === null ? "선택된 셀 없음" : selection.value === null ? "(결측)" : selection.value === "" ? "(빈 문자열)" : selection.value}
            </output>
          </section>
        </>
      ) : (
        <div className="notice-box">버전 생성 후 행 미리보기를 불러옵니다.</div>
      )}
    </section>
  );
}

function handleCanonicalGridKeyDown(
  event: KeyboardEvent<HTMLTableCellElement>,
  rowIndex: number,
  columnIndex: number,
  preview: DatasetRowsPreviewResponse,
) {
  const offsets: Record<string, [number, number]> = {
    ArrowDown: [1, 0],
    ArrowLeft: [0, -1],
    ArrowRight: [0, 1],
    ArrowUp: [-1, 0],
  };
  const offset = offsets[event.key];
  if (offset === undefined) return;
  event.preventDefault();
  const nextRow = Math.max(0, Math.min(preview.rows.length - 1, rowIndex + offset[0]));
  const nextColumn = Math.max(0, Math.min(preview.columns.length - 1, columnIndex + offset[1]));
  const table = event.currentTarget.closest("table");
  table?.querySelector<HTMLElement>(
    `[data-canonical-cell="${nextRow}-${nextColumn}"]`,
  )?.focus();
}
