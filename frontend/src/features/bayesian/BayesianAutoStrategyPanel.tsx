import { useEffect, useRef, useState } from "react";
import { Check, Download, ListChecks } from "lucide-react";
import { requestAutoStrategy, validAutoStrategy, verifyAutoStrategySource, type AutoStrategySource, type AutoStrategyView } from "../../api/boAutoStrategy";
import { triggerBrowserDownload } from "../../api/client";
import type { AugmentationPolicy } from "../../api/types/boAugmentation";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { useI18n } from "../../i18n/LocaleProvider";
import { autoStrategyMessages } from "../../i18n/boAutoStrategy";
import { augmentationPolicyLabel } from "../../i18n/boAugmentation";
import { createLatestRequestGuard } from "../../latestRequest";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";

interface Props {
  studyId: string; model: AutoStrategySource; contextKey: string; kinds: readonly string[];
  mixed?: boolean; disabled: boolean; onApply: (policy: AugmentationPolicy, view: AutoStrategyView) => void;
  onAdviceEdit?: () => void;
}
export function BayesianAutoStrategyPanel(props: Props) {
  const sourceKey = `${props.contextKey}:${props.studyId}:${props.mixed === true}:${props.model.model_id}:${props.model.snapshot_sha256}:${props.model.config_sha256}:${props.model.history_sha256}`;
  return <AutoSourceDraft key={sourceKey} {...props} />;
}

function AutoSourceDraft(props: Props) {
  const [threshold, setThreshold] = useState("0.25");
  // A competing operation cancels request ownership without erasing the draft.
  return <AutoSourcePanel key={String(props.disabled)} {...props} threshold={threshold} onThresholdChange={setThreshold} />;
}

function AutoSourcePanel({ studyId, model, kinds, mixed = false, disabled, onApply, onAdviceEdit, threshold, onThresholdChange }: Props & { threshold: string; onThresholdChange: (value: string) => void }) {
  const { locale } = useI18n(), text = autoStrategyMessages(locale);
  const [view, setView] = useState<AutoStrategyView | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState(false);
  const guard = useRef(createLatestRequestGuard()), controller = useRef<AbortController | null>(null);
  useEffect(() => { const lane = guard.current; return () => { lane.cancel(); controller.current?.abort(); }; }, []);
  const number = parseDoeResponseNumber(threshold), valid = number !== null && number >= 0 && number <= 1;
  function edit(value: string) {
    onAdviceEdit?.();
    guard.current.cancel(); controller.current?.abort(); setBusy(false); setView(null); setError(false); onThresholdChange(value);
  }
  async function run(apply: boolean) {
    if (!valid || disabled || (apply && (!view?.apply_allowed || !model.source_is_current))) return;
    const token = guard.current.begin(); controller.current?.abort(); controller.current = new AbortController();
    setError(false); setBusy(true);
    try {
      if (apply) {
        const current = await verifyAutoStrategySource(studyId, model, mixed, controller.current.signal);
        if (!guard.current.isCurrent(token)) return;
        if (!current) { setView(null); throw new Error("stale_auto_source"); }
        if (view?.decision.recommended_policy) onApply(view.decision.recommended_policy, view);
      } else {
        onAdviceEdit?.();
        setView(null);
        const result = await requestAutoStrategy(studyId, model, mixed, number, controller.current.signal);
        if (!guard.current.isCurrent(token)) return;
        if (!validAutoStrategy(result, studyId, model, kinds, number)) throw new Error("invalid_auto_receipt");
        setView(result);
      }
    } catch {
      if (guard.current.isCurrent(token)) setError(true);
    } finally {
      if (guard.current.isCurrent(token)) setBusy(false);
    }
  }
  return <section className="bo-auto-strategy" aria-label={text.title}>
    <h4>{text.title}</h4><p>{text.meaning}</p><p>{text.conditional}</p>
    {kinds.some(kind => kind !== "continuous") && <p>{text.mixed}</p>}
    <label>{text.threshold}<input aria-label={text.threshold} inputMode="decimal" value={threshold} disabled={disabled} onChange={event => edit(event.currentTarget.value)} /></label>
    {!valid && <p role="alert">{text.invalid}</p>}
    <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={disabled || busy || !valid} onClick={() => void run(false)}><ListChecks size={16} aria-hidden="true" />{text.run}</button>
      {busy && <span role="status">{text.busy}</span>}</div>
    {error && <p role="alert">{text.error}</p>}
    {view && <><p>{view.decision.reason === "r_squared_unavailable" ? text.unavailable : view.decision.reason === "any_response_below_threshold" ? text.below : text.all}</p>
      <div className="table-wrap"><table className="result-table"><thead><tr><th>{text.response}</th><th>{text.r2}</th></tr></thead><tbody>{view.diagnostic.calculation.responses.map(row => <tr key={row.response_id}>
        <th scope="row">{model.objective.responses.find(item => item.response_id === row.response_id)?.name ?? row.response_id}</th><td>{row.r_squared === null ? text.scoreUnavailable : exact(row.r_squared)}</td>
      </tr>)}</tbody></table></div>
      {view.decision.recommended_policy && <p>{text.proposed}: <strong>{augmentationPolicyLabel(view.decision.recommended_policy, locale)}</strong></p>}
      {(!view.apply_allowed || !model.source_is_current) && <p>{text.stale}</p>}
      <p>{text.snapshot}</p>
      <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={disabled || busy || !view.apply_allowed || !model.source_is_current} onClick={() => void run(true)}><Check size={16} aria-hidden="true" />{text.apply}</button>
        <button type="button" className="secondary-button" onClick={() => triggerBrowserDownload(new Blob([JSON.stringify(view, null, 2)], { type: "application/json" }), `bo-auto-${model.model_id}.json`)}><Download size={16} aria-hidden="true" />{text.download}</button></div>
      <details><summary>{text.source}</summary><dl className="bo-planning-source"><div><dt>model_sha256</dt><dd>{view.diagnostic.model_sha256}</dd></div><div><dt>history_sha256</dt><dd>{view.diagnostic.history_sha256}</dd></div><div><dt>decision_sha256</dt><dd>{view.decision_sha256}</dd></div></dl></details>
    </>}
  </section>;
}
