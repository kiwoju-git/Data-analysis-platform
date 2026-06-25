import type {
  AnalysisFilterCondition,
  AnalysisFilterOperator,
  DatasetColumnResponse,
} from "./api";

export interface AnalysisFilterDraft {
  id: string;
  column_id: string;
  operator: AnalysisFilterOperator;
  value: string;
}

export interface FilterOperatorOption {
  value: AnalysisFilterOperator;
  label: string;
}

const numericDataTypes = new Set<DatasetColumnResponse["data_type"]>(["integer", "decimal"]);
const valueLessOperators = new Set<AnalysisFilterOperator>(["is_missing", "is_not_missing"]);

const baseOperatorOptions: FilterOperatorOption[] = [
  { value: "is_not_missing", label: "결측 아님" },
  { value: "is_missing", label: "결측" },
  { value: "eq", label: "=" },
  { value: "ne", label: "!=" },
];

const numericOperatorOptions: FilterOperatorOption[] = [
  { value: "gt", label: ">" },
  { value: "gte", label: ">=" },
  { value: "lt", label: "<" },
  { value: "lte", label: "<=" },
];

export function createDefaultFilterDraft(
  columns: DatasetColumnResponse[],
): AnalysisFilterDraft | null {
  const firstColumn = columns[0];
  if (firstColumn === undefined) {
    return null;
  }
  return {
    id: createFilterDraftId(),
    column_id: firstColumn.column_id,
    operator: "is_not_missing",
    value: "",
  };
}

export function filterOperatorOptions(column: DatasetColumnResponse): FilterOperatorOption[] {
  return isNumericColumn(column)
    ? [...baseOperatorOptions, ...numericOperatorOptions]
    : baseOperatorOptions;
}

export function filterOperatorRequiresValue(operator: AnalysisFilterOperator): boolean {
  return !valueLessOperators.has(operator);
}

export function normalizeFilterDraft(
  draft: AnalysisFilterDraft,
  columns: DatasetColumnResponse[],
): AnalysisFilterDraft {
  const selectedColumn = findColumn(columns, draft.column_id) ?? columns[0] ?? null;
  if (selectedColumn === null) {
    return draft;
  }

  const operatorOptions = filterOperatorOptions(selectedColumn);
  const operator = operatorOptions.some((option) => option.value === draft.operator)
    ? draft.operator
    : operatorOptions[0].value;
  return {
    ...draft,
    column_id: selectedColumn.column_id,
    operator,
    value: filterOperatorRequiresValue(operator) ? draft.value : "",
  };
}

export function validateAnalysisFilterDrafts(
  drafts: AnalysisFilterDraft[],
  columns: DatasetColumnResponse[],
): string | null {
  for (const draft of drafts) {
    const column = findColumn(columns, draft.column_id);
    if (column === null) {
      return "filter_column_not_found";
    }
    if (!filterOperatorOptions(column).some((operator) => operator.value === draft.operator)) {
      return "filter_operator_not_supported_for_column";
    }
    if (filterOperatorRequiresValue(draft.operator) && draft.value.trim() === "") {
      return "filter_value_required";
    }
  }
  return null;
}

export function serializeAnalysisFilterDrafts(
  drafts: AnalysisFilterDraft[],
  columns: DatasetColumnResponse[],
): AnalysisFilterCondition[] {
  const validationError = validateAnalysisFilterDrafts(drafts, columns);
  if (validationError !== null) {
    throw new Error(validationError);
  }

  return drafts.map((draft) => {
    const condition: AnalysisFilterCondition = {
      column_id: draft.column_id,
      operator: draft.operator,
    };
    if (filterOperatorRequiresValue(draft.operator)) {
      condition.value = draft.value.trim();
    }
    return condition;
  });
}

export function findFilterColumn(
  columns: DatasetColumnResponse[],
  columnId: string,
): DatasetColumnResponse | null {
  return findColumn(columns, columnId);
}

export function isNumericFilterColumn(column: DatasetColumnResponse): boolean {
  return isNumericColumn(column);
}

function findColumn(
  columns: DatasetColumnResponse[],
  columnId: string,
): DatasetColumnResponse | null {
  return columns.find((column) => column.column_id === columnId) ?? null;
}

function isNumericColumn(column: DatasetColumnResponse): boolean {
  return numericDataTypes.has(column.data_type);
}

function createFilterDraftId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `filter-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}
