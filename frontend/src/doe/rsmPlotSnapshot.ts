import type { RsmPlotSettings, RsmPlotSource, RsmPlotView } from "../api/types/rsmPlots";

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value !== null && typeof value === "object") return `{${Object.entries(value)
    .sort(([a], [b]) => a.localeCompare(b)).map(([key, entry]) => `${JSON.stringify(key)}:${stable(entry)}`).join(",")}}`;
  return JSON.stringify(value);
}

export function rsmViewMatchesSnapshot(view: RsmPlotView, snapshot: {
  design: string; analysis: string; source: RsmPlotSource; settings: RsmPlotSettings;
}): boolean {
  return view.design_id === snapshot.design && view.analysis_id === snapshot.analysis &&
    view.expected_result_sha256 === snapshot.source.expected_result_sha256 &&
    view.response_revision_id === snapshot.source.response_revision_id &&
    view.response_revision_sha256 === snapshot.source.response_revision_sha256 &&
    /^[a-f0-9]{64}$/.test(view.view_sha256) &&
    stable(view.bundle.settings) === stable(snapshot.settings);
}
