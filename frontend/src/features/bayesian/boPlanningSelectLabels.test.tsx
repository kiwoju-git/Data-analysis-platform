import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { planningMessages } from "../../i18n/boPlanning";
import { augmentationMessages } from "../../i18n/boAugmentation";
import { BayesianPlanningPanel } from "./BayesianPlanningPanel";
import { BayesianAugmentationPanel } from "./BayesianAugmentationPanel";
import { augmentationFixture } from "./boAugmentation.fixture";

const state = vi.hoisted(() => ({ modelBased: false }));

vi.mock("./hooks/useBayesianPlanning", async importOriginal => {
  const actual = await importOriginal<typeof import("./hooks/useBayesianPlanning")>();
  return { ...actual, useBayesianPlanning(props: Parameters<typeof actual.useBayesianPlanning>[0]) {
    return { ...actual.useBayesianPlanning(props), model: augmentationFixture(true).model };
  } };
});

vi.mock("./hooks/useBayesianAugmentation", async importOriginal => {
  const actual = await importOriginal<typeof import("./hooks/useBayesianAugmentation")>();
  return { ...actual, useBayesianAugmentation(props: Parameters<typeof actual.useBayesianAugmentation>[0]) {
    const original = actual.useBayesianAugmentation(props);
    return state.modelBased ? { ...original, draft: augmentationFixture(true).draft } : original;
  } };
});

function expectSelectNames(html: string, labels: readonly string[]) {
  const selects = html.match(/<select\b[^>]*>/g) ?? [];
  for (const label of labels) {
    expect(selects.filter(select => select.includes(`aria-label="${label}"`))).toHaveLength(1);
  }
}

describe("planning select accessible names", () => {
  afterEach(() => { setCurrentLocale("ko"); state.modelBased = false; });

  it.each(["en", "ko"] as const)("names saved sources and profiler axes independently of option text in %s", locale => {
    setCurrentLocale(locale);
    const { study } = augmentationFixture(true), text = planningMessages(locale);
    const html = renderToStaticMarkup(<BayesianPlanningPanel study={study} fitRequest={null} onConfirmed={vi.fn()} />);
    expectSelectNames(html, [text.models, text.sets, text.savedSelections, text.axis]);
  });

  it.each(["en", "ko"] as const)("names augmentation strategy and sources in both model-free and model-based states in %s", locale => {
    setCurrentLocale(locale);
    const { study } = augmentationFixture(), text = augmentationMessages(locale), common = planningMessages(locale);
    const render = () => renderToStaticMarkup(<BayesianAugmentationPanel study={study} disabled={false} onConfirmed={vi.fn()} onConfirmingChange={vi.fn()} />);
    const modelFree = render();
    // A model can inform Auto advice without becoming the model-free selection's source.
    expectSelectNames(modelFree, [common.sets, text.policy, common.models]);
    state.modelBased = true;
    expectSelectNames(render(), [common.sets, text.policy, common.models]);
  });
});
