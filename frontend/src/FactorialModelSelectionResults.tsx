import { useState } from "react";
import type { DoeFinalModelWorkflow, DoeModelSelectionResult } from "./api/types/doeModelWorkflow";
import { t, type TranslationKey } from "./i18n/translate";

import { factorialNumber } from "./doe/factorialWorkflowPresentation";
import { DoeSelectionStepMatrix } from "./doe/DoeSelectionStepMatrix";
import { doeTermLabel } from "./doe/DoeTermSelection";

const stopKeys: Record<string, TranslationKey> = {
  residual_variance_unavailable: "doe.selection.stop.residual_variance_unavailable",
  all_terms_below_alpha: "doe.selection.stop.all_terms_below_alpha",
  no_removable_terms_due_to_hierarchy: "doe.selection.stop.no_removable_terms_due_to_hierarchy",
  intercept_only_or_structural_terms_only: "doe.selection.stop.intercept_only_or_structural_terms_only",
  insufficient_residual_df: "doe.selection.stop.insufficient_residual_df",
  rank_failure: "doe.selection.stop.rank_failure",
  maximum_steps_reached: "doe.selection.stop.maximum_steps_reached",
  selection_not_requested: "doe.selection.stop.selection_not_requested",
  not_requested: "doe.selection.stop.selection_not_requested",
};

export function FactorialModelSelectionResults({ selection, model, fit, n }: {
  selection: DoeModelSelectionResult; model: DoeFinalModelWorkflow;
  fit: { r_squared: number; adjusted_r_squared: number | null; residual_standard_error?: number | null };
  n: number;
}) {
  const [copied, setCopied] = useState(false);
  const termLabels = new Map(selection.term_catalog?.map((term) => [term.term_id, doeTermLabel(term)]));
  const termList = (ids: readonly string[]) => ids.map((id) => termLabels.get(id) ?? id).join(", ") || "-";
  const equation = [String(model.equation.intercept), ...model.equation.terms
    .filter((term) => term.kind !== "intercept")
    .map((term) => `${term.coefficient < 0 ? "-" : "+"} ${Math.abs(term.coefficient)} * ${term.label}`)].join(" ");
  return <>
    <section className="result-section factorial-selection-results">
      <h3>{t("doe.selection.title")}</h3>
      <dl className="result-definition-grid">
        <div><dt>{t("doe.selection.title")}</dt><dd>{t(selection.method === "none" ? "doe.selection.none" : "doe.selection.backward")}</dd></div>
        {selection.method !== "none" ? <div><dt>{t("doe.selection.alpha")}</dt><dd>{selection.alpha_to_remove}</dd></div> : null}
        {([
          ["doe.selection.initial", selection.initial_term_ids.length], ["doe.selection.pooled", selection.pooled_term_ids.length],
          ["doe.selection.removed", selection.removed_term_ids.length], ["doe.selection.final", selection.final_term_ids.length],
        ] as const).map(([key, value]) => <div key={key}><dt>{t(key)}</dt><dd>{value}</dd></div>)}
        <div><dt>{t("doe.selection.stop")}</dt><dd>{stopKeys[selection.stop_reason] ? t(stopKeys[selection.stop_reason]) : selection.stop_reason}</dd></div>
        {selection.initial_model_saturated && selection.method !== "none" ? <>
          <div><dt>{t("doe.selection.initialParameters")}</dt><dd>{selection.initial_parameter_count}</dd></div>
          <div><dt>{t("doe.selection.initialDf")}</dt><dd>{selection.initial_residual_df}</dd></div>
          <div><dt>{t("doe.selection.poolTarget")}</dt><dd>{selection.target_pool_count}</dd></div>
          <div><dt>{t("doe.selection.finalDf")}</dt><dd>{model.prediction_basis.residual_df}</dd></div>
        </> : null}
      </dl>
      {selection.term_catalog ? <dl className="doe-term-summary">{([
        ["doe.terms.candidates", selection.candidate_term_ids ?? selection.initial_term_ids],
        ["doe.terms.userExcluded", selection.initially_excluded_term_ids ?? []],
        ["doe.terms.forced", selection.fixed_term_ids],
        ["doe.selection.removed", [...selection.pooled_term_ids, ...selection.removed_term_ids]],
        ["doe.selection.final", selection.final_term_ids],
      ] as const).map(([key, ids]) => <div key={key}><dt>{t(key)}</dt><dd>{termList(ids)}</dd></div>)}</dl> : null}
      {selection.initial_model_saturated && selection.method !== "none" ? <p className="notice-box notice-warning">{t("doe.selection.poolingPolicy")} {selection.pooled_term_ids.join(", ")}</p> : null}
      {selection.method !== "none" ? <p className="notice-box notice-warning">{t("doe.selection.exploratory")}</p> : null}
      {selection.method !== "none" && selection.display_step_details && selection.steps[0]?.term_statistics?.length ? <DoeSelectionStepMatrix selection={selection} multiDf={model.equation.scale === "treatment"} /> : null}
      {selection.method !== "none" && selection.steps.length > 0 && !selection.steps[0]?.term_statistics?.length ? <div className="table-wrap"><table className="result-table factorial-selection-steps">
        <thead><tr><th>#</th><th>{t("doe.selection.phase")}</th><th>{t("doe.selection.removed")}</th><th>Adj SS</th><th>P</th><th>DF</th><th>S</th><th>R²</th><th>Adj R²</th><th>Pred R²</th><th>PRESS</th><th>{t("doe.selection.active")}</th></tr></thead>
        <tbody>{selection.steps.map((step) => <tr key={step.step}>
          <td>{step.step}</td><td>{t(`doe.selection.phase.${step.phase}`)}</td><td>{step.removed_term_id ?? "-"}</td>
          {[step.removal_adjusted_ss, step.removal_p_value, step.residual_df, step.residual_standard_error, step.r_squared, step.adjusted_r_squared, step.predicted_r_squared, step.press].map((value, index) => <td key={index}>{factorialNumber(value)}</td>)}
          <td><details><summary>{t("doe.selection.active")}</summary><p>{step.active_term_ids.join(", ")}</p>
            <pre>{step.coefficients.map((item) => `${item.column_index}: ${item.coefficient}`).join("\n")}</pre></details></td>
        </tr>)}</tbody>
      </table></div> : null}
    </section>
    <section className="result-section factorial-equation">
      <div className="panel-heading compact-heading"><h3>{t(model.equation.scale === "coded" ? "doe.equation.coded" : "doe.equation.treatment")}</h3>
        <button type="button" className="secondary-button" onClick={() => { void navigator.clipboard.writeText(`${model.equation.response_name} = ${equation}`).then(() => setCopied(true)).catch(() => setCopied(false)); }}>
          {t(copied ? "doe.equation.copied" : "doe.equation.copy")}</button></div>
      <p className="factorial-equation-text">{model.equation.display_equation}</p><p className="field-help">{t("doe.equation.policy")}</p>
    </section>
    <section className="result-section"><h3>{t("doe.model.summary")}</h3>
      <dl className="result-definition-grid">{[
        ["S", fit.residual_standard_error ?? (model.prediction_basis.residual_mean_square === null ? null : Math.sqrt(model.prediction_basis.residual_mean_square))],
        ["R²", fit.r_squared], ["Adjusted R²", fit.adjusted_r_squared], ["Predicted R²", model.predicted_r_squared], ["PRESS", model.press], ["N", n], ["Residual DF", model.prediction_basis.residual_df],
      ].map(([label, value]) => <div key={label as string}><dt>{label}</dt><dd>{factorialNumber(value as number | null)}</dd></div>)}</dl>
    </section>
    <section className="result-section"><h3>{t(model.equation.scale === "coded" ? "doe.model.coefficients" : "doe.model.treatmentCoefficients")}</h3>
      <div className="table-wrap"><table className="result-table factorial-coded-coefficients"><thead><tr>
        <th>{t("doe.model.term")}</th><th>Effect</th><th>Coef</th><th>SE Coef</th><th>T-Value</th><th>P-Value</th><th>VIF</th><th>{t("doe.model.status")}</th>
      </tr></thead><tbody>{model.coded_coefficients.map((term, index) => <tr key={`${term.term_id}-${index}`}><td>{term.label}</td>
        {[term.effect, term.coefficient, term.standard_error, term.t_statistic, term.p_value, term.vif].map((value, cell) => <td key={cell} title={value === null ? t("doe.model.unavailable") : String(value)}>{factorialNumber(value)}</td>)}
        <td>{t(term.status === "structural" ? "doe.model.structural" : "doe.model.retained")}</td>
      </tr>)}</tbody></table></div><p className="field-help">{t("doe.model.vifPolicy")}</p>
    </section>
    {model.anova_groups?.length ? <section className="result-section factorial-grouped-anova"><h3>ANOVA</h3>
      <p className="field-help">{t("doe.anova.policy")}</p>
      {model.anova_groups.map((group) => <details key={group.kind}><summary>{t(group.kind === "main_effect" ? "doe.anova.linear" : group.kind === "block" ? "doe.anova.blocks" : group.kind === "center_curvature" ? "doe.anova.curvature" : group.kind === "interaction_2" ? "doe.anova.twoWay" : "doe.anova.threeWay")} · DF {group.df} · Adj SS {factorialNumber(group.adjusted_ss)}</summary>
        <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("doe.model.term")}</th><th>DF</th><th>Adj SS</th><th>Adj MS</th><th>F</th><th>P</th></tr></thead><tbody>
          {[{ ...group, label: t("doe.anova.group") }, ...group.terms].map((row, index) => <tr key={index}><td>{row.label}</td>{[row.df, row.adjusted_ss, row.mean_square, row.f_statistic, row.p_value].map((value, cell) => <td key={cell}>{factorialNumber(value)}</td>)}</tr>)}
        </tbody></table></div></details>)}
    </section> : null}
  </>;
}
