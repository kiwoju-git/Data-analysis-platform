import { describe, expect, it } from "vitest";
import { validDatasetImportedInitialDesign } from "./boDatasetSource";
import { buildDesirabilityRequest, defaultDesirabilityDraft } from "./bayesianDesirabilityDraft";
import { desirabilityFixture } from "./bayesianDesirability.fixture";
import { mixedStudyFixture } from "./boMixed.test.fixture";
import { validMixedStudy } from "./boMixedDraft";
import { apiRequestError } from "../../api/client";
import { datasetImportErrorNotice } from "../../i18n/boDatasetImport";

function receipt(n: number) {
  return {
    policy: "dataset_observations_v1", import_schema_version: 1,
    n_total: n, n_filtered: 0, n_missing: 0, n_used: n,
    requested_size: n, generated_size: n, unique_coordinate_count: n,
    repeated_coordinate_count: 0, conflicting_coordinate_count: 0, warnings: [],
    source: { dataset_id: "00000000-0000-0000-0000-000000000001", dataset_version_id: "00000000-0000-0000-0000-000000000002",
      schema_hash: "a".repeat(64), canonical_sha256: "b".repeat(64), raw_sha256: "c".repeat(64), filter_sha256: "d".repeat(64) },
    preflight_sha256: "e".repeat(64), observations_sha256: "f".repeat(64), request_sha256: "a".repeat(64),
    request_id: "00000000-0000-0000-0000-000000000003", runtime_provenance: {}, missing_policy: "reject",
    source_row_indices: Array.from({ length: n }, (_, i) => i), factor_columns: { x: "x" }, response_columns: { y: "y" },
    filter_snapshot: { expression_version: 1, conditions: [] },
  };
}

describe("bounded 500-trial BO capacity", () => {
  it.each([200, 201, 240, 500])("reads all %i imported rows without altering their receipt", n => {
    const value = receipt(n), before = JSON.stringify(value);
    expect(validDatasetImportedInitialDesign(value)).toBe(true);
    expect(JSON.stringify(value)).toBe(before);
  });
  it("rejects 501 imported rows instead of accepting a truncated prefix", () => {
    expect(validDatasetImportedInitialDesign(receipt(501))).toBe(false);
  });
  it.each([240, 500])("preserves the repeated/conflicting counts of %i observations", n => {
    const value = { ...receipt(n), unique_coordinate_count: n / 2, repeated_coordinate_count: n / 2, conflicting_coordinate_count: n / 2 };
    expect(validDatasetImportedInitialDesign(value)).toBe(true);
  });
  it("permits a 500 budget, rejects 501, and never admits a partial last batch", () => {
    const { study } = desirabilityFixture(); study.recommendation_hard_trial_limit = 500; study.trial_count = 499;
    const draft = { ...defaultDesirabilityDraft(study), totalBudget: "500" };
    expect(buildDesirabilityRequest(study, draft).request).toMatchObject({ total_trial_budget: 500, batch_size: 1 });
    expect(buildDesirabilityRequest(study, { ...draft, batchSize: "2" }).errors.totalBudget).toBe("budget");
    expect(buildDesirabilityRequest(study, { ...draft, totalBudget: "501" }).errors.totalBudget).toBe("budget");
    study.trial_count = 500;
    expect(buildDesirabilityRequest(study, draft).errors.totalBudget).toBe("budget");
    expect(buildDesirabilityRequest(study, draft, "planning").request).not.toBeNull();
  });
  it("suggests room for new trials after a 240-row import without changing old requests", () => {
    const { study } = desirabilityFixture(); study.recommendation_hard_trial_limit = 500; study.trial_count = 240;
    const draft = defaultDesirabilityDraft(study);
    expect(Number(draft.totalBudget)).toBeGreaterThan(240);
    expect(Number(draft.totalBudget)).toBeLessThanOrEqual(500);
    expect(buildDesirabilityRequest(study, draft).request).not.toBeNull();
    study.trial_count = 2;
    const legacy = { ...defaultDesirabilityDraft(study), totalBudget: "200" }, before = JSON.stringify(legacy);
    expect(buildDesirabilityRequest(study, legacy).request?.total_trial_budget).toBe(200);
    expect(JSON.stringify(legacy)).toBe(before);
  });
  it.each([240, 500, 501])("checks the complete %i-trial mixed study rather than a 200-row prefix", n => {
    const study = mixedStudyFixture();
    study.trials = Array.from({ length: n }, (_, i) => ({ ...study.trials[i % study.trials.length], trial_id: `00000000-0000-0000-0000-${String(i).padStart(12, "0")}`, trial_number: i + 1 }));
    study.trial_count = n; study.completed_trial_count = n;
    expect(validMixedStudy(study)).toBe(n <= 500);
  });
  it("retains only safe import-limit counts from the single parsed API error", async () => {
    const response = new Response(JSON.stringify({ error: { code: "bayesian_import_trial_limit", correlation_id: "safe",
      limits: { observed_count: 501, maximum_count: 500, raw: "PRIVATE_CELL" }, developer_detail: "PRIVATE_PATH" } }), { status: 409 });
    const error = await apiRequestError(response, "fallback");
    expect(error).toMatchObject({ limits: { observed_count: 501, maximum_count: 500 } });
    expect(JSON.stringify(error)).not.toContain("PRIVATE_CELL");
    expect(JSON.stringify(error)).not.toContain("PRIVATE_PATH");
  });
  it.each([null, { observed_count: -1, maximum_count: 500 }, { observed_count: "501", maximum_count: 500 },
    { observed_count: 501, maximum_count: 0 }, { observed_count: 501.5, maximum_count: 500 }])("rejects invalid limit metadata %j", async limits => {
    const error = await apiRequestError(new Response(JSON.stringify({ error: { code: "bayesian_import_trial_limit", limits } }), { status: 409 }), "fallback");
    expect(error.limits).toBeNull();
  });
  it("never attaches counts from an unrelated error", async () => {
    const error = await apiRequestError(new Response(JSON.stringify({ error: { code: "other", limits: { observed_count: 501, maximum_count: 500 } } }), { status: 409 }), "fallback");
    expect(error.limits).toBeNull();
  });
  it.each(["ko", "en"] as const)("shows usable count and maximum with explicit recovery in %s", locale => {
    const message = datasetImportErrorNotice(locale, "bayesian_import_trial_limit", { observed_count: 501, maximum_count: 500 });
    expect(message).toContain("501"); expect(message).toContain("500");
    expect(message).toContain(locale === "en" ? "No rows were automatically sampled or changed" : "행을 자동으로 추출하거나 변경하지 않았습니다");
    expect(datasetImportErrorNotice(locale, "bayesian_import_trial_limit")).not.toContain("undefined");
  });
});
