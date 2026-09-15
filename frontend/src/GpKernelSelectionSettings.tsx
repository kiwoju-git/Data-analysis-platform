import { useId } from "react";
import type { GpKernelPreset, GpKernelSelection } from "./api/types/analysisResultsRegression";
import { t } from "./i18n/translate";

export const gpPresets: readonly GpKernelPreset[] = ["matern_5_2_ard", "matern_3_2_ard", "rbf_ard", "rational_quadratic"];
export function gpKernelName(preset: GpKernelPreset): string {
  return t(preset === "matern_5_2_ard" ? "gp.kernel.matern52" : preset === "matern_3_2_ard" ? "gp.kernel.matern32" : preset === "rbf_ard" ? "gp.kernel.rbf" : "gp.kernel.rq");
}
export function gpOptimizerStarts(selection: GpKernelSelection, folds: number, cvRestarts: number, finalRestarts: number): number {
  const count = selection.mode === "compare" ? selection.kernel_candidates.length : 1;
  return count * folds * (1 + cvRestarts) + (selection.mode === "compare" && selection.retain_candidate_details ? count : 1) * (1 + finalRestarts);
}

export function GpKernelSelectionSettings({ value, onChange, onModeChange, noiseMode, disabled }: {
  value: GpKernelSelection; onChange: (value: Extract<GpKernelSelection, { mode: "compare" }>) => void;
  onModeChange: (mode: GpKernelSelection["mode"]) => void; noiseMode: "estimate" | "fixed" | "near_noiseless"; disabled: boolean;
}) {
  const id = useId();
  const presets = value.mode === "single" ? [value.kernel_preset] : value.kernel_candidates;
  return <fieldset className="gp-kernel-selection" disabled={disabled} aria-describedby={`${id}-noise`}>
    <legend>{t("gp.selection.mode")}</legend>
    <div className="segmented-control">{(["single", "compare"] as const).map((mode) => <label key={mode}>
      <input type="radio" name={`${id}-mode`} value={mode} checked={value.mode === mode} onChange={() => onModeChange(mode)} />
      <span>{t(`gp.selection.${mode}`)}</span></label>)}</div>
    {value.mode === "compare" ? <>
      <fieldset className="gp-kernel-candidates"><legend>{t("gp.selection.candidates")}</legend>
        {gpPresets.map((preset) => <label key={preset}><input type="checkbox" checked={value.kernel_candidates.includes(preset)} onChange={(event) => onChange({ ...value,
          kernel_candidates: event.currentTarget.checked ? gpPresets.filter((item) => item === preset || value.kernel_candidates.includes(item)) : value.kernel_candidates.filter((item) => item !== preset),
        })} /><span>{gpKernelName(preset)}</span></label>)}
      </fieldset>
      {value.kernel_candidates.length < 2 ? <p role="alert" className="field-help">{t("gp.selection.minimum")}</p> : null}
      <div className="option-grid"><label><span>{t("gp.selection.criterion")}</span><select value={value.criterion} onChange={(event) => onChange({ ...value, criterion: event.currentTarget.value as typeof value.criterion })}>
        <option value="cv_nlpd">{t("gp.nlpd")}</option><option value="cv_rmse">{t("gp.cvRmse")}</option><option value="cv_mae">{t("gp.cvMae")}</option>
      </select></label>
      <label className="checkbox-field"><input type="checkbox" checked={value.retain_candidate_details} onChange={(event) => onChange({ ...value, retain_candidate_details: event.currentTarget.checked })} /><span>{t("gp.selection.details")}</span></label></div>
    </> : null}
    <dl className="gp-kernel-composition"><dt>{t("gp.selection.combined")}</dt><dd>{presets.map((preset) => `Constant * ${gpKernelName(preset)}${noiseMode === "estimate" ? " + WhiteKernel" : ""}`).join("; ")}</dd></dl>
    <p className="field-help" id={`${id}-noise`}>{t(noiseMode === "estimate" ? "gp.selection.whiteHelp" : noiseMode === "fixed" ? "gp.selection.fixedHelp" : "gp.selection.jitterHelp")}</p>
  </fieldset>;
}
