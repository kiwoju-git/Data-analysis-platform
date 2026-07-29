export type WorkspaceMutationKind =
  | "dataset_created"
  | "dataset_archived"
  | "dataset_unarchived"
  | "dataset_deleted"
  | "model_deleted"
  | "analysis_deleted"
  | "export_deleted";

export interface WorkspaceMutation {
  kind: WorkspaceMutationKind;
  occurredAt: string;
  revision: number;
}

export const workspaceAssetAlreadyRemovedNotice =
  "이 자산은 데이터셋 정리 과정에서 이미 함께 삭제되어 목록을 갱신했습니다.";
