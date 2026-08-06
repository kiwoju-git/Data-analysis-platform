export type WorkspaceAssetType =
  | "dataset_version"
  | "analysis_run"
  | "regression_model"
  | "doe_design"
  | "bayesian_study";

export type WorkspaceAssetCategory = "datasets" | "analyses" | "models" | "designs";
export type WorkspaceAssetSort = "updated_desc" | "created_desc" | "name_asc";

export interface WorkspaceAssetFilters {
  category: WorkspaceAssetCategory | null;
  methodId?: string;
  status?: string;
  pinned?: boolean;
  search: string;
  sort?: WorkspaceAssetSort;
}

export interface WorkspaceAssetDescriptor {
  asset_id: string;
  asset_type: WorkspaceAssetType;
  subtype: string;
  method_id: string | null;
  display_name: string;
  secondary_text: string;
  status: string;
  created_at: string;
  updated_at: string;
  pinned: boolean;
  note: string | null;
  dependency_count: number;
  open_target: { path: string; label: string };
}

export interface WorkspaceAssetCatalogResponse {
  total: number;
  offset: number;
  limit: number;
  items: WorkspaceAssetDescriptor[];
}
