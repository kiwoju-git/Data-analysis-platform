import { useId, type ReactNode } from "react";

export interface DoeSettingsField {
  key: string;
  label: ReactNode;
  control: ReactNode;
  controlId?: string;
  helper?: ReactNode;
  helperId?: string;
  helperTone?: "neutral" | "error";
}

export function DoeSettingsTable({
  fields,
  ariaLabel,
  className = "",
}: {
  fields: readonly DoeSettingsField[];
  ariaLabel?: string;
  className?: string;
}) {
  const generatedId = useId().split(":").join("");
  const hasHelpers = fields.some((field) => field.helper !== undefined);
  const columnClass = `doe-settings-columns-${Math.min(fields.length, 4)}`;

  return (
    <div className="table-wrap doe-settings-table-wrap">
      <table
        aria-label={ariaLabel}
        className={`result-table doe-settings-table ${columnClass} ${className}`.trim()}
      >
        <thead>
          <tr>
            {fields.map((field) => {
              const headingId = `doe-setting-${generatedId}-${field.key}`;
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
          <tr className="doe-settings-control-row">
            {fields.map((field) => (
              <td key={field.key}>{field.control}</td>
            ))}
          </tr>
          {hasHelpers ? (
            <tr className="doe-settings-help-row">
              {fields.map((field) => (
                <td key={field.key}>
                  {field.helper !== undefined ? (
                    <span
                      className={
                        field.helperTone === "error"
                          ? "doe-settings-helper is-error"
                          : "doe-settings-helper"
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
