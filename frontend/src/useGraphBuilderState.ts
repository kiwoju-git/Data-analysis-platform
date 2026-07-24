import { useEffect, useMemo, useRef, useState } from "react";

import {
  createGraphPreview,
  type DatasetColumnResponse,
  type DatasetVersionResponse,
  type GraphPreviewLayout,
  type GraphPreviewResponse,
  type GraphPreviewType,
} from "./api";
import type { AnalysisFilterDraft } from "./analysisFilters";
import {
  serializeAnalysisFilterDrafts,
  validateAnalysisFilterDrafts,
} from "./analysisFilters";
import { validateGraphBuilderSelection } from "./graphBuilderValidation";

export function useGraphBuilderState(version: DatasetVersionResponse | null) {
  const numericColumns = useMemo(
    () =>
      (version?.columns ?? []).filter(
        (column) =>
          (column.data_type === "integer" || column.data_type === "decimal") &&
          column.role !== "id" &&
          column.measurement_level !== "id",
      ),
    [version],
  );
  const [graphType, setGraphType] = useState<GraphPreviewType>("box_plot");
  const [valueColumnIds, setValueColumnIds] = useState<string[]>([]);
  const [xColumnId, setXColumnId] = useState<string | null>(null);
  const [yColumnIds, setYColumnIds] = useState<string[]>([]);
  const [groupColumnId, setGroupColumnId] = useState<string | null>(null);
  const [orderColumnId, setOrderColumnId] = useState<string | null>(null);
  const [layout, setLayout] = useState<GraphPreviewLayout>("combined");
  const [filterDrafts, setFilterDrafts] = useState<AnalysisFilterDraft[]>([]);
  const [result, setResult] = useState<GraphPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const first = numericColumns[0]?.column_id ?? null;
    const second = numericColumns[1]?.column_id ?? first;
    setValueColumnIds(first === null ? [] : [first]);
    setXColumnId(first);
    setYColumnIds(second === null ? [] : [second]);
    setGroupColumnId(null);
    setOrderColumnId(null);
    setFilterDrafts([]);
    setResult(null);
    setError(null);
    requestIdRef.current += 1;
  }, [numericColumns, version?.version_id]);

  const selectionError =
    version === null
      ? "dataset_version_required"
      : validateGraphBuilderSelection(
          { graphType, valueColumnIds, xColumnId, yColumnIds, groupColumnId },
          version.columns,
        );
  const filterError =
    version === null ? null : validateAnalysisFilterDrafts(filterDrafts, version.columns);
  const validationError = selectionError ?? filterError;

  function invalidate() {
    requestIdRef.current += 1;
    setResult(null);
    setError(null);
    setIsGenerating(false);
  }

  function changeGraphType(next: GraphPreviewType) {
    invalidate();
    setGraphType(next);
    setGroupColumnId(null);
    setOrderColumnId(null);
    setLayout(next === "box_plot" ? "combined" : "small_multiples");
  }

  async function generate() {
    if (version === null || validationError !== null) return;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setIsGenerating(true);
    setError(null);
    try {
      const response = await createGraphPreview({
        dataset_version_id: version.version_id,
        filter_snapshot: {
          expression_version: 1,
          conditions: serializeAnalysisFilterDrafts(filterDrafts, version.columns),
        },
        graph_type: graphType,
        value_column_ids: graphType === "scatter_plot" ? [] : valueColumnIds,
        x_column_id: graphType === "scatter_plot" ? xColumnId : null,
        y_column_ids: graphType === "scatter_plot" ? yColumnIds : [],
        group_column_id: groupColumnId,
        order_column_id: orderColumnId,
        point_limit: graphType === "individual_value_plot" ? 2000 : 1000,
        layout,
      });
      if (requestIdRef.current === requestId) {
        setResult(response);
      }
    } catch (caught) {
      if (requestIdRef.current === requestId) {
        setError(caught instanceof Error ? caught.message : "graph_preview_failed");
      }
    } finally {
      if (requestIdRef.current === requestId) {
        setIsGenerating(false);
      }
    }
  }

  function updateAndInvalidate<T>(setter: (value: T) => void, value: T) {
    invalidate();
    setter(value);
  }

  return {
    error,
    filterDrafts,
    graphType,
    groupColumnId,
    isGenerating,
    layout,
    numericColumns,
    orderColumnId,
    result,
    validationError,
    valueColumnIds,
    xColumnId,
    yColumnIds,
    generate,
    setFilterDrafts: (drafts: AnalysisFilterDraft[]) =>
      updateAndInvalidate(setFilterDrafts, drafts),
    setGraphType: changeGraphType,
    setGroupColumnId: (value: string | null) =>
      updateAndInvalidate(setGroupColumnId, value),
    setLayout: (value: GraphPreviewLayout) => updateAndInvalidate(setLayout, value),
    setOrderColumnId: (value: string | null) =>
      updateAndInvalidate(setOrderColumnId, value),
    setValueColumnIds: (value: string[]) =>
      updateAndInvalidate(setValueColumnIds, value),
    setXColumnId: (value: string | null) => updateAndInvalidate(setXColumnId, value),
    setYColumnIds: (value: string[]) => updateAndInvalidate(setYColumnIds, value),
  };
}

export function graphBuilderColumns(version: DatasetVersionResponse | null): {
  group: DatasetColumnResponse[];
  order: DatasetColumnResponse[];
} {
  const columns = version?.columns ?? [];
  return {
    group: columns.filter(
      (column) => column.role !== "id" && column.measurement_level !== "id",
    ),
    order: columns.filter(
      (column) =>
        column.data_type === "integer" ||
        column.data_type === "decimal" ||
        column.data_type === "datetime",
    ),
  };
}
