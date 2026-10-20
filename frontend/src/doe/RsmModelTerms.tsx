import { useEffect, useState } from "react";
import { fetchRsmTermCatalog } from "../api/factorialWorkflow";
import type { RsmTermPreset } from "../api/types/doe";
import type { DoeAnalysisTermCatalog, DoeModelSelectionOptions } from "../api/types/doeModelWorkflow";
import { t } from "../i18n/translate";
import { DoeTermSelection, type useDoeTermCatalog } from "./DoeTermSelection";

export const rsmPresets = ["linear", "linear_squares", "linear_interactions", "full_quadratic"] as const;

export function useRsmTermCatalog(
  designId: string | null, preset: RsmTermPreset, options: DoeModelSelectionOptions,
): ReturnType<typeof useDoeTermCatalog> & { retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const key = JSON.stringify([designId, preset, attempt]);
  const [loaded, setLoaded] = useState<{ key: string; catalog: DoeAnalysisTermCatalog | null } | null>(null);
  useEffect(() => {
    let current = true;
    if (designId) void fetchRsmTermCatalog(designId, preset)
      .then((catalog) => { if (current) setLoaded({ key, catalog }); })
      .catch(() => { if (current) setLoaded({ key, catalog: null }); });
    return () => { current = false; };
  }, [key, designId, preset]);
  const catalog = loaded?.key === key ? loaded.catalog : null;
  const terms = catalog?.terms ?? [];
  const configured = new Map(options.term_policies?.map((policy) => [policy.term_id, policy.disposition]));
  return {
    retry: () => setAttempt((value) => value + 1),
    terms, error: loaded?.key === key && loaded.catalog === null,
    ready: Boolean(catalog), catalogReady: Boolean(catalog),
    preflightError: null, estimability: null,
    options: { ...options, term_policies: terms.map((term) => ({
      term_id: term.term_id,
      disposition: term.hierarchy_role === "structural_term" ? "forced"
        : configured.get(term.term_id) ?? term.default_disposition,
    })) },
  };
}

export function RsmModelTerms({ preset, onPresetChange, state, options, onOptionsChange }: {
  preset: RsmTermPreset; onPresetChange: (preset: RsmTermPreset) => void;
  state: ReturnType<typeof useRsmTermCatalog>; options: DoeModelSelectionOptions;
  onOptionsChange: (options: DoeModelSelectionOptions) => void;
}) {
  const parameterCount = state.options.term_policies.filter((policy) => policy.disposition !== "excluded").length;
  return <section className="result-section">
    <label>{t("doe.rsm.preset")}<select value={preset}
      onChange={(event) => onPresetChange(event.currentTarget.value as RsmTermPreset)}>
      {rsmPresets.map((value) => <option key={value} value={value}>{t(`doe.rsm.preset.${value}`)}</option>)}
    </select></label>
    <p className="field-help">{t("doe.rsm.parameterCount")}: {state.catalogReady ? parameterCount : "-"}</p>
    {state.error ? <button type="button" className="secondary-button" onClick={state.retry}>{t("doe.rsm.retryTerms")}</button> : null}
    <DoeTermSelection state={state} value={options} onChange={onOptionsChange} autoIncludeParents={false} />
  </section>;
}
