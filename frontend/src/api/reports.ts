import { apiRequestError, fetchApi, filenameFromContentDisposition } from "./client";
import { apiRoutes } from "./routes";
import { downloadSha256 } from "./downloadDigest";
import type { ManagedReportDescriptor, ManagedReportList, ReportSourceKind, ReportSourceList, ReportSourceRef, StoredReportCapability, StoredSourceSnapshot } from "./types/reports";
import type { AppLocale } from "../i18n/types";

async function reportJson<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetchApi(url, { method, headers: { Accept: "application/json", "Content-Type": "application/json" }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  if (!response.ok) throw await apiRequestError(response, "managed_report_request_failed");
  return await response.json() as T;
}
export const fetchReportSources = (kind: ReportSourceKind, offset = 0) => reportJson<ReportSourceList>(apiRoutes.reportSources(kind, 20, offset));
export const fetchStoredReportCapability = (source: ReportSourceRef, locale: AppLocale) => reportJson<StoredReportCapability>(apiRoutes.storedReportCapability(), "POST", { source, locale });
export const fetchStoredSourceSnapshot = (source: ReportSourceRef, locale: AppLocale) => reportJson<StoredSourceSnapshot>(apiRoutes.storedSourceSnapshot(), "POST", { source, locale });
export const fetchManagedReports = (source: ReportSourceRef, locale: AppLocale) => reportJson<ManagedReportList>(apiRoutes.managedReportQuery(), "POST", { source, locale });
export const fetchManagedReport = (id: string) => reportJson<ManagedReportDescriptor>(apiRoutes.managedReport(id));
export const createManagedReport = (source: ReportSourceRef, locale: AppLocale, sourceHash: string) => reportJson<ManagedReportDescriptor>(apiRoutes.managedReports(), "POST", { source, locale, expected_source_ref_sha256: sourceHash });
export const deleteManagedReport = (report: ManagedReportDescriptor) => reportJson<{ deleted: true }>(apiRoutes.managedReport(report.export_id), "DELETE", { source: report.source, expected_sha256: report.sha256 });

export async function fetchManagedReportDownload(report: ManagedReportDescriptor): Promise<{ blob: Blob; filename: string }> {
  const response = await fetchApi(apiRoutes.managedReportDownload(report.export_id), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: report.source, expected_sha256: report.sha256 }) });
  if (!response.ok) throw await apiRequestError(response, "managed_report_download_failed");
  const blob = await response.blob();
  const bytes = await blob.arrayBuffer();
  const hash = await downloadSha256(bytes);
  if (hash !== report.sha256 || bytes.byteLength !== report.size_bytes) throw new Error("managed_report_checksum_mismatch");
  return { blob, filename: filenameFromContentDisposition(response.headers.get("content-disposition")) ?? `report-${report.export_id}.html` };
}
