import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianTargetCurvePreview } from "./BayesianTargetCurvePreview";
import { curvePreviewRequest, initialCurvePreviewDraft } from "./boCurvePreviewDraft";
import { buildVectorObjective, newResponseDraft } from "./bayesianVectorDraft";

const goal = { ...newResponseDraft(1), goal: "match_target" as const, lower: "-2", target: "0", upper: "3", name: "측정 <raw>" };
afterEach(() => setCurrentLocale("ko"));
it("keeps preview separate from the study policy and uses explicit assumptions only", () => {
  const before = JSON.stringify(goal);
  const draft = initialCurvePreviewDraft();
  const request = curvePreviewRequest(goal, draft)!;
  expect(request.controls.peak).toBe(1);
  expect(request.assumed_distribution).toBeNull();
  expect(request.plot_lower).toBe(-3.25);
  expect(curvePreviewRequest(goal, { ...draft, assumed: true })).toBeNull();
  expect(curvePreviewRequest(goal, { ...draft, assumed: true, mean: "1e-6", sd: "0", incumbent: ".5" })?.assumed_distribution?.mean).toBe(1e-6);
  expect(JSON.stringify(goal)).toBe(before);
  expect(buildVectorObjective("Synthetic", [goal])).toHaveProperty("curve_policy", "derringer_suich_linear_v1");
});
it.each(["", " ", "1e", "NaN", "Infinity", "0", "1", "-.1"])("rejects invalid side ordinates: %s", value => {
  expect(curvePreviewRequest(goal, { ...initialCurvePreviewDraft(), lower: value })).toBeNull();
});
it.each(["en", "ko"] as const)("renders a distinct, escaped, non-persistent comparison boundary (%s)", locale => {
  setCurrentLocale(locale);
  const html = renderToStaticMarkup(<BayesianTargetCurvePreview goals={[goal]} sourceKey="synthetic" />);
  expect(html).toContain("측정 &lt;raw&gt;");
  expect(html).toContain(locale === "en" ? "not saved or applied to recommendations" : "저장하거나 추천에 적용하지 않습니다");
  expect(html).not.toContain("dangerouslySetInnerHTML");
});
