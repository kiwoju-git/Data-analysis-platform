import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import { AnalysisMethodNavigation } from "./AnalysisMethodNavigation";
import { setCurrentLocale } from "./i18n/store";

afterEach(() => setCurrentLocale("en"));

describe("compact method navigation", () => {
  it("keeps the domain landing visible before selecting a method", () => {
    const html = renderToStaticMarkup(
      <AnalysisMethodNavigation selectedMethodId={null}>
        <button type="button">Principal Components Analysis</button>
      </AnalysisMethodNavigation>,
    );
    expect(html).not.toContain("<details");
    expect(html).toContain("Principal Components Analysis");
  });

  it.each(["en", "ko"] as const)("offers a closed, native disclosure in %s", (locale) => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(
      <AnalysisMethodNavigation selectedMethodId="regression.linear_model">
        <button type="button">PLS</button>
      </AnalysisMethodNavigation>,
    );
    expect(html).toContain('<details class="analysis-method-navigation">');
    expect(html).not.toMatch(/<details[^>]*\bopen/);
    expect(html).toContain(locale === "en" ? "Change analysis" : "분석 변경");
    expect(html).toContain("<summary>");
    expect(html).toContain("PLS");
  });
});
