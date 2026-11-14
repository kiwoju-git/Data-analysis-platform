import { useEffect, useRef, useState } from "react";
import { Save, RotateCw } from "lucide-react";
import { saveBoView, type BoSavedView, type BoViewReceipt } from "../../api/boViews";
import { useI18n } from "../../i18n/LocaleProvider";
import { boViewMessages } from "../../i18n/boViews";
import { validSavedView } from "./boSavedViews";
import { BoSavedViewReport } from "./BoSavedViewReport";
import { bayesianRequestId } from "./bayesianRequestId";
import { BoViewMetadata } from "./BoViewMetadata";

export function BoViewSaveAction({ receipt }: { receipt: BoViewReceipt }) {
  return <SaveReceipt key={receipt.receipt_id} receipt={receipt} />;
}
function SaveReceipt({ receipt }: { receipt: BoViewReceipt }) {
  const { locale } = useI18n(), text = boViewMessages(locale), mounted = useRef(true), running = useRef(false);
  const request = useRef<{ request_id: string; receipt_id: string; expected_model_sha256: string; expected_request_sha256: string; expected_view_sha256: string } | null>(null);
  const [state, setState] = useState<{ busy: boolean; error: boolean; saved: BoSavedView | null }>({ busy: false, error: false, saved: null });
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function save() {
    if (running.current || state.saved) return;
    running.current = true; setState({ busy: true, error: false, saved: null });
    try {
      request.current ??= { request_id: bayesianRequestId(), receipt_id: receipt.receipt_id, expected_model_sha256: receipt.payload.source.model_sha256, expected_request_sha256: receipt.request_sha256, expected_view_sha256: receipt.view_sha256 };
      const saved = await saveBoView(receipt.payload.source.study_id, request.current);
      if (!mounted.current) return;
      if (!validSavedView(saved, receipt.payload.source.study_id) || saved.view_sha256 !== receipt.view_sha256 || saved.request_sha256 !== receipt.request_sha256) throw Error("bayesian_view_save_mismatch");
      setState({ busy: false, error: false, saved });
    } catch { if (mounted.current) setState({ busy: false, error: true, saved: null }); }
    finally { running.current = false; }
  }
  return <div className="bo-view-save"><BoViewMetadata payload={receipt.payload} /><div className="bo-planning-actions">
    <button type="button" className="secondary-button" disabled={state.busy || state.saved !== null} onClick={() => void save()}>{state.error ? <RotateCw size={16} aria-hidden="true" /> : <Save size={16} aria-hidden="true" />}{state.saved ? text.saved : state.error ? text.retry : text.save}</button>
    {state.busy && <span role="status">{text.busy}</span>}
  </div><p className="cell-subtext">{text.expired}</p>{state.error && <p role="alert">{text.error}</p>}{state.saved && <BoSavedViewReport view={state.saved} />}</div>;
}
