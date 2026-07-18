import { afterEach, describe, expect, it, vi } from "vitest";

import { createDatasetFromPastedText } from "./api";
import {
  detectPastedTableDelimiter,
  parsePastedTablePreview,
  spreadsheetColumnLabel,
  utf8ByteCount,
} from "./pastedTablePreview";

describe("parsePastedTablePreview", () => {
  it("parses Excel TSV with CRLF, Korean labels, and exact empty cells", () => {
    const preview = parsePastedTablePreview("그룹\t측정값\t메모\r\n가\t\t첫 행\r\n나\t2\t");

    expect(preview.delimiter).toBe("\t");
    expect(preview.lineEnding).toBe("CRLF");
    expect(preview.rows).toEqual([
      ["그룹", "측정값", "메모"],
      ["가", "", "첫 행"],
      ["나", "2", ""],
    ]);
    expect(preview.detectedRowCount).toBe(3);
    expect(preview.detectedColumnCount).toBe(3);
    expect(preview.emptyCellCount).toBe(2);
    expect(preview.trailingEmptyCellCount).toBe(1);
  });

  it("does not invent a row for a trailing newline", () => {
    const preview = parsePastedTablePreview("A\tB\n1\t2\n");

    expect(preview.lineEnding).toBe("LF");
    expect(preview.detectedRowCount).toBe(2);
    expect(preview.rows).toEqual([["A", "B"], ["1", "2"]]);
  });

  it("detects ragged rows and preserves trailing tabs", () => {
    const preview = parsePastedTablePreview("A\tB\tC\n1\t2\n3\t4\t");

    expect(preview.rows[2]).toEqual(["3", "4", ""]);
    expect(preview.raggedRowCount).toBe(1);
    expect(preview.raggedRowIndices).toEqual([2]);
    expect(preview.warnings.map((warning) => warning.code)).toContain(
      "paste_preview_ragged_rows",
    );
  });

  it("parses quoted commas and escaped quotes", () => {
    const preview = parsePastedTablePreview('name,note\n"Kim, Min","said ""hello"""');

    expect(preview.delimiter).toBe(",");
    expect(preview.rows).toEqual([
      ["name", "note"],
      ["Kim, Min", 'said "hello"'],
    ]);
  });

  it("parses quoted tabs and embedded newlines without changing logical cells", () => {
    const preview = parsePastedTablePreview('A\tB\n"left\tright"\t"line 1\nline 2"');

    expect(preview.delimiter).toBe("\t");
    expect(preview.detectedRowCount).toBe(2);
    expect(preview.rows[1]).toEqual(["left\tright", "line 1\nline 2"]);
  });

  it("renders formula-like values only as text metadata", () => {
    const preview = parsePastedTablePreview("value\n=SUM(A1:A2)\n+cmd\n-safe\n@name");

    expect(preview.rows.slice(1).flat()).toEqual(["=SUM(A1:A2)", "+cmd", "-safe", "@name"]);
    expect(preview.formulaLikeCellCount).toBe(4);
    expect(preview.warnings.map((warning) => warning.code)).toContain(
      "paste_preview_formula_like_text",
    );
  });

  it("caps materialized rows, columns, and cells while retaining scan metadata", () => {
    const preview = parsePastedTablePreview("a\tb\tc\n1\t2\t3\n4\t5\t6", {
      maxRows: 2,
      maxColumns: 2,
      maxCells: 4,
    });

    expect(preview.rows).toEqual([["a", "b"], ["1", "2"]]);
    expect(preview.previewRowCount).toBe(2);
    expect(preview.previewColumnCount).toBe(2);
    expect(preview.detectedRowCount).toBe(3);
    expect(preview.detectedColumnCount).toBe(3);
    expect(preview.truncatedRows).toBe(true);
    expect(preview.truncatedColumns).toBe(true);
  });

  it("marks large-input structure counts as lower bounds after the scan cap", () => {
    const preview = parsePastedTablePreview("A\tB\n1\t2\n3\t4", {
      maxScanCharacters: 8,
    });

    expect(preview.countsAreLowerBounds).toBe(true);
    expect(preview.truncatedRows).toBe(true);
    expect(preview.warnings.map((warning) => warning.code)).toContain(
      "paste_preview_scan_truncated",
    );
  });

  it("falls back to raw mode for an unbalanced quote", () => {
    const preview = parsePastedTablePreview('A,B\n"unfinished');

    expect(preview.rawModeOnly).toBe(true);
    expect(preview.rows).toEqual([]);
    expect(preview.warnings).toEqual([
      expect.objectContaining({ code: "paste_preview_unbalanced_quote" }),
    ]);
  });

  it("handles empty and whitespace-only input without coercion", () => {
    expect(parsePastedTablePreview("").detectedRowCount).toBe(0);
    expect(parsePastedTablePreview("  \t ").rows).toEqual([["  ", " "]]);
  });

  it("detects conservative supported delimiters and spreadsheet labels", () => {
    expect(detectPastedTableDelimiter("A,B,C\n1,hello\tworld,3")).toBe(",");
    expect(detectPastedTableDelimiter("A\tB\tC\n1\t2\t3")).toBe("\t");
    expect(detectPastedTableDelimiter("A;B;C\n1;2;3")).toBe(";");
    expect(detectPastedTableDelimiter("A|B\n1|2")).toBe("|");
    expect(detectPastedTableDelimiter("single value")).toBeNull();
    expect(spreadsheetColumnLabel(0)).toBe("A");
    expect(spreadsheetColumnLabel(25)).toBe("Z");
    expect(spreadsheetColumnLabel(26)).toBe("AA");
  });

  it("counts UTF-8 bytes without storing an encoded copy", () => {
    expect(utf8ByteCount("A가😀")).toBe(8);
  });
});

describe("pasted dataset API source text", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits the original clipboard string byte-for-byte in the JSON request", async () => {
    const original = '열1\t열2\r\n"line\nvalue"\t\r\n=1+1\t"quoted"';
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          dataset_id: "11111111-1111-4111-8111-111111111111",
          original_filename: "pasted-data.txt",
          size_bytes: utf8ByteCount(original),
          sha256: "a".repeat(64),
          detected_format: "delimited_text",
          parsing: {
            kind: "delimited_text",
            encoding_candidates: ["utf-8"],
            suggested_encoding: "utf-8",
            delimiter_candidates: [],
            suggested_delimiter: "\t",
            quote_char: '"',
            decimal: ".",
            thousands: null,
            has_header: true,
            header_row: 1,
            data_start_row: 2,
            xlsx_requires_sheet_selection: false,
          },
          warnings: [],
          next_step: "confirm_schema",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createDatasetFromPastedText({
      content: original,
      original_filename: "pasted-data.txt",
    });

    const firstCall: unknown = fetchMock.mock.calls[0];
    expect(Array.isArray(firstCall)).toBe(true);
    const requestInit: unknown = Array.isArray(firstCall) ? firstCall[1] : null;
    const requestBody =
      typeof requestInit === "object" && requestInit !== null && "body" in requestInit
        ? (requestInit as Record<string, unknown>).body
        : null;
    expect(typeof requestBody).toBe("string");
    const submitted = JSON.parse(requestBody as string) as { content: string };
    expect(submitted.content).toBe(original);
    expect(Array.from(new TextEncoder().encode(submitted.content))).toEqual(
      Array.from(new TextEncoder().encode(original)),
    );
  });
});
