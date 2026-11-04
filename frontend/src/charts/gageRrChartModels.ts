import type { GageRrPlotBundle, GageRrResult } from "../api/types/analysisResultsQuality";
import { t } from "../i18n/translate";
import { formatExactNumericValue } from "../statisticalNumberFormat";
import { paddedNumericRange } from "./chartScale";
import { STANDARD_CHART_LAYOUT } from "./chartLayout";
import type { ChartSeries, InteractiveScatterPoint, ScatterReferenceLine } from "./InteractiveScatterChart";
import type { SummaryBar, SummaryBox, SummaryDot } from "./InteractiveSummaryChart";

type Translate = typeof t;
export const GAGE_PART_PAGE_SIZE = 10;
export const GAGE_OPERATOR_PAGE_SIZE = 3;
const components = ["total_gage_rr", "repeatability", "reproducibility", "part_to_part"] as const;
const shortKeys = ["gage.charts.shortTotal", "gage.charts.shortRepeat", "gage.charts.shortReprod", "gage.charts.shortPart"] as const;
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
export const operatorClass = (index: number) => `gage-operator-${index % 6}`;
export const operatorMarker = (index: number) => (["circle", "square", "diamond"] as const)[index % 3];
const record = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const records = (value: unknown): value is Record<string, unknown>[] => Array.isArray(value) && value.every(record);
const optionalNumber = (value: unknown) => value === null || finite(value);
const integer = (value: unknown): value is number => finite(value) && Number.isInteger(value) && value >= 0;
// Match Python str.strip's whitespace set without treating a preserved BOM as whitespace.
const partEdgeWhitespace = (code: number) => (code >= 9 && code <= 13) || (code >= 28 && code <= 32)
  || (code >= 0x2000 && code <= 0x200a) || [0x85, 0xa0, 0x1680, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000].includes(code);
const canonicalPartId = (value: unknown): value is string => typeof value === "string" && value.length > 0
  && !partEdgeWhitespace(value.charCodeAt(0)) && !partEdgeWhitespace(value.charCodeAt(value.length - 1));

// API validation owns the full statistical contract. This display guard keeps malformed
// or incomplete historical graph data from taking down the independent ANOVA tables.
export function gagePlotState(result: GageRrResult): "legacy" | "valid" | "invalid" {
  if (result.schema_version < 3) return "legacy";
  const b: unknown = result.plot_bundle;
  if (!record(b) || !((result.schema_version === 3 && b.schema_version === 1) || (result.schema_version === 4 && b.schema_version === 2))
    || !record(b.measurement) || !record(b.counts) || !record(b.measurement_range) || !record(b.calculation_metadata)) return "invalid";
  const c = b.counts;
  if (typeof b.measurement.display_name !== "string" || !(b.measurement.unit === null || typeof b.measurement.unit === "string")
    || !["n_total", "n_used", "part_count", "operator_count", "replicate_count", "displayed_raw_point_count", "raw_point_limit"].every((key) => integer(c[key]))) return "invalid";
  const partCount = c.part_count as number, operatorCount = c.operator_count as number;
  if (partCount < 2 || operatorCount < 2 || c.n_used !== result.sample.n_used
    || !finite(b.measurement_range.minimum) || !finite(b.measurement_range.maximum) || b.measurement_range.minimum > b.measurement_range.maximum) return "invalid";
  if (!records(b.parts) || !records(b.operators) || !records(b.cells) || b.parts.length !== partCount || b.operators.length !== operatorCount) return "invalid";
  if (b.parts.some((part, index) => part.part_index !== index || !optionalNumber(part.mean) || !integer(part.n))
    || b.operators.some((operator, index) => operator.operator_index !== index || !optionalNumber(operator.mean) || !integer(operator.n))) return "invalid";
  const metadata = b.calculation_metadata;
  if (metadata.operator_order !== "sorted_full_stripped_identity") return "invalid";
  if (b.schema_version === 2) {
    if (metadata.policy_version !== "gage_rr_six_panel_v2" || metadata.part_order !== "natural_ascii_digit_runs_full_identity_v1"
      || metadata.identifier_policy !== "part_ids_preserved_operator_replicate_redacted"
      || b.parts.some((part) => !canonicalPartId(part.part_id))
      || new Set(b.parts.map((part) => part.part_id)).size !== b.parts.length) return "invalid";
  } else if (metadata.policy_version !== "gage_rr_six_panel_v1" || metadata.part_order !== "sorted_full_stripped_identity"
    || metadata.identifier_policy !== "zero_based_indices_original_labels_redacted" || b.parts.some((part) => "part_id" in part)) return "invalid";
  const cellIdentity = (item: Record<string, unknown>) => integer(item.part_index) && item.part_index < partCount && integer(item.operator_index) && item.operator_index < operatorCount;
  const cellRows = (items: unknown, valueKeys: string[], available: boolean) => records(items) && items.length === partCount * operatorCount
    && new Set(items.map((item) => `${String(item.part_index)}:${String(item.operator_index)}`)).size === items.length
    && items.every((item) => cellIdentity(item) && integer(item.n) && valueKeys.every((key) => available ? finite(item[key]) : optionalNumber(item[key])));
  if (!cellRows(b.cells, ["mean", "range", "sample_sd"], false)) return "invalid";
  const views = [b.components, b.dispersion, b.xbar, b.response_by_part, b.response_by_operator, b.interaction];
  if (!views.every((view) => record(view) && (view.status === "available" || view.status === "unavailable")
    && (view.unavailable_reason === null || typeof view.unavailable_reason === "string"))) return "invalid";
  const componentsView = b.components as Record<string, unknown>;
  if (!records(componentsView.items) || componentsView.items.length !== 4
    || new Set(componentsView.items.map((item) => item.component)).size !== 4
    || componentsView.items.some((item) => !components.includes(item.component as typeof components[number])
      || [item.final_variance, item.standard_deviation, item.percent_contribution, item.percent_study_variation].some((value) => value !== null && (!finite(value) || value < 0)))) return "invalid";
  for (const key of ["dispersion", "xbar"] as const) {
    const view = b[key] as Record<string, unknown>;
    if (!cellRows(view.points, ["value"], view.status === "available")
      || !["center", "lower_limit", "upper_limit"].every((name) => view.status === "available" ? finite(view[name]) : optionalNumber(view[name]))) return "invalid";
  }
  const dispersion = b.dispersion as Record<string, unknown>;
  if (!record(dispersion.constants) || !Object.values(dispersion.constants).every(optionalNumber)
    || !Array.isArray(dispersion.warning_codes) || !dispersion.warning_codes.every((code) => typeof code === "string")
    || !["range", "sample_sd"].includes(dispersion.statistic as string)) return "invalid";
  const rawPoint = (item: Record<string, unknown>) => cellIdentity(item) && integer(item.source_row_number) && finite(item.value);
  const raw = (b.response_by_part as Record<string, unknown>).points;
  if (!records(raw) || !raw.every(rawPoint) || raw.length !== c.displayed_raw_point_count) return "invalid";
  const operatorView = b.response_by_operator as Record<string, unknown>;
  const boxes = operatorView.boxes;
  if (!records(boxes) || boxes.length !== operatorCount || boxes.some((box, index) => box.operator_index !== index || !integer(box.n)
    || !["mean", "q1", "median", "q3", "lower_fence", "upper_fence", "lower_whisker", "upper_whisker"].every((key) => operatorView.status === "available" ? finite(box[key]) : optionalNumber(box[key]))
    || !records(box.outliers) || !box.outliers.every(rawPoint) || !integer(box.outlier_count) || !integer(box.displayed_outlier_count))) return "invalid";
  const interaction = b.interaction as Record<string, unknown>;
  if (!cellRows(interaction.points, ["mean"], interaction.status === "available") || typeof interaction.interaction_pooled !== "boolean") return "invalid";
  return "valid";
}

export function componentChart(result: GageRrResult, translate: Translate) {
  const bars: SummaryBar[] = [];
  components.forEach((component, category) => {
    const item = result.schema_version >= 3
      ? (result.plot_bundle?.components.status === "available" ? result.plot_bundle.components.items.find((entry) => entry.component === component) : undefined)
      : result.variance_components[component];
    if (!item) return;
    const title = translate(`gage.charts.${component}`);
    const details = [
      { label: translate("gage.charts.contribution"), value: formatExactNumericValue(item.percent_contribution) + "%" },
      { label: translate("gage.charts.studyVariation"), value: formatExactNumericValue(item.percent_study_variation) + "%" },
      { label: translate("gage.charts.variance"), value: formatExactNumericValue(item.final_variance) },
      { label: translate("gage.charts.standardDeviation"), value: formatExactNumericValue(item.standard_deviation) },
      { label: translate("gage.charts.policy"), value: translate(result.interaction_selection?.pooled ? "gage.charts.pooled" : "gage.charts.retain") },
    ];
    [item.percent_contribution, item.percent_study_variation].forEach((value, series) => {
      if (finite(value) && value >= 0) bars.push({ id: `${component}:${series}`, title, details, category, series, value, className: `gage-component-series-${series}` });
    });
  });
  return { bars, categories: shortKeys.map((key, value) => ({ value, label: translate(key) })),
    yRange: { min: 0, max: Math.max(1, ...bars.map((bar) => bar.value)) * 1.05 } };
}

export function gageChartModels(bundle: GageRrPlotBundle, partPage: number, operatorPage: number, translate: Translate) {
  const parts = bundle.parts.slice(partPage * GAGE_PART_PAGE_SIZE, (partPage + 1) * GAGE_PART_PAGE_SIZE);
  const operators = bundle.operators.slice(operatorPage * GAGE_OPERATOR_PAGE_SIZE, (operatorPage + 1) * GAGE_OPERATOR_PAGE_SIZE);
  const partPosition = new Map(parts.map((part, index) => [part.part_index, index]));
  const operatorPosition = new Map(operators.map((operator, index) => [operator.operator_index, index]));
  const partLabels = new Map(bundle.schema_version === 2
    ? bundle.parts.map((part) => [part.part_index, part.part_id] as const)
    : bundle.parts.map((part) => [part.part_index, translate("gage.charts.displayIndex", { index: part.part_index + 1 })] as const));
  const partLabel = (index: number) => {
    const label = partLabels.get(index);
    if (label === undefined) throw new Error("Invalid stored Gage part reference");
    return label;
  };
  const partIdentityLabel = translate(bundle.schema_version === 2 ? "gage.charts.partId" : "gage.charts.displayNumber");
  const partDetails = (index: number) => [{ label: partIdentityLabel, value: partLabel(index) }];
  const tickLabel = (index: number) => {
    const label = Array.from(partLabel(index));
    return label.length > 10 ? label.slice(0, 9).join("") + "…" : label.join("");
  };
  const operatorLabel = (index: number) => translate("gage.charts.operator", { index: index + 1 });
  const xRange = { min: -0.5, max: Math.max(0.5, parts.length - 0.5) };
  const yRange = paddedNumericRange([bundle.measurement_range.minimum, bundle.measurement_range.maximum]);
  const shortPartIds = bundle.schema_version === 2 && parts.every((part) => Array.from(partLabel(part.part_index)).length <= 3);
  const partTicks = parts.filter((_, index) => shortPartIds || parts.length <= 5 || index % 3 === 0 || index === parts.length - 1)
    .map((part) => ({ value: partPosition.get(part.part_index)!, label: tickLabel(part.part_index) }));
  const point = (id: string, part: number, operator: number, x: number, y: number, extra: { label: string; value: string }[] = []): InteractiveScatterPoint => {
    const title = `${partLabel(part)} / ${operatorLabel(operator)}`;
    const details = [...partDetails(part), { label: translate("gage.charts.value"), value: formatExactNumericValue(y) }, ...extra];
    return { id, title, ariaLabel: `${title}; ${details.map((item) => `${item.label}: ${item.value}`).join("; ")}`,
      details, x, y, className: operatorClass(operator), marker: operatorMarker(operator), seriesId: `operator:${operator}` };
  };
  const seriesFor = (points: InteractiveScatterPoint[], connect: "line" | "none" = "line"): ChartSeries[] => operators.map(({ operator_index: index }) => ({
    id: `operator:${index}`, label: operatorLabel(index), className: operatorClass(index),
    pointIds: points.filter((item) => item.seriesId === `operator:${index}`).map((item) => item.id), connect,
  }));
  const included = (item: { part_index: number; operator_index: number }) => partPosition.has(item.part_index) && operatorPosition.has(item.operator_index);
  const measurementPoints = bundle.response_by_part.points.filter(included).map((item) => point(`raw:${item.source_row_number}`, item.part_index, item.operator_index,
    partPosition.get(item.part_index)! + ((item.source_row_number * 17 % 31) / 30 - 0.5) * 0.44, item.value,
    [{ label: translate("gage.charts.sourceRow"), value: String(item.source_row_number) }]));
  const meanPoints: InteractiveScatterPoint[] = parts.flatMap((part) => finite(part.mean) ? [{
    id: `part-mean:${part.part_index}`, title: partLabel(part.part_index), ariaLabel: `${partLabel(part.part_index)}; ${translate("gage.charts.partMean")}: ${formatExactNumericValue(part.mean)}`,
    details: [...partDetails(part.part_index), { label: translate("gage.charts.partMean"), value: formatExactNumericValue(part.mean) }, { label: translate("gage.charts.count"), value: String(part.n) }],
    x: partPosition.get(part.part_index)!, y: part.mean, className: "gage-part-mean", marker: "diamond", seriesId: "part-means",
  }] : []);
  // Keep raw markers above summaries; earlier source rows own overlapping raw hits.
  const responsePart = { points: [...meanPoints, ...[...measurementPoints].reverse()], series: [...seriesFor(measurementPoints, "none"),
    { id: "part-means", label: translate("gage.charts.partMean"), className: "gage-part-mean", pointIds: meanPoints.map((item) => item.id), connect: "line" as const }] };
  const interactionPoints = bundle.interaction.points.filter(included).flatMap((item) => finite(item.mean)
    ? [point(`interaction:${item.operator_index}:${item.part_index}`, item.part_index, item.operator_index, partPosition.get(item.part_index)!, item.mean)] : []);
  const sectionWidth = parts.length + 1;
  const sectionRange = { min: -0.5, max: Math.max(0.5, operators.length * sectionWidth - 1.5) };
  const sections = operators.map((operator, index) => ({ id: `operator:${operator.operator_index}`, label: operatorLabel(operator.operator_index), start: index * sectionWidth - 0.5, end: index * sectionWidth + parts.length - 0.5 }));
  const sectionPartTicks = partTicks.filter((tick) => parts.length <= 5 || tick.value % 3 === 0 || tick.value === parts.length - 1);
  const sectionTicks = operators.flatMap((_, index) => sectionPartTicks.map((tick) => ({ ...tick, value: tick.value + index * sectionWidth })));
  const limitsChart = (kind: "dispersion" | "xbar") => {
    const view = bundle[kind];
    let minimum = Infinity, maximum = -Infinity;
    for (const item of view.points) if (finite(item.value)) { minimum = Math.min(minimum, item.value); maximum = Math.max(maximum, item.value); }
    for (const value of [view.lower_limit, view.center, view.upper_limit]) if (finite(value)) { minimum = Math.min(minimum, value); maximum = Math.max(maximum, value); }
    const points = view.points.filter(included).flatMap((item) => finite(item.value) ? [point(`${kind}:${item.operator_index}:${item.part_index}`,
      item.part_index, item.operator_index, operatorPosition.get(item.operator_index)! * sectionWidth + partPosition.get(item.part_index)!, item.value,
      kind === "xbar" ? [{ label: translate("gage.charts.xbar"), value: translate("outside_repeatability_limits" in item && item.outside_repeatability_limits ? "gage.charts.outside" : "gage.charts.inside") }] : [])] : []);
    const referenceLines: ScatterReferenceLine[] = (["lower_limit", "center", "upper_limit"] as const).flatMap((key, index) => finite(view[key]) ? [{
      label: `${translate((["gage.charts.lcl", "gage.charts.cl", "gage.charts.ucl"] as const)[index])}: ${formatExactNumericValue(view[key])}`,
      x1: sectionRange.min, x2: sectionRange.max, y1: view[key], y2: view[key], className: index === 1 ? "gage-center-line" : "gage-limit-line",
    }] : []);
    return { points, referenceLines, series: seriesFor(points), xRange: sectionRange, xTicks: sectionTicks, xSections: sections,
      layout: { ...STANDARD_CHART_LAYOUT, height: 344, plot: { ...STANDARD_CHART_LAYOUT.plot, top: 48 } },
      yRange: paddedNumericRange([minimum, maximum]) };
  };
  const boxes: SummaryBox[] = bundle.response_by_operator.boxes.filter((box) => operatorPosition.has(box.operator_index)).flatMap((box) => {
    if (![box.q1, box.median, box.q3, box.mean, box.lower_whisker, box.upper_whisker].every(finite)) return [];
    return [{ id: `box:${box.operator_index}`, title: operatorLabel(box.operator_index), category: operatorPosition.get(box.operator_index)!,
      q1: box.q1!, median: box.median!, q3: box.q3!, mean: box.mean!, lowerWhisker: box.lower_whisker!, upperWhisker: box.upper_whisker!, className: operatorClass(box.operator_index),
      details: (["q1", "median", "q3", "mean", "lower_whisker", "upper_whisker", "outlier_count", "n"] as const).map((key, index) => ({
        label: translate((["gage.charts.q1", "gage.charts.median", "gage.charts.q3", "gage.charts.mean", "gage.charts.lowerWhisker", "gage.charts.upperWhisker", "gage.charts.outliers", "gage.charts.count"] as const)[index]), value: formatExactNumericValue(box[key]),
      })) }];
  });
  const dots: SummaryDot[] = bundle.response_by_operator.boxes.filter((box) => operatorPosition.has(box.operator_index)).flatMap((box) => {
    const raw = box.n <= 40 ? bundle.response_by_part.points.filter((item) => item.operator_index === box.operator_index) : box.outliers;
    return raw.map((item) => ({ id: `box-dot:${item.source_row_number}`, title: `${partLabel(item.part_index)} / ${operatorLabel(item.operator_index)}`,
      details: [...partDetails(item.part_index), { label: translate("gage.charts.value"), value: formatExactNumericValue(item.value) }, { label: translate("gage.charts.sourceRow"), value: String(item.source_row_number) }],
      x: operatorPosition.get(item.operator_index)! + ((item.source_row_number * 17 % 31) / 30 - 0.5) * 0.3, value: item.value, className: operatorClass(item.operator_index),
      outlier: finite(box.lower_fence) && finite(box.upper_fence) && (item.value < box.lower_fence || item.value > box.upper_fence),
    }));
  });
  return { xRange, yRange, partTicks, responsePart, interaction: { points: interactionPoints, series: seriesFor(interactionPoints) },
    dispersion: limitsChart("dispersion"), xbar: limitsChart("xbar"), boxes, dots,
    operatorTicks: operators.map((operator, value) => ({ value, label: operatorLabel(operator.operator_index) })),
    operatorSummaries: bundle.response_by_operator.boxes.filter((box) => operatorPosition.has(box.operator_index)),
    partIdentityLabel, partSummaries: parts.map((part) => ({ ...part, label: partLabel(part.part_index) })) };
}
