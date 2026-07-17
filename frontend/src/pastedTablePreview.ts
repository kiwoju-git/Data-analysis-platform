export const MAX_PASTE_PREVIEW_ROWS = 200;
export const MAX_PASTE_PREVIEW_COLUMNS = 100;
export const MAX_PASTE_PREVIEW_CELLS = 20_000;
export const MAX_PASTE_PREVIEW_SCAN_CHARACTERS = 2_000_000;

export type PastePreviewDelimiter = "\t" | "," | ";" | "|" | null;
export type PastePreviewLineEnding = "CRLF" | "LF" | "CR" | "mixed" | "none";

export interface PastePreviewWarning {
  code:
    | "paste_preview_ragged_rows"
    | "paste_preview_trailing_empty_cells"
    | "paste_preview_truncated"
    | "paste_preview_scan_truncated"
    | "paste_preview_unbalanced_quote"
    | "paste_preview_formula_like_text";
  message: string;
}

export interface PastedTablePreview {
  delimiter: PastePreviewDelimiter;
  lineEnding: PastePreviewLineEnding;
  rows: string[][];
  previewRowCount: number;
  previewColumnCount: number;
  detectedRowCount: number;
  detectedColumnCount: number;
  countsAreLowerBounds: boolean;
  emptyCellCount: number;
  raggedRowCount: number;
  raggedRowIndices: number[];
  trailingEmptyCellCount: number;
  formulaLikeCellCount: number;
  truncatedRows: boolean;
  truncatedColumns: boolean;
  rawModeOnly: boolean;
  warnings: PastePreviewWarning[];
}

export interface PastedTablePreviewOptions {
  delimiter?: PastePreviewDelimiter;
  maxRows?: number;
  maxColumns?: number;
  maxCells?: number;
  maxScanCharacters?: number;
}

const delimiterCandidates: Exclude<PastePreviewDelimiter, null>[] = ["\t", ",", ";", "|"];

export function parsePastedTablePreview(
  text: string,
  options: PastedTablePreviewOptions = {},
): PastedTablePreview {
  const maxRows = positiveLimit(options.maxRows, MAX_PASTE_PREVIEW_ROWS);
  const maxColumns = positiveLimit(options.maxColumns, MAX_PASTE_PREVIEW_COLUMNS);
  const maxCells = positiveLimit(options.maxCells, MAX_PASTE_PREVIEW_CELLS);
  const maxScanCharacters = positiveLimit(
    options.maxScanCharacters,
    MAX_PASTE_PREVIEW_SCAN_CHARACTERS,
  );
  const delimiter =
    options.delimiter === undefined ? detectPastedTableDelimiter(text) : options.delimiter;
  const lineEnding = detectLineEnding(text);

  if (text.length === 0) {
    return emptyPreview(delimiter, lineEnding);
  }

  const scanLength = Math.min(text.length, maxScanCharacters);
  const countsAreLowerBounds = scanLength < text.length;
  const rows: string[][] = [];
  const previewWidths: number[] = [];
  const widthCounts = new Map<number, number>();
  let currentRow: string[] = [];
  let currentCell = "";
  let cellHasContent = false;
  let rowColumnCount = 0;
  let detectedRowCount = 0;
  let detectedColumnCount = 0;
  let emptyCellCount = 0;
  let trailingEmptyCellCount = 0;
  let formulaLikeCellCount = 0;
  let materializedCells = 0;
  let inQuotes = false;
  let quoteOpenedAtCellStart = false;
  let rowTouched = false;
  let lastTokenWasDelimiter = false;

  const finishCell = () => {
    rowColumnCount += 1;
    if (!cellHasContent) emptyCellCount += 1;
    if (/^[=+\-@]/.test(currentCell)) formulaLikeCellCount += 1;

    if (
      rows.length < maxRows &&
      currentRow.length < maxColumns &&
      materializedCells < maxCells
    ) {
      currentRow.push(currentCell);
      materializedCells += 1;
    }
    currentCell = "";
    cellHasContent = false;
    quoteOpenedAtCellStart = false;
  };

  const finishRow = () => {
    if (rowColumnCount === 0) finishCell();
    if (!cellHasContent && lastTokenWasDelimiter) trailingEmptyCellCount += 1;
    detectedRowCount += 1;
    detectedColumnCount = Math.max(detectedColumnCount, rowColumnCount);
    widthCounts.set(rowColumnCount, (widthCounts.get(rowColumnCount) ?? 0) + 1);
    if (rows.length < maxRows) {
      rows.push(currentRow);
      previewWidths.push(rowColumnCount);
    }
    currentRow = [];
    rowColumnCount = 0;
    rowTouched = false;
    lastTokenWasDelimiter = false;
  };

  let index = 0;
  while (index < scanLength) {
    const character = text[index];
    if (inQuotes) {
      if (character === '"') {
        if (index + 1 < scanLength && text[index + 1] === '"') {
          currentCell += '"';
          cellHasContent = true;
          index += 2;
          continue;
        }
        inQuotes = false;
        index += 1;
        continue;
      }
      currentCell += character;
      cellHasContent = true;
      rowTouched = true;
      index += 1;
      continue;
    }

    if (character === '"' && currentCell.length === 0 && !cellHasContent) {
      inQuotes = true;
      quoteOpenedAtCellStart = true;
      rowTouched = true;
      index += 1;
      continue;
    }

    if (delimiter !== null && character === delimiter) {
      finishCell();
      rowTouched = true;
      lastTokenWasDelimiter = true;
      index += 1;
      continue;
    }

    if (character === "\r" || character === "\n") {
      finishCell();
      finishRow();
      if (character === "\r" && index + 1 < scanLength && text[index + 1] === "\n") {
        index += 2;
      } else {
        index += 1;
      }
      continue;
    }

    currentCell += character;
    cellHasContent = true;
    rowTouched = true;
    lastTokenWasDelimiter = false;
    index += 1;
  }

  const unbalancedQuote = inQuotes && !countsAreLowerBounds && quoteOpenedAtCellStart;
  if (!countsAreLowerBounds && (rowTouched || rowColumnCount > 0 || lastTokenWasDelimiter)) {
    finishCell();
    finishRow();
  } else if (countsAreLowerBounds && (rowTouched || rowColumnCount > 0 || lastTokenWasDelimiter)) {
    finishCell();
    finishRow();
  }

  if (unbalancedQuote) {
    return {
      ...emptyPreview(delimiter, lineEnding),
      countsAreLowerBounds: false,
      rawModeOnly: true,
      warnings: [
        {
          code: "paste_preview_unbalanced_quote",
          message: "따옴표 구조를 완전히 해석하지 못해 원문 보기로 전환했습니다.",
        },
      ],
    };
  }

  const raggedRowCount = detectedRowCount - (widthCounts.get(detectedColumnCount) ?? 0);
  const raggedRowIndices = previewWidths.flatMap((width, rowIndex) =>
    width === detectedColumnCount ? [] : [rowIndex + 1],
  );
  const previewColumnCount = Math.min(detectedColumnCount, maxColumns);
  const truncatedRows = countsAreLowerBounds || detectedRowCount > rows.length;
  const truncatedColumns = detectedColumnCount > previewColumnCount;
  const warnings: PastePreviewWarning[] = [];

  if (raggedRowCount > 0) {
    warnings.push({
      code: "paste_preview_ragged_rows",
      message: "행마다 열 수가 다릅니다. 최종 구조는 파싱 확정 단계에서 다시 확인하세요.",
    });
  }
  if (trailingEmptyCellCount > 0) {
    warnings.push({
      code: "paste_preview_trailing_empty_cells",
      message: "마지막 열이 빈 행이 있습니다.",
    });
  }
  if (truncatedRows || truncatedColumns) {
    warnings.push({
      code: "paste_preview_truncated",
      message: `미리보기는 첫 ${maxRows}행 ${maxColumns}열, 최대 ${maxCells.toLocaleString()}개 셀만 표시합니다. 전체 원문은 변경 없이 등록됩니다.`,
    });
  }
  if (countsAreLowerBounds) {
    warnings.push({
      code: "paste_preview_scan_truncated",
      message: `브라우저 응답성을 위해 앞 ${maxScanCharacters.toLocaleString()}자만 구조 검사했습니다. 표시된 행·열 수는 최소값이며 서버가 전체 원문을 다시 검증합니다.`,
    });
  }
  if (formulaLikeCellCount > 0) {
    warnings.push({
      code: "paste_preview_formula_like_text",
      message: "수식처럼 보이는 값은 계산하지 않고 문자로 표시합니다.",
    });
  }

  return {
    delimiter,
    lineEnding,
    rows,
    previewRowCount: rows.length,
    previewColumnCount,
    detectedRowCount,
    detectedColumnCount,
    countsAreLowerBounds,
    emptyCellCount,
    raggedRowCount,
    raggedRowIndices,
    trailingEmptyCellCount,
    formulaLikeCellCount,
    truncatedRows,
    truncatedColumns,
    rawModeOnly: false,
    warnings,
  };
}

export function detectPastedTableDelimiter(text: string): PastePreviewDelimiter {
  const sample = text.slice(0, 65_536);
  const candidates = delimiterCandidates
    .map((delimiter, priority) => ({
      delimiter,
      priority,
      widths: candidateRowWidths(sample, delimiter),
    }))
    .map(({ delimiter, priority, widths }) => {
      const usableWidths = widths.filter((width) => width > 0);
      const frequencies = new Map<number, number>();
      for (const width of usableWidths) {
        frequencies.set(width, (frequencies.get(width) ?? 0) + 1);
      }
      const [modeWidth, modeCount] = Array.from(frequencies.entries()).sort(
        (left, right) => right[1] - left[1] || right[0] - left[0],
      )[0] ?? [1, 0];
      return {
        delimiter,
        modeWidth,
        score:
          modeWidth <= 1 || usableWidths.length === 0
            ? -1
            : (modeCount / usableWidths.length) * 1_000 + modeWidth * 10 - priority,
      };
    })
    .filter((candidate) => candidate.score >= 0)
    .sort((left, right) => {
      if (left.delimiter === "\t" && right.delimiter !== "\t") return -1;
      if (right.delimiter === "\t" && left.delimiter !== "\t") return 1;
      return right.score - left.score;
    });
  return candidates[0]?.delimiter ?? null;
}

export function spreadsheetColumnLabel(columnIndex: number): string {
  if (!Number.isInteger(columnIndex) || columnIndex < 0) return "?";
  let current = columnIndex + 1;
  let label = "";
  while (current > 0) {
    const remainder = (current - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    current = Math.floor((current - 1) / 26);
  }
  return label;
}

export function pastedDelimiterLabel(delimiter: PastePreviewDelimiter): string {
  if (delimiter === "\t") return "Tab";
  if (delimiter === ",") return "Comma";
  if (delimiter === ";") return "Semicolon";
  if (delimiter === "|") return "Pipe";
  return "단일 열";
}

export function utf8ByteCount(text: string): number {
  let count = 0;
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index);
    if (code < 0x80) count += 1;
    else if (code < 0x800) count += 2;
    else if (code >= 0xd800 && code <= 0xdbff && index + 1 < text.length) {
      const next = text.charCodeAt(index + 1);
      if (next >= 0xdc00 && next <= 0xdfff) {
        count += 4;
        index += 1;
      } else {
        count += 3;
      }
    } else count += 3;
  }
  return count;
}

function candidateRowWidths(text: string, delimiter: string): number[] {
  const widths: number[] = [];
  let width = 1;
  let inQuotes = false;
  let atCellStart = true;
  for (let index = 0; index < text.length && widths.length < 24; index += 1) {
    const character = text[index];
    if (inQuotes) {
      if (character === '"') {
        if (text[index + 1] === '"') index += 1;
        else inQuotes = false;
      }
      continue;
    }
    if (character === '"' && atCellStart) {
      inQuotes = true;
      continue;
    }
    if (character === delimiter) {
      width += 1;
      atCellStart = true;
      continue;
    }
    if (character === "\r" || character === "\n") {
      widths.push(width);
      width = 1;
      atCellStart = true;
      if (character === "\r" && text[index + 1] === "\n") index += 1;
      continue;
    }
    atCellStart = false;
  }
  if (width > 1 || (text.length > 0 && !/[\r\n]$/.test(text))) widths.push(width);
  return widths;
}

function detectLineEnding(text: string): PastePreviewLineEnding {
  let crlf = 0;
  let lf = 0;
  let cr = 0;
  for (let index = 0; index < text.length; index += 1) {
    if (text[index] === "\r") {
      if (text[index + 1] === "\n") {
        crlf += 1;
        index += 1;
      } else cr += 1;
    } else if (text[index] === "\n") lf += 1;
  }
  const kinds = Number(crlf > 0) + Number(lf > 0) + Number(cr > 0);
  if (kinds === 0) return "none";
  if (kinds > 1) return "mixed";
  if (crlf > 0) return "CRLF";
  if (lf > 0) return "LF";
  return "CR";
}

function positiveLimit(value: number | undefined, fallback: number): number {
  return value === undefined || !Number.isInteger(value) || value <= 0 ? fallback : value;
}

function emptyPreview(
  delimiter: PastePreviewDelimiter,
  lineEnding: PastePreviewLineEnding,
): PastedTablePreview {
  return {
    delimiter,
    lineEnding,
    rows: [],
    previewRowCount: 0,
    previewColumnCount: 0,
    detectedRowCount: 0,
    detectedColumnCount: 0,
    countsAreLowerBounds: false,
    emptyCellCount: 0,
    raggedRowCount: 0,
    raggedRowIndices: [],
    trailingEmptyCellCount: 0,
    formulaLikeCellCount: 0,
    truncatedRows: false,
    truncatedColumns: false,
    rawModeOnly: false,
    warnings: [],
  };
}
