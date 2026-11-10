import { useEffect, useRef, useState } from "react";
import { Download, FileText, RefreshCw } from "lucide-react";
import { fetchPlanningBatchReportSource } from "../../api/boPlanning";
import { fetchAugmentationReportSource } from "../../api/boAugmentation";
import { fetchMixedBatchReportSource } from "../../api/boMixed";
import type { MixedBatchResponse } from "../../api/types/boMixed";
import type { AugmentationBatchResponse } from "../../api/types/boAugmentation";
import { triggerBrowserDownload } from "../../api/client";
import { createManagedReport, fetchManagedReportDownload, fetchStoredReportCapability } from "../../api/reports";
import type { BayesianStudyResponse } from "../../api/types/bayesian";
import type { PlanningBatchResponse } from "../../api/types/boPlanning";
import type { ManagedReportDescriptor } from "../../api/types/reports";
import { useI18n } from "../../i18n/LocaleProvider";
import { planningMessages } from "../../i18n/boPlanning";
import { augmentationMessages } from "../../i18n/boAugmentation";
import { isManagedReport, isStoredReportCapability, reportSourceKey } from "../../managedReportSource";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { createPlanningRequestFence, validPlanningBatchReportSource } from "./boPlanningDraft";
import { validAugmentationReportSource } from "./boAugmentationDraft";
import { validMixedReportSource } from "./boMixedPlanningDraft";
import { usePlanningSavedBatch } from "./hooks/usePlanningSavedBatch";
import { PlanningFitSummary } from "./BayesianPlanningPanel";

export function BayesianPlanningSavedBatch({ study, batchId }: { study: BayesianStudyResponse; batchId: string }) {
  const state = usePlanningSavedBatch(study, batchId), { locale } = useI18n(), text = planningMessages(locale);
  return <section className="bo-planning" aria-label={text.savedBatch}>
    <h3>{text.savedBatch}</h3><p>{text.exactBatch}</p>
    <button type="button" className="secondary-button" disabled={state.loading} onClick={state.refresh}><RefreshCw size={16} aria-hidden="true" />{text.reloadBatch}</button>
    {state.loading && <p role="status">{text.busy}</p>}
    {state.error && <div className="notice-box notice-warning" role="alert"><p>{text.savedSourceError}</p><code>{state.error}</code></div>}
    {state.batch && <><PlanningSavedBatchDetails batch={state.batch} study={study} /><PlanningSavedBatchReport batch={state.batch} /></>}
  </section>;
}

export function PlanningSavedBatchDetails({ batch, study }: { batch: PlanningBatchResponse; study: BayesianStudyResponse }) {
  const { locale } = useI18n(), text = planningMessages(locale);
  const states = { pending: text.batchPending, partially_completed: text.batchPartial, completed: text.batchCompleted, abandoned: text.batchAbandoned, closed_mixed: text.batchMixed };
  return <>
    <dl className="bo-planning-source"><div><dt>{text.confirmed}</dt><dd>{batch.batch_id}</dd></div><div><dt>{text.batchState}</dt><dd>{states[batch.batch_state]}</dd></div>
      <div><dt>{text.model}</dt><dd>{batch.source.model_id}</dd></div><div><dt>{text.modelHash}</dt><dd>{batch.source.model_sha256}</dd></div>
      <div><dt>{text.history}</dt><dd>{batch.source_observation_history_sha256}</dd></div><div><dt>{text.rowsHash}</dt><dd>{batch.source.rows_sha256}</dd></div>
      <div><dt>{text.batchHash}</dt><dd>{batch.result_sha256}</dd></div><div><dt>{text.selectionHash}</dt><dd>{batch.source.selection_result_sha256}</dd></div>
    </dl>
    <p>{batch.source_history_revision_id === study.observation_history.history_revision_id && batch.source_observation_history_sha256 === study.observation_history.observation_history_sha256 ? text.current : text.historical}</p>
    <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.reviewed}</caption><thead><tr><th>{text.rank}</th>{study.factors.map(factor => <th key={factor.factor_id}>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</th>)}<th>{text.expected}</th><th>{text.sd}</th><th>{text.ei}</th><th>{text.marginal}</th><th>{text.trialState}</th></tr></thead>
      <tbody>{batch.calculation.items.map((row, index) => <tr key={row.row_id}><th scope="row">{row.rank}</th>{study.factors.map(factor => <td key={factor.factor_id}>{exact(row.actual_coordinates[factor.factor_id])}</td>)}<td>{exact(row.desirability_moments.mean)}</td><td>{exact(Math.sqrt(row.desirability_moments.variance))}</td><td>{exact(row.acquisition.value)}</td><td>{exact(row.planning.score)}</td><td>{states[batch.items[index].current_trial.state]}</td></tr>)}</tbody>
    </table></div>
    <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.evaluated}</caption><thead><tr><th>{text.rank}</th><th>{text.response}</th><th>{text.mean}</th><th>{text.latent}</th><th>{text.predictive}</th></tr></thead>
      <tbody>{batch.calculation.items.flatMap(row => row.response_predictions.map(prediction => { const response = batch.objective.responses.find(item => item.response_id === prediction.response_id); return <tr key={`${row.row_id}:${prediction.response_id}`}><td>{row.rank}</td><th scope="row">{response?.name ?? prediction.response_id}{response?.unit ? ` (${response.unit})` : ""}</th><td>{exact(prediction.mean_raw)}</td><td>{exact(prediction.latent_standard_deviation_raw)}</td><td>{exact(prediction.predictive_standard_deviation_raw)}</td></tr>; }))}</tbody>
    </table></div>
    <PlanningFitSummary model={{ model_id: batch.source.model_id, snapshot_sha256: batch.source.model_sha256, objective: batch.objective, response_models: batch.response_models, warnings: batch.warnings }} />
  </>;
}

export function PlanningSavedBatchReport({ batch }: { batch: PlanningBatchResponse | AugmentationBatchResponse | MixedBatchResponse }) {
  const { locale } = useI18n(), text = planningMessages(locale);
  const key = `${batch.study_id}:${batch.batch_id}:${batch.result_sha256}:${locale}`;
  const guard = useRef(createPlanningRequestFence()).current; guard.source(key);
  const [state, setState] = useState<{ key: string; busy: boolean; error: string | null; report: ManagedReportDescriptor | null }>({ key: "", busy: false, error: null, report: null });
  const current = state.key === key ? state : { key, busy: false, error: null, report: null };
  const running = useRef(false);
  useEffect(() => { running.current = false; return () => { guard.invalidate(); running.current = false; }; }, [key, guard]);
  async function create() {
    if (running.current) return;
    running.current = true; const token = guard.begin();
    setState({ key, busy: true, error: null, report: null });
    try {
      const descriptor = await (batch.batch_policy === "source_owned_mixed_planning_v1" ? fetchMixedBatchReportSource : batch.result_schema_version === 9 || batch.result_schema_version === 11 ? fetchAugmentationReportSource : fetchPlanningBatchReportSource)(batch.study_id, batch.batch_id);
      if (!guard.current(token)) return;
      if (!(batch.batch_policy === "source_owned_mixed_planning_v1" ? validMixedReportSource(descriptor, batch) : batch.batch_policy === "source_owned_augmentation_v1" ? validAugmentationReportSource(descriptor, batch) : validPlanningBatchReportSource(descriptor, batch))) throw new Error("bayesian_planning_report_source_mismatch");
      const capability = await fetchStoredReportCapability(descriptor.source, locale);
      if (!guard.current(token)) return;
      if (!isStoredReportCapability(capability) || capability.source_ref_sha256 !== descriptor.source_ref_sha256 || reportSourceKey(capability.source) !== reportSourceKey(descriptor.source) || capability.locale !== locale) throw new Error("bayesian_planning_report_source_mismatch");
      if (!capability.html_available || capability.report_level === "unsupported") throw new Error("bayesian_planning_report_unavailable");
      const report = await createManagedReport(descriptor.source, locale, descriptor.source_ref_sha256);
      if (!guard.current(token)) return;
      if (!isManagedReport(report) || report.source_ref_sha256 !== descriptor.source_ref_sha256 || reportSourceKey(report.source) !== reportSourceKey(descriptor.source) || report.locale !== locale) throw new Error("bayesian_planning_report_source_mismatch");
      setState({ key, busy: false, error: null, report });
    } catch (caught) {
      if (guard.current(token)) setState({ key, busy: false, report: null, error: caught instanceof Error && /^[a-z][a-z0-9_]+$/.test(caught.message) ? caught.message : "managed_report_request_failed" });
    } finally { if (guard.current(token)) running.current = false; }
  }
  async function download() {
    if (!current.report || running.current) return;
    running.current = true; const token = guard.begin(), report = current.report;
    setState({ ...current, busy: true, error: null });
    try {
      const file = await fetchManagedReportDownload(report);
      if (guard.current(token)) { triggerBrowserDownload(file.blob, file.filename); setState({ key, busy: false, error: null, report }); }
    } catch (caught) {
      if (guard.current(token)) setState({ key, busy: false, report, error: caught instanceof Error && /^[a-z][a-z0-9_]+$/.test(caught.message) ? caught.message : "managed_report_download_failed" });
    } finally { if (guard.current(token)) running.current = false; }
  }
  return <section aria-label={text.createReport}><p>{batch.result_schema_version === 9 || batch.result_schema_version === 11 ? augmentationMessages(locale).reportMeaning : text.reportMeaning}</p><div className="bo-planning-actions">
    <button type="button" className="secondary-button" disabled={current.busy} onClick={() => void create()}><FileText size={16} aria-hidden="true" />{text.createReport}</button>
    {current.report && <><button type="button" className="secondary-button" disabled={current.busy} onClick={() => void download()}><Download size={16} aria-hidden="true" />{text.downloadReport}</button><a href={`/reports?source_kind=bayesian_history_revision&report_id=${encodeURIComponent(current.report.export_id)}`}>{text.openReport}</a></>}
    </div>{current.busy && <p role="status">{text.busy}</p>}{current.error && <div role="alert" className="notice-box notice-warning"><p>{current.error === "bayesian_planning_report_unavailable" ? text.reportUnavailable : text.error}</p><code>{current.error}</code></div>}
  </section>;
}
