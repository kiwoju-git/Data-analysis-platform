import type { RuntimeCapabilities, RuntimeInfoResponse } from "./api";

export const EXPECTED_API_CONTRACT_VERSION = 3;
export const MINIMUM_METADATA_SCHEMA_VERSION = 16;

export const REQUIRED_RUNTIME_CAPABILITIES = [
  "asset_management",
  "dataset_version_metadata",
  "dataset_version_deletion",
  "dataset_version_archiving",
  "dataset_version_cascade_deletion",
  "dataset_version_preserve_unverified_cleanup",
  "regression_model_metadata",
  "regression_model_deletion",
  "dedicated_predict",
  "dedicated_response_optimizer",
  "bayesian_optimization",
] as const satisfies readonly (keyof RuntimeCapabilities)[];

export const FRONTEND_BUILD_COMMIT = normalizeBuildCommit(import.meta.env.VITE_GIT_COMMIT);

export interface RuntimeCompatibilityResult {
  compatible: boolean;
  code: string | null;
  missingCapabilities: (keyof RuntimeCapabilities)[];
}

function normalizeBuildCommit(value: unknown): string {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : "unknown";
}

export function evaluateRuntimeCompatibility(
  runtime: RuntimeInfoResponse,
  frontendBuildCommit = FRONTEND_BUILD_COMMIT,
): RuntimeCompatibilityResult {
  const missingCapabilities = REQUIRED_RUNTIME_CAPABILITIES.filter(
    (capability) => runtime.capabilities[capability] !== true,
  );
  if (runtime.api_contract_version !== EXPECTED_API_CONTRACT_VERSION) {
    return { compatible: false, code: "api_contract_version_mismatch", missingCapabilities };
  }
  if (runtime.metadata_schema_version < MINIMUM_METADATA_SCHEMA_VERSION) {
    return { compatible: false, code: "metadata_schema_version_mismatch", missingCapabilities };
  }
  if (missingCapabilities.length > 0) {
    return { compatible: false, code: "runtime_capability_missing", missingCapabilities };
  }
  if (
    frontendBuildCommit !== "unknown" &&
    runtime.build_commit !== "unknown" &&
    frontendBuildCommit !== runtime.build_commit
  ) {
    return { compatible: false, code: "runtime_build_commit_mismatch", missingCapabilities };
  }
  return { compatible: true, code: null, missingCapabilities };
}
