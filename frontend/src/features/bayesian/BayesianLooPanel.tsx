import { useEffect, useRef, useState } from "react";
import { Download, ChartScatter } from "lucide-react";
import { requestBoLoo, type BoLooView } from "../../api/boLoo";
import { triggerBrowserDownload } from "../../api/client";
import { InteractiveScatterChart } from "../../charts/InteractiveScatterChart";
import { paddedNumericRange } from "../../charts/chartScale";
import { useI18n } from "../../i18n/LocaleProvider";
import { boLooMessages } from "../../i18n/boLoo";
import { createLatestRequestGuard } from "../../latestRequest";
import { formatExactNumericValue as exact, formatMeasurement } from "../../statisticalNumberFormat";

interface Source {
  model_id: string; snapshot_sha256: string; config_sha256: string; history_sha256: string;
  source_history_revision_id: string; source_is_current: boolean;
  objective: { responses: { response_id: string; name: string; unit: string | null }[] };
}
interface Props { studyId: string; model: Source; contextKey: string; mixed?: boolean; disabled?: boolean }

export function BayesianLooPanel(props: Props) {
  const source = `${props.contextKey}:${props.studyId}:${props.mixed === true}:${props.model.model_id}:${props.model.snapshot_sha256}:${props.model.history_sha256}:${props.model.config_sha256}`;
  return <LooSourcePanel key={source} {...props} />;
}

function LooSourcePanel({ studyId, model, mixed = false, disabled = false }: Props) {
  const { locale } = useI18n(), text = boLooMessages(locale);
  const [view, setView] = useState<BoLooView | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(false);
  const guard = useRef(createLatestRequestGuard()), controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const lane = guard.current;
    return () => { lane.cancel(); controller.current?.abort(); };
  }, []);
  async function run() {
    const token = guard.current.begin();
    controller.current?.abort(); controller.current = new AbortController();
    setView(null); setError(false); setBusy(true);
    try {
      const result = await requestBoLoo(studyId, model.model_id, model.snapshot_sha256, model.history_sha256, mixed, controller.current.signal);
      if (!guard.current.isCurrent(token)) return;
      if (result.study_id !== studyId || result.model_id !== model.model_id || result.model_sha256 !== model.snapshot_sha256
        || result.history_sha256 !== model.history_sha256 || result.config_sha256 !== model.config_sha256
        || result.source_history_revision_id !== model.source_history_revision_id || result.calculation.model_refit !== false
        || result.calculation.policy !== "fixed_full_fit_parameters_row_loo_v1"
        || result.calculation.responses.map(row => row.response_id).join("|") !== model.objective.responses.map(row => row.response_id).join("|")) throw new Error("invalid_loo_source");
      setView(result);
    } catch {
      if (guard.current.isCurrent(token)) setError(true);
    } finally {
      if (guard.current.isCurrent(token)) setBusy(false);
    }
  }
  return <section aria-label={text.title} className="bo-loo">
    <h4>{text.title}</h4><p>{text.meaning}</p><p>{text.repeats}</p><p>{text.routing}</p>
    <p>{model.source_is_current && view?.source_is_current !== false ? text.current : text.historical}</p>
    <div className="bo-planning-actions">
      <button type="button" className="secondary-button" disabled={disabled || busy} onClick={() => void run()}><ChartScatter size={16} aria-hidden="true" />{text.run}</button>
      {busy && <span role="status">{text.busy}</span>}
      {view && <button type="button" className="secondary-button" onClick={() => triggerBrowserDownload(new Blob([JSON.stringify(view, null, 2)], { type: "application/json" }), `bo-loo-${view.model_id}.json`)}><Download size={16} aria-hidden="true" />{text.download}</button>}
    </div>
    {error && <p role="alert" className="notice-box notice-warning">{text.error}</p>}
    {view && <><p>{text.snapshot}</p><p>{text.formula}</p>
      {view.calculation.responses.map(response => {
        const definition = model.objective.responses.find(item => item.response_id === response.response_id)!;
        const range = paddedNumericRange(response.points.flatMap(point => [point.observed, point.predicted]));
        const predictedRange = paddedNumericRange(response.points.map(point => point.predicted));
        return <section key={response.response_id} aria-label={definition.name}>
          <h5>{definition.name}</h5>
          <dl className="bo-planning-source">
            <div><dt>{text.raw}</dt><dd>{response.raw_observation_count}</dd></div>
            <div><dt>{text.effective}</dt><dd>{response.effective_training_count}</dd></div>
            <div><dt>{text.scored}</dt><dd>{response.n_scored}</dd></div>
            <div><dt>{text.r2}</dt><dd>{response.r_squared === null ? text.constant : formatMeasurement(response.r_squared, locale)}</dd></div>
            <div><dt>{text.rmse}</dt><dd>{formatMeasurement(response.rmse, locale)} {definition.unit}</dd></div>
          </dl>
          <div className="bo-loo-observed"><InteractiveScatterChart chartId={`bo-loo-${response.response_id}`} sourceKey={`${view.model_sha256}:${view.calculation_sha256}:${response.response_id}:observed`}
            title={`${definition.name}: ${text.points}`} description={text.meaning} annotations={[text.formula]} emptyLabel={text.none}
            xLabel={text.predicted} yLabel={text.observed} xUnit={definition.unit} yUnit={definition.unit} xRange={range} yRange={range}
            referenceLines={[{ label: text.identity, x1: range.min, x2: range.max, y1: range.min, y2: range.max }]}
            points={response.points.map(point => ({ id: point.trial_id, x: point.predicted, y: point.observed, className: "bo-planning-profile-mean", title: `${text.observation} ${point.observation_index}`,
              ariaLabel: `${text.observation} ${point.observation_index}: ${text.observed} ${exact(point.observed)}, ${text.predicted} ${exact(point.predicted)}`,
              details: [{ label: text.trial, value: point.trial_id }, { label: text.observation, value: String(point.observation_index) }, { label: text.observed, value: exact(point.observed) }, { label: text.predicted, value: exact(point.predicted) }, { label: text.residual, value: exact(point.residual) }],
            }))} /></div>
          <div className="bo-loo-residual"><h6>{definition.name}: {text.residualPoints}</h6>
            <InteractiveScatterChart chartId={`bo-loo-residual-${response.response_id}`} sourceKey={`${view.model_sha256}:${view.calculation_sha256}:${response.response_id}:residual`}
              title={`${definition.name}: ${text.residualPoints}`} description={text.residualMeaning} annotations={[text.residualMeaning]} emptyLabel={text.none}
              xLabel={text.predicted} yLabel={text.residual} xUnit={definition.unit} yUnit={definition.unit} xRange={predictedRange}
              yRange={paddedNumericRange([0, ...response.points.map(point => point.residual)])}
              referenceLines={[{ label: text.zeroResidual, x1: predictedRange.min, x2: predictedRange.max, y1: 0, y2: 0 }]}
              points={response.points.map(point => ({ id: point.trial_id, x: point.predicted, y: point.residual, className: "bo-planning-profile-mean", title: `${text.observation} ${point.observation_index}`,
                ariaLabel: `${text.observation} ${point.observation_index}: ${text.predicted} ${exact(point.predicted)}, ${text.residual} ${exact(point.residual)}`,
                details: [{ label: text.trial, value: point.trial_id }, { label: text.observation, value: String(point.observation_index) }, { label: text.observed, value: exact(point.observed) }, { label: text.predicted, value: exact(point.predicted) }, { label: text.residual, value: exact(point.residual) }],
              }))} />
          </div>
          <details><summary>{text.rows}</summary><div className="table-wrap"><table className="result-table"><thead><tr><th>{text.observation}</th><th>{text.observed}</th><th>{text.predicted}</th><th>{text.residual}</th></tr></thead><tbody>
            {response.points.map(point => <tr key={point.trial_id}><th scope="row">{point.observation_index}</th><td>{exact(point.observed)}</td><td>{exact(point.predicted)}</td><td>{exact(point.residual)}</td></tr>)}
          </tbody></table></div></details>
        </section>;
      })}
      <details><summary>{text.source}</summary><dl className="bo-planning-source">
        <div><dt>model_id</dt><dd>{view.model_id}</dd></div><div><dt>model_sha256</dt><dd>{view.model_sha256}</dd></div>
        <div><dt>history_sha256</dt><dd>{view.history_sha256}</dd></div><div><dt>calculation_sha256</dt><dd>{view.calculation_sha256}</dd></div>
      </dl></details>
    </>}
  </section>;
}
