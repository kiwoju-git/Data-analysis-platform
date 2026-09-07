import type { RegularizedEstimator, RegularizedRunConfig } from "./api";
import { CompactSettingsTable, type CompactSettingsField } from "./components/CompactSettingsTable";
import { useI18n } from "./i18n/LocaleProvider";
import type { TranslationKey } from "./i18n/translate";

export function regularizationDefaults(estimator: RegularizedEstimator): RegularizedRunConfig {
  return {
    estimator, fixed_alpha: 1,
    regularization: { mode: "automatic_cv", validation: "k_fold", outer_folds: 5,
      inner_folds: 5, shuffle: true, random_seed: 20260907,
      alpha_candidates: estimator === "ridge" ? 49 : 50, alpha_min: 1e-6,
      alpha_max: estimator === "ridge" ? 1e6 : 10, max_iter: 10000,
      tolerance: 1e-6, time_budget_seconds: 120 },
    ...(estimator === "elastic_net" ? { l1_ratio_selection: "automatic_cv" as const,
      fixed_l1_ratio: 0.5, l1_ratio_candidates: [0.1, 0.5, 0.7, 0.9, 0.95, 0.99] } : {}),
  };
}

export function regularizationValid(config: RegularizedRunConfig): boolean {
  const cv = config.regularization;
  return Number.isFinite(cv.alpha_min) && cv.alpha_min > 0 && cv.alpha_max > cv.alpha_min &&
    Number.isFinite(cv.alpha_max) && cv.alpha_candidates >= 2 && cv.alpha_candidates <= 100 &&
    Number.isInteger(cv.alpha_candidates) && cv.outer_folds >= 2 && cv.outer_folds <= 10 &&
    cv.inner_folds >= 2 && cv.inner_folds <= 10 && Number.isInteger(cv.outer_folds) &&
    Number.isInteger(cv.inner_folds) && cv.max_iter >= 1 && cv.max_iter <= 100000 &&
    Number.isInteger(cv.max_iter) && cv.tolerance > 0 && cv.tolerance <= 0.1 &&
    cv.time_budget_seconds > 0 && cv.time_budget_seconds <= 300 &&
    Number.isInteger(cv.random_seed) && cv.random_seed >= 0 && cv.random_seed <= 4294967295 &&
    (cv.mode === "fixed" ? Number.isFinite(config.fixed_alpha) && (config.fixed_alpha ?? 0) > 0 : cv.validation !== "none") &&
    (config.estimator !== "elastic_net" || (
      (cv.mode === "fixed" || config.l1_ratio_selection === "fixed")
        ? (config.fixed_l1_ratio ?? 0) > 0 && (config.fixed_l1_ratio ?? 1) < 1
        : (config.l1_ratio_candidates?.length ?? 0) > 0 && (config.l1_ratio_candidates?.length ?? 11) <= 10 &&
          config.l1_ratio_candidates!.every((ratio) => Number.isFinite(ratio) && ratio > 0 && ratio < 1)));
}

export function RegularizationSettingsPanel({ config, rowCount, onChange }: {
  config: RegularizedRunConfig; rowCount?: number; onChange: (config: RegularizedRunConfig) => void;
}) {
  const { t } = useI18n();
  const cv = config.regularization;
  const outerCount = cv.validation === "none" ? 0 : cv.validation === "leave_one_out" ? rowCount : cv.outer_folds;
  const ratioCount = config.estimator === "elastic_net" && config.l1_ratio_selection === "automatic_cv" ? config.l1_ratio_candidates?.length ?? 0 : 1;
  const estimatedFits = outerCount === undefined ? null :
    (outerCount + 1) * (cv.mode === "automatic_cv" ? cv.inner_folds * cv.alpha_candidates * ratioCount + 1 : 1) + cv.alpha_candidates;
  function updateCv<K extends keyof typeof cv>(key: K, value: typeof cv[K]) {
    onChange({ ...config, regularization: { ...cv, [key]: value } });
  }
  const id = `regularization-${config.estimator}`;
  function numberField(key: keyof typeof cv, label: TranslationKey,
    minimum: number, maximum: number, step: number): CompactSettingsField {
    const inputId = `${id}-${key}`;
    return { key, label: t(label), controlId: inputId, control: <input id={inputId}
      type="number" min={minimum} max={maximum} step={step} value={Number(cv[key])}
      onChange={(event) => updateCv(key, Number(event.currentTarget.value))} /> };
  }
  const fields: CompactSettingsField[] = [
    { key: "mode", label: t("reg.tuning"), controlId: `${id}-mode`, control: <select
      id={`${id}-mode`} value={cv.mode} onChange={(event) => onChange({ ...config,
        regularization: { ...cv, mode: event.currentTarget.value as typeof cv.mode,
          validation: event.currentTarget.value === "automatic_cv" && cv.validation === "none" ? "k_fold" : cv.validation } })}>
      <option value="automatic_cv">{t("reg.automatic")}</option><option value="fixed">{t("reg.fixed")}</option>
    </select> },
    ...(cv.mode === "fixed" ? [{ key: "alpha", label: t("reg.alpha"), controlId: `${id}-alpha`, control:
      <input id={`${id}-alpha`} aria-describedby={`${id}-validation`} type="number" min="0.000000000001" step="any"
        value={config.fixed_alpha ?? ""} onChange={(event) => onChange({ ...config, fixed_alpha: Number(event.currentTarget.value) })} /> }] : []),
    { key: "validation", label: t("reg.validation"), controlId: `${id}-validation-mode`, control:
      <select id={`${id}-validation-mode`} value={cv.validation} onChange={(event) => updateCv("validation", event.currentTarget.value as typeof cv.validation)}>
        <option value="k_fold">{t("reg.kFold")}</option><option value="leave_one_out">{t("reg.loo")}</option>
        {cv.mode === "fixed" ? <option value="none">{t("reg.none")}</option> : null}
      </select> },
    ...(cv.validation === "k_fold" ? [numberField("outer_folds", "reg.outer", 2, 10, 1)] : []),
  ];
  return <section className="regularization-settings" aria-label={t("reg.tuning")}>
    <CompactSettingsTable fields={fields} />
    {config.estimator === "elastic_net" ? <div className="option-grid">
      {cv.mode === "automatic_cv" ? <label><span>{t("reg.ratioSelection")}</span><select value={config.l1_ratio_selection}
        onChange={(event) => onChange({ ...config, l1_ratio_selection: event.currentTarget.value as "automatic_cv" | "fixed" })}>
        <option value="automatic_cv">{t("reg.automatic")}</option><option value="fixed">{t("reg.fixed")}</option>
      </select></label> : null}
      {cv.mode === "fixed" || config.l1_ratio_selection === "fixed" ? <label><span>{t("reg.ratio")}</span>
        <input type="number" min="0.001" max="0.999" step="0.01" value={config.fixed_l1_ratio ?? ""}
          onChange={(event) => onChange({ ...config, fixed_l1_ratio: Number(event.currentTarget.value) })} /></label> :
        <fieldset><legend>{t("reg.ratioCandidates")}</legend><div className="checkbox-grid">
          {[0.1, 0.5, 0.7, 0.9, 0.95, 0.99].map((ratio) => <label key={ratio}><input type="checkbox"
            checked={config.l1_ratio_candidates?.includes(ratio) ?? false}
            onChange={(event) => onChange({ ...config, l1_ratio_candidates: event.currentTarget.checked
              ? [...(config.l1_ratio_candidates ?? []), ratio].sort((a, b) => a - b)
              : config.l1_ratio_candidates?.filter((value) => value !== ratio) })} /><span>{ratio}</span></label>)}
        </div></fieldset>}
    </div> : null}
    <p className="cell-subtle">{t("reg.scaling")}</p>
    {estimatedFits !== null ? <p className={estimatedFits > 10000 ? "warning-box" : "cell-subtle"}>{t("reg.fitBudget", { count: estimatedFits })}</p> : null}
    {cv.mode === "automatic_cv" ? <p className="cell-subtle">{t("reg.nested")}</p> : null}
    <details><summary>{t("reg.advanced")}</summary>
      <CompactSettingsTable fields={[
        numberField("alpha_min", "reg.alphaMin", 1e-12, 1e12, 0.001),
        numberField("alpha_max", "reg.alphaMax", 1e-12, 1e12, 0.1),
        numberField("alpha_candidates", "reg.alphaCount", 2, 100, 1),
        numberField("inner_folds", "reg.inner", 2, 10, 1),
      ]} />
      <CompactSettingsTable fields={[
        numberField("random_seed", "reg.seed", 0, 4294967295, 1),
        numberField("max_iter", "reg.iterations", 1, 100000, 100),
        numberField("tolerance", "reg.tolerance", 1e-12, 0.1, 0.000001),
        numberField("time_budget_seconds", "reg.timeBudget", 1, 300, 1),
      ]} />
      <label className="checkbox-field"><input type="checkbox" checked={cv.shuffle}
        onChange={(event) => updateCv("shuffle", event.currentTarget.checked)} /><span>{t("reg.shuffle")}</span></label>
    </details>
    <div id={`${id}-validation`} role="status">{regularizationValid(config) ? null : t("reg.invalid")}</div>
  </section>;
}
