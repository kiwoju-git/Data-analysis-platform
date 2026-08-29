import type { DatasetColumnResponse } from "../api";
import { useI18n } from "../i18n/LocaleProvider";

interface NumericColumnPickerProps {
  className?: string;
  columns: readonly DatasetColumnResponse[];
  excludedColumnIds?: readonly string[];
  helpText: string;
  legend: string;
  maximumSelection: number;
  minimumSelection: number;
  onClear?: () => void;
  onToggle: (columnId: string, checked: boolean) => void;
  selectedColumnIds: readonly string[];
  selectedCountLabel?: string;
}

export function NumericColumnPicker({
  className,
  columns,
  excludedColumnIds = [],
  helpText,
  legend,
  maximumSelection,
  minimumSelection,
  onClear,
  onToggle,
  selectedColumnIds,
  selectedCountLabel,
}: NumericColumnPickerProps) {
  const { t } = useI18n();
  const excluded = new Set(excludedColumnIds);
  const visibleColumns = columns.filter((column) => !excluded.has(column.column_id));
  const selectionValid = selectedColumnIds.length >= minimumSelection;
  return (
    <fieldset
      className={["checkbox-field", "numeric-column-picker", className]
        .filter(Boolean)
        .join(" ")}
      data-selection-valid={selectionValid}
    >
      <legend>{legend}</legend>
      <div className="numeric-column-picker-heading">
        <small>{helpText}</small>
        <div>
          <span>
            {selectedCountLabel ?? t("columnPicker.selectedCount", {
              selected: selectedColumnIds.length,
              maximum: maximumSelection,
            })}
          </span>
          {onClear === undefined ? null : (
            <button
              className="secondary-button compact-button"
              disabled={selectedColumnIds.length === 0}
              type="button"
              onClick={onClear}
            >
              {t("columnPicker.clear")}
            </button>
          )}
        </div>
      </div>
      <div className="numeric-column-picker-grid">
        {visibleColumns.map((column) => {
          const checked = selectedColumnIds.includes(column.column_id);
          return (
            <label key={column.column_id}>
              <input
                checked={checked}
                disabled={!checked && selectedColumnIds.length >= maximumSelection}
                type="checkbox"
                onChange={(event) => onToggle(column.column_id, event.currentTarget.checked)}
              />
              <span>{column.display_name}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
