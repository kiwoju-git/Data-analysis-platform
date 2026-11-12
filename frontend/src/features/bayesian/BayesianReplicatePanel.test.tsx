import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianReplicatePanel } from "./BayesianReplicatePanel";
import { desirabilityFixture } from "./bayesianDesirability.fixture";
import type { useBayesianReplicateState } from "./hooks/useBayesianReplicateState";

afterEach(() => setCurrentLocale("ko"));
it("initially collapses replicate controls while keeping retry/error outside disclosure", () => {
  setCurrentLocale("en"); const { study } = desirabilityFixture();
  const state = { count: "1", parentId: "", confirmed: false, isRunning: false, error: "network", canRetry: true,
    created: null, setCount: () => {}, setParentId: () => {}, setConfirmed: () => {} } as unknown as ReturnType<typeof useBayesianReplicateState>;
  const html = renderToStaticMarkup(<BayesianReplicatePanel study={study} state={state} totalBudget="40" disabled={false} onSubmit={() => {}} onRefresh={() => {}} />);
  expect(html).toMatch(/<details[^>]*><summary[^>]*>Explicit replicate experiments<\/summary>/);
  expect(html).not.toMatch(/<details[^>]*open/);
  expect(html.indexOf("Check / retry identical request")).toBeGreaterThan(html.indexOf("</details>"));
  expect(html.indexOf('role="alert"')).toBeGreaterThan(html.indexOf("</details>"));
});
