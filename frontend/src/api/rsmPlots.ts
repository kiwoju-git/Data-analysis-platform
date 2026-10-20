import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";
import type { RsmPlotSettings, RsmPlotSource, RsmPlotView, RsmSavedPlotView, RsmPlotViewDescriptor } from "./types/rsmPlots";

function base(designId: string, analysisId: string) {
  return `${getApiBaseUrl()}/api/v1/doe-designs/${encodeURIComponent(designId)}/response-surface-analyses/${encodeURIComponent(analysisId)}`;
}
async function json<T>(url: string, body?: unknown): Promise<T> {
  const response = await fetchApi(url, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!response.ok) throw await apiRequestError(response, "doe_rsm_plot_invalid");
  return await response.json() as T;
}
export const fetchRsmPlotSource = (design: string, analysis: string) =>
  json<RsmPlotSource>(`${base(design, analysis)}/plot-source`);
export const createRsmPlotView = (design: string, analysis: string, source: RsmPlotSource, settings: RsmPlotSettings) =>
  json<RsmPlotView>(`${base(design, analysis)}/plot-view`, { ...source, settings });
export const saveRsmPlotView = (view: RsmPlotView) =>
  json<RsmSavedPlotView>(`${base(view.design_id, view.analysis_id)}/plot-views`, {
    expected_result_sha256: view.expected_result_sha256,
    response_revision_id: view.response_revision_id, response_revision_sha256: view.response_revision_sha256,
    settings: view.bundle.settings, expected_view_sha256: view.view_sha256,
  });
export const fetchRsmPlotViews = (design: string, analysis: string) =>
  json<RsmPlotViewDescriptor[]>(`${base(design, analysis)}/plot-views`);
export const fetchRsmPlotView = (design: string, analysis: string, assetId: string) =>
  json<RsmSavedPlotView>(`${base(design, analysis)}/plot-views/${encodeURIComponent(assetId)}`);
