import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { mixedMessages } from "../../i18n/boMixed";
import { BayesianMixedStudyBuilder } from "./BayesianMixedStudyBuilder";

describe("mixed study builder accessible select names", () => {
  afterEach(() => setCurrentLocale("ko"));

  it.each(["en", "ko"] as const)("names select controls independently of option text in %s", locale => {
    setCurrentLocale(locale);
    const text = mixedMessages(locale);
    const html = renderToStaticMarkup(<BayesianMixedStudyBuilder
      ownerKey="synthetic-owner"
      disabled={false}
      onCreated={() => undefined}
      onCancel={() => undefined}
      onBusyChange={() => undefined}
    />);
    const selects = html.match(/<select\b[^>]*>/g) ?? [];
    expect(selects.filter(select => select.includes(`aria-label="${text.kind}"`))).toHaveLength(2);
    expect(selects.filter(select => select.includes(`aria-label="${text.correlation}"`))).toHaveLength(1);
    expect(html).toContain('value="continuous" selected=""');
    expect(html).toContain('value="nominal" selected=""');
    expect(html).toContain('value="equal_positive_correlation_v1" selected=""');
  });
});
