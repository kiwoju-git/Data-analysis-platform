import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequestError, fetchApi } from "./api/client";
import { clearSupportObservation, readSupportObservation } from "./supportDiagnostics";

afterEach(() => { clearSupportObservation(); vi.unstubAllGlobals(); });

describe("support error boundary observation", () => {
  it("observes only the already parsed error fields, reading the body once", async () => {
    const secret = "SECRET_DATA /private/customer.csv ?auth=secret <column_name>";
    const response = new Response(JSON.stringify({ error: { code: "analysis_failed", message: secret, correlation_id: "00000000-0000-4000-8000-000000000001" }, rows: [secret] }), { status: 422 });
    const json = vi.spyOn(response, "json");
    const error = await apiRequestError(response, "analysis_failed");
    expect(json).toHaveBeenCalledTimes(1);
    expect(error.backendMessage).toBe(secret);
    expect(JSON.stringify(readSupportObservation())).not.toContain(secret);
    expect(readSupportObservation()).toEqual({ errorCode: "analysis_failed", correlationId: "00000000-0000-4000-8000-000000000001", serverConnection: "connected" });
  });

  it("never consumes successful bodies or records request URLs and data", async () => {
    const response = new Response("PRIVATE successful data");
    const fetch = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetch);
    const result = await fetchApi("http://127.0.0.1/api/private?secret=QUERY", { method: "POST", body: "PRIVATE request" });
    expect(result).toBe(response);
    expect(response.bodyUsed).toBe(false);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(readSupportObservation()).toEqual({ errorCode: null, correlationId: null, serverConnection: "connected" });
  });

  it("records a fixed network code without copying raw exceptions or aborts", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("SECRET hostname and path")));
    await expect(fetchApi("/api/private")).rejects.toThrow("api_unreachable");
    expect(readSupportObservation()).toEqual({ errorCode: "api_unreachable", correlationId: null, serverConnection: "unreachable" });
    clearSupportObservation();
    const abort = new DOMException("private abort reason", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(fetchApi("/api/private")).rejects.toBe(abort);
    expect(readSupportObservation().errorCode).toBeNull();
  });
});
