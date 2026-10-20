import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../i18n/store";
import { CcdBoundsPreview } from "./CcdBoundsPreview";

describe("CCD range disclosure", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["ko", "en"] as const)("keeps narrow distinct endpoints visible in %s", (locale) => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<CcdBoundsPreview ccdType="circumscribed" factors={
      [1, 2, 3, 4].map((id) => ({ id, name: `Factor ${id}`, unit: "g", low: "1000", high: "1000.0001" }))
    } />);
    expect(html).toContain("[1,000, 1,000.0001]");
    expect(html).toContain("[999.99995, 1,000.0002]");
    const exact = [...html.matchAll(/<p>[^[]*\[([^,]+), ([^\]]+)\]<\/p>/g)];
    expect(exact).toHaveLength(8);
    expect(Number(exact[1][1])).toBeCloseTo(999.99995, 10);
    expect(Number(exact[1][2])).toBeCloseTo(1000.00015, 10);
    expect(html).toContain("Factor 1 (g)");
  });
});
