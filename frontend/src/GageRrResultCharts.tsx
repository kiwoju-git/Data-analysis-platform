import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { GageRrResult, GageRrPlotBundle } from "./api/types/analysisResultsQuality";
import { useI18n } from "./i18n/LocaleProvider";
import { InteractiveScatterChart, type InteractiveScatterChartProps } from "./charts/InteractiveScatterChart";
import { InteractiveGroupedBarChart, InteractiveVerticalBoxplotChart } from "./charts/InteractiveSummaryChart";
import { componentChart, gageChartModels, gagePlotState, GAGE_OPERATOR_PAGE_SIZE, GAGE_PART_PAGE_SIZE } from "./charts/gageRrChartModels";
import "./gageRrCharts.css";

type Kind = "components" | "response_by_part" | "dispersion" | "response_by_operator" | "xbar" | "interaction";
const kinds: Kind[] = ["components", "response_by_part", "dispersion", "response_by_operator", "xbar", "interaction"];

export function GageRrResultCharts({ result, sourceKey }: { result: GageRrResult; sourceKey: string }) {
  const { t } = useI18n();
  const state = gagePlotState(result);
  return <section className="gage-six-panel" data-gage-six-panel data-plot-state={state} aria-label={t("gage.charts.title")}>
    <h3>{t("gage.charts.title")}</h3>
    <p>{t("gage.charts.identity")}</p>
    {state === "invalid" ? <p className="notice-box notice-warning" role="alert">{t("gage.charts.invalid")}</p>
      : <GageChartBody key={sourceKey} result={result} sourceKey={sourceKey} bundle={state === "valid" ? result.plot_bundle! : null} />}
  </section>;
}

function Pager({ label, page, count, onChange }: { label: string; page: number; count: number; onChange: (page: number) => void }) {
  const { t } = useI18n();
  return <div className="gage-chart-pager" role="group" aria-label={label}>
    <span>{label}</span>
    <button type="button" className="icon-button" title={t("gage.charts.previous")} aria-label={`${label}: ${t("gage.charts.previous")}`} disabled={page === 0} onClick={() => onChange(page - 1)}><ChevronLeft size={18} /></button>
    <output aria-live="polite">{t("gage.charts.page", { current: page + 1, total: count })}</output>
    <button type="button" className="icon-button" title={t("gage.charts.next")} aria-label={`${label}: ${t("gage.charts.next")}`} disabled={page + 1 >= count} onClick={() => onChange(page + 1)}><ChevronRight size={18} /></button>
  </div>;
}

function GageChartBody({ result, bundle, sourceKey }: { result: GageRrResult; bundle: GageRrPlotBundle | null; sourceKey: string }) {
  const { t } = useI18n();
  const [partPage, setPartPage] = useState(0);
  const [operatorPage, setOperatorPage] = useState(0);
  const models = useMemo(() => bundle ? gageChartModels(bundle, partPage, operatorPage, t) : null, [bundle, partPage, operatorPage, t]);
  const components = useMemo(() => componentChart(result, t), [result, t]);
  const measurement = bundle?.measurement.display_name ?? t("gage.charts.measurement");
  const unit = bundle?.measurement.unit;
  const titles: Record<Kind, string> = {
    components: t("gage.charts.components"), response_by_part: t("gage.charts.response_by_part"),
    dispersion: t(bundle?.dispersion.statistic === "sample_sd" ? "gage.charts.dispersionS" : "gage.charts.dispersionR"),
    response_by_operator: t("gage.charts.response_by_operator"), xbar: t("gage.charts.xbar"), interaction: t("gage.charts.interaction"),
  };
  const help: Record<Kind, string> = {
    components: t("gage.charts.componentsHelp"), response_by_part: t("gage.charts.partHelp"), dispersion: t("gage.charts.rangeHelp"),
    response_by_operator: t("gage.charts.boxHelp"), xbar: t("gage.charts.xbarHelp"), interaction: t("gage.charts.interactionHelp"),
  };
  function scatter(kind: "response_by_part" | "dispersion" | "xbar" | "interaction", options: Partial<InteractiveScatterChartProps>) {
    if (!models) return null;
    return <InteractiveScatterChart chartId={`gage-${kind}`} sourceKey={`${sourceKey}:${kind}:1`}
      title={titles[kind]} description={help[kind]} annotations={[]} emptyLabel={t("gage.charts.unavailable")}
      points={[]} xRange={models.xRange} yRange={models.yRange} xTicks={models.partTicks}
      xLabel={t("gage.charts.partAxis")} yLabel={measurement} yUnit={unit} collapsibleDetails {...options} />;
  }
  function render(kind: Kind) {
    if (kind === "components") {
      if (components.bars.length !== 8) return <p className="notice-box">{t("gage.charts.componentUnavailable")}</p>;
      return <InteractiveGroupedBarChart chartId="gage-components" sourceKey={`${sourceKey}:components:1`} title={titles.components}
        description={help.components} xLabel={t("gage.charts.componentAxis")} yLabel={t("gage.charts.percentAxis")}
        {...components} footer={<ul className="chart-series-legend"><li><i className="gage-component-series-0" aria-hidden="true" />{t("gage.charts.contribution")}</li><li><i className="gage-component-series-1" aria-hidden="true" />{t("gage.charts.studyVariation")}</li></ul>} />;
    }
    if (!bundle || !models || bundle[kind].status === "unavailable") return <div className="gage-chart-unavailable"><p>{t("gage.charts.unavailable")}</p>
      {bundle?.[kind].unavailable_reason && <details><summary>{t("gage.charts.details")}</summary><code>{bundle[kind].unavailable_reason}</code></details>}</div>;
    if (kind === "dispersion") return scatter(kind, { ...models.dispersion, yLabel: t(bundle.dispersion.statistic === "range" ? "gage.charts.range" : "gage.charts.sd") });
    if (kind === "xbar") return scatter(kind, models.xbar);
    if (kind === "response_by_part") return scatter(kind, models.responsePart);
    if (kind === "interaction") return scatter(kind, models.interaction);
    return <InteractiveVerticalBoxplotChart chartId="gage-response_by_operator" sourceKey={`${sourceKey}:response_by_operator:1`}
      title={titles.response_by_operator} description={help.response_by_operator} xLabel={t("gage.charts.operatorAxis")}
      yLabel={measurement} yUnit={unit} categories={models.operatorTicks} yRange={models.yRange} boxes={models.boxes} dots={models.dots}
      footer={<><ul className="chart-series-legend"><li>{t("gage.charts.mean")} ◇</li><li>{t("gage.charts.median")} ─</li></ul>
        <ul className="gage-box-counts">{models.operatorSummaries.map((box) => <li key={box.operator_index}>{t("gage.charts.boxSample", { index: box.operator_index + 1, n: box.n, outliers: box.outlier_count, displayed: box.displayed_outlier_count })}</li>)}</ul></>} />;
  }
  return <>
    {bundle ? <>
      <p data-gage-point-counts>{t("gage.charts.sample", { used: bundle.counts.n_used, total: bundle.counts.n_total, displayed: bundle.counts.displayed_raw_point_count, limit: bundle.counts.raw_point_limit })}</p>
      {bundle.counts.truncated && <p className="notice-box">{t("gage.charts.sampling")}</p>}
      <div className="gage-chart-controls">
        <Pager label={t("gage.charts.partPage")} page={partPage} count={Math.ceil(bundle.counts.part_count / GAGE_PART_PAGE_SIZE)} onChange={setPartPage} />
        <Pager label={t("gage.charts.operatorPage")} page={operatorPage} count={Math.ceil(bundle.counts.operator_count / GAGE_OPERATOR_PAGE_SIZE)} onChange={setOperatorPage} />
      </div>
    </> : <p className="notice-box">{t("gage.charts.legacy")}</p>}
    <div className="gage-six-grid">{kinds.map((kind) => <div className="gage-chart-panel" key={kind} data-gage-chart-kind={kind}
      data-gage-chart-state={kind === "components" ? (components.bars.length === 8 ? "available" : "unavailable") : (bundle?.[kind].status ?? "unavailable")}>
      <h4>{titles[kind]}</h4>{render(kind)}<p className="gage-chart-explanation">{help[kind]}</p>
      {kind === "interaction" && bundle?.interaction.interaction_pooled && <p className="notice-box">{t("gage.charts.pooledHelp")}</p>}
      {kind === "dispersion" && bundle?.dispersion.warning_codes.includes("within_cell_variation_zero") && <p className="notice-box">{t("gage.charts.zeroWithin")}</p>}
    </div>)}</div>
    {bundle && <details className="gage-policy-details"><summary>{t("gage.charts.details")}</summary><dl>
      <div><dt>{t("gage.charts.policy")}</dt><dd>{t(bundle.calculation_metadata.selected_interaction_policy === "pooled" ? "gage.charts.pooled" : "gage.charts.retain")}</dd></div>
      <div><dt>{titles.dispersion}</dt><dd><code>{bundle.dispersion.policy}</code>; {Object.entries(bundle.dispersion.constants).filter(([, value]) => value !== null).map(([key, value]) => `${key} = ${value}`).join("; ")}; <code>{bundle.dispersion.constant_precision}</code></dd></div>
      <div><dt>{titles.xbar}</dt><dd><code>{bundle.xbar.limit_source}</code></dd></div>
    </dl></details>}
  </>;
}
