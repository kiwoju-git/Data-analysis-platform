import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("current analysis publication boundary", () => {
  it("routes every main execution through the guarded owner, leaving quick graph independent", () => {
    const source = readFileSync(new URL("./App.tsx", import.meta.url), "utf8");
    expect(source.match(/await createAnalysisRun\(/g) ?? []).toHaveLength(1);
    expect(source.match(/await currentAnalysis\.execute\(/g) ?? []).toHaveLength(31);
    expect(source).not.toContain("setAnalysisResult(response)");
  });
  it("delegates deletion invalidation to the dataset owner instead of clearing unrelated current work", () => {
    const source = readFileSync(new URL("./App.tsx", import.meta.url), "utf8");
    const body = source.split("function handleAssetsDeleted(")[1].split("function handleOpenManagePage")[0];
    expect(body).toContain("onDatasetDeleted(response)");
    expect(body).toContain('publishWorkspaceMutation("dataset_deleted")');
    expect(body).not.toContain("invalidateAnalysisInput()");
    expect(body).not.toContain("setDatasetStateRevision");
  });
});
