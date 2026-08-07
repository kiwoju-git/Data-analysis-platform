import type {
  DatasetColumnResponse,
  GraphComparisonMode,
  GraphPreviewType,
  ScatterMode,
} from "./api";
import { graphBuilderDefinition } from "./graphBuilderRegistry";

export interface GraphBuilderSelection {
  graphType: GraphPreviewType;
  valueColumnIds: string[];
  xColumnId: string | null;
  yColumnIds: string[];
  fixedYColumnId?: string | null;
  multipleXColumnIds?: string[];
  scatterMode?: ScatterMode;
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
    const scatterMode = selection.scatterMode ?? "fixed_x_multiple_y";
    const xIds = scatterMode === "fixed_x_multiple_y"
      ? selection.xColumnId === null ? [] : [selection.xColumnId]
      : selection.multipleXColumnIds ?? [];
    const yIds = scatterMode === "fixed_x_multiple_y"
      ? selection.yColumnIds
      : selection.fixedYColumnId == null ? [] : [selection.fixedYColumnId];
    if (
      xIds.length === 0 ||
      yIds.length === 0 ||
      xIds.some((columnId) => !numericIds.has(columnId)) ||
      yIds.some((columnId) => !numericIds.has(columnId))
    ) {
      return "graph_builder_scatter_roles_required";
    }
    const multipleIds = scatterMode === "fixed_x_multiple_y" ? yIds : xIds;
    if (multipleIds.length > definition.maximumValues) {
      return "graph_builder_too_many_values";
    }
    if (new Set(xIds).size !== xIds.length || new Set(yIds).size !== yIds.length) {
      return "graph_builder_scatter_duplicate_columns";
    }
    if (xIds.some((columnId) => yIds.includes(columnId))) {
      return "graph_builder_scatter_same_axis_column";
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
