import { useEffect, useState } from "react";
import { createFactorialReport, deleteFactorialAsset, downloadFactorialAsset, fetchFactorialPrediction, fetchFactorialPredictionAssets, fetchFactorialReports, preflightFactorialAssetDeletion } from "./api/factorialWorkflow";
import type { DoeAnalysisAssetDescriptor, DoePredictionResponse } from "./api/types/doeModelWorkflow";
import { FactorialPredictionResults } from "./FactorialPredictionPanel";
import { factorialWorkflowMessage } from "./doe/factorialWorkflowPresentation";
import { getCurrentLocale } from "./i18n/store";
import { t } from "./i18n/translate";

export function FactorialAnalysisAssetsPanel({ designId, analysisId, refreshKey = 0 }: { designId: string; analysisId: string; refreshKey?: number }) {
  const [assets, setAssets] = useState<DoeAnalysisAssetDescriptor[]>([]);
  const [prediction, setPrediction] = useState<DoePredictionResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletion, setDeletion] = useState<DoeAnalysisAssetDescriptor | null>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let current = true;
    setError(null);
    void Promise.all([fetchFactorialReports(designId, analysisId), fetchFactorialPredictionAssets(designId, analysisId)])
      .then(([reports, predictions]) => { if (current) setAssets([...reports.items, ...predictions.items].sort((a, b) => b.created_at.localeCompare(a.created_at))); })
      .catch((caught) => { if (current) setError(caught instanceof Error ? caught.message : "doe_factorial_workflow_failed"); });
    return () => { current = false; };
  }, [analysisId, designId, refreshKey, reload]);
  async function perform(action: () => Promise<void>) {
    setPending(true); setError(null);
    try { await action(); } catch (caught) { setError(caught instanceof Error ? caught.message : "doe_factorial_workflow_failed"); }
    finally { setPending(false); }
  }
  return <section className="result-section factorial-analysis-assets"><div className="panel-heading compact-heading"><h3>{t("doe.report.title")}</h3>
    <div className="button-row"><button type="button" className="secondary-button" disabled={pending} onClick={() => setReload((value) => value + 1)}>{t("doe.report.refresh")}</button>
      <button type="button" className="primary-button" disabled={pending} onClick={() => void perform(async () => { await createFactorialReport(designId, analysisId, getCurrentLocale()); setReload((value) => value + 1); })}>{t(pending ? "doe.workflow.busy" : "doe.report.generate")}</button></div></div>
    <p className="field-help">{t("doe.report.policy")}</p>
    {error ? <p className="error-box" role="alert">{factorialWorkflowMessage(error)} <code>{error}</code></p> : null}
    {assets.length === 0 ? <p>{t("doe.report.empty")}</p> : <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("doe.report.kind")}</th><th>{t("doe.report.created")}</th><th>{t("doe.report.size")}</th><th /></tr></thead><tbody>
      {assets.map((asset) => <tr key={asset.asset_id}><td>{t(asset.kind === "html_report" ? "doe.report.html" : "doe.report.prediction")} {asset.locale?.toUpperCase()}</td><td>{new Date(asset.created_at).toLocaleString()}</td><td>{(asset.size_bytes / 1024).toFixed(1)} KB</td><td><div className="button-row">
        {asset.kind === "prediction" ? <button type="button" className="secondary-button" disabled={pending} onClick={() => void perform(async () => setPrediction(await fetchFactorialPrediction(designId, analysisId, asset.asset_id)))}>{t("doe.report.open")}</button> : null}
        <button type="button" className="secondary-button" disabled={pending} onClick={() => void perform(() => downloadFactorialAsset(designId, analysisId, asset))}>{t("doe.report.download")}</button>
        <button type="button" className="secondary-button" disabled={pending} onClick={() => void perform(async () => setDeletion(await preflightFactorialAssetDeletion(designId, analysisId, asset.asset_id)))}>{t("doe.report.delete")}</button>
      </div></td></tr>)}
    </tbody></table></div>}
    {deletion ? <section className="notice-box notice-warning" aria-label={t("doe.report.delete")}><p>{t("doe.report.confirm")}</p><p>{deletion.kind} · {deletion.size_bytes} bytes · SHA {deletion.sha256.slice(0, 12)}</p><div className="button-row">
      <button type="button" className="secondary-button" disabled={pending} onClick={() => setDeletion(null)}>{t("doe.paste.cancel")}</button>
      <button type="button" className="danger-button" disabled={pending} onClick={() => void perform(async () => { await deleteFactorialAsset(designId, analysisId, deletion); setDeletion(null); setPrediction(null); setReload((value) => value + 1); })}>{t("doe.report.deleteConfirm")}</button>
    </div></section> : null}
    {prediction ? <FactorialPredictionResults result={prediction} /> : null}
  </section>;
}
