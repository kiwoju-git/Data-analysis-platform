import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { mixtureFixture } from "./boMixture.test.fixture";
import { BayesianMixtureWorkspace, MixtureAppliedSelectionSettings } from "./BayesianMixtureWorkspace";
import { BayesianMixtureDiagnostics } from "./BayesianMixtureDiagnostics";
import { BayesianMixtureProgress } from "./BayesianMixtureProgress";
import { planningMessages } from "../../i18n/boPlanning";

describe("mixture lifecycle display boundaries", () => {
  afterEach(() => setCurrentLocale("ko"));
  it("renders measured amounts and actual response progress without implicit fit", () => {
    setCurrentLocale("en");
    const { study } = mixtureFixture();
    const html = renderToStaticMarkup(<BayesianMixtureWorkspace study={study} disabled={false} onRefresh={vi.fn()} onBusyChange={vi.fn()} />);
    expect(html).toContain("Observation entry");
    expect(html).toContain("Measured responses, not predictions or causal effects");
    expect(html).toContain("Amount A");
    expect(html).toContain("fixed-candidate posterior and maximin planning");
    expect(html).not.toContain("NaN");
    const replicate = html.match(/<details\b[^>]*>\s*<summary>Add replicate<\/summary>/);
    expect(replicate).not.toBeNull();
    expect(replicate?.[0]).not.toContain("open=");
  });
  it("uses a valid actual point for holds, with no independent-low fallback", () => {
    setCurrentLocale("en");
    const { study, model } = mixtureFixture();
    const html = renderToStaticMarkup(<BayesianMixtureDiagnostics study={study} model={model} disabled={false} />);
    expect(html).toContain('value="0.2"');
    expect(html).toContain('value="0.8"');
    expect(html).toContain("co-vary");
    expect(html).toContain("not isolated component effects");
    expect(html).not.toContain("Component sum or bounds do not match");
    expect(html).toContain("120"); expect(html).toContain("1,000"); expect(html).toContain("21");
  });
  it("shows immutable applied selection policy, budget and minimum distance", () => {
    setCurrentLocale("en"); const { selection } = mixtureFixture();
    const html = renderToStaticMarkup(<MixtureAppliedSelectionSettings config={{ ...selection.config, policy: "greedy_mixture_maximin_v1", total_trial_budget: 20, min_batch_distance: .2 }} />);
    expect(html).toContain("greedy_mixture_maximin_v1"); expect(html).toContain("20"); expect(html).toContain("0.2");
  });
  it.each(["ko", "en"] as const)("shows shared profiler budgets and category coverage before evaluation in %s", locale => {
    setCurrentLocale(locale); const { study, model } = mixtureFixture();
    const html = renderToStaticMarkup(<BayesianMixtureDiagnostics study={study} model={model} disabled={false} />);
    expect(html).toContain(planningMessages(locale).matrixBudget);
    expect(html).toContain(locale === "ko" ? "선언된 전체 수준" : "all declared levels");
    expect(html).toContain("21");
  });
  it("shows no completed observations rather than a fabricated zero curve", () => {
    setCurrentLocale("en"); const { study } = mixtureFixture(false);
    const html = renderToStaticMarkup(<BayesianMixtureProgress study={study} />);
    expect(html).toContain("No completed observations"); expect(html).not.toContain("<svg");
  });
});
