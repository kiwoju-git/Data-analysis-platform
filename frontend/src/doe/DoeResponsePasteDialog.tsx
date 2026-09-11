import { useId, useRef, useState } from "react";

import { useI18n } from "../i18n/LocaleProvider";
import { parseDoeResponsePaste, type DoeResponsePasteLayout, type DoeResponsePasteResult } from "./doeResponsePaste";

interface Props {
  disabled: boolean;
  runOrders: readonly number[];
  onApply: (values: Record<string, string>) => void;
}

export function DoeResponsePasteDialog({ disabled, runOrders, onApply }: Props) {
  const { t } = useI18n();
  const id = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState("");
  const [layout, setLayout] = useState<DoeResponsePasteLayout>("values");
  const [hasHeader, setHasHeader] = useState(false);
  const [delimiter, setDelimiter] = useState("auto");
  const [preview, setPreview] = useState<DoeResponsePasteResult | null>(null);

  function close() { setOpen(false); buttonRef.current?.focus(); }
  function parse() {
    const result = parseDoeResponsePaste(content, runOrders, {
      layout, hasHeader, delimiter: delimiter === "auto" ? undefined : delimiter === "tab" ? "\t" : ",",
    });
    setPreview(result);
    if (!result.ok) textareaRef.current?.focus();
  }

  return <>
    <button ref={buttonRef} className="secondary-button" type="button" disabled={disabled}
      aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}>
      {t("doe.paste.title")}
    </button>
    {open && !disabled ? <section className="doe-response-paste" id={id} aria-labelledby={`${id}-title`}>
      <h4 id={`${id}-title`}>{t("doe.paste.title")}</h4>
      <p id={`${id}-help`}>{t("doe.paste.policy")}</p>
      <div className="option-grid">
        <label>{t("doe.paste.layout")}<select aria-label={t("doe.paste.layout")} value={layout} onChange={(event) => { setLayout(event.currentTarget.value as DoeResponsePasteLayout); setPreview(null); }}>
          <option value="values">{t("doe.paste.values")}</option>
          <option value="run_order">{t("doe.paste.runValues")}</option>
        </select></label>
        <label>{t("doe.paste.delimiter")}<select aria-label={t("doe.paste.delimiter")} value={delimiter} onChange={(event) => { setDelimiter(event.currentTarget.value); setPreview(null); }}>
          <option value="auto">{t("doe.paste.auto")}</option><option value="tab">TSV</option><option value="comma">CSV</option>
        </select></label>
        <label className="checkbox-label"><input type="checkbox" checked={hasHeader} onChange={(event) => { setHasHeader(event.currentTarget.checked); setPreview(null); }} />{t("doe.paste.header")}</label>
      </div>
      <textarea ref={textareaRef} aria-label={t("doe.paste.title")} aria-describedby={`${id}-help${preview && !preview.ok ? ` ${id}-error` : ""}`}
        aria-invalid={preview !== null && !preview.ok} rows={6} value={content}
        onChange={(event) => { setContent(event.currentTarget.value); setPreview(null); }} />
      {preview && !preview.ok ? <p className="error-box" id={`${id}-error`} role="alert">{t(`doe.paste.error.${preview.error}`)}</p> : null}
      {preview?.ok ? <div className="table-wrap"><table className="result-table">
        <thead><tr><th>{t("doe.workflow.runOrder")}</th><th>{t("doe.workflow.response")}</th></tr></thead>
        <tbody>{preview.rows.map((row) => <tr key={row.runOrder}><td>{row.runOrder}</td><td>{row.value}</td></tr>)}</tbody>
      </table></div> : null}
      <div className="button-row">
        <button className="secondary-button" type="button" onClick={close}>{t("doe.paste.cancel")}</button>
        <button className="secondary-button" type="button" onClick={parse}>{t("doe.paste.preview")}</button>
        <button className="primary-button" type="button" disabled={!preview?.ok} onClick={() => {
          if (!preview?.ok) return;
          onApply(Object.fromEntries(preview.rows.map((row) => [String(row.runOrder), row.value])));
          setPreview(null); setContent(""); close();
        }}>{t("doe.paste.apply")}</button>
      </div>
    </section> : null}
  </>;
}
