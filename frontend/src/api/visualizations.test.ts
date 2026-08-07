import { afterEach, describe, expect, it, vi } from "vitest";

import { createGraphPreview } from "./visualizations";

describe("createGraphPreview", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts the typed preview request to the centralized route", async () => {
    const payload = {
      visualization_schema_version: 3 as const,
      graph_type: "box_plot" as const,
      dataset_version_id: "version-1",
      source_schema_hash: "schema",
      filter_snapshot_sha256: "filter",
      preview_config_sha256: "config",
      row_count_total: 10,
      row_count_included: 8,
      warnings: [],
      layout: "combined" as const,
      comparison_mode: "multiple_values" as const,
      group_order_policy: "first_occurrence" as const,
      missing_group_policy: "exclude" as const,
      missing_group_row_count: 0,
      panels: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createGraphPreview({
      dataset_version_id: "version-1",
      filter_snapshot: { expression_version: 1, conditions: [] },
      graph_type: "box_plot",
      value_column_ids: ["column-1"],
      layout: "combined",
      comparison_mode: "multiple_values",
    });

    expect(result).toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/visualizations/preview",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
