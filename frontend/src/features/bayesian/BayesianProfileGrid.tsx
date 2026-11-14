import { InteractiveScatterChart } from "../../charts/InteractiveScatterChart";
import { paddedNumericRange } from "../../charts/chartScale";
import { useI18n } from "../../i18n/LocaleProvider";
import { planningMessages } from "../../i18n/boPlanning";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { categoryDisplayTicks } from "./bayesianProgress";

interface ProfileRow {
  row_id: string;
  actual_coordinates: Record<string, string | number>;
  response_predictions: { response_id: string; mean_raw: number }[];
  desirability_moments: { mean: number };
  constraints_satisfied: boolean;
}
interface Props {
  sourceKey: string;
  axis: { factor_id: string; name: string; unit: string | null; category: boolean; meaning?: string; range?: { min: number; max: number } };
  responses: { response_id: string; name: string; unit: string | null }[];
  rows: ProfileRow[];
}

// Display only: rows belong to the single already-evaluated axis and its applied holds.
export function BayesianProfileGrid({ sourceKey, axis, responses, rows }: Props) {
  const { locale } = useI18n(), text = planningMessages(locale);
  const categoryTicks = axis.category ? rows.map((row, index) => ({ value: index, label: String(row.actual_coordinates[axis.factor_id]) })) : undefined;
  const quantities = [
    ...responses.map(response => ({ key: `response:${response.response_id}`, response, name: response.name, unit: response.unit })),
    { key: "composite", response: null, name: text.desirability, unit: null },
  ];
  return <section aria-label={text.profileGrid}>
    <h5>{text.profileGrid}</h5>
    {rows.some(row => !row.constraints_satisfied) && <p className="notice-box notice-warning">{text.profileConstraintMeaning}</p>}
    <div className="bo-profile-grid">{quantities.map(quantity => {
      const points = rows.map((row, index) => {
        const coordinate = row.actual_coordinates[axis.factor_id], coordinateLabel = typeof coordinate === "string" ? coordinate : exact(coordinate);
        const value = quantity.response ? row.response_predictions.find(prediction => prediction.response_id === quantity.response.response_id)?.mean_raw ?? NaN : row.desirability_moments.mean;
        const label = quantity.response ? text.mean : text.expected;
        const constraint = row.constraints_satisfied ? text.constraintsSatisfied : text.constraintFailure;
        return { id: row.row_id, x: axis.category ? index : Number(coordinate), y: value, title: coordinateLabel,
          ariaLabel: `${axis.name}: ${coordinateLabel}, ${quantity.name}: ${exact(value)}${quantity.unit ? ` ${quantity.unit}` : ""}, ${text.constraintStatus}: ${constraint}`,
          marker: row.constraints_satisfied ? "circle" as const : "diamond" as const,
          warning: !row.constraints_satisfied,
          className: "bo-planning-profile-mean", details: [{ label: axis.name, value: coordinateLabel }, { label: `${quantity.name}: ${label}`, value: `${exact(value)}${quantity.unit ? ` ${quantity.unit}` : ""}` }, { label: text.constraintStatus, value: constraint }] };
      });
      return <div className="bo-profile-grid-item" key={quantity.key} data-profile-kind={quantity.response ? "response" : "composite"} data-response-id={quantity.response?.response_id}>
        <h6>{quantity.name}{quantity.unit ? ` (${quantity.unit})` : ""}</h6>
        <InteractiveScatterChart chartId={`bo-profile-grid-${axis.factor_id}-${quantity.key}`} sourceKey={`${sourceKey}:${axis.factor_id}:${quantity.key}:mean`}
          title={`${quantity.name}: ${quantity.response ? text.mean : text.expected}`} description={text.profileMeaning} annotations={axis.meaning ? [axis.meaning] : []} emptyLabel={text.none}
          points={points} connectPoints={axis.category ? undefined : "line"} xLabel={axis.name} xUnit={axis.unit} xRange={axis.range ?? paddedNumericRange(points.map(point => point.x))}
          xTicks={categoryDisplayTicks(categoryTicks)}
          yLabel={quantity.response ? text.mean : text.expected} yUnit={quantity.unit} yRange={paddedNumericRange(points.map(point => point.y))} collapsibleDetails />
      </div>;
    })}</div>
    {categoryTicks && <BayesianProfileLevelMap ticks={categoryTicks} />}
  </section>;
}

export function BayesianProfileLevelMap({ ticks }: { ticks: { value: number; label: string }[] }) {
  const { locale } = useI18n(), text = planningMessages(locale);
  return <details className="bo-profile-levels"><summary>{text.profileLevels}</summary><dl>{ticks.map(tick =>
    <div key={tick.value}><dt>#{tick.value + 1}</dt><dd>{tick.label}</dd></div>)}</dl></details>;
}
