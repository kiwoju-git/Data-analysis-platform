import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { RuntimeInfoResponse } from "./api";
import { apiRequestError } from "./api/client";
import { RuntimeCompatibilityGate } from "./RuntimeMismatchPage";
import {
  evaluateRuntimeCompatibility,
  EXPECTED_API_CONTRACT_VERSION,
} from "./runtimeCompatibility";

describe("runtime compatibility", () => {
  it("accepts the current contract and required capabilities", () => {
    expect(evaluateRuntimeCompatibility(runtimeInfo())).toEqual({
      compatible: true,
      code: null,
      missingCapabilities: [],
    });
  });

  it("blocks old contracts, missing capabilities, and known commit mismatches", () => {
    expect(
      evaluateRuntimeCompatibility(runtimeInfo({ api_contract_version: 1 })),
    ).toMatchObject({ compatible: false, code: "api_contract_version_mismatch" });
    expect(
      evaluateRuntimeCompatibility(
        runtimeInfo({
          capabilities: { ...runtimeInfo().capabilities, dataset_version_metadata: false },
        }),
      ),
    ).toMatchObject({
      compatible: false,
      code: "runtime_capability_missing",
      missingCapabilities: ["dataset_version_metadata"],
    });
    expect(
      evaluateRuntimeCompatibility(runtimeInfo({ build_commit: "backend-build" }), "frontend-build"),
    ).toMatchObject({ compatible: false, code: "runtime_build_commit_mismatch" });
  });

  it("distinguishes a missing API route from a domain asset not found", async () => {
    const routeError = await apiRequestError(
      new Response('{"detail":"Not Found"}', { status: 404 }),
      "metadata_update_failed",
    );
    const assetError = await apiRequestError(
      new Response(
        JSON.stringify({
          error: {
            code: "dataset_version_not_found",
            message: "missing",
            correlation_id: "correlation-id",
          },
        }),
        { status: 404 },
      ),
      "metadata_update_failed",
    );

    expect(routeError).toMatchObject({
      status: 404,
      code: "api_contract_mismatch",
      routeNotFound: true,
    });
    expect(assetError).toMatchObject({
      status: 404,
      code: "dataset_version_not_found",
      routeNotFound: false,
      correlationId: "correlation-id",
    });
  });

  it("renders blocking recovery steps without exposing a path", () => {
    const html = renderToStaticMarkup(
      <RuntimeCompatibilityGate
        onRetry={() => undefined}
        state={{
          kind: "blocked",
          runtime: runtimeInfo({ api_contract_version: 1 }),
          result: evaluateRuntimeCompatibility(runtimeInfo({ api_contract_version: 1 })),
          error: "api_contract_version_mismatch",
        }}
      />,
    );

    expect(html).toContain("프런트엔드와 백엔드 버전이 일치하지 않습니다.");
    expect(html).toContain("다시 확인");
    expect(html).toContain(`expected ${EXPECTED_API_CONTRACT_VERSION}`);
    expect(html).toContain("포트 8000");
    expect(html).not.toContain("D:\\");
  });
});

function runtimeInfo(overrides: Partial<RuntimeInfoResponse> = {}): RuntimeInfoResponse {
  return {
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
    ...overrides,
  };
}
