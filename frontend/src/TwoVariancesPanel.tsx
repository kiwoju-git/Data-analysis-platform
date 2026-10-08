import { useEffect, useMemo, useRef, useState } from "react";
import type { AnalysisResultEnvelope, DatasetVersionResponse, TwoVariancesOptions, TwoVariancesPreflightResponse, TwoVariancesResult } from "./api";
import { apiRequestError, fetchApi } from "./api/client";
import { apiRoutes } from "./api/routes";
import { serializeAnalysisFilterDrafts, type AnalysisFilterDraft } from "./analysisFilters";
import { createLatestRequestGuard } from "./latestRequest";
import { useI18n } from "./i18n/LocaleProvider";
import type { TranslationKey } from "./i18n/translate";
import { InteractiveScatterChart } from "./charts/InteractiveScatterChart";
import { paddedNumericRange } from "./charts/chartScale";

interface Props {
  version: DatasetVersionResponse | null;
  filterDrafts: AnalysisFilterDraft[];
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  analysisResult: AnalysisResultEnvelope | null;
  result: TwoVariancesResult | null;
  onRun: (options: TwoVariancesOptions) => void;
}
const fmt = (value: number) => Number(value.toPrecision(8)).toString();
const warningKeys: Record<string, TranslationKey> = {
  two_variances_independence_required: "twoVariances.warning.two_variances_independence_required",
  two_variances_nonrejection_not_equivalence: "twoVariances.warning.two_variances_nonrejection_not_equivalence",
  two_variances_f_normality_sensitive: "twoVariances.warning.two_variances_f_normality_sensitive",
  two_variances_ratio_ci_unavailable: "twoVariances.warning.two_variances_ratio_ci_unavailable",
  two_variances_complete_case_exclusions: "twoVariances.warning.two_variances_complete_case_exclusions",
  two_variances_display_points_limited: "twoVariances.warning.two_variances_display_points_limited",
};

export function TwoVariancesPanel({ version, filterDrafts, filterValidationError, isRunningAnalysis, analysisResult, result, onRun }: Props) {
  const { t } = useI18n();
  const [responseId, setResponseId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [numerator, setNumerator] = useState("");
  const [method, setMethod] = useState<TwoVariancesOptions["method"]>("brown_forsythe");
  const [scale, setScale] = useState<TwoVariancesOptions["ratio_scale"]>("variance");
  const [ratio, setRatio] = useState("1");
  const [alternative, setAlternative] = useState<TwoVariancesOptions["alternative"]>("two_sided");
  const [confidence, setConfidence] = useState("0.95");
  const [preflight, setPreflight] = useState<TwoVariancesPreflightResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const guard = useRef(createLatestRequestGuard()).current;
  const filters = useMemo(() => version && !filterValidationError ? {
    expression_version: 1, conditions: serializeAnalysisFilterDrafts(filterDrafts, version.columns),
  } : null, [version, filterDrafts, filterValidationError]);
  const configKey = JSON.stringify([version?.version_id, responseId, groupId, filters]);
  const latestKey = useRef(configKey);
  latestKey.current = configKey;
  useEffect(() => { guard.cancel(); setPreflight(null); setBusy(false); setError(null); return () => guard.cancel(); }, [configKey, guard]);
  useEffect(() => {
    if (!result) return;
    setResponseId(result.response.column_id); setGroupId(result.group_column.column_id);
    setNumerator(result.groups[0].key); setMethod(result.method); setScale(result.ratio_estimate.scale);
    setRatio(String(result.hypothesis.ratio)); setAlternative(result.hypothesis.alternative); setConfidence(String(result.hypothesis.confidence_level));
  }, [result]);
  const columns = version?.columns.filter((column) => column.role !== "id" && column.measurement_level !== "id") ?? [];
  const numeric = columns.filter((column) => ["integer", "number", "decimal", "float"].includes(column.data_type));
  const denominator = preflight?.groups.find((group) => group.key !== numerator)?.key ?? "";
  const minimum = method === "brown_forsythe" ? 3 : 2;
  const valid = preflight?.eligible && preflight.groups.some((group) => group.key === numerator)
    && preflight.groups.every((group) => group.n_used >= minimum)
    && Number.isFinite(Number(ratio)) && Number(ratio) > 0 && Number(confidence) > .5 && Number(confidence) < 1;
  async function checkGroups() {
    if (!version || !filters) return;
    const token = guard.begin(); const key = configKey; setBusy(true); setError(null); setPreflight(null);
    try {
      const response = await fetchApi(apiRoutes.twoVariancesPreflight(), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        dataset_version_id: version.version_id, response_column_id: responseId, group_column_id: groupId, filter_snapshot: filters,
      }) });
      if (!response.ok) throw await apiRequestError(response, "two_variances_preflight_failed");
      const value = (await response.json()) as TwoVariancesPreflightResponse;
      if (!guard.isCurrent(token) || latestKey.current !== key) return;
      setPreflight(value); setNumerator((current) => value.groups.some((group) => group.key === current) ? current : (value.groups[0]?.key ?? ""));
    } catch (failure) {
      if (guard.isCurrent(token) && latestKey.current === key) setError(failure instanceof Error ? failure.message : "two_variances_preflight_failed");
    } finally { if (guard.isCurrent(token) && latestKey.current === key) setBusy(false); }
  }
  return <section className="analysis-run-panel" data-analysis-execution="quality.two_variances">
    <div className="option-grid">
      <label>{t("twoVariances.response")}<select value={responseId} onChange={(event) => setResponseId(event.target.value)}><option value="">{t("twoVariances.choose")}</option>{numeric.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}</select></label>
      <label>{t("twoVariances.group")}<select value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">{t("twoVariances.choose")}</option>{columns.filter((column) => column.column_id !== responseId).map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}</select></label>
    </div>
    <button type="button" className="secondary-button" disabled={!responseId || !groupId || !filters || busy || isRunningAnalysis} onClick={() => void checkGroups()}>{t(busy ? "twoVariances.checking" : "twoVariances.checkGroups")}</button>
    {error && <p role="alert">{t("twoVariances.preflightError")} <code>{error}</code></p>}
    {preflight && <><p>{t("twoVariances.sample", { used: preflight.n_used, excluded: preflight.n_excluded })}</p>
      <div className="table-wrap"><table><thead><tr><th>{t("twoVariances.group")}</th><th>N</th></tr></thead><tbody>{preflight.groups.map((group) => <tr key={group.key}><td title={group.key}>{group.key}</td><td>{group.n_used}</td></tr>)}</tbody></table></div>
      {!preflight.eligible ? <p role="alert">{t("twoVariances.twoGroupsRequired")}</p> : <div className="option-grid"><label>{t("twoVariances.numerator")}<select value={numerator} onChange={(event) => setNumerator(event.target.value)}>{preflight.groups.map((group) => <option key={group.key} value={group.key}>{group.key}</option>)}</select><span>{t("twoVariances.denominator")}: {denominator}</span></label></div>}
    </>}
    <div className="option-grid">
      <label>{t("twoVariances.method")}<select value={method} onChange={(event) => {
        const next = event.target.value as TwoVariancesOptions["method"]; setMethod(next);
        if (next === "brown_forsythe") { setRatio("1"); setAlternative("two_sided"); }
      }}><option value="brown_forsythe">{t("twoVariances.bf")}</option><option value="normal_f">{t("twoVariances.f")}</option></select></label>
      <label>{t("twoVariances.scale")}<select value={scale} onChange={(event) => setScale(event.target.value as TwoVariancesOptions["ratio_scale"])}><option value="variance">{t("twoVariances.variance")}</option><option value="standard_deviation">{t("twoVariances.sd")}</option></select></label>
      <label>{t("twoVariances.nullRatio")}<input type="number" step="any" min="0" value={ratio} disabled={method === "brown_forsythe"} onChange={(event) => setRatio(event.target.value)} /></label>
      <label>{t("twoVariances.alternative")}<select value={alternative} disabled={method === "brown_forsythe"} onChange={(event) => setAlternative(event.target.value as TwoVariancesOptions["alternative"])}>{(["two_sided", "less", "greater"] as const).map((value) => <option key={value} value={value}>{t(`twoVariances.${value}`)}</option>)}</select></label>
      <label>{t("twoVariances.confidence")}<input type="number" min="0.5" max="0.9999" step="0.01" value={confidence} onChange={(event) => setConfidence(event.target.value)} /></label>
    </div>
    <p>{t(method === "brown_forsythe" ? "twoVariances.bfLimit" : "twoVariances.fWarning")}</p>
    <p>{t("twoVariances.independence")}</p>
    <button type="button" className="primary-button" disabled={!valid || busy || isRunningAnalysis || !!filterValidationError} onClick={() => onRun({
      response_column_id: responseId, group_column_id: groupId, numerator_group_key: numerator, denominator_group_key: denominator,
      method, ratio_scale: scale, hypothesized_ratio: Number(ratio), alternative, confidence_level: Number(confidence), preflight_fingerprint: preflight!.fingerprint,
    })}>{t("twoVariances.run")}</button>
    {result && <TwoVariancesResults result={result} sourceKey={analysisResult?.analysis_id} />}
  </section>;
}

export function TwoVariancesResults({ result, sourceKey }: { result: TwoVariancesResult; sourceKey?: string }) {
  const { t } = useI18n();
  const points = result.plot.groups.flatMap((group, index) => group.points.map((point) => ({ id: `${index}:${point.row_number}`, x: index + 1, y: point.value,
    title: group.key, ariaLabel: `${group.key}: ${point.row_number}, ${fmt(point.value)}`, className: index ? "pls-cv-point" : "scatter-point",
    details: [{ label: t("twoVariances.filteredRow"), value: String(point.row_number) }, { label: result.response.display_name, value: fmt(point.value) }],
  })));
  const interval = result.ratio_interval;
  const intervalText = interval.available ? `${interval.lower.value === null ? "-" : fmt(interval.lower.value)} - ${interval.upper.kind === "unbounded" ? "∞" : fmt(interval.upper.value)}` : t("twoVariances.noCI");
  const ratioRange = paddedNumericRange([result.ratio_estimate.value, result.hypothesis.ratio,
    ...(interval.available ? [interval.lower.value, interval.upper.value].filter((value): value is number => value !== null) : [])]);
  return <section className="result-section"><h3>{t("twoVariances.title")}</h3>
    <p>{t(result.method === "normal_f" ? "twoVariances.f" : "twoVariances.bf")} · {t("twoVariances.sample", { used: result.sample.n_used, excluded: result.sample.n_excluded })}</p>
    <p>{result.groups[0].key} / {result.groups[1].key} · {t(`twoVariances.${result.ratio_estimate.scale === "variance" ? "variance" : "sd"}`)} = {fmt(result.ratio_estimate.value)}</p>
    <p>{t("twoVariances.interval")}: {intervalText}</p>
    <p>{t(result.test.reject ? "twoVariances.reject" : "twoVariances.notReject")}</p>
    <div className="table-wrap"><table><thead><tr><th>{t("twoVariances.group")}</th><th>N</th><th>{t("twoVariances.mean")}</th><th>{t("twoVariances.variance")}</th><th>{t("twoVariances.sd")}</th></tr></thead><tbody>{result.groups.map((group) => <tr key={group.key}><th>{group.key}</th><td>{group.n}</td><td>{fmt(group.mean)}</td><td>{fmt(group.variance)}</td><td>{fmt(group.standard_deviation)}</td></tr>)}</tbody></table></div>
    <p>{t("twoVariances.statistic")}: {fmt(result.test.statistic)} · DF {result.test.df1}, {result.test.df2} · p = {fmt(result.test.p_value)} · alpha = {fmt(result.test.alpha)}</p>
    <div className="analysis-result-grid">
      <InteractiveScatterChart chartId="two-variances-groups" sourceKey={sourceKey} title={t("twoVariances.groupPlot")} description={t("twoVariances.filteredRow")}
        points={points} formatValue={fmt} emptyLabel={t("charts.noData")} xLabel={result.group_column.display_name} yLabel={result.response.display_name} yUnit={result.response.unit}
        xRange={{ min: .5, max: 2.5 }} yRange={paddedNumericRange(points.map((point) => point.y))} xTicks={result.groups.map((group, index) => ({ value: index + 1, label: group.label }))}
        annotations={[t("charts.displayCount", { shown: points.length, total: result.sample.n_used })]} />
      {interval.available && <InteractiveScatterChart chartId="two-variances-ratio" sourceKey={sourceKey} title={t("twoVariances.interval")} description={intervalText}
        formatValue={fmt} emptyLabel={t("charts.noData")} xLabel={t(result.ratio_estimate.scale === "variance" ? "twoVariances.varianceRatio" : "twoVariances.sdRatio")} yLabel={t("twoVariances.comparison")}
        xRange={ratioRange} yRange={{ min: 0, max: 2 }} yTicks={[{ value: 1, label: t("twoVariances.ratio") }]}
        points={[{ id: "ratio", x: result.ratio_estimate.value, y: 1, title: t("twoVariances.ratio"), ariaLabel: intervalText, className: "scatter-point", details: [{ label: t("twoVariances.interval"), value: intervalText }] }]}
        referenceLines={[{ label: t("twoVariances.nullRatio"), x1: result.hypothesis.ratio, x2: result.hypothesis.ratio, y1: 0, y2: 2 },
          { label: `${100 * interval.confidence_level}% ${intervalText}`, x1: interval.lower.value ?? 0, x2: interval.upper.value ?? ratioRange.max, y1: 1, y2: 1, arrow: interval.upper.kind === "unbounded" }]}
        annotations={[`${100 * interval.confidence_level}% ${intervalText}`]} />}
    </div>
    <ul>{result.warnings.map((warning) => <li key={warning}>{t(warningKeys[warning] ?? "warnings.generic")}</li>)}</ul>
  </section>;
}
