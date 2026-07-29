import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import type {
  DatasetCellCorrectionRequest,
  DatasetCellCorrectionResponse,
  DatasetColumnResponse,
  DatasetRowsPreviewResponse,
  DatasetVersionResponse,
} from "./api";
import { spreadsheetColumnLabel } from "./pastedTablePreview";

interface DatasetPreviewSectionProps {
  isLoadingPreview: boolean;
  preview: DatasetRowsPreviewResponse | null;
  previewLimit: number;
  previewOffset: number;
  version: DatasetVersionResponse;
  onLoadRowsPreview: (versionId: string, offset: number) => void;
  onPreviewLimitChange: (limit: number) => void;
  onCreateCellCorrection: (
    request: DatasetCellCorrectionRequest,
  ) => Promise<DatasetCellCorrectionResponse>;
  onDirtyChange: (dirty: boolean) => void;
}

interface CanonicalCellSelection {
  address: string;
  columnName: string;
  columnId: string;
  dataType: DatasetColumnResponse["data_type"];
  role: DatasetColumnResponse["role"];
  rowIndex: number;
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
  onCreateCellCorrection,
  onDirtyChange,
}: DatasetPreviewSectionProps) {
  const [jumpRow, setJumpRow] = useState("1");
  const [selection, setSelection] = useState<CanonicalCellSelection | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [draftValue, setDraftValue] = useState("");
  const [draftMissing, setDraftMissing] = useState(false);
  const [isConfirmingSave, setIsConfirmingSave] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const saveButtonRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  const dirty =
    isEditing &&
    selection !== null &&
    (draftMissing ? selection.value !== null : draftValue !== (selection.value ?? ""));
  const draftValidationError =
    selection === null
      ? null
      : validateCellDraft(selection.dataType, draftMissing, draftValue);
  const correctionSourceUnavailable = version.canonical_artifact === null;

  useEffect(() => {
    setSelection(null);
    setIsEditing(false);
    setDraftMissing(false);
    setDraftValue("");
    setIsConfirmingSave(false);
    setEditError(null);
  }, [preview?.offset, preview?.limit, version.version_id]);

  useEffect(() => {
    onDirtyChange(dirty);
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      onDirtyChange(false);
    };
  }, [dirty, onDirtyChange]);

  useEffect(() => {
    if (!isConfirmingSave) return;
    const dialog = dialogRef.current;
    const focusable = dialog?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    focusable?.[0]?.focus();
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape" && !isSaving) {
        event.preventDefault();
        setIsConfirmingSave(false);
        window.requestAnimationFrame(() => saveButtonRef.current?.focus());
        return;
      }
      if (event.key !== "Tab" || focusable === undefined || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isConfirmingSave, isSaving]);

  const confirmDiscard = () =>
    !dirty ||
    window.confirm("저장하지 않은 셀 수정이 있습니다. 변경을 버리고 이동하시겠습니까?");

  const selectCell = (next: CanonicalCellSelection) => {
    if (selection?.address !== next.address && !confirmDiscard()) return;
    setSelection(next);
    setIsEditing(false);
    setDraftMissing(false);
    setDraftValue(next.value ?? "");
    setEditError(null);
  };

  const submitJump = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!confirmDiscard()) return;
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
              onChange={(event) => {
                if (!confirmDiscard()) return;
                onPreviewLimitChange(Number(event.currentTarget.value));
              }}
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
                if (!confirmDiscard()) return;
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
                if (!confirmDiscard()) return;
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
                          onClick={() => selectCell({
                            address,
                            columnName: preview.columns[columnIndex]?.display_name ?? address,
                            columnId: preview.columns[columnIndex]?.column_id ?? "",
                            dataType: preview.columns[columnIndex]?.data_type ?? "text",
                            role: preview.columns[columnIndex]?.role ?? "unspecified",
                            rowIndex: row.row_index,
                            rowNumber: row.row_index + 1,
                            value,
                          })}
                          onFocus={() => selectCell({
                            address,
                            columnName: preview.columns[columnIndex]?.display_name ?? address,
                            columnId: preview.columns[columnIndex]?.column_id ?? "",
                            dataType: preview.columns[columnIndex]?.data_type ?? "text",
                            role: preview.columns[columnIndex]?.role ?? "unspecified",
                            rowIndex: row.row_index,
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
            {selection === null ? (
              <output className="cell-inspector-value">선택된 셀 없음</output>
            ) : isEditing ? (
              <div className="cell-editor">
                <label>
                  <span>새 값</span>
                  <textarea
                    disabled={draftMissing || isSaving}
                    rows={2}
                    value={draftValue}
                    onChange={(event) => {
                      setDraftValue(event.currentTarget.value);
                      setEditError(null);
                    }}
                  />
                </label>
                <label className="inline-check-control">
                  <input
                    checked={draftMissing}
                    disabled={isSaving}
                    type="checkbox"
                    onChange={(event) => {
                      setDraftMissing(event.currentTarget.checked);
                      setEditError(null);
                    }}
                  />
                  결측으로 설정
                </label>
                {selection.role === "id" ? (
                  <p className="warning-text">
                    ID 역할 변수는 수정 후 고유값 중복 여부를 데이터 품질 점검에서
                    다시 확인하세요.
                  </p>
                ) : null}
                {editError !== null ? (
                  <p className="error-text" role="alert">
                    {cellDraftValidationMessage(editError)}
                    <span className="cell-subtext">오류 코드: {editError}</span>
                  </p>
                ) : null}
                {correctionSourceUnavailable ? (
                  <p className="warning-text">
                    수정 원본의 무결성 정보를 확인할 수 없어 새 버전을 만들 수 없습니다.
                  </p>
                ) : null}
                <div className="button-row">
                  <button
                    className="secondary-button"
                    disabled={isSaving}
                    type="button"
                    onClick={() => {
                      setIsEditing(false);
                      setDraftMissing(false);
                      setDraftValue(selection.value ?? "");
                      setEditError(null);
                    }}
                  >
                    수정 취소
                  </button>
                  <button
                    className="primary-button"
                    disabled={
                      !dirty ||
                      isSaving ||
                      draftValidationError !== null ||
                      correctionSourceUnavailable
                    }
                    ref={saveButtonRef}
                    type="button"
                    onClick={() => {
                      if (draftValidationError !== null) {
                        setEditError(draftValidationError);
                        return;
                      }
                      setIsConfirmingSave(true);
                    }}
                  >
                    새 버전으로 저장
                  </button>
                </div>
              </div>
            ) : (
              <>
                <output className="cell-inspector-value">
                  {selection.value === null
                    ? "(결측)"
                    : selection.value === ""
                      ? "(빈 문자열)"
                      : selection.value}
                </output>
                <button
                  className="secondary-button cell-edit-button"
                  type="button"
                  onClick={() => {
                    setDraftValue(selection.value ?? "");
                    setDraftMissing(selection.value === null);
                    setIsEditing(true);
                    setSuccessMessage(null);
                  }}
                >
                  수정
                </button>
              </>
            )}
            {successMessage !== null ? (
              <p className="success-box" role="status">{successMessage}</p>
            ) : null}
          </section>
          {isConfirmingSave && selection !== null ? (
            <div className="modal-backdrop">
              <div
                aria-labelledby="cell-correction-dialog-title"
                aria-modal="true"
                className="confirmation-dialog"
                ref={dialogRef}
                role="dialog"
              >
                <h3 id="cell-correction-dialog-title">
                  셀 수정 내용을 새 데이터셋 버전으로 저장
                </h3>
                <dl className="confirmation-summary">
                  <div><dt>원본 버전</dt><dd>v{version.version_number}</dd></div>
                  <div><dt>위치</dt><dd>{selection.rowNumber}행 · {selection.columnName}</dd></div>
                  <div>
                    <dt>기존 값</dt>
                    <dd>{displayCellValue(selection.value)}</dd>
                  </div>
                  <div>
                    <dt>새 값</dt>
                    <dd>{displayCellValue(draftMissing ? null : draftValue)}</dd>
                  </div>
                </dl>
                <p>
                  기존 v{version.version_number}은 변경되지 않습니다. 수정된 데이터는
                  새로운 v{version.version_number + 1} 이상 버전으로 저장되며, 기존
                  버전에 저장된 분석·모델·리포트도 변경되지 않습니다.
                </p>
                <div className="button-row dialog-actions">
                  <button
                    className="secondary-button"
                    disabled={isSaving}
                    type="button"
                    onClick={() => {
                      setIsConfirmingSave(false);
                      window.requestAnimationFrame(() => saveButtonRef.current?.focus());
                    }}
                  >
                    취소
                  </button>
                  <button
                    className="primary-button"
                    disabled={isSaving}
                    type="button"
                    onClick={() => {
                      setIsSaving(true);
                      setEditError(null);
                      void onCreateCellCorrection({
                        confirmation_parent_version_id: version.version_id,
                        expected_parent_schema_hash: version.schema_hash,
                        expected_parent_canonical_sha256:
                          version.canonical_artifact?.sha256 ?? "",
                        edits: [{
                          row_index: selection.rowIndex,
                          column_id: selection.columnId,
                          operation: draftMissing ? "set_missing" : "set_value",
                          value: draftMissing ? null : draftValue,
                        }],
                      })
                        .then((response) => {
                          setIsConfirmingSave(false);
                          setIsEditing(false);
                          setSelection(null);
                          setSuccessMessage(
                            `셀 수정 내용을 데이터셋 v${response.new_version.version_number}로 저장했습니다. 원본 v${version.version_number}은 그대로 유지됩니다.`,
                          );
                        })
                        .catch((error) => {
                          setIsConfirmingSave(false);
                          setEditError(
                            error instanceof Error
                              ? error.message
                              : "dataset_cell_correction_failed",
                          );
                        })
                        .finally(() => setIsSaving(false));
                    }}
                  >
                    {isSaving ? "새 버전 생성 중" : `v${version.version_number + 1} 생성`}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </>
      ) : (
        <div className="notice-box">버전 생성 후 행 미리보기를 불러옵니다.</div>
      )}
    </section>
  );
}

function displayCellValue(value: string | null): string {
  if (value === null) return "(결측)";
  if (value === "") return "(빈 문자열)";
  return value;
}

function validateCellDraft(
  dataType: DatasetColumnResponse["data_type"],
  missing: boolean,
  value: string,
): string | null {
  if (missing || dataType === "text" || dataType === "boolean") return null;
  if (dataType === "integer") {
    return /^[+-]?\d+$/.test(value.trim())
      ? null
      : "dataset_cell_correction_value_invalid";
  }
  if (dataType === "decimal") {
    return value.trim() !== "" && Number.isFinite(Number(value))
      ? null
      : "dataset_cell_correction_value_invalid";
  }
  if (dataType === "datetime") {
    return value.trim() !== "" && !Number.isNaN(Date.parse(value))
      ? null
      : "dataset_cell_correction_value_invalid";
  }
  return null;
}

function cellDraftValidationMessage(code: string): string {
  return code === "dataset_cell_correction_value_invalid"
    ? "선택한 컬럼 타입으로 해석할 수 있는 값을 입력하세요."
    : "셀 수정 내용을 확인할 수 없습니다.";
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
