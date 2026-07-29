import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AnalysisSelectionQuickGuide } from "./AnalysisSelectionQuickGuide";
import { DatasetProfileSection } from "./DatasetProfileSection";
import { DatasetVersionPanel } from "./DatasetVersionPanel";
import { LatinHypercubePanel } from "./LatinHypercubePanel";
import type {
  DatasetProfileResponse,
  DatasetVersionResponse,
} from "./api";

describe("dataset correction and LHS usability", () => {
  it("keeps dataset diagnostics in a closed technical disclosure", () => {
    const html = renderToStaticMarkup(
      <DatasetVersionPanel
        canApplyBayesianPreset={false}
        isLoadingPreview={false}
        isLoadingProfile={false}
        isSavingSchema={false}
        preview={null}
        previewLimit={25}
        previewOffset={0}
        profile={null}
        schemaDrafts={[]}
        version={versionFixture()}
        onApplyBayesianPreset={vi.fn()}
        onCellEditDirtyChange={vi.fn()}
        onCreateCellCorrection={vi.fn()}
        onLoadDatasetProfile={vi.fn()}
        onLoadRowsPreview={vi.fn()}
        onPreviewLimitChange={vi.fn()}
        onSaveSchema={vi.fn()}
        onSchemaDraftChange={vi.fn()}
      />,
    );

    expect(html).toContain("데이터셋 v2");
    expect(html).toContain("v1에서 셀 1건을 수정해 생성됨");
    expect(html).toContain("<details");
    expect(html).not.toContain("<details open");
    expect(html).toContain("기술 정보 펼치기");
    expect(html).toContain("Schema hash");
    expect(html).toContain("데이터 품질 점검");
  });

  it("uses compact one-line profile cells and explicit column widths", () => {
    const html = renderToStaticMarkup(
      <DatasetProfileSection
        isLoadingProfile={false}
        profile={profileFixture()}
        versionId="version-2"
        onLoadDatasetProfile={vi.fn()}
      />,
    );

    expect(html).toContain("profile-role-level");
    expect(html).toContain("profile-numeric-cell");
    expect(html).toContain("0 / 240");
    expect(html).toContain("고유값");
    expect(html).toContain("profile-column-summary");
    expect(html).not.toContain("Canonical artifact");
    expect(html).not.toContain("메모리 추정");
  });

  it("renders the standalone LHS design and response revision workflow", () => {
    const html = renderToStaticMarkup(<LatinHypercubePanel />);

    expect(html).toContain("LHS 공간충전 설계");
    expect(html).toContain("Discrepancy 개선");
    expect(html).toContain("GP 계산 bare minimum");
    expect(html).toContain("LHS 설계 생성");
    expect(html).toContain("별도 Bayesian Study가 LHS 초기점을 생성");
  });

  it("offers DOE methods by design purpose", () => {
    const html = renderToStaticMarkup(
      <AnalysisSelectionQuickGuide
        selectedModuleId="doe"
        onSelectMethod={vi.fn()}
      />,
    );

    expect(html).toContain("실험계획법 선택 가이드");
    expect(html).toContain("2-level factorial");
    expect(html).toContain("LHS");
    expect(html).toContain("Response Surface");
    expect(html).toContain("Bayesian Optimization");
    expect(html).toContain("전역 최적점을 보장하지 않습니다");
  });
});

function versionFixture(): DatasetVersionResponse {
  return {
    version_id: "version-2",
    dataset_id: "dataset-1",
    version_number: 2,
    row_count: 240,
    column_count: 1,
    schema_hash: "a".repeat(64),
    created_at: "2026-07-29T12:00:00Z",
    source_sha256: "b".repeat(64),
    parsing: {
      kind: "delimited_text",
      encoding: "utf-8",
      delimiter: ",",
      quote_char: '"',
      decimal: ".",
      thousands: null,
      has_header: true,
      header_row: 1,
      data_start_row: 2,
      missing_tokens: [""],
      xlsx_sheet_name: null,
    },
    columns: [
      {
        column_id: "column-1",
        version_id: "version-2",
        column_index: 0,
        original_name: "temperature_c",
        display_name: "temperature_c",
        data_type: "decimal",
        measurement_level: "continuous",
        role: "feature",
        unit: "C",
      },
    ],
    canonical_artifact: {
      artifact_id: "artifact-1",
      version_id: "version-2",
      kind: "canonical_rows",
      path: "internal",
      sha256: "c".repeat(64),
      media_type: "application/x-ndjson",
      size_bytes: 1024,
      created_at: "2026-07-29T12:00:00Z",
    },
    parent_version_id: "version-1",
    lineage_operation_kind: "cell_correction",
    lineage_affected_cell_count: 1,
  };
}

function profileFixture(): DatasetProfileResponse {
  return {
    profile_schema_version: 1,
    version_id: "version-2",
    dataset_id: "dataset-1",
    row_count: 240,
    column_count: 1,
    schema_hash: "a".repeat(64),
    computed_at: "2026-07-29T12:00:00Z",
    unique_count_limit: 10_000,
    canonical_artifact: null,
    profile_artifact: null,
    preflight: {
      estimated_memory_bytes: 2048,
      duplicate_row_count: 0,
      duplicate_row_count_capped: false,
      duplicate_row_check_limit: 10_000,
    },
    columns: [
      {
        column_id: "column-1",
        column_index: 0,
        display_name: "temperature_c",
        data_type: "decimal",
        measurement_level: "continuous",
        role: "feature",
        n_total: 240,
        n_present: 240,
        n_missing: 0,
        missing_rate: 0,
        unique_count: 238,
        unique_count_capped: false,
        n_numeric: 240,
        n_non_numeric: 0,
        numeric_min: 60.716,
        numeric_max: 89.876,
        numeric_mean: 75.8,
        datetime_profile: null,
        constant: false,
        warnings: [],
      },
    ],
    warnings: [],
  };
}
