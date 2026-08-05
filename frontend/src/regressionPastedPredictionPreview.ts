export type RegressionPredictionDelimiter = "auto" | "tab" | "comma";

export function parseRegressionPastedPredictionPreview(
  content: string,
  delimiter: RegressionPredictionDelimiter,
  hasHeader: boolean,
) {
  const lines = content
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .filter((line) => line.trim() !== "");
  if (lines.length === 0) {
    return {
      headers: [] as string[],
      rows: [] as string[][],
      columnCount: 0,
      nonEmptyLineCount: 0,
      headerRowCount: 0,
      dataRowCount: 0,
      inferredHeaderState: "unknown" as const,
      validationCode: "regression_pasted_prediction_no_rows" as const,
    };
  }
  const separator = delimiter === "tab"
    ? "\t"
    : delimiter === "comma"
      ? ","
      : lines[0].includes("\t")
        ? "\t"
        : ",";
  const previewRows = lines
    .slice(0, 11)
    .map((line) => line.split(separator).map((cell) => cell.trim()));
  const columnCount = Math.max(...previewRows.map((row) => row.length));
  const headers = hasHeader
    ? previewRows[0]
    : Array.from({ length: columnCount }, (_, index) => `입력 ${index + 1}`);
  const dataRows = hasHeader ? previewRows.slice(1) : previewRows;
  const dataRowCount = lines.length - (hasHeader ? 1 : 0);
  return {
    headers,
    rows: dataRows.slice(0, 10),
    columnCount,
    nonEmptyLineCount: lines.length,
    headerRowCount: hasHeader ? 1 : 0,
    dataRowCount,
    inferredHeaderState: hasHeader
      ? dataRowCount > 0 ? "header" as const : "header_only" as const
      : "data" as const,
    validationCode: hasHeader && dataRowCount === 0
      ? "regression_pasted_prediction_header_without_data" as const
      : null,
  };
}
