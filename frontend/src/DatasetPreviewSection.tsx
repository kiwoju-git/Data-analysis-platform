import type { DatasetRowsPreviewResponse, DatasetVersionResponse } from "./api";

interface DatasetPreviewSectionProps {
  isLoadingPreview: boolean;
  preview: DatasetRowsPreviewResponse | null;
  previewLimit: number;
  previewOffset: number;
  version: DatasetVersionResponse;
  onLoadRowsPreview: (versionId: string, offset: number) => void;
}

export function DatasetPreviewSection({
  isLoadingPreview,
  preview,
  previewLimit,
  previewOffset,
  version,
  onLoadRowsPreview,
}: DatasetPreviewSectionProps) {
  return (
    <>
      <div className="schema-actions">
        <span>
          행 미리보기 {previewOffset + 1}-
          {Math.min(previewOffset + previewLimit, version.row_count).toLocaleString()}
        </span>
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
      {preview !== null ? (
        <div className="table-wrap">
          <table className="preview-table">
            <thead>
              <tr>
                <th>행</th>
                {preview.columns.map((column) => (
                  <th key={column.column_id}>{column.display_name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row) => (
                <tr key={row.row_index}>
                  <td>{row.row_index + 1}</td>
                  {row.values.map((value, index) => (
                    <td key={`${row.row_index}-${index}`}>{value ?? "(missing)"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="notice-box">버전 생성 후 행 미리보기를 불러옵니다.</div>
      )}
    </>
  );
}
