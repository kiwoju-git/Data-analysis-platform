import type { DatasetColumnResponse } from "./api";
import { toggleGraphVariableSelection } from "./graphVariableSelection";

interface GraphVariablePickerProps {
  columns: DatasetColumnResponse[];
  disabledIds?: string[];
  label: string;
  maximum: number;
  selectedIds: string[];
  onChange: (columnIds: string[]) => void;
}

export function GraphVariablePicker({
  columns,
  disabledIds = [],
  label,
  maximum,
  selectedIds,
  onChange,
}: GraphVariablePickerProps) {
  const limitReached = selectedIds.length >= maximum;
  const helperId = `graph-variable-picker-${slugify(label)}-helper`;
  const selectionCountLabel = `선택 ${selectedIds.length.toLocaleString()} / ${maximum.toLocaleString()}`;
  const limitMessage = `최대 ${maximum.toLocaleString()}개를 선택했습니다. 다른 변수를 선택하려면 하나를 해제하세요.`;

  return (
    <fieldset className="graph-variable-picker" aria-describedby={helperId}>
      <legend>{label}</legend>
      <div className="graph-variable-picker-heading">
        <p id={helperId}>최대 {maximum.toLocaleString()}개</p>
        <div className="graph-variable-picker-actions">
          <span>{selectionCountLabel}</span>
          <button
            className="secondary-button graph-variable-clear"
            disabled={selectedIds.length === 0}
            onClick={() => onChange([])}
            type="button"
          >
            모두 지우기
          </button>
        </div>
      </div>
      <div className="graph-variable-option-grid">
        {columns.map((column) => {
          const selected = selectedIds.includes(column.column_id);
          const disabled = disabledIds.includes(column.column_id) || (limitReached && !selected);
          return (
            <label
              className={
                selected
                  ? "graph-variable-option is-selected"
                  : "graph-variable-option"
              }
              key={column.column_id}
            >
              <input
                checked={selected}
                disabled={disabled}
                onChange={() =>
                  onChange(
                    toggleGraphVariableSelection(
                      selectedIds,
                      column.column_id,
                      maximum,
                    ),
                  )
                }
                type="checkbox"
              />
              <span className="graph-variable-option-copy">
                <strong>{column.display_name}</strong>
                {column.unit ? <small>{column.unit}</small> : null}
              </span>
            </label>
          );
        })}
      </div>
      {limitReached ? (
        <p className="graph-variable-limit" role="status">{limitMessage}</p>
      ) : null}
    </fieldset>
  );
}

function slugify(value: string): string {
  return (
    value
      .normalize("NFKD")
      .replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .toLowerCase() || "values"
  );
}
