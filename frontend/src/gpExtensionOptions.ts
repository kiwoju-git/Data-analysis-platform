import type { GpValidationMethod } from "./api/types/analysisResultsRegression";

export interface GpExtensionDraft {
  groupColumnId: string;
  timeColumnId: string;
  timeFormat: "numeric" | "timestamp";
  timeUnit: string;
  timestampTimezone: "require_offset" | "UTC";
  gapTimeBlocks: number;
  lagEnabled: boolean;
  laggedColumnIds: string[];
  lagText: string;
  seriesColumnId: string;
  initialX: string;
  initialY: string;
  resourceProfile: "standard_exact" | "extended_exact";
}
export const defaultGpExtensionDraft = (): GpExtensionDraft => ({
  groupColumnId: "", timeColumnId: "", timeFormat: "numeric", timeUnit: "",
  timestampTimezone: "require_offset", gapTimeBlocks: 0, lagEnabled: false,
  laggedColumnIds: [], lagText: "1", seriesColumnId: "", initialX: "", initialY: "", resourceProfile: "standard_exact",
});
export interface GpExtensionOptions {
  cv: { group_column_id?: string; time_column_id?: string; time_format?: "numeric" | "timestamp"; time_unit?: string | null; timestamp_timezone?: "require_offset" | "UTC"; gap_time_blocks?: number };
  lag_features: { lagged_column_ids: string[]; lags: number[]; series_column_id: string | null; prediction_horizon: 1; interval: "observation_order"; gap_policy: "exclude_embargo_sources" } | null;
  initial_surface_x_column_id: string | null;
  initial_surface_y_column_id: string | null;
  resource_profile: "standard_exact" | "extended_exact";
}
export function buildGpExtensionOptions(draft: GpExtensionDraft, method: GpValidationMethod, predictors: readonly string[], response: string): GpExtensionOptions | null {
  const cv: GpExtensionOptions["cv"] = {};
  if (method === "group_k_fold") {
    if (!draft.groupColumnId || draft.groupColumnId === response || predictors.includes(draft.groupColumnId)) return null;
    cv.group_column_id = draft.groupColumnId;
  }
  if (method === "time_series_split") {
    if (!draft.timeColumnId || draft.timeColumnId === response || (draft.timeFormat === "numeric" && !draft.timeUnit.trim()) || !Number.isInteger(draft.gapTimeBlocks) || draft.gapTimeBlocks < 0 || draft.gapTimeBlocks > 1000) return null;
    Object.assign(cv, { time_column_id: draft.timeColumnId, time_format: draft.timeFormat, time_unit: draft.timeFormat === "numeric" ? draft.timeUnit.trim() : null, timestamp_timezone: draft.timestampTimezone, gap_time_blocks: draft.gapTimeBlocks });
  }
  let lag: GpExtensionOptions["lag_features"] = null;
  if (draft.lagEnabled) {
    const pieces = draft.lagText.split(",").map((value) => value.trim());
    if (method !== "time_series_split" || draft.laggedColumnIds.length === 0 || pieces.some((value) => !/^[1-9]\d*$/.test(value))) return null;
    const lags = pieces.map(Number);
    if (lags.some((value) => value > 100) || new Set(lags).size !== lags.length || predictors.length + lags.length * draft.laggedColumnIds.length > 12) return null;
    if (draft.seriesColumnId && (draft.seriesColumnId === response || draft.seriesColumnId === draft.timeColumnId || predictors.includes(draft.seriesColumnId))) return null;
    lag = { lagged_column_ids: [...draft.laggedColumnIds], lags, series_column_id: draft.seriesColumnId || null, prediction_horizon: 1, interval: "observation_order", gap_policy: "exclude_embargo_sources" };
  }
  if ((draft.initialX || draft.initialY) && (!draft.initialX || !draft.initialY || draft.initialX === draft.initialY || !predictors.includes(draft.initialX) || !predictors.includes(draft.initialY))) return null;
  return { cv, lag_features: lag, initial_surface_x_column_id: draft.initialX || null, initial_surface_y_column_id: draft.initialY || null, resource_profile: draft.resourceProfile };
}
