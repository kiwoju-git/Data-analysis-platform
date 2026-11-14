import { describe, expect, it } from "vitest";
import { buildMixtureGroup, validMixtureCoordinates, validMixtureModel, currentMixtureModel, validMixturePage, validMixtureSelection, mixtureReviewDraftKey } from "./boMixtureDraft";
import { mixtureFixture } from "./boMixture.test.fixture";
import { buildDatasetImportRequest, type DatasetImportDraft } from "./boDatasetImportDraft";
import { newMixedFactor } from "./boMixedDraft";
import { newResponseDraft } from "./bayesianVectorDraft";

const components = [
  { key: 1, factorId: "a", name: "A", low: "0.1", high: "0.8" },
  { key: 2, factorId: "b", name: "B", low: "0.1", high: "0.8" },
  { key: 3, factorId: "fixed", name: "Fixed", low: "0.1", high: "0.1" },
];
describe("mixture actual-amount closure", () => {
  it("keeps bounds, total, units, explicit coding and fixed components", () => {
    const result = buildMixtureGroup("1", "g", "upper", components);
    expect(typeof result).not.toBe("string");
    if (typeof result === "string") throw Error(result);
    expect(result.total).toBe(1);
    expect(result.coding).toBe("upper");
    expect(result.components[2]).toEqual({ factor_id: "fixed", name: "Fixed", low: .1, high: .1, unit: "g" });
    expect(validMixtureCoordinates({ a: .3, b: .6, fixed: .1 }, result)).toBe(true);
    expect(validMixtureCoordinates({ a: .31, b: .6, fixed: .1 }, result)).toBe(false);
    expect(validMixtureCoordinates({ a: "0.3", b: .6, fixed: .1 }, result)).toBe(false);
    expect(validMixtureCoordinates({ a: .3, b: .6 }, result)).toBe(false);
  });
  it("rejects infeasible, collapsed, duplicate, blank and nonfinite definitions", () => {
    expect(typeof buildMixtureGroup(".1", "g", "lower", components)).toBe("string");
    expect(typeof buildMixtureGroup("1", "", "auto", components)).toBe("string");
    expect(typeof buildMixtureGroup("NaN", "g", "auto", components)).toBe("string");
    expect(typeof buildMixtureGroup("1", "g", "auto", components.map(c => ({ ...c, low: ".5", high: ".5" })))).toBe("string");
    expect(typeof buildMixtureGroup("1", "g", "auto", components.map(c => ({ ...c, factorId: "same" })))).toBe("string");
  });
});

describe("mixture existing-data import", () => {
  it("uses schema2 with declared ordered component mappings and preserves source/missing choices", () => {
    const response = { ...newResponseDraft(1), lower: "0", target: "10" };
    const draft: DatasetImportDraft = { name: "Measured mixture", factors: [
      { ...newMixedFactor(1), factorId: "a", columnId: "amount-a", low: "0", high: "1" },
      { ...newMixedFactor(2), factorId: "b", columnId: "amount-b", low: "0", high: "1" },
    ], responseMode: "vector", scalarColumnId: "", goal: "maximize", target: "", tolerance: "", responses: [response], responseColumns: { [response.responseId]: "measured-y" }, constraints: [], missingPolicy: "reject", mixture: { total: "1", unit: "g", coding: "upper", componentKeys: [1, 2] } };
    const version = { version_id: "source-version", schema_hash: "a".repeat(64), columns: [{ column_id: "amount-a", display_name: "Amount A", unit: "g" }, { column_id: "amount-b", display_name: "Amount B", unit: "g" }, { column_id: "measured-y", display_name: "Measured Y", unit: "Pa" }] };
    const filter = { expression_version: 1 as const, conditions: [] };
    const result = buildDatasetImportRequest(version, filter, draft);
    expect(typeof result).not.toBe("string");
    expect(result).toMatchObject({ schema_version: 2, mixture: { total: 1, coding: "upper" }, missing_policy: "reject", dataset_version_id: version.version_id, expected_schema_hash: version.schema_hash, filter_snapshot: filter });
    if (typeof result === "string") throw Error(result);
    expect(result.factor_mappings.map(row => [row.column_id, row.factor.factor_id, row.factor.domain_kind])).toEqual([["amount-a", "a", "mixture_component"], ["amount-b", "b", "mixture_component"]]);
    expect(result.response_mappings).toEqual([{ column_id: "measured-y", response_id: response.responseId }]);
    expect(result).not.toHaveProperty("initial_design_seed");
    expect(typeof buildDatasetImportRequest(version, filter, { ...draft, responseMode: "scalar" })).toBe("string");
    expect(typeof buildDatasetImportRequest(version, filter, { ...draft, mixture: { ...draft.mixture!, componentKeys: [1] } })).toBe("string");
  });
});

describe("mixture immutable planning ownership", () => {
  it("invalidates a reviewed selection for every mutable selection input", () => {
    const draft = { seed: "42", budget: "20", distance: "0", batch: "2", manual: true, selected: ["a", "b"] };
    const reviewed = mixtureReviewDraftKey(draft);
    expect(mixtureReviewDraftKey({ ...draft })).toBe(reviewed);
    for (const update of [{ seed: "43" }, { budget: "21" }, { distance: ".1" }, { batch: "3" }, { manual: false }, { selected: ["b", "a"] }]) {
      expect(mixtureReviewDraftKey({ ...draft, ...update })).not.toBe(reviewed);
    }
  });
  it("rejects changed owner/model/page identities and latent/predictive uncertainty swaps", () => {
    const { study, model, page, selection } = mixtureFixture();
    expect(validMixtureModel(model, study)).toBe(true);
    expect(currentMixtureModel({ ...model, history_sha256: "f".repeat(64) }, study)).toBe(false);
    expect(validMixtureModel({ ...model, study_id: "other" }, study)).toBe(false);
    expect(validMixturePage(page, study, model)).toBe(true);
    expect(validMixturePage({ ...page, revision: { ...page.revision, model_id: "other" } }, study, model)).toBe(false);
    expect(validMixturePage({ ...page, items: page.items.map(row => ({ ...row, response_predictions: row.response_predictions.map(p => ({ ...p, latent_standard_deviation_raw: 2, predictive_standard_deviation_raw: 1 })) })) }, study, model)).toBe(false);
    expect(validMixtureSelection(selection, study, model)).toBe(true);
    expect(validMixtureSelection({ ...selection, config: { ...selection.config, expected_model_sha256: "f".repeat(64) } }, study, model)).toBe(false);
  });
});
