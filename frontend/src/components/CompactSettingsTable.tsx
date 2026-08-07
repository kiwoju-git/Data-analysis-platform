import { useId, type ReactNode } from "react";

export interface CompactSettingsField {
  key: string;
  label: ReactNode;
  control: ReactNode;
  controlId?: string;
  helper?: ReactNode;
  helperId?: string;
  helperTone?: "neutral" | "error";
  columnClassName?: string;
}

export function CompactSettingsTable({
  fields,
  ariaLabel,
  className = "",
}: {
  fields: readonly CompactSettingsField[];
  ariaLabel?: string;
  className?: string;
}) {
  const generatedId = useId().split(":").join("");
  const hasHelpers = fields.some((field) => field.helper !== undefined);
  const columnClass = `compact-settings-columns-${Math.min(fields.length, 4)}`;

  return (
    <div className="table-wrap compact-settings-table-wrap">
      <table
        aria-label={ariaLabel}
        className={`result-table ${className} compact-settings-table ${columnClass}`.trim()}
      >
        <colgroup>
          {fields.map((field) => (
            <col className={field.columnClassName} key={field.key} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {fields.map((field) => {
              const headingId = `compact-setting-${generatedId}-${field.key}`;
              return (
                <th id={headingId} key={field.key} scope="col">
                  {field.controlId ? (
                    <label htmlFor={field.controlId}>{field.label}</label>
                  ) : (
                    field.label
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          <tr className="compact-settings-control-row">
            {fields.map((field) => <td key={field.key}>{field.control}</td>)}
          </tr>
          {hasHelpers ? (
            <tr className="compact-settings-help-row">
              {fields.map((field) => (
                <td key={field.key}>
                  {field.helper !== undefined ? (
                    <span
                      className={
                        field.helperTone === "error"
                          ? "compact-settings-helper is-error"
                          : "compact-settings-helper"
                      }
                      id={field.helperId}
                    >
                      {field.helper}
                    </span>
                  ) : null}
                </td>
              ))}
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
