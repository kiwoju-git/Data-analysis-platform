import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../i18n/store";
import { aliasEquation, visibleAliasClasses, type FractionalMetadata } from "./aliasPresentation";
import { FractionalAliasSummary } from "./FractionalAliasSummary";

const metadata: FractionalMetadata = {
  catalog_entry_id: "synthetic",
  base_factor_count: 4, fraction_exponent: 1, fraction: "1/2", resolution: 5,
  generators: ["E=ABCD"], defining_relation: ["I", "ABCDE"], alias_groups: [["legacy = name"]],
  estimable_terms: [], non_estimable_terms: [], principal_fraction: true,
  alias_view_schema_version: 1,
  alias_classes: [
    [{ factor_indices: [], sign: 1, order: 0, compact_label: "I", full_label: "I" },
      { factor_indices: [0, 1, 2, 3, 4], sign: 1, order: 5, compact_label: "ABCDE", full_label: "A × odd = <B>" }],
    [{ factor_indices: [0, 1, 2], sign: 1, order: 3, compact_label: "ABC", full_label: "High order" }],
  ],
};

afterEach(() => setCurrentLocale("en"));

describe("structured alias presentation", () => {
  it("uses algebraic identity, never parses names to recover symbols", () => {
    expect(aliasEquation(metadata.alias_classes![0])).toBe("I = ABCDE");
    expect(aliasEquation(metadata.alias_classes![0], true)).toBe("I = A × odd = <B>");
    expect(visibleAliasClasses(metadata, 2)).toHaveLength(1);
    expect(visibleAliasClasses(metadata, null)).toHaveLength(2);
    expect(metadata.alias_classes).toHaveLength(2);
    expect(visibleAliasClasses({ ...metadata, alias_classes: undefined }, 2)).toBeNull();
  });

  it.each(["en", "ko"] as const)("preserves complete escaped names and details in %s", (locale) => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<FractionalAliasSummary design={{
      design_id: "synthetic", fractional: metadata,
      factors: [{ name: "A × odd = <B>", low: -1, high: 1, unit: "m/s" }],
    }} />);
    expect(html).toContain("I = ABCDE");
    expect(html).toContain("A × odd = &lt;B&gt;");
    expect(html).toContain("m/s");
    expect(html).toContain("<details");
    expect(html).not.toContain("legacy = name");
    expect(html).toContain(locale === "en" ? "Complete" : "전체");
  });
});
