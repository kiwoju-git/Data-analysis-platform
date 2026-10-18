import { afterEach, describe, expect, it, vi } from "vitest";
import { datasetRequestErrorCode } from "../datasetRequestErrors";
import { ApiRequestError } from "./client";
import {
  confirmDatasetParsing, createDatasetFromPastedText, fetchDatasetProfile,
  fetchDatasetVersion, fetchRowsPreview, updateDatasetSchema, uploadDataset,
} from "./datasets";

const versionId = "00000000-0000-4000-8000-000000000001";
const rawText = "source \uE000language.selector\uE001 한글";
const calls = [
  { label: "upload", code: "upload_size_limit_exceeded", invoke: () => uploadDataset(new File([rawText], "synthetic.csv")) },
  { label: "paste", code: "pasted_data_too_large", invoke: () => createDatasetFromPastedText({ content: rawText, original_filename: "synthetic.txt" }) },
  { label: "confirmation", code: "parsing_configuration_invalid", invoke: () => confirmDatasetParsing("synthetic-dataset", {
    parsing: {
      kind: "delimited_text", encoding: "utf-8", delimiter: ",", quote_char: '"',
      decimal: ".", thousands: null, has_header: true, header_row: 1,
      data_start_row: 2, missing_tokens: [], xlsx_sheet_name: null,
    }, columns: [],
  }) },
  { label: "version", code: "dataset_version_not_found", invoke: () => fetchDatasetVersion(versionId) },
  { label: "schema", code: "dataset_schema_conflict", invoke: () => updateDatasetSchema(versionId, { expected_schema_hash: "a".repeat(64), columns: [] }) },
  { label: "preview", code: "rows_preview_failed", invoke: () => fetchRowsPreview(versionId, 0, 10) },
  { label: "profile", code: "dataset_profile_failed", invoke: () => fetchDatasetProfile(versionId) },
] as const;

describe("dataset workflow transport errors", () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each(calls)("preserves typed $label errors through the workflow presentation boundary", async ({ code, invoke }) => {
    const status = code === "dataset_version_not_found" ? 404 : code === "dataset_schema_conflict" ? 409 : 422;
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({
      error: { code, message: rawText, correlation_id: "synthetic-correlation" },
    }), { status }))));
    const error: unknown = await invoke().catch((failure: unknown) => failure);
    expect(error).toBeInstanceOf(ApiRequestError);
    expect(error).toMatchObject({ code, status, message: code, backendMessage: rawText, correlationId: "synthetic-correlation" });
    expect(datasetRequestErrorCode(error, "fallback")).toBe(code);
  });

  it("distinguishes a missing API route from a missing dataset", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 }))));
    const error: unknown = await fetchDatasetVersion(versionId).catch((failure: unknown) => failure);
    expect(error).toMatchObject({ code: "api_contract_mismatch", routeNotFound: true, status: 404 });
    expect(datasetRequestErrorCode(error, "fallback")).not.toBe("dataset_version_not_found");
  });

  it("does not rewrite successful dataset payload text or pasted input", async () => {
    const payload = { original_filename: rawText, warnings: [{ code: "synthetic", message: rawText }] };
    const fetch = vi.fn((_url: unknown, options: RequestInit) => {
      if (typeof options.body !== "string") throw new Error("Expected the original JSON request body");
      expect(JSON.parse(options.body)).toEqual({ content: rawText, original_filename: "synthetic.txt" });
      return Promise.resolve(new Response(JSON.stringify(payload)));
    });
    vi.stubGlobal("fetch", fetch);
    expect(await createDatasetFromPastedText({ content: rawText, original_filename: "synthetic.txt" })).toEqual(payload);
  });

  it("serializes the supplied immutable schema base hash without rewriting user fields", async () => {
    const request = { expected_schema_hash: "b".repeat(64), columns: [{ column_id: "column-1", display_name: rawText, unit: "kg", measurement_level: "continuous" as const, role: "feature" as const }] };
    vi.stubGlobal("fetch", vi.fn((_url: unknown, options: RequestInit) => {
      expect(options.method).toBe("PATCH");
      if (typeof options.body !== "string") throw new Error("Expected JSON request body");
      expect(JSON.parse(options.body)).toEqual(request);
      return Promise.resolve(new Response(JSON.stringify({ schema_hash: "c".repeat(64) })));
    }));
    await updateDatasetSchema(versionId, request);
  });
});
