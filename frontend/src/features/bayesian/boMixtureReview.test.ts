import { afterEach, describe, expect, it, vi } from "vitest";
import { mixtureFixture } from "./boMixture.test.fixture";
import { createMixtureReview, restoreMixtureReview, fetchMixtureReviewPage, runMixtureTask } from "./boMixtureReview";
import { createPlanningRequestFence } from "./boPlanningDraft";

describe("exact mixture review HTTP boundaries", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("restores nondefault settings for ID and initial-link callers", async () => {
    const { study, model, selection } = mixtureFixture();
    const saved = { ...selection, config: { ...selection.config, policy: "greedy_mixture_maximin_v1", row_ids: [], total_trial_budget: 20, min_batch_distance: .2 } };
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => Promise.resolve(new Response(JSON.stringify(url.includes("mixture-selections") ? saved : model)))));
    for (const caller of ["id", "initial-link"]) {
      const restored = await restoreMixtureReview(study, selection.selection_id, () => true);
      expect(restored?.draft, caller).toMatchObject({ manual: false, budget: "20", distance: "0.2", selected: [] });
    }
  });
  it("rejects another valid selection ID from the same owner", async () => {
    const { study, selection } = mixtureFixture();
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ ...selection, selection_id: "33333333-3333-4333-8333-000000000099" })))));
    await expect(restoreMixtureReview(study, selection.selection_id, () => true)).rejects.toThrow("bayesian_mixture_source_mismatch");
  });
  it("rejects create responses with changed request/config identity", async () => {
    const { study, model, selection } = mixtureFixture();
    for (const changed of [{ request_id: "33333333-3333-4333-8333-000000000099" }, { policy: "greedy_mixture_maximin_v1", row_ids: [] }, { row_ids: ["0".repeat(64)] }, { total_trial_budget: 21 }, { min_batch_distance: .2 }, { expected_rows_sha256: "0".repeat(64) }, { candidate_revision_id: "33333333-3333-4333-8333-000000000099" }]) {
      vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ ...selection, config: { ...selection.config, ...changed } })))));
      await expect(createMixtureReview(study, model, selection.config, () => true)).rejects.toThrow("bayesian_mixture_source_mismatch");
    }
  });
  it("rejects wrong pagination revision, offset, limit and row digest", async () => {
    const { study, model, page } = mixtureFixture();
    for (const changed of [{ offset: 50 }, { limit: 25 }, { revision: { ...page.revision, revision_id: "33333333-3333-4333-8333-000000000099" } }, { revision: { ...page.revision, rows_sha256: "0".repeat(64) } }]) {
      vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ ...page, ...changed })))));
      await expect(fetchMixtureReviewPage(study, model, page.revision, 0, () => true)).rejects.toThrow("bayesian_mixture_source_mismatch");
    }
  });
});

describe("mixture async A-B-A mutation lane", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("discards an old HTTP restore before fetching its model or committing state", async () => {
    const { study, selection } = mixtureFixture(), guard = createPlanningRequestFence(); guard.source("A");
    let resolve!: (response: Response) => void;
    const fetch = vi.fn().mockImplementation(() => new Promise<Response>(yes => { resolve = yes; })); vi.stubGlobal("fetch", fetch);
    const commit = vi.fn(), success = vi.fn(), error = vi.fn(), settled = vi.fn();
    const task = runMixtureTask(guard, async current => { const value = await restoreMixtureReview(study, selection.selection_id, current); if (value) commit(value); }, { success, error, settled });
    guard.source("B"); guard.source("A"); resolve(new Response(JSON.stringify(selection))); await task;
    expect(fetch).toHaveBeenCalledTimes(1); expect(commit).not.toHaveBeenCalled(); expect(success).not.toHaveBeenCalled(); expect(error).not.toHaveBeenCalled(); expect(settled).not.toHaveBeenCalled();
  });
  it.each([false, true])("does not apply stale success/error/finally (reject=%s)", async reject => {
    const guard = createPlanningRequestFence(); guard.source("A");
    let resolve!: () => void, fail!: (error: Error) => void;
    const pending = new Promise<void>((yes, no) => { resolve = yes; fail = no; });
    const success = vi.fn(), error = vi.fn(), settled = vi.fn();
    const task = runMixtureTask(guard, () => pending, { success, error, settled });
    guard.source("B"); guard.source("A");
    if (reject) fail(Error("old failure")); else resolve();
    await task;
    expect(success).not.toHaveBeenCalled(); expect(error).not.toHaveBeenCalled(); expect(settled).not.toHaveBeenCalled();
  });
});
