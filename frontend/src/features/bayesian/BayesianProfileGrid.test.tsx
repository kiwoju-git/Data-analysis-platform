import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianProfileGrid } from "./BayesianProfileGrid";

describe("profile constraint presentation", () => {
  afterEach(() => setCurrentLocale("ko"));

  it.each(["en", "ko"] as const)("keeps infeasible predictions visible and explicit in %s", locale => {
    setCurrentLocale(locale);
    const rows = [0, 1, 2].map(index => ({
      row_id: `row-${index}`, actual_coordinates: { x: index },
      response_predictions: [{ response_id: "yield", mean_raw: 100 + index }],
      desirability_moments: { mean: index / 4 }, constraints_satisfied: index !== 1,
    }));
    const original = JSON.stringify(rows);
    const html = renderToStaticMarkup(<BayesianProfileGrid sourceKey="saved-model:hold-snapshot"
      axis={{ factor_id: "x", name: "User <X>", unit: "mg", category: false }}
      responses={[{ response_id: "yield", name: "Yield", unit: "%" }]} rows={rows} />);
    expect(html).toContain(locale === "en" ? "Outside the stored constraints." : "저장된 제약 조건을 벗어납니다.");
    expect((html.match(/data-point-id=/g) ?? [])).toHaveLength(6);
    expect(html).toMatch(/<polygon[^>]*data-point-id="row-1"[^>]*data-x="1" data-y="101"/);
    expect(html).toContain(locale === "en" ? "Constraint status" : "제약 상태");
    expect(html).toContain("User &lt;X&gt;");
    expect(JSON.stringify(rows)).toBe(original);
  });
});
