import { useMemo, useRef, useState } from "react";
import { createFactorialPrediction, preflightFactorialPrediction } from "./api/factorialWorkflow";
import type { DoePredictionBasis, DoePredictionPreflightResponse, DoePredictionResponse, DoePredictionRowRequest } from "./api/types/doeModelWorkflow";
import { factorialViewFactors, isGeneralFactorial, type FactorialViewDesign } from "./doe/factorialView";
import { factorialNumber } from "./doe/factorialWorkflowPresentation";
import { parsePastedTablePreview } from "./pastedTablePreview";
import { t } from "./i18n/translate";

import { factorialWorkflowMessage } from "./doe/factorialWorkflowPresentation";

interface DraftRow { id: string; settings: Record<string, string>; block: string }
export function FactorialPredictionPanel({ design, analysisId, basis, onSaved }: {
  design: FactorialViewDesign; analysisId: string; basis: DoePredictionBasis; onSaved: () => void;
}) {
  const factors = factorialViewFactors(design);
  const sequence = useRef(1);
  const revision = useRef(0);
  const makeRow = (): DraftRow => ({ id: `row-${sequence.current++}`, settings: Object.fromEntries(factors.map((factor) => [factor.name, String(factor.levels[0].actual)])), block: String(basis.block_levels[0] ?? "") });
  const [rows, setRows] = useState<DraftRow[]>(() => [makeRow()]);
  const [confidence, setConfidence] = useState(basis.confidence_level);
  const [preflight, setPreflight] = useState<DoePredictionPreflightResponse | null>(null);
  const [result, setResult] = useState<DoePredictionResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paste, setPaste] = useState("");
  const [header, setHeader] = useState(false);
  const pasted = useMemo(() => parsePastedTablePreview(paste, { maxRows: 258, maxColumns: factors.length + 1, maxCells: 3000, maxScanCharacters: 100_000 }), [paste, factors.length]);
  const pasteRows = pasted.rows.slice(header ? 1 : 0);
  const pasteValid = paste.length > 0 && paste.length <= 100_000 && !pasted.rawModeOnly && !pasted.truncatedRows && !pasted.truncatedColumns && !pasted.countsAreLowerBounds &&
    pasteRows.length > 0 && pasteRows.length <= 256 && pasteRows.every((row) => row.length === factors.length && row.every((cell) => cell.trim() !== "")) &&
    (!header || factors.every((factor, index) => pasted.rows[0]?.[index]?.trim() === factor.name));
  function invalidate() { revision.current += 1; setPreflight(null); setResult(null); setError(null); }
  function edit(next: DraftRow[]) { invalidate(); setRows(next); }
  function requestRows(): DoePredictionRowRequest[] | null {
    const parsed: DoePredictionRowRequest[] = [];
    for (const row of rows) {
      const settings: Record<string, number | string> = {};
      for (const factor of factors) {
        const value = row.settings[factor.name]?.trim() ?? "";
        if (factor.numeric) {
          if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(value) || !Number.isFinite(Number(value))) return null;
          settings[factor.name] = Number(value);
        } else {
          const level = factor.levels.find((candidate) => String(candidate.actual) === value);
          if (!level) return null;
          settings[factor.name] = level.actual;
        }
      }
      parsed.push({ row_id: row.id, factor_settings: settings, block_index: row.block === "" ? null : Number(row.block) });
    }
    return parsed;
  }
  async function execute(predict: boolean) {
    const parsed = requestRows();
    if (!parsed || !(confidence > 0 && confidence < 1)) { setError("doe_factorial_prediction_input_invalid"); return; }
    const current = revision.current; setPending(true); setError(null);
    try {
      const body = { rows: parsed, confidence_level: confidence };
      if (predict && preflight?.valid) {
        const saved = await createFactorialPrediction(design.design_id, analysisId, { ...body, expected_preflight_sha256: preflight.preflight_sha256 });
        if (current === revision.current) { setResult(saved); onSaved(); }
      } else {
        const checked = await preflightFactorialPrediction(design.design_id, analysisId, body);
        if (current === revision.current) setPreflight(checked);
      }
    } catch (caught) { if (current === revision.current) setError(caught instanceof Error ? caught.message : "doe_factorial_workflow_failed"); }
    finally { setPending(false); }
  }
  return <section className="result-section factorial-prediction"><h3>{t("doe.prediction.title")}</h3><p className="field-help">{t("doe.prediction.policy")}</p>
    {isGeneralFactorial(design) ? <p className="field-help">{t("doe.prediction.generalPolicy")}</p> : null}
    {basis.features.some((feature) => feature.kind === "center_curvature") ? <p className="notice-box notice-warning">{t("doe.prediction.centerPolicy")}</p> : null}
    <div className="table-wrap"><table className="result-table factorial-prediction-input"><thead><tr><th>#</th>{factors.map((factor) => <th key={factor.name}>{factor.name}</th>)}{basis.block_levels.length > 1 ? <th>{t("doe.prediction.block")}</th> : null}<th /></tr></thead>
      <tbody>{rows.map((row, index) => <tr key={row.id}><td>{index + 1}</td>{factors.map((factor) => <td key={factor.name}>
        {factor.numeric ? <input aria-label={`${factor.name} ${index + 1}`} disabled={pending} inputMode="decimal" value={row.settings[factor.name]}
          onChange={(event) => edit(rows.map((item) => item.id === row.id ? { ...item, settings: { ...item.settings, [factor.name]: event.currentTarget.value } } : item))} />
          : <select aria-label={`${factor.name} ${index + 1}`} disabled={pending} value={row.settings[factor.name]}
            onChange={(event) => edit(rows.map((item) => item.id === row.id ? { ...item, settings: { ...item.settings, [factor.name]: event.currentTarget.value } } : item))}>
            {factor.levels.map((level) => <option key={level.code} value={String(level.actual)}>{String(level.actual)}</option>)}
          </select>}
        <small>{factor.levels.map((level) => String(level.actual)).join(" / ")}{factor.unit ? ` ${factor.unit}` : ""}</small>
      </td>)}{basis.block_levels.length > 1 ? <td><select aria-label={`${t("doe.prediction.block")} ${index + 1}`} value={row.block} disabled={pending}
        onChange={(event) => edit(rows.map((item) => item.id === row.id ? { ...item, block: event.currentTarget.value } : item))}>{basis.block_levels.map((block) => <option key={block} value={String(block)}>{block}</option>)}</select></td> : null}
      <td><button type="button" className="icon-button" title={t("doe.prediction.remove")} aria-label={`${t("doe.prediction.remove")} ${index + 1}`} disabled={pending || rows.length === 1} onClick={() => edit(rows.filter((item) => item.id !== row.id))}>−</button></td></tr>)}</tbody>
    </table></div>
    <button type="button" className="secondary-button" disabled={pending || rows.length >= 256} onClick={() => edit([...rows, makeRow()])}>{t("doe.prediction.add")}</button>
    <details className="factorial-prediction-paste"><summary>{t("doe.prediction.paste")}</summary><p>{t("doe.prediction.pastePolicy")}</p>
      <textarea aria-label={t("doe.prediction.paste")} rows={5} maxLength={100_000} value={paste} onChange={(event) => setPaste(event.currentTarget.value)} />
      <label className="doe-table-toggle"><input type="checkbox" checked={header} onChange={(event) => setHeader(event.currentTarget.checked)} /><span>{t("doe.paste.header")}</span></label>
      {!pasteValid && paste !== "" ? <p role="alert">{t("doe.prediction.invalidPaste")}</p> : null}
      {pasteValid ? <div className="table-wrap factorial-paste-preview"><table className="result-table"><thead><tr>{factors.map((factor) => <th key={factor.name}>{factor.name}</th>)}</tr></thead><tbody>{pasteRows.map((row, index) => <tr key={index}>{row.map((cell, column) => <td key={column}>{cell}</td>)}</tr>)}</tbody></table></div> : null}
      <button type="button" className="secondary-button" disabled={pending || !pasteValid} onClick={() => { edit(pasteRows.map((row) => ({ ...makeRow(), settings: Object.fromEntries(factors.map((factor, index) => [factor.name, row[index].trim()])) }))); setPaste(""); }}>{t("doe.paste.apply")}</button>
    </details>
    <label className="factorial-inline-select"><span>{t("doe.selection.confidence")}</span><input type="number" disabled={pending} step="0.01" min="0.01" max="0.999" value={Number.isFinite(confidence) ? confidence : ""}
      onChange={(event) => { invalidate(); setConfidence(event.currentTarget.valueAsNumber); }} /></label>
    <div className="button-row"><button type="button" className="secondary-button" disabled={pending} onClick={() => void execute(false)}>{t("doe.prediction.preflight")}</button>
      <button type="button" className="primary-button" disabled={pending || !preflight?.valid} onClick={() => void execute(true)}>{t(pending ? "doe.workflow.busy" : "doe.prediction.run")}</button></div>
    {error ? <div className="error-box" role="alert">{factorialWorkflowMessage(error)} <code>{error}</code></div> : null}
    {preflight ? <div role="status">{preflight.valid ? t("doe.prediction.ready") : preflight.issues.map((issue, index) => <p className="notice-box notice-warning" key={index}>{issue.row_id} {issue.factor_name}: {factorialWorkflowMessage(issue.code)}</p>)}</div> : null}
    {result ? <FactorialPredictionResults result={result} /> : null}
  </section>;
}

export function FactorialPredictionResults({ result }: { result: DoePredictionResponse }) {
  const interval = (value: DoePredictionResponse["rows"][number]["mean_confidence_interval"]) => value === null ? "-" : `[${factorialNumber(value.lower)}, ${factorialNumber(value.upper)}] (${factorialNumber(value.level * 100)}%)`;
  return <section className="result-section"><h4>{t("doe.report.prediction")}</h4><div className="table-wrap"><table className="result-table factorial-prediction-results"><thead><tr><th>#</th><th>{t("doe.plots.fixed")}</th><th>{t("doe.prediction.mean")}</th><th>{t("doe.prediction.se")}</th><th>{t("doe.prediction.ci")}</th><th>{t("doe.prediction.pi")}</th></tr></thead><tbody>
    {result.rows.map((row) => <tr key={row.row_id}><td>{row.row_id}</td><td>{Object.entries(row.factor_settings).map(([name, value]) => `${name}=${value}`).join(", ")}</td><td>{factorialNumber(row.fitted_mean)}</td><td>{factorialNumber(row.standard_error_fit)}</td><td>{interval(row.mean_confidence_interval)}</td><td>{interval(row.individual_prediction_interval)}</td></tr>)}
  </tbody></table></div>{result.rows.some((row) => row.interval_unavailability_reason) ? <p className="notice-box notice-warning">{t("doe.prediction.noVariance")}</p> : null}
  {result.warnings.map((warning) => <p className="notice-box notice-warning" key={warning}>{factorialWorkflowMessage(warning)}</p>)}
  <details><summary>SHA-256</summary><p>{result.source_analysis_sha256}</p><p>{result.prediction_id}</p></details></section>;
}
