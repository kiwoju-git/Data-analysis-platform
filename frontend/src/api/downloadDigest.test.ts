import { webcrypto } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchManagedReportDownload } from "./reports";
import type { ManagedReportDescriptor } from "./types/reports";
import type { DoeAnalysisAssetDescriptor } from "./types/doeModelWorkflow";
import { downloadFactorialAsset } from "./factorialWorkflow";
import { downloadSha256 } from "./downloadDigest";

const downloaded = vi.hoisted(() => vi.fn());
vi.mock("./client", async (original) => ({ ...await original<typeof import("./client")>(), triggerBrowserDownload: downloaded }));

const abcHash = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
const report: ManagedReportDescriptor = {
  export_id: "10000000-0000-4000-8000-000000000001",
  source: { kind: "analysis_run", analysis_id: "10000000-0000-4000-8000-000000000002", expected_source_sha256: "a".repeat(64) },
  source_ref_sha256: "b".repeat(64), locale: "en", report_level: "full", renderer_version: "1",
  sha256: abcHash, size_bytes: 3, created_at: "2026-10-18T00:00:00Z", stale: false, media_type: "text/html",
};
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

describe("shared SHA-256 download digest", () => {
  it.each(["fallback", "webcrypto"] as const)("matches published SHA-256 vectors using %s", async (implementation) => {
    vi.stubGlobal("crypto", implementation === "webcrypto" ? webcrypto : undefined);
    const vectors = [
      ["", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
      ["abc", abcHash],
      ["abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq", "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"],
      ["a".repeat(1_000_000), "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"],
    ];
    for (const [input, expected] of vectors) expect(await downloadSha256(new TextEncoder().encode(input).buffer)).toBe(expected);
  });

  it("uses available WebCrypto and never hides an operational digest failure", async () => {
    const error = new Error("synthetic_native_digest_failure");
    const digest = vi.fn().mockRejectedValue(error);
    vi.stubGlobal("crypto", { subtle: { digest } });
    const bytes = new ArrayBuffer(3);
    await expect(downloadSha256(bytes)).rejects.toBe(error);
    expect(digest).toHaveBeenCalledWith("SHA-256", bytes);
  });
});

describe("download bytes on HTTP LAN", () => {
  it.each([undefined, {}, { subtle: undefined }])("verifies the actual report bytes without SubtleCrypto (%j)", async (cryptoValue) => {
    vi.stubGlobal("crypto", cryptoValue);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("abc", { headers: { "Content-Type": "text/html" } })));
    const result = await fetchManagedReportDownload(report);
    expect(await result.blob.text()).toBe("abc");
  });

  it.each([undefined, webcrypto])("rejects one-byte corruption even when length and claimed digest match", async (cryptoValue) => {
    vi.stubGlobal("crypto", cryptoValue);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("abd", { headers: { ETag: `"${abcHash}"`, "Content-Type": "text/html" } })));
    await expect(fetchManagedReportDownload(report)).rejects.toThrow("managed_report_checksum_mismatch");
  });

  it.each(["abc", "abd"])("keeps Factorial asset integrity checks on HTTP LAN for %s", async (content) => {
    vi.stubGlobal("crypto", {});
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(content, { headers: { "Content-Type": "text/html" } })));
    const asset: DoeAnalysisAssetDescriptor = {
      asset_id: report.export_id, analysis_id: "10000000-0000-4000-8000-000000000002", kind: "html_report", schema_version: 2,
      locale: "en", source_analysis_sha256: "a".repeat(64), sha256: abcHash, media_type: "text/html", size_bytes: 3, created_at: report.created_at,
    };
    if (content === "abc") {
      await downloadFactorialAsset("design", asset.analysis_id, asset);
      expect(downloaded).toHaveBeenCalledOnce();
    } else {
      await expect(downloadFactorialAsset("design", asset.analysis_id, asset)).rejects.toThrow("doe_factorial_asset_checksum_mismatch");
      expect(downloaded).not.toHaveBeenCalled();
    }
  });
});
