import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnalysisReportCapability, type AnalysisReportCapability } from "./api";
import type { AppLocale } from "./i18n/types";
import { createLatestRequestGuard } from "./latestRequest";

export function useAnalysisReportCapability(analysisId: string | null, locale: AppLocale, revision: number) {
  const key = JSON.stringify([analysisId, locale, revision]);
  const context = useRef(key);
  context.current = key;
  const requestGuard = useRef(createLatestRequestGuard()).current;
  const [state, setState] = useState<{
    key: string; capability: AnalysisReportCapability | null; error: string | null; loading: boolean;
  }>({ key, capability: null, error: null, loading: false });

  const refresh = useCallback(async () => {
    const request = requestGuard.begin();
    const current = () => context.current === key && requestGuard.isCurrent(request);
    setState({ key, capability: null, error: null, loading: analysisId !== null });
    if (analysisId === null) return;
    try {
      const capability = await fetchAnalysisReportCapability(analysisId, locale);
      if (!current()) return;
      if (capability == null || capability.capability_schema_version !== 1 ||
          capability.analysis_id !== analysisId || capability.locale !== locale ||
          !/^[a-f0-9]{64}$/.test(capability.source_result_sha256) ||
          capability.source_validation !== "stored_dependencies_only") {
        throw new Error("analysis_report_capability_invalid");
      }
      setState({ key, capability, error: null, loading: false });
    } catch (error) {
      if (current()) setState({ key, capability: null, error: error instanceof Error && /^[a-z][a-z0-9_]*$/.test(error.message) ? error.message : "analysis_report_capability_failed", loading: false });
    }
  }, [analysisId, key, locale, requestGuard]);

  useEffect(() => {
    void refresh();
    return () => requestGuard.cancel();
  }, [refresh, requestGuard]);

  return {
    analysisReportCapability: state.key === key ? state.capability : null,
    analysisReportCapabilityError: state.key === key ? state.error : null,
    isLoadingAnalysisReportCapability: state.key === key ? state.loading : analysisId !== null,
    onRefreshAnalysisReportCapability: () => { void refresh(); },
  };
}
