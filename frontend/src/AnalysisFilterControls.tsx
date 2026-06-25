import type { AnalysisFilterOperator, DatasetColumnResponse } from "./api";
import {
  createDefaultFilterDraft,
  filterOperatorOptions,
  filterOperatorRequiresValue,
  findFilterColumn,
  isNumericFilterColumn,
  normalizeFilterDraft,
  type AnalysisFilterDraft,
} from "./analysisFilters";

interface AnalysisFilterControlsProps {
  columns: DatasetColumnResponse[];
  drafts: AnalysisFilterDraft[];
  onChange: (drafts: AnalysisFilterDraft[]) => void;
}

export function AnalysisFilterControls({
  columns,
  drafts,
  onChange,
}: AnalysisFilterControlsProps) {
  function updateDraft(id: string, patch: Partial<AnalysisFilterDraft>) {
    onChange(
      drafts.map((draft) =>
        draft.id === id ? normalizeFilterDraft({ ...draft, ...patch }, columns) : draft,
      ),
    );
  }

  function removeDraft(id: string) {
    onChange(drafts.filter((draft) => draft.id !== id));
  }

  function addDraft() {
    const draft = createDefaultFilterDraft(columns);
    if (draft !== null) {
      onChange([...drafts, draft]);
    }
  }

  return (
    <section className="filter-panel" aria-labelledby="analysis-filter-title">
      <div className="filter-heading">
        <div>
          <h4 id="analysis-filter-title">분석 필터</h4>
          <p>{drafts.length === 0 ? "전체 행" : `AND ${drafts.length}개 조건`}</p>
        </div>
        <div className="filter-actions">
          <button
            className="secondary-button"
            disabled={columns.length === 0}
            onClick={addDraft}
            type="button"
          >
            조건 추가
          </button>
          <button
            className="secondary-button"
            disabled={drafts.length === 0}
            onClick={() => {
              onChange([]);
            }}
            type="button"
          >
            모두 지우기
          </button>
        </div>
      </div>
      {drafts.length === 0 ? (
        <div className="notice-box">필터 없음</div>
      ) : (
        <div className="filter-list">
          {drafts.map((draft, index) => {
            const normalizedDraft = normalizeFilterDraft(draft, columns);
            const selectedColumn = findFilterColumn(columns, normalizedDraft.column_id);
            const operatorOptions =
              selectedColumn === null ? [] : filterOperatorOptions(selectedColumn);
            const requiresValue = filterOperatorRequiresValue(normalizedDraft.operator);

            return (
              <div className="filter-row" key={draft.id}>
                <label>
                  <span>컬럼</span>
                  <select
                    aria-label={`필터 ${index + 1} 컬럼`}
                    value={normalizedDraft.column_id}
                    onChange={(event) => {
                      updateDraft(draft.id, { column_id: event.currentTarget.value });
                    }}
                  >
                    {columns.map((column) => (
                      <option key={column.column_id} value={column.column_id}>
                        {column.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>조건</span>
                  <select
                    aria-label={`필터 ${index + 1} 조건`}
                    value={normalizedDraft.operator}
                    onChange={(event) => {
                      updateDraft(draft.id, {
                        operator: event.currentTarget.value as AnalysisFilterOperator,
                      });
                    }}
                  >
                    {operatorOptions.map((operator) => (
                      <option key={operator.value} value={operator.value}>
                        {operator.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>값</span>
                  <input
                    aria-label={`필터 ${index + 1} 값`}
                    disabled={!requiresValue}
                    inputMode={
                      selectedColumn !== null && isNumericFilterColumn(selectedColumn)
                        ? "decimal"
                        : "text"
                    }
                    value={requiresValue ? normalizedDraft.value : ""}
                    onChange={(event) => {
                      updateDraft(draft.id, { value: event.currentTarget.value });
                    }}
                  />
                </label>
                <button
                  className="secondary-button"
                  onClick={() => {
                    removeDraft(draft.id);
                  }}
                  type="button"
                >
                  삭제
                </button>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
