import { describe, expect, it } from "vitest";

import { ApiRequestError } from "./api/client";
import { classifyAssetManagementError } from "./assetManagementErrors";

function requestError(code: string, routeNotFound = false) {
  return new ApiRequestError({
    status: 404,
    code,
    message: code,
    routeNotFound,
    correlationId: "request-1",
  });
}

describe("asset management errors", () => {
  it("distinguishes a missing API route from a missing asset", () => {
    const contract = classifyAssetManagementError(
      requestError("api_contract_mismatch", true),
      "metadata_update_failed",
    );
    const asset = classifyAssetManagementError(
      requestError("dataset_version_not_found"),
      "metadata_update_failed",
    );

    expect(contract).toMatchObject({
      code: "api_contract_mismatch",
      kind: "contract_mismatch",
      correlationId: "request-1",
    });
    expect(contract.message).toContain("dev.ps1");
    expect(asset).toMatchObject({
      code: "dataset_version_not_found",
      kind: "asset_not_found",
    });
    expect(asset.message).toContain("목록을 새로고침");
  });

  it("keeps conflicts, dependency blockers, and integrity failures distinct", () => {
    expect(
      classifyAssetManagementError(
        requestError("asset_user_metadata_conflict"),
        "metadata_update_failed",
      ).kind,
    ).toBe("metadata_conflict");
    expect(
      classifyAssetManagementError(
        requestError("dataset_version_deletion_analysis_dependency"),
        "dataset_version_deletion_failed",
      ).kind,
    ).toBe("deletion_blocked");
    expect(
      classifyAssetManagementError(
        requestError("regression_model_manifest_checksum_mismatch"),
        "regression_model_deletion_failed",
      ).kind,
    ).toBe("integrity_error");
  });
});
