import type { DesirabilityFitCalculation, DesirabilityCurveCalculation } from "../../api/types/bayesianDesirability";
import { InteractiveScatterChart, type InteractiveScatterPoint } from "../../charts/InteractiveScatterChart";
import { useI18n } from "../../i18n/LocaleProvider";
import { desirabilityMessages } from "../../i18n/boDesirability";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";

export function BayesianFitDiagnostics({ calculation, sourceKey }: { calculation: DesirabilityFitCalculation | DesirabilityCurveCalculation; sourceKey: string }) {
  const { locale } = useI18n();
  const text = desirabilityMessages(locale);
  if (!calculation.shared_model.response_models.some(r => r.model.schema_version === 5)) return null;
  return <section className="bo-fit-diagnostics" aria-label={text.fitTitle}>
    <h5>{text.fitTitle}</h5><p>{text.fitMeaning}</p>
    {calculation.shared_model.response_models.map(({ response_id, model }) => {
      if (model.schema_version !== 5) return null;
      const response = calculation.objective.responses.find(r => r.response_id === response_id)!;
      const evidence = model.fit_diagnostics;
      const starts = model.optimizer.starts;
      const labels = [text.initialLml, text.bestLml, text.finalLml];
      const values = [evidence.start_initial_negative_log_likelihoods,
        evidence.start_best_evaluations.map(s => s.negative_log_likelihood), starts.map(s => s.negative_log_likelihood)];
      const points: InteractiveScatterPoint[] = values.flatMap((series, s) => series.map((value, i) => ({
        id: `${s}:${i}`, seriesId: String(s), x: i + 1, y: -value,
        className: `bo-fit-point bo-fit-series-${s}`, marker: s === 0 ? "circle" : s === 1 ? "square" : "diamond",
        title: `${labels[s]}: ${text.start} ${i + 1}`, ariaLabel: `${labels[s]}, ${text.start} ${i + 1}, ${exact(-value)}`,
        details: [{ label: text.start, value: String(i + 1) }, { label: labels[s], value: exact(-value) }],
      })));
      const yValues = [...points.map(p => p.y), model.log_marginal_likelihood];
      return <section key={response_id} className="bo-fit-response" aria-label={`${text.fitTitle}: ${response.name}`}>
        <h6>{response.name}</h6>
        <dl className="bo-desirability-summary">
          <div><dt>{text.selectedLml}</dt><dd>{exact(model.log_marginal_likelihood)}</dd></div>
          <div><dt>{text.fitEvaluations}</dt><dd>{model.optimizer.evaluations} / {model.optimizer.max_evaluations}</dd></div>
          <div><dt>{text.deterministicStarts}</dt><dd>{evidence.deterministic_start_count}</dd></div>
          <div><dt>{text.randomRestarts}</dt><dd>{model.optimizer.restarts}</dd></div>
        </dl>
        <InteractiveScatterChart chartId={`bo-fit-${response_id}`} sourceKey={`${sourceKey}:${response_id}`}
          title={`${text.fitTitle}: ${response.name}`} description={text.fitMeaning} emptyLabel="-" annotations={[]}
          points={points} xLabel={text.start} yLabel="LML" xRange={{ min: 0.5, max: starts.length + 0.5 }}
          yRange={{ min: Math.min(...yValues), max: Math.max(...yValues) }}
          xTicks={starts.map((_, i) => ({ value: i + 1, label: String(i + 1) }))}
          series={labels.map((label, i) => ({ id: String(i), label, className: `bo-fit-series-${i}`, pointIds: points.filter(p => p.seriesId === String(i)).map(p => p.id), connect: "none" }))}
          referenceLines={[{ label: text.selectedLml, x1: 0.5, x2: starts.length + 0.5, y1: model.log_marginal_likelihood, y2: model.log_marginal_likelihood }]}
          collapsibleDetails />
        <div className="table-wrap"><table className="result-table"><caption>{text.fitTitle}: {response.name}</caption>
          <thead><tr>{[text.start, ...labels, text.fitEvaluations, text.converged].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
          <tbody>{starts.map((s, i) => <tr key={i}><th scope="row">{i + 1}</th>{values.map((v, j) => <td key={j}>{exact(-v[i])}</td>)}<td>{s.evaluations}</td><td>{s.success ? text.yes : text.no}</td></tr>)}</tbody>
        </table></div>
        <details><summary>{text.boundaryHits}</summary>{evidence.bound_hits.length ? <ul>{evidence.bound_hits.map((hit, i) => <li key={i}>
          {hit.parameter === "signal_amplitude" ? text.signalAmplitude : hit.parameter === "length_scale" ? `${text.lengthScale} ${hit.factor_index! + 1}` : text.measurementVariance}: {hit.side === "lower" ? text.lowerBound : text.upperBound} = {exact(hit.value)}
        </li>)}</ul> : <p>{text.noBoundHits}</p>}</details>
        <details><summary>{text.fitScreening}</summary><div className="table-wrap"><table className="result-table"><thead><tr><th>{text.start}</th><th>{text.logParameters}</th><th>LML</th></tr></thead>
          <tbody>{evidence.screening.map((row, i) => <tr key={i}><th scope="row">{i + 1}</th><td>{row.log_parameters.map(v => exact(v)).join(", ")}</td><td>{exact(-row.negative_log_likelihood)}</td></tr>)}</tbody>
        </table></div><code>{evidence.policy}</code></details>
      </section>;
    })}
  </section>;
}
