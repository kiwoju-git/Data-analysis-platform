import { useEffect, useId, useState } from "react";
import { fetchDoeTermCatalog } from "../api/factorialWorkflow";
import type { DoeAnalysisTerm, DoeAnalysisTermCatalog, DoeModelSelectionOptions, DoeTermDisposition } from "../api/types/doeModelWorkflow";
import { t } from "../i18n/translate";

export function useDoeTermCatalog(designId: string | null, order: number, options: DoeModelSelectionOptions, enabled = true) {
  const [catalog, setCatalog] = useState<DoeAnalysisTermCatalog | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let current = true;
    setCatalog(null); setError(false);
    if (designId && enabled) void fetchDoeTermCatalog(designId, order)
      .then((value) => { if (current) setCatalog(value); })
      .catch(() => { if (current) setError(true); });
    return () => { current = false; };
  }, [designId, order, enabled]);
  const matching = catalog?.design_id === designId && catalog.max_interaction_order === order;
  const terms = matching ? catalog.terms : [];
  const selected = new Map(options.term_policies?.map((policy) => [policy.term_id, policy.disposition]));
  const termPolicies = terms.map((term) => ({ term_id: term.term_id,
    disposition: term.hierarchy_role === "structural_term" ? "forced" as const : selected.get(term.term_id) ?? term.default_disposition }));
  return { terms, error, ready: !enabled || Boolean(matching), options: { ...options, term_policies: termPolicies } };
}

export function doeTermLabel(term: Pick<DoeAnalysisTerm, "label" | "kind">): string {
  return term.kind === "curvature" ? t("doe.terms.center") : term.kind === "intercept" ? t("doe.terms.intercept") : term.label;
}

export function DoeTermSelection({ state, value, onChange, disabled = false }: {
  state: ReturnType<typeof useDoeTermCatalog>; value: DoeModelSelectionOptions;
  onChange: (options: DoeModelSelectionOptions) => void; disabled?: boolean;
}) {
  const id = useId();
  const [notice, setNotice] = useState<string | null>(null);
  const dispositions = new Map(state.options.term_policies.map((policy) => [policy.term_id, policy.disposition]));
  function update(changes: Map<string, DoeTermDisposition>) {
    const draft = new Map(value.term_policies?.map((policy) => [policy.term_id, policy.disposition]));
    changes.forEach((disposition, termId) => draft.set(termId, disposition));
    onChange({ ...value, term_policies: [...draft].map(([term_id, disposition]) => ({ term_id, disposition })) });
  }
  function change(term: DoeAnalysisTerm, disposition: DoeTermDisposition) {
    const changes = new Map<string, DoeTermDisposition>([[term.term_id, disposition]]);
    const parents = disposition === "excluded" ? [] : term.hierarchy_dependencies.filter((parent) => dispositions.get(parent) === "excluded");
    parents.forEach((parent) => changes.set(parent, "candidate"));
    setNotice(parents.length ? t("doe.terms.parentsIncluded") : null);
    update(changes);
  }
  function bulk(interactionsOnly: boolean) {
    setNotice(null);
    update(new Map(state.terms.filter((term) => term.hierarchy_role !== "structural_term" && (!interactionsOnly || term.kind === "interaction"))
      .map((term) => [term.term_id, interactionsOnly ? "excluded" : "candidate"])));
  }
  return <fieldset className="doe-term-selection" disabled={disabled || !state.ready} aria-describedby={`${id}-help`}>
    <legend>{t("doe.terms.title")}</legend>
    <p id={`${id}-help`} className="field-help">{t("doe.terms.policy")}</p>
    {state.error ? <p role="alert" className="error-box">{t("doe.terms.loadFailed")}</p> : !state.ready ? <p role="status">{t("doe.terms.loading")}</p> : <>
      <div className="button-row"><button type="button" className="secondary-button" onClick={() => bulk(false)}>{t("doe.terms.reset")}</button>
        <button type="button" className="secondary-button" onClick={() => update(new Map(state.terms.map((term) => [term.term_id, dispositions.get(term.term_id) === "forced" ? "forced" : "candidate"])))}>{t("doe.terms.selectAll")}</button>
        <button type="button" className="secondary-button" onClick={() => bulk(true)}>{t("doe.terms.clearInteractions")}</button></div>
      {notice ? <p role="status" className="field-help">{notice}</p> : null}
      <div className="table-wrap"><table className="result-table"><thead><tr>
        <th>{t("doe.model.term")}</th><th>DF</th><th>{t("doe.model.status")}</th><th>{t("doe.terms.constraint")}</th>
      </tr></thead><tbody>{state.terms.map((term) => {
        const structural = term.hierarchy_role === "structural_term";
        const dependent = state.terms.find((other) => dispositions.get(other.term_id) !== "excluded" && other.hierarchy_dependencies.includes(term.term_id));
        const help = dependent ? t("doe.terms.parentRequired", { term: doeTermLabel(dependent) }) : term.kind === "curvature" ? t("doe.terms.centerPolicy") : "";
        const helpId = `${id}-${term.term_id}`;
        return <tr key={term.term_id}><th scope="row">{doeTermLabel(term)}</th><td>{term.df}</td><td>
          <select aria-label={doeTermLabel(term)} aria-describedby={helpId} value={dispositions.get(term.term_id)} disabled={structural}
            onChange={(event) => change(term, event.currentTarget.value as DoeTermDisposition)}>
            <option value="candidate">{t(value.method === "none" ? "doe.terms.included" : "doe.terms.candidate")}</option>
            {value.method !== "none" || dispositions.get(term.term_id) === "forced" ? <option value="forced">{t("doe.terms.forced")}</option> : null}
            <option value="excluded" disabled={Boolean(dependent)}>{t("doe.terms.excluded")}</option>
          </select></td><td id={helpId} className="field-help">{structural ? t("doe.model.structural") : help}</td></tr>;
      })}</tbody></table></div>
    </>}
  </fieldset>;
}
