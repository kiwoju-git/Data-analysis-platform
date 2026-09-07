import { useState } from "react";
import type { RegularizedLinearModelResult } from "./api";
import { InteractiveScatterChart, type ScatterReferenceLine } from "./charts/InteractiveScatterChart";
import { InteractiveHistogramChart } from "./charts/InteractiveHistogramChart";
import { paddedNumericRange } from "./charts/chartScale";
import { useI18n } from "./i18n/LocaleProvider";
import type { TranslationKey } from "./i18n/translate";
import { regularizedWarningKeys } from "./i18n/regularizedMessages";

export function RegularizedLinearModelResults({ result }: { result: RegularizedLinearModelResult }) {
  const { t, formatNumber } = useI18n();
  const fmt = (value: number | null | undefined) => value == null ? "-" : formatNumber(value, { maximumSignificantDigits: 6 });
  const r = result.regularization;
  const validation = result.validation;
  const diagnosticPoints = result.diagnostics.points;
  const sources = new Map(result.predictors.map((column) => [column.column_id, column.display_name]));
  const summary: Array<[TranslationKey, string | number]> = [
    ["reg.estimator", t(`reg.${result.estimator.kind}`)],
    ["reg.tuning", t(r.mode === "automatic_cv" ? "reg.automatic" : "reg.fixed")],
    ["reg.selectedAlpha", fmt(r.selected_alpha)], ["reg.selectedRatio", fmt(r.selected_l1_ratio)],
    ["reg.total", result.sample.n_total], ["reg.used", result.sample.n_used],
    ["reg.missing", result.sample.n_excluded_missing], ["reg.nonNumeric", result.sample.n_excluded_non_numeric],
    ["reg.features", result.sample.feature_count], ["reg.outer", validation?.outer_folds ?? "-"],
    ["reg.inner", validation?.inner_folds ?? "-"], ["reg.elapsed", fmt(r.elapsed_seconds)],
    ["reg.convergence", t(r.converged ? "reg.converged" : "reg.notConverged")],
  ];
  return <div className="regularized-results">
    <section className="result-section"><h4>{t("reg.method")}</h4>
      <dl className="result-definition-grid">{summary.map(([label, value]) => <div key={label}><dt>{t(label)}</dt><dd>{value}</dd></div>)}</dl>
      <p>{t("reg.scaling")}</p><p>{t("reg.assumptions")}</p>
    </section>
    <section className="result-section"><h4>{t("reg.summary")}</h4><div className="table-wrap"><table className="result-table">
      <thead><tr><th>{t("reg.metric")}</th><th>{t("reg.training")}</th><th>{t("reg.cv")}</th></tr></thead>
      <tbody>{([
        ["reg.rSquared", result.fit.r_squared, validation?.predicted_r_squared],
        ["reg.press", null, validation?.press], ["reg.rmse", result.fit.rmse, validation?.rmse],
        ["reg.mae", result.fit.mae, validation?.mae],
      ] as const).map(([key, train, cv]) => <tr key={key}><th>{t(key)}</th><td>{fmt(train)}</td><td>{fmt(cv)}</td></tr>)}</tbody>
    </table></div></section>
    <section className="result-section"><h4>{t("reg.coefficients")}</h4>
      <p>{t("reg.zeroCount", { count: r.zero_coefficient_count })}</p>
      <div className="table-wrap"><table className="result-table"><thead><tr>
        {["reg.term", "reg.original", "reg.standardized", "reg.zero", "reg.kind", "reg.source"].map((key) => <th key={key}>{t(key as TranslationKey)}</th>)}
      </tr></thead><tbody>{result.coefficients.map((coefficient) => <tr key={coefficient.term}>
        <th>{coefficient.term}</th><td>{fmt(coefficient.estimate)}</td><td>{fmt(coefficient.standardized_estimate)}</td>
        <td>{coefficient.is_zero ? t("pls.yes") : t("pls.no")}</td><td><code>{coefficient.term_kind}</code></td>
        <td>{coefficient.source_column_ids?.map((id) => sources.get(id) ?? id).join(", ")}</td>
      </tr>)}</tbody></table></div>
      <h4>{t("reg.equation")}</h4><p className="regularized-equation">
        {result.response.display_name} = {result.coefficients.filter((c) => !c.is_zero).map((c, i) =>
          `${i > 0 && c.estimate >= 0 ? "+ " : ""}${fmt(c.estimate)}${c.term_kind === "intercept" ? "" : ` * ${c.term}`}`).join(" ")}
      </p>
    </section>
    <div className="chart-grid regularized-chart-grid">
      <section className="result-section"><h4>{t("reg.curve")}</h4><RegularizationCurve result={result} /></section>
      <section className="result-section"><h4>{t("reg.path")}</h4><RegularizationPath result={result} /></section>
      <Diagnostic titleKey="reg.observedFitted" xLabel={t("reg.fitted")} yLabel={t("reg.observed")}
        values={diagnosticPoints.map((p) => ({ x: p.fitted, y: p.observed, row: p.row_index }))} identity />
      {validation ? <Diagnostic titleKey="reg.observedCv" xLabel={t("reg.fitted")} yLabel={t("reg.observed")}
        values={diagnosticPoints.filter((p) => p.oof_predicted !== null).map((p) => ({ x: p.oof_predicted!, y: p.observed, row: p.row_index }))} identity /> : null}
      <Diagnostic titleKey="reg.residualFitted" xLabel={t("reg.fitted")} yLabel={t("reg.residual")}
        values={diagnosticPoints.map((p) => ({ x: p.fitted, y: p.residual, row: p.row_index }))} />
      <Diagnostic titleKey="reg.residualOrder" xLabel={t("reg.row")} yLabel={t("reg.residual")}
        values={diagnosticPoints.map((p) => ({ x: p.row_index + 1, y: p.residual, row: p.row_index }))} />
      <Diagnostic titleKey="reg.qq" xLabel={t("reg.theoretical")} yLabel={t("reg.residual")}
        values={result.diagnostics.qq_plot.points.map((p) => ({ x: p.theoretical_quantile, y: p.residual, row: p.row_index }))} />
      <section className="result-section"><h4>{t("reg.histogram")}</h4><InteractiveHistogramChart
        chartId="regularized-residual-histogram" columnName={t("reg.residual")} nBasis={result.sample.n_used}
        bins={result.diagnostics.histogram.bins.map((bin, i, bins) => ({ ...bin, include_lower: true, include_upper: i === bins.length - 1 }))} /></section>
    </div>
    <p className="cell-subtle">{t("reg.plotCount", { shown: diagnosticPoints.length, total: result.sample.n_used })}</p>
    <section className="result-section"><h4>{t("reg.warnings")}</h4><ul className="warning-list">{result.warnings.map((code) =>
      <li key={code}>{t(regularizedWarningKeys[code] ?? "reg.warning.generic")}<span className="cell-subtle">{code}</span></li>)}</ul></section>
    <p className="notice-box">{t("reg.pointOnly")}</p>
  </div>;
}

function Diagnostic({ titleKey, xLabel, yLabel, values, identity = false }: {
  titleKey: TranslationKey; xLabel: string; yLabel: string;
  values: Array<{ x: number; y: number; row: number }>; identity?: boolean;
}) {
  const { t, formatNumber } = useI18n();
  const range = paddedNumericRange(values.flatMap((p) => [p.x, p.y]));
  return <section className="result-section"><h4>{t(titleKey)}</h4><InteractiveScatterChart
    chartId={titleKey.replace(/\./g, "-")} title={t(titleKey)} description={t("reg.assumptions")}
    annotations={[]} emptyLabel={t("reg.empty")} formatValue={(v) => formatNumber(v, { maximumSignificantDigits: 4 })}
    xLabel={xLabel} yLabel={yLabel} xRange={identity ? range : paddedNumericRange(values.map((p) => p.x))}
    yRange={identity ? range : paddedNumericRange(values.map((p) => p.y))}
    referenceLines={identity ? [{ label: "y=x", x1: range.min, x2: range.max, y1: range.min, y2: range.max }] : []}
    points={values.map((p) => ({ ...p, id: String(p.row), className: "diagnostic-point",
      title: `${t("reg.row")} ${p.row + 1}`, ariaLabel: `${t("reg.row")} ${p.row + 1}, ${xLabel} ${formatNumber(p.x)}, ${yLabel} ${formatNumber(p.y)}`,
      details: [{ label: xLabel, value: formatNumber(p.x) }, { label: yLabel, value: formatNumber(p.y) }] }))} /></section>;
}

function RegularizationCurve({ result }: { result: RegularizedLinearModelResult }) {
  const { t, formatNumber } = useI18n();
  const [ratio, setRatio] = useState<number | null>(null);
  const r = result.regularization;
  const selectedRatio = r.cv_curve.some((row) => row.l1_ratio === ratio) ? ratio : r.selected_l1_ratio;
  const rows = r.cv_curve.filter((row) => row.l1_ratio === selectedRatio);
  const ratios = [...new Set(r.cv_curve.map((row) => row.l1_ratio))].filter((v): v is number => v !== null);
  const yRange = paddedNumericRange(rows.flatMap((row) => [row.mean_squared_error - row.fold_error_sd, row.mean_squared_error + row.fold_error_sd]));
  return <>{ratios.length > 1 ? <label><span>{t("reg.ratio")}</span><select value={selectedRatio ?? ""} onChange={(e) => setRatio(Number(e.currentTarget.value))}>
    {ratios.map((value) => <option key={value} value={value}>{value}</option>)}</select></label> : null}
    {rows.length ? <InteractiveScatterChart chartId="regularization-cv-curve" title={t("reg.curve")} description={t("reg.curveDescription")}
      annotations={[t("reg.curveDescription")]} emptyLabel={t("reg.empty")} formatValue={(v) => formatNumber(v, { maximumSignificantDigits: 4 })}
      xLabel="log10(alpha)" yLabel={t("reg.mse")} xRange={paddedNumericRange(rows.map((row) => Math.log10(row.alpha)))} yRange={yRange} connectPoints="line"
      referenceLines={[{ label: t("reg.selectedAlpha"), x1: Math.log10(r.selected_alpha), x2: Math.log10(r.selected_alpha), y1: yRange.min, y2: yRange.max },
        ...rows.map((row) => ({ label: `${t("reg.foldSd")} ${row.alpha}`, x1: Math.log10(row.alpha), x2: Math.log10(row.alpha), y1: row.mean_squared_error - row.fold_error_sd, y2: row.mean_squared_error + row.fold_error_sd }))]}
      points={rows.map((row) => ({ id: String(row.alpha), title: `alpha ${row.alpha}`, className: "diagnostic-point", x: Math.log10(row.alpha), y: row.mean_squared_error,
        ariaLabel: `alpha ${row.alpha}, ${t("reg.mse")} ${row.mean_squared_error}`, details: [{ label: t("reg.alpha"), value: String(row.alpha) },
          { label: t("reg.mse"), value: formatNumber(row.mean_squared_error) }, { label: t("reg.foldSd"), value: formatNumber(row.fold_error_sd) }] }))} /> : <p>{t("reg.fixedCurve")}</p>}
    <details><summary>{t("reg.curve")}</summary><div className="table-wrap"><table className="result-table"><thead><tr><th>alpha</th><th>{t("reg.ratio")}</th><th>{t("reg.mse")}</th><th>{t("reg.foldSd")}</th></tr></thead>
      <tbody>{r.cv_curve.map((row) => <tr key={`${row.alpha}-${row.l1_ratio}`}><td>{row.alpha}</td><td>{row.l1_ratio ?? "-"}</td><td>{formatNumber(row.mean_squared_error)}</td><td>{formatNumber(row.fold_error_sd)}</td></tr>)}</tbody></table></div></details>
  </>;
}

function RegularizationPath({ result }: { result: RegularizedLinearModelResult }) {
  const { t, formatNumber } = useI18n();
  const [feature, setFeature] = useState(0);
  const r = result.regularization;
  const yRange = paddedNumericRange(r.coefficient_path.map((row) => row.standardized_coefficients[feature]));
  const lines: ScatterReferenceLine[] = [{ label: t("reg.selectedAlpha"), x1: Math.log10(r.selected_alpha), x2: Math.log10(r.selected_alpha), y1: yRange.min, y2: yRange.max }];
  return <><label><span>{t("reg.pathFeature")}</span><select value={feature} onChange={(event) => setFeature(Number(event.currentTarget.value))}>
    {r.feature_order.map((name, index) => <option key={name} value={index}>{name}</option>)}</select></label>
    <InteractiveScatterChart chartId="regularization-coefficient-path" title={t("reg.path")} description={t("reg.pathDescription")}
      annotations={[t("reg.pathDescription")]} emptyLabel={t("reg.empty")} formatValue={(v) => formatNumber(v, { maximumSignificantDigits: 4 })}
      xLabel="log10(alpha)" yLabel={t("reg.standardized")} xRange={paddedNumericRange([Math.log10(r.selected_alpha), ...r.coefficient_path.map((row) => Math.log10(row.alpha))])} yRange={yRange}
      connectPoints="line" referenceLines={lines} points={r.coefficient_path.map((row) => ({ id: String(row.alpha), title: r.feature_order[feature],
        className: "diagnostic-point", x: Math.log10(row.alpha), y: row.standardized_coefficients[feature],
        ariaLabel: `${r.feature_order[feature]}, alpha ${row.alpha}, ${row.standardized_coefficients[feature]}`,
        details: [{ label: t("reg.alpha"), value: String(row.alpha) }, { label: r.feature_order[feature], value: formatNumber(row.standardized_coefficients[feature]) }] }))} />
    <details><summary>{t("reg.fullPath")}</summary><div className="table-wrap"><table className="result-table"><thead><tr><th>alpha</th>{r.feature_order.map((name) => <th key={name}>{name}</th>)}</tr></thead>
      <tbody>{r.coefficient_path.map((row) => <tr key={row.alpha}><th>{row.alpha}</th>{row.standardized_coefficients.map((value, index) => <td key={index}>{formatNumber(value)}</td>)}</tr>)}</tbody></table></div></details>
  </>;
}
