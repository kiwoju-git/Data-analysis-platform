import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import type { DoeFractionalEstimability, DoeModelSelectionResult } from "../api/types/doeModelWorkflow";
import { DoeCompactPlotCard, DoeCompactPlotGrid } from "./DoeCompactPlotGrid";
import { defaultDoeSelection } from "./factorialWorkflowPresentation";
import { doePlotStatus } from "./doePlotStatus";

const selection: DoeModelSelectionResult = {
  ...defaultDoeSelection, tie_break_policy: "deterministic", initial_model_saturated: true,
  initial_parameter_count: 8, initial_residual_df: 0, target_pool_count: 1,
  initial_term_ids: ["retained", "removed", "pooled"], final_term_ids: ["retained"],
  removed_term_ids: ["removed"], pooled_term_ids: ["pooled"], initially_excluded_term_ids: ["excluded"],
  fixed_term_ids: ["intercept"], stop_reason: "complete", steps: [], post_selection_inference: "exploratory",
  term_catalog: [],
};
const plan: DoeFractionalEstimability = {
  policy: "actual_matrix", requested_parameter_count: 11, estimable_parameter_count: 8,
  rank: 8, expected_residual_df: 0, saturated: true, representative_term_ids: [],
  initially_excluded_term_ids: ["excluded"],
  exclusions: [{ term_id: "alias", reason: "complete_alias", representative_term_id: "retained", sign: 1 }],
  rank_tolerance: 1e-12, rank_scaling: "unit_column_norm",
};

it("uses committed status, never inventing backward removal from absent terms", () => {
  expect(["retained", "removed", "pooled", "excluded", "alias", "outside"].map((id) => doePlotStatus(id, selection, plan)))
    .toEqual(["retained", "backward_removed", "pooled", "user_excluded", "alias_nonestimable", "not_requested"]);
  expect(doePlotStatus("removed")).toBe("unknown");
});

it("keeps compact removed plots interactive and uses a real small layout", () => {
  const html = renderToStaticMarkup(<DoeCompactPlotGrid>
    <DoeCompactPlotCard title="AB" status="backward_removed" meanLabel="Data mean">
      {(layout) => <svg viewBox={`0 0 ${layout.width} ${layout.height}`}><circle tabIndex={0} /></svg>}
    </DoeCompactPlotCard>
  </DoeCompactPlotGrid>);
  expect(html).toContain('viewBox="0 0 280 210"');
  expect(html).toContain("backward_removed");
  expect(html).toContain('tabindex="0"');
  expect(html).not.toContain("pointer-events");
  expect(html).toContain("Data mean");
});
