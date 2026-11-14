import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { mixtureMessages } from "../../i18n/boMixture";
import { BayesianMixtureStudyBuilder } from "./BayesianMixtureStudyBuilder";

describe("mixture setup in the existing workflow", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["ko", "en"] as const)("renders explicit total, unit, bounds and coding in %s", locale => {
    setCurrentLocale(locale);
    const text = mixtureMessages(locale);
    const html = renderToStaticMarkup(<BayesianMixtureStudyBuilder ownerKey="new" disabled={false} onCreated={() => undefined} onCancel={() => undefined} onBusyChange={() => undefined} />);
    expect(html).toContain(text.total);
    expect(html).toContain(text.unit);
    expect(html).toContain(`aria-label="${text.coding}"`);
    expect(html).toContain(text.closure);
    expect(html).toContain(text.addProcess);
    expect(html).toContain(text.lower);
    expect(html).toContain(text.upper);
    expect(html).not.toContain("NaN");
  });
});
