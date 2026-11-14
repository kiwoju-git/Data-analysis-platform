import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { PlanningDeletionCounts } from "./BayesianStudyDeletionPanel";

describe("planning deletion impact", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["ko", "en"] as const)("lists all planning dependencies in %s", locale => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<PlanningDeletionCounts counts={{ planning_model_count: 2, candidate_set_count: 3, candidate_revision_count: 5, planning_selection_count: 7, planning_confirmation_count: 11, augmentation_renewal_count: 13, saved_view_count: 17 }} />);
    expect(html).toContain(locale === "en" ? "Saved fitted models" : "저장 적합 모형");
    expect(html).toContain(locale === "en" ? "Batch confirmation records" : "배치 확정 기록");
    expect(html).toContain(`<dt>${locale === "en" ? "Recommendation renewal links" : "추천 재검토 연결"}</dt><dd>13</dd>`);
    expect(html).toContain(`<dt>${locale === "en" ? "Saved diagnostic views" : "저장된 진단 그래프"}</dt><dd>17</dd>`);
    expect(html).toContain("<dd>2</dd>"); expect(html).toContain("<dd>3</dd>"); expect(html).toContain("<dd>5</dd>"); expect(html).toContain("<dd>7</dd>"); expect(html).toContain("<dd>11</dd>");
  });
  it.each(["ko", "en"] as const)("does not invent missing counts for an older response in %s", locale => {
    setCurrentLocale(locale);
    expect(renderToStaticMarkup(<PlanningDeletionCounts counts={{}} />)).toBe("");
    const html = renderToStaticMarkup(<PlanningDeletionCounts counts={{ planning_model_count: 0 }} />);
    expect(html).toContain(`<dt>${locale === "en" ? "Saved fitted models" : "저장 적합 모형"}</dt><dd>0</dd>`);
    expect(html.match(/<dd>0<\/dd>/g)).toHaveLength(1);
    expect(html.match(/<dd>-<\/dd>/g)).toHaveLength(6);
    expect(html).toContain(`<dt>${locale === "en" ? "Recommendation renewal links" : "추천 재검토 연결"}</dt><dd>-</dd>`);
    expect(html).toContain(`<dt>${locale === "en" ? "Saved diagnostic views" : "저장된 진단 그래프"}</dt><dd>-</dd>`);
  });
});
