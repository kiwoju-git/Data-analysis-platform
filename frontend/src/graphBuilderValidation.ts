import type {
  DatasetColumnResponse,
  GraphComparisonMode,
  GraphPreviewType,
} from "./api";
import { graphBuilderDefinition } from "./graphBuilderRegistry";

export interface GraphBuilderSelection {
  graphType: GraphPreviewType;
  valueColumnIds: string[];
  xColumnId: string | null;
  yColumnIds: string[];
  groupColumnId: string | null;
  comparisonMode: GraphComparisonMode;
}

export function validateGraphBuilderSelection(
  selection: GraphBuilderSelection,
  columns: DatasetColumnResponse[],
): string | null {
  const definition = graphBuilderDefinition(selection.graphType);
  const numericIds = new Set(
    columns
      .filter(
        (column) =>
          (column.data_type === "integer" || column.data_type === "decimal") &&
          column.role !== "id" &&
          column.measurement_level !== "id",
      )
      .map((column) => column.column_id),
  );
  if (selection.graphType === "scatter_plot") {
    if (
      selection.xColumnId === null ||
      !numericIds.has(selection.xColumnId) ||
      selection.yColumnIds.length === 0 ||
      selection.yColumnIds.some((columnId) => !numericIds.has(columnId))
    ) {
      return "graph_builder_scatter_roles_required";
    }
    if (selection.yColumnIds.length > definition.maximumValues) {
      return "graph_builder_too_many_values";
    }
    return null;
  }
  if (
    selection.valueColumnIds.length === 0 ||
    selection.valueColumnIds.some((columnId) => !numericIds.has(columnId))
  ) {
    return "graph_builder_value_required";
  }
  if (selection.valueColumnIds.length > definition.maximumValues) {
    return "graph_builder_too_many_values";
  }
  if (selection.comparisonMode === "one_value_by_group") {
    if (!definition.supportsGroup) {
      return "graph_builder_group_comparison_unsupported";
    }
    if (selection.valueColumnIds.length !== 1) {
      return "graph_builder_group_requires_one_value";
    }
    if (selection.groupColumnId === null) {
      return "graph_builder_group_required";
    }
  } else if (selection.groupColumnId !== null) {
    return "graph_builder_group_not_allowed_in_multiple_mode";
  }
  return null;
}
