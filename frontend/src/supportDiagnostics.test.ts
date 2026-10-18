import { afterEach, describe, expect, it } from "vitest";

import {
  buildSupportDiagnostics,
  clearSupportObservation,
  observeApiFailure,
  observeApiResponse,
  observeNetworkFailure,
  readSupportObservation,
} from "./supportDiagnostics";

afterEach(clearSupportObservation);

const context = {
  appVersion: "0.1.0",
  buildCommit: "a".repeat(40),
  apiContractVersion: 24,
  metadataSchemaVersion: 22,
  methodId: "eda.normality",
  catalogMethodIds: ["eda.normality"],
};
const options = { locale: "en", width: 1440, height: 900, now: new Date("2026-10-20T01:02:03Z") };

describe("privacy-safe support diagnostics", () => {
  it("constructs only approved fields, not raw objects or identifiers", () => {
    const secret = "SECRET customer_name column_name raw_cell C:/private/data.csv ?token=abc";
    observeApiFailure({ code: "analysis_failed", correlationId: "00000000-0000-4000-8000-000000000001", status: 422, message: secret } as never);
    const diagnostics = buildSupportDiagnostics({ ...context, rawData: secret, columns: [secret], url: secret, model: { coefficient: secret } } as never, options);
    expect(diagnostics).toEqual({
      schema_version: 1,
      created_at: "2026-10-20T01:02:03.000Z",
      app_version: "0.1.0",
      build_commit: "a".repeat(40),
      api_contract_version: 24,
      metadata_schema_version: 22,
      locale: "en",
      viewport: { width: 1440, height: 900 },
      method_id: "eda.normality",
      error_code: "analysis_failed",
      correlation_id: "00000000-0000-4000-8000-000000000001",
      server_connection: "connected",
    });
    expect(JSON.stringify(diagnostics)).not.toContain(secret);
  });

  it("rejects malformed versions, method IDs, codes and arbitrary correlation headers", () => {
    observeApiFailure({ code: "failure/private?secret=raw", correlationId: "operator@example.com", status: 500 });
    const diagnostics = buildSupportDiagnostics({ appVersion: "SECRET", buildCommit: "C:/private", apiContractVersion: NaN, metadataSchemaVersion: -1, methodId: "raw.column", catalogMethodIds: [] }, { ...options, locale: "secret", width: Infinity, height: -5 });
    expect(diagnostics).toMatchObject({ app_version: null, build_commit: null, api_contract_version: null, metadata_schema_version: null, method_id: null, error_code: null, correlation_id: null, locale: "unknown", viewport: { width: null, height: null } });
    expect(JSON.stringify(diagnostics)).not.toMatch(/SECRET|private|operator|raw.column/);
  });

  it("keeps only the latest sanitized failure and never reads raw message getters", () => {
    observeApiFailure({ code: "first_failure", correlationId: null, status: 400 });
    observeApiFailure({ code: "second_failure", correlationId: null, status: 503, get message() { throw new Error("Raw message accessed"); } } as never);
    expect(readSupportObservation().errorCode).toBe("second_failure");
    expect(JSON.stringify(readSupportObservation())).not.toContain("first_failure");
    observeApiResponse();
    expect(readSupportObservation().serverConnection).toBe("connected");
    observeNetworkFailure();
    expect(readSupportObservation()).toEqual({ errorCode: "api_unreachable", correlationId: null, serverConnection: "unreachable" });
  });

  it("returns independent snapshots and unknown defaults without browser globals", () => {
    const first = readSupportObservation();
    first.errorCode = "mutated";
    expect(readSupportObservation().errorCode).toBeNull();
    expect(buildSupportDiagnostics({}, options)).toMatchObject({ method_id: null, server_connection: "unknown", error_code: null });
  });

  it("validates both catalog membership and machine-ID syntax", () => {
    expect(buildSupportDiagnostics({ ...context, methodId: "eda.other" }, options).method_id).toBeNull();
    expect(buildSupportDiagnostics({ ...context, methodId: "private filename.csv", catalogMethodIds: ["private filename.csv"] }, options).method_id).toBeNull();
  });
});
