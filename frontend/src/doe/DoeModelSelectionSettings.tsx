import { useId } from "react";
import type { DoeModelSelectionOptions } from "../api/types/doeModelWorkflow";
import { t } from "../i18n/translate";

export function DoeModelSelectionSettings({ value, onChange, confidence, onConfidenceChange, aliased = false, selectionSupported = !aliased, disabled = false, modelKind = "factorial" }: {
  value: DoeModelSelectionOptions; onChange: (value: DoeModelSelectionOptions) => void;
  confidence: number; onConfidenceChange: (value: number) => void;
  aliased?: boolean; selectionSupported?: boolean; disabled?: boolean;
  modelKind?: "factorial" | "rsm";
}) {
  const id = useId();
  return <fieldset className="doe-model-selection" disabled={disabled} aria-describedby={`${id}-policy`}>
    <legend>{t("doe.selection.title")}</legend>
    <div className="option-grid">
      <label><span>{t("doe.selection.title")}</span><select value={value.method}
        onChange={(event) => onChange({ ...value, method: event.currentTarget.value as DoeModelSelectionOptions["method"] })}>
        <option value="none">{t("doe.selection.none")}</option>
        <option value="backward_elimination" disabled={!selectionSupported}>{t("doe.selection.backward")}</option>
      </select></label>
      {value.method === "backward_elimination" && selectionSupported ? <label>
        <span>{t("doe.selection.alpha")}</span><input type="number" step="0.01" min="0.000001" max="0.999999"
          value={Number.isFinite(value.alpha_to_remove) ? value.alpha_to_remove : ""}
          aria-invalid={!(value.alpha_to_remove > 0 && value.alpha_to_remove < 1)}
          onChange={(event) => onChange({ ...value, alpha_to_remove: event.currentTarget.valueAsNumber })} />
      </label> : null}
      <label><span>{t("doe.selection.confidence")}</span><input type="number" min="0.01" max="0.999" step="0.01"
        value={Number.isFinite(confidence) ? confidence : ""} onChange={(event) => onConfidenceChange(event.currentTarget.valueAsNumber)} /></label>
    </div>
    <p className="field-help" id={`${id}-policy`}>{t(!selectionSupported ? "doe.selection.aliased" : "doe.selection.hierarchy")}</p>
    {value.method === "backward_elimination" && selectionSupported ? <>
      <p className="notice-box notice-warning">{t(modelKind === "rsm" ? "doe.rsm.selectionDf" : "doe.selection.poolingPolicy")}</p>
      <label className="doe-table-toggle"><input type="checkbox" checked={value.display_step_details}
        onChange={(event) => onChange({ ...value, display_step_details: event.currentTarget.checked })} />
        <span>{t("doe.selection.details")}</span></label>
    </> : null}
  </fieldset>;
}
