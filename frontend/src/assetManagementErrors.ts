import { ApiRequestError } from "./api/client";

export type AssetManagementErrorKind =
  | "contract_mismatch"
  | "asset_not_found"
  | "metadata_conflict"
  | "deletion_blocked"
  | "integrity_error"
  | "transient_error";

export interface AssetManagementError {
  code: string;
  correlationId: string | null;
  kind: AssetManagementErrorKind;
  message: string;
  title: string;
}

const integrityMarkers = [
  "artifact_mismatch",
  "checksum",
  "file_missing",
  "path_invalid",
  "manifest_invalid",
  "manifest_missing",
];

export function classifyAssetManagementError(
  error: unknown,
  fallbackCode: string,
): AssetManagementError {
  const code =
    error instanceof ApiRequestError
      ? error.code
      : error instanceof Error
        ? error.message
        : fallbackCode;
  const correlationId = error instanceof ApiRequestError ? error.correlationId : null;
  if (error instanceof ApiRequestError && error.routeNotFound) {
    return {
      code: "api_contract_mismatch",
      correlationId,
      kind: "contract_mismatch",
      title: "앱 버전 불일치",
      message: "현재 백엔드에는 이 관리 경로가 없습니다. 이전 DataLab 창을 종료한 뒤 최신 폴더의 dev.ps1로 다시 실행하세요.",
    };
  }
  if (code === "dataset_version_not_found" || code === "regression_model_not_found") {
    return {
      code,
      correlationId,
      kind: "asset_not_found",
      title: "저장 자산을 찾을 수 없음",
      message: "이미 삭제되었거나 목록이 오래되었을 수 있습니다. 목록을 새로고침하세요.",
    };
  }
  if (code === "asset_user_metadata_conflict") {
    return {
      code,
      correlationId,
      kind: "metadata_conflict",
      title: "다른 변경이 먼저 저장됨",
      message: "최신 이름과 메모를 다시 불러온 뒤 변경 내용을 확인하세요.",
    };
  }
  if (code.endsWith("_dependency") || code.endsWith("_deletion_blocked")) {
    return {
      code,
      correlationId,
      kind: "deletion_blocked",
      title: "참조 자산이 있어 삭제 차단됨",
      message: "연결된 분석, 예측, 모델 또는 관리한계를 먼저 확인해야 합니다. 자동 연쇄 삭제는 하지 않습니다.",
    };
  }
  if (integrityMarkers.some((marker) => code.includes(marker))) {
    return {
      code,
      correlationId,
      kind: "integrity_error",
      title: "저장 자산 무결성 오류",
      message: "checksum 또는 저장 경로 검증에 실패했습니다. 삭제된 것으로 간주하거나 임의 복구하지 않습니다.",
    };
  }
  return {
    code,
    correlationId,
    kind: "transient_error",
    title: "관리 요청 실패",
    message: "API 연결 상태를 확인하고 목록을 새로고침한 뒤 다시 시도하세요.",
  };
}
