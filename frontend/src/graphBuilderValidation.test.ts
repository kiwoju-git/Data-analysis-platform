import { describe, expect, it } from "vitest";

import type { DatasetColumnResponse } from "./api";
import { validateGraphBuilderSelection } from "./graphBuilderValidation";

const numeric = (id: string): DatasetColumnResponse => ({
  column_id: id,
  version_id: "version-1",
  column_index: 0,
  original_name: id,
  display_name: id,
  data_type: "decimal",
  measurement_level: "continuous",
  role: "feature",
  unit: null,
});

describe("graph builder validation", () => {
  it("requires one value in group mode and exact scatter roles", () => {
    const columns = [numeric("x"), numeric("y"), numeric("z")];
    expect(
      validateGraphBuilderSelection(
        {
          graphType: "box_plot",
          valueColumnIds: ["x", "y"],
          xColumnId: null,
          yColumnIds: [],
          groupColumnId: "z",
        },
        columns,
      ),
    ).toBe("graph_builder_group_requires_one_value");
    expect(
      validateGraphBuilderSelection(
        {
          graphType: "scatter_plot",
          valueColumnIds: [],
          xColumnId: "x",
          yColumnIds: ["y"],
          groupColumnId: null,
        },
        columns,
      ),
    ).toBeNull();
  });
});
