import { useState } from "react";
import { setCurrentLocale } from "../i18n/store";
import { Biplot, LoadingPlot as PcaLoading, OutlierPlot, ScorePlot as PcaScore, ScreePlot } from "./PrincipalComponentCharts";
import { LineMetricChart, LoadingPlot as PlsLoading, ResponsePlot, ScorePlot as PlsScore } from "./PlsResultCharts";
import { GpScatter, GpProfileChart, GpSurfaceChart, GpUncertaintyChart } from "./GaussianProcessCharts";
import { gpFixture, pcaFixture, plsFixture } from "./resultChartFixtures";

const pca = pcaFixture();
const pls = plsFixture();
pls.component_selection.rows[0].predicted_r_squared = -0.4;
pls.predictors = Array.from({ length: 25 }, (_, i) => ({ ...pls.predictors[0], column_id: `column-${i}`, display_name: `Predictor ${i + 1} with a long label` }));
pls.latent_components.x_loadings = pls.predictors.map((_, i) => [(i - 12) / 20, i / 40]);
const gp = gpFixture();
gp.predictors.push({ ...gp.predictors[0], column_id: "x3", display_name: "Third factor" });
gp.training_ranges.push({ column_id: "x3", display_name: "Third factor", minimum: 0, maximum: 1, median: 0.5 });
gp.two_predictor_surface!.fixed_values.push(0.5);
gp.two_predictor_surface!.grid_size = 3;
gp.two_predictor_surface!.points = Array.from({ length: 9 }, (_, index) => ({
  x: index % 3, y: Math.floor(index / 3), predicted_mean: 10 + index, predictive_standard_deviation: 0.2 + index / 100,
}));
gp.conditional_profiles.forEach((profile) => {
  profile.points = Array.from({ length: 25 }, (_, index) => ({ ...profile.points[0], value: index / 24,
    predicted_mean: 10 + index / 24, predictive_interval_95: { lower: 9 + index / 24, upper: 11 + index / 24 } }));
});

export function ResultChartsFixture() {
  const [single, setSingle] = useState(false);
  const [component, setComponent] = useState(1);
  const [source, setSource] = useState("fixture-analysis");
  const [locale, setLocale] = useState<"en" | "ko">("en");
  setCurrentLocale(locale);
  const pcaView = single ? { ...pca, plot: { ...pca.plot, points: pca.plot.points.map((p) => ({ ...p, scores: p.scores.slice(0, 1) })) }, loadings: pca.loadings.map((p) => ({ ...p, values: p.values.slice(0, 1) })) } : pca;
  const plsView = single ? { ...pls, latent_components: { ...pls.latent_components, x_scores: pls.latent_components.x_scores.map((p) => p.slice(0, 1)) } } : pls;
  return <main style={{ padding: 16, maxWidth: 1300, margin: "auto" }}>
    <button onClick={() => setSingle((v) => !v)}>Toggle one component</button>
    <button onClick={() => setComponent((v) => v === 1 ? 2 : 1)}>Change loading component</button>
    <button onClick={() => setSource("replacement-analysis")}>Replace source</button>
    <button onClick={() => setLocale((v) => v === "en" ? "ko" : "en")}>Language</button>
    <ScreePlot result={pcaView} analysisId={source} />
    <PcaScore result={pcaView} analysisId={source} xComponent={1} yComponent={single ? null : 2} />
    <PcaLoading result={pcaView} analysisId={source} xComponent={1} yComponent={single ? null : 2} />
    <Biplot result={pcaView} analysisId={source} xComponent={1} yComponent={single ? null : 2} />
    <OutlierPlot result={pcaView} analysisId={source} />
    <LineMetricChart result={plsView} analysisId={source} />
    <ResponsePlot result={plsView} analysisId={source} />
    <PlsScore result={plsView} analysisId={source} />
    <PlsLoading result={plsView} analysisId={source} component={component} />
    <GpScatter result={gp} scope={`${source}:selected`} mode="cv" />
    <GpScatter result={gp} scope={`${source}:candidate:rbf`} mode="cv" />
    <GpUncertaintyChart result={gp} scope={`${source}:selected`} />
    {gp.conditional_profiles.map((profile) => <GpProfileChart key={profile.column_id} profile={profile} result={gp} scope={source} />)}
    <GpSurfaceChart result={gp} scope={source} />
  </main>;
}
