import type { ReactNode } from "react";

import {
  CompactSettingsTable,
  type CompactSettingsField,
} from "../components/CompactSettingsTable";

export interface DoeSettingsField extends CompactSettingsField {
  label: ReactNode;
  control: ReactNode;
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
  return (
    <CompactSettingsTable
      ariaLabel={ariaLabel}
      className={`doe-settings-table ${className}`.trim()}
      fields={fields}
    />
  );
}
