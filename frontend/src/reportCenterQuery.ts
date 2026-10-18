export type ReportSelectionQuery =
  | { kind: "absent" }
  | { kind: "valid"; analysisId: string }
  | { kind: "invalid"; code: "report_center_analysis_id_invalid" };

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu;

export function validReportAnalysisId(value: string): boolean {
  return uuidPattern.test(value);
}

export function readReportSelectionQuery(href: string): ReportSelectionQuery {
  const ids = new URL(href).searchParams.getAll("analysis_id");
  if (ids.length === 0) return { kind: "absent" };
  if (ids.length !== 1 || !validReportAnalysisId(ids[0])) {
    return { kind: "invalid", code: "report_center_analysis_id_invalid" };
  }
  return { kind: "valid", analysisId: ids[0].toLowerCase() };
}

export function reportSelectionLocation(href: string, analysisId: string | null): string {
  const url = new URL(href);
  if (analysisId === null) url.searchParams.delete("analysis_id");
  else url.searchParams.set("analysis_id", analysisId);
  return `${url.pathname}${url.search}${url.hash}`;
}

export function reportRequestErrorCode(error: unknown, fallback: string): string {
  // Transport APIs return machine codes. Never render an arbitrary exception message.
  const code = error instanceof Error ? error.message : null;
  return code !== null && /^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$/u.test(code) ? code : fallback;
}
