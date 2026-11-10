import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { AugmentationSelectionDetails } from "./BayesianAugmentationPanel";
import { augmentationFixture } from "./boAugmentation.fixture";

describe("automatic augmentation presentation", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["ko", "en"] as const)("keeps model-free points free of invented response values in %s", locale => {
    setCurrentLocale(locale); const { selection, study } = augmentationFixture();
    const before = JSON.stringify(selection);
    study.factors[0].name = "온도 <user>";
    const html = renderToStaticMarkup(<AugmentationSelectionDetails selection={selection} study={study} />);
    expect(html).toContain("온도 &lt;user&gt;"); expect(html).toContain(selection.selection_id); expect(html).toContain(selection.result_sha256);
    expect(html).toContain(locale === "en" ? "Not evaluated" : "미평가"); expect(html).toContain(locale === "en" ? "Natural log" : "자연로그");
    expect(html).not.toContain("<input"); expect(html).not.toContain("New-measurement predictive SD"); expect(JSON.stringify(selection)).toBe(before);
  });
  it.each(["ko", "en"] as const)("preserves response units and latent/predictive distinctions in %s", locale => {
    setCurrentLocale(locale); const { selection, study } = augmentationFixture(true);
    const html = renderToStaticMarkup(<AugmentationSelectionDetails selection={selection} study={study} />);
    expect(html).toContain("Yield &lt;raw&gt;"); expect(html).toContain("1e-8");
    expect(html).toContain(locale === "en" ? "Latent SD" : "잠재 SD"); expect(html).toContain(locale === "en" ? "New-measurement predictive SD" : "새 측정 예측 SD");
    expect(html).toContain(locale === "en" ? "read-only" : "읽기 전용");
  });
});
