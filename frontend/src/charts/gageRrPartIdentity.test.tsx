import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { GageRrResult } from "../api/types/analysisResultsQuality";
import { GageRrResultCharts } from "../GageRrResultCharts";
import { isGageRrResult } from "../gageRrRestore";
import { LocaleProvider } from "../i18n/LocaleProvider";
import { setCurrentLocale } from "../i18n/store";
import { t } from "../i18n/translate";
import { gageChartModels, gagePlotState } from "./gageRrChartModels";

const fixture = JSON.parse(readFileSync(new URL("../../../tests/fixtures/gage_rr_six_panel.json", import.meta.url), "utf8")) as { retain: GageRrResult };
const currentFixture = JSON.parse(readFileSync(new URL("../../../tests/fixtures/gage_rr_part_ids.json", import.meta.url), "utf8")) as { retain: GageRrResult };
const ids = Array.from({ length: 10 }, (_, index) => String(index + 1));

// These are display-contract fixtures, not independent ANOVA reference values.
function current(partIds = ids): GageRrResult {
  const source = structuredClone(currentFixture.retain);
  const bundle = source.plot_bundle!;
  return {
    ...source, schema_version: 4,
    plot_bundle: {
      ...bundle, schema_version: 2,
      parts: bundle.parts.map((part, index) => ({ ...part, part_id: partIds[index] })),
      calculation_metadata: {
        ...bundle.calculation_metadata, policy_version: "gage_rr_six_panel_v2",
        part_order: "natural_ascii_digit_runs_full_identity_v1",
        identifier_policy: "part_ids_preserved_operator_replicate_redacted",
      },
    },
  };
}

beforeEach(() => {
  setCurrentLocale("en");
  vi.stubGlobal("window", { localStorage: { getItem: () => "en" } });
});
afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("en"); });

describe("original Gage part identities", () => {
  it("uses actual IDs 1 through 10 for all part charts rather than a position-derived label", () => {
    const result = current();
    const before = JSON.stringify(result);
    expect(isGageRrResult(result)).toBe(true);
    expect(gagePlotState(result)).toBe("valid");
    const model = gageChartModels(result.plot_bundle!, 0, 0, t);
    expect(model.partTicks.map((tick) => tick.label)).toEqual(ids);
    expect(model.dispersion.xTicks.at(-1)?.label).toBe("10");
    expect(model.xbar.points.find((point) => point.id === "xbar:0:9")?.title).toBe("10 / Operator 1");
    expect(model.interaction.points.find((point) => point.id === "interaction:0:1")?.title).toBe("2 / Operator 1");
    expect(model.responsePart.points.find((point) => point.id === "part-mean:9")?.details)
      .toContainEqual({ label: "Part ID", value: "10" });
    expect(model.responsePart.points.find((point) => point.id === "part-mean:9")?.y).toBeCloseTo(68, 12);
    expect(model.responsePart.points.find((point) => point.id === "raw:55")?.title).toBe("10 / Operator 1");
    expect(JSON.stringify(result)).toBe(before);
  });

  it("keeps leading zeros and nonconsecutive IDs distinct without numeric coercion", () => {
    const result = current(["01", "1", "3", "7", "11", "19", "A2", "A10", "C", "D"]);
    const model = gageChartModels(result.plot_bundle!, 0, 0, t);
    expect(gagePlotState(result)).toBe("valid");
    expect(model.partTicks.slice(0, 2).map((tick) => tick.label)).toEqual(["01", "1"]);
    expect(model.responsePart.points.find((point) => point.id === "part-mean:0")?.title).toBe("01");
    expect(model.responsePart.points.find((point) => point.id === "part-mean:1")?.title).toBe("1");
  });

  it("validates the saved Python strip policy without adding JavaScript BOM trimming", () => {
    const preserved = current([...ids.slice(0, 9), "\uFEFF10"]);
    expect(gagePlotState(preserved)).toBe("valid");
    expect(gageChartModels(preserved.plot_bundle!, 0, 0, t).partTicks.at(-1)?.label).toBe("\uFEFF10");
    expect(gagePlotState(current([...ids.slice(0, 9), "\u0085ten"]))).toBe("invalid");
  });

  it("does not translate IDs or change point identity and coordinates on KO/EN/KO changes", () => {
    const result = current(["01", "1", "3", "7", "11", "19", "A2", "A10", "부품 B", "부품 C"]);
    const before = JSON.stringify(result);
    const baseline = gageChartModels(result.plot_bundle!, 0, 0, t);
    for (const locale of ["ko", "en", "ko"] as const) {
      setCurrentLocale(locale);
      const model = gageChartModels(result.plot_bundle!, 0, 0, t);
      expect(model.partSummaries.map((part) => part.label)).toEqual(baseline.partSummaries.map((part) => part.label));
      expect(model.responsePart.points.map(({ id, x, y }) => ({ id, x, y })))
        .toEqual(baseline.responsePart.points.map(({ id, x, y }) => ({ id, x, y })));
      expect(JSON.stringify(result)).toBe(before);
    }
  });

  it("keeps full colliding display prefixes separate in point detail and saved identity table", () => {
    const prefix = "한글".repeat(80);
    const result = current([...ids.slice(0, 8), prefix + "A", prefix + "B"]);
    const model = gageChartModels(result.plot_bundle!, 0, 0, t);
    expect(model.responsePart.points.find((point) => point.id === "part-mean:8")?.details)
      .toContainEqual({ label: "Part ID", value: prefix + "A" });
    expect(model.responsePart.points.find((point) => point.id === "part-mean:9")?.details)
      .toContainEqual({ label: "Part ID", value: prefix + "B" });
    expect(model.partSummaries.slice(-2).map((part) => part.label)).toEqual([prefix + "A", prefix + "B"]);
    expect(gagePlotState(result)).toBe("valid");
  });

  it.each(["missing", "blank", "space", "duplicate", "metadata", "result-version", "bundle-version"])("rejects malformed new %s identity without legacy fallback", (kind) => {
    const result = current();
    const bundle = result.plot_bundle! as unknown as { schema_version: number; parts: Record<string, unknown>[]; calculation_metadata: Record<string, unknown> };
    if (kind === "missing") delete bundle.parts[0].part_id;
    if (kind === "blank") bundle.parts[0].part_id = "";
    if (kind === "space") bundle.parts[0].part_id = " 1 ";
    if (kind === "duplicate") bundle.parts[1].part_id = bundle.parts[0].part_id;
    if (kind === "metadata") bundle.calculation_metadata.identifier_policy = "zero_based_indices_original_labels_redacted";
    if (kind === "result-version") result.schema_version = 3;
    if (kind === "bundle-version") bundle.schema_version = 1;
    expect(gagePlotState(result)).toBe("invalid");
  });

  it.each(["en", "ko"] as const)("shows escaped full user IDs in accessible details and preserves them in %s", (locale) => {
    vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
    const long = '부품 <script>alert("synthetic")</script> ' + "X".repeat(130);
    const result = current([...ids.slice(0, 9), long]);
    const before = JSON.stringify(result);
    const html = renderToStaticMarkup(<LocaleProvider><GageRrResultCharts result={result} sourceKey="synthetic:source:4" /></LocaleProvider>);
    expect(html).toContain('data-gage-part-identities="original"');
    expect(html).toContain('data-gage-part-index="9"');
    expect(html).toContain("부품 &lt;script&gt;alert(&quot;synthetic&quot;)&lt;/script&gt; " + "X".repeat(130));
    expect(html).not.toContain("<script>");
    expect(html).toContain(locale === "en" ? "Part ID" : "부품 ID");
    expect(JSON.stringify(result)).toBe(before);
  });

  it("labels legacy indices as display numbers and never invents original IDs", () => {
    const result = structuredClone(fixture.retain);
    const before = JSON.stringify(result);
    const model = gageChartModels(result.plot_bundle!, 0, 0, t);
    expect(model.responsePart.points.find((point) => point.id === "part-mean:1")?.title).toBe("Display 2");
    const html = renderToStaticMarkup(<LocaleProvider><GageRrResultCharts result={result} sourceKey="legacy:3" /></LocaleProvider>);
    expect(html).toContain('data-gage-part-identity="legacy"');
    expect(html).toContain("Reanalyze");
    expect(html).not.toContain('data-gage-part-identities="original"');
    expect(JSON.stringify(result)).toBe(before);
  });
});
