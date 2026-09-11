import { parsePastedTablePreview, type PastePreviewDelimiter } from "../pastedTablePreview";

export type DoeResponsePasteLayout = "values" | "run_order";
export type DoeResponsePasteError = "empty" | "shape" | "count" | "header" | "run" | "number" | "limit";
export interface DoeResponsePasteRow { runOrder: number; value: string }
export type DoeResponsePasteResult =
  | { ok: true; rows: DoeResponsePasteRow[] }
  | { ok: false; error: DoeResponsePasteError };

export function parseDoeResponsePaste(
  content: string,
  runOrders: readonly number[],
  options: { layout: DoeResponsePasteLayout; hasHeader: boolean; delimiter?: PastePreviewDelimiter },
): DoeResponsePasteResult {
  if (content.trim() === "") return { ok: false, error: "empty" };
  if (runOrders.length > 256 || content.length > 100_000) return { ok: false, error: "limit" };
  const parsed = parsePastedTablePreview(content, {
    delimiter: options.delimiter, maxRows: 258, maxColumns: 3, maxCells: 774,
    maxScanCharacters: 100_000,
  });
  if (parsed.rawModeOnly || parsed.countsAreLowerBounds || parsed.truncatedRows || parsed.truncatedColumns) {
    return { ok: false, error: "shape" };
  }
  const width = options.layout === "values" ? 1 : 2;
  if (parsed.rows.some((row) => row.length !== width || row.some((value) => value.trim() === ""))) {
    return { ok: false, error: "shape" };
  }
  if (options.hasHeader) {
    const header = parsed.rows[0]?.map((cell) => cell.trim().toLowerCase()) ?? [];
    if (new Set(header).size !== width || (options.layout === "run_order" && header[0] !== "run_order")) {
      return { ok: false, error: "header" };
    }
  }
  const values = parsed.rows.slice(options.hasHeader ? 1 : 0);
  if (values.length !== runOrders.length) return { ok: false, error: "count" };
  const expected = new Set(runOrders);
  if (expected.size !== runOrders.length || runOrders.length === 0) return { ok: false, error: "run" };
  const sorted = [...runOrders].sort((a, b) => a - b);
  const seen = new Set<number>();
  const rows: DoeResponsePasteRow[] = [];
  for (const [index, row] of values.entries()) {
    const runText = options.layout === "run_order" ? row[0].trim() : String(sorted[index]);
    const runOrder = Number(runText);
    if (!/^\d+$/.test(runText) || !expected.has(runOrder) || seen.has(runOrder)) {
      return { ok: false, error: "run" };
    }
    seen.add(runOrder);
    const value = row[width - 1].trim();
    if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(value) || !Number.isFinite(Number(value))) {
      return { ok: false, error: "number" };
    }
    rows.push({ runOrder, value });
  }
  return { ok: true, rows: rows.sort((a, b) => a.runOrder - b.runOrder) };
}
