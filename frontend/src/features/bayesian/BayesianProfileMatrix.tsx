import { useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { InteractiveScatterChart } from "../../charts/InteractiveScatterChart";
import { paddedNumericRange } from "../../charts/chartScale";
import { useI18n } from "../../i18n/LocaleProvider";
import { planningMessages } from "../../i18n/boPlanning";
import { boViewMessages } from "../../i18n/boViews";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { categoryDisplayTicks } from "./bayesianProgress";
import { BayesianProfileLevelMap } from "./BayesianProfileGrid";
import type { ProfileMatrixRow, ProfileMatrixView } from "./boProfileMatrix";
type Metric = "mean_raw" | "latent_standard_deviation_raw" | "predictive_standard_deviation_raw";

export function BayesianProfileMatrix({ view }: { view: ProfileMatrixView }) {
  const { locale } = useI18n(), text = planningMessages(locale);
  const viewText = boViewMessages(locale);
  const [metric, setMetric] = useState<Metric>("mean_raw"), [page, setPage] = useState(0);
  const at = Math.min(page, Math.max(0, Math.ceil(view.axes.length / 2) - 1)), axes = view.axes.slice(at * 2, at * 2 + 2);
  const quantities = [...view.responses.map(response => ({ key: `response:${response.response_id}`, response, name: response.name, unit: response.unit })), { key: "composite", response: null, name: text.desirability, unit: null }];
  const metricName = metric === "mean_raw" ? text.mean : metric === "latent_standard_deviation_raw" ? text.latent : text.predictive;
  return <section aria-label={text.profileMatrix} className="bo-profile-matrix">
    <h5>{text.profileMatrix}</h5><p>{text.model}: <code>{view.modelId}</code></p><p>{text.modelHash}: <code>{view.modelHash}</code></p><p>{text.history}: <code>{view.historyHash}</code></p>
    <h6>{text.appliedHolds}</h6><dl className="bo-planning-source">{view.axes.map(axis => <div key={axis.factor_id}><dt>{axis.name}{axis.unit ? ` (${axis.unit})` : ""}</dt><dd>{String(view.holds[axis.factor_id])}</dd></div>)}</dl>
    <div className="bo-profile-matrix-controls"><label>{text.profileMetric}<select aria-label={text.profileMetric} value={metric} onChange={event => setMetric(event.currentTarget.value as Metric)}><option value="mean_raw">{text.mean}</option><option value="latent_standard_deviation_raw">{text.latent}</option><option value="predictive_standard_deviation_raw">{text.predictive}</option></select></label>
      <div className="bo-profile-matrix-pagination"><button type="button" className="secondary-button bo-planning-icon" title={text.previous} aria-label={text.previous} disabled={at === 0} onClick={() => setPage(at - 1)}><ArrowLeft size={16} aria-hidden="true" /></button><span>{at * 2 + 1}-{Math.min(at * 2 + 2, view.axes.length)} / {view.axes.length}</span><button type="button" className="secondary-button bo-planning-icon" title={text.next} aria-label={text.next} disabled={(at + 1) * 2 >= view.axes.length} onClick={() => setPage(at + 1)}><ArrowRight size={16} aria-hidden="true" /></button></div>
    </div>
    {view.axes.some(axis => axis.rows.some(row => !row.constraints_satisfied)) && <p className="notice-box notice-warning">{text.profileConstraintMeaning}</p>}
    {quantities.map(quantity => {
      const value = (row: ProfileMatrixRow) => quantity.response ? row.response_predictions.find(item => item.response_id === quantity.response.response_id)![metric] : row.desirability_moments.mean;
      const range = paddedNumericRange(view.axes.flatMap(axis => axis.rows.map(value)));
      return <section key={quantity.key} data-profile-kind={quantity.response ? "response" : "composite"} data-response-id={quantity.response?.response_id}><h6>{quantity.name}{quantity.unit ? ` (${quantity.unit})` : ""}: {quantity.response ? metricName : text.expected}</h6>
        <div className="bo-profile-matrix-row">{axes.map(axis => {
          const pathMeaning = axis.pathPolicy === "excess_above_lower" ? viewText.excess : axis.pathPolicy === "deficit_below_upper" ? viewText.deficit : viewText.process;
          const meaning = axis.pathPolicy && axis.pathPolicy !== "held_mixture_process_axis_v1" ? `${viewText.coVary} ${pathMeaning}` : text.profileMeaning;
          if (axis.unavailableReason) return <div key={axis.factor_id} className="bo-profile-grid-item"><h6>{axis.name}</h6><p>{axis.unavailableReason === "fixed_component" ? viewText.fixedComponent : axis.unavailableReason === "zero_balancing_mass" ? viewText.zeroMass : viewText.pathUnavailable}</p><p>{pathMeaning}</p><code>{axis.unavailableReason}</code></div>;
          const ticks = axis.category ? axis.rows.map((row, index) => ({ value: index, label: String(row.actual_coordinates[axis.factor_id]) })) : undefined;
          const points = axis.rows.map((row, index) => {
            const coordinate = row.actual_coordinates[axis.factor_id], label = typeof coordinate === "number" ? exact(coordinate) : coordinate, y = value(row), constraint = row.constraints_satisfied ? text.constraintsSatisfied : text.constraintFailure;
            return { id: row.row_id, x: axis.category ? index : Number(coordinate), y, title: label, ariaLabel: `${axis.name}: ${label}, ${quantity.name}: ${exact(y)}, ${constraint}`, marker: row.constraints_satisfied ? "circle" as const : "diamond" as const, warning: !row.constraints_satisfied, className: "bo-planning-profile-mean", details: [{ label: axis.name, value: label }, { label: quantity.name, value: `${exact(y)}${quantity.unit ? ` ${quantity.unit}` : ""}` }, { label: text.constraintStatus, value: constraint }, ...view.axes.filter(other => other.factor_id !== axis.factor_id).map(other => ({ label: `${viewText.actualCoordinates}: ${other.name}`, value: typeof row.actual_coordinates[other.factor_id] === "number" ? exact(row.actual_coordinates[other.factor_id] as number) : String(row.actual_coordinates[other.factor_id]) }))] };
          });
          return <div key={axis.factor_id} className="bo-profile-grid-item"><InteractiveScatterChart annotations={[meaning]} chartId={`bo-matrix-${axis.factor_id}-${quantity.key}`} sourceKey={`${view.modelHash}:${JSON.stringify(view.holds)}:${axis.factor_id}:${quantity.key}:${metric}`} title={axis.name} description={meaning} emptyLabel={text.none} points={points} connectPoints={axis.category ? undefined : "line"} xLabel={axis.name} xUnit={axis.unit} xRange={axis.range && axis.range.min < axis.range.max ? axis.range : paddedNumericRange(points.map(point => point.x))} xTicks={categoryDisplayTicks(ticks)} yLabel={quantity.name} yUnit={quantity.unit} yRange={range} collapsibleDetails />{ticks && <BayesianProfileLevelMap ticks={ticks} />}</div>;
        })}</div>
      </section>;
    })}
  </section>;
}
