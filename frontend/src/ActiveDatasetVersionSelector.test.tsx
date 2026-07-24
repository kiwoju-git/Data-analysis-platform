import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ActiveDatasetVersionSelector } from "./ActiveDatasetVersionSelector";
import type {
  DatasetVersionCatalogItem,
  DatasetVersionResponse,
} from "./api";
import type { DatasetVersionCatalogState } from "./useDatasetVersionCatalogState";

describe("ActiveDatasetVersionSelector", () => {
  it("separates picker, summary, technical metadata, and operational rows", () => {
    const html = renderToString(
      <ActiveDatasetVersionSelector
        catalogState={catalogState({
          error: "catalog_failed",
          isResolvingActiveItem: true,
        })}
        isSwitching={true}
        pendingVersionId={null}
        version={version()}
        onRetrySwitch={vi.fn()}
        onSelect={vi.fn()}
      />,
    );

    expect(html).toContain('class="active-dataset-picker"');
    expect(html).toContain('class="active-dataset-select-stack"');
    expect(html).toContain('aria-describedby="active-dataset-help"');
    expect(html).toContain("<dt>버전</dt><dd>v1</dd>");
    expect(html).toContain("<dt>행</dt><dd>240</dd>");
    expect(html).toContain("<dt>열</dt><dd>15</dd>");
    expect(html).toContain("<dt>생성</dt>");
    expect(html).toContain('aria-label="데이터셋 기술 정보"');
    expect(html).toContain("schema 57cdd88e");
    expect(html).toContain("ID bad30e2e");
    expect(html).toContain("데이터셋 버전 확인 중");
    expect(html).toContain("데이터셋 목록 조회 실패");
    expect(html).toContain("분석 데이터셋 목록 페이지 이동");
    expect((html.match(/active-dataset-operational-row/g) ?? [])).toHaveLength(3);
  });

  it("keeps long catalog labels, off-page options, and invalid dates safe", () => {
    const offPage = catalogItem({
      version_id: "off-page-version-123456",
      original_filename: "매우_긴_공정_데이터셋_파일명_with_long_english_suffix.csv",
      created_at: "not-a-date",
      user_label: "사용자 지정 공정 데이터",
    });
    const html = renderToString(
      <ActiveDatasetVersionSelector
        catalogState={catalogState({
          activeItem: offPage,
          catalog: {
            offset: 20,
            limit: 20,
            total: 21,
            returned: 1,
            has_previous: true,
            has_next: false,
            versions: [catalogItem()],
          },
        })}
        isSwitching={false}
        pendingVersionId={offPage.version_id}
        version={null}
        onRetrySwitch={vi.fn()}
        onSelect={vi.fn()}
      />,
    );

    expect(html).toContain("사용자 지정 공정 데이터");
    expect(html).toContain("매우_긴_공정_데이터셋_파일명_with_long_english_suffix.csv");
    expect(html).toContain("날짜 확인 불가");
    expect(html).toContain("선택한 데이터셋 다시 불러오기");
    expect((html.match(/id="active-dataset-version"/g) ?? [])).toHaveLength(1);
    expect((html.match(/id="active-dataset-help"/g) ?? [])).toHaveLength(1);
  });
});

function catalogState(
  overrides: Partial<DatasetVersionCatalogState> = {},
): DatasetVersionCatalogState {
  return {
    activeItem: catalogItem(),
    catalog: {
      offset: 0,
      limit: 1,
      total: 2,
      returned: 1,
      has_previous: false,
      has_next: true,
      versions: [catalogItem()],
    },
    error: null,
    isLoading: false,
    isResolvingActiveItem: false,
    onPageChange: vi.fn(),
    onRefresh: vi.fn(),
    ...overrides,
  };
}

function catalogItem(
  overrides: Partial<DatasetVersionCatalogItem> = {},
): DatasetVersionCatalogItem {
  return {
    version_id: "bad30e2e12345678",
    dataset_id: "dataset-1",
    original_filename: "studio_process_training.csv",
    version_number: 1,
    row_count: 240,
    column_count: 15,
    created_at: "2026-07-22T12:43:00Z",
    user_label: null,
    note: null,
    pinned: false,
    metadata_updated_at: null,
    archived: false,
    archived_at: null,
    ...overrides,
  };
}

function version(): DatasetVersionResponse {
  return {
    version_id: "bad30e2e12345678",
    dataset_id: "dataset-1",
    version_number: 1,
    row_count: 240,
    column_count: 15,
    schema_hash: "57cdd88efbb3",
    created_at: "2026-07-22T12:43:00Z",
    source_sha256: "source-sha",
    parsing: {
      kind: "delimited_text",
      encoding: "utf-8",
      delimiter: ",",
      quote_char: '"',
      decimal: ".",
      thousands: null,
      has_header: true,
      header_row: 0,
      data_start_row: 1,
      missing_tokens: [],
      xlsx_sheet_name: null,
    },
    columns: [],
    canonical_artifact: null,
  };
}
