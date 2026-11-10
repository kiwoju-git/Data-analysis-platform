import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { fetchMixedBatch } from "../../api/boMixed";
import type { MixedBatchResponse, MixedStudyResponse } from "../../api/types/boMixed";
import { useI18n } from "../../i18n/LocaleProvider";
import { mixedMessages } from "../../i18n/boMixed";
import { planningMessages } from "../../i18n/boPlanning";
import { PlanningSavedBatchReport } from "./BayesianPlanningSavedBatch";
import { MixedFitReceipt, MixedSelectionDetails } from "./BayesianMixedPlanningPanel";
import { createPlanningRequestFence } from "./boPlanningDraft";
import { augmentationFailureCode } from "./boAugmentationDraft";
import { validMixedBatch } from "./boMixedPlanningDraft";

export function BayesianMixedSavedBatch({ study, batchId }: { study: MixedStudyResponse; batchId: string }) {
  const { locale } = useI18n(), text = mixedMessages(locale), common = planningMessages(locale), [refresh, setRefresh] = useState(0);
  const key = `${study.study_id}:${study.study_version_id}:${study.definition_sha256}:${batchId}:${refresh}`;
  const fence = useRef(createPlanningRequestFence()).current; fence.source(key);
  const [state, setState] = useState<{ key: string; batch: MixedBatchResponse | null; error: string | null; busy: boolean }>({ key: "", batch: null, error: null, busy: false });
  const source = useRef(study); source.current = study;
  useEffect(() => {
    const token = fence.begin(), saved = source.current;
    setState({ key, batch: null, error: null, busy: true });
    void fetchMixedBatch(saved.study_id, batchId).then(batch => {
      if (!fence.current(token)) return;
      if (!validMixedBatch(batch, saved, batchId)) throw new Error("bayesian_mixed_response_mismatch");
      setState({ key, batch, error: null, busy: false });
    }).catch(caught => { if (fence.current(token)) setState({ key, batch: null, error: augmentationFailureCode(caught), busy: false }); });
    return () => fence.invalidate();
  }, [key, batchId, fence]);
  const current = state.key === key ? state : { key, batch: null, error: null, busy: true }, batch = current.batch;
  const states = { pending: common.batchPending, partially_completed: common.batchPartial, completed: common.batchCompleted, abandoned: common.batchAbandoned, closed_mixed: common.batchMixed };
  return <section className="bo-planning" aria-label={text.savedBatch}><h3>{text.savedBatch}</h3><p>{common.exactBatch}</p>
    <button type="button" className="secondary-button" disabled={current.busy} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={16} aria-hidden="true" />{common.reloadBatch}</button>
    {current.busy && <p role="status">{common.busy}</p>}{current.error && <div role="alert" className="notice-box notice-warning"><p>{common.savedSourceError}</p><code>{current.error}</code></div>}
    {batch && <><dl className="bo-planning-source"><div><dt>{common.confirmed}</dt><dd>{batch.batch_id}</dd></div><div><dt>{common.batchState}</dt><dd>{states[batch.batch_state]}</dd></div><div><dt>{common.history}</dt><dd>{batch.source_observation_history_sha256}</dd></div><div><dt>{common.modelHash}</dt><dd>{batch.source.model_sha256 ?? "-"}</dd></div><div><dt>{common.rowsHash}</dt><dd>{batch.source.rows_sha256}</dd></div><div><dt>{common.batchHash}</dt><dd>{batch.result_sha256}</dd></div></dl>
      <MixedSelectionDetails selection={{ selection_id: batch.source.selection_id, result_sha256: batch.source.selection_result_sha256, calculation: batch.calculation, request: batch.selection_request }} study={study} />
      <div className="table-wrap"><table className="result-table"><thead><tr><th>{common.rank}</th><th>{common.trial}</th><th>{common.trialState}</th></tr></thead><tbody>{batch.items.map(item => <tr key={item.item_id}><th scope="row">{item.rank}</th><td>{item.trial.trial_id}</td><td>{states[item.current_trial.state]}</td></tr>)}</tbody></table></div>
      {batch.response_models && batch.source.model_id && batch.source.model_sha256 && <MixedFitReceipt model={{ model_id: batch.source.model_id, snapshot_sha256: batch.source.model_sha256, source_is_current: batch.source_observation_history_sha256 === study.observation_history.observation_history_sha256, response_models: batch.response_models, warnings: batch.warnings }} study={study} />}
      <PlanningSavedBatchReport batch={batch} />
    </>}
  </section>;
}
