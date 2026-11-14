import { useEffect, useRef, useState } from "react";
import { Download, FileText } from "lucide-react";
import { boViewReportSource, type BoSavedView } from "../../api/boViews";
import { createManagedReport, fetchManagedReportDownload, fetchStoredReportCapability } from "../../api/reports";
import { triggerBrowserDownload } from "../../api/client";
import type { ManagedReportDescriptor } from "../../api/types/reports";
import { isManagedReport, isStoredReportCapability, reportSourceKey } from "../../managedReportSource";
import { useI18n } from "../../i18n/LocaleProvider";
import { boViewMessages } from "../../i18n/boViews";
import { createPlanningRequestFence } from "./boPlanningDraft";

export function BoSavedViewReport({ view }: { view: BoSavedView }) {
  const { locale } = useI18n(), text = boViewMessages(locale), key = `${view.view_id}:${view.view_sha256}:${locale}`;
  const guard = useRef(createPlanningRequestFence()).current; guard.source(key);
  const [state, setState] = useState<{ key: string; busy: boolean; error: boolean; report: ManagedReportDescriptor | null }>({ key, busy: false, error: false, report: null });
  const current = state.key === key ? state : { key, busy: false, error: false, report: null };
  useEffect(() => () => guard.invalidate(), [guard]);
  async function create() {
    if (current.busy) return;
    const token = guard.begin(); setState({ key, busy: true, error: false, report: null });
    try {
      const descriptor = await boViewReportSource(view.source.study_id, view.view_id);
      if (!guard.current(token)) return;
      const source = descriptor.source;
      if (source.kind !== "bayesian_history_revision" || source.study_id !== view.source.study_id || source.study_version_id !== view.source.study_version_id || source.history_revision_id !== view.source.history_revision_id || source.expected_source_sha256 !== view.source.history_sha256
        || source.attachment.kind !== "view" || source.attachment.view_id !== view.view_id || source.attachment.view_sha256 !== view.view_sha256 || source.attachment.request_sha256 !== view.request_sha256 || source.attachment.model_sha256 !== view.source.model_sha256 || source.attachment.model_config_sha256 !== view.source.model_config_sha256) throw Error("bayesian_view_report_mismatch");
      const capability = await fetchStoredReportCapability(source, locale);
      if (!guard.current(token)) return;
      if (!isStoredReportCapability(capability) || !capability.html_available || capability.source_ref_sha256 !== descriptor.source_ref_sha256 || reportSourceKey(capability.source) !== reportSourceKey(source) || capability.locale !== locale) throw Error("bayesian_view_report_mismatch");
      const report = await createManagedReport(source, locale, descriptor.source_ref_sha256);
      if (!guard.current(token)) return;
      if (!isManagedReport(report) || report.source_ref_sha256 !== descriptor.source_ref_sha256 || reportSourceKey(report.source) !== reportSourceKey(source) || report.locale !== locale) throw Error("bayesian_view_report_mismatch");
      setState({ key, busy: false, error: false, report });
    } catch { if (guard.current(token)) setState({ key, busy: false, error: true, report: null }); }
  }
  async function download() {
    if (!current.report || current.busy) return;
    const token = guard.begin(), report = current.report; setState({ ...current, busy: true });
    try {
      const file = await fetchManagedReportDownload(report);
      if (guard.current(token)) { triggerBrowserDownload(file.blob, file.filename); setState({ key, busy: false, error: false, report }); }
    } catch { if (guard.current(token)) setState({ key, busy: false, error: true, report }); }
  }
  return <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={current.busy} onClick={() => void create()}><FileText size={16} aria-hidden="true" />{text.report}</button>
    {current.report && <button type="button" className="secondary-button" disabled={current.busy} onClick={() => void download()}><Download size={16} aria-hidden="true" />{text.download}</button>}{current.busy && <span role="status">{text.busy}</span>}{current.error && <p role="alert">{text.reportError}</p>}</div>;
}
