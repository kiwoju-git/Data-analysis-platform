import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it } from "vitest";
import { setCurrentLocale } from "../i18n/store";
import { DoeResidualPlots } from "./DoeResidualPlots";

afterEach(() => setCurrentLocale("en"));

it.each(["en", "ko"] as const)("shows four saved residual views, units, counts and raw identity in %s", (locale) => {
  setCurrentLocale(locale);
  const view = { n: 12, n_available: 12, n_displayed: 2,
    histogram: [{ lower: -1e-6, upper: 1e-6, count: 12 }],
    qq_points: [{ run_order: 3, theoretical_quantile: -1, residual: -5e-7 }, { run_order: 7, theoretical_quantile: 1, residual: 5e-7 }],
    reference_line: { slope: 5e-7, intercept: 0 },
    points: [{ run_order: 3, fitted: 10, residual: -5e-7 }, { run_order: 7, fitted: 12, residual: 5e-7 }] };
  const plots = { raw: view, standardized: view, n_total: 12, point_limit: 2, truncated: true };
  const html = renderToStaticMarkup(<DoeResidualPlots plots={plots} sourceKey="analysis:revision-hash" responseUnit="kg<script>" defaultOpen />);
  expect(html.match(/class="chart-frame-svg"/g)).toHaveLength(4);
  expect(html).toContain('open=""');
  expect(html).toContain("N = 12");
  expect(html).toContain("kg&lt;script&gt;");
  expect(html).not.toContain("<script>");
  expect(html).toContain("5e-7");
  expect(html).toContain('tabindex="0"');
  expect(html).toContain('value="raw" selected');
  expect(html).toContain('value="standardized"');
  expect(html).not.toContain("studentized");
});
