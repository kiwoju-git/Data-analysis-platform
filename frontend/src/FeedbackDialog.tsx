import { Copy, Download, MessageSquare, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { triggerBrowserDownload } from "./api/client";
import { useI18n } from "./i18n/LocaleProvider";
import {
  buildSupportDiagnostics,
  copyFeedbackText,
  serializeFeedback,
  type FeedbackDraft,
  type SupportContext,
} from "./supportDiagnostics";
import "./feedbackDialog.css";

export function FeedbackEntry({ context, beforeOpen }: {
  context?: SupportContext;
  beforeOpen?: () => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return <>
    <button className="secondary-button feedback-entry" onClick={() => { beforeOpen?.(); setOpen(true); }} type="button">
      <MessageSquare size={16} aria-hidden="true" />
      {t("feedback.title")}
    </button>
    {open ? <FeedbackDialog context={context} onClose={() => setOpen(false)} /> : null}
  </>;
}

export function FeedbackDialog({ context = {}, onClose }: {
  context?: SupportContext;
  onClose: () => void;
}) {
  const { locale, t } = useI18n();
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const preview = useRef<HTMLTextAreaElement>(null);
  const [draft, setDraft] = useState<FeedbackDraft>({
    problemType: "problem", reproduction: "", expected: "", actual: "", repeatability: "unknown",
  });
  const [diagnostics] = useState(() => buildSupportDiagnostics(context, {
    locale,
    width: typeof window === "undefined" ? undefined : window.innerWidth,
    height: typeof window === "undefined" ? undefined : window.innerHeight,
  }));
  const [notice, setNotice] = useState<"copied" | "manual" | "downloaded" | "failed" | null>(null);
  const [copying, setCopying] = useState(false);
  const alive = useRef(true);
  const serialized = serializeFeedback(draft, diagnostics);

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const element = dialog.current;
    alive.current = true;
    element?.showModal();
    return () => {
      alive.current = false;
      element?.close();
      if (opener?.isConnected) opener.focus();
    };
  }, []);

  function selectPreview() {
    preview.current?.focus();
    preview.current?.select();
  }

  function updateDraft(change: Partial<FeedbackDraft>) {
    setDraft((current) => ({ ...current, ...change }));
    setNotice(null);
  }

  async function copy() {
    setCopying(true);
    let clipboard: Clipboard | undefined;
    try { clipboard = navigator.clipboard; } catch { clipboard = undefined; }
    const outcome = await copyFeedbackText(serialized, clipboard);
    if (!alive.current) return;
    setCopying(false);
    setNotice(outcome);
    if (outcome === "manual") selectPreview();
  }

  function download(format: "json" | "txt") {
    try {
      triggerBrowserDownload(new Blob([serialized], {
        type: format === "json" ? "application/json;charset=utf-8" : "text/plain;charset=utf-8",
      }), `statistical-twin-feedback.${format}`);
      setNotice("downloaded");
    } catch {
      setNotice("failed");
      selectPreview();
    }
  }

  return (
    <dialog
      aria-labelledby={`${id}-title`}
      aria-describedby={`${id}-privacy`}
      aria-modal="true"
      className="feedback-dialog"
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      ref={dialog}
    >
      <div className="feedback-heading">
        <h2 id={`${id}-title`}>{t("feedback.title")}</h2>
        <button aria-label={t("feedback.close")} className="secondary-button feedback-close" onClick={onClose} type="button">
          <X size={18} aria-hidden="true" />
        </button>
      </div>
      <p>{t("feedback.localOnly")}</p>
      <p className="feedback-privacy" id={`${id}-privacy`}>{t("feedback.sensitiveWarning")}</p>
      <div className="feedback-fields">
        <label>
          {t("feedback.problemType")}
          <select value={draft.problemType} onChange={(event) => updateDraft({ problemType: event.target.value as FeedbackDraft["problemType"] })}>
            <option value="problem">{t("feedback.type.problem")}</option>
            <option value="suggestion">{t("feedback.type.suggestion")}</option>
            <option value="other">{t("feedback.type.other")}</option>
          </select>
        </label>
        <label>
          {t("feedback.repeatability")}
          <select value={draft.repeatability} onChange={(event) => updateDraft({ repeatability: event.target.value as FeedbackDraft["repeatability"] })}>
            <option value="unknown">{t("feedback.repeat.unknown")}</option>
            <option value="always">{t("feedback.repeat.always")}</option>
            <option value="sometimes">{t("feedback.repeat.sometimes")}</option>
            <option value="once">{t("feedback.repeat.once")}</option>
          </select>
        </label>
      </div>
      <label className="feedback-field">
        {t("feedback.reproduction")}
        <textarea maxLength={4000} rows={3} value={draft.reproduction} onChange={(event) => updateDraft({ reproduction: event.target.value })} />
      </label>
      <div className="feedback-fields">
        <label>
          {t("feedback.expected")}
          <textarea maxLength={4000} rows={3} value={draft.expected} onChange={(event) => updateDraft({ expected: event.target.value })} />
        </label>
        <label>
          {t("feedback.actual")}
          <textarea maxLength={4000} rows={3} value={draft.actual} onChange={(event) => updateDraft({ actual: event.target.value })} />
        </label>
      </div>
      <p className="muted">{t("feedback.diagnosticsNotice")}</p>
      <p className="muted">{t(`feedback.connection.${diagnostics.server_connection}`)}</p>
      <label className="feedback-field">
        {t("feedback.preview")}
        <textarea className="feedback-preview" readOnly ref={preview} rows={9} spellCheck={false} value={serialized} />
      </label>
      <div className="feedback-actions">
        <button className="secondary-button" disabled={copying} onClick={() => void copy()} type="button"><Copy size={16} aria-hidden="true" />{t("feedback.copy")}</button>
        <button className="secondary-button" onClick={() => download("json")} type="button"><Download size={16} aria-hidden="true" />{t("feedback.downloadJson")}</button>
        <button className="secondary-button" onClick={() => download("txt")} type="button"><Download size={16} aria-hidden="true" />{t("feedback.downloadText")}</button>
      </div>
      <p aria-live="polite" className="feedback-notice" role="status">
        {notice === "copied" ? t("feedback.copied") : notice === "manual" ? t("feedback.copyFallback") : notice === "downloaded" ? t("feedback.downloadStarted") : notice === "failed" ? t("feedback.downloadFailed") : ""}
      </p>
    </dialog>
  );
}
