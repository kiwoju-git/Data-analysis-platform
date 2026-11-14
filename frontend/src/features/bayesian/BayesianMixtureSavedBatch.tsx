import { useEffect, useRef, useState } from "react";
import { Download, FileText, RefreshCw } from "lucide-react";
import { fetchMixtureBatch, fetchMixtureBatchReportSource, fetchMixtureModel, type MixtureBatch, type MixtureStudy } from "../../api/boMixture";
import { createManagedReport, fetchManagedReportDownload, fetchStoredReportCapability } from "../../api/reports";
import { triggerBrowserDownload } from "../../api/client";
import type { ManagedReportDescriptor } from "../../api/types/reports";
import { isManagedReport, isReportSourceDescriptor, isStoredReportCapability, reportSourceKey } from "../../managedReportSource";
import { useI18n } from "../../i18n/LocaleProvider";
import { mixtureMessages } from "../../i18n/boMixture";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { createPlanningRequestFence } from "./boPlanningDraft";
import { validMixtureCoordinates, validMixtureModel, validMixtureSelection } from "./boMixtureDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";

export function BayesianMixtureSavedBatch({ study, batchId }: { study: MixtureStudy; batchId: string }) {
  const { locale } = useI18n(), text = mixtureMessages(locale), [reload, setReload] = useState(0);
  const key = JSON.stringify([study.study_id, study.study_version_id, study.definition_sha256, batchId, reload]);
  const guard = useRef(createPlanningRequestFence()).current; guard.source(key);
  const [state, setState] = useState<{ key: string; batch: MixtureBatch | null; error: boolean }>({ key, batch: null, error: false });
  useEffect(() => {
    const token = guard.begin(); setState({ key, batch: null, error: false });
    void fetchMixtureBatch(study.study_id, batchId).then(async batch => {
      if (!guard.current(token)) return;
      const model = await fetchMixtureModel(study.study_id, batch.config.model_id);
      if (!guard.current(token)) return;
      if (batch.schema_version !== 13 || batch.batch_id !== batchId || !validMixtureModel(model, study) || !validMixtureSelection({ ...batch, selection_id: batch.batch_id }, study, model) || !Array.isArray(batch.items) || batch.items.length !== batch.result.items.length || batch.items.some((item, i) => item.rank !== i + 1 || item.trial.study_version_id !== study.study_version_id || !validMixtureCoordinates(item.trial.actual_coordinates, study.mixture, study.process_factors) || !sameDesirabilityJson(item.result, batch.result.items[i]) || !sameDesirabilityJson(item.trial.actual_coordinates, item.result.actual_coordinates))) throw Error("bayesian_mixture_batch_source_mismatch");
      setState({ key, batch, error: false });
    }).catch(() => { if (guard.current(token)) setState({ key, batch: null, error: true }); });
    return () => guard.invalidate();
  }, [batchId, guard, key, study]);
  const stateNow = state.key === key ? state : { key, batch: null, error: false }, batch = stateNow.batch;
  return <section className="bo-planning" aria-label={locale === "ko" ? "저장 혼합물 배치" : "Saved mixture batch"}><h3>{locale === "ko" ? "저장 혼합물 배치" : "Saved mixture batch"}</h3><button type="button" className="secondary-button" onClick={() => setReload(current => current + 1)}><RefreshCw size={16} aria-hidden="true" />{text.refresh}</button>
    {stateNow.error ? <p role="alert">{text.invalid}</p> : !batch ? <p role="status">{text.working}</p> : <><p>{batch.config.expected_history_sha256 === study.observation_history.observation_history_sha256 && batch.config.expected_trial_count === study.trial_count ? "" : text.stale}</p><dl className="bo-planning-source"><dt>ID</dt><dd>{batch.batch_id}</dd><dt>Config SHA-256</dt><dd><code>{batch.config_sha256}</code></dd><dt>Result SHA-256</dt><dd><code>{batch.result_sha256}</code></dd><dt>Model SHA-256</dt><dd><code>{batch.config.expected_model_sha256}</code></dd><dt>History SHA-256</dt><dd><code>{batch.config.expected_history_sha256}</code></dd></dl>
      <div className="table-wrap"><table><thead><tr><th>{locale === "ko" ? "순서" : "Rank"}</th><th>{locale === "ko" ? "실험" : "Trial"}</th><th>{locale === "ko" ? "상태" : "State"}</th>{study.factors.map(factor => <th key={factor.factor_id}>{factor.name} {factor.unit}</th>)}{study.objective.responses.map(response => <th key={response.response_id}>{response.name} {response.unit}: Mean / Latent SD / Predictive SD</th>)}<th>{locale === "ko" ? "종합 만족도" : "Composite desirability"}</th></tr></thead><tbody>{batch.items.map(item => <tr key={item.trial.trial_id}><th>{item.rank}</th><td>{item.trial.trial_id}</td><td>{item.trial.state}</td>{study.factors.map(factor => <td key={factor.factor_id}>{typeof item.result.actual_coordinates[factor.factor_id] === "number" ? exact(item.result.actual_coordinates[factor.factor_id] as number) : item.result.actual_coordinates[factor.factor_id]}</td>)}{item.result.response_predictions.map(response => <td key={response.response_id}>{exact(response.mean_raw)} / {exact(response.latent_standard_deviation_raw)} / {exact(response.predictive_standard_deviation_raw)}</td>)}<td>{exact(item.result.desirability_moments.mean)}</td></tr>)}</tbody></table></div><p>{text.unsupported}</p><MixtureBatchReport study={study} batch={batch} /></>}
  </section>;
}

function MixtureBatchReport({ study, batch }: { study: MixtureStudy; batch: MixtureBatch }) {
  const { locale } = useI18n(), key = `${study.study_id}:${batch.batch_id}:${batch.result_sha256}:${locale}`;
  const fence = useRef(createPlanningRequestFence()).current; fence.source(key);
  const [state, setState] = useState<{ key: string; busy: boolean; error: boolean; report: ManagedReportDescriptor | null }>({ key, busy: false, error: false, report: null });
  useEffect(() => () => fence.invalidate(), [fence]);
  const current = state.key === key ? state : { key, busy: false, error: false, report: null };
  async function create() {
    if (current.busy) return;
    const token = fence.begin(); setState({ key, busy: true, error: false, report: null });
    try {
      const descriptor = await fetchMixtureBatchReportSource(study.study_id, batch.batch_id);
      if (!fence.current(token)) return;
      const source = descriptor.source;
      if (!isReportSourceDescriptor(descriptor) || source.kind !== "bayesian_history_revision" || source.study_id !== study.study_id || source.study_version_id !== study.study_version_id || source.definition_sha256 !== study.definition_sha256 || source.history_revision_id !== batch.config.expected_history_revision_id || source.expected_source_sha256 !== batch.config.expected_history_sha256 || source.attachment.kind !== "batch" || source.attachment.batch_id !== batch.batch_id || source.attachment.result_payload_sha256 !== batch.result_sha256) throw Error("bayesian_mixture_report_source_mismatch");
      const capability = await fetchStoredReportCapability(source, locale);
      if (!fence.current(token)) return;
      if (!isStoredReportCapability(capability) || !capability.html_available || capability.report_level === "unsupported" || capability.source_ref_sha256 !== descriptor.source_ref_sha256 || capability.locale !== locale || reportSourceKey(capability.source) !== reportSourceKey(source)) throw Error("bayesian_mixture_report_source_mismatch");
      const report = await createManagedReport(source, locale, descriptor.source_ref_sha256);
      if (!fence.current(token)) return;
      if (!isManagedReport(report) || report.source_ref_sha256 !== descriptor.source_ref_sha256 || report.locale !== locale || reportSourceKey(report.source) !== reportSourceKey(source)) throw Error("bayesian_mixture_report_source_mismatch");
      setState({ key, busy: false, error: false, report });
    } catch { if (fence.current(token)) setState({ key, busy: false, error: true, report: null }); }
  }
  async function download() {
    if (!current.report || current.busy) return;
    const token = fence.begin(), report = current.report; setState({ ...current, busy: true });
    try { const file = await fetchManagedReportDownload(report); if (fence.current(token)) { triggerBrowserDownload(file.blob, file.filename); setState({ key, busy: false, error: false, report }); } }
    catch { if (fence.current(token)) setState({ key, busy: false, error: true, report }); }
  }
  return <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={current.busy} onClick={() => void create()}><FileText size={16} aria-hidden="true" />{locale === "ko" ? "저장 배치 HTML 보고서" : "Saved batch HTML report"}</button>{current.report && <button type="button" className="secondary-button" disabled={current.busy} onClick={() => void download()}><Download size={16} aria-hidden="true" />{locale === "ko" ? "다운로드" : "Download"}</button>}{current.error && <p role="alert">{locale === "ko" ? "정확한 보고서 출처를 확인할 수 없습니다." : "The exact report source could not be verified."}</p>}</div>;
}
