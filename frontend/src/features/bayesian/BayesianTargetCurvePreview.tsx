import { useEffect, useRef, useState } from "react";
import { ChartLine } from "lucide-react";
import { previewBayesianTargetCurve } from "../../api/bayesianDesirability";
import type { CurvePreviewResponse } from "../../api/types/boCurvePreview";
import { InteractiveScatterChart, type InteractiveScatterPoint } from "../../charts/InteractiveScatterChart";
import { useI18n } from "../../i18n/LocaleProvider";
import { curvePreviewMessages } from "../../i18n/boCurvePreview";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import type { ResponseGoalDraft } from "./bayesianVectorDraft";
import { curvePreviewRequest, initialCurvePreviewDraft } from "./boCurvePreviewDraft";
import "./boCurvePreview.css";

export function BayesianTargetCurvePreview({ goals, sourceKey }: { goals: ResponseGoalDraft[]; sourceKey: string }) {
  const { locale } = useI18n();
  const text = curvePreviewMessages(locale);
  const [selected, setSelected] = useState("");
  const [draft, setDraft] = useState(initialCurvePreviewDraft);
  const [response, setResponse] = useState<{ source: string; token: number; value: CurvePreviewResponse } | null>(null);
  const [pending, setPending] = useState<{ source: string; token: number } | null>(null);
  const [failed, setFailed] = useState<{ source: string; token: number } | null>(null);
  const sequence = useRef(0);
  const current = `${sourceKey}:${selected}:${JSON.stringify(draft)}`;
  const currentRef = useRef(current);
  if (currentRef.current !== current) sequence.current += 1;
  currentRef.current = current;
  useEffect(() => () => { sequence.current += 1; }, []);
  const goal = goals.find(g => g.responseId === selected && g.goal === "match_target");
  const effectiveDraft = goal?.curve === "gaussian_target" ? { ...draft, lower: goal.lowerDesirability ?? "", upper: goal.upperDesirability ?? "" } : draft;
  const request = curvePreviewRequest(goal, effectiveDraft);
  const running = pending?.source === current && pending.token === sequence.current;
  const result = response?.source === current && response.token === sequence.current ? response.value : null;
  function change(field: keyof typeof draft, value: string | boolean) {
    sequence.current += 1;
    setPending(null); setResponse(null); setFailed(null);
    setDraft(previous => ({ ...previous, [field]: value }));
  }
  async function compare() {
    if (!request) return;
    const token = ++sequence.current, snapshot = current;
    setPending({ source: snapshot, token }); setResponse(null); setFailed(null);
    const valid = () => token === sequence.current && currentRef.current === snapshot;
    try {
      const value = await previewBayesianTargetCurve(request);
      if (valid()) {
        if (value.schema_version !== 1 || !value.preview_only || value.persisted || value.applied_to_recommendations ||
          Object.entries(request.controls).some(([key, v]) => value.request_snapshot.controls[key as keyof typeof request.controls] !== v) ||
          value.request_snapshot.plot_lower !== request.plot_lower || value.request_snapshot.plot_upper !== request.plot_upper ||
          JSON.stringify(value.request_snapshot.assumed_distribution) !== JSON.stringify(request.assumed_distribution)) throw new Error("preview_snapshot_invalid");
        setResponse({ source: snapshot, token, value });
      }
    } catch { if (valid()) setFailed({ source: snapshot, token }); }
    finally { if (valid()) setPending(null); }
  }
  const labels = [text.gaussian, text.linear];
  const points: InteractiveScatterPoint[] = result?.points.flatMap((point, index) => (["gaussian", "linear"] as const).map((field, series) => ({
    id: `${field}:${index}`, seriesId: field, x: point.response_value, y: point[field], marker: series === 0 ? "circle" : "square", markerRadius: 2,
    className: `bo-curve-${field}`, title: labels[series], ariaLabel: `${labels[series]}, ${exact(point.response_value)}, ${exact(point[field])}`,
    details: [{ label: text.value, value: exact(point.response_value) }, { label: text.desirability, value: exact(point[field]) }],
  }))) ?? [];
  return <details className="bo-curve-preview"><summary>{text.title}</summary>
    <p className="notice-box" role="status">{text.preview}</p><p>{text.meaning}</p>
    <label>{text.response}<select aria-label={text.response} value={goal ? selected : ""} onChange={event => {
      const value = event.currentTarget.value; sequence.current += 1; setSelected(value); setPending(null); setResponse(null); setFailed(null);
    }}><option value="">{text.select}</option>{goals.filter(g => g.goal === "match_target").map(g => <option value={g.responseId} key={g.key}>{g.name}</option>)}</select></label>
    {goal ? <>
      <div className="bo-curve-fields">{(["lower", "upper"] as const).map(field => <label key={field}>{text[field]}
        <input inputMode="decimal" readOnly={goal.curve === "gaussian_target"} value={effectiveDraft[field]} onChange={event => change(field, event.currentTarget.value)} /></label>)}</div>
      <label><input type="checkbox" checked={draft.assumed} onChange={event => change("assumed", event.currentTarget.checked)} />{text.assumed}</label>
      {draft.assumed && <><p>{text.assumedMeaning}</p><div className="bo-curve-fields">{(["mean", "sd", "incumbent", "xi"] as const).map(field => <label key={field}>{text[field]}
        <input inputMode="decimal" value={draft[field]} onChange={event => change(field, event.currentTarget.value)} /></label>)}</div></>}
      {!request && <p role="status">{text.invalid}</p>}
      <button type="button" className="secondary-button" disabled={!request || running} onClick={() => void compare()}><ChartLine size={16} aria-hidden="true" />{running ? text.running : text.run}</button>
    </> : <p>{text.empty}</p>}
    {failed?.source === current && failed.token === sequence.current && <p role="alert">{text.failure}</p>}
    {result && <section aria-label={text.title}>
      <p>{text.preview}</p>
      {result.gaussian_underflow_count > 0 && <p className="notice-box notice-warning">{text.underflow}: {result.gaussian_underflow_count}</p>}
      <InteractiveScatterChart chartId="bo-target-curve" sourceKey={current} title={text.title} description={text.meaning}
        points={points} annotations={[]} emptyLabel="-" xLabel={goal?.name || text.value} xUnit={goal?.unit} yLabel={text.desirability}
        xRange={{ min: result.request_snapshot.plot_lower, max: result.request_snapshot.plot_upper }} yRange={{ min: 0, max: 1 }}
        series={(["gaussian", "linear"] as const).map((id, index) => ({ id, label: labels[index], className: `bo-curve-${id}`, connect: "line", pointIds: points.filter(p => p.seriesId === id).map(p => p.id) }))}
        collapsibleDetails />
      <div className="table-wrap"><table className="result-table"><caption>{text.controls}</caption><thead><tr><th>{text.value}</th><th>{text.gaussian}</th><th>{text.linear}</th></tr></thead>
        <tbody>{result.points.filter(p => [result.request_snapshot.controls.lower, result.request_snapshot.controls.target, result.request_snapshot.controls.upper].includes(p.response_value)).map(p =>
          <tr key={p.response_value}><th scope="row">{exact(p.response_value)}</th><td>{exact(p.gaussian)}</td><td>{exact(p.linear)}</td></tr>)}</tbody></table></div>
      {result.metrics.length > 0 && <><p>{text.assumedMeaning}</p><div className="table-wrap"><table className="result-table"><caption>{text.moments}</caption>
        <thead><tr>{[text.policy, text.expected, text.variance, text.ei].map(label => <th key={label}>{label}</th>)}</tr></thead><tbody>{result.metrics.map((row, index) => <tr key={row.policy}>
          <th scope="row">{labels[index]}</th>{(["mean", "variance", "beta_ei"] as const).map(field => <td key={field}>{row[field] === null ? text.unavailable : exact(row[field])}</td>)}</tr>)}</tbody></table></div>
        <details><summary>{text.details}</summary>{result.metrics.map(row => <div key={row.policy}><code>{row.policy}</code>
          <p>{row.unavailable_code || row.ei_unavailable_code || row.ei_distribution}</p><p>{text.tail}: {exact(row.normal_tail_bound)}; {text.integrationError}: {exact(row.integration_error)}</p></div>)}</details></>}
    </section>}
  </details>;
}
