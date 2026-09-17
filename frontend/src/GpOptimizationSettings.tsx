import type { GpLengthScale, GpOptimizer } from "./api/types/analysisResultsRegression";
import { useI18n } from "./i18n/LocaleProvider";

export interface GpLengthDraft { lower: string; initial: string; upper: string }
export function gpLengthPreset(standardized: boolean, legacy = false): GpLengthDraft {
  return { lower: standardized && !legacy ? "0.5" : "0.01", initial: "1", upper: "100" };
}
export function gpLengthValue(draft: GpLengthDraft, standardized: boolean, optimizer: GpOptimizer): GpLengthScale | null {
  const values = [draft.lower, draft.initial, draft.upper].map(Number);
  if ([draft.lower, draft.initial, draft.upper].some((value) => value.trim() === "") ||
    values.some((value) => !Number.isFinite(value) || value <= 0)) return null;
  const [lower, initial, upper] = values;
  if (lower >= upper || initial < lower || initial > upper ||
    (optimizer === "bfgs" && (initial === lower || initial === upper))) return null;
  return { lower, initial, upper, coordinate_system: standardized ? "standardized" : "original" };
}

export function GpOptimizationSettings({ draft, onChange, optimizer, onOptimizerChange, standardized }: {
  draft: GpLengthDraft; onChange: (draft: GpLengthDraft) => void;
  optimizer: GpOptimizer; onOptimizerChange: (optimizer: GpOptimizer) => void; standardized: boolean;
}) {
  const { t } = useI18n();
  const valid = gpLengthValue(draft, standardized, optimizer) !== null;
  return <fieldset className="gp-optimization-settings">
    <legend>{t("gp.optimization.title")}</legend>
    <p id="gp-length-coordinate-help" className="field-help">{t(standardized ? "gp.optimization.standardized" : "gp.optimization.original")}</p>
    <div className="option-grid option-grid-wide">
      {(["lower", "initial", "upper"] as const).map((key) => <label key={key}>
        <span>{t(`gp.optimization.${key}`)}</span>
        <input type="number" step="any" min="0" value={draft[key]} aria-invalid={!valid}
          aria-describedby="gp-length-coordinate-help gp-length-validation"
          onChange={(event) => onChange({ ...draft, [key]: event.currentTarget.value })} />
      </label>)}
      <label><span>{t("gp.optimization.optimizer")}</span><select value={optimizer} aria-label={t("gp.optimization.optimizer")}
        onChange={(event) => onOptimizerChange(event.currentTarget.value as GpOptimizer)}>
        <option value="l_bfgs_b">L-BFGS-B</option><option value="bfgs">BFGS</option>
      </select></label>
    </div>
    <div className="button-row"><button className="secondary-button compact-button" type="button" onClick={() => onChange(gpLengthPreset(standardized, true))}>{t("gp.optimization.legacy")}</button>
      {standardized ? <button className="secondary-button compact-button" type="button" onClick={() => onChange(gpLengthPreset(true))}>{t("gp.optimization.smooth")}</button> : null}</div>
    <p className="field-help">{t(optimizer === "bfgs" ? "gp.optimization.bfgsHelp" : "gp.optimization.lbfgsbHelp")}</p>
    <p id="gp-length-validation" role={valid ? undefined : "alert"}>{valid ? null : t("gp.optimization.invalid")}</p>
  </fieldset>;
}
