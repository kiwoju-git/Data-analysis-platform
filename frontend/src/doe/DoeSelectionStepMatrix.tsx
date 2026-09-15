import { useId, useState } from "react";
import type { DoeModelSelectionResult, DoeModelSelectionStep } from "../api/types/doeModelWorkflow";
import { t } from "../i18n/translate";
import { doeTermLabel } from "./DoeTermSelection";
import { factorialNumber } from "./factorialWorkflowPresentation";

const metrics: Array<[string, keyof DoeModelSelectionStep]> = [
  ["S", "residual_standard_error"], ["R²", "r_squared"], ["R²(adj)", "adjusted_r_squared"],
  ["R²(pred)", "predicted_r_squared"], ["PRESS", "press"], ["Mallows Cp", "mallows_cp"], ["Residual DF", "residual_df"],
];

export function DoeSelectionStepMatrix({ selection, multiDf }: { selection: DoeModelSelectionResult; multiDf: boolean }) {
  const [selected, setSelected] = useState(0);
  const id = useId();
  const steps = selection.steps;
  const chosen = steps[Math.min(selected, steps.length - 1)];
  const catalog = selection.term_catalog ?? [];
  const labels = new Map(catalog.map((term) => [term.term_id, doeTermLabel(term)]));
  const terms = catalog.filter((term) => steps.some((step) => step.active_term_ids.includes(term.term_id)));
  const stepLabel = (step: DoeModelSelectionStep) => t("doe.steps.step", { number: step.step + 1 });
  const summary = (step: DoeModelSelectionStep, key: keyof DoeModelSelectionStep) => {
    const value = step[key];
    return <span title={key === "mallows_cp" && value == null ? t("doe.steps.cpUnavailable") : undefined}>{stepNumber(typeof value === "number" ? value : null)}</span>;
  };
  if (!chosen) return null;
  return <section className="doe-step-matrix">
    <h4>{t("doe.steps.title")}</h4>
    <div className="doe-step-desktop table-wrap" tabIndex={0} aria-label={t("doe.steps.title")}>
      <table className="result-table"><thead><tr><th rowSpan={2}>{t("doe.model.term")}</th>
        {steps.map((step) => <th key={step.step} colSpan={2} scope="colgroup">{stepLabel(step)}
          {step.removed_term_id ? <small className="doe-step-removed">{t("doe.steps.afterRemoval", { term: labels.get(step.removed_term_id) ?? step.removed_term_label ?? step.removed_term_id })}</small> : null}</th>)}
      </tr><tr>{steps.map((step) => <StepHead key={step.step} multiDf={multiDf} />)}</tr></thead><tbody>
        {terms.map((term) => <tr key={term.term_id}><th scope="row">{doeTermLabel(term)}</th>{steps.map((step) => {
          const statistic = step.term_statistics?.find((item) => item.term_id === term.term_id && item.status !== "removed_this_step");
          return <StepCells key={step.step} value={statistic} multiDf={multiDf} />;
        })}</tr>)}
        {metrics.map(([label, key]) => <tr key={key}><th scope="row">{label}</th>{steps.map((step) => <td key={step.step} colSpan={2}>{summary(step, key)}</td>)}</tr>)}
      </tbody></table>
    </div>
    <div className="doe-step-mobile">
      <label htmlFor={id}>{t("doe.steps.select")}</label><select id={id} value={Math.min(selected, steps.length - 1)} onChange={(event) => setSelected(Number(event.currentTarget.value))}>
        {steps.map((step, index) => <option key={step.step} value={index}>{stepLabel(step)}</option>)}
      </select>
      {chosen.removed_term_id ? <p>{t("doe.steps.afterRemoval", { term: labels.get(chosen.removed_term_id) ?? chosen.removed_term_id })}</p> : null}
      <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("doe.model.term")}</th><StepHead multiDf={multiDf} /></tr></thead>
        <tbody>{chosen.term_statistics?.filter((item) => item.status !== "removed_this_step").map((term) => <tr key={term.term_id}>
          <th scope="row">{labels.get(term.term_id) ?? term.label}</th><StepCells value={term} multiDf={multiDf} />
        </tr>)}</tbody></table></div>
      <dl className="result-definition-grid">{metrics.map(([label, key]) => <div key={key}><dt>{label}</dt><dd>{summary(chosen, key)}</dd></div>)}</dl>
    </div>
    {multiDf ? <details><summary>{t("doe.steps.levelCoefficients")}</summary>{steps.map((step) => <section key={step.step}><h5>{stepLabel(step)}</h5>
      {step.term_statistics?.filter((term) => term.status !== "removed_this_step").map((term) => <div key={term.term_id}><strong>{labels.get(term.term_id) ?? term.label}</strong>
        <ul>{term.coefficients.map((coefficient) => <li key={coefficient.column_index}>{coefficient.label ?? t("doe.steps.feature", { number: coefficient.column_index })}: {factorialNumber(coefficient.coefficient)}; P: {factorialNumber(coefficient.p_value ?? null)}</li>)}</ul>
      </div>)}
    </section>)}</details> : null}
    <p className="field-help">{t("doe.steps.cpPolicy")}</p>
  </section>;
}

function StepHead({ multiDf }: { multiDf: boolean }) { return <><th scope="col">{multiDf ? "DF" : "Coef"}</th><th scope="col">P</th></>; }
function stepNumber(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? "-" : value.toLocaleString(undefined, { maximumSignificantDigits: 7 });
}
function StepCells({ value, multiDf }: { value: NonNullable<DoeModelSelectionStep["term_statistics"]>[number] | undefined; multiDf: boolean }) {
  return <><td>{stepNumber(value ? multiDf ? value.df : value.coefficient : null)}</td>
    <td title={value?.status === "retained_for_hierarchy" ? t("doe.terms.hierarchyRetained") : undefined}>{value?.p_value != null && value.p_value < .001 ? "<0.001" : stepNumber(value?.p_value)}{value?.status === "forced" ? " *" : ""}</td></>;
}
