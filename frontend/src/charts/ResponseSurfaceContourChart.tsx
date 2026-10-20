import { useId, useMemo } from "react";
import type { RsmPlotBundle, RsmVertex } from "../api/types/rsmPlots";
import { useI18n } from "../i18n/LocaleProvider";
import { formatExactNumericValue, formatMeasurement } from "../statisticalNumberFormat";
import { InteractiveGridChart } from "./InteractiveGridChart";
import { InteractiveScatterChart } from "./InteractiveScatterChart";
import { axisTitle, type ChartLayout } from "./chartLayout";
import { paddedNumericRange } from "./chartScale";

const COLORS = ["#eef5fa", "#d6e9f2", "#afd5e4", "#80bacf", "#519cb6", "#2d7c99",
  "#225d79", "#1a455f", "#16354b", "#112a3e", "#0d2031", "#091723"];

export function ResponseSurfaceContourChart({ bundle, sourceKey, layout, yRange }: {
  bundle: RsmPlotBundle; sourceKey: string; layout?: ChartLayout;
  yRange?: { min: number; max: number };
}) {
  const { t, locale } = useI18n();
  const instance = useId().replace(/:/g, "");
  const number = (value: number) => formatMeasurement(value, locale);
  const fixed = Object.entries(bundle.held_actual_values).map(([key, value]) =>
    `${key}=${number(value)}`).join("; ");
  const xLabel = axisTitle(bundle.x_axis.name, bundle.settings.axis_scale === "coded"
    ? t("charts.coded") : bundle.x_axis.unit);
  const yLabel = bundle.y_axis ? axisTitle(bundle.y_axis.name,
    bundle.settings.axis_scale === "coded" ? t("charts.coded") : bundle.y_axis.unit) : "";
  const valueLabel = axisTitle(bundle.response_name, bundle.response_unit);
  const cells = useMemo(() => bundle.points.map((point) => ({
    id: point.point_id, x: point.x, y: point.y, value: point.predicted,
    title: valueLabel, details: [
      { label: xLabel, value: formatExactNumericValue(point.x) },
      { label: yLabel, value: formatExactNumericValue(point.y) },
      { label: valueLabel, value: formatExactNumericValue(point.predicted) },
      { label: t("charts.fixedValues"), value: fixed || t("rsm.plot.noHolds") },
      { label: t("rsm.plot.region"), value: t(point.outside_design_hull
        ? "rsm.plot.outsideHull" : "rsm.plot.insideHull") },
    ],
  })), [bundle, valueLabel, xLabel, yLabel, t, fixed]);
  if (!bundle.geometry || !bundle.y_axis) return <InteractiveScatterChart
    chartId="rsm-conditional" sourceKey={sourceKey} title={t("rsm.plot.conditional")}
    layout={layout} yRange={yRange ?? paddedNumericRange(bundle.points.map((point) => point.predicted), .05)}
    xRange={{ min: bundle.x_axis.minimum, max: bundle.x_axis.maximum }}
    axisTickCount={layout ? 3 : undefined} collapsibleDetails={Boolean(layout)}
    annotations={[]} emptyLabel={t("charts.noData")}
    description={fixed} xLabel={xLabel} yLabel={valueLabel}
    points={bundle.curves.flatMap((curve, curveIndex) => curve.points.map((point) => ({
      id: point.point_id, x: point.x, y: point.predicted,
      className: curveIndex % 2 ? "chart-series-secondary" : "chart-series-primary",
      ariaLabel: `${xLabel}: ${number(point.x)}; ${valueLabel}: ${number(point.predicted)}`,
      title: valueLabel, details: [
        { label: xLabel, value: number(point.x) }, { label: valueLabel, value: number(point.predicted) },
        { label: t("charts.fixedValues"), value: fixed || t("rsm.plot.noHolds") },
        ...(curve.trace_actual_value === null ? [] : [{ label: bundle.y_axis?.name ?? "",
          value: number(curve.trace_actual_value) }]),
      ],
    })))}
    series={bundle.curves.map((curve, index) => ({ id: curve.series_id,
      label: curve.trace_actual_value === null ? t("rsm.plot.conditional")
        : `${bundle.y_axis?.name}=${number(curve.trace_actual_value)}`,
      className: index % 2 ? "chart-series-secondary" : "chart-series-primary",
      pointIds: curve.points.map((point) => point.point_id), connect: "line" as const }))}
  />;
  const geometry = bundle.geometry;
  const levelLabels = geometry.levels.map(number);
  const levelNumber = new Set(levelLabels).size === levelLabels.length ? number : formatExactNumericValue;
  return <div className="rsm-contour-view">
    <p className="muted-text">{t("rsm.plot.conditions")} {fixed || t("rsm.plot.noHolds")}</p>
    <InteractiveGridChart chartId="rsm-contour" sourceKey={sourceKey}
      title={valueLabel} description={`${t("rsm.plot.conditional")}; ${fixed}`}
      xLabel={xLabel} yLabel={yLabel} valueLabel={valueLabel} cells={cells}
      xRange={{ min: bundle.x_axis.minimum, max: bundle.x_axis.maximum }}
      yRange={{ min: bundle.y_axis.minimum, max: bundle.y_axis.maximum }}
      colorScale={<div className="chart-color-scale rsm-contour-legend">
        <strong>{valueLabel}</strong>
        {geometry.bands.map((band, index) => <span key={index}>
          <i aria-hidden="true" style={{ backgroundColor: COLORS[Math.round(index * 11 /
            Math.max(1, geometry.bands.length - 1))] }} />
          {geometry.constant ? number(geometry.minimum)
            : `${band.lower === null ? "-inf" : levelNumber(band.lower)} .. ${band.upper === null ? "+inf" : levelNumber(band.upper)}`}
        </span>)}
      </div>}
      renderSurface={({ x, y }) => {
        const path = (points: readonly RsmVertex[], close = false) => points.length
          ? `M${points.map(([px, py]) => `${x(px)},${y(py)}`).join("L")}${close ? "Z" : ""}` : "";
        const outer: RsmVertex[] = [[bundle.x_axis.minimum, bundle.y_axis!.minimum],
          [bundle.x_axis.maximum, bundle.y_axis!.minimum], [bundle.x_axis.maximum, bundle.y_axis!.maximum],
          [bundle.x_axis.minimum, bundle.y_axis!.maximum]];
        return <g pointerEvents="none">
          <defs><pattern id={`rsm-hatch-${instance}`} width="8" height="8" patternUnits="userSpaceOnUse">
            <path d="M0 8L8 0" stroke="#454f5e" strokeOpacity=".5" strokeWidth="1" />
          </pattern></defs>
          {bundle.settings.filled && geometry.bands.flatMap((band, index) => band.polygons.map((polygon, pi) =>
            <path key={`band:${index}:${pi}`} d={polygon.rings.map((ring) => path(ring, true)).join("")}
              data-contour-band={index} fillRule="evenodd"
              fill={COLORS[Math.round(index * 11 / Math.max(1, geometry.bands.length - 1))]} />))}
          {bundle.settings.lines && geometry.lines.flatMap((line, index) => line.paths.map((points, pi) => {
            const mid = points[Math.floor(points.length / 2)];
            return <g key={`line:${index}:${pi}`} data-contour-level={line.level}>
              <path d={path(points)} fill="none" stroke="#273340" strokeWidth="1" />
              {mid && <text x={x(mid[0])} y={y(mid[1])} fontSize="10" fill="#111"
                stroke="#fff" strokeWidth="2" paintOrder="stroke">{levelNumber(line.level)}</text>}
            </g>;
          }))}
          <path d={path(outer, true) + path(bundle.hull_slice_polygon, true)}
            fill={`url(#rsm-hatch-${instance})`} fillRule="evenodd" />
          {bundle.settings.design_points && bundle.design_points.map((point) =>
            <circle key={point.run_order} cx={x(point.x)} cy={y(point.y)} r={3}
              data-on-slice={point.on_slice} fill={point.on_slice ? "#111" : "#fff"} stroke="#111" />)}
        </g>;
      }} />
    <p className="muted-text">{t("rsm.plot.hullNotice")}</p>
    {bundle.settings.design_points && <p className="muted-text">{t("rsm.plot.designNotice")}</p>}
    <details><summary>{t("rsm.plot.storedValues")}</summary>
      <div className="table-wrap"><table><thead><tr><th>{xLabel}</th><th>{yLabel}</th>
        <th>{valueLabel}</th><th>{t("rsm.plot.region")}</th></tr></thead><tbody>
        {bundle.points.map((point) => <tr key={point.point_id}><td>{formatExactNumericValue(point.x)}</td>
          <td>{formatExactNumericValue(point.y)}</td><td>{formatExactNumericValue(point.predicted)}</td>
          <td>{t(point.outside_design_hull ? "rsm.plot.outsideHull" : "rsm.plot.insideHull")}</td></tr>)}
      </tbody></table></div>
    </details>
  </div>;
}
