import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { fetchAugmentationBatch } from "../../api/boAugmentation";
import type { BayesianStudyResponse } from "../../api/types/bayesian";
import type { AugmentationBatchResponse } from "../../api/types/boAugmentation";
import { useI18n } from "../../i18n/LocaleProvider";
import { augmentationMessages } from "../../i18n/boAugmentation";
import { planningMessages } from "../../i18n/boPlanning";
import { createPlanningRequestFence, planningStudyKey } from "./boPlanningDraft";
import { augmentationFailureCode, validAugmentationBatch } from "./boAugmentationDraft";
import { AugmentationTraceTable } from "./BayesianAugmentationPanel";
import { PlanningFitSummary } from "./BayesianPlanningPanel";
import { PlanningSavedBatchReport } from "./BayesianPlanningSavedBatch";

export function BayesianAugmentationSavedBatch({ study, batchId }: { study: BayesianStudyResponse; batchId: string }) {
  const { locale } = useI18n(), text = augmentationMessages(locale), common = planningMessages(locale);
  const key = `${planningStudyKey(study)}:${batchId}`, guard = useRef(createPlanningRequestFence()).current; guard.source(key);
  const [state, setState] = useState<{ key: string; batch: AugmentationBatchResponse | null; loading: boolean; error: string | null }>({ key: "", batch: null, loading: false, error: null });
  async function refresh() {
    const token = guard.begin(); setState({ key, batch: null, loading: true, error: null });
    try {
      const batch = await fetchAugmentationBatch(study.study_id, batchId);
      if (!guard.current(token)) return;
      if (!validAugmentationBatch(batch, study, batchId)) throw new Error("bayesian_augmentation_saved_source_mismatch");
      setState({ key, batch, loading: false, error: null });
    } catch (caught) { if (guard.current(token)) setState({ key, batch: null, loading: false, error: augmentationFailureCode(caught) }); }
  }
  const latest = useRef(refresh); latest.current = refresh;
  useEffect(() => { void latest.current(); return () => guard.invalidate(); }, [key, guard]);
  const current = state.key === key ? state : { key, batch: null, loading: true, error: null }, batch = current.batch;
  const states = { pending: common.batchPending, partially_completed: common.batchPartial, completed: common.batchCompleted, abandoned: common.batchAbandoned, closed_mixed: common.batchMixed };
  return <section className="bo-planning" aria-label={text.savedBatch}><h3>{text.savedBatch}</h3><p>{text.exactBatch}</p>
    <button type="button" className="secondary-button" disabled={current.loading} onClick={() => void refresh()}><RefreshCw size={16} aria-hidden="true" />{common.reloadBatch}</button>
    {current.loading && <p role="status">{common.busy}</p>}{current.error && <div role="alert" className="notice-box notice-warning"><p>{common.savedSourceError}</p><code>{current.error}</code></div>}
    {batch && <><dl className="bo-planning-source"><div><dt>{common.confirmed}</dt><dd>{batch.batch_id}</dd></div><div><dt>{common.batchState}</dt><dd>{states[batch.batch_state]}</dd></div>
      <div><dt>{common.batchHash}</dt><dd>{batch.result_sha256}</dd></div><div><dt>{common.rowsHash}</dt><dd>{batch.source.rows_sha256}</dd></div><div><dt>{common.history}</dt><dd>{batch.source_observation_history_sha256}</dd></div><div><dt>{common.modelHash}</dt><dd>{batch.source.model_sha256 ?? text.noModel}</dd></div></dl>
      <AugmentationTraceTable calculation={batch.calculation} study={study} />
      <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{common.trialState}</caption><thead><tr><th>{common.rank}</th><th>{common.trial}</th><th>{common.trialState}</th></tr></thead><tbody>{batch.items.map(item => <tr key={item.item_id}><th scope="row">{item.rank}</th><td>{item.current_trial.trial_id}</td><td>{states[item.current_trial.state]}</td></tr>)}</tbody></table></div>
      {batch.model && <PlanningFitSummary model={batch.model} />}<PlanningSavedBatchReport batch={batch} /></>}
  </section>;
}
