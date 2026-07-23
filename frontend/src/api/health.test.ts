import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchRuntimeInfo } from "./health";

describe("fetchRuntimeInfo", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses a CORS-safelisted GET without a cache-control request header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          service: "datalab-studio-api",
          app_version: "0.1.0",
          api_contract_version: 3,
          metadata_schema_version: 16,
          build_commit: "unknown",
          capabilities: {
            asset_management: true,
            dataset_version_metadata: true,
            dataset_version_deletion: true,
            dataset_version_archiving: true,
            dataset_version_cascade_deletion: true,
            dataset_version_preserve_unverified_cleanup: true,
            regression_model_metadata: true,
            regression_model_deletion: true,
            dedicated_predict: true,
            dedicated_response_optimizer: true,
            bayesian_optimization: true,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchRuntimeInfo();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBeUndefined();
    expect(init.headers).toEqual({ Accept: "application/json" });
  });
});
