import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type { DoeFactorialAnalysisResponse, GeneralFactorialAnalysisResponse } from "./types/doe";
import type { DoeAnalysisTermCatalog, DoeAnalysisAssetDescriptor, DoeAnalysisAssetList, DoeAnalysisDeletionPreflight, DoePredictionPreflightRequest, DoePredictionPreflightResponse, DoePredictionResponse } from "./types/doeModelWorkflow";

async function workflowJson<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetchApi(url, { method, headers: { Accept: "application/json", "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  if (!response.ok) throw new Error(await apiErrorCode(response, "doe_factorial_workflow_failed"));
  return await response.json() as T;
}

export const preflightFactorialPrediction = (design: string, analysis: string, body: DoePredictionPreflightRequest) =>
  workflowJson<DoePredictionPreflightResponse>(apiRoutes.factorialPredictionPreflight(design, analysis), "POST", body);
export const fetchDoeTermCatalog = (design: string, order: number) =>
  workflowJson<DoeAnalysisTermCatalog>(apiRoutes.factorialTermCatalog(design, order));
export const createFactorialPrediction = (design: string, analysis: string, body: DoePredictionPreflightRequest & { expected_preflight_sha256: string }) =>
  workflowJson<DoePredictionResponse>(apiRoutes.factorialPredictions(design, analysis), "POST", body);
export const fetchFactorialPrediction = (design: string, analysis: string, prediction: string) =>
  workflowJson<DoePredictionResponse>(apiRoutes.factorialPrediction(design, analysis, prediction));
export const fetchFactorialPredictionAssets = (design: string, analysis: string) =>
  workflowJson<DoeAnalysisAssetList>(apiRoutes.factorialPredictions(design, analysis));
export const fetchFactorialReports = (design: string, analysis: string) =>
  workflowJson<DoeAnalysisAssetList>(apiRoutes.factorialAnalysisExports(design, analysis));
export const createFactorialReport = (design: string, analysis: string, locale: "en" | "ko") =>
  workflowJson<DoeAnalysisAssetDescriptor>(apiRoutes.factorialAnalysisHtmlExport(design, analysis), "POST", { locale });
export const preflightFactorialAssetDeletion = (design: string, analysis: string, asset: string) =>
  workflowJson<DoeAnalysisAssetDescriptor>(apiRoutes.factorialAnalysisAssetDeletionPreflight(design, analysis, asset));
export const deleteFactorialAsset = (design: string, analysis: string, asset: DoeAnalysisAssetDescriptor) =>
  workflowJson<{ asset_id: string; deleted: true }>(apiRoutes.factorialAnalysisAsset(design, analysis, asset.asset_id), "DELETE", {
    confirmation_asset_id: asset.asset_id, expected_sha256: asset.sha256,
  });
export const preflightFactorialAnalysisDeletion = (design: string, analysis: string) =>
  workflowJson<DoeAnalysisDeletionPreflight>(apiRoutes.factorialAnalysisDeletionPreflight(design, analysis));
export const deleteFactorialAnalysis = (design: string, preflight: DoeAnalysisDeletionPreflight) =>
  workflowJson<DoeAnalysisDeletionPreflight>(apiRoutes.factorialAnalysisDelete(design, preflight.analysis_id), "DELETE", {
    confirmation_analysis_id: preflight.analysis_id, expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
  });
export const fetchStoredFactorialAnalysis = (design: string, analysis: string) =>
  workflowJson<DoeFactorialAnalysisResponse>(apiRoutes.factorialAnalysisDelete(design, analysis));
export const fetchStoredGeneralFactorialAnalysis = (design: string, analysis: string) =>
  workflowJson<GeneralFactorialAnalysisResponse>(apiRoutes.generalFactorialAnalysis(design, analysis));

export async function downloadFactorialAsset(design: string, analysis: string, asset: DoeAnalysisAssetDescriptor): Promise<void> {
  const response = await fetchApi(apiRoutes.factorialAnalysisAssetDownload(design, analysis, asset.asset_id));
  if (!response.ok) throw new Error(await apiErrorCode(response, "doe_factorial_workflow_failed"));
  const blob = await response.blob();
  const bytes = await blob.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const sha = Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, "0")).join("");
  if (sha !== asset.sha256 || bytes.byteLength !== asset.size_bytes) throw new Error("doe_factorial_asset_checksum_mismatch");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = `factorial-${asset.asset_id}.${asset.kind === "html_report" ? "html" : "json"}`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
