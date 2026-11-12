import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianStudySummary } from "./BayesianStudySummary";
import { BayesianVectorStudySnapshot } from "./BayesianVectorStudySnapshot";
import { BayesianMixedStudyWorkspace } from "./BayesianMixedStudyWorkspace";
import { datasetImportedInitialFixture } from "./boDatasetSource.fixture";
import { mixedStudyFixture } from "./boMixed.test.fixture";
import { planningBatchFixture } from "./boPlanning.fixture";
import { validMixedStudy } from "./boMixedDraft";
import { BayesianStudyClosePanel } from "./BayesianStudyClosePanel";

describe("stored measured-dataset BO source", () => {
  afterEach(() => setCurrentLocale("ko"));
  it("accepts an explicit imported receipt while preserving mixed coordinate validation", () => {
    const study = mixedStudyFixture();
    study.initial_design = datasetImportedInitialFixture();
    expect(validMixedStudy(study, study.study_id)).toBe(true);
    study.trials[0].encoded_coordinates.material = 1;
    expect(validMixedStudy(study)).toBe(false);
  });
  it.each([
    { import_schema_version: 2 }, { policy: "future_import" }, { observations_sha256: "bad" },
    { n_used: 201 }, { n_filtered: 2 }, { requested_size: 3 }, { generated_size: 3 },
    { repeated_coordinate_count: 1 }, { conflicting_coordinate_count: 1 },
    { source_row_indices: [2, 2, 4, 5] }, { source_row_indices: [2, 3, 4, 9] },
    { factor_columns: { x: "column-x" } }, { response_columns: { objective: "column-y" } },
    { missing_policy: "infer" }, { filter_snapshot: { expression_version: 9, conditions: [] } },
    { source: { dataset_id: "missing-version-and-hashes" } }, { request_id: "bad" },
  ])("rejects inconsistent or unsupported imported receipt %j", (change) => {
    const study = mixedStudyFixture();
    study.initial_design = { ...datasetImportedInitialFixture(), ...change } as unknown as typeof study.initial_design;
    expect(validMixedStudy(study)).toBe(false);
  });
  it("requires imported initial observations to remain completed", () => {
    const study = mixedStudyFixture(false);
    study.initial_design = datasetImportedInitialFixture();
    expect(validMixedStudy(study)).toBe(false);
  });
  it("explains why imported studies cannot reuse a generated-design successor seed", () => {
    setCurrentLocale("en");
    const study = planningBatchFixture().study;
    study.initial_design = datasetImportedInitialFixture(2);
    study.status = "completed";
    study.lifecycle_event = { resulting_status: "completed", reason_code: "confirmation_complete", closed_at: "2026-11-12", note: null } as typeof study.lifecycle_event;
    const noop = () => undefined;
    const html = renderToStaticMarkup(<BayesianStudyClosePanel study={study} hasRecommendation target="completed" reason="confirmation_complete" note=""
      pending={false} isClosing={false} actionsDisabled={false} onTargetChange={noop} onReasonChange={noop} onNoteChange={noop}
      onRequestClose={noop} onConfirmClose={noop} onCancelClose={noop} onPrepareSuccessor={noop} />);
    expect(html).toContain("Imported observations have no generation seed");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>[^<]*successor/);
  });
  it.each(["ko", "en"] as const)("shows source/counts for scalar, vector and mixed imports without invented seeds (%s)", (locale) => {
    setCurrentLocale(locale);
    const mixed = mixedStudyFixture();
    mixed.initial_design = datasetImportedInitialFixture();
    const vector = planningBatchFixture().study;
    vector.initial_design = datasetImportedInitialFixture(2);
    const scalar = { ...vector, constraints: [], objective: { name: "Measured Y", goal_type: "maximize" as const,
      direction: "maximize" as const, unit: null, target_value: null, target_tolerance: null, observation_policy: "manual_single_observation" as const } };
    const renders = [
      () => renderToStaticMarkup(<BayesianStudySummary study={scalar} />),
      () => renderToStaticMarkup(<BayesianVectorStudySnapshot study={vector} />),
      () => renderToStaticMarkup(<BayesianMixedStudyWorkspace study={mixed} disabled={false} onCommitted={() => undefined} onRefresh={() => undefined} onBusyChange={() => undefined} />),
    ];
    for (const render of renders) {
      const html = render();
      expect(html).toContain(locale === "en" ? "Imported measured observations" : "데이터셋에서 가져온 실측 관측");
      expect(html).toContain(datasetImportedInitialFixture().source.dataset_version_id);
      expect(html).toContain(locale === "en" ? "Missing exclusions" : "결측 제외");
      expect(html).not.toContain("Centered discrepancy");
      expect(html).not.toContain("LHS random-cd");
      expect(html).not.toContain(">Seed<");
    }
  });
});
