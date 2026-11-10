import { describe, expect, it } from "vitest";
import { initialMixedFit, initialMixedSelection, mixedDefaultPoint, mixedFitOptions, mixedProfilePoints, mixedSelectionRequest, sameMixedExecutableInput, validMixedBatch, validMixedModel, validMixedPage, validMixedPrediction, validMixedReportSource, validMixedSelection } from "./boMixedPlanningDraft";
import { mixedPlanningFixture } from "./boMixedPlanning.test.fixture";
import { createPlanningCommitFence, createPlanningRequestFence } from "./boPlanningDraft";

describe("mixed planning strict source and draft contract", () => {
  it("accepts exact typed model/candidate/selection/batch ownership without changing source bytes", () => {
    const fixture = mixedPlanningFixture(), before = JSON.stringify(fixture);
    expect(validMixedModel(fixture.model, fixture.study)).toBe(true); expect(validMixedPage(fixture.page, fixture.study)).toBe(true);
    expect(validMixedSelection(fixture.selection, fixture.study, fixture.selection.request)).toBe(true); expect(validMixedBatch(fixture.batch, fixture.study, fixture.batch.batch_id)).toBe(true);
    expect(validMixedReportSource(fixture.descriptor, fixture.batch)).toBe(true); expect(JSON.stringify(fixture)).toBe(before);
  });
  it.each(["owner", "hash", "category", "coordinate", "rank", "payload"])("rejects corrupted saved %s", kind => {
    const { batch, study, descriptor } = mixedPlanningFixture();
    if (kind === "owner") batch.study_version_id = "wrong";
    if (kind === "hash") batch.source.rows_sha256 = "f".repeat(64);
    if (kind === "category") batch.items[0].current_trial.actual_coordinates.material = "unseen";
    if (kind === "coordinate") batch.items[0].current_trial.encoded_coordinates.material = 1;
    if (kind === "rank") batch.items[0].rank = 2;
    if (kind === "payload" && descriptor.source.kind === "bayesian_history_revision" && descriptor.source.attachment.kind === "batch") descriptor.source.attachment.result_payload_sha256 = "d".repeat(64);
    expect(kind === "payload" ? validMixedReportSource(descriptor, batch) : validMixedBatch(batch, study, batch.batch_id)).toBe(false);
  });
  it("keeps category codes out of fit numeric kernel options and validates complete numeric drafts", () => {
    const { study } = mixedPlanningFixture(), draft = initialMixedFit(study);
    expect(mixedFitOptions(study, draft)?.fit_policy.policy).toBe("bounded_typed_factor_starts_v1");
    for (const value of ["", " ", "10abc", "1.5", "Infinity"]) expect(mixedFitOptions(study, { ...draft, evaluations: value })).toBeNull();
    expect(mixedFitOptions(study, { ...draft, models: draft.models.map(model => ({ ...model, noise: "fixed", fixedSd: "1e-8" })) })?.response_models[0].surrogate.fixed_noise_sd).toBe(1e-8);
    expect(mixedFitOptions(study, { ...draft, models: draft.models.map(model => ({ ...model, lower: "2", upper: "1" })) })).toBeNull();
  });
  it("supports explicit model-free mixed maximin but never nominal MaxPro or implicit ordinal distances", () => {
    const { study, page, model } = mixedPlanningFixture(), draft = { ...initialMixedSelection(), kind: "augmentation" as const };
    const request = mixedSelectionRequest(study, page, null, [], draft, "request");
    expect(request?.model_id).toBeNull(); expect(request?.ordinal_rank_distance).toBe(false);
    expect(mixedSelectionRequest(study, page, model, [], { ...draft, policy: "greedy_incremental_maxpro_v1" }, "request")).toBeNull();
    expect(mixedSelectionRequest(study, page, null, [], { ...draft, policy: "refine_ei_alternating_desirability_response_sd_v2" }, "request")).toBeNull();
  });
  it("requires exact current history/candidate trial count and manual order", () => {
    const { study, page, model } = mixedPlanningFixture(), ids = page.items.map(row => row.row_id).reverse();
    expect(mixedSelectionRequest(study, page, model, ids, initialMixedSelection(), "request")?.row_ids).toEqual(ids);
    expect(mixedSelectionRequest(study, page, model, [ids[0], ids[0]], initialMixedSelection(), "request")).toBeNull();
    expect(mixedSelectionRequest({ ...study, pending_trial_count: 1 }, page, model, ids, initialMixedSelection(), "request")).toBeNull();
    expect(mixedSelectionRequest(study, { ...page, revision: { ...page.revision, source_trial_count: study.trial_count - 1 } }, model, ids, initialMixedSelection(), "request")).toBeNull();
    expect(mixedSelectionRequest(study, page, { ...model, source_is_current: false }, ids, initialMixedSelection(), "request")).toBeNull();
  });
  it("profiles categories as exact declared levels and discrete coordinates on the original decimal lattice", () => {
    const { study } = mixedPlanningFixture();
    expect(mixedDefaultPoint(study).material).toBe("001");
    expect(mixedProfilePoints(study, { x: .3, material: "001" }, "material")).toEqual([{ x: .3, material: "001" }, { x: .3, material: "한글 A" }]);
    study.factors[0] = { ...study.factors[0], domain_kind: "discrete_numeric", low: 1000.1, high: 1000.3, step: .1 } as typeof study.factors[0];
    expect(mixedProfilePoints(study, { x: 1000.1, material: "001" }, "x")?.map(point => point.x)).toEqual([1000.1, 1000.2, 1000.3]);
    study.factors[0] = { ...study.factors[0], high: 1020.1 } as typeof study.factors[0];
    expect(mixedProfilePoints(study, { x: 1000.1, material: "001" }, "x")).toBeNull();
  });
  it("accepts a server-canonical discrete level while preserving the exact supplied input", () => {
    const { study, page } = mixedPlanningFixture();
    study.factors[0] = { ...study.factors[0], domain_kind: "discrete_numeric", low: 0, high: 1, step: .1 } as typeof study.factors[0];
    const row = page.items[0]; row.input_coordinates = { ...row.input_coordinates, x: .30000000000000004 };
    row.actual_coordinates = { ...row.actual_coordinates, x: .3 }; row.encoded_coordinates = { ...row.encoded_coordinates, x: .3 };
    row.canonical_level_indices = { ...row.canonical_level_indices, x: 3 };
    const before = JSON.stringify(page);
    expect(validMixedPage(page, study)).toBe(true); expect(JSON.stringify(page)).toBe(before);
  });
  it("rejects distinct executable levels and retains exact category and continuous identities", () => {
    const { study } = mixedPlanningFixture(), actual = { x: .3, material: "001" };
    expect(sameMixedExecutableInput({ ...actual, x: .30000000000000004 }, actual, study.factors)).toBe(false);
    study.factors[0] = { ...study.factors[0], domain_kind: "discrete_numeric", low: 0, high: 1, step: .1 } as typeof study.factors[0];
    expect(sameMixedExecutableInput({ ...actual, x: .30000000000000004 }, actual, study.factors)).toBe(true);
    for (const x of [.31, .4, -1e-15, 1.0000000000000002]) expect(sameMixedExecutableInput({ ...actual, x }, actual, study.factors)).toBe(false);
    expect(sameMixedExecutableInput({ x: .3, material: "1" }, actual, study.factors)).toBe(false);
    expect(sameMixedExecutableInput({ ...actual, extra: 1 }, actual, study.factors)).toBe(false);
    study.factors[0] = { ...study.factors[0], domain_kind: "discrete_numeric", low: 1000.1, high: 1000.4, step: .1 } as typeof study.factors[0];
    expect(sameMixedExecutableInput({ x: 1000.2, material: "001" }, { x: 1000.2, material: "001" }, study.factors)).toBe(true);
  });
  it("retains latent/predictive distinction and rejects unavailable/bad posterior data", () => {
    const { selection, study } = mixedPlanningFixture(); if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    const row = selection.calculation.items[0]; expect(validMixedPrediction(row, study)).toBe(true);
    row.response_predictions[0].predictive_standard_deviation_raw = -1; expect(validMixedPrediction(row, study)).toBe(false);
  });
  it("uses separate ABA request and same-owner commit fences", () => {
    const read = createPlanningRequestFence(), commit = createPlanningCommitFence(); read.source("A"); commit.source("ownerA");
    const request = read.begin(), saved = commit.begin()!; read.source("B"); read.source("A");
    expect(read.current(request)).toBe(false); expect(commit.current(saved)).toBe(true);
    commit.source("ownerB"); commit.source("ownerA"); expect(commit.current(saved)).toBe(false);
  });
});
