import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { PlanningDeletionCounts } from "./BayesianStudyDeletionPanel";

describe("planning deletion impact", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["ko", "en"] as const)("lists all planning dependencies in %s", locale => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<PlanningDeletionCounts counts={{ planning_model_count: 2, candidate_set_count: 3, candidate_revision_count: 5, planning_selection_count: 7, planning_confirmation_count: 11 }} />);
    expect(html).toContain(locale === "en" ? "Saved fitted models" : "저장 적합 모형");
    expect(html).toContain(locale === "en" ? "Batch confirmation records" : "배치 확정 기록");
    expect(html).toContain("<dd>2</dd>"); expect(html).toContain("<dd>3</dd>"); expect(html).toContain("<dd>5</dd>"); expect(html).toContain("<dd>7</dd>"); expect(html).toContain("<dd>11</dd>");
  });
  it("does not invent missing counts for an older response", () => {
    expect(renderToStaticMarkup(<PlanningDeletionCounts counts={{}} />)).toBe("");
    const html = renderToStaticMarkup(<PlanningDeletionCounts counts={{ planning_model_count: 0 }} />);
    expect(html).toContain("<dd>0</dd>"); expect(html.match(/<dd>-<\/dd>/g)).toHaveLength(4);
  });
});
