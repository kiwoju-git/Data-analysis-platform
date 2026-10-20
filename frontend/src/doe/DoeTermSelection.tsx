import { useEffect, useId, useState } from "react";
import { fetchDoeTermCatalog, preflightDoeTerms } from "../api/factorialWorkflow";
import type { DoeAnalysisTerm, DoeAnalysisTermCatalog, DoeModelSelectionOptions, DoeTermDisposition } from "../api/types/doeModelWorkflow";
import { t } from "../i18n/translate";

export function useDoeTermCatalog(designId: string | null, order: number, options: DoeModelSelectionOptions, enabled = true, fractional = false) {
  const [catalog, setCatalog] = useState<DoeAnalysisTermCatalog | null>(null);
  const [error, setError] = useState(false);
  const [preflight, setPreflight] = useState<{ key: string; catalog: DoeAnalysisTermCatalog | null; error: string | null } | null>(null);
  const matching = catalog?.design_id === designId && catalog.max_interaction_order === order;
  const selected = new Map(options.term_policies?.map((policy) => [policy.term_id, policy.disposition]));
  const termPolicies = (matching ? catalog.terms : []).map((term) => ({ term_id: term.term_id,
    disposition: term.hierarchy_role === "structural_term" ? "forced" as const : selected.get(term.term_id) ?? term.default_disposition }));
  const optionsJson = JSON.stringify({ ...options, term_policies: termPolicies });
  const preflightKey = JSON.stringify([designId, order, optionsJson]);
  useEffect(() => {
    let current = true;
    setCatalog(null); setError(false);
    if (designId && enabled) void fetchDoeTermCatalog(designId, order)
      .then((value) => { if (current) setCatalog(value); })
      .catch(() => { if (current) setError(true); });
    return () => { current = false; };
  }, [designId, order, enabled]);
  useEffect(() => {
    let current = true;
    if (designId && enabled && fractional && matching) {
      void preflightDoeTerms(designId, order, JSON.parse(optionsJson) as DoeModelSelectionOptions)
        .then((value) => { if (current) setPreflight({ key: preflightKey, catalog: value, error: null }); })
        .catch((caught: unknown) => {
          if (current) setPreflight({ key: preflightKey, catalog: null, error: caught instanceof Error ? caught.message : "doe_fractional_preflight_failed" });
        });
    }
    return () => { current = false; };
  }, [designId, order, optionsJson, preflightKey, enabled, fractional, matching]);
  const matchedPreflight = fractional && preflight?.key === preflightKey ? preflight : null;
  const terms = matching ? (matchedPreflight?.catalog?.terms ?? catalog.terms) : [];
  return {
    terms, error, catalogReady: Boolean(matching),
    preflightError: matchedPreflight?.error ?? null,
    estimability: matchedPreflight?.catalog?.estimability ?? null,
    ready: !enabled || Boolean(matching && (!fractional || matchedPreflight?.catalog)),
    options: { ...options, term_policies: termPolicies },
  };
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
  return <fieldset className="doe-term-selection" disabled={disabled || !state.catalogReady} aria-describedby={`${id}-help`}>
    <legend>{t("doe.terms.title")}</legend>
    <p id={`${id}-help`} className="field-help">{t("doe.terms.policy")}</p>
    {state.preflightError ? <p role="alert" className="error-box">{t("doe.fraction.preflightError")} <code>{state.preflightError}</code></p> : null}
    {state.estimability ? <div className="metadata-grid" aria-label={t("doe.fraction.estimability")}>
      <span>{t("doe.fraction.requestedParameters")}</span><strong>{state.estimability.requested_parameter_count}</strong>
      <span>{t("doe.fraction.rank")}</span><strong>{state.estimability.rank}</strong>
      <span>{t("doe.fraction.residualDf")}</span><strong>{state.estimability.expected_residual_df}</strong>
      <span>{t("doe.fraction.aliasExcluded")}</span><strong>{state.estimability.exclusions.length}</strong>
    </div> : null}
    {state.error ? <p role="alert" className="error-box">{t("doe.terms.loadFailed")}</p> : !state.catalogReady ? <p role="status">{t("doe.terms.loading")}</p> : <>
      <div className="button-row"><button type="button" className="secondary-button" onClick={() => bulk(false)}>{t("doe.terms.reset")}</button>
        <button type="button" className="secondary-button" onClick={() => update(new Map(state.terms.map((term) => [term.term_id, dispositions.get(term.term_id) === "forced" ? "forced" : "candidate"])))}>{t("doe.terms.selectAll")}</button>
        <button type="button" className="secondary-button" onClick={() => bulk(true)}>{t("doe.terms.clearInteractions")}</button></div>
      {notice ? <p role="status" className="field-help">{notice}</p> : null}
      <div className="table-wrap"><table className="result-table"><thead><tr>
        <th>{t("doe.model.term")}</th><th>DF</th><th>{t("doe.model.status")}</th><th>{t("doe.terms.constraint")}</th>
      </tr></thead><tbody>{state.terms.map((term) => {
        const structural = term.hierarchy_role === "structural_term";
        const dependent = state.terms.find((other) => dispositions.get(other.term_id) !== "excluded" && other.hierarchy_dependencies.includes(term.term_id));
        const exclusion = state.estimability?.exclusions.find((item) => item.term_id === term.term_id);
        const help = exclusion
          ? `${t("doe.fraction.aliasExcluded")}: ${exclusion.reason}${exclusion.representative_term_id ? ` (${exclusion.representative_term_id})` : ""}`
          : dependent ? t("doe.terms.parentRequired", { term: doeTermLabel(dependent) }) : term.kind === "curvature" ? t("doe.terms.centerPolicy") : "";
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
