import { useEffect, useRef, useState } from "react";
import { FolderOpen, RefreshCw } from "lucide-react";
import { listBoViews, readBoView, type BoSavedView, type BoSavedViewSummary } from "../../api/boViews";
import { useI18n } from "../../i18n/LocaleProvider";
import { boViewMessages } from "../../i18n/boViews";
import { createPlanningRequestFence } from "./boPlanningDraft";
import { validSavedView, matrixFromPayload, looFromPayload } from "./boSavedViews";
import { BayesianProfileMatrix } from "./BayesianProfileMatrix";
import { BayesianLooPanel } from "./BayesianLooPanel";
import { BoSavedViewReport } from "./BoSavedViewReport";
import { BoViewMetadata } from "./BoViewMetadata";

export function BayesianSavedViews({ studyId, contextKey, initialViewId = null }: { studyId: string; contextKey: string; initialViewId?: string | null }) {
  return <SavedViewCatalog key={`${studyId}:${contextKey}`} studyId={studyId} initialViewId={initialViewId} />;
}
function SavedViewCatalog({ studyId, initialViewId }: { studyId: string; initialViewId: string | null }) {
  const { locale } = useI18n(), text = boViewMessages(locale), guard = useRef(createPlanningRequestFence()).current;
  const [items, setItems] = useState<BoSavedViewSummary[]>([]), [selected, setSelected] = useState(initialViewId ?? "");
  const [view, setView] = useState<BoSavedView | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(false);
  async function refresh() {
    const token = guard.begin(); setBusy(true); setError(false);
    try { const result = await listBoViews(studyId); if (guard.current(token)) {
      if (result.items.some(item => item.source.study_id !== studyId)) throw Error("bayesian_view_owner_mismatch"); setItems(result.items);
    } } catch { if (guard.current(token)) setError(true); } finally { if (guard.current(token)) setBusy(false); }
  }
  async function open(id: string) {
    const token = guard.begin(); setBusy(true); setError(false); setView(null);
    try { const result = await readBoView(studyId, id); if (guard.current(token)) {
      if (result.view_id !== id || !validSavedView(result, studyId)) throw Error("bayesian_view_owner_mismatch"); setView(result);
    } } catch { if (guard.current(token)) setError(true); } finally { if (guard.current(token)) setBusy(false); }
  }
  useEffect(() => {
    const token = guard.begin(); setBusy(true); setError(false);
    void (async () => {
      try {
        const catalog = await listBoViews(studyId);
        if (!guard.current(token)) return;
        if (catalog.items.some(item => item.source.study_id !== studyId)) throw Error("bayesian_view_owner_mismatch");
        setItems(catalog.items);
        if (initialViewId) {
          const saved = await readBoView(studyId, initialViewId);
          if (!guard.current(token)) return;
          if (saved.view_id !== initialViewId || !validSavedView(saved, studyId)) throw Error("bayesian_view_owner_mismatch");
          setView(saved);
        }
      } catch { if (guard.current(token)) setError(true); }
      finally { if (guard.current(token)) setBusy(false); }
    })();
    return () => guard.invalidate();
  }, [studyId, initialViewId, guard]);
  return <section className="bo-saved-views" aria-label={text.stored}><h4>{text.stored}</h4>
    <div className="bo-planning-actions"><label>{text.choose}<select value={selected} onChange={event => { const id = event.currentTarget.value; guard.invalidate(); setBusy(false); setView(null); setSelected(id); }}><option value="">{text.choose}</option>{items.map(item => <option key={item.view_id} value={item.view_id}>{item.created_at} · {item.kind === "profiler_matrix" ? text.profiler : text.loo}</option>)}</select></label>
      <button type="button" className="secondary-button" disabled={!selected || busy} onClick={() => void open(selected)}><FolderOpen size={16} aria-hidden="true" />{text.open}</button>
      <button type="button" className="secondary-button" disabled={busy} onClick={() => void refresh()}><RefreshCw size={16} aria-hidden="true" />{text.refresh}</button></div>
    {busy && <p role="status">{text.busy}</p>}{error && <p role="alert">{text.error}</p>}{!busy && !error && !items.length && <p>{text.empty}</p>}
    {view && <><p className="notice-box">{text.immutable}</p>{view.payload.kind === "profiler_matrix" ? <BayesianProfileMatrix view={matrixFromPayload(view.payload)} /> : <BayesianLooPanel studyId={studyId} contextKey={view.view_sha256} savedView={looFromPayload(view.payload)} model={{ model_id: view.source.model_id, snapshot_sha256: view.source.model_sha256, config_sha256: view.source.model_config_sha256, history_sha256: view.source.history_sha256, source_history_revision_id: view.source.history_revision_id, source_is_current: false, objective: { responses: view.payload.responses } }} />}
      <BoViewMetadata payload={view.payload} /><BoSavedViewReport view={view} /><details><summary>{text.source}</summary><dl className="bo-planning-source"><div><dt>model_sha256</dt><dd>{view.source.model_sha256}</dd></div><div><dt>history_sha256</dt><dd>{view.source.history_sha256}</dd></div><div><dt>view_sha256</dt><dd>{view.view_sha256}</dd></div></dl></details></>}
  </section>;
}
