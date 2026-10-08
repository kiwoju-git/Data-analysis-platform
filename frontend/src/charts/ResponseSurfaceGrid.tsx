import type { DoeResponseSurfaceAnalysisResponse } from "../api";
import { InteractiveGridChart } from "./InteractiveGridChart";
import { useI18n } from "../i18n/LocaleProvider";

export function ResponseSurfaceGrid({ analysis }: { analysis: DoeResponseSurfaceAnalysisResponse }) {
  const { t, formatNumber } = useI18n();
  const { contour } = analysis.result;
  const fixed = Object.entries(contour.held_coded_levels).map(([name, value]) => `${name}=${formatNumber(value)}`).join("; ");
  return <InteractiveGridChart chartId="rsm-contour" sourceKey={analysis.analysis_id} title={analysis.response_name}
    description={`${contour.x_factor}; ${contour.y_factor}; ${fixed}`} xLabel={`${contour.x_factor} (${t("charts.coded")})`}
    yLabel={`${contour.y_factor} (${t("charts.coded")})`} valueLabel={analysis.response_name} valueUnit={analysis.result.response.unit}
    xRange={{ min: contour.coded_range[0], max: contour.coded_range[1] }} yRange={{ min: contour.coded_range[0], max: contour.coded_range[1] }}
    cells={contour.points.map((point) => ({ id: `cell:${point.x_coded}:${point.y_coded}`, x: point.x_coded, y: point.y_coded, value: point.predicted,
      title: analysis.response_name, details: [{ label: contour.x_factor, value: formatNumber(point.x_actual) }, { label: contour.y_factor, value: formatNumber(point.y_actual) },
        { label: t("charts.coded"), value: `${formatNumber(point.x_coded)}, ${formatNumber(point.y_coded)}` },
        { label: analysis.response_name, value: formatNumber(point.predicted) }, { label: t("charts.fixedValues"), value: fixed }] }))} />;
}
