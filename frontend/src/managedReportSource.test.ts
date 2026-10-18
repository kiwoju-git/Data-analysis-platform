import { describe, expect, it } from "vitest";
import { isReportSourceRef, managedReportQuery, reportSourceKey, safeReportOpenTarget } from "./managedReportSource";
import type { ReportSourceRef } from "./api/types/reports";

const id = "10000000-0000-4000-8000-000000000001";
const hash = "a".repeat(64);
const revision = { response_revision_id: id, response_revision_sha256: hash };
export const reportSources: ReportSourceRef[] = [
  { kind: "analysis_run", analysis_id: id, expected_source_sha256: hash },
  { kind: "regression_prediction", prediction: { storage: "completed_prediction", family: "pls", source_analysis_id: id, source_result_sha256: hash, model_id: id, model_manifest_sha256: hash, prediction_artifact_id: id, expected_source_sha256: hash } },
  { kind: "doe_analysis", family: "factorial", design_id: id, design_version_id: id, design_sha256: hash, analysis_id: id, expected_source_sha256: hash, response_revision: revision },
  { kind: "doe_optimizer_result", optimizer: { workflow: "response_surface", design_id: id, design_version_id: id, design_sha256: hash, optimization_id: id, expected_source_sha256: hash, source_bundle_sha256: hash, source_dependencies: [{ analysis_id: id, analysis_sha256: hash, response_revision: revision }] } },
  { kind: "lhs_design_revision", design_id: id, design_version_id: id, expected_source_sha256: hash, response_revisions: [revision] },
  { kind: "bayesian_history_revision", study_id: id, study_version_id: id, definition_sha256: hash, history_revision_id: id, expected_source_sha256: hash, attachment: { kind: "recommendation", recommendation_id: id, result_json_sha256: hash, result_payload_sha256: hash } },
];

describe("exact managed report sources", () => {
  it("keeps six kinds distinct even when their UUIDs collide", () => {
    expect(reportSources.every(isReportSourceRef)).toBe(true);
    expect(new Set(reportSources.map(reportSourceKey)).size).toBe(6);
    for (const source of reportSources) expect(reportSourceKey(source)).toBe(reportSourceKey(Object.fromEntries(Object.entries(source).reverse()) as ReportSourceRef));
  });
  it("binds revisions, nested dependencies and attachments, not open-target text", () => {
    for (const source of reportSources) {
      const changed = JSON.parse(JSON.stringify(source).replace(hash, "b".repeat(64))) as ReportSourceRef;
      expect(reportSourceKey(changed)).not.toBe(reportSourceKey(source));
    }
    expect(isReportSourceRef({ kind: "doe_analysis", open_target: "/analysis/doe/doe.factorial_design?analysis_id=" + id })).toBe(false);
    expect(isReportSourceRef({ ...reportSources[4], response_revisions: [revision, revision] })).toBe(false);
    expect(isReportSourceRef({ ...reportSources[0], expected_source_sha256: "unknown" })).toBe(false);
  });
  it("validates direct report URLs without accepting duplicate or non-UUID owners", () => {
    expect(managedReportQuery(`?analysis_id=legacy&report_id=${id}&source_kind=doe_analysis`)).toEqual({ kind: "doe_analysis", reportId: id, error: null });
    for (const query of ["?report_id=not-uuid", `?report_id=${id}&report_id=${id}`, "?source_kind=doe_analysis&source_kind=analysis_run", "?source_kind=unknown"]) expect(managedReportQuery(query).error).toBe("managed_report_query_invalid");
  });
  it("allows same-origin navigation only and never treats a target as source identity", () => {
    expect(safeReportOpenTarget("/analysis/doe/method?design_id=1")).toBe("/analysis/doe/method?design_id=1");
    for (const target of ["javascript:alert(1)", "https://example.com", "//example.com", "/\\example.com", "/\nexample.com"]) expect(safeReportOpenTarget(target)).toBeNull();
  });
});
