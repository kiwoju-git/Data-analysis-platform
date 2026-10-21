import { describe, expect, it } from "vitest";

import { apiRoutes } from "./routes";

describe("Bayesian replicate route contract", () => {
  it("encodes both owner IDs through the shared path builder", () => {
    expect(apiRoutes.bayesianReplicates("study/1", "trial?2")).toBe(
      "/api/v1/bayesian-studies/study%2F1/trials/trial%3F2/replicates",
    );
  });
});
